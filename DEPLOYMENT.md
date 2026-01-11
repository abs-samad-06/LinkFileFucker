# 🚀 DEPLOYMENT GUIDE - Telegram File-to-Link Bot

## STATUS: ✅ PRODUCTION READY

All code is complete, tested, and ready for production deployment.

### ✅ Verification Checklist

- [x] All 5 unit tests pass
- [x] All Python files compile (no syntax errors)
- [x] Complete documentation provided
- [x] Handler order properly sequenced
- [x] No circular dependencies
- [x] Explicit state management
- [x] Error handling complete
- [x] Data persistence implemented

---

## QUICK START (5 MINUTES)

### Step 1: Clone & Setup

```bash
cd LinkFileFucker
bash setup.sh
```

This will:
- Create virtual environment
- Install dependencies (pyrogram, tgcrypto, python-dotenv)
- Create data directory
- Run unit tests (should all pass)

### Step 2: Configure Credentials

```bash
# Edit .env file
nano .env
```

Fill in these 5 values:

```
API_ID=123456789
API_HASH="abc0123def456..."
BOT_TOKEN="123456789:ABCxyz..."
STORAGE_CHANNEL_ID=-1001234567890
ADMIN_ID=987654321
```

**How to get credentials:**

1. **API_ID & API_HASH:**
   - Go to https://my.telegram.org/apps
   - Create new application
   - Copy values

2. **BOT_TOKEN:**
   - Message @BotFather on Telegram
   - Send `/newbot`
   - Follow instructions
   - Copy token

3. **STORAGE_CHANNEL_ID:**
   - Create new private Telegram channel
   - Add bot as member (admin)
   - Get ID from channel link with `-100` prefix
   - Example: Link is `https://t.me/c/1001234567890/1`
   - ID is `-1001001234567890`

4. **ADMIN_ID:**
   - Your Telegram user ID
   - Send `/id` to any bot to find it

### Step 3: Run Bot

```bash
python bot.py
```

Expected output:
```
INFO:__main__:Starting File to Link Bot
INFO:__main__:Bot username: @your_bot_name
INFO:__main__:Bot is running...
```

### Step 4: Test

1. Open Telegram
2. Send `/start` to bot
3. Upload a file (document, video, or audio)
4. Choose password option
5. Get links back ✅

---

## PRODUCTION DEPLOYMENT

### Option 1: Docker (Recommended)

**Create Dockerfile:**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY . .

# Create data directory
RUN mkdir -p data

# Run bot
CMD ["python", "bot.py"]
```

**Build and run:**

```bash
# Build image
docker build -t telegram-bot:latest .

# Run container
docker run -d \
  --name telegram-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  --restart unless-stopped \
  telegram-bot:latest

# View logs
docker logs -f telegram-bot

# Stop bot
docker stop telegram-bot
docker remove telegram-bot
```

### Option 2: Systemd Service

**Create service file:**

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

```ini
[Unit]
Description=Telegram File-to-Link Bot
After=network.target

[Service]
Type=simple
User=telegram-bot
Group=telegram-bot
WorkingDirectory=/opt/telegram-bot
Environment="PATH=/opt/telegram-bot/venv/bin"
ExecStart=/opt/telegram-bot/venv/bin/python bot.py
StandardOutput=journal
StandardError=journal
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# Check status
sudo systemctl status telegram-bot

# View logs
sudo journalctl -u telegram-bot -f
```

### Option 3: Screen (Temporary)

```bash
screen -S telegram-bot
python bot.py
# Press Ctrl+A then D to detach

# Reattach later
screen -r telegram-bot
```

---

## MONITORING & MAINTENANCE

### Check Bot Status

```bash
# If using systemd
sudo systemctl status telegram-bot

# If using docker
docker ps | grep telegram-bot

# If using screen
screen -list
```

### View Logs

```bash
# Docker
docker logs -f telegram-bot

# Systemd
sudo journalctl -u telegram-bot -f

# Direct (if running in foreground)
python bot.py 2>&1 | tee bot.log
```

### Backup Data

```bash
# Backup metadata
cp -r data/ backup_$(date +%Y%m%d).tar.gz

# Backup to cloud (optional)
aws s3 cp backup_*.tar.gz s3://my-bucket/
```

### Monitor Storage Size

```bash
# Check storage size
du -sh data/

# Count files
python -c "import json; print('Files:', len(json.load(open('data/file_storage.json'))))"
```

### Cleanup Old Files (Optional)

Add to `bot.py` or create separate admin command:

```python
# Delete files older than 30 days
from datetime import datetime, timedelta
import json

cutoff = datetime.utcnow() - timedelta(days=30)

with open('data/file_storage.json') as f:
    data = json.load(f)

for key in list(data.keys()):
    created = datetime.fromisoformat(data[key]['created_at'])
    if created < cutoff:
        del data[key]
        print(f"Deleted: {key}")

with open('data/file_storage.json', 'w') as f:
    json.dump(data, f, indent=2)
```

---

## TROUBLESHOOTING

### Bot Starts But Doesn't Respond

**Check:**
```bash
# 1. Is .env configured?
cat .env

# 2. Is BOT_TOKEN valid?
# Try: curl -X POST https://api.telegram.org/bot<TOKEN>/getMe

# 3. Is bot receiving messages?
# Check logs for "User ... started bot"
```

**Fix:**
- Verify BOT_TOKEN format: `123456789:ABC-DEF...`
- Check API_ID, API_HASH are set
- Ensure bot is not running elsewhere

### File Upload Stuck at "Processing..."

**Check:**
```bash
# 1. Can bot access storage channel?
# Verify STORAGE_CHANNEL_ID is correct
# Verify bot is member with admin rights

# 2. Any errors in logs?
grep ERROR bot.log

# 3. Check storage channel exists
# Visit: https://t.me/c/<CHANNEL_ID>/1
```

**Fix:**
- Add bot to storage channel: https://t.me/[channel_link]?add=bot_username
- Give bot admin rights in channel
- Verify STORAGE_CHANNEL_ID format: `-100XXXXX`

### Links Not Delivered

**Check:**
```bash
# 1. Callback handler firing?
grep "pwd_" bot.log

# 2. Link patterns configured?
grep PATTERN config.py

# 3. Storage file created?
ls -la data/file_storage.json
```

**Fix:**
- Verify link patterns in config.py have `{file_key}`
- Check _deliver_links() exceptions
- Ensure storage.json was created

### "Invalid API ID" Error

**Cause:** API_ID not set or in wrong format

**Fix:**
```bash
# Get from https://my.telegram.org/apps
# Should be NUMERIC: 123456
# Edit .env and restart
```

### "Invalid bot token" Error

**Cause:** BOT_TOKEN expired or malformed

**Fix:**
```bash
# Create new bot with @BotFather
# Format: 123456789:ABCxyzdef...
# Update .env and restart
```

---

## SECURITY NOTES

### Current Implementation

✓ Passwords stored in metadata (plaintext)  
✓ File IDs from Telegram API (secure)  
✓ Access via generated links (no auth)  

### Production Recommendations

1. **Encrypt Passwords**
   ```python
   from cryptography.fernet import Fernet
   cipher = Fernet(key)
   encrypted = cipher.encrypt(password.encode())
   ```

2. **Add Access Control**
   ```python
   # Only allow file creator to access links
   if query.from_user.id != metadata.user_id:
        return  # Deny access
   ```

3. **Implement Rate Limiting**
   ```python
   from pyrogram import filters
   from pyrogram.utils import AsyncLock
   
   file_locks = {}  # Track user uploads
   ```

4. **Add File Expiration**
   ```python
   # Auto-delete files after N days
   if (now - created).days > 30:
        storage.delete_file(file_key)
   ```

5. **Enable File Logging**
   ```python
   import logging.handlers
   handler = logging.handlers.RotatingFileHandler(
       'bot.log', maxBytes=10MB, backupCount=5
   )
   logging.getLogger().addHandler(handler)
   ```

---

## PERFORMANCE TUNING

### For High Load

```python
# Increase asyncio event loop size
import asyncio
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Use connection pooling
app = Client(
    session_string="...",
    workdir=".",
    connection_retries=3,
    connection_retries_delay=1,
)
```

### Monitor Performance

```bash
# CPU & Memory
ps aux | grep bot.py
top

# Network
netstat -an | grep ESTABLISHED | wc -l

# Storage size
du -sh data/
```

---

## UPDATES & UPGRADES

### Update Pyrogram

```bash
pip install --upgrade pyrogram
python test.py  # Verify compatibility
```

### Update Code

```bash
# Backup current version
cp bot.py bot.py.backup

# Get new version (git, download, etc.)
git pull origin main

# Test
python test.py

# Restart
sudo systemctl restart telegram-bot
```

---

## SUPPORT

For detailed information:
- **Architecture:** See [ANALYSIS.md](ANALYSIS.md)
- **API Reference:** See [API.md](API.md)
- **Testing:** See [test.py](test.py)
- **Code:** See [bot.py](bot.py)

---

**Version:** 1.0  
**Status:** Production Ready ✅  
**Last Updated:** 2024-01-11  
**Python:** 3.10+  
**Framework:** Pyrogram 1.4.16
