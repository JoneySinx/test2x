from hydrogram import Client, filters
from info import INDEX_CHANNELS, INDEX_EXTENSIONS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video

@Client.on_message(filters.chat(INDEX_CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    # मीडिया ऑब्जेक्ट निकालें (Video या Document)
    media = getattr(message, message.media.value, None)
    
    # चेक करें कि मीडिया और फाइल का नाम मौजूद है या नहीं
    if media and media.file_name:
        if str(media.file_name).lower().endswith(tuple(INDEX_EXTENSIONS)):
            # save_file फंक्शन के लिए कैप्शन को मीडिया ऑब्जेक्ट में जोड़ें
            media.caption = message.caption
            await save_file(media)
