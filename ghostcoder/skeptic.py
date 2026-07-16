import json
import logging
from typing import List, Dict, Any, Optional

class SkepticChallenge:
    def __init__(self, flaw: str, severity: str, scenario: str, fix: str, confidence: float):
        self.flaw = flaw
        self.severity = severity  # "critical", "warning", "info"
        self.scenario = scenario
        self.fix = fix
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flaw": self.flaw,
            "severity": self.severity,
            "scenario": self.scenario,
            "fix": self.fix,
            "confidence": self.confidence
        }

class GhostSkeptic:
    def __init__(self, config=None, model_manager=None):
        self.config = config
        self.model_manager = model_manager
        self.last_improved_fix: Optional[str] = None

    async def challenge(self, original_code: str, suggested_fix: str, context: str) -> List[SkepticChallenge]:
        """Challenge a code suggestion by generating 3 flaws using Qwen2.5-0.5B."""
        self.last_improved_fix = suggested_fix
        
        if not self.config or not self.model_manager:
            return []

        system_prompt = (
            "You are a skeptical senior engineer. Find 3 flaws in this suggestion. "
            "Respond ONLY as a valid JSON object matching the requested schema. Do not output any conversational text or markdown code blocks."
        )
        
        prompt = (
            f"Original Code:\n{original_code}\n\n"
            f"Suggested Fix:\n{suggested_fix}\n\n"
            f"Context/Errors/Info:\n{context}\n\n"
            "Return the flaws as a JSON object with this exact schema:\n"
            "{\n"
            "  \"challenges\": [\n"
            "    {\n"
            "      \"flaw\": \"Description of the flaw/bug/issue\",\n"
            "      \"severity\": \"critical\" | \"warning\" | \"info\",\n"
            "      \"scenario\": \"Under what exact conditions this manifests\",\n"
            "      \"fix\": \"How to address/write the code correctly\",\n"
            "      \"confidence\": 0.95\n"
            "    }\n"
            "  ],\n"
            "  \"improved_fix\": \"A single consolidated correct version of the suggested fix incorporating all fixes\"\n"
            "}"
        )
        
        model = getattr(self.config, "skeptic_model", None) or getattr(self.config, "classifier_model", "qwen2.5:0.5b")
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1
            }
        }
        
        try:
            await self.model_manager.ensure_classifier_loaded()
            res = await self.model_manager.make_request("/api/generate", payload)
            response_text = res.get("response", "").strip()
            if not response_text:
                return []
            
            data = json.loads(response_text)
            challenges_data = data.get("challenges", [])
            self.last_improved_fix = data.get("improved_fix", suggested_fix)
            
            challenges = []
            for item in challenges_data:
                flaw = item.get("flaw", "")
                severity = item.get("severity", "info").lower()
                if severity not in ["critical", "warning", "info"]:
                    severity = "info"
                scenario = item.get("scenario", "")
                fix = item.get("fix", "")
                try:
                    confidence = float(item.get("confidence", 1.0))
                except (ValueError, TypeError):
                    confidence = 1.0
                
                challenges.append(SkepticChallenge(flaw, severity, scenario, fix, confidence))
            
            return challenges
        except Exception as e:
            logging.error(f"GhostSkeptic challenge failed: {e}")
            self.last_improved_fix = suggested_fix
            return []

    def should_block(self, challenges: List[SkepticChallenge]) -> bool:
        """Block suggestions that contain any critical flaws."""
        return any(c.severity == "critical" for c in challenges)

    def format_inline(self, challenges: List[SkepticChallenge]) -> str:
        """Format challenges into a human-readable list."""
        if not challenges:
            return ""
        return ", ".join([f"[{c.severity.upper()}] {c.flaw}" for c in challenges])
