import logging
import tiktoken
from config.settings import settings


def setup_logging():
    level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s"
        if settings.debug
        else "%(levelname)s - %(message)s",
    )
    for noisy in ["httpx", "httpcore", "openai", "urllib3", "asyncio"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


class TokenCounter:
    def __init__(self):
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoder = None
        self.total_tokens = 0
        self.calls = []

    def count(self, text: str) -> int:
        if not self.encoder:
            return len(text) // 4
        return len(self.encoder.encode(text))

    def track(self, input_text: str, output_text: str, model: str = "deepseek"):
        input_tokens = self.count(input_text)
        output_tokens = self.count(output_text)
        total = input_tokens + output_tokens

        self.calls.append(
            {
                "model": model,
                "input": input_tokens,
                "output": output_tokens,
                "total": total,
            }
        )
        self.total_tokens += total

        if settings.debug:
            cost = self._estimate_cost(input_tokens, output_tokens, model)
            logging.debug(f"🎫 Tokens: {input_tokens}→{output_tokens} (${cost:.6f})")

        return total

    def _estimate_cost(self, input_t: int, output_t: int, model: str) -> float:
        prices = {
            "deepseek": {"input": 0.14, "output": 0.28},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 5.0, "output": 15.0},
        }
        p = prices.get(model, prices["deepseek"])
        return (input_t * p["input"] + output_t * p["output"]) / 1_000_000

    def get_summary(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "total_calls": len(self.calls),
            "calls": self.calls[-5:] if settings.debug else [],
        }

    def reset(self):
        self.total_tokens = 0
        self.calls = []

token_counter = TokenCounter()
