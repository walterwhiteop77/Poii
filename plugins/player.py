import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
from database.users_db import db

PLAYER_TIMEOUT = 1200
PLAYER_DB = {}


# ===== BUTTONS =====
def buttons():
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
async def create_player(client, message, user_id):

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
        reply_markup=buttons()
    )

    PLAYER_DB[user_id] = {
        "msg_id": sent.id,
        "time": time(),
        "index": 0,
        "history": [video_id]
    }

    asyncio.create_task(delete_player(client, message.chat.id, sent.id, user_id))


# ===== MAIN HANDLER =====
@Client.on_callback_query(filters.regex("^player_"), group=0)
async def player_handler(client, query):
    await query.answer()

    user_id = query.from_user.id

    if user_id not in PLAYER_DB:
        return await query.answer("⚠️ Player expired!", show_alert=True)

    data = PLAYER_DB[user_id]

    # ===== NEXT =====
    if query.data == "player_next":

        attempts = 0
        new_video = None

        # try to get a new unique video
        while attempts < 5:
            vid = await db.get_random_video()

            if vid and vid not in data["history"]:
                new_video = vid
                break

            attempts += 1

        if not new_video:
            return await query.answer("⚠️ No new videos!", show_alert=True)

        data["history"].append(new_video)
        data["index"] += 1

        await db.increment_video_count(user_id)

    # ===== BACK =====
    elif query.data == "player_prev":

        if data["index"] <= 0:
            return await query.answer("⚠️ No previous video!", show_alert=True)

        data["index"] -= 1

    # ===== BOOKMARK =====
    elif query.data == "player_bookmark":

        vid = data["history"][data["index"]]

        await client.send_message(
            user_id,
            f"🔖 Bookmarked\n\n<code>{vid}</code>"
        )

        return await query.answer("Saved ✅", show_alert=True)

    # ===== CURRENT VIDEO =====
    vid = data["history"][data["index"]]

    await client.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.id,
        media=InputMediaVideo(
            media=vid,
            caption=f"🎬 Video Player\n\nVideo {data['index']+1}"
        ),
        reply_markup=buttons()
    )
