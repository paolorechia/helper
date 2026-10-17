from dataclasses import dataclass, field
from enum import StrEnum, auto


class OpenAIRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


@dataclass
class OpenAIMessage:
    role: OpenAIRole
    content: str

    def as_dict(self):
        return {"role": self.role.value, "content": self.content}


@dataclass
class Chat:
    messages: list[OpenAIMessage] = field(default_factory=list)

    def add_system_instruction(self, text: str):
        print(f"Adding system instruction: {text}")
        self.messages.append(OpenAIMessage(role=OpenAIRole.system, content=text))

    def add_user_message(self, text: str):
        print(f"Adding user message: {text}")
        self.messages.append(OpenAIMessage(role=OpenAIRole.user, content=text))

    def add_model_response(self, text: str):
        print(f"Adding model response model: {text}")
        self.messages.append(OpenAIMessage(role=OpenAIRole.assistant, content=text))

    def to_openai_prompt(self) -> list:
        chat_text = []
        for message in self.messages:
            chat_text.append(message.as_dict())
        # print(f"Generated prompt: {chat_text}")
        return chat_text
