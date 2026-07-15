#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  👻 GhostCoder Self-Test Suite"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $1"
        ((PASS++))
    else
        echo -e "${RED}❌ FAIL${NC}: $1"
        ((FAIL++))
    fi
}

warn() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
}

echo "1. Python Environment"
echo "---------------------"
python --version
check "Python available"

pip show ghostcoder >/dev/null 2>&1
check "GhostCoder package installed"

echo ""
echo "2. Ollama & Models"
echo "-------------------"
ollama --version >/dev/null 2>&1
check "Ollama installed"

ollama list | grep -q "qwen2.5:0.5b"
check "Qwen2.5-0.5B model pulled"

ollama list | grep -q "qwen2.5-coder"
check "Qwen2.5-Coder model pulled"

echo ""
echo "3. VRAM Check"
echo "-------------"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
    check "GPU detected"
else
    warn "nvidia-smi not found — CPU-only mode"
fi

echo ""
echo "4. Antigravity Skills"
echo "---------------------"
SKILL_DIR="$HOME/.gemini/antigravity/skills"
if [ -d "$SKILL_DIR" ]; then
    SKILL_COUNT=$(ls -1 "$SKILL_DIR"/agency-* 2>/dev/null | wc -l)
    echo "Found $SKILL_COUNT agency agents"
    if [ "$SKILL_COUNT" -gt 0 ]; then
        check "Agency agents loaded"
    else
        check "Agency agents directory exists but empty"
    fi
else
    check "Agency agents directory missing"
fi

echo ""
echo "5. GhostCoder Daemon"
echo "--------------------"
ghostcoder --version >/dev/null 2>&1
check "GhostCoder CLI works"

# Test daemon start/stop
ghostcoder status >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Starting daemon..."
    ghostcoder start --daemon
    sleep 2
fi

ghostcoder status | grep -q "running"
check "Daemon is running"

echo ""
echo "6. Shell Integration"
echo "--------------------"
if [ -n "$GHOSTCODER_SOCKET" ]; then
    check "Shell hook active (GHOSTCODER_SOCKET set)"
else
    warn "Shell hook not active — run 'source shell/ghostcoder.bash'"
fi

echo ""
echo "7. Editor Plugins"
echo "-----------------"
# Neovim
if [ -d "$HOME/.config/nvim/lua/ghostcoder" ] || [ -d "$HOME/.local/share/nvim/lazy/ghostcoder" ]; then
    check "Neovim plugin installed"
else
    warn "Neovim plugin not found"
fi

# VS Code
if [ -d "$HOME/.vscode/extensions" ]; then
    if ls "$HOME/.vscode/extensions" | grep -q "ghostcoder"; then
        check "VS Code extension installed"
    else
        warn "VS Code extension not found"
    fi
else
    warn "VS Code not detected"
fi

echo ""
echo "8. Functional Test — Error Detection"
echo "-----------------------------------"
# Create a temp project with a deliberate error
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
echo '{"name": "test-project", "dependencies": {"react": "^18.0.0"}}' > package.json
echo "console.log(undefinedVariable)" > index.js

# Trigger ghostcoder analysis
ghostcoder analyze --file index.js --project "$TMPDIR" > /tmp/ghost_test.json 2>&1
check "GhostCoder analyzed file"

if grep -q "error\|undefined\|Variable" /tmp/ghost_test.json; then
    check "Detected undefined variable"
else
    check "Error detection response"
fi

# Cleanup
cd -
rm -rf "$TMPDIR"

echo ""
echo "9. Functional Test — Agent Routing"
echo "----------------------------------"
TMPDIR=$(mktemp -d)
cd "$TMPDIR"
echo "def vulnerable(password):\n    return password == 'admin'" > auth.py

ghostcoder analyze --file auth.py --project "$TMPDIR" > /tmp/ghost_security.json 2>&1
check "Security analysis triggered"

if grep -q "security-engineer\|plaintext\|hash" /tmp/ghost_security.json; then
    check "Routed to security-engineer agent"
else
    check "Agent routing response"
fi

rm -rf "$TMPDIR"

echo ""
echo "10. Session Persistence"
echo "-----------------------"
SESSION_DIR="$HOME/.ghostcoder/sessions"
if [ -d "$SESSION_DIR" ]; then
    SESSION_COUNT=$(ls -1 "$SESSION_DIR" 2>/dev/null | wc -l)
    echo "Found $SESSION_COUNT session files"
    check "Session directory exists"
else
    warn "No sessions yet — run ghostcoder in a real project"
fi

echo ""
echo "=========================================="
echo "  Test Results: $PASS passed, $FAIL failed"
echo "=========================================="

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}All systems operational. GhostCoder is ready.${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Check output above.${NC}"
    exit 1
fi
