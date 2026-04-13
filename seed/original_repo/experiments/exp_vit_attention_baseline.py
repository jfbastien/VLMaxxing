#!/usr/bin/env python3
"""
Experiment: ViT Attention Mass as Gold Standard for Spatial Importance
=====================================================================
Extracts per-token attention mass from Qwen2.5-VL-7B's vision encoder
at every layer and correlates with pixel variance and JPEG complexity signals.

This establishes the CEILING for any codec-based spatial importance signal:
if codec signal X correlates at rho=Y with ViT attention, then Y is the
max codec efficiency for spatial merge decisions.

Also tests early-layer attention as cheap approximation of final-layer
attention, enabling a compute-aware merge strategy:
  - Run 2 ViT layers at full tokens (~6% ViT compute)
  - Merge based on early attention
  - Run remaining 30 layers at reduced tokens

Usage:
    cd experiments && uv run python exp_vit_attention_baseline.py
"""

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from scipy.stats import spearmanr, pearsonr

from qtable_prefilter import extract_block_complexity

IMAGE_DIR = Path(__file__).parent / "data" / "images"
RESULTS_FILE = Path(__file__).parent / "vit_attention_results.json"


def get_test_images():
    """Get test images grouped by scene type."""
    images = {}
    for f in sorted(IMAGE_DIR.glob("*.jpg")):
        images[f.stem] = str(f)
    return images


def compute_pixel_variance_per_patch(img, patch_size=14, grid_h=None, grid_w=None):
    """Compute pixel variance for each ViT patch.
    Returns array of shape [grid_h, grid_w] with variance per patch.
    """
    target_h = grid_h * patch_size
    target_w = grid_w * patch_size
    img_resized = img.resize((target_w, target_h), Image.BILINEAR)
    arr = np.array(img_resized.convert("RGB"), dtype=np.float32)
    
    # Luminance
    lum = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]
    
    patches = lum.reshape(grid_h, patch_size, grid_w, patch_size)
    patches = patches.transpose(0, 2, 1, 3)  # (gh, gw, ps, ps)
    variance = np.var(patches.reshape(grid_h, grid_w, -1), axis=2)
    return variance


def compute_jpeg_complexity_per_token(jpeg_path, token_h, token_w):
    """Get JPEG surviving AC coefficient count mapped to token grid."""
    result = extract_block_complexity(jpeg_path)
    if result is None:
        return None
    
    surviving = result["surviving"]  # (h_blocks, w_blocks)
    surv_tensor = torch.tensor(surviving, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
    mapped = F.interpolate(surv_tensor, size=(token_h, token_w), mode="bilinear", align_corners=False)
    return mapped.squeeze().numpy()


class AttentionExtractor:
    """Extracts per-layer attention weights from Qwen2.5-VL's ViT."""
    
    def __init__(self, model_name="Qwen/Qwen2.5-VL-7B-Instruct"):
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"Loading {model_name} on {self.device} with eager attention...")
        
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            attn_implementation="eager",
        ).to(self.device)
        self.model.eval()
        self.vm = self.model.model.visual
        
        self.num_layers = len(self.vm.blocks)
        self.spatial_merge_size = self.vm.spatial_merge_size
        self.fullatt_indexes = list(self.vm.fullatt_block_indexes)
        print(f"ViT: {self.num_layers} layers, spatial_merge_size={self.spatial_merge_size}")
        print(f"Full attention layers: {self.fullatt_indexes}")
        
        self.attention_weights = {}
        self._originals = {}
    
    def _install_hooks(self):
        """Monkey-patch each VisionAttention forward to capture attention weights."""
        self.attention_weights = {}
        self._originals = {}
        
        for layer_idx, blk in enumerate(self.vm.blocks):
            attn_module = blk.attn
            self._originals[layer_idx] = attn_module.forward
            
            # Create closure capturing layer_idx
            def make_hooked(li, am):
                extractor = self
                from transformers.models.qwen2_5_vl.modeling_qwen2_5_vl import apply_rotary_pos_emb_vision
                
                def hooked_forward(hidden_states, cu_seqlens, rotary_pos_emb=None,
                                   position_embeddings=None, **kwargs):
                    seq_length = hidden_states.shape[0]
                    qkv = am.qkv(hidden_states).reshape(seq_length, 3, am.num_heads, -1).permute(1, 0, 2, 3).unbind(0)
                    query_states, key_states, value_states = qkv
                    
                    cos, sin = position_embeddings
                    query_states, key_states = apply_rotary_pos_emb_vision(query_states, key_states, cos, sin)
                    
                    q = query_states.transpose(0, 1).unsqueeze(0)
                    k = key_states.transpose(0, 1).unsqueeze(0)
                    v = value_states.transpose(0, 1).unsqueeze(0)
                    
                    lengths = cu_seqlens[1:] - cu_seqlens[:-1]
                    q_splits = torch.split(q, lengths.tolist(), dim=2)
                    k_splits = torch.split(k, lengths.tolist(), dim=2)
                    v_splits = torch.split(v, lengths.tolist(), dim=2)
                    
                    all_attn_w = []
                    attn_outputs = []
                    
                    for qs, ks, vs in zip(q_splits, k_splits, v_splits):
                        scaling = am.head_dim ** -0.5
                        aw = torch.matmul(qs, ks.transpose(2, 3)) * scaling
                        aw = torch.nn.functional.softmax(aw, dim=-1, dtype=torch.float32).to(qs.dtype)
                        ao = torch.matmul(aw, vs)
                        ao = ao.transpose(1, 2).contiguous()
                        all_attn_w.append(aw.detach().cpu())
                        attn_outputs.append(ao)
                    
                    extractor.attention_weights[li] = all_attn_w
                    
                    attn_output = torch.cat(attn_outputs, dim=1)
                    attn_output = attn_output.reshape(seq_length, -1).contiguous()
                    attn_output = am.proj(attn_output)
                    return attn_output
                
                return hooked_forward
            
            attn_module.forward = make_hooked(layer_idx, attn_module)
    
    def _remove_hooks(self):
        for layer_idx, orig in self._originals.items():
            self.vm.blocks[layer_idx].attn.forward = orig
        self._originals = {}
    
    def extract_attention(self, img):
        """Extract per-token attention mass at every layer.
        
        Returns:
            per_layer_spatial_mass: dict[layer_idx] -> np array [num_post_merge_tokens]
            gh, gw: post-merge token grid dimensions
            vit_time: seconds for ViT forward
        """
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": "Describe this image."},
        ]}]
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(
            text=[text], images=[img], return_tensors="pt", padding=True
        ).to(self.device)
        
        grid_thw = inputs["image_grid_thw"]
        sms = self.spatial_merge_size
        gh = int(grid_thw[0, 1]) // sms
        gw = int(grid_thw[0, 2]) // sms
        
        print(f"  Grid: {int(grid_thw[0,1])}x{int(grid_thw[0,2])} patches -> "
              f"{gh}x{gw} = {gh*gw} tokens (after {sms}x merge)")
        
        self._install_hooks()
        
        t0 = time.time()
        with torch.no_grad():
            vit_out = self.vm(inputs["pixel_values"], grid_thw=grid_thw)
        vit_time = time.time() - t0
        print(f"  ViT forward: {vit_time*1000:.0f}ms")
        
        # Get window_index for un-reordering
        window_index, _ = self.vm.get_window_index(grid_thw)
        reverse_indices = torch.argsort(window_index).numpy()
        
        total_pre_merge = int(grid_thw[0,0] * grid_thw[0,1] * grid_thw[0,2])
        merge_unit = sms ** 2
        
        per_layer_spatial_mass = {}
        
        for layer_idx in range(self.num_layers):
            if layer_idx not in self.attention_weights:
                continue
            
            chunks = self.attention_weights[layer_idx]
            is_fullatt = layer_idx in self.fullatt_indexes
            
            if is_fullatt and len(chunks) == 1:
                aw = chunks[0]  # (1, heads, N, N)
                # Attention RECEIVED: sum over source dim (dim=2), avg over heads
                received = aw[0].sum(dim=1).mean(dim=0)  # (N,)
                mass = received.numpy()
            else:
                mass = np.zeros(total_pre_merge, dtype=np.float32)
                pos = 0
                for aw_chunk in chunks:
                    chunk_len = aw_chunk.shape[2]
                    received = aw_chunk[0].sum(dim=1).mean(dim=0)
                    mass[pos:pos + chunk_len] = received.numpy()
                    pos += chunk_len
            
            # Group by merge_unit and average, then undo window reorder
            n_groups = total_pre_merge // merge_unit
            grouped = mass[:n_groups * merge_unit].reshape(n_groups, merge_unit)
            group_avg = grouped.mean(axis=1)
            spatial_mass = group_avg[reverse_indices[:n_groups]]
            per_layer_spatial_mass[layer_idx] = spatial_mass
        
        self._remove_hooks()
        return per_layer_spatial_mass, gh, gw, vit_time


def run_experiment():
    """Run the full ViT attention baseline experiment."""
    images = get_test_images()
    if not images:
        print("ERROR: No test images found in", IMAGE_DIR)
        sys.exit(1)
    
    print(f"Found {len(images)} test images:")
    for name in images:
        print(f"  {name}")
    
    extractor = AttentionExtractor("Qwen/Qwen2.5-VL-7B-Instruct")
    
    all_results = {}
    key_layers = [0, 1, 3, 7, 15, 23, 30, 31]
    
    for img_name, img_path in images.items():
        print(f"\n{'='*60}")
        print(f"Processing: {img_name}")
        
        img = Image.open(img_path)
        print(f"  Image size: {img.size}")
        
        per_layer_mass, gh, gw, vit_time = extractor.extract_attention(img)
        
        available_layers = sorted(per_layer_mass.keys())
        print(f"  Attention extracted for {len(available_layers)} layers")
        
        final_layer = max(available_layers)
        gold_std = per_layer_mass[final_layer]
        n_tokens = len(gold_std)
        
        # Pixel variance at pre-merge resolution, then average to post-merge
        pv = compute_pixel_variance_per_patch(img, patch_size=14,
                                               grid_h=gh * extractor.spatial_merge_size,
                                               grid_w=gw * extractor.spatial_merge_size)
        sms = extractor.spatial_merge_size
        pv = pv.reshape(gh, sms, gw, sms).mean(axis=(1, 3))
        pv_flat = pv.flatten()
        
        # JPEG complexity
        jpeg_complexity = compute_jpeg_complexity_per_token(img_path, gh, gw)
        jpeg_flat = jpeg_complexity.flatten() if jpeg_complexity is not None else None
        
        result = {
            "image": img_name,
            "image_size": list(img.size),
            "token_grid": [gh, gw],
            "num_tokens": n_tokens,
            "vit_time_ms": round(vit_time * 1000, 1),
            "layer_correlations": {},
            "signal_correlations": {},
        }
        
        # Layer vs final correlations
        for layer_idx in available_layers:
            if layer_idx == final_layer:
                continue
            layer_mass = per_layer_mass[layer_idx]
            if len(layer_mass) != n_tokens:
                continue
            rho, _ = spearmanr(layer_mass, gold_std)
            r, _ = pearsonr(layer_mass, gold_std)
            result["layer_correlations"][str(layer_idx)] = {
                "spearman": round(float(rho), 4),
                "pearson": round(float(r), 4),
            }
        
        # Signal vs final attention
        if len(pv_flat) == n_tokens:
            rho_pv, _ = spearmanr(pv_flat, gold_std)
            r_pv, _ = pearsonr(pv_flat, gold_std)
            result["signal_correlations"]["pixel_variance"] = {
                "spearman": round(float(rho_pv), 4),
                "pearson": round(float(r_pv), 4),
            }
        else:
            print(f"  WARN: pv size {len(pv_flat)} != tokens {n_tokens}")
        
        if jpeg_flat is not None and len(jpeg_flat) == n_tokens:
            rho_jp, _ = spearmanr(jpeg_flat, gold_std)
            r_jp, _ = pearsonr(jpeg_flat, gold_std)
            result["signal_correlations"]["jpeg_surviving_ac"] = {
                "spearman": round(float(rho_jp), 4),
                "pearson": round(float(r_jp), 4),
            }
        elif jpeg_flat is not None:
            print(f"  WARN: jpeg size {len(jpeg_flat)} != tokens {n_tokens}")
        
        # Attention distribution stats
        result["attention_stats"] = {
            "final_mean": round(float(np.mean(gold_std)), 6),
            "final_std": round(float(np.std(gold_std)), 6),
            "final_min": round(float(np.min(gold_std)), 6),
            "final_max": round(float(np.max(gold_std)), 6),
            "dynamic_range": round(float(np.max(gold_std) / (np.min(gold_std) + 1e-8)), 2),
        }
        
        # Print summary
        print(f"\n  Layer vs Final (layer {final_layer}) Spearman rho:")
        for li in key_layers:
            if str(li) in result["layer_correlations"]:
                rho = result["layer_correlations"][str(li)]["spearman"]
                pct = (li + 1) / (final_layer + 1) * 100
                print(f"    Layer {li:2d} ({pct:4.0f}% compute): rho = {rho:.4f}")
        
        print(f"\n  External signals vs Final attention:")
        for sig_name, vals in result["signal_correlations"].items():
            if "spearman" in vals:
                print(f"    {sig_name}: rho = {vals['spearman']:.4f}")
        
        all_results[img_name] = result
        extractor.attention_weights = {}
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    
    # ---- AGGREGATE ----
    print(f"\n{'='*60}")
    print("AGGREGATE RESULTS")
    print(f"{'='*60}")
    
    layer_rhos = {}
    for result in all_results.values():
        for layer_str, vals in result["layer_correlations"].items():
            layer = int(layer_str)
            layer_rhos.setdefault(layer, []).append(vals["spearman"])
    
    aggregate_layers = {}
    for layer in sorted(layer_rhos.keys()):
        mean_rho = float(np.mean(layer_rhos[layer]))
        std_rho = float(np.std(layer_rhos[layer]))
        aggregate_layers[str(layer)] = {
            "mean_spearman": round(mean_rho, 4),
            "std_spearman": round(std_rho, 4),
            "n": len(layer_rhos[layer]),
        }
    
    print("\nLayer vs Final (mean Spearman rho):")
    final_layer_num = max(layer_rhos.keys()) if layer_rhos else 31
    for layer in sorted(layer_rhos.keys()):
        m = aggregate_layers[str(layer)]["mean_spearman"]
        s = aggregate_layers[str(layer)]["std_spearman"]
        pct = (layer + 1) / (final_layer_num + 1) * 100
        print(f"  Layer {layer:2d} ({pct:4.0f}%): rho = {m:.4f} +/- {s:.4f}")
    
    signal_rhos = {}
    for result in all_results.values():
        for sig_name, vals in result["signal_correlations"].items():
            if isinstance(vals, dict) and "spearman" in vals:
                signal_rhos.setdefault(sig_name, []).append(vals["spearman"])
    
    aggregate_signals = {}
    for sig_name in sorted(signal_rhos.keys()):
        mean_rho = float(np.mean(signal_rhos[sig_name]))
        std_rho = float(np.std(signal_rhos[sig_name]))
        aggregate_signals[sig_name] = {
            "mean_spearman": round(mean_rho, 4),
            "std_spearman": round(std_rho, 4),
            "n": len(signal_rhos[sig_name]),
        }
    
    print("\nExternal signals vs Final attention:")
    for sig_name, vals in aggregate_signals.items():
        print(f"  {sig_name}: rho = {vals['mean_spearman']:.4f} +/- {vals['std_spearman']:.4f}")
    
    # Comparison table
    print("\n" + "="*80)
    print("SPATIAL IMPORTANCE SIGNAL COMPARISON TABLE")
    print("="*80)
    fmt = f"{'Signal':<30} {'rho w/ Final Attn':>18} {'Source':>15} {'Compute':>12}"
    print(fmt)
    print("-"*80)
    print(f"{'ViT layer '+str(final_layer_num)+' attn':<30} {'1.0000 (defn)':>18} {'ViT':>15} {'100% ViT':>12}")
    
    for layer in [23, 15, 7, 3, 1, 0]:
        if str(layer) in aggregate_layers:
            r = aggregate_layers[str(layer)]["mean_spearman"]
            pct = (layer + 1) / (final_layer_num + 1) * 100
            print(f"{'ViT layer '+str(layer)+' attn':<30} {r:>18.4f} {'ViT':>15} {f'{pct:.0f}% ViT':>12}")
    
    for sig_name, vals in aggregate_signals.items():
        cost = "~1ms" if "pixel" in sig_name else "~0ms"
        source = "Pixels" if "pixel" in sig_name else "JPEG"
        print(f"{sig_name:<30} {vals['mean_spearman']:>18.4f} {source:>15} {cost:>12}")
    print("-"*80)
    
    output = {
        "experiment": "vit_attention_baseline",
        "model": "Qwen/Qwen2.5-VL-7B-Instruct",
        "num_images": len(all_results),
        "vit_config": {
            "num_layers": extractor.num_layers,
            "spatial_merge_size": extractor.spatial_merge_size,
            "fullatt_block_indexes": extractor.fullatt_indexes,
        },
        "aggregate_layer_correlations": aggregate_layers,
        "aggregate_signal_correlations": aggregate_signals,
        "per_image": all_results,
    }
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {RESULTS_FILE}")
    
    return output


if __name__ == "__main__":
    run_experiment()
