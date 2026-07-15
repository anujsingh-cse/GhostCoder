import pytest
import asyncio
from ghostcoder.brain import Brain
from ghostcoder.config import Config
from ghostcoder.agents import AgentLoader
from ghostcoder.session import SessionState

class SessionEvent:
    def __init__(self, type, content, context):
        self.type = type
        self.content = content
        self.context = context or {}

class GhostBrain:
    def __init__(self):
        self.config = Config()
        self.agent_loader = AgentLoader()
        self.last_prompt = ""
        self.last_system = ""
        
        class MockModelManager:
            def __init__(self, parent):
                self.parent = parent
            async def generate_coder(self, prompt, system=None):
                self.parent.last_prompt = prompt
                self.parent.last_system = system
                return "mock suggestion"
            async def ensure_classifier_loaded(self):
                pass
                
        self.model_manager = MockModelManager(self)
        self.brain = Brain(self.config, self.agent_loader, self.model_manager)

    def handle(self, event):
        cwd = event.context.get("cwd", "/project")
        session = SessionState(cwd)
        session.git_branch = event.context.get("git_branch", "main")
        
        situation = {
            "error_text": event.content,
            "focused_file": "",
            "file_content": "",
            "timestamp": 0
        }
        
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.brain.generate_suggestion(situation, session))
        finally:
            loop.close()
            
        return {
            "agent": session.active_agents[0] if session.active_agents else "",
            # Combine system prompt (SKILL.md content) and user situation prompt for assertions
            "prompt": (self.last_system or "") + "\n" + (self.last_prompt or "")
        }

def test_agent_prompt_includes_skill_context():
    """Verify that dispatched agents receive full SKILL.md as system prompt"""
    brain = GhostBrain()
    event = SessionEvent(
        type="error",
        content="npm ERR! audit CVE-2024-1234",
        context={"cwd": "/project", "git_branch": "main"}
    )
    
    result = brain.handle(event)
    
    # The prompt sent to the LLM must include the security-engineer's SKILL.md
    assert "security-engineer" in result["agent"]
    assert "threat modeling" in result["prompt"] or "vulnerability" in result["prompt"]
    assert "CVE-2024-1234" in result["prompt"]
