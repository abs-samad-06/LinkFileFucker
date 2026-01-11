"""
Main Telegram bot application.
Pyrogram-based File-to-Link converter with proper handler flow.

HANDLER REGISTRATION ORDER (CRITICAL):
1. Start command
2. File upload (document/video/audio)
3. Password choice callback
4. Password input message
5. Error handlers

This ordering prevents handler conflicts and ensures linear flow.
"""

import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, Document, Video, Audio
from pyrogram.errors import RpcError

from config import (
    API_ID, API_HASH, BOT_TOKEN, STORAGE_CHANNEL_ID, ADMIN_ID, BOT_NAME
)
from storage import storage, FileMetadata
from states import state_manager
from links import link_gen
from keyboards import keyboards

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Pyrogram client
app = Client(
    name="file_to_link_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


# ==============================================================================
# HANDLER 1: START COMMAND
# ==============================================================================

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    state_manager.get_state(user_id)  # Initialize state
    
    await message.reply_text(
        f"👋 Welcome to {BOT_NAME}!\n\n"
        "📤 Send me any file (document, video, audio) and I'll convert it to:\n"
        "  • Stream Link (▶️)\n"
        "  • Download Link (⬇️)\n"
        "  • Telegram Link (📱)\n\n"
        "🔒 Optional: Protect your file with a password!\n\n"
        "Just send a file to get started.",
        disable_web_page_preview=True
    )
    logger.info(f"User {user_id} started bot")


# ==============================================================================
# HANDLER 2: FILE UPLOAD INTERCEPTION
# This handler MUST come before any other message handlers.
# It catches document, video, and audio uploads.
# ==============================================================================

@app.on_message(
    (filters.document | filters.video | filters.audio) & 
    filters.private &
    ~filters.bot
)
async def file_upload_handler(client: Client, message: Message):
    """
    PRIMARY HANDLER: Intercept file uploads and start the flow.
    
    Flow:
    1. Extract file metadata
    2. Forward to storage channel
    3. Generate unique file_key
    4. Store metadata
    5. Ask about password protection
    """
    user_id = message.from_user.id
    
    # Determine file type and extract metadata
    if message.document:
        file_obj = message.document
        file_name = file_obj.file_name or "document"
        file_id = file_obj.file_id
        file_size = file_obj.file_size
    elif message.video:
        file_obj = message.video
        file_name = file_obj.file_name or f"video_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_size = file_obj.file_size
    elif message.audio:
        file_obj = message.audio
        file_name = file_obj.file_name or f"audio_{file_obj.file_unique_id[:8]}"
        file_id = file_obj.file_id
        file_size = file_obj.file_size
    else:
        return
    
    try:
        # Step 1: Send processing indicator
        processing_msg = await message.reply_text(
            "⏳ Processing your file..."
        )
        
        # Step 2: Forward file to storage channel
        stored_message = await client.forward_messages(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=user_id,
            message_ids=message.id,
        )
        
        # Step 3: Generate unique file key
        file_key = storage.generate_file_key()
        
        # Step 4: Store file metadata
        metadata = FileMetadata(
            file_key=file_key,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            user_id=user_id,
            message_id_in_storage=stored_message.id,
            has_password=False,
        )
        storage.store_file(metadata)
        
        # Step 5: Update user state with file info
        state_manager.set_file_info(
            user_id=user_id,
            file_key=file_key,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
        )
        
        logger.info(
            f"File uploaded by {user_id}: {file_name} "
            f"(key: {file_key}, size: {file_size})"
        )
        
        # Step 6: Ask about password protection
        await processing_msg.edit_text(
            f"📁 **File Received:** `{file_name}`\n"
            f"💾 **Size:** {file_size / (1024*1024):.2f} MB\n"
            f"🔑 **Key:** `{file_key}`\n\n"
            f"🔐 Do you want to protect this file with a password?",
            reply_markup=keyboards.password_choice_keyboard()
        )
        
    except RpcError as e:
        logger.error(f"RPC error processing file for {user_id}: {e}")
        await message.reply_text(
            "❌ Error processing file. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error in file_upload_handler: {e}")
        await message.reply_text(
            "❌ Unexpected error. Please try again."
        )


# ==============================================================================
# HANDLER 3: PASSWORD CHOICE CALLBACK
# User clicks "Yes, Set Password" or "No Password"
# ==============================================================================

@app.on_callback_query(filters.regex("^pwd_(yes|no)$"))
async def password_choice_callback(client: Client, callback_query: CallbackQuery):
    """
    Handle password choice callback.
    
    Branches:
    - pwd_no: Immediately generate and send links
    - pwd_yes: Ask user to input password
    """
    user_id = callback_query.from_user.id
    choice = callback_query.data  # "pwd_yes" or "pwd_no"
    
    state = state_manager.get_state(user_id)
    
    # Verify user has a file in progress
    if not state.file_key:
        await callback_query.answer(
            "❌ No file in progress. Send a file first.",
            show_alert=True
        )
        return
    
    try:
        if choice == "pwd_no":
            # BRANCH 1: NO PASSWORD
            # Generate links immediately and send them
            await _deliver_links(
                client=client,
                callback_query=callback_query,
                user_id=user_id,
                state=state,
                has_password=False,
                password=None
            )
            
        elif choice == "pwd_yes":
            # BRANCH 2: YES PASSWORD
            # Ask user to enter password
            state_manager.set_awaiting_password(user_id, True)
            state_manager.set_password_choice(user_id, "yes")
            
            await callback_query.message.edit_text(
                "🔐 Enter a password for your file:\n\n"
                "Just send the password as a message.",
                reply_markup=None
            )
            await callback_query.answer()
            logger.info(f"User {user_id} chose password protection")
        
    except RpcError as e:
        logger.error(f"RPC error in password_choice_callback: {e}")
        await callback_query.answer(
            "❌ Error processing choice",
            show_alert=True
        )
    except Exception as e:
        logger.error(f"Unexpected error in password_choice_callback: {e}")
        await callback_query.answer(
            "❌ Unexpected error",
            show_alert=True
        )


# ==============================================================================
# HANDLER 4: PASSWORD INPUT MESSAGE
# User sends password as a message (only if awaiting_password=True)
# ==============================================================================

@app.on_message(
    filters.private &
    ~filters.bot &
    ~filters.command
)
async def password_input_handler(client: Client, message: Message):
    """
    Handle password input from user.
    
    This handler is specific to users who are awaiting password input.
    It processes the message as a password and delivers links.
    """
    user_id = message.from_user.id
    state = state_manager.get_state(user_id)
    
    # Check if user is actually awaiting password
    if not state.awaiting_password:
        # User might be sending a file or other message
        # This handler should NOT interfere with file uploads
        # File uploads are already handled by file_upload_handler
        # which has higher specificity (filters.document | filters.video | filters.audio)
        return
    
    password = message.text.strip()
    
    if not password or len(password) < 1:
        await message.reply_text(
            "❌ Password cannot be empty. Please try again:"
        )
        return
    
    try:
        # Update storage with password
        storage.update_password(state.file_key, password)
        
        logger.info(f"Password set for file {state.file_key} by user {user_id}")
        
        # Deliver links with password enabled
        await _deliver_links(
            client=client,
            message=message,
            user_id=user_id,
            state=state,
            has_password=True,
            password=password
        )
        
    except Exception as e:
        logger.error(f"Error in password_input_handler: {e}")
        await message.reply_text(
            "❌ Error setting password. Please try again."
        )


# ==============================================================================
# HELPER FUNCTION: DELIVER LINKS
# Common logic for both password and no-password flows
# ==============================================================================

async def _deliver_links(
    client: Client,
    user_id: int,
    state,
    has_password: bool,
    password: Optional[str] = None,
    callback_query: Optional[CallbackQuery] = None,
    message: Optional[Message] = None,
):
    """
    Deliver links to user.
    
    This is the final step of both flows:
    1. No Password Flow: pwd_no callback → immediate delivery
    2. Yes Password Flow: pwd_yes callback → password input → delivery
    
    Args:
        client: Pyrogram client
        user_id: User ID
        state: User state
        has_password: Whether file has password protection
        password: Password (if any)
        callback_query: CallbackQuery if called from callback
        message: Message if called from message handler
    """
    try:
        # Generate links
        stream_link = link_gen.generate_stream_link(state.file_key)
        download_link = link_gen.generate_download_link(state.file_key)
        
        # Retrieve storage message for Telegram link
        metadata = storage.get_file(state.file_key)
        
        if not metadata:
            if callback_query:
                await callback_query.answer(
                    "❌ File not found",
                    show_alert=True
                )
            else:
                await message.reply_text("❌ File not found")
            return
        
        # Get bot username for Telegram link
        bot = await client.get_me()
        tg_link = link_gen.generate_tg_link(
            bot_username=bot.username,
            message_id=metadata.message_id_in_storage
        )
        
        # Format the links message
        links_message = link_gen.format_links_message(
            file_name=state.file_name,
            file_key=state.file_key,
            has_password=has_password,
            stream_link=stream_link,
            download_link=download_link,
            tg_link=tg_link
        )
        
        # Send links
        if callback_query:
            await callback_query.message.edit_text(
                links_message,
                disable_web_page_preview=True
            )
            await callback_query.answer("✅ Links generated!")
        else:
            await message.reply_text(
                links_message,
                disable_web_page_preview=True
            )
        
        # Clear user state after successful delivery
        state_manager.clear_state(user_id)
        
        logger.info(
            f"Links delivered for file {state.file_key} to user {user_id}"
        )
        
    except Exception as e:
        logger.error(f"Error in _deliver_links: {e}")
        error_msg = "❌ Error generating links. Please try again."
        
        if callback_query:
            await callback_query.answer(error_msg, show_alert=True)
        else:
            await message.reply_text(error_msg)


# ==============================================================================
# ERROR HANDLER
# ==============================================================================

@app.on_message()
async def default_handler(client: Client, message: Message):
    """
    Catch-all handler for unhandled messages.
    Only triggers if no other handler matched.
    """
    user_id = message.from_user.id
    state = state_manager.get_state(user_id)
    
    # If user is not awaiting password, they might have sent
    # a message that doesn't match any handler
    if not state.awaiting_password:
        await message.reply_text(
            "📤 Please send a file (document, video, or audio) "
            "or use /start for help."
        )


# ==============================================================================
# BOT LIFECYCLE
# ==============================================================================

async def on_startup():
    """Run on bot startup"""
    logger.info(f"Starting {BOT_NAME}")
    bot = await app.get_me()
    logger.info(f"Bot username: @{bot.username}")


async def on_shutdown():
    """Run on bot shutdown"""
    logger.info(f"Shutting down {BOT_NAME}")


def run():
    """Start the bot"""
    app.add_handler(on_startup, startup_handler=True)
    app.add_handler(on_shutdown, shutdown_handler=True)
    
    logger.info("Bot is running...")
    app.run()


if __name__ == "__main__":
    run()
