from hydrogram import Client, filters
from hydrogram.errors import MessageTooLong
import sys
import os
import traceback
from io import StringIO
from info import ADMINS

@Client.on_message(filters.command("eval") & filters.user(ADMINS))
async def executor(client, message):
    try:
        # कोड को अलग किया
        code = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply('Command Incomplete!\nUsage: /eval print("hello")')
        
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    redirected_error = sys.stderr = StringIO()
    stdout, stderr, exc = None, None, None
    returned = None
    
    try:
        # aexec से return value भी अब कैप्चर होगी
        returned = await aexec(code, client, message)
    except Exception:
        exc = traceback.format_exc()
        
    stdout = redirected_output.getvalue()
    stderr = redirected_error.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr
    
    evaluation = ""
    if exc:
        evaluation = exc
    elif stderr:
        evaluation = stderr
    elif stdout:
        evaluation = stdout
    else:
        evaluation = "Success!"
        
    # अगर कोड ने कुछ return किया है तो उसे भी दिखाएं
    if returned:
        evaluation += f"\n\nReturned: {returned}"

    final_output = f"<b>Output:</b>\n<pre>{evaluation}</pre>"
    
    try:
        await message.reply(final_output)
    except MessageTooLong:
        # फाइल राइट करते समय utf-8 का उपयोग करें
        with open('eval.txt', 'w+', encoding='utf-8') as outfile:
            outfile.write(str(evaluation))
        await message.reply_document('eval.txt', caption="Evaluation Result")
        os.remove('eval.txt')

async def aexec(code, client, message):
    exec(
        "async def __aexec(client, message): "
        + "".join(f"\n {a}" for a in code.split("\n"))
    )
    return await locals()["__aexec"](client, message)
