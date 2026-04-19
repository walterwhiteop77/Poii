import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
from database.users_db import db
from info import DAILY_LIMIT, PREMIUM_DAILY_LIMIT

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


async def create_player(client, message, user_id):

    # prevent multiple players
    if user_id in PLAYER_DB:
        data = PLAYER_DB[user_id]
        if time() - data["time"] < PLAYER_TIMEOUT:
            return await message.reply(
                "⚠️ Player already active 👇",
                reply_to_message_id=data["msg_id"]
            )

    video_id = await db.get_random_video()

    if not video_id:
        return await message.reply("❌ No videos found!")

    sent = await client.send_video(
        chat_id=message.chat.id,
        video=video_id,
        caption="🎬 Video Player\n\nVideo 1",
        reply_markup=get_buttons()
    )

    PLAYER_DB[user_id] = {
        "msg_id": sent.id,
        "time": time(),
        "index": 0,
        "history": [video_id]
    }

    asyncio.create_task(delete_player(client, message.chat.id, sent.id, user_id))


# ===== CALLBACK HANDLER =====
@Client.on_callback_query(filters.regex("^player_"))
async def player_handler(client, query):
    await query.answer()

    user_id = query.from_user.id

    if user_id not in PLAYER_DB:
        return await query.answer("⚠️ Player expired!", show_alert=True)

    data = PLAYER_DB[user_id]

    # ===== CHECK LIMIT =====
    is_premium = await db.has_premium_access(user_id)
    limit = PREMIUM_DAILY_LIMIT if is_premium else DAILY_LIMIT
    used = await db.get_video_count(user_id) or 0

    if used >= limit:
        return await query.answer(
            "❌ Daily limit reached!",
            show_alert=True
        )

    # ===== NEXT =====
    if query.data == "player_next":

        # fetch new video
        video_id = await db.get_random_video()

        if not video_id:
            return await query.answer("No more videos!", show_alert=True)

        data["history"].append(video_id)
        data["index"] += 1

        await db.increment_video_count(user_id)

    # ===== PREV =====
    elif query.data == "player_prev":

        if data["index"] == 0:
            return await query.answer("No previous video!", show_alert=True)

        data["index"] -= 1
        video_id = data["history"][data["index"]]

    # ===== BOOKMARK =====
    elif query.data == "player_bookmark":

        video_id = data["history"][data["index"]]

        await client.send_message(
            user_id,
            f"🔖 Bookmarked\n\n<code>{video_id}</code>"
        )

        return await query.answer("Saved ✅", show_alert=True)

    # current video
    video_id = data["history"][data["index"]]

    await client.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        media=InputMediaVideo(
            media=video_id,
            caption=f"🎬 Video Player\n\nVideo {data['index']+1}"
        ),
        reply_markup=get_buttons()
    )
