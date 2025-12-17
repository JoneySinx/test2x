import logging
import os
import time
import asyncio
import uvloop
from aiohttp import web
from typing import Union, Optional, AsyncGenerator

from hydrogram import Client, types
from hydrogram.errors import FloodWait

from web import web_app
from info import (
    INDEX_CHANNELS, SUPPORT_GROUP, LOG_CHANNEL, API_ID, DATA_DATABASE_URL, 
    API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, 
    SECOND_FILES_DATABASE_URL, FILES_DATABASE_URL
)
from utils import temp, get_readable_time, check_premium
from database.users_chats_db import db

# Logging Configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('hydrogram').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Install uvloop
uvloop.install()

# =========================================================
# FIX: Manually create and set the Event Loop here
# This fixes the "There is no current event loop" error
# =========================================================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
# =========================================================

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        await super().start()
        temp.START_TIME = time.time()
        
        # Load banned users/chats from DB
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats

        # Restart Handling
        if os.path.exists('restart.txt'):
            try:
                with open("restart.txt") as file:
                    content = file.read().split()
                    if len(content) >= 2:
                        chat_id, msg_id = int(content[0]), int(content[1])
                        await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
            except Exception as e:
                logger.error(f"Failed to edit restart message: {e}")
            finally:
                if os.path.exists('restart.txt'):
                    os.remove('restart.txt')

        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        
        # Web Server Setup
        app = web.AppRunner(web_app)
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        # Start background task
        asyncio.create_task(check_premium(self))
        
        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>")
        except Exception:
            logger.error("Make sure bot admin is in LOG_CHANNEL, exiting now")
            # exit() 
        
        logger.info(f"@{me.username} is started now ✓")

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot Stopped! Bye...")

    async def iter_messages(self: Client, chat_id: Union[int, str], limit: int, offset: int = 0) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially."""
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            
            # Fetch messages in batch
            try:
                messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            except Exception:
                return

            for message in messages:
                # IMPORTANT: Check if message exists (not None/Empty) before yielding
                if message:
                    yield message
                    current += 1
                else:
                    # If message is deleted/empty, still increment current to move forward
                    current += 1

# Initialize Bot
app = Bot()
app.run()
