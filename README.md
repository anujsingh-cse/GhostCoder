# 👻 GhostCoder

**The AI coding partner that doesn't trust itself.**

![Inline hint](docs/detection.png)

[![Tests](https://github.com/anujsingh-cse/GhostCoder/actions/workflows/ci.yml/badge.svg)](https://github.com/anujsingh-cse/GhostCoder/actions)
[![PyPI](https://img.shields.io/pypi/v/ghostcoder)](https://pypi.org/project/ghostcoder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why GhostCoder?

| | Cursor | Copilot | GhostCoder |
|--|--------|---------|------------|
| UI | Sidebar chat | Inline completion | **No UI. Inline hints only** |
| Trust | You trust the AI | You trust the AI | **AI challenges itself** |
| Audit | None | None | **Full replay + explain** |
| Safety | None | None | **Guardrails block dangerous** |
| Cost | $20/mo | $10/mo | **Free, local, MIT** |
| Hardware | Cloud | Cloud | **GTX 1650 4GB** |

## Three Features Nobody Else Has

### 🔍 Inline Hints
Specialist agents watch your code and whisper fixes. No sidebar. No context switching.

When you run a command that fails, or write code with an obvious bug, GhostCoder classifies the error and routes it to the correct specialist agent (e.g., security engineer, database optimizer, frontend developer) to give you a dismissible inline hint.

### 🔁 Ghost Replay
Every decision is recorded, explainable, and replayable. 

If you want to understand why GhostCoder suggested a particular change or see a step-by-step trace of how an error was handled, you can inspect it or run a full replay.

```bash
# Explain what happened in a specific session event
ghostcoder explain --session 20260716-001 --event 0

# Generate a project automation report (weekly/monthly)
ghostcoder report --period week

# Re-apply proposed fixes from a session
ghostcoder replay --session 20260716-001
```

### 🛡️ Ghost Skeptic & Safety Guardrails
GhostCoder is the first coding assistant that validates its own output. 

- **Ghost Skeptic**: Uses an adversarial classifier model to look for logic flaws and security issues (e.g. plaintext credentials) in every suggested fix. If a flaw is detected, it is either corrected or blocked.
- **Safety Guardrail**: Automatically screens proposed code blocks for database-destructive operations (`DROP DATABASE`) or risky directory deletions (`rm -rf`) to keep your workspace safe.

---

## Hardware Compatibility & local LLMs

GhostCoder runs entirely on your local machine. It is designed to work efficiently even on lightweight GPUs (e.g., **NVIDIA GTX 1650 4GB VRAM**):
1. **Qwen2.5-0.5B (1GB VRAM)**: Kept loaded in memory for fast situation classification.
2. **Qwen2.5-Coder-1.5B (2GB VRAM)**: Loaded on-demand for code generation, and automatically unloaded after 30 seconds of idle time.
3. **CPU Fallback**: Gracefully falls back to CPU execution if GPU memory headroom (default 500MB) is exceeded.

---

## Quick Start

### 1. Prerequisites
Install [Ollama](https://ollama.com/) and pull the models:
```bash
ollama pull qwen2.5:0.5b
ollama pull qwen2.5-coder:1.5b
```

### 2. Install GhostCoder
Install the CLI and background daemon:
```bash
pip install ghostcoder
```

### 3. Initialize Integrations
Configure your shell and start the daemon:
```bash
ghostcoder init
```
This automatically appends source lines to your shell configuration (`.bashrc`, `.zshrc`, or `config.fish`) and launches the background daemon.

---

## Editor & IDE Setup

### Neovim
Add the plugin folder to your runtimepath (e.g., using your package manager):
```lua
-- lazy.nvim configuration example
{
  "anujsingh-cse/GhostCoder",
  config = function()
    -- Integration works automatically over the Unix Domain Socket
  end
}
```

### VS Code
1. Open the `vscode` folder in this repository.
2. Package the extension:
   ```bash
   cd vscode
   npm install
   npm run compile
   npx vsce package
   ```
3. Install the generated `.vsix` file in VS Code.

---

## CLI Command Reference

- `ghostcoder start` - Start the background daemon.
- `ghostcoder status` - Show active models, VRAM usage, and active integrations.
- `ghostcoder logs` - Tail background daemon log output.
- `ghostcoder stop` - Stop the daemon gracefully.
- `ghostcoder skeptic --on|--off` - Enable or disable the skeptic validation agent.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
