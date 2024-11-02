from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ConversationHistory(BaseModel):
    messages: list[dict]
    memory_size: int
    system_prompt: Optional[str] = None

    def __init__(self, memory_size: int = 3, system_prompt: Optional[str] = None, messages: list[dict] = []):
        super().__init__(
            messages=messages, 
            memory_size=memory_size,
            system_prompt=system_prompt
        )
        if system_prompt:
            self.add_message("assistant", system_prompt)

    def add_message(self, role: str, message: str):
        if role not in ["user", "assistant"]:
            logger.warning(f"Ignoring message with role '{role}'. Only 'user' and 'assistant' roles are allowed.")
            return
        self.messages.append({"role": role, "content": message})
        self.prune_history()

    def prune_history(self):
        initial_length = len(self.messages)
        user_messages = [msg for msg in self.messages if msg["role"] == "user"]
        
        if self.memory_size == 0:
            self.messages = [self.messages[0]]
            logger.info(f"Pruned history to system message")

        
        elif len(user_messages) > self.memory_size:
            cutoff_index = self.messages.index(user_messages[-self.memory_size])
            # Always keep the assistant prompt if present
            if self.messages and self.messages[0]["role"] == "assistant":
                self.messages = [self.messages[0]] + self.messages[cutoff_index:]
            else:
                self.messages = self.messages[cutoff_index:]
            final_length = len(self.messages)
            logger.info(f"Pruned history from {initial_length} to {final_length} messages")

    def pretty_print(self):
        print("\n\nCONVERSATION HISTORY:")
        for msg in self.messages:
            print(f"\n{msg['role'].upper()}: {msg['content']}")