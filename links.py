"""
Link generation module.
Creates streaming, download, and Telegram-accessible links.
"""

import secrets
from typing import Dict, Tuple
from config import STREAM_LINK_PATTERN, DOWNLOAD_LINK_PATTERN, TG_LINK_PATTERN


class LinkGenerator:
    """Generates access links for stored files"""
    
    @staticmethod
    def generate_stream_link(file_key: str) -> str:
        """Generate streaming link"""
        return STREAM_LINK_PATTERN.format(file_key=file_key)
    
    @staticmethod
    def generate_download_link(file_key: str) -> str:
        """Generate download link"""
        return DOWNLOAD_LINK_PATTERN.format(file_key=file_key)
    
    @staticmethod
    def generate_tg_link(bot_username: str, message_id: int) -> str:
        """Generate Telegram link"""
        return TG_LINK_PATTERN.format(
            bot_username=bot_username,
            message_id=message_id
        )
    
    @staticmethod
    def generate_access_token(file_key: str) -> str:
        """Generate secure access token for password-protected files"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def format_links_message(
        file_name: str,
        file_key: str,
        has_password: bool = False,
        stream_link: str = None,
        download_link: str = None,
        tg_link: str = None
    ) -> str:
        """Format links into a user-friendly message"""
        
        message = f"📁 **File Links for:** `{file_name}`\n\n"
        message += f"🔑 **File Key:** `{file_key}`\n"
        message += f"🔒 **Password Protected:** {'Yes' if has_password else 'No'}\n\n"
        
        message += "**Available Links:**\n"
        if stream_link:
            message += f"▶️ [Stream Link]({stream_link})\n"
        if download_link:
            message += f"⬇️ [Download Link]({download_link})\n"
        if tg_link:
            message += f"📱 [Telegram Link]({tg_link})\n"
        
        return message


# Global instance
link_gen = LinkGenerator()
