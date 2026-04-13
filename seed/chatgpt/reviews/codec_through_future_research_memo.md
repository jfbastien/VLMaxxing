# Codec-Through: expanded future-research memo

## Core update

The strongest broadened framing is no longer just **embedding caching**. It is:

**codec-conditioned dynamic compute for video VLMs**.

That broader program includes:
- temporal cache reuse
- changed-window sparse execution
- changed-query attention
- frame scheduling from codec metadata
- task-aware luma/chroma/resolution policies
- egomotion-aware stabilization and multi-reference caching
- screen-content specialization
- multi-camera and multi-sensor fusion
- robustness against compute-denial and temporal adversarial inputs
- long-term machine-first codecs and hardware co-design

## Systems-engineering low-hanging fruit

1. **Early-exit before pixels**
   Use codec metadata to skip decode and skip the vision encoder on fully static or low-novelty frames.

2. **Changed-window execution, not just changed-token substitution**
   Move the savings before or inside the vision encoder.

3. **Changed-query attention**
   Let dynamic tokens query broadly; keep static tokens as memory, summaries, or local-only context.

4. **Frame scheduling from the GOP**
   Use I/P/B type, residual size, motion magnitude, and bitrate bursts to decide which frames deserve full processing.

5. **Luma-first / chroma-on-demand policies**
   Many tasks can tolerate grayscale or reduced chroma. Promote chroma only for color-sensitive questions.

6. **Resolution ladders**
   Run low resolution first, then selectively refine ROIs or uncertain regions.

7. **Screen-content fork**
   Slides, UIs, code editors, and spreadsheets should use different heuristics from natural video.

8. **Asynchronous pipeline engineering**
   Overlap decode, novelty classification, sparse vision compute, and LLM generation.

9. **Deadline-aware inference**
   Choose the visual budget to meet a control or serving deadline instead of using a fixed frame/token budget.

10. **Robustness harness first-class citizen**
    Every efficiency gain should be paired with a compute-denial and adversarial-stability test.

## Codec truths and what to do with each

### 1. Prediction + residual is the real structure of video
A codec does not really store "frames". It stores references plus corrections.

**Exploit:** treat static areas as memory, residual-heavy areas as mandatory recompute, and motion vectors as routing priors.

### 2. Block sizes should adapt to local complexity
Modern codecs use variable partitioning because flat and detailed regions want different granularity.

**Exploit:** adaptive tokenization / quadtree frontend instead of a fixed visual patch grid.

### 3. Luma matters more often than chroma
Codecs usually allocate more fidelity to brightness than color.

**Exploit:** task-aware luma-first inference; chroma only where color matters.

### 4. Frequency matters
Transforms separate coarse structure from fine detail.

**Exploit:** coarse-to-fine visual encoding, progressive refinement, text/edge-focused high-frequency rescue.

### 5. Multiple references matter
Codecs already look beyond a single previous frame.

**Exploit:** multi-reference cache, B-frame-inspired hidden-state interpolation, best-reference selection.

### 6. Camera motion is different from object motion
AV1 and newer codecs explicitly model warped/global motion.

**Exploit:** stabilize first; cache second. Canonical coordinates are better than naïve embedding relocation.

### 7. Screen content is not natural video
Palette coding and intra block copy exist for a reason.

**Exploit:** exact-copy, glyph-like, and palette-like token paths for UI/video of screens.

### 8. ROI and scalability are underused
Wavelet/progressive systems made coarse-to-fine and ROI access natural.

**Exploit:** low-cost global pass followed by ROI refinement guided by the prompt, uncertainty, or detector outputs.

### 9. Hardware feasibility shapes codec design
Classic codecs are constrained by decode complexity, memory access, and branch-heavy control.

**Exploit:** future machine codecs should optimize not just bitrate, but decoder regularity, tensor-friendliness, and low-latency scheduling.

## High-priority new experiments

### Immediate
1. True codec metadata vs pixel-diff on the same clips.
2. Changed-window sparse execution inside the visual stack.
3. Changed-query attention simulator and then implementation.
4. Luma/chroma/gray-only and low-resolution sweeps.
5. Frame scheduling from GOP metadata and residual bursts.
6. Egomotion stabilization before caching for FPV/mobile video.
7. Robustness / compute-denial benchmark.

### Medium-term
1. Multi-reference and B-frame-aware caching.
2. Screen-content specialization.
3. Prompt-conditioned visual fidelity policy.
4. Multi-camera shared cache in world coordinates.
5. IMU + video fusion for temporal grounding.
6. ROI refinement with uncertainty triggers.

### Long-term
1. Machine-first codec with direct token outputs.
2. Hybrid classical-neural codec for machine utility.
3. Feature-native transport and standardization alignment with VCM/FCM.
4. Hardware co-design for tensor-friendly decode.
5. Scene/state/world codecs rather than frame codecs.

## Robotics interpretation

The promising robotics version is not just "cache static tokens". It is:
- world-aligned static memory
- dynamic working set around gripper, manipulated object, contact zone, and goal site
- pose/time-aware updates
- compute budget guardrails and safe fallback policy

This can raise effective visual update rate sharply, but should **not** eliminate hard safety layers. Efficiency can collapse perception hierarchy; it should not eliminate fail-safe control hierarchy.

## Adversarial / red-team concerns

Treat these as evaluation categories, not deployment assumptions:
- temporal flicker / strobe-like novelty inflation
- rolling-shutter or lighting-induced stripe artifacts
- high-frequency textures that force partition explosions or residual bursts
- reflective/occluding materials that create false novelty everywhere
- sensor desynchronization across camera/IMU/multi-camera setups
- compute-denial scenes that maximize change masks while preserving semantics

Required defenses:
- compute budget caps
- anti-flicker preprocessing / temporal smoothing
- watchdog timers and safe-mode fallback
- novelty-rate anomaly detection
- cross-sensor consistency checks
- uncertainty-triggered refresh or controller slowdown

## Machine-first codec direction

The natural endgame is a codec optimized for:
- task utility, not human perception alone
- decoder latency and energy
- direct emission of visual tokens / descriptors
- synchronization with time, pose, and sensor metadata
- uncertainty estimates
- regular dense compute that maps well to modern accelerators

A provocative but useful thought: future codecs may be criticized for having **too little regular tensor math** and **too much branchy entropy plumbing** for AI pipelines.

## Paper framing

Current paper: **training-free temporal compression via embedding caching**.

Next paper / broader program:
**codec-conditioned dynamic compute for video VLMs**.

Paper future-work section should explicitly mention:
- sparse execution beyond semantic substitution
- changed-query attention
- frame scheduling and task-aware fidelity policies
- robustness to compute-denial inputs
- egomotion and multi-reference caching
- multi-camera / sensor fusion
- machine-first codec and hardware co-design

## Key scientific questions

1. Where is the real waste: decode, vision encoder, attention, or LLM prefill?
2. Which codec signals are best for novelty, uncertainty, scheduling, and saliency?
3. When is grayscale or low-resolution enough, and for which task families?
4. Does stabilization beat relocation for mobile video?
5. How much does multi-reference caching help under occlusion and large motion?
6. What attacks maximize compute without changing semantics much?
7. Can a machine-first codec beat human-first codecs on both latency and downstream task utility?
8. Can a world/state codec replace frame streams for robotics and embodied AI?
