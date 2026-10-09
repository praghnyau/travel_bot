"""Minimal Gemini REST client; imports remain optional for local/offline use."""
import requests


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-3.6-flash", timeout: int = 30):
        if not api_key:
            raise ValueError("A Gemini API key is required.")
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def generate(self, system_prompt: str, question: str, excerpts: list[str]) -> str:
        context = "\n\n".join(excerpts) if excerpts else "No matching policy excerpts were found."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        response = requests.post(
            url,
            headers={"x-goog-api-key": self.api_key},
            json={"systemInstruction": {"parts": [{"text": system_prompt}]},
                 "contents": [{"parts": [{"text": f"Policy excerpts:\n{context}\n\nEmployee question: {question}"}]}],
                 "generationConfig": {"temperature": 0.1, "maxOutputTokens": 700}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return "".join(p.get("text", "") for p in payload["candidates"][0]["content"]["parts"]).strip()
