from hydrogram import Client, filters
from utils import temp
from hydrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from database.users_chats_db import db
from info import SUPPORT_LINK

# --- Custom Filters ---

async def banned_users(_, __, message: Message):
    # Check if user exists to avoid errors
    return (
        message.from_user is not None 
        and message.from_user.id in temp.BANNED_USERS
    )

banned_user = filters.create(banned_users)

async def disabled_chat(_, __, message: Message):
    return message.chat.id in temp.BANNED_CHATS

disabled_group = filters.create(disabled_chat)

# --- Handlers ---

@Client.on_message(filters.private & banned_user & filters.incoming)
async def is_user_banned(bot, message):
    buttons = [[
        InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    # Error handling added in case DB fails
    try:
        ban = await db.get_ban_status(message.from_user.id)
        reason = ban.get("ban_reason", "No reason provided")
    except Exception:
        reason = "No reason provided"

    await message.reply(
        f'Sorry {message.from_user.mention},\nMy owner banned you from using me! If you want to know more about it contact support group.\nReason - <code>{reason}</code>',
        reply_markup=reply_markup
    )

@Client.on_message(filters.group & disabled_group & filters.incoming)
async def is_group_disabled(bot, message):
    buttons = [[
        InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    try:
        vazha = await db.get_chat(message.chat.id)
        reason = vazha.get('reason', 'No reason provided')
    except Exception:
        reason = "No reason provided"

    k = await message.reply(
        text=f"<b><u>Chat Not Allowed</u></b>\n\nMy owner has restricted me from working here! If you want to know more about it contact support group.\nReason - <code>{reason}</code>",
        reply_markup=reply_markup
    )
    
    try:
        await k.pin()
    except:
        pass
    
    await bot.leave_chat(message.chat.id)
