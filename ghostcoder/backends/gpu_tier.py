import subprocess
import shutil
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class GPUTier:
    name: str
    vram_gb: float
    tier: str  # "entry" | "mid" | "high" | "workstation" | "datacenter"
    max_model_size: float  # max parameter size in B (billion)

# Recommended model presets for each tier
MODEL_PRESETS: Dict[str, Dict[str, str]] = {
    "entry": {
        "classifier": "qwen2.5:0.5b",
        "coder": "qwen2.5-coder:1.5b",
        "reasoner": "qwen2.5-coder:1.5b",
        "skeptic": "qwen2.5:0.5b"
    },
    "mid": {
        "classifier": "qwen2.5:0.5b",
        "coder": "qwen2.5-coder:7b",
        "reasoner": "qwen2.5:7b",
        "skeptic": "qwen2.5:3b"
    },
    "high": {
        "classifier": "qwen2.5:3b",
        "coder": "qwen2.5-coder:14b",
        "reasoner": "qwen2.5:14b",
        "skeptic": "qwen2.5:7b"
    },
    "workstation": {
        "classifier": "qwen2.5:7b",
        "coder": "qwen2.5-coder:32b",
        "reasoner": "qwen2.5:32b",
        "skeptic": "qwen2.5:14b"
    },
    "datacenter": {
        "classifier": "qwen2.5:14b",
        "coder": "qwen2.5-coder:32b",
        "reasoner": "qwen2.5:72b",
        "skeptic": "qwen2.5:32b"
    }
}

class GPUTierDetector:
    @staticmethod
    def get_tier_by_vram(vram_gb: float) -> str:
        if vram_gb < 6.0:
            return "entry"
        elif vram_gb < 12.0:
            return "mid"
        elif vram_gb < 20.0:
            return "high"
        elif vram_gb < 48.0:
            return "workstation"
        else:
            return "datacenter"

    @staticmethod
    def get_max_model_size_by_tier(tier: str) -> float:
        mapping = {
            "entry": 3.0,
            "mid": 7.0,
            "high": 14.0,
            "workstation": 32.0,
            "datacenter": 72.0
        }
        return mapping.get(tier, 3.0)

    @classmethod
    def detect(cls) -> GPUTier:
        if not shutil.which("nvidia-smi"):
            # Fallback for CPU / non-NVIDIA environments
            return GPUTier(
                name="CPU / Non-NVIDIA GPU",
                vram_gb=0.0,
                tier="entry",
                max_model_size=3.0
            )

        try:
            # Query nvidia-smi for total VRAM (in MiB) and GPU Name
            import sys
            creation_flags = 0x08000000 if sys.platform == "win32" else 0
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=creation_flags
            )
            output = res.stdout.strip()
            if not output:
                raise ValueError("Empty output from nvidia-smi")

            # In case of multi-GPU, take the first one
            first_line = output.splitlines()[0]
            parts = first_line.split(",")
            if len(parts) < 2:
                raise ValueError(f"Unexpected nvidia-smi output format: {first_line}")

            gpu_name = parts[0].strip()
            vram_mib = float(parts[1].strip())
            vram_gb = vram_mib / 1024.0

            tier = cls.get_tier_by_vram(vram_gb)
            max_model_size = cls.get_max_model_size_by_tier(tier)

            return GPUTier(
                name=gpu_name,
                vram_gb=vram_gb,
                tier=tier,
                max_model_size=max_model_size
            )
        except Exception:
            # Graceful degradation on query failure
            return GPUTier(
                name="NVIDIA GPU (Detection Failed)",
                vram_gb=4.0,
                tier="entry",
                max_model_size=3.0
            )
