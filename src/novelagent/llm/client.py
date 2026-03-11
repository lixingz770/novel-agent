from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from ..config import LLMConfig


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMClient:
    cfg: LLMConfig

    def _base_url(self) -> str:
        base = (self.cfg.base_url or "").strip()
        if not base or base.startswith("${"):
            return ""
        return base.rstrip("/")

    def is_configured(self) -> bool:
        return bool((self._base_url()) and (self.cfg.api_key or "").strip() and (self.cfg.model or "").strip())

    def chat_json(self, *, system: str, user: str, json_schema_hint: Optional[str] = None) -> dict[str, Any]:
        if not self.is_configured():
            raise LLMError("LLM is not configured. Set NOVELAGENT_BASE_URL/NOVELAGENT_API_KEY/NOVELAGENT_MODEL.")

        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
        }
        if json_schema_hint:
            payload["response_format"] = {"type": "json_object"}

        base = self._base_url()
        url = f"{base}/v1/chat/completions" if not base.endswith("/v1") else f"{base}/chat/completions"

        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        timeout = httpx.Timeout(self.cfg.timeout_s)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            raise LLMError(f"Unexpected response format: {data}") from e

        import json  # local import

        def _try_parse(text: str) -> dict[str, Any]:
            obj = json.loads(text)
            if not isinstance(obj, dict):
                raise ValueError("JSON root is not an object")
            return obj

        # 1) strict parse
        try:
            return _try_parse(content)
        except Exception:
            pass

        # 2) best-effort: extract the largest JSON object substring
        start = content.find("{")
        end = content.rfind("}")
        if 0 <= start < end:
            snippet = content[start : end + 1]
            try:
                return _try_parse(snippet)
            except Exception as e:  # noqa: BLE001
                raise LLMError(f"Model did not return valid JSON: {content[:2000]}") from e

        raise LLMError(f"Model did not return valid JSON: {content[:2000]}")

    def chat_text(self, *, system: str, user: str) -> str:
        if not self.is_configured():
            raise LLMError("LLM is not configured. Set NOVELAGENT_BASE_URL/NOVELAGENT_API_KEY/NOVELAGENT_MODEL.")

        payload: dict[str, Any] = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
        }

        base = self._base_url()
        url = f"{base}/v1/chat/completions" if not base.endswith("/v1") else f"{base}/chat/completions"

        headers = {"Authorization": f"Bearer {self.cfg.api_key}"}
        timeout = httpx.Timeout(self.cfg.timeout_s)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:  # noqa: BLE001
            raise LLMError(str(e)) from e

        try:
            return str(data["choices"][0]["message"]["content"])
        except Exception as e:  # noqa: BLE001
            raise LLMError(f"Unexpected response format: {data}") from e

