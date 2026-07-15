import json
from typing import Dict, Any

class SuggestionRenderer:
    @staticmethod
    def to_ansi(suggestion: Dict[str, Any]) -> str:
        """Format the suggestion using ANSI escape sequences for faded italics."""
        agent = suggestion.get("agent", "GhostCoder")
        hint = suggestion.get("hint", "")
        
        # Color codes
        # 90m = Bright Black (gray)
        # 3m = Italic
        # 0m = Reset
        # 36m = Cyan (for agent name)
        gray_start = "\033[90m\033[3m"
        cyan_start = "\033[36m"
        reset = "\033[0m"
        
        lines = hint.splitlines()
        formatted_hint = f"\n{cyan_start}[{agent}]{reset} {gray_start}{lines[0]}{reset}"
        if len(lines) > 1:
            for line in lines[1:]:
                formatted_hint += f"\n  {gray_start}{line}{reset}"
                
        # Append interactive hotkeys guide
        formatted_hint += f"\n  {gray_start}(g: expand, G: fix, d: dismiss, D: dismiss all){reset}"
        return formatted_hint

    @staticmethod
    def to_json(suggestion: Dict[str, Any]) -> str:
        """Format the suggestion as JSON line for editor IPC."""
        return json.dumps({
            "type": "suggestion",
            "agent": suggestion.get("agent", "GhostCoder"),
            "hint": suggestion.get("hint", ""),
            "timestamp": suggestion.get("timestamp", 0)
        })
