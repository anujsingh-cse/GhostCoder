# 🛡️ Ghost Skeptic & Safety Guardrails Guide

GhostCoder implements dual-layer safety validation to prevent incorrect code insertion and protect developers from executing destructive operations.

---

## 🔁 Ghost Skeptic: Adversarial Self-Validation

Every time an engineering specialist agent generates a fix or code block, it is intercepted and evaluated by a separate **Ghost Skeptic** workflow.

```
[Brain Specialist Agent] ──> Proposes Suggested Fix
                                    │
                                    ▼
[Ghost Skeptic Agent]   ──> Evaluates Suggestion against original code and context
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
          [No Flaws Found]                     [Flaws Detected]
                  │                                   │
                  ▼                                   ▼
        Approve suggestion for User            Attempt Auto-Correction
                                               (Max 3 iterations)
                                                      │
                                                      ▼
                                            Inject Warning or Block
```

### Skeptic Evaluation Prompts
The Skeptic runs with a temperature of `0.1` and uses a structured schema to enforce logical consistency:

```json
{
  "challenges": [
    {
      "flaw": "Removes a variable validation check, introducing a Potential NoneType dereference.",
      "severity": "critical",
      "scenario": "When lookup returns null and caller accesses profile properties",
      "fix": "Reintroduce if user is not None check before dereference.",
      "confidence": 0.98
    }
  ],
  "improved_fix": "A corrected code block incorporating the re-added check."
}
```

---

## 🧱 Static Command Guardrails

GhostCoder intercepts and screens terminal commands and proposed code changes against a blocklist of high-risk operational patterns.

### Enforced Rules

1.  **Destructive Operations**: Prohibits any command or patch containing unchecked database drop statements (`DROP DATABASE`, `DROP TABLE` without confirmation).
2.  **Unbounded Deletions**: Flags or blocks recursive file system removal statements containing wildcards or targeting system paths (e.g., `rm -rf /`, `rm -rf *` inside critical workspace directories).
3.  **Command Execution Blocks**: If an inline suggestion contains commands, they are shown in red to the user in the IDE and require manual copy-paste confirmation to execute (they are never run silently).
