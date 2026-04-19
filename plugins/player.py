import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo

PLAYER_TIMEOUT = 1200
PLAYER_DB = {}


def get_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏮ Back", callback_data="player_prev"),
            InlineKeyboardButton("▶️ Next", callback_data="player_next")
        ],
        [
            InlineKeyboardButton("🔖 Bookmark", callback_data="player_bookmark")
        ]
    ])


async def delete_player(client, chat_id, msg_id, user_id):
    await asyncio.sleep(PLAYER_TIMEOUT)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

    PLAYER_DB.pop(user_id, None)


async def create_player(client, message, user_id, playlist):

    if user_id in PLAYER_DB:
        data = PLAYER_DB[user_id]
        if time() - data["time"] < PLAYER_TIMEOUT:
            return await message.reply(
                "⚠️ Player already active 👇",
                reply_to_message_id=data["msg_id"]
            )

    sent = await client.send_video(
        chat_id=message.chat.id,
        video=playlist[0],
        caption="🎬 Video Player\n\nUse buttons 👇",
        reply_markup=get_buttons()
    )

    PLAYER_DB[user_id] = {
        "msg_id": sent.id,
        "time": time(),
        "index": 0,
        "playlist": playlist
    }

    asyncio.create_task(delete_player(client, message.chat.id, sent.id, user_id))


# ===== SINGLE CALLBACK HANDLER (IMPORTANT) =====
@Client.on_callback_query(filters.regex("^player_"))
async def player_handler(client, query):
    await query.answer()

    user_id = query.from_user.id

    if user_id not in PLAYER_DB:
        return await query.answer("⚠️ Player expired!", show_alert=True)

    data = PLAYER_DB[user_id]
    playlist = data["playlist"]
    index = data["index"]

    if query.data == "player_next":
        index += 1
        if index >= len(playlist):
            index = 0

    elif query.data == "player_prev":
        index -= 1
        if index < 0:
            index = len(playlist) - 1

    elif query.data == "player_bookmark":
        file_id = playlist[index]

        await client.send_message(
            user_id,
            f"🔖 Bookmarked\n\n<code>{file_id}</code>"
        )

        return await query.answer("Saved ✅", show_alert=True)

    file_id = playlist[index]

    await client.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        media=InputMediaVideo(
            media=file_id,
            caption=f"🎬 Video Player\n\nVideo {index+1}/{len(playlist)}"
        ),
        reply_markup=get_buttons()
    )

    data["index"] = index
