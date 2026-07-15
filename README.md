# GhostCoder 👻

An invisible coding partner that runs in the background, watches your terminal and IDE sessions, detects when you're stuck, and dispatches the right specialist agent to help without interrupting your flow.

## Core Concept
GhostCoder does **NOT** have a sidebar or chat interface. It observes:
- Terminal session (pre/post-commands, exit codes, stderr/stdout stack traces).
- File system changes (modified files, contents, open buffers).

When it detects errors or complex tasks, it uses local LLMs to classify the situation and selects an appropriate specialist agent from your local Antigravity agency skills to show a concise, inline, dismissible hint.

## Architecture

```
                                  +-----------------------+
                                  |   GhostCoder Daemon   |
                                  |        (Python)       |
                                  +-----------+-----------+
                                              |
                     +------------------------+------------------------+
                     |                        |                        |
             [Unix Domain Socket]     [Unix Domain Socket]     [Unix Domain Socket]
                     |                        |                        |
                     v                        v                        v
          +--------------------+    +--------------------+    +--------------------+
          |   Shell Plugin     |    |   Neovim Plugin    |    | VS Code Extension  |
          |  (Bash/Zsh/Fish)   |    |       (Lua)        |    |    (TypeScript)    |
          +--------------------+    +--------------------+    +--------------------+
```

## Hardware Compatibility & LLMs
GhostCoder is designed to run efficiently on low-end GPUs (e.g., **NVIDIA GTX 1650 4GB VRAM**):
1. **Qwen2.5-0.5B (1GB VRAM)**: Kept loaded in memory for fast command and situation classification.
2. **Qwen2.5-Coder-1.5B (2GB VRAM)**: Loaded on demand for code generation, and automatically unloaded after 30 seconds of idle time.
3. **Fallback**: Auto-falls back to CPU inference (or Gemini API Free Tier) if GPU memory is constrained.

---

## Installation & Setup

1. **Prerequisites**:
   - Install [Ollama](https://ollama.ai/) and start the daemon.
   - Pull the required models:
     ```bash
     ollama pull qwen2.5:0.5b
     ollama pull qwen2.5-coder:1.5b
     ```

2. **Install package**:
   ```bash
   pip install -e .
   ```

3. **Initialize Plugins**:
   ```bash
   ghostcoder init
   ```
   This command detects your shell, registers shell hooks, and starts the daemon.

---

## CLI Usage

- `ghostcoder status` - Show loaded models, VRAM usage, and active integrations.
- `ghostcoder logs` - Tail daemon logs.
- `ghostcoder stop` - Stop the background daemon gracefully.
