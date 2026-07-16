import json
import time
import urllib.request
import urllib.error
import asyncio
from typing import Dict, List, Any, Optional

class ModelManager:
    def __init__(self, config):
        self.config = config
        self.last_coder_used_time = 0.0
        self.coder_loaded = False
        self.unload_timer_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

    async def make_request(self, endpoint: str, data: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """Make an async JSON request to Ollama API."""
        url = f"{self.config.ollama_url.rstrip('/')}{endpoint}"
        payload = json.dumps(data).encode("utf-8") if data else None
        
        def _request():
            headers = {"Content-Type": "application/json"} if payload else {}
            req = urllib.request.Request(
                url,
                data=payload,
                headers=headers,
                method=method
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.URLError as e:
                # Attempt GET for endpoints that are GET or handle errors
                if endpoint in ["/api/ps", "/api/tags"]:
                    try:
                        req_get = urllib.request.Request(url, method="GET")
                        with urllib.request.urlopen(req_get, timeout=5) as res:
                            return json.loads(res.read().decode("utf-8"))
                    except Exception:
                        pass
                raise e

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _request)

    async def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get models currently loaded in Ollama VRAM/RAM."""
        try:
            res = await self.make_request("/api/ps", {})
            return res.get("models", [])
        except Exception as e:
            # If Ollama doesn't support /api/ps or is offline
            return []

    async def get_local_models(self) -> List[Dict[str, Any]]:
        """Get models currently pulled/available locally in Ollama."""
        try:
            res = await self.make_request("/api/tags", {}, method="GET")
            return res.get("models", [])
        except Exception:
            return []

    async def get_model_size_mb(self, model_name: str) -> float:
        """Estimate or retrieve model memory size in MB."""
        try:
            local_models = await self.get_local_models()
            for m in local_models:
                name = m.get("name", "")
                if name == model_name or name.startswith(model_name + ":") or model_name.startswith(name + ":"):
                    # size is in bytes
                    return m.get("size", 0) / (1024.0 * 1024.0)
        except Exception:
            pass

        # Fallbacks for heuristics
        if "72b" in model_name:
            return 45000.0
        elif "32b" in model_name:
            return 20000.0
        elif "14b" in model_name:
            return 9000.0
        elif "7b" in model_name:
            return 5000.0
        elif "3b" in model_name:
            return 2500.0
        elif "1.5b" in model_name:
            return 1200.0
        return 1000.0

    def get_max_vram_limit_mb(self) -> float:
        """Calculate maximum VRAM limit (85% default or total - headroom)."""
        from .backends.gpu_tier import GPUTierDetector
        gpu_info = GPUTierDetector.detect()
        if gpu_info.vram_gb == 0.0:
            return 4096.0 - self.config.vram_headroom_mb
        total_vram_mb = gpu_info.vram_gb * 1024.0
        return min(total_vram_mb * 0.85, total_vram_mb - self.config.vram_headroom_mb)

    async def get_vram_usage_mb(self) -> float:
        """Calculate currently consumed VRAM by Ollama in MB."""
        models = await self.get_loaded_models()
        total_vram = 0.0
        for m in models:
            # size_vram is in bytes usually
            vram_bytes = m.get("size_vram", 0)
            total_vram += vram_bytes / (1024 * 1024)
        return total_vram

    async def ensure_classifier_loaded(self):
        """Ensure the lightweight classifier model is loaded."""
        model = self.config.classifier_model
        try:
            await self.make_request("/api/generate", {
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": -1
            })
        except Exception as e:
            print(f"Warning: Failed to pre-load classifier model: {e}")

    async def load_coder_model(self):
        """Load the code generation model, checking VRAM budget first."""
        async with self.lock:
            max_vram = self.get_max_vram_limit_mb()
            current_vram = await self.get_vram_usage_mb()
            
            coder_model = self.config.coder_model
            model_size = await self.get_model_size_mb(coder_model)
            
            # If loading Coder will exceed max VRAM, we should unload others
            if current_vram + model_size > max_vram:
                print(f"VRAM budget tight (current: {current_vram:.1f}MB, model: {model_size:.1f}MB, limit: {max_vram:.1f}MB). Unloading active models to make room.")
                loaded = await self.get_loaded_models()
                for m in loaded:
                    name = m.get("name", "")
                    if name and coder_model not in name:
                        try:
                            await self.make_request("/api/generate", {
                                "model": name,
                                "prompt": "",
                                "stream": False,
                                "keep_alive": 0
                            })
                        except Exception:
                            pass
            
            # Load Coder model
            try:
                await self.make_request("/api/generate", {
                    "model": coder_model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": "5m"  # Keep alive for 5 minutes (will be unloaded by our idle manager)
                })
                self.coder_loaded = True
                self.last_coder_used_time = time.time()
                self._schedule_unload()
            except Exception as e:
                print(f"Error loading coder model: {e}")
                raise e

    def _schedule_unload(self):
        if self.unload_timer_task and not self.unload_timer_task.done():
            self.unload_timer_task.cancel()
        
        self.unload_timer_task = asyncio.create_task(self._unload_coder_after_idle())

    async def _unload_coder_after_idle(self):
        while True:
            check_interval = getattr(self.config, "idle_check_interval", 5.0)
            await asyncio.sleep(check_interval)
            idle_time = time.time() - self.last_coder_used_time
            if idle_time >= self.config.coder_idle_timeout:
                async with self.lock:
                    if self.coder_loaded:
                        print(f"Coder model idle for {idle_time:.1f}s. Unloading to free VRAM.")
                        try:
                            await self.make_request("/api/generate", {
                                "model": self.config.coder_model,
                                "prompt": "",
                                "stream": False,
                                "keep_alive": 0
                            })
                            self.coder_loaded = False
                        except Exception as e:
                            print(f"Error unloading coder model: {e}")
                break

    async def generate_classifier(self, prompt: str, system: Optional[str] = None) -> str:
        """Run classification on Qwen2.5-0.5B."""
        payload = {
            "model": self.config.classifier_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0}  # Deterministic
        }
        if system:
            payload["system"] = system
        
        try:
            res = await self.make_request("/api/generate", payload)
            return res.get("response", "").strip()
        except Exception as e:
            print(f"Classifier error: {e}. Falling back to basic local rules.")
            return ""

    async def generate_coder(self, prompt: str, system: Optional[str] = None) -> str:
        """Run code generation on Qwen2.5-Coder-1.5B (with VRAM budget check and fallbacks)."""
        # Update last used timestamp to prevent unloading during/immediately after
        self.last_coder_used_time = time.time()
        
        # Ensure model is loaded
        if not self.coder_loaded:
            try:
                await self.load_coder_model()
            except Exception:
                if self.config.use_gemini_fallback and self.config.gemini_api_key:
                    print("Ollama failed. Falling back to Gemini API.")
                    return await self.generate_gemini(prompt, system)
                else:
                    print("Ollama failed. Falling back to CPU/Direct text execution.")
                    # Try generation anyway, Ollama will auto-fallback to CPU
        
        self.last_coder_used_time = time.time()
        self._schedule_unload()

        payload = {
            "model": self.config.coder_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        if system:
            payload["system"] = system

        try:
            res = await self.make_request("/api/generate", payload)
            return res.get("response", "").strip()
        except Exception as e:
            print(f"Coder model generation error: {e}")
            if self.config.use_gemini_fallback and self.config.gemini_api_key:
                print("Falling back to Gemini API.")
                return await self.generate_gemini(prompt, system)
            raise e

    async def generate_gemini(self, prompt: str, system: Optional[str] = None) -> str:
        """Fallback to Gemini API (free tier) for complex reasoning or memory overflow."""
        api_key = self.config.gemini_api_key
        if not api_key:
            return "Error: Gemini API fallback requested but gemini_api_key is empty."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        # Build contents object
        contents = []
        if system:
            # Gemini supports system instruction
            contents.append({"role": "user", "parts": [{"text": f"System Instruction: {system}\n\nUser Request:\n{prompt}"}]})
        else:
            contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 256
            }
        }
        
        def _request():
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                    return "No suggestion from Gemini fallback."
            except Exception as e:
                return f"Gemini Fallback Error: {e}"

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _request)
