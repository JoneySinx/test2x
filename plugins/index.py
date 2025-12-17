import re
import time
import asyncio
from hydrogram import Client, filters, enums
from hydrogram.errors import FloodWait
from info import ADMINS, INDEX_EXTENSIONS
from database.ia_filterdb import save_file
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp, get_readable_time

lock = asyncio.Lock()

# --- 1. HANDLE BUTTON CLICKS (CALLBACKS) ---
@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    # Data Format: index # Action # ChatID # LastMsgID # Skip
    _, ident, chat, lst_msg_id, skip = query.data.split("#")
    
    if ident == 'yes':
        # "START (No Skip)" clicked
        msg = query.message
        await msg.edit(f"<b>🔄 Initializing Indexing...</b>\n\nChannel ID: `{chat}`\nTotal Msgs: `{lst_msg_id}`\nSkip: `{skip}`")
        try:
            chat = int(chat)
        except:
            chat = chat
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip))
        
    elif ident == 'ask_skip':
        # "SET SKIP" clicked - Ask user for number
        await query.message.edit("🔢 **Send the amount of messages to skip:**\n\n(Send `0` to start from beginning)")
        try:
            # Wait for user reply
            response = await bot.listen(chat_id=query.message.chat.id, user_id=query.from_user.id, timeout=60)
            try:
                skip_no = int(response.text)
            except:
                await query.message.reply("❌ Invalid Number! Indexing Cancelled.")
                return
            
            # Start Indexing with custom skip
            await response.delete() # Delete user's number message
            msg = query.message
            await msg.edit(f"<b>🔄 Starting Indexing...</b>\n\nSkip: `{skip_no}`")
            
            try:
                chat = int(chat)
            except:
                chat = chat
                
            await index_files_to_db(int(lst_msg_id), chat, msg, bot, skip_no)
            
        except Exception as e:
            await query.message.edit("❌ Timeout or Error. Try again.")
            print(e)

    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("🛑 **Stopping Indexing... Please wait.**")


# --- 2. HANDLE FORWARDS & LINKS (AUTO DETECT) ---
@Client.on_message(filters.private & filters.user(ADMINS) & (filters.forwarded | (filters.text & filters.regex(r"https://t.me/"))))
async def auto_index_handler(bot, message):
    if lock.locked():
        return await message.reply('⚠️ Wait until previous process complete.')

    chat_id = None
    last_msg_id = 0

    # CASE A: If Message is a Link
    if message.text and message.text.startswith("https://t.me"):
        try:
            msg_link = message.text.split("/")
            last_msg_id = int(msg_link[-1])
            chat_id = msg_link[-2]
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        except:
            await message.reply('❌ Invalid message link!')
            return
            
    # CASE B: If Message is Forwarded from Channel
    elif message.forward_from_chat and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = message.forward_from_message_id
        chat_id = message.forward_from_chat.username or message.forward_from_chat.id
    
    else:
        # Ignore normal messages
        return

    # Verify Channel Access
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f'❌ Error: I cannot access this channel.\nMake sure I am Admin there.\nError: {e}')

    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("⚠️ I can index only channels.")

    # --- SMART BUTTONS ---
    buttons = [
        [
            InlineKeyboardButton('✅ START (No Skip)', callback_data=f'index#yes#{chat_id}#{last_msg_id}#0')
        ],
        [
            InlineKeyboardButton('⏭ SET SKIP (Custom)', callback_data=f'index#ask_skip#{chat_id}#{last_msg_id}#0')
        ],
        [
            InlineKeyboardButton('❌ CLOSE', callback_data='close_data')
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await message.reply(
        f"**🧐 Channel Detected:** `{chat.title}`\n"
        f"**🆔 ID:** `{chat.id}`\n"
        f"**📊 Total Messages:** `{last_msg_id}`\n\n"
        f"__Select an option to start indexing:__",
        reply_markup=reply_markup
    )


# --- 3. MAIN INDEXING FUNCTION (WITH ERROR HANDLING & LIVE UPDATE) ---
async def index_files_to_db(lst_msg_id, chat, msg, bot, skip):
    start_time = time.time()
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    badfiles = 0
    current = skip
    
    async with lock:
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, skip):
                time_taken = get_readable_time(time.time()-start_time)
                
                if temp.CANCEL:
                    temp.CANCEL = False
                    await msg.edit(f"✅ **Index Cancelled!**\n\nSaved: `{total_files}`\nDupes: `{duplicate}`\nTime: {time_taken}")
                    return
                
                current += 1
                
                # Live Update every 20 messages
                if current % 20 == 0:
                    btn = [[
                        InlineKeyboardButton('🛑 STOP INDEXING', callback_data=f'index#cancel#{chat}#{lst_msg_id}#{skip}')
                    ]]
                    try:
                        await msg.edit_text(
                            text=f"**🔄 Indexing in Progress...**\n\n"
                                 f"📥 **Read:** `{current}`\n"
                                 f"💾 **Saved:** `{total_files}`\n"
                                 f"♻️ **Dupes:** `{duplicate}`\n"
                                 f"⏱ **Time:** {time_taken}",
                            reply_markup=InlineKeyboardMarkup(btn)
                        )
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception:
                        pass
                
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                
                if not getattr(media, 'file_name', None):
                    unsupported += 1
                    continue

                if not (str(media.file_name).lower()).endswith(tuple(INDEX_EXTENSIONS)):
                    unsupported += 1
                    continue
                
                media.caption = message.caption
                file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
                
                sts = await save_file(media)
                if sts == 'suc':
                    total_files += 1
                elif sts == 'dup':
                    duplicate += 1
                elif sts == 'err':
                    errors += 1
                    
        except Exception as e:
            try:
                await msg.reply(f'❌ Indexing stopped due to Error: {e}')
            except:
                pass
        else:
            time_taken = get_readable_time(time.time()-start_time)
            try:
                await msg.edit(
                    f'✅ **Indexing Completed Successfully!**\n\n'
                    f'💾 **Total Saved:** `{total_files}`\n'
                    f'♻️ **Duplicates:** `{duplicate}`\n'
                    f'🗑 **Deleted/Skipped:** `{deleted + no_media + unsupported}`\n'
                    f'⏱ **Time Taken:** {time_taken}'
                )
            except Exception as e:
                # If editing fails (socket closed), try sending fresh message
                try:
                    await bot.send_message(
                        chat_id=msg.chat.id, 
                        text=f'✅ **Indexing Completed!**\nFiles Saved: `{total_files}`\n(Status update failed, but job is done)'
                    )
                except:
                    pass
