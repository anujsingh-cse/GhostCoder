# Zsh Integration for GhostCoder
# Sourced in ~/.zshrc

GHOSTCODER_DIR="$(cd "$(dirname "${(%):-%N}")" && pwd)"
source "${GHOSTCODER_DIR}/ghostcoder.sh"

ghostcoder_preexec() {
    local cmd="$1"
    local payload
    payload=$(printf '{"type": "command_pre", "command": %s, "cwd": %s}' \
        "$(python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$cmd")" \
        "$(python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$PWD")")
    ghostcoder_send "$payload"
}

ghostcoder_precmd() {
    local exit_code=$?
    # Send post-command event
    local payload
    payload=$(printf '{"type": "command_post", "command": %s, "exit_code": %d, "output": ""}' \
        "$(python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$history[$((HISTCMD-1))]")" \
        "$exit_code")
    ghostcoder_send "$payload"
}

# Register hooks
autoload -Uz add-zsh-hook
add-zsh-hook preexec ghostcoder_preexec
add-zsh-hook precmd ghostcoder_precmd
