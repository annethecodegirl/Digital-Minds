"""
runner.py — Sends adversarial prompts to a target model and collects responses.
"""

import anthropic
from dataclasses import dataclass


@dataclass
class ModelResponse:
    prompt_id: str
    prompt_text: str
    category: str
    severity: str
    response_text: str
    model: str


class ModelRunner:
    """Sends prompts to a target LLM and returns its raw responses."""

    def __init__(self, model: str = "claude-haiku-4-5"):
        self.client = anthropic.Anthropic()
        self.model = model

    def run(self, prompt: dict) -> ModelResponse:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt["text"]}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return ModelResponse(
            prompt_id=prompt["id"],
            prompt_text=prompt["text"],
            category=prompt["category"],
            severity=prompt["severity"],
            response_text=text,
            model=self.model,
        )

    def run_all(self, prompts: list[dict]) -> list[ModelResponse]:
        results = []
        for prompt in prompts:
            print(f"    [{prompt['id']}] querying target model...")
            results.append(self.run(prompt))
        return results
