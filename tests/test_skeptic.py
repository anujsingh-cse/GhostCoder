import pytest
import json
import asyncio
from ghostcoder.skeptic import GhostSkeptic, SkepticChallenge

class MockConfig:
    def __init__(self):
        self.classifier_model = "qwen2.5:0.5b"
        self.skeptic = True

class MockModelManager:
    def __init__(self, response_data):
        self.response_data = response_data
        self.ensure_loaded_called = False
        self.requests_made = []

    async def ensure_classifier_loaded(self):
        self.ensure_loaded_called = True

    async def make_request(self, endpoint, data):
        self.requests_made.append((endpoint, data))
        return {"response": self.response_data}

@pytest.mark.asyncio
async def test_catches_logic_error():
    # Mock returns a critical logic flaw
    response_json = {
        "challenges": [
            {
                "flaw": "Off-by-one error in loop boundary",
                "severity": "critical",
                "scenario": "When parsing an empty array or array with length 1",
                "fix": "Use range(len(arr)) instead of range(len(arr) + 1)",
                "confidence": 0.95
            }
        ],
        "improved_fix": "for i in range(len(arr)):\n    print(arr[i])"
    }
    
    config = MockConfig()
    manager = MockModelManager(json.dumps(response_json))
    skeptic = GhostSkeptic(config, manager)
    
    original = "for i in range(len(arr) + 1):\n    print(arr[i])"
    suggested = "for i in range(len(arr) + 1):\n    print(arr[i])"
    
    challenges = await skeptic.challenge(original, suggested, "logic error index error")
    
    assert manager.ensure_loaded_called is True
    assert len(challenges) == 1
    assert challenges[0].flaw == "Off-by-one error in loop boundary"
    assert challenges[0].severity == "critical"
    assert skeptic.should_block(challenges) is True
    assert skeptic.last_improved_fix == response_json["improved_fix"]

@pytest.mark.asyncio
async def test_catches_security_issue():
    # Mock returns a warning/critical security flaw
    response_json = {
        "challenges": [
            {
                "flaw": "Plaintext comparison of passwords",
                "severity": "critical",
                "scenario": "When a malicious actor inspects the db or inputs plain credentials",
                "fix": "Use bcrypt.checkpw",
                "confidence": 0.99
            }
        ],
        "improved_fix": "return bcrypt.checkpw(password, hashed)"
    }
    
    config = MockConfig()
    manager = MockModelManager(json.dumps(response_json))
    skeptic = GhostSkeptic(config, manager)
    
    original = "return password == 'admin'"
    suggested = "return password == 'admin'"
    
    challenges = await skeptic.challenge(original, suggested, "plaintext credential verification")
    
    assert len(challenges) == 1
    assert challenges[0].severity == "critical"
    assert skeptic.should_block(challenges) is True

@pytest.mark.asyncio
async def test_catches_downstream_breakage():
    # Mock returns a warning downstream breakage
    response_json = {
        "challenges": [
            {
                "flaw": "Removes log_event function which is used by downstream components",
                "severity": "warning",
                "scenario": "When daemon.py tries to call log_event",
                "fix": "Retain log_event signature",
                "confidence": 0.85
            }
        ],
        "improved_fix": "def log_event(name, data):\n    pass"
    }
    
    config = MockConfig()
    manager = MockModelManager(json.dumps(response_json))
    skeptic = GhostSkeptic(config, manager)
    
    original = "def log_event(name, data):\n    pass"
    suggested = "def log(name):\n    pass"
    
    challenges = await skeptic.challenge(original, suggested, "refactoring method signatures")
    
    assert len(challenges) == 1
    assert challenges[0].severity == "warning"
    assert skeptic.should_block(challenges) is False

@pytest.mark.asyncio
async def test_blocks_critical():
    skeptic = GhostSkeptic()
    critical_challenge = SkepticChallenge("Flaw 1", "critical", "Scenario", "Fix", 0.9)
    warning_challenge = SkepticChallenge("Flaw 2", "warning", "Scenario", "Fix", 0.9)
    
    assert skeptic.should_block([critical_challenge, warning_challenge]) is True
    assert skeptic.should_block([warning_challenge]) is False

@pytest.mark.asyncio
async def test_passes_clean_suggestion():
    # Mock returns no challenges
    response_json = {
        "challenges": [],
        "improved_fix": "def safe_func():\n    pass"
    }
    
    config = MockConfig()
    manager = MockModelManager(json.dumps(response_json))
    skeptic = GhostSkeptic(config, manager)
    
    challenges = await skeptic.challenge("def safe_func():\n    pass", "def safe_func():\n    pass", "clean suggestion")
    
    assert len(challenges) == 0
    assert skeptic.should_block(challenges) is False
    assert skeptic.last_improved_fix == "def safe_func():\n    pass"
