"""S0 provenance dump for Gemma 4 26B-A4B cache-correctness audit.

Captures model id, quantization, mlx versions, hardware, attention topology,
and the model_id-based config so JF/Sam can audit reproducibility.

Output: research/2026-04-26-s0-provenance.json
"""
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import importlib.metadata as md

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "research" / "2026-04-26-s0-provenance.json"

MODEL_ID_DEFAULT = "google/gemma-4-26B-A4B-it"


def shellout(cmd, timeout=10):
    try:
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip() or out.stderr.strip()
    except Exception as e:  # noqa: BLE001
        return f"<error: {e}>"


def pkg_version(name):
    try:
        return md.version(name)
    except Exception as e:  # noqa: BLE001
        return f"<not installed: {e}>"


def find_pkg_commit(pkg_name):
    """Best-effort: locate package on disk and check if its parent is a git repo."""
    try:
        dist = md.distribution(pkg_name)
        loc = dist.locate_file("")
        if loc is None:
            return None
        loc = Path(str(loc))
        # Walk up looking for a .git
        for parent in [loc] + list(loc.parents):
            if (parent / ".git").exists():
                sha = subprocess.run(
                    ["git", "-C", str(parent), "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                )
                if sha.returncode == 0:
                    return {"git_root": str(parent), "sha": sha.stdout.strip()}
        return "from PyPI (no .git in parents)"
    except Exception as e:  # noqa: BLE001
        return f"<error: {e}>"


def hf_config_for(model_id):
    """Locate the HF cache config.json for the model id and parse it."""
    cache_root = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))) / "hub"
    safe = "models--" + model_id.replace("/", "--")
    snapshot_dir = cache_root / safe / "snapshots"
    if not snapshot_dir.exists():
        return {"path": None, "error": f"snapshots dir missing: {snapshot_dir}"}
    snaps = sorted(snapshot_dir.iterdir())
    if not snaps:
        return {"path": None, "error": "no snapshot subdirs"}
    cfg_path = snaps[-1] / "config.json"
    if not cfg_path.exists():
        return {"path": str(cfg_path), "error": "config.json missing"}
    with cfg_path.open() as f:
        cfg = json.load(f)
    text_cfg = cfg.get("text_config", {})
    layer_types = text_cfg.get("layer_types", [])
    swa_layers = [i for i, t in enumerate(layer_types) if t == "sliding_attention"]
    full_layers = [i for i, t in enumerate(layer_types) if t == "full_attention"]
    topology = {
        "model_type": cfg.get("model_type"),
        "image_token_id": cfg.get("image_token_id"),
        "video_token_id": cfg.get("video_token_id"),
        "vision_soft_tokens_per_image": cfg.get("vision_soft_tokens_per_image"),
        "text_config": {
            "num_hidden_layers": text_cfg.get("num_hidden_layers"),
            "sliding_window": text_cfg.get("sliding_window"),
            "attention_chunk_size": text_cfg.get("attention_chunk_size"),
            "attn_window_size": text_cfg.get("attn_window_size"),
            "rope_parameters": text_cfg.get("rope_parameters"),
            "rope_local_base_freq": text_cfg.get("rope_local_base_freq"),
            "rope_global_base_freq": text_cfg.get("rope_global_base_freq"),
            "layer_types": layer_types,
            "n_sliding_layers": len(swa_layers),
            "n_full_layers": len(full_layers),
            "sliding_layer_indices": swa_layers,
            "full_layer_indices": full_layers,
            "max_position_embeddings": text_cfg.get("max_position_embeddings"),
            "use_bidirectional_attention": text_cfg.get("use_bidirectional_attention"),
            "enable_moe_block": text_cfg.get("enable_moe_block"),
            "num_experts": text_cfg.get("num_experts"),
            "top_k_experts": text_cfg.get("top_k_experts"),
            "dtype": text_cfg.get("dtype"),
        },
        "vision_config": {
            "num_hidden_layers": cfg.get("vision_config", {}).get("num_hidden_layers"),
            "hidden_size": cfg.get("vision_config", {}).get("hidden_size"),
            "patch_size": cfg.get("vision_config", {}).get("patch_size"),
            "pooling_kernel_size": cfg.get("vision_config", {}).get("pooling_kernel_size"),
            "max_position_embeddings": cfg.get("vision_config", {}).get("max_position_embeddings"),
            "rope_parameters": cfg.get("vision_config", {}).get("rope_parameters"),
        },
    }
    quantization = cfg.get("quantization") or {
        # mlx-vlm community quants put the field at root level. Pure HF weights
        # don't carry one.
        "note": "no top-level 'quantization' field in HF config; weights are likely BF16 native"
    }
    return {"path": str(cfg_path), "model_type": cfg.get("model_type"),
            "topology": topology, "quantization": quantization,
            "dtype_top": cfg.get("dtype")}


def safetensors_quant_info(model_id):
    """Look at safetensors metadata for quantization hints."""
    cache_root = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface"))) / "hub"
    safe = "models--" + model_id.replace("/", "--")
    snapshot_dir = cache_root / safe / "snapshots"
    if not snapshot_dir.exists():
        return None
    snaps = sorted(snapshot_dir.iterdir())
    if not snaps:
        return None
    snap = snaps[-1]
    sft_files = sorted(snap.glob("*.safetensors"))
    info = {"n_safetensor_files": len(sft_files), "files_sample": [p.name for p in sft_files[:3]]}
    if not sft_files:
        return info
    try:
        from safetensors import safe_open
        with safe_open(sft_files[0], framework="numpy") as f:
            keys = list(f.keys())[:20]
            info["sample_keys"] = keys
            # Inspect dtypes of first few tensors
            dtypes = {}
            for k in keys[:6]:
                t = f.get_slice(k)
                dtypes[k] = {"dtype": t.get_dtype(), "shape": list(t.get_shape())}
            info["sample_dtypes"] = dtypes
            md_ = f.metadata() or {}
            info["safetensors_metadata"] = md_
    except Exception as e:  # noqa: BLE001
        info["safetensors_error"] = repr(e)
    return info


def main():
    model_id = os.environ.get("S0_MODEL_ID", MODEL_ID_DEFAULT)
    prov = {
        "model_id": model_id,
        "python_version": sys.version,
        "platform_uname": dict(platform.uname()._asdict()),
        "packages": {
            "mlx": pkg_version("mlx"),
            "mlx-lm": pkg_version("mlx-lm"),
            "mlx-vlm": pkg_version("mlx-vlm"),
            "transformers": pkg_version("transformers"),
            "huggingface-hub": pkg_version("huggingface-hub"),
            "safetensors": pkg_version("safetensors"),
            "numpy": pkg_version("numpy"),
            "pillow": pkg_version("Pillow"),
        },
        "mlx_vlm_commit": find_pkg_commit("mlx-vlm"),
        "mlx_lm_commit": find_pkg_commit("mlx-lm"),
        "hardware": {
            "system_profiler": shellout("system_profiler SPHardwareDataType"),
            "machdep_cpu_brand": shellout("sysctl -n machdep.cpu.brand_string"),
            "uname_a": shellout("uname -a"),
        },
        "thermal_state": shellout("pmset -g therm"),
        "power_mode": shellout("pmset -g | head -10"),
        "cwd_git_sha": shellout(f"git -C {REPO_ROOT} rev-parse HEAD"),
        "cwd_git_status_short": shellout(f"git -C {REPO_ROOT} status --short | head -40"),
        "hf_config": hf_config_for(model_id),
        "safetensors_inspection": safetensors_quant_info(model_id),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(prov, f, indent=2, default=str)
    print(f"Provenance written to {OUT_PATH}")
    # Highlight the JF-relevant facts
    topo = prov["hf_config"].get("topology", {}).get("text_config", {}) if prov["hf_config"] else {}
    print("--- attention topology summary ---")
    print(f"  num_hidden_layers: {topo.get('num_hidden_layers')}")
    print(f"  sliding_window:    {topo.get('sliding_window')}")
    print(f"  n_sliding_layers:  {topo.get('n_sliding_layers')}")
    print(f"  n_full_layers:     {topo.get('n_full_layers')}")
    print(f"  layer_types[:8]:   {topo.get('layer_types', [])[:8]}")


if __name__ == "__main__":
    main()
