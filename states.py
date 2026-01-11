"""
User state management for handling conversation flow.
Uses Pyrogram's FSM-like pattern with simple state tracking.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class UserState:
    """Represents a user's current state in the file upload flow"""
    user_id: int
    file_key: Optional[str] = None
    file_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    awaiting_password: bool = False
    password_choice: Optional[str] = None  # "yes" or "no"
    context: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Manages user states across the bot"""
    
    def __init__(self):
        self.states: Dict[int, UserState] = {}
    
    def get_state(self, user_id: int) -> UserState:
        """Get or create user state"""
        if user_id not in self.states:
            self.states[user_id] = UserState(user_id=user_id)
        return self.states[user_id]
    
    def set_file_info(
        self, user_id: int, file_key: str, file_id: str,
        file_name: str, file_size: int
    ):
        """Store file info in user state"""
        state = self.get_state(user_id)
        state.file_key = file_key
        state.file_id = file_id
        state.file_name = file_name
        state.file_size = file_size
    
    def set_awaiting_password(self, user_id: int, awaiting: bool):
        """Set whether user is awaiting password input"""
        state = self.get_state(user_id)
        state.awaiting_password = awaiting
    
    def set_password_choice(self, user_id: int, choice: str):
        """Set user's password choice (yes/no)"""
        state = self.get_state(user_id)
        state.password_choice = choice
    
    def clear_state(self, user_id: int):
        """Clear user state after flow completion"""
        if user_id in self.states:
            del self.states[user_id]


# Global state manager instance
state_manager = StateManager()
