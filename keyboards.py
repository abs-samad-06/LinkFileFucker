"""
Keyboard/button generation for user interactions.
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class Keyboards:
    """Generates inline keyboards for user interactions"""
    
    @staticmethod
    def password_choice_keyboard() -> InlineKeyboardMarkup:
        """Keyboard for asking password protection choice"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ No Password", callback_data="pwd_no"),
                InlineKeyboardButton("🔒 Yes, Set Password", callback_data="pwd_yes"),
            ]
        ])
    
    @staticmethod
    def confirm_password_keyboard() -> InlineKeyboardMarkup:
        """Keyboard for confirming password was set"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Password Set", callback_data="pwd_confirm"),
            ]
        ])


keyboards = Keyboards()
