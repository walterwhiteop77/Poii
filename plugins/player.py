import asyncio
from time import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
from database.users_db import db

PLAYER_TIMEOUT = 1200
PLAYER_DB = {}


def buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏮ Back", callback_data="player_prev"),
            InlineKeyboardButton("▶️ Next", callback_data="player_next")
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

    video_id = await db.get_random_video()

    if not video_id:
        return await message.reply("No videos found")

    sent = await client.send_video(
        chat_id=message.chat.id,
        video=video_id,
        caption="🎬 Video 1",
        reply_markup=buttons()
    )

    PLAYER_DB[user_id] = {
        "msg_id": sent.id,
        "chat_id": message.chat.id,
        "videos": [video_id],
        "index": 0,
        "time": time()
    }

    asyncio.create_task(delete_player(client, message.chat.id, sent.id, user_id))


@Client.on_callback_query(filters.regex("^player_"), group=0)
async def handler(client, query):
    await query.answer()

    user_id = query.from_user.id

    if user_id not in PLAYER_DB:
        return await query.answer("Expired", show_alert=True)

    data = PLAYER_DB[user_id]

    # ===== NEXT =====
    if query.data == "player_next":

        attempts = 0
        new_video = None

        while attempts < 5:
            vid = await db.get_random_video()

            # ensure new video
            if vid and vid not in data["videos"]:
                new_video = vid
                break

            attempts += 1

        if not new_video:
            return await query.answer("No new videos", show_alert=True)

        data["videos"].append(new_video)
        data["index"] += 1

        await db.increment_video_count(user_id)

    # ===== BACK =====
    elif query.data == "player_prev":

        if data["index"] == 0:
            return await query.answer("No previous", show_alert=True)

        data["index"] -= 1

    video_id = data["videos"][data["index"]]

    # 🔥 FORCE DIFFERENT CAPTION (IMPORTANT)
    caption = f"🎬 Video {data['index']+1} • {time()}"

    await client.edit_message_media(
        chat_id=data["chat_id"],
        message_id=data["msg_id"],
        media=InputMediaVideo(
            media=video_id,
            caption=caption
        ),
        reply_markup=buttons()
    )
