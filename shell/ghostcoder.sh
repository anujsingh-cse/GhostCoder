# Common GhostCoder Shell Logic

GHOSTCODER_SOCK="${HOME}/.ghostcoder/ghostcoder.sock"
GHOSTCODER_PORT=48673

ghostcoder_send() {
    local payload="$1"
    # Send using Python to guarantee cross-platform compatibility without depending on netcat flavors
    python -c "
import socket, sys, json
payload = sys.argv[1].encode('utf-8') + b'\n'
try:
    # Try Unix Domain Socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(r'${GHOSTCODER_SOCK}')
    s.sendall(payload)
    s.close()
except Exception:
    try:
        # Fallback to TCP
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', ${GHOSTCODER_PORT}))
        s.sendall(payload)
        s.close()
    except Exception:
        pass
" "$payload"
}

# Variable to track active suggestion
GHOSTCODER_ACTIVE_SUGGESTION=""
GHOSTCODER_ACTIVE_AGENT=""

ghostcoder_listen_and_print() {
    # Request latest status/suggestions by checking if there's any suggestion back
    # But since daemon broadcasts to active listeners, the terminal can also poll
    # or the daemon will push to clients.
    # To receive pushed suggestions, we can write a background listener or just
    # query the daemon at prompt time. Querying the daemon status/last suggestion
    # at prompt time is very clean, simple, and avoids background job noise in the shell!
    # Let's query the status/last suggestion.
    local res
    res=$(python -c "
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
print(line.strip())
" 2>/dev/null)

    if [ -n "$res" ]; then
        # Check if there is a suggestion
        # In a real shell we want to print inline
        # Let's print suggestions if any
        # But we'll let zsh/bash call this on precmd
        return 0
    fi
}

# Bind keys function
ghostcoder_handle_key() {
    local key="$1"
    if [ "$key" = "g" ]; then
        # Expand
        echo -e "\n\033[36m[GhostCoder] Expanding suggestion:\033[0m"
        # Request full output
        ghostcoder_send '{"type": "action", "action": "expand"}'
    elif [ "$key" = "G" ]; then
        # Apply fix
        echo -e "\n\033[32m[GhostCoder] Applying fix...\033[0m"
        ghostcoder_send '{"type": "action", "action": "apply"}'
    elif [ "$key" = "d" ]; then
        # Dismiss
        echo -e "\n\033[90m[GhostCoder] Suggestion dismissed.\033[0m"
        ghostcoder_send '{"type": "action", "action": "dismiss"}'
    elif [ "$key" = "D" ]; then
        # Dismiss all
        echo -e "\n\033[90m[GhostCoder] Dismissed all.\033[0m"
        ghostcoder_send '{"type": "action", "action": "dismiss_all"}'
    fi
}
