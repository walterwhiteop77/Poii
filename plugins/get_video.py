from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from database.users_db import db
from info import PROTECT_CONTENT, DAILY_LIMIT, PREMIUM_DAILY_LIMIT, VERIFICATION_DAILY_LIMIT, FSUB, IS_VERIFY
from plugins.verification import av_x_verification
from plugins.ban_manager import ban_manager
from utils import temp, is_user_joined
from plugins.player import create_player


@Client.on_message(filters.command("getvideo") | filters.regex(r"(?i)get video"))
async def handle_video_request(client, m: Message):

    # Safety check
    if not m.from_user:
        return

    # Force subscribe check
    if FSUB and not await is_user_joined(client, m):
        return

    user_id = m.from_user.id

    # Ban check
    if await ban_manager.check_ban(client, m):
        return

    # Premium + limit info
    is_premium = await db.has_premium_access(user_id)
    current_limit = PREMIUM_DAILY_LIMIT if is_premium else DAILY_LIMIT
    used = await db.get_video_count(user_id) or 0

    # ---------------- LIMIT SYSTEM ---------------- #

    limit_reached_msg = (
        f"𝖸𝗈𝗎'𝗏𝖾 𝖱𝖾𝖺𝖼𝗁𝖾𝖽 𝖸𝗈𝗎𝗋 𝖣𝖺𝗂𝗅𝗒 𝖫𝗂𝗆𝗂𝗍 𝖮𝖿 {used} 𝖥𝗂𝗅𝖾𝗌.\n\n"
        "𝖳𝗋𝗒 𝖠𝗀𝖺𝗂𝗇 𝖳𝗈𝗆𝗈𝗋𝗋𝗈𝗐!\n"
        "𝖮𝗋 𝖯𝗎𝗋𝖼𝗁𝖺𝗌𝖾 𝖲𝗎𝖻𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇"
    )

    buy_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Buy Premium", callback_data="get")]
    ])

    if is_premium:
        if used >= PREMIUM_DAILY_LIMIT:
            return await m.reply(
                f"❌ Premium daily limit reached ({PREMIUM_DAILY_LIMIT})"
            )
    else:
        if used >= VERIFICATION_DAILY_LIMIT:
            return await m.reply(limit_reached_msg, reply_markup=buy_button)

        if used >= DAILY_LIMIT:
            if IS_VERIFY:
                verified = await av_x_verification(client, m)
                if not verified:
                    return
            else:
                return await m.reply(limit_reached_msg, reply_markup=buy_button)

    # ---------------- GET VIDEO ---------------- #

    video_id = await db.get_unseen_video(user_id)

    if not video_id:
        video_id = await db.get_random_video()

    if not video_id:
        return await m.reply("❌ No videos found!")

    # ---------------- PLAYER SYSTEM ---------------- #

    # create playlist (for now single video, can expand later)
    playlist = [video_id]

    await create_player(client, m, user_id, playlist)

    # ---------------- UPDATE COUNT ---------------- #

    await db.increment_video_count(user_id)
