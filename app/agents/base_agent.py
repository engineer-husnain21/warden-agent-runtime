from abc import ABC, abstractmethod
from string import Template
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.clients.llm_client import LlmClient
from app.core.exceptions import AgentOutputError
from app.core.prompt_loader import PromptLoader
from app.schemas.llm_message import LlmMessage
from app.schemas.llm_usage import LlmUsage

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)
TReply = TypeVar("TReply", bound=BaseModel)


class BaseAgent(ABC, Generic[TInput, TOutput]):  # noqa: UP046  (template from CLAUDE.md section 6)
    name: str

    def __init__(self, llm_client: LlmClient, prompt_loader: PromptLoader) -> None:
        self._llm_client = llm_client
        self._prompt_loader = prompt_loader

    @abstractmethod
    async def run(self, input: TInput) -> TOutput: ...

    async def _build_messages(self, prompt_prefix: str, **values: str) -> list[LlmMessage]:
        """System prompt from `<prefix>_system.md`, user message from `<prefix>_user.md`
        with `$placeholders` filled in."""
        system = await self._prompt_loader.load(f"{prompt_prefix}_system")
        user_template = await self._prompt_loader.load(f"{prompt_prefix}_user")
        return [
            LlmMessage(role="system", content=system),
            LlmMessage(role="user", content=Template(user_template).substitute(values)),
        ]

    async def _complete_json(
        self, messages: list[LlmMessage], reply_type: type[TReply]
    ) -> tuple[TReply, list[LlmUsage]]:
        """Ask for JSON and validate it into `reply_type`; bad replies raise AgentOutputError."""
        response = await self._llm_client.complete(messages, json_mode=True)
        try:
            reply = reply_type.model_validate_json(_strip_code_fence(response.text))
        except ValidationError as error:
            raise AgentOutputError(
                f"{self.name} returned output that does not match its schema",
                details={"agent": self.name, "error": str(error)[:500]},
            ) from error
        return reply, [response.usage]

    async def _complete_text(self, messages: list[LlmMessage]) -> tuple[str, LlmUsage]:
        response = await self._llm_client.complete(messages)
        return response.text.strip(), response.usage


def _strip_code_fence(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences even in JSON mode."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()
