import pytest
import shutil
import subprocess
from unittest.mock import MagicMock
from ghostcoder.backends.gpu_tier import GPUTierDetector, MODEL_PRESETS
from ghostcoder.config import Config
from ghostcoder.models import ModelManager

def test_gpu_tier_mapping():
    assert GPUTierDetector.get_tier_by_vram(2.0) == "entry"
    assert GPUTierDetector.get_tier_by_vram(4.0) == "entry"
    assert GPUTierDetector.get_tier_by_vram(8.0) == "mid"
    assert GPUTierDetector.get_tier_by_vram(16.0) == "high"
    assert GPUTierDetector.get_tier_by_vram(24.0) == "workstation"
    assert GPUTierDetector.get_tier_by_vram(80.0) == "datacenter"

def test_gpu_tier_resolution_fallback(monkeypatch):
    # Mock shutil.which to return None (simulating no nvidia-smi)
    monkeypatch.setattr(shutil, "which", lambda cmd: None)
    
    tier_info = GPUTierDetector.detect()
    assert tier_info.tier == "entry"
    assert tier_info.vram_gb == 0.0
    assert "CPU" in tier_info.name

def test_gpu_tier_resolution_nvidia(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/nvidia-smi")
    
    class MockCompletedProcess:
        def __init__(self):
            self.stdout = "NVIDIA RTX 4090, 24576\n"
            self.stderr = ""
            self.returncode = 0
            
    def mock_run(args, **kwargs):
        return MockCompletedProcess()
        
    monkeypatch.setattr(subprocess, "run", mock_run)
    
    tier_info = GPUTierDetector.detect()
    assert tier_info.tier == "workstation"
    assert tier_info.vram_gb == 24.0
    assert tier_info.name == "NVIDIA RTX 4090"
    assert tier_info.max_model_size == 32.0

def test_config_resolution_logic(monkeypatch):
    # Mock detector to return 'high' tier preset
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/nvidia-smi")
    class MockCompletedProcess:
        def __init__(self):
            self.stdout = "NVIDIA RTX 4080, 16384\n"
            
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockCompletedProcess())
    
    config = Config()
    # Should resolve high preset classifier and coder since no overrides exist
    assert config.gpu_tier == "auto"
    assert config.classifier_model == MODEL_PRESETS["high"]["classifier"]
    assert config.coder_model == MODEL_PRESETS["high"]["coder"]
    assert config.reasoner_model == MODEL_PRESETS["high"]["reasoner"]
    assert config.skeptic_model == MODEL_PRESETS["high"]["skeptic"]
    
    # Override tier manually
    config.data["gpu_tier"] = "datacenter"
    assert config.coder_model == MODEL_PRESETS["datacenter"]["coder"]
    
    # Specific model overrides
    config.data["model_coder"] = "custom-coder-model:7b"
    assert config.coder_model == "custom-coder-model:7b"
    
    # Dynamic classifier fallback still works
    assert config.classifier_model == MODEL_PRESETS["datacenter"]["classifier"]

def test_vram_limit_calculation(monkeypatch):
    # Setup known 16GB tier
    monkeypatch.setattr(shutil, "which", lambda cmd: "/usr/bin/nvidia-smi")
    class MockCompletedProcess:
        def __init__(self):
            self.stdout = "NVIDIA RTX 4080, 16384\n"
            
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MockCompletedProcess())
    
    config = Config()
    config.data["vram_headroom_mb"] = 1000
    manager = ModelManager(config)
    
    # Total VRAM is 16384MB. 85% of it is 13926.4MB. 
    # Total - headroom is 15384MB. Max limit should be the minimum: 13926.4MB.
    limit = manager.get_max_vram_limit_mb()
    assert limit == 16384.0 * 0.85

def test_get_model_size_mb(monkeypatch):
    config = Config()
    manager = ModelManager(config)
    
    # Test fallback estimations
    assert asyncio_run(manager.get_model_size_mb("qwen2.5-coder:1.5b")) == 1200.0
    assert asyncio_run(manager.get_model_size_mb("qwen2.5-coder:7b")) == 5000.0
    assert asyncio_run(manager.get_model_size_mb("qwen2.5-coder:32b")) == 20000.0
    assert asyncio_run(manager.get_model_size_mb("custom:72b")) == 45000.0
    assert asyncio_run(manager.get_model_size_mb("unknown")) == 1000.0

def asyncio_run(coro):
    import asyncio
    return asyncio.new_event_loop().run_until_complete(coro)
