# GhostCoder Testing Script
# Open this file in VS Code with the GhostCoder extension enabled.

# Test Case 1: Vulnerable Plaintext Password Verification
# Placing your cursor or editing this block will trigger the Application Security Engineer agent.
# Action: Hover over the suggestion and click "[⚡ Apply Fix]" or hit Ctrl+. to apply the fix.
def login(password):
    if password == 'admin':
        return True
    return False


# Test Case 2: ReferenceError / Undefined Variable
# Placing your cursor or editing this line will trigger the Reality Checker agent.
# Action: Click "[⚡ Apply Fix]" on hover or select the lightbulb quick fix action.
def check_status():
    print(undefinedVariable)


# Test Case 3: Terminal Command Failure Execution
# Run this file in your terminal: `python test_ghostcoder.py`
# This will raise a NameError, and the shell hook will capture the stderr trace,
# classify the compiler crash, and dispatch the Senior Developer agent to output a fix in the IDE.
if __name__ == "__main__":
    check_status()
