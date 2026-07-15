import os
import time
import json
import hashlib
import pathlib
from typing import Dict, List, Any, Optional

class SessionState:
    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self.project_hash = hashlib.md5(self.project_path.encode("utf-8")).hexdigest()[:12]
        self.timestamp = int(time.time())
        self.session_id = f"{self.project_hash}_{self.timestamp}"
        
        # State tracking
        self.commands: List[Dict[str, Any]] = []  # Max 50
        self.errors: List[Dict[str, Any]] = []    # Max 20
        self.open_files: Dict[str, str] = {}      # path -> content_hash
        self.git_branch: str = "unknown"
        self.git_last_commit: str = ""
        self.git_status: str = ""
        self.active_agents: List[str] = []
        self.current_task: str = "Idle"

        self._ensure_session_dir()
        self.load_git_context()

    def _ensure_session_dir(self):
        self.sessions_dir = os.path.expanduser(f"~/.ghostcoder/sessions/{self.project_hash}")
        pathlib.Path(self.sessions_dir).mkdir(parents=True, exist_ok=True)

    def load_git_context(self):
        """Read Git status using subprocess or fallback gracefully."""
        import subprocess
        try:
            # Branch
            branch_proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_path, capture_output=True, text=True, timeout=2
            )
            if branch_proc.returncode == 0:
                self.git_branch = branch_proc.stdout.strip()
            
            # Last commit
            commit_proc = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%h - %s"],
                cwd=self.project_path, capture_output=True, text=True, timeout=2
            )
            if commit_proc.returncode == 0:
                self.git_last_commit = commit_proc.stdout.strip()

            # Status
            status_proc = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.project_path, capture_output=True, text=True, timeout=2
            )
            if status_proc.returncode == 0:
                self.git_status = status_proc.stdout.strip()
        except Exception:
            # Not a git repo or git not installed
            pass

    def add_command(self, cmd: str, exit_code: Optional[int] = None, output: Optional[str] = None):
        self.commands.append({
            "timestamp": time.time(),
            "command": cmd,
            "exit_code": exit_code,
            "output_snippet": output[-500:] if output else None  # limit size
        })
        if len(self.commands) > 50:
            self.commands.pop(0)
        self.save()

    def add_error(self, error_text: str, command: str, resolved: Optional[bool] = None):
        self.errors.append({
            "timestamp": time.time(),
            "error": error_text,
            "command": command,
            "resolved": resolved  # True = user accepted fix, False = dismissed
        })
        if len(self.errors) > 20:
            self.errors.pop(0)
        self.save()

    def update_file_hash(self, filepath: str, content: str):
        abs_path = os.path.abspath(filepath)
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.open_files[abs_path] = h
        self.save()

    def set_active_agents(self, agents: List[str]):
        self.active_agents = agents
        self.save()

    def set_current_task(self, task: str):
        self.current_task = task
        self.save()

    def save(self):
        """Serialize session data to JSON."""
        session_file = os.path.join(self.sessions_dir, f"{self.timestamp}.json")
        data = {
            "project_path": self.project_path,
            "project_hash": self.project_hash,
            "timestamp": self.timestamp,
            "commands": self.commands,
            "errors": self.errors,
            "open_files": self.open_files,
            "git_branch": self.git_branch,
            "git_last_commit": self.git_last_commit,
            "git_status": self.git_status,
            "active_agents": self.active_agents,
            "current_task": self.current_task
        }
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving session state: {e}")
