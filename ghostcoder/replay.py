import os
import json
import time
import hashlib
import logging
import re
from typing import Dict, Any, List, Optional

class GhostGuardrail:
    """Hard safety boundaries for agent actions with scanning, file inspection, and append-only audits."""
    
    def __init__(self, audit_log_path: str = "~/.ghostcoder/audit.log"):
        self.audit_log_path = os.path.abspath(os.path.expanduser(audit_log_path))
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
        
        # BLOCKED_PATTERNS: regex patterns for destructive actions categorized by risk area
        self.BLOCKED_PATTERNS = {
            "filesystem_destructive": [
                r"\brm\s+-rf\b",
                r"\brm\s+-f\b",
                r"\bRemove-Item\b.*\bRecurse\b",
                r"\brmdir\s+/s\b",
                r"\bdel\s+/f\b"
            ],
            "database_destructive": [
                r"\bDROP\s+DATABASE\b",
                r"\bDROP\s+TABLE\b",
                r"\bTRUNCATE\s+TABLE\b"
            ],
            "network_dangerous": [
                r"\bnetcat\b",
                r"\bcurl\b.*\b\|\s*(?:bash|sh)\b",
                r"\bwget\b.*\b\|\s*(?:bash|sh)\b"
            ],
            "crypto_weak": [
                r"\bmd5\b",
                r"\bsha1\b",
                r"\bDES\b"
            ],
            "secret_exposure": [
                r"\b(?:api_key|password|secret|token)\s*=\s*['\"][a-zA-Z0-9_-]{20,}['\"]"
            ]
        }

    def check_action(self, agent_name: str, action_type: str, 
                     original_code: str, proposed_code: str) -> dict:
        """Determines if a proposed agent action violates any safety policies."""
        violations = self.check_code_pattern(proposed_code)
        
        allowed = True
        reason = "All checks passed."
        severity = "info"
        suggestion = ""
        
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        warning_violations = [v for v in violations if v["severity"] == "warning"]
        
        if critical_violations:
            allowed = False
            severity = "critical"
            reason = f"Blocked critical safety violation(s): {', '.join([v['reason'] for v in critical_violations])}"
            suggestion = "Refactor code to avoid destructive commands or weak cryptography."
        elif warning_violations:
            severity = "warning"
            reason = f"Warning violation(s) detected: {', '.join([v['reason'] for v in warning_violations])}"
            suggestion = "Consider upgrading algorithms or validating inputs."
            
        decision = {
            "agent_name": agent_name,
            "action_type": action_type,
            "allowed": allowed,
            "reason": reason,
            "severity": severity,
            "suggestion": suggestion,
            "agent_override": False,
            "timestamp": time.time()
        }
        
        self.audit_log(decision)
        return decision

    def check_file_operation(self, filepath: str, operation: str) -> dict:
        """Blocks critical system paths and metadata deletion."""
        allowed = True
        reason = "File operation allowed."
        severity = "info"
        
        norm_path = os.path.normpath(filepath).replace("\\", "/")
        is_git = ".git" in norm_path.split("/")
        is_root = norm_path in ["/", "C:/", "C:"]
        is_system = any(p in norm_path.lower() for p in ["windows/system32", "/etc/passwd", "/etc/hosts", "/etc/shadow"])
        
        if (is_root or is_git or is_system) and operation.lower() in ["delete", "remove", "modify"]:
            allowed = False
            severity = "critical"
            reason = f"Blocked attempt to {operation} system or core repository files at {filepath}."
            
        decision = {
            "filepath": filepath,
            "operation": operation,
            "allowed": allowed,
            "reason": reason,
            "severity": severity,
            "timestamp": time.time()
        }
        
        self.audit_log(decision)
        return decision

    def check_code_pattern(self, code: str) -> list:
        """Scans code for known risk patterns and categorizes their severity."""
        violations = []
        if not code:
            return violations
            
        for category, patterns in self.BLOCKED_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    sev = "warning"
                    if category in ["filesystem_destructive", "database_destructive", "secret_exposure"]:
                        sev = "critical"
                    elif category == "crypto_weak":
                        sev = "warning"
                        
                    violations.append({
                        "category": category,
                        "pattern": pattern,
                        "severity": sev,
                        "reason": f"Matches dangerous {category} pattern: {pattern}"
                    })
        return violations

    def audit_log(self, decision: dict):
        """Appends decision logs to an append-only audit trail file."""
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision) + "\n")
        except Exception as e:
            logging.error(f"Failed to append to audit log: {e}")


class SafetyGuardrail:
    """Enforces safety guardrails against destructive or unauthorized agent actions."""
    
    @classmethod
    def check_suggestion(cls, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """Inspects suggestions and blocks them if they attempt unsafe operations."""
        guardrail = GhostGuardrail()
        hint = suggestion.get("hint", "")
        fix = suggestion.get("fix", "")
        combined_text = f"{hint}\n{fix}" if fix else hint
        
        decision = guardrail.check_action(
            agent_name=suggestion.get("agent", "unknown"),
            action_type="suggestion",
            original_code="",
            proposed_code=combined_text
        )
        
        if not decision["allowed"]:
            return {
                "agent": suggestion.get("agent", "safety-guardrail"),
                "hint": f"[BLOCKED BY SAFETY GUARDRAIL] {decision['reason']}",
                "fix": None,
                "blocked": True,
                "reason": decision["reason"]
            }
            
        suggestion["blocked"] = False
        return suggestion


class GhostReplay:
    """Logs session events, executes replays, handles decision explanation, and generates reports."""
    
    def __init__(self, sessions_dir: str = "~/.ghostcoder/sessions"):
        self.sessions_dir = os.path.abspath(os.path.expanduser(sessions_dir))
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.current_session_id: Optional[str] = None
        self.current_session_data: Optional[Dict[str, Any]] = None

    def start_session(self, project: str, branch: str) -> str:
        """Starts a new tracking session."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        rand_hash = hashlib.md5(f"{project}-{branch}-{time.time()}".encode()).hexdigest()[:6]
        session_id = f"{timestamp}-{rand_hash}"
        
        self.current_session_id = session_id
        self.current_session_data = {
            "id": session_id,
            "project": project,
            "branch": branch,
            "start_time": time.time(),
            "end_time": None,
            "events": []
        }
        self.save_session()
        logging.info(f"GhostReplay session started: {session_id}")
        return session_id

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs an event within the active session."""
        if not self.current_session_data:
            # Lazy start if no session active
            self.start_session(os.getcwd(), "unknown")
            
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "data": data
        }
        self.current_session_data["events"].append(event)
        self.save_session()
        logging.info(f"GhostReplay event logged: {event_type}")

    def save_session(self):
        """Saves current session data atomically to disk."""
        if not self.current_session_id or not self.current_session_data:
            return
            
        filepath = os.path.join(self.sessions_dir, f"{self.current_session_id}.json")
        temp_filepath = f"{filepath}.tmp"
        try:
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(self.current_session_data, f, indent=2)
            os.replace(temp_filepath, filepath)
        except Exception as e:
            logging.error(f"Failed to save replay session: {e}")

    def load_session(self, session_id: str) -> Dict[str, Any]:
        """Loads and returns historical session data."""
        filepath = os.path.join(self.sessions_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Session file not found: {filepath}")
            
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def replay_session(self, session_id: str, target_branch: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extracts and filters re-applicable fixes from a past session."""
        session = self.load_session(session_id)
        replay_plan = []
        
        for event in session.get("events", []):
            if event.get("type") == "fix_applied":
                data = event.get("data", {})
                replay_plan.append({
                    "agent": data.get("agent"),
                    "hint": data.get("hint"),
                    "fix": data.get("fix"),
                    "file": data.get("file")
                })
        return replay_plan

    def explain_decision(self, session_id: str, event_index: int) -> str:
        """Returns a human-readable explanation of why a specific routing occurred."""
        session = self.load_session(session_id)
        events = session.get("events", [])
        
        if event_index < 0 or event_index >= len(events):
            return f"Error: Event index {event_index} is out of bounds for session {session_id}."
            
        event = events[event_index]
        event_type = event.get("type", "unknown")
        data = event.get("data", {})
        
        explanation = []
        explanation.append(f"# Explain Decision: Event #{event_index} ({event_type})")
        explanation.append(f"**Session ID**: `{session_id}`")
        explanation.append(f"**Timestamp**: {time.ctime(event.get('timestamp'))}\n")
        
        if event_type == "agent_dispatched":
            explanation.append("## Dispatch Details")
            explanation.append(f"- **Agent Dispatched**: `{data.get('agent')}`")
            explanation.append(f"- **Reasoning/Trigger**: {data.get('trigger_reason', 'N/A')}")
            explanation.append(f"- **Active Model**: `{data.get('model', 'N/A')}`")
        elif event_type == "fix_suggested":
            explanation.append("## Suggestion Details")
            explanation.append(f"- **Agent**: `{data.get('agent')}`")
            explanation.append(f"- **Actionable Hint**: *{data.get('hint')}*")
            explanation.append("- **Generated Code Fix**:")
            explanation.append(f"```python\n{data.get('fix')}\n```")
        elif event_type == "guardrail_blocked":
            explanation.append("## Guardrail Intercepted Action")
            explanation.append(f"- **Agent**: `{data.get('agent')}`")
            explanation.append(f"- **Violation Reason**: `{data.get('reason')}`")
            explanation.append(f"- **Original Hint**: *{data.get('original_hint')}*")
        elif event_type == "skeptic_checked":
            explanation.append("## Skeptic Validation Results")
            explanation.append(f"- **Agent**: `{data.get('agent')}`")
            explanation.append(f"- **Blocked**: `{data.get('blocked', False)}`")
            explanation.append("- **Original Code Fix**:")
            explanation.append(f"```python\n{data.get('original_fix')}\n```")
            explanation.append("- **Skeptic Improved Code Fix**:")
            explanation.append(f"```python\n{data.get('improved_fix')}\n```")
            explanation.append("- **Challenges Detected**:")
            for idx, c in enumerate(data.get("challenges", [])):
                explanation.append(f"  {idx + 1}. **[{c.get('severity', 'info').upper()}]** {c.get('flaw')}")
                explanation.append(f"     *Scenario:* {c.get('scenario')}")
                explanation.append(f"     *Proposed Fix:* {c.get('fix')}")
        else:
            explanation.append(f"General event details:\n```json\n{json.dumps(data, indent=2)}\n```")
            
        return "\n".join(explanation)

    def generate_report(self, period: str = "week") -> Dict[str, Any]:
        """Aggregates local session statistics and accepts/applied rates."""
        now = time.time()
        seconds_limit = 7 * 86400 if period == "week" else 30 * 86400
        
        total_sessions = 0
        total_applied = 0
        total_dismissed = 0
        total_blocked = 0
        agent_counts = {}
        time_saved_sec = 0
        
        for filename in os.listdir(self.sessions_dir):
            if not filename.endswith(".json"):
                continue
                
            try:
                with open(os.path.join(self.sessions_dir, filename), "r", encoding="utf-8") as f:
                    session = json.load(f)
                    
                start_time = session.get("start_time", 0)
                if now - start_time > seconds_limit:
                    continue
                    
                total_sessions += 1
                for event in session.get("events", []):
                    etype = event.get("type")
                    if etype in ["fix_applied", "apply"]:
                        total_applied += 1
                        time_saved_sec += 300
                    elif etype in ["fix_dismissed", "dismiss"]:
                        total_dismissed += 1
                    elif etype == "guardrail_blocked":
                        total_blocked += 1
                        
                    if etype == "agent_dispatched":
                        agent = event.get("data", {}).get("agent", "unknown")
                        agent_counts[agent] = agent_counts.get(agent, 0) + 1
            except Exception:
                pass
                
        return {
            "period": period,
            "sessions_analyzed": total_sessions,
            "applied_fixes": total_applied,
            "dismissed_fixes": total_dismissed,
            "blocked_actions": total_blocked,
            "acceptance_rate": (total_applied / (total_applied + total_dismissed) * 100) if (total_applied + total_dismissed) > 0 else 0.0,
            "estimated_time_saved_mins": int(time_saved_sec / 60),
            "agent_distribution": agent_counts
        }
