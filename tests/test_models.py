import pytest
import asyncio
from ghostcoder.models import ModelManager

class MockConfig:
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.classifier_model = "qwen2.5:0.5b"
        self.coder_model = "qwen2.5-coder:1.5b"
        self.vram_headroom_mb = 500
        self.coder_idle_timeout = 0.5  # Short timeout for testing
        self.idle_check_interval = 0.1

class MockResponse:
    def __init__(self, data):
        self.data = data
    def read(self):
        return self.data.encode('utf-8')

@pytest.mark.asyncio
async def test_vram_and_loading_mock(monkeypatch):
    config = MockConfig()
    manager = ModelManager(config)

    requests_made = []

    # Mock the HTTP call
    async def mock_make_request(endpoint, data):
        requests_made.append((endpoint, data))
        if endpoint == "/api/ps":
            return {"models": [{"name": "qwen2.5:0.5b", "size_vram": 1000 * 1024 * 1024}]}
        return {"response": "mock_response"}

    monkeypatch.setattr(manager, "make_request", mock_make_request)

    # 1. Ensure preloading classifier works
    await manager.ensure_classifier_loaded()
    assert len(requests_made) == 1
    assert requests_made[0][1]["model"] == config.classifier_model

    # 2. Test loading coder model
    await manager.load_coder_model()
    assert manager.coder_loaded is True
    assert any(req[1].get("model") == config.coder_model for req in requests_made)

    # 3. Wait for idle timeout and verify it unloads
    await asyncio.sleep(1.0)
    assert manager.coder_loaded is False
    assert any(req[1].get("model") == config.coder_model and req[1].get("keep_alive") == 0 for req in requests_made)
