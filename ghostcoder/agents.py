import os
import yaml
import pathlib
from typing import Dict, Any, Optional

class AgentLoader:
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.load_all_agents()

    def load_all_agents(self):
        # We search in ~/.gemini/config/skills/ and ~/.gemini/antigravity/skills/
        search_dirs = [
            os.path.expanduser("~/.gemini/config/skills"),
            os.path.expanduser("~/.gemini/antigravity/skills")
        ]
        
        for base_dir in search_dirs:
            if not os.path.isdir(base_dir):
                continue
            
            p = pathlib.Path(base_dir)
            for skill_dir in p.iterdir():
                if skill_dir.is_dir() and skill_dir.name.startswith("agency-"):
                    skill_md_path = skill_dir / "SKILL.md"
                    if skill_md_path.exists():
                        self.parse_skill_file(skill_dir.name, skill_md_path)

    def parse_skill_file(self, folder_name: str, file_path: pathlib.Path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Parse YAML frontmatter
            # Example format:
            # ---
            # name: agency-software-architect
            # description: ...
            # ---
            # Body...
            parts = content.split("---")
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                body_str = "---".join(parts[2:])
                
                try:
                    metadata = yaml.safe_load(frontmatter_str)
                except Exception:
                    metadata = {}
                
                name = metadata.get("name", folder_name)
                description = metadata.get("description", "")
                
                self.agents[name] = {
                    "name": name,
                    "description": description,
                    "system_prompt": body_str.strip(),
                    "folder_name": folder_name,
                    "path": str(file_path)
                }
        except Exception as e:
            print(f"Error parsing skill file {file_path}: {e}")

    def get_agent(self, name: str) -> Optional[Dict[str, Any]]:
        # Match by name or folder name (e.g. "agency-reality-checker")
        if name in self.agents:
            return self.agents[name]
        
        # Try match by suffix
        for k, v in self.agents.items():
            if k.endswith(name) or v["folder_name"] == name:
                return v
        return None

    def list_available_agents(self) -> Dict[str, str]:
        return {name: info["description"] for name, info in self.agents.items()}
