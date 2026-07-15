import os
import pathlib
import yaml

DEFAULT_CONFIG = {
    "ollama_url": "http://localhost:11434",
    "socket_path": "~/.ghostcoder/ghostcoder.sock",
    "fallback_port": 48673,
    "use_tcp_fallback": True,
    "vram_headroom_mb": 500,
    "coder_idle_timeout": 30.0,
    "classifier_model": "qwen2.5:0.5b",
    "coder_model": "qwen2.5-coder:1.5b",
    "skeptic": True,
    "gemini_api_key": "",
    "use_gemini_fallback": False,
    "agent_mappings": {
        "errors": [
            {"pattern": "FAILED tests/", "agents": ["agency-reality-checker", "agency-senior-developer"]},
            {"pattern": "AssertionError", "agents": ["agency-reality-checker", "agency-senior-developer"]},
            {"pattern": "npm ERR! audit", "agents": ["agency-application-security-engineer"]},
            {"pattern": "CVE-", "agents": ["agency-application-security-engineer"]},
            {"pattern": "git push rejected", "agents": ["agency-git-workflow-master"]},
            {"pattern": "merge conflict", "agents": ["agency-git-workflow-master"]},
            {"pattern": "CREATE INDEX", "agents": ["agency-database-optimizer"]},
            {"pattern": "slow query", "agents": ["agency-database-optimizer"]},
            {"pattern": "React", "agents": ["agency-frontend-developer"]},
            {"pattern": "useState", "agents": ["agency-frontend-developer"]},
            {"pattern": "API", "agents": ["agency-backend-architect"]},
            {"pattern": "endpoint", "agents": ["agency-backend-architect"]},
            {"pattern": "Docker", "agents": ["agency-devops-automator"]},
            {"pattern": "deploy", "agents": ["agency-devops-automator"]},
            {"pattern": "CI/CD", "agents": ["agency-devops-automator"]}
        ],
        "file_extensions": {
            ".tsx": "agency-frontend-developer",
            ".jsx": "agency-frontend-developer",
            ".vue": "agency-frontend-developer",
            ".rs": "agency-senior-developer",
            ".sol": "agency-solidity-smart-contract-engineer",
            ".tf": "agency-devops-automator",
            ".yaml": "agency-devops-automator",
            ".yml": "agency-devops-automator"
        }
    }
}

class Config:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.expanduser("~/.ghostcoder/config.yaml")
        self.data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        path = pathlib.Path(self.config_path)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    user_data = yaml.safe_load(f)
                    if user_data:
                        self._merge(self.data, user_data)
            except Exception as e:
                print(f"Error loading config file: {e}")
        else:
            # Ensure folder exists
            path.parent.mkdir(parents=True, exist_ok=True)
            self.save()

    def _merge(self, base, update):
        for k, v in update.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._merge(base[k], v)
            else:
                base[k] = v

    def save(self):
        path = pathlib.Path(self.config_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.data, f)
        except Exception as e:
            print(f"Error saving config file: {e}")

    @property
    def ollama_url(self):
        return self.data.get("ollama_url", "http://localhost:11434")

    @property
    def socket_path(self):
        path = self.data.get("socket_path", "~/.ghostcoder/ghostcoder.sock")
        return os.path.abspath(os.path.expanduser(path))

    @property
    def fallback_port(self):
        return self.data.get("fallback_port", 48673)

    @property
    def use_tcp_fallback(self):
        return self.data.get("use_tcp_fallback", True)

    @property
    def vram_headroom_mb(self):
        return self.data.get("vram_headroom_mb", 500)

    @property
    def coder_idle_timeout(self):
        return self.data.get("coder_idle_timeout", 30.0)

    @property
    def classifier_model(self):
        return self.data.get("classifier_model", "qwen2.5:0.5b")

    @property
    def coder_model(self):
        return self.data.get("coder_model", "qwen2.5-coder:1.5b")

    @property
    def skeptic(self):
        return self.data.get("skeptic", True)

    @property
    def gemini_api_key(self):
        return self.data.get("gemini_api_key", "")

    @property
    def use_gemini_fallback(self):
        return self.data.get("use_gemini_fallback", False)

    @property
    def agent_mappings(self):
        return self.data.get("agent_mappings", DEFAULT_CONFIG["agent_mappings"])
