"""
Integration tests and manual testing guide for the Telegram File-to-Link bot.

TESTING CHECKLIST:
==================

1. BOT STARTUP
   [ ] Set .env with valid API_ID, API_HASH, BOT_TOKEN
   [ ] Set STORAGE_CHANNEL_ID to a valid private channel
   [ ] Set ADMIN_ID to your Telegram ID
   [ ] Run: python bot.py
   [ ] Check logs for "Bot is running..."

2. START COMMAND
   [ ] Send /start to bot
   [ ] Expected: Welcome message with instructions
   [ ] Check: User state initialized

3. NO-PASSWORD FLOW
   [ ] Send a document/video/audio file
   [ ] Expected: "Processing your file..."
   [ ] Expected: File details + password choice keyboard
   [ ] Click: "✅ No Password"
   [ ] Expected: Links message with file key
   [ ] Verify: File stored in storage channel
   [ ] Verify: Links contain correct file_key

4. YES-PASSWORD FLOW
   [ ] Send another file
   [ ] Expected: File processing
   [ ] Click: "🔒 Yes, Set Password"
   [ ] Expected: "Enter a password for your file"
   [ ] Send password: "mypassword123"
   [ ] Expected: Links message with password indicator
   [ ] Verify: File metadata has password flag

5. FILE STORAGE
   [ ] Check storage directory: ls -la data/
   [ ] Verify file_storage.json exists
   [ ] Check file metadata is persisted
   [ ] Verify message_id_in_storage matches storage channel

6. STATE MANAGEMENT
   [ ] Upload file 1 → choose no password
   [ ] Immediately upload file 2 → choose yes password
   [ ] Send password for file 2
   [ ] Expected: Each flow completes independently
   [ ] Expected: No state collision

7. ERROR HANDLING
   [ ] Test with invalid environment
   [ ] Test with invalid storage channel
   [ ] Test with network interruption
   [ ] Expected: Graceful error messages
   [ ] Check: Logs show error details

8. HANDLER ISOLATION
   [ ] Send file → receive password prompt
   [ ] Send another file while awaiting password
   [ ] Expected: First file password handler should NOT intercept
   [ ] Expected: Second file should start new flow

EXPECTED LOGS:
==============
- "User X started bot"
- "File uploaded by X: filename (key: ..., size: ...)"
- "User X chose password protection"
- "Password set for file X by user Y"
- "Links delivered for file X to user Y"

TROUBLESHOOTING:
================

Problem: "No module named pyrogram"
Solution: pip install -r requirements.txt

Problem: Links not delivered
Check:
  1. File uploaded to storage channel? → Check STORAGE_CHANNEL_ID
  2. Password choice callback received? → Check callback_data in handler
  3. State manager has file_key? → Check state initialization

Problem: Handler conflicts (file not intercepted)
Check:
  1. Order: file_upload_handler must come before default_handler
  2. Filters: document | video | audio are exclusive
  3. State: awaiting_password prevents interference

Problem: File stuck at "Processing..."
Check:
  1. Storage channel is valid and bot is member
  2. No RpcError in logs
  3. Forward message operation succeeds
"""

import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all modules can be imported (except config which needs .env)"""
    try:
        # Skip config import as it requires .env file
        # from config import API_ID, API_HASH, BOT_TOKEN
        from storage import storage, FileMetadata
        from states import state_manager
        from links import link_gen
        from keyboards import keyboards
        # from bot import app  # Requires config which requires .env
        
        logger.info("✅ All imports successful")
        return True
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def test_storage():
    """Test file storage operations"""
    try:
        from storage import storage, FileMetadata
        
        # Generate key
        key = storage.generate_file_key()
        assert key, "Failed to generate key"
        assert len(key) > 0, "Key is empty"
        
        # Store file
        metadata = FileMetadata(
            file_key=key,
            file_id="test_file_id",
            file_name="test.pdf",
            file_size=1024*1024,
            user_id=12345,
            message_id_in_storage=999,
            has_password=False,
        )
        
        stored_key = storage.store_file(metadata)
        assert stored_key == key, "Stored key mismatch"
        
        # Retrieve file
        retrieved = storage.get_file(key)
        assert retrieved, "Failed to retrieve file"
        assert retrieved.file_name == "test.pdf", "File name mismatch"
        
        # Update password
        success = storage.update_password(key, "secret")
        assert success, "Failed to update password"
        
        retrieved = storage.get_file(key)
        assert retrieved.password == "secret", "Password not updated"
        assert retrieved.has_password, "Password flag not set"
        
        # Delete file
        success = storage.delete_file(key)
        assert success, "Failed to delete file"
        
        retrieved = storage.get_file(key)
        assert not retrieved, "File not deleted"
        
        logger.info("✅ Storage tests passed")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Storage test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in storage test: {e}")
        return False


def test_states():
    """Test state management"""
    try:
        from states import state_manager
        
        user_id = 99999
        
        # Get state
        state = state_manager.get_state(user_id)
        assert state.user_id == user_id, "User ID mismatch"
        assert not state.awaiting_password, "Initial state should not await password"
        
        # Set file info
        state_manager.set_file_info(
            user_id=user_id,
            file_key="test_key",
            file_id="test_id",
            file_name="test.txt",
            file_size=5000,
        )
        
        state = state_manager.get_state(user_id)
        assert state.file_key == "test_key", "File key not set"
        assert state.file_name == "test.txt", "File name not set"
        
        # Set password state
        state_manager.set_awaiting_password(user_id, True)
        state = state_manager.get_state(user_id)
        assert state.awaiting_password, "Awaiting password not set"
        
        state_manager.set_password_choice(user_id, "yes")
        state = state_manager.get_state(user_id)
        assert state.password_choice == "yes", "Password choice not set"
        
        # Clear state
        state_manager.clear_state(user_id)
        assert user_id not in state_manager.states, "State not cleared"
        
        logger.info("✅ State tests passed")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ State test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in state test: {e}")
        return False


def test_links():
    """Test link generation"""
    try:
        # Temporarily create a dummy .env for this test
        from pathlib import Path
        env_file = Path(".env")
        had_env = env_file.exists()
        
        if not had_env:
            with open(".env", "w") as f:
                f.write("API_ID=123\nAPI_HASH=abc\nBOT_TOKEN=token\n")
                f.write("STORAGE_CHANNEL_ID=456\nADMIN_ID=789\n")
        
        from links import link_gen
        
        file_key = "test_key_12345"
        
        # Generate links
        stream = link_gen.generate_stream_link(file_key)
        assert file_key in stream, "File key not in stream link"
        
        download = link_gen.generate_download_link(file_key)
        assert file_key in download, "File key not in download link"
        
        tg = link_gen.generate_tg_link("testbot", 12345)
        assert "testbot" in tg, "Bot username not in TG link"
        assert "12345" in tg, "Message ID not in TG link"
        
        # Format message
        msg = link_gen.format_links_message(
            file_name="test.pdf",
            file_key=file_key,
            has_password=True,
            stream_link=stream,
            download_link=download,
            tg_link=tg
        )
        
        assert "test.pdf" in msg, "File name not in message"
        assert file_key in msg, "File key not in message"
        assert "Password Protected:" in msg and "Yes" in msg, "Password status not in message"
        assert stream in msg, "Stream link not in message"
        
        # Cleanup
        if not had_env and env_file.exists():
            env_file.unlink()
        
        logger.info("✅ Link generation tests passed")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Link test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in link test: {e}")
        return False


def test_keyboards():
    """Test keyboard generation"""
    try:
        from keyboards import keyboards
        from pyrogram.types import InlineKeyboardMarkup
        
        # Password choice keyboard
        kb = keyboards.password_choice_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup), "Invalid keyboard type"
        assert len(kb.inline_keyboard) > 0, "Keyboard has no buttons"
        
        # Check buttons
        buttons = kb.inline_keyboard[0]
        assert len(buttons) == 2, "Should have 2 buttons"
        
        button_data = [btn.callback_data for btn in buttons]
        assert "pwd_no" in button_data, "pwd_no button missing"
        assert "pwd_yes" in button_data, "pwd_yes button missing"
        
        logger.info("✅ Keyboard tests passed")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Keyboard test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in keyboard test: {e}")
        return False


def run_all_tests():
    """Run all unit tests"""
    logger.info("=" * 60)
    logger.info("RUNNING UNIT TESTS")
    logger.info("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Storage", test_storage),
        ("States", test_states),
        ("Links", test_links),
        ("Keyboards", test_keyboards),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            logger.error(f"Fatal error in {name}: {e}")
            results[name] = False
    
    logger.info("=" * 60)
    logger.info("TEST RESULTS")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    return all(results.values())


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
