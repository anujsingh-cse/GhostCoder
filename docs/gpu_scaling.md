# ⚡ GPU Scaling & Model Presets Guide

GhostCoder features a dynamic **GPU Auto-Scaling engine** that auto-detects your local GPU hardware VRAM capacity and automatically loads the largest compatible models.

---

## 📟 GPU Tier System
When the daemon initializes, it parses `nvidia-smi` (or platform equivalents) to estimate VRAM availability and assigns a hardware profile:

| Profile Tier | VRAM Capacity | Max Model Size | Classifier Model | Coder Model | Reasoner Model | Skeptic Model |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`entry`** | < 6 GB | 3B params | `qwen2.5:0.5b` | `qwen2.5-coder:1.5b` | `qwen2.5-coder:1.5b` | `qwen2.5:0.5b` |
| **`mid`** | 6 - 12 GB | 7B params | `qwen2.5:0.5b` | `qwen2.5-coder:7b` | `qwen2.5-coder:7b` | `qwen2.5:0.5b` |
| **`high`** | 12 - 20 GB | 14B params | `qwen2.5:0.5b` | `qwen2.5-coder:14b` | `deepseek-coder:6.7b` | `qwen2.5:3b` |
| **`workstation`** | 20 - 48 GB | 32B params | `qwen2.5:3b` | `qwen2.5-coder:32b` | `deepseek-coder:33b` | `qwen2.5:7b` |
| **`datacenter`** | >= 48 GB | 72B param+ | `qwen2.5:7b` | `qwen2.5-coder:72b` | `deepseek-coder:33b` | `qwen2.5:14b` |

---

## 💾 Memory Allocations & Keep-Alive Lifecycle
To operate seamlessly alongside other user processes, GhostCoder implements strict VRAM management:

1.  **VRAM Limit**: The maximum memory allowed for models is calculated as `min(Total_VRAM * 85%, Total_VRAM - Headroom)`. The default safety headroom is `500 MB`.
2.  **Continuous Classifier**: The fast classifier model is loaded permanently with `keep_alive = -1`.
3.  **On-Demand Coder**: The heavier Coder model is loaded only when generating a suggestion.
4.  **Auto-Unload Guard**: When loading the Coder model would violate the VRAM budget limit, GhostCoder automatically triggers an eviction command to unload any other active models from Ollama memory (`keep_alive = 0`). Once idle for `30 seconds`, the Coder model is automatically unloaded to free VRAM.

---

## ⚙️ Hardware Overrides & Hot-Swapping

### Project and Global Configuration File
You can override hardware-detected defaults using global or local YAML configurations:
- **Global**: `~/.ghostcoder/config.yaml`
- **Per-Project**: `.ghostcoder/config.yml` in your project root.

```yaml
# Override config.yaml example
gpu_tier: workstation
model_coder: deepseek-coder:33b
vram_headroom_mb: 1000
```

### CLI Overrides
Configure settings directly from the terminal. If the background daemon is running, it will be notified and hot-swap its models immediately:
```bash
# Force a mid-range GPU tier profile
ghostcoder config --gpu-tier mid

# Customize the code generation model
ghostcoder config --model-coder deepseek-coder:6.7b

# View active GPU metrics and configuration
ghostcoder status
```
