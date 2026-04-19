import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaVideo
)

# ===== SETTINGS =====
PLAYER_TIMEOUT = 1200  # 20 minutes

# ===== MEMORY STORAGE =====
PLAYER_DB = {}


# ===== BUTTON UI =====
def get_player_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏮ Back", callback_data="player_prev"),
            InlineKeyboardButton("▶️ Next", callback_data="player_next")
        ],
        [
            InlineKeyboardButton("🔖 Bookmark", callback_data="player_bookmark")
        ]
    ])


# ===== AUTO DELETE =====
async def delete_player(client, chat_id, msg_id, user_id):
    await asyncio.sleep(PLAYER_TIMEOUT)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

    PLAYER_DB.pop(user_id, None)


# ===== CREATE PLAYER =====
async def create_player(client, message, user_id, playlist):

    # Check existing player
    if user_id in PLAYER_DB:
        data = PLAYER_DB[user_id]

        if time() - data["time"] < PLAYER_TIMEOUT:
            return await message.reply(
                "⚠️ You already have an active player!\n\nUse it 👇",
                reply_to_message_id=data["msg_id"]
            )

    # First video
    index = 0
    file_id = playlist[index]

    sent = await client.send_video(
        chat_id=message.chat.id,
        video=file_id,
        caption="🎬 <b>Video Player</b>\n\nUse buttons below 👇",
        reply_markup=get_player_buttons()
    )

    # Save player
    PLAYER_DB[user_id] = {
        "msg_id": sent.id,
        "time": time(),
        "index": index,
        "playlist": playlist
    }

    # Auto delete
    asyncio.create_task(delete_player(client, message.chat.id, sent.id, user_id))


# ===== NEXT =====
@Client.on_callback_query(filters.regex("player_next"))
async def next_video(client, query):
    user_id = query.from_user.id

    if user_id not in PLAYER_DB:
        return await query.answer("⚠️ Player expired!", show_alert=True)

    data = PLAYER_DB[user_id]

    playlist = data["playlist"]
    index = data["index"] + 1

    if index >= len(playlist):
        index = 0

    file_id = playlist[index]

    await client.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        media=InputMediaVideo(
            media=file_id,
            caption=f"🎬 <b>Video Player</b>\n\nVideo {index+1}/{len(playlist)}"
        ),
        reply_markup=get_player_buttons()
    )

    data["index"] = index


# ===== PREVIOUS =====
@Client.on_callback_query(filters.regex("player_prev"))
async def prev_video(client, query):
    user_id = query.from_user.id

    if user_id not in PLAYER_DB:
        return await query.answer("⚠️ Player expired!", show_alert=True)

    data = PLAYER_DB[user_id]

    playlist = data["playlist"]
    index = data["index"] - 1

    if index < 0:
        index = len(playlist) - 1

    file_id = playlist[index]

    await client.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        media=InputMediaVideo(
            media=file_id,
            caption=f"🎬 <b>Video Player</b>\n\nVideo {index+1}/{len(playlist)}"
        ),
        reply_markup=get_player_buttons()
    )

    data["index"] = index


# ===== BOOKMARK =====
@Client.on_callback_query(filters.regex("player_bookmark"))
async def bookmark(client, query):
    user_id = query.from_user.id

    if user_id not in PLAYER_DB:
        return await query.answer("⚠️ Player expired!", show_alert=True)

    data = PLAYER_DB[user_id]
    file_id = data["playlist"][data["index"]]

    await client.send_message(
        user_id,
        f"🔖 <b>Bookmarked Video</b>\n\n<code>{file_id}</code>"
    )

    await query.answer("Saved ✅", show_alert=True)
