from pydantic import BaseModel, Field
from typing import List, Optional

class ConversationHistory(BaseModel):
    history: List[dict] = Field(default_factory=list)
    user_message_memory_size: int = 3

    def update(self, role, content, name = None):
        message = {"role": role, "content": content}
        if name:
            message["name"] = name
        self.history.append(message)

    def get_recent(self, user_message_memory_size = 3):
        system_message = next((msg for msg in self.history if msg["role"] == "system"), None)
        user_messages = [msg for msg in self.history if msg["role"] == "user"]
        recent_messages = user_messages[user_message_memory_size:]
        start_index = self.history.index(recent_messages[0]) if recent_messages else len(self.history)
        recent_history = self.history[start_index:]
        
        if system_message:
            recent_history = [system_message] + recent_history
        
        return recent_history

    def get(self):
        return self.history
