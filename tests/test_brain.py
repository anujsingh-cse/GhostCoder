import pytest
from ghostcoder.brain import Brain
from ghostcoder.config import Config
from ghostcoder.agents import AgentLoader
from ghostcoder.models import ModelManager
from ghostcoder.session import SessionState

class MockConfig:
    def __init__(self):
        self.agent_mappings = {
            "errors": [
                {"pattern": "AssertionError", "agents": ["agency-reality-checker"]},
                {"pattern": "git push rejected", "agents": ["agency-git-workflow-master"]},
                {"pattern": "React", "agents": ["agency-frontend-developer"]}
            ],
            "file_extensions": {
                ".tsx": "agency-frontend-developer",
                ".rs": "agency-senior-developer"
            }
        }
        self.classifier_model = "qwen2.5:0.5b"
        self.coder_model = "qwen2.5-coder:1.5b"
        self.ollama_url = "http://localhost:11434"

def test_brain_routing():
    config = MockConfig()
    # We pass None/dummies for services we won't execute in these unit tests
    brain = Brain(config, None, None)

    # 1. Test error pattern routing
    sit_error = {"error_text": "AssertionError: 1 != 2"}
    routed = brain.route_agent_deterministic(sit_error)
    assert "agency-reality-checker" in routed

    # 2. Test file extension routing
    sit_file = {"focused_file": "src/App.tsx", "file_content": ""}
    routed_file = brain.route_agent_deterministic(sit_file)
    assert "agency-frontend-developer" in routed_file

    # 3. Test python router heuristic overrides
    sit_py_backend = {"focused_file": "src/routes.py", "file_content": "from fastapi import APIRouter"}
    routed_py = brain.route_agent_deterministic(sit_py_backend)
    assert "agency-backend-architect" in routed_py
