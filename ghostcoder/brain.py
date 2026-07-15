import os
from typing import Dict, Any, Optional, List
from .agents import AgentLoader
from .models import ModelManager
from .session import SessionState

import re

class Brain:
    def __init__(self, config, agent_loader: AgentLoader, model_manager: ModelManager, replay=None):
        self.config = config
        self.agent_loader = agent_loader
        self.model_manager = model_manager
        self.replay = replay

    def route_agent_deterministic(self, situation: Dict[str, Any]) -> List[str]:
        """Route to appropriate agents based on static rules."""
        matched_agents = []
        
        # 1. Error pattern matching
        error_text = situation.get("error_text", "")
        if error_text:
            for rule in self.config.agent_mappings.get("errors", []):
                if rule["pattern"].lower() in error_text.lower():
                    matched_agents.extend(rule["agents"])
            
            # Additional logic
            if "failed tests" in error_text.lower() or "pytest" in error_text.lower() or "jest" in error_text.lower():
                if "agency-reality-checker" not in matched_agents:
                    matched_agents.append("agency-reality-checker")

        # 2. File extension mapping
        focused_file = situation.get("focused_file", "")
        if focused_file and not matched_agents:
            _, ext = os.path.splitext(focused_file)
            ext = ext.lower()
            
            # Specific python rules
            if ext == ".py":
                content = situation.get("file_content", "")
                if "import django" in content or "from fastapi" in content or "import flask" in content:
                    matched_agents.append("agency-backend-architect")
                elif "spark" in content or "pandas" in content or "pipeline" in content:
                    matched_agents.append("agency-data-engineer")
                else:
                    matched_agents.append("agency-senior-developer")
            else:
                mapping = self.config.agent_mappings.get("file_extensions", {})
                if ext in mapping:
                    matched_agents.append(mapping[ext])
        
        # Unique list
        return list(dict.fromkeys(matched_agents))

    async def classify_situation(self, situation_desc: str) -> str:
        """Use Qwen2.5-0.5B to classify the situation and select the best agent."""
        available = self.agent_loader.list_available_agents()
        if not available:
            return "agency-senior-developer" # Default fallback
        
        system_prompt = (
            "You are a routing system. Based on the developer's problem, you must output EXACTLY "
            "one agent name from the list of available agents. Output ONLY the agent name, nothing else."
        )
        
        available_str = "\n".join([f"- {name}: {desc}" for name, desc in available.items()])
        
        user_prompt = (
            f"Available Agents:\n{available_str}\n\n"
            f"Developer Situation:\n{situation_desc}\n\n"
            "Selected Agent (output ONLY the name):"
        )
        
        response = await self.model_manager.generate_classifier(user_prompt, system=system_prompt)
        response = response.strip()
        
        # Clean response if LLM added formatting/backticks
        response = response.replace("`", "").strip()
        
        # Check if response is in available
        if response in available:
            return response
            
        # Try substring match
        for name in available:
            if name in response or response in name:
                return name
                
        return "agency-senior-developer"

    async def generate_suggestion(self, situation: Dict[str, Any], session: SessionState) -> Optional[Dict[str, Any]]:
        """Orchestrate classification, agent selection, prompt building, and suggestion generation."""
        # 1. Determine agent team
        agents = self.route_agent_deterministic(situation)
        
        if not agents:
            # Fallback to classifier LLM
            situation_desc = (
                f"Command error: {situation.get('error_text', 'None')}\n"
                f"Recent commands: {[c.get('command') for c in session.commands[-3:]]}\n"
                f"Focused file: {situation.get('focused_file', 'None')}\n"
                f"Tech stack: {session.git_branch} branch"
            )
            classified = await self.classify_situation(situation_desc)
            agents = [classified]
        
        session.set_active_agents(agents)
        if not agents:
            agents = ["agency-senior-developer"]

        # Pick primary agent
        primary_agent_name = agents[0]
        
        if self.replay:
            self.replay.log_event("agent_dispatched", {
                "agent": primary_agent_name,
                "trigger_reason": f"Active error or file extension routing for {situation.get('focused_file')}",
                "model": self.config.classifier_model
            })

        agent_data = self.agent_loader.get_agent(primary_agent_name)
        
        if not agent_data:
            # Fallback to basic developer prompt
            system_prompt = (
                "You are an expert software developer pair programming with the user. "
                "Provide ONE concise suggestion (max 2 sentences) and include code if relevant."
            )
        else:
            system_prompt = agent_data["system_prompt"]

        # 2. Build situation context
        error_text = situation.get("error_text", "")
        file_path = situation.get("focused_file", "")
        file_content = situation.get("file_content", "")
        
        recent_cmds_str = "\n".join([
            f"$ {c['command']} (Exit: {c.get('exit_code')})"
            for c in session.commands[-5:]
        ])
        
        situation_prompt = (
            f"--- SITUATION ENVIRONMENT ---\n"
            f"Project Path: {session.project_path}\n"
            f"Git Branch: {session.git_branch}\n"
            f"Git Status:\n{session.git_status}\n\n"
            f"Recent Terminal Commands:\n{recent_cmds_str}\n\n"
        )
        
        if error_text:
            situation_prompt += f"Active Error Encountered:\n{error_text}\n\n"
            
        if file_path:
            situation_prompt += (
                f"Current File Focused: {os.path.basename(file_path)}\n"
                f"File Path: {file_path}\n"
                f"File Content Context:\n```\n{file_content[:1500]}\n```\n\n"
            )
            
        situation_prompt += (
            "--- INSTRUCTIONS ---\n"
            "Review the situation above. Based on your role, provide a highly actionable, "
            "one-line or two-line correction or hint. Make it short and punchy. "
            "If code is required to fix it, show a concise diff/snippet. "
            "Remember: NO sidebar conversations, be brief."
        )

        # 3. Generate suggestion
        try:
            raw_suggestion = await self.model_manager.generate_coder(situation_prompt, system=system_prompt)
            if raw_suggestion:
                # Attempt to extract code block if present
                code_match = re.search(r"```(?:\w+)?\n(.*?)```", raw_suggestion, re.DOTALL)
                fix_code = code_match.group(1).strip() if code_match else None
                
                if self.replay:
                    self.replay.log_event("fix_suggested", {
                        "agent": primary_agent_name,
                        "hint": raw_suggestion.split("\n")[0],
                        "fix": fix_code,
                        "file": situation.get("focused_file")
                    })
                
                return {
                    "agent": primary_agent_name,
                    "hint": raw_suggestion,
                    "fix": fix_code,
                    "timestamp": situation.get("timestamp", session.timestamp)
                }
        except Exception as e:
            print(f"Error in brain suggestion generation: {e}")
            
        return None
            
        return None
