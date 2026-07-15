import os
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Dict, Any, Optional, List, Callable

class ProjectDetector:
    @staticmethod
    def detect_stack(project_path: str) -> Dict[str, Any]:
        stack = {
            "type": "Generic",
            "technologies": [],
            "package_manager": "unknown"
        }
        
        project_path = os.path.abspath(project_path)
        if not os.path.isdir(project_path):
            return stack

        try:
            files = os.listdir(project_path)
        except Exception:
            return stack
        
        # Node/JS/TS Project
        if "package.json" in files:
            stack["type"] = "Node"
            stack["package_manager"] = "npm"
            if "yarn.lock" in files:
                stack["package_manager"] = "yarn"
            elif "pnpm-lock.yaml" in files:
                stack["package_manager"] = "pnpm"
            
            # Read package.json to check for React
            try:
                with open(os.path.join(project_path, "package.json"), "r", encoding="utf-8") as f:
                    import json
                    pkg = json.load(f)
                    deps = pkg.get("dependencies", {})
                    dev_deps = pkg.get("devDependencies", {})
                    all_deps = {**deps, **dev_deps}
                    if "react" in all_deps:
                        stack["technologies"].append("React")
                    if "typescript" in all_deps:
                        stack["technologies"].append("TypeScript")
                    if "next" in all_deps:
                        stack["technologies"].append("Next.js")
            except Exception:
                pass

        # Rust Project
        if "Cargo.toml" in files:
            stack["type"] = "Rust"
            stack["technologies"].append("Cargo")
            if "Cargo.lock" in files:
                stack["package_manager"] = "cargo"

        # Go Project
        if "go.mod" in files:
            stack["type"] = "Go"
            stack["technologies"].append("Go Modules")
            stack["package_manager"] = "go"

        # Python Project
        if "requirements.txt" in files or "pyproject.toml" in files or "Pipfile" in files:
            stack["type"] = "Python"
            if "poetry.lock" in files:
                stack["package_manager"] = "poetry"
            elif "Pipfile.lock" in files:
                stack["package_manager"] = "pipenv"
            else:
                stack["package_manager"] = "pip"
            
            # Read content to check Django/FastAPI
            try:
                content = ""
                if "requirements.txt" in files:
                    with open(os.path.join(project_path, "requirements.txt"), "r", encoding="utf-8") as f:
                        content = f.read()
                elif "pyproject.toml" in files:
                    with open(os.path.join(project_path, "pyproject.toml"), "r", encoding="utf-8") as f:
                        content = f.read()
                
                if "django" in content.lower():
                    stack["technologies"].append("Django")
                if "fastapi" in content.lower():
                    stack["technologies"].append("FastAPI")
                if "flask" in content.lower():
                    stack["technologies"].append("Flask")
            except Exception:
                pass

        # Docker / DevOps
        if "Dockerfile" in files or os.path.exists(os.path.join(project_path, "k8s")):
            stack["technologies"].append("Docker/DevOps")

        # Blockchain
        sol_files = [f for f in files if f.endswith(".sol")]
        if sol_files or os.path.exists(os.path.join(project_path, "contracts")):
            stack["technologies"].append("Solidity")

        return stack


class FileWatcher(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, str], None]):
        super().__init__()
        self.callback = callback

    def on_modified(self, event):
        if event.is_directory:
            return
        # Skip hidden files or logs
        if "/.git/" in event.src_path or "\\.git\\" in event.src_path:
            return
        if "/.ghostcoder/" in event.src_path or "\\.ghostcoder\\" in event.src_path:
            return
        
        try:
            with open(event.src_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.callback(event.src_path, content)
        except Exception:
            pass


class ErrorDetector:
    @staticmethod
    def parse_error(stdout: str) -> Optional[Dict[str, Any]]:
        """Identify compiler and test framework stack trace patterns."""
        if not stdout:
            return None

        # 1. Pytest / Python Errors
        if "traceback (most recent call last)" in stdout.lower() or "failed tests/" in stdout or "assertionerror" in stdout.lower():
            # Extract exception line
            lines = stdout.splitlines()
            err_line = ""
            for line in reversed(lines):
                if ":" in line and not line.startswith(" ") and len(line) > 5:
                    err_line = line
                    break
            return {
                "type": "pytest/python",
                "message": err_line or "Python test assertion failure",
                "raw": stdout[-2000:]  # Last 2000 chars context
            }

        # 2. Cargo / Rust Compiler Errors
        if "error[" in stdout or "error: could not compile" in stdout:
            match = re.search(r"(error\[E\d+\].*?)(?:\n\n|\Z)", stdout, re.DOTALL)
            msg = match.group(1) if match else "Rust compilation error"
            return {
                "type": "rustc",
                "message": msg.strip().split("\n")[0],
                "raw": stdout[-2000:]
            }

        # 3. Jest / NPM test failures
        if "fail" in stdout.lower() and ("expect(" in stdout or "at " in stdout):
            return {
                "type": "jest",
                "message": "JS/TS assertion failure or uncaught error",
                "raw": stdout[-2000:]
            }

        # 4. NPM / Audit errors
        if "npm err!" in stdout.lower() or "cve-" in stdout.lower():
            return {
                "type": "npm",
                "message": "NPM module error or security audit warning",
                "raw": stdout[-1000:]
            }

        # 5. Git failures
        if "git push rejected" in stdout.lower() or "merge conflict" in stdout.lower() or "error: failed to push" in stdout.lower():
            return {
                "type": "git",
                "message": "Git push rejected or merge conflict encountered",
                "raw": stdout[-1000:]
            }

        # 6. SQL/Database errors
        if "create index" in stdout.lower() or "slow query" in stdout.lower() or "postgresql error" in stdout.lower():
            return {
                "type": "sql",
                "message": "Database query performance warning or syntax error",
                "raw": stdout[-1000:]
            }

        return None
