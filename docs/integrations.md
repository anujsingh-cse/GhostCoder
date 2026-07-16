# 🔌 Shell & Editor Integrations

GhostCoder hooks directly into your shell session and your editor via an asynchronous IPC broker, providing zero-latency assistance as you work.

---

## 🐚 Shell Hook Setup

During initialization (`ghostcoder init`), shell scripts are configured to hook into your prompt lifecycle.

### How it works
The scripts define command hook wrappers (`preexec` and `precmd` equivalents):
- **`command_pre`**: Triggered before a command starts execution. It alerts the daemon to temporarily pause editor file watches or prepare context.
- **`command_post`**: Triggered immediately after a command finishes. It captures:
  - Command exit status code.
  - Errors from `stderr`.
  - Directory stack info.

If a command fails (exit code > 0), the wrapper sends a payload to the daemon over TCP/Unix sockets.

---

## 💤 Neovim Integration

The Neovim plugin hooks into editor events using autocmd rules.

### Installation
Add the following template to your Neovim configurations (`init.lua` or your plugin manager directory):

```lua
-- lazy.nvim Example
{
  "anujsingh-cse/GhostCoder",
  event = { "BufReadPost", "BufNewFile" },
  config = function()
    local gc = require("ghostcoder")
    gc.setup({
      socket_path = "~/.ghostcoder/ghostcoder.sock",
      enable_inline_virtual_text = true,
      highlight_groups = {
        suggestion = "Comment",
        warning = "DiagnosticWarn"
      }
    })
  end
}
```

### Event Listeners
- **CursorHold / CursorMoved**: Periodically reports active file path and cursor line position to the daemon.
- **TextChanged / TextChangedI**: Notifies the daemon of buffer changes, updating hashes used for dynamic context matching.

---

## 💻 VS Code Extension

The VS Code extension exposes inline recommendations utilizing standard `vscode.languages` diagnostics and inline decoration APIs.

### Setup
Ensure the Extension configuration specifies the correct fallback port or IPC domain path:

```json
{
  "ghostcoder.socketPath": "~/.ghostcoder/ghostcoder.sock",
  "ghostcoder.fallbackPort": 48673,
  "ghostcoder.showHintsInline": true
}
```

The extension automatically creates a socket channel client to connect with the local daemon on startup, parsing any returned JSON messages to inject annotations directly.
