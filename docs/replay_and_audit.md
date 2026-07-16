# 🔁 Replay & Audit Trail Guide

Every event, routing decision, code evaluation, and model response in GhostCoder is tracked in a transparent audit ledger. This allows you to inspect, review, and reproduce any changes.

---

## 💾 The Ledger System

Logs are saved as discrete session transactions in your local folder:
`~/.ghostcoder/sessions/`

Each session file contains sequential events:

```json
{
  "session_id": "20260716-112000",
  "git_branch": "main",
  "project_path": "/users/developer/ghostcoder",
  "events": [
    {
      "timestamp": 1784175600.123,
      "event_type": "command_failed",
      "command": "npm run test",
      "exit_code": 1,
      "stderr": "TypeError: Cannot read properties of undefined (reading 'config')"
    },
    {
      "timestamp": 1784175601.456,
      "event_type": "agent_suggestion_generated",
      "agent": "agency-senior-developer",
      "prompt_hash": "a8e9f2d...",
      "suggestion": "Initialize the config object before parsing...",
      "skeptic_challenges": []
    }
  ]
}
```

---

## 🔍 CLI Audit Commands

Use these CLI utilities to audit and replay past actions.

### 1. Explain Decisions
To query the AI logic behind a specific suggestion:
```bash
ghostcoder explain --session <session_id> --event <event_index>
```
*Outputs: The original code, the exact agent instructions, the stderr traceback, and the reasoning path chosen by the models.*

### 2. Activity Reporting
Generate a summary report of issues encountered, agent routing statistics, and fix success rates:
```bash
# Get a summary of the current week
ghostcoder report --period week

# Get a summary of the current month
ghostcoder report --period month
```

### 3. Session Replay
If you reset your workspace or branch and want to re-apply all code modifications proposed during a session:
```bash
ghostcoder replay --session <session_id>
```
*This parses the transaction log and safely applies all accepted code edits to matching lines in the workspace.*
