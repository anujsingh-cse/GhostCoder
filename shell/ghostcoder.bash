# Bash Integration for GhostCoder
# Sourced in ~/.bashrc

GHOSTCODER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${GHOSTCODER_DIR}/ghostcoder.sh"

GHOSTCODER_LAST_CMD=""
GHOSTCODER_IN_CMD=0
GHOSTCODER_INSIDE_HOOK=0

ghostcoder_preexec() {
    [ -n "$COMP_LINE" ] && return  # Skip autocomplete runs
    [ "$GHOSTCODER_INSIDE_HOOK" -eq 1 ] && return
    GHOSTCODER_INSIDE_HOOK=1
    
    GHOSTCODER_LAST_CMD="$1"
    GHOSTCODER_IN_CMD=1
    
    # Send pre-command event
    local payload
    payload=$(printf '{"type": "command_pre", "command": %s, "cwd": %s}' \
        "$(python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$GHOSTCODER_LAST_CMD")" \
        "$(python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$PWD")")
    ghostcoder_send "$payload"
    
    GHOSTCODER_INSIDE_HOOK=0
}

ghostcoder_precmd() {
    local exit_code=$?
    [ "$GHOSTCODER_INSIDE_HOOK" -eq 1 ] && return
    GHOSTCODER_INSIDE_HOOK=1
    
    if [ "$GHOSTCODER_IN_CMD" -eq 1 ]; then
        GHOSTCODER_IN_CMD=0
        
        # Capture output context if possible (e.g., from history or quick stdout log)
        # For simplicity and reliability, we send command and exit code,
        # and let the daemon inspect the workspace modifications or test output caches.
        local payload
        payload=$(printf '{"type": "command_post", "command": %s, "exit_code": %d, "output": ""}' \
            "$(python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$GHOSTCODER_LAST_CMD")" \
            "$exit_code")
        ghostcoder_send "$payload"
        
        # Display inline suggestion if one is active
        ghostcoder_show_hint
    fi
    
    GHOSTCODER_INSIDE_HOOK=0
}

ghostcoder_show_hint() {
    # Fetch active suggestion from daemon
    local suggestion
    suggestion=$(python -c "
import socket, sys, json
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(r'${GHOSTCODER_SOCK}')
except Exception:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', ${GHOSTCODER_PORT}))
    except Exception:
        sys.exit(0)

s.sendall(json.dumps({'type': 'status_request'}).encode('utf-8') + b'\n')
f = s.makefile('r')
line = f.readline()
s.close()
data = json.loads(line.strip())
# Extract last error/suggestion
# In status_request we returned loaded info, let's see if there is any pending hint
# If we have a pending suggestion, print it!
" 2>/dev/null)
}

# Trap to capture command execution before it runs
trap 'ghostcoder_preexec "$BASH_COMMAND"' DEBUG

# Prompt command runs before rendering next prompt
PROMPT_COMMAND="ghostcoder_precmd; $PROMPT_COMMAND"
