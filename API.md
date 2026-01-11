"""
API and Integration Guide for Telegram File-to-Link Bot

This module documents the public interfaces and how external systems can
interact with the bot's core components.
"""

# ==============================================================================
# STORAGE API
# ==============================================================================

"""
storage.py provides the FileStorage class for file metadata management.

Usage:
------
from storage import storage, FileMetadata

# Generate unique file key
file_key = storage.generate_file_key()
# Returns: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5"

# Store file metadata
metadata = FileMetadata(
    file_key=file_key,
    file_id="AgACAgIAAxkBAAIBZGdPVa...",  # Telegram file_id
    file_name="document.pdf",
    file_size=2048576,  # bytes
    user_id=123456789,
    message_id_in_storage=42,  # Message ID in storage channel
    has_password=False,
)
key = storage.store_file(metadata)

# Retrieve file metadata
meta = storage.get_file(file_key)
print(meta.file_name)  # "document.pdf"
print(meta.user_id)    # 123456789

# Update password
storage.update_password(file_key, "my_secret_password")

# Get all files for a user
user_files = storage.get_user_files(user_id=123456789)
for f in user_files:
    print(f.file_name, f.has_password)

# Delete file metadata
storage.delete_file(file_key)

Data Structure:
---------------
FileMetadata:
  - file_key: str (unique identifier)
  - file_id: str (Telegram file_id for access)
  - file_name: str
  - file_size: int (bytes)
  - user_id: int (uploader Telegram ID)
  - message_id_in_storage: int (message in storage channel)
  - has_password: bool
  - password: Optional[str]
  - created_at: str (ISO timestamp)

Persistence:
  - All data stored in data/file_storage.json
  - Automatically saved on every modification
  - Load on startup from disk
"""


# ==============================================================================
# STATE MANAGEMENT API
# ==============================================================================

"""
states.py provides the StateManager for tracking user conversation state.

Usage:
------
from states import state_manager

# Get or create user state
state = state_manager.get_state(user_id=123456789)

# Track file being uploaded
state_manager.set_file_info(
    user_id=123456789,
    file_key="abc123",
    file_id="AgAC...",
    file_name="video.mp4",
    file_size=50000000,
)

# Check if user is awaiting password
state = state_manager.get_state(123456789)
if state.awaiting_password:
    # Next message from this user is password input
    password = "user_input"

# Set password state
state_manager.set_awaiting_password(user_id=123456789, awaiting=True)
state_manager.set_password_choice(user_id=123456789, choice="yes")

# Clear state after flow completion
state_manager.clear_state(user_id=123456789)

State Machine Diagram:
----------------------
[Idle] 
  ↓ (user sends file)
[File Uploaded] 
  ↓ (show password choice)
[Awaiting Choice]
  ├→ pwd_no: [Deliver Links] → Clear
  └→ pwd_yes: [Awaiting Password] → (user types) → [Deliver Links] → Clear
"""


# ==============================================================================
# LINK GENERATION API
# ==============================================================================

"""
links.py provides the LinkGenerator for creating access URLs.

Usage:
------
from links import link_gen

# Generate individual links
stream_url = link_gen.generate_stream_link("abc123")
# Returns: "https://stream.example.com/abc123"

download_url = link_gen.generate_download_link("abc123")
# Returns: "https://download.example.com/abc123"

tg_url = link_gen.generate_tg_link("my_bot", 12345)
# Returns: "https://t.me/my_bot/12345"

# Generate secure token for API access
token = link_gen.generate_access_token("abc123")
# Returns: secure 32-byte URL-safe token

# Format user-friendly message
message = link_gen.format_links_message(
    file_name="presentation.pptx",
    file_key="abc123",
    has_password=True,
    stream_link="https://stream.example.com/abc123",
    download_link="https://download.example.com/abc123",
    tg_link="https://t.me/bot/123"
)
# Returns: Markdown-formatted message with all links

Configuration:
  - Update config.py STREAM_LINK_PATTERN to customize URLs
  - Pattern must include {file_key} placeholder
  - Example: "https://mycdn.com/files/{file_key}"
"""


# ==============================================================================
# KEYBOARD GENERATION API
# ==============================================================================

"""
keyboards.py provides pre-built inline keyboards for user interactions.

Usage:
------
from keyboards import keyboards
from pyrogram.types import Message

# Password choice keyboard
async def ask_password(message: Message):
    await message.reply_text(
        "Do you want to protect this file?",
        reply_markup=keyboards.password_choice_keyboard()
    )
    # Shows: [✅ No Password] [🔒 Yes, Set Password]

# Confirm password keyboard
async def confirm_password(message: Message):
    await message.reply_text(
        "Password has been set.",
        reply_markup=keyboards.confirm_password_keyboard()
    )
    # Shows: [✅ Password Set]

Button Callbacks:
  - "pwd_no" → User chose no password
  - "pwd_yes" → User chose password protection
  - "pwd_confirm" → User confirmed password entry
"""


# ==============================================================================
# BOT HANDLER FLOW DOCUMENTATION
# ==============================================================================

"""
Handler Registration Order (CRITICAL):
=====================================

The order handlers are registered DIRECTLY affects which handler processes
each message. This bot uses Pyrogram's handler system with specific filters.

1. START COMMAND HANDLER
   Pattern: filters.command("start") & filters.private
   Behavior: Initializes user state, shows instructions
   When: User sends /start
   
2. FILE UPLOAD HANDLER ⭐ CRITICAL POSITION
   Pattern: (filters.document | filters.video | filters.audio) & filters.private
   Behavior: Intercepts files, creates metadata, asks password choice
   When: User uploads file
   WHY HERE: This handler MUST come before default_handler to prevent
             "awaiting_password" messages from being caught
   
3. PASSWORD CHOICE CALLBACK HANDLER
   Pattern: filters.regex("^pwd_(yes|no)$")
   Behavior: Routes to password or link delivery
   When: User clicks password choice button
   
4. PASSWORD INPUT HANDLER
   Pattern: filters.private & ~filters.bot & ~filters.command
   Behavior: ONLY processes if state.awaiting_password=True
   When: User sends text while awaiting password
   SAFETY: Guards with "if not state.awaiting_password: return"
           prevents interfering with other flows
   
5. DEFAULT HANDLER (FALLBACK)
   Pattern: (none - catches all)
   Behavior: Prompts user to send file or use /start
   When: Message doesn't match any above handler
   Position: MUST be last to avoid intercepting intended handlers

Control Flow Diagram:
=====================

User sends /start
  ↓
START HANDLER
  ↓ (initializes state)
  ↓
Prompts user to send file

User sends file
  ↓
FILE UPLOAD HANDLER (highest specificity - document|video|audio)
  ↓ (stores metadata, generates key)
  ↓
PASSWORD CHOICE HANDLER shows button
  ↓
User clicks button
  ↓
PASSWORD CHOICE CALLBACK (filters.regex matches)
  ├→ pwd_no: _deliver_links() → clear state
  └→ pwd_yes: set state.awaiting_password=True
              show password input prompt
  ↓
User sends password text
  ↓
PASSWORD INPUT HANDLER
  ├→ if state.awaiting_password: process password
  └→ else: return (don't interfere)
  ↓
_deliver_links() → clear state

Handler Specificity (Why Order Matters):
=========================================

Pyrogram applies handlers in registration order. When a message arrives:

1. Filters are checked in order
2. First matching handler processes the message
3. Message is consumed (subsequent handlers don't see it)

THEREFORE:
- File upload handler MUST come before default handler
  (otherwise files would be caught by default handler)
  
- Password input handler must check state.awaiting_password
  (otherwise all text would be treated as password)

- Callback handlers use regex for perfect matching
  (no conflict with other handlers)

No Circular Dependencies:
=========================
✅ Each handler either:
   - Processes and returns
   - Sets state for next handler
   - Calls helper function (_deliver_links)

❌ No handler should:
   - Call another handler
   - Use recursive message sending
   - Depend on reply_to_message without verification
"""


# ==============================================================================
# DEPLOYMENT CHECKLIST
# ==============================================================================

"""
Pre-Deployment:
  ☑ Copy .env.example to .env
  ☑ Fill in API_ID, API_HASH, BOT_TOKEN
  ☑ Create private storage channel, get ID for STORAGE_CHANNEL_ID
  ☑ Set your Telegram ID as ADMIN_ID
  ☑ Run: python test.py (all tests pass)
  ☑ Create data/ directory: mkdir -p data

Runtime:
  ☑ Run: python bot.py
  ☑ Check: Bot starts without errors
  ☑ Check: Can send /start command
  ☑ Check: Can upload file
  ☑ Check: File appears in storage channel
  ☑ Check: Password buttons appear
  ☑ Check: Links delivered successfully

Monitoring:
  ☑ Check logs regularly: grep "ERROR" bot.log
  ☑ Monitor data/file_storage.json size
  ☑ Verify storage channel has enough space
  ☑ Check for stuck states (await_password=True)

Troubleshooting:
  Problem: File upload stuck at "Processing..."
    - Check storage channel access
    - Verify STORAGE_CHANNEL_ID is correct
    - Check bot is member of storage channel
    
  Problem: Links not generated
    - Check config.py link patterns
    - Verify file_key was stored
    - Check for exceptions in logs
    
  Problem: Callback not working
    - Verify callback_data matches regex
    - Check message.edit_text succeeds
    - Monitor callback_query.answer
"""

# ==============================================================================
# EXTENSION POINTS
# ==============================================================================

"""
How to Extend the Bot:

1. Custom Link Generator:
   - Modify links.py LinkGenerator class
   - Implement custom URL patterns
   - Update config.py patterns
   
2. Additional File Handlers:
   - Add new filter in bot.py file_upload_handler
   - Extract metadata same way
   - Store in same format
   
3. Advanced State Tracking:
   - Extend UserState dataclass in states.py
   - Add new fields for application logic
   - Update state_manager methods
   
4. Database Integration:
   - Replace FileStorage with database adapter
   - Implement same interface (get_file, store_file, etc.)
   - Add migrations as needed
   
5. Admin Commands:
   - Add new handler with filters.command
   - Check if user_id == ADMIN_ID
   - Examples: /delete_file, /stats, /clear_all
"""
