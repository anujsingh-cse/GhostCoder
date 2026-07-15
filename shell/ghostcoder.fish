# Fish Integration for GhostCoder
# Sourced in config.fish

set -l ghostcoder_dir (dirname (status filename))
source "$ghostcoder_dir/ghostcoder.sh"

function ghostcoder_preexec --on-event fish_preexec
    set -l cmd $argv[1]
    set -l payload (printf '{"type": "command_pre", "command": %s, "cwd": %s}' \
        (python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$cmd") \
        (python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$PWD"))
    ghostcoder_send "$payload"
end

function ghostcoder_postexec --on-event fish_postexec
    set -l cmd $argv[1]
    set -l exit_code $argv[2]
    set -l payload (printf '{"type": "command_post", "command": %s, "exit_code": %d, "output": ""}' \
        (python -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$cmd") \
        $exit_code)
    ghostcoder_send "$payload"
end
