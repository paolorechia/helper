"""Minimal chat-history model that serializes to the OpenAI messages format."""

from dataclasses import dataclass, field
from enum import StrEnum


class OpenAIRole(StrEnum):
    """Roles accepted by the OpenAI chat-completions schema."""

    user = "user"
    assistant = "assistant"
    system = "system"


@dataclass
class OpenAIMessage:
    """A single chat message with an OpenAI role and text content."""

    role: OpenAIRole
    content: str

    def as_dict(self):
        """Serialize to the `{"role": ..., "content": ...}` wire format."""
        return {"role": self.role.value, "content": self.content}


@dataclass
class Chat:
    """Ordered chat history for the session."""

    messages: list[OpenAIMessage] = field(default_factory=list)

    def add_system_instruction(self, text: str):
        """Append a system-prompt message."""
        print(f"Adding system instruction: {text}")
        self.messages.append(OpenAIMessage(role=OpenAIRole.system, content=text))

    def add_user_message(self, text: str):
        """Append a user message."""
        print(f"Adding user message: {text}")
        self.messages.append(OpenAIMessage(role=OpenAIRole.user, content=text))

    def add_model_response(self, text: str):
        """Append an assistant message."""
        print(f"Adding model response model: {text}")
        self.messages.append(OpenAIMessage(role=OpenAIRole.assistant, content=text))

    def to_openai_prompt(self) -> list:
        """Serialize the full history as an OpenAI-style messages list."""
        chat_text = []
        for message in self.messages:
            chat_text.append(message.as_dict())
        return chat_text
