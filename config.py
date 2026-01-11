"""
Configuration module for the Telegram File-to-Link bot.
Loads environment variables and provides centralized config.
"""

import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Validation
if not all([API_ID, API_HASH, BOT_TOKEN, STORAGE_CHANNEL_ID, ADMIN_ID]):
    raise ValueError(
        "Missing required environment variables. "
        "Check .env file against .env.example"
    )

# Bot configuration
BOT_NAME = "File to Link Bot"

# File storage
MAX_FILE_NAME_LENGTH = 100
TEMP_STORAGE_PATH = "temp_storage"

# Link generation
STREAM_LINK_PATTERN = "https://stream.example.com/{file_key}"
DOWNLOAD_LINK_PATTERN = "https://download.example.com/{file_key}"
TG_LINK_PATTERN = "https://t.me/{bot_username}/{message_id}"

# Message TTL (never expire unless admin deletes)
FILE_STORAGE_TTL = None
