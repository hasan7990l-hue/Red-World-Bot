import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time, base64, threading, json, os, io, re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error as ID3Error
from PIL import Image

# ⚠️ للاختبار فقط
TELEGRAM_TOKEN = "8180650384:AAHX37rerimsZIWBEc71HleexJKWqSaSsZ0"
GROQ_API_KEY   = "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"

ADMIN_ID = 8456056018
FORCE_CHANNELS = ["@Eror_7", "@lb2_c"]
CHANNEL_NAME = "Red World"
CHANNEL_LINK = "https://t.me/Eror_7"
GROQ_MODEL = "qwen/qwen3-32b"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
DB_FILE, STATS_FILE = "user_channels.json", "stats.json"
audio_edit_state, pending_audio_merge, ad_builder_state, image_gen_state = {}, {}, {}, {}
audio_cache = {}

# ============================================================
#              ENGLISH MESSAGES (no emojis)
# ============================================================
MSGS = {
    "welcome": (
        "<b>RED WORLD GATE</b>\n"
        "────────────────────\n\n"
        "<blockquote>"
        "Welcome to <b>R W | Bot</b>\n"
        "A professional Telegram channel manager.\n\n"
        "AI text generation\n"
        "Auto scheduling and publishing\n"
        "Promotional ads with spoilers\n"
        "Audio copyright stamping"
        "</blockquote>\n\n"
        "<i>Select an option below to begin.</i>"
    ),
    "force_sub": (
        "<b>GATE CLOSED</b>\n"
        "────────────────────\n\n"
        "<blockquote>"
        "To enter <b>Red World</b>,\n"
        "join our channels first:\n\n"
        "<a href='https://t.me/Eror_7'>@Eror_7</a>\n"
        "<a href='https://t.me/lb2_c'>@lb2_c</a>"
        "</blockquote>\n\n"
        "<i>After joining, press verify.</i>"
    ),
    "control_panel": (
        "<b>CONTROL ROOM</b>\n"
        "────────────────────\n\n"
        "<blockquote>All systems ready.\n"
        "Choose your action below.</blockquote>"
    ),
    "verify_ok": (
        "<b>VERIFIED</b>\n\n"
        "<blockquote><b>Status:</b> Success\n"
        "<b>Channel:</b> {title}\n"
        "<b>Permissions:</b> Admin + can post.</blockquote>"
    ),
    "verify_fail": "<b>VERIFICATION FAILED</b>\n\n<blockquote>Bot is not admin or lacks posting rights.</blockquote>",
    "verify_error": "<b>UNEXPECTED ERROR</b>\n\n<blockquote>{error}</blockquote>",
    "verify_ask": "<b>CHANNEL ID REQUIRED</b>\n\n<blockquote>Send the channel username\nExample: <code>@Eror_7</code></blockquote>",
    "verifying": "<i>Checking channel...</i>",
    "text_preview": "<b>NEW MANUSCRIPT</b>\n────────────────────\n\n{text}",
    "text_before_publish": "<b>REVIEW BEFORE PUBLISH</b>\n\n{text}",
    "photo_preview": "<b>VISUAL SCENE</b>\n────────────────────\n\n{caption}",
    "photo_regenerated": "<b>VISUAL SCENE - NEW VERSION</b>\n\n{caption}",
    "audio_wait_cover": (
        "<b>AUDIO COPYRIGHT STAMP</b>\n"
        "────────────────────\n\n"
        "<blockquote>Step 1 of 2\n"
        "Send the cover image now.</blockquote>"
    ),
    "audio_wait_track": "<b>STEP 2 OF 2</b>\n\n<blockquote>Send the audio file now\nFormat: <code>MP3</code></blockquote>",
    "audio_done": "<b>STAMP COMPLETE</b>\n\n<blockquote>Audio and visual rights added.\nThe track is ready to publish.</blockquote>",
    "audio_ask_merge": "<b>ADD AUDIO TO POST</b>\n\n<blockquote>Send an MP3 file\nto merge with the current post.</blockquote>",
    "ad_q1": "<b>AD PROTOCOL - 1/6</b>\n\n<blockquote>Send the group name.</blockquote>",
    "ad_q2": "<b>AD PROTOCOL - 2/6</b>\n\n<blockquote>Select the group type.</blockquote>",
    "ad_q3": "<b>AD PROTOCOL - 3/6</b>\n\n<blockquote>Send the group link\nto extract its ID.</blockquote>",
    "ad_q4": "<b>AD PROTOCOL - 4/6</b>\n\n<blockquote>Send the owner username\nExample: <code>@user</code></blockquote>",
    "ad_q5": "<b>AD PROTOCOL - 5/6</b>\n\n<blockquote>Do you want to attach a channel username?</blockquote>",
    "ad_q5_input": "<b>CHANNEL USERNAME</b>\n\n<blockquote>Send the channel username\nExample: <code>@mychannel</code></blockquote>",
    "ad_q6": "<b>AD PROTOCOL - 6/6</b>\n\n<blockquote>Send the media (photo or video).</blockquote>",
    "ad_publish_ok": "<b>PUBLISHED</b>\n\n<blockquote>The ad is now live in Red World.</blockquote>",
    "schedule_ask": "<b>SCHEDULE PUBLISH</b>\n\n<blockquote>Send the number of minutes.\nExample: <code>30</code></blockquote>",
    "schedule_done": "<b>SCHEDULED</b>\n\n<blockquote>Will publish in {minutes} minutes.</blockquote>",
    "stats": (
        "<b>KINGDOM RECORD</b>\n"
        "────────────────────\n\n"
        "<blockquote><b>Channel:</b> {title}\n"
        "<b>Subscribers:</b> {members}\n"
        "<b>Posts:</b> {posts}</blockquote>"
    ),
    "not_verified": "<b>ACCESS DENIED</b>\n\n<blockquote>Verify the bot upload first.</blockquote>",
    "channel_unlinked": "<b>CHANNEL NOT LINKED</b>\n\n<blockquote>Open the upload check first.</blockquote>",
    "expired": "<i>This action has expired.</i>",
    "left_channel": "<b>UNLINKED</b>\n\n<blockquote>You are no longer linked to any channel.</blockquote>",
    "no_channel": "<i>No channel linked.</i>",
    "status_on": "Publishing is ON",
    "status_off": "Publishing is OFF",
    "text_mode_on": "Text mode is ON",
    "text_mode_off": "Text mode is OFF",
    "lang_updated": "<b>LANGUAGE UPDATED</b>",
    "cat_updated": "<b>CATEGORY UPDATED</b>",
}

# ============================================================
#         INSTRUCTIONS FOR EACH BUTTON (shown as alerts)
# ============================================================
INSTRUCTIONS = {
    "toggle_status": "Toggle automatic publishing ON or OFF for your channel.",
    "toggle_text_mode": "When ON, any text you send is converted to an AI phrase and published.",
    "menu_categories": "Choose the style of generated phrases: sad, optimistic, philosophical, or mysterious.",
    "menu_lang": "Choose the output language: Arabic, English, or mixed.",
    "generate_long_text": "Generate a detailed 3-4 line phrase with AI.",
    "generate_short_text": "Generate a very short one-line phrase with AI.",
    "start_ad_builder": "Build a promotional ad with group ID, AI caption, group link button, and owner button.",
    "start_audio_edit": "Add copyright cover art and artist info to an MP3 file.",
    "show_stats": "View subscribers count and total published posts.",
    "show_source": "View the bot developer card with channel info.",
    "leave_channel": "Unlink your channel from this bot.",
    "verify_channel": "Verify that the bot is admin in your channel with posting rights.",
}

# ============================================================
#                    HELPERS
# ============================================================
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

user_channels = load_json(DB_FILE)
stats = load_json(STATS_FILE)
if "published_count" not in stats: stats["published_count"] = 0

def get_default_settings():
    return {"status": "ON", "text_only_mode": False, "category": "philosophical",
            "language": "English", "add_hashtags": True,
            "hashtags": "#RedWorld #Red_World"}

user_settings, generated_texts, pending_posts, saved_images = {}, {}, {}, {}

def convert_to_jpg(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((200, 200))
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=75)
        return output.getvalue()
    except: return image_bytes

def rebuild_audio_with_cover(original_audio_bytes, cover_bytes):
    try:
        audio_buffer = io.BytesIO(original_audio_bytes)
        audio = MP3(audio_buffer, ID3=ID3)
        try: audio.delete()
        except ID3Error: pass
        audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text="Red World"))
        audio.tags.add(TPE1(encoding=3, text="@Eror_7"))
        cover_data_jpg = convert_to_jpg(cover_bytes)
        audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data_jpg))
        audio.save(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.getvalue(), cover_data_jpg
    except Exception as e:
        print("rebuild audio error:", e)
        return original_audio_bytes, cover_bytes

def apply_formatting(raw_text, flags):
    text = raw_text
    if flags.get("bold"): text = f"<b>{text}</b>"
    if flags.get("italic"): text = f"<i>{text}</i>"
    if flags.get("strike"): text = f"<s>{text}</s>"
    if flags.get("quote"): text = f"<blockquote>{text}</blockquote>"
    return text

def extract_group_id(link):
    """Extract group ID from a Telegram invite link (returns the invite hash or username)"""
    link = link.strip()
    m = re.search(r'(?:t\.me/|telegram\.me/)(?:\+)?([A-Za-z0-9_-]+)', link)
    return m.group(1) if m else link

def check_subscription(user_id):
    for channel in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def send_force_sub_message(chat_id):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Join First Channel", url="https://t.me/Eror_7"),
        InlineKeyboardButton("Join Second Channel", url="https://t.me/lb2_c"),
        InlineKeyboardButton("Verify Subscription", callback_data="check_sub"))
    bot.send_message(chat_id, MSGS["force_sub"], reply_markup=markup, parse_mode='HTML')

def notify_instruction(call):
    """Show instruction as a toast alert on top of chat"""
    if call.data in INSTRUCTIONS:
        bot.answer_callback_query(call.id, INSTRUCTIONS[call.data])

# ============================================================
#                    BASIC COMMANDS
# ============================================================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID and not check_subscription(user_id):
        return send_force_sub_message(message.chat.id)
    if user_id not in user_settings: user_settings[user_id] = get_default_settings()
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("1. Add bot to your channel (admin)", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
        InlineKeyboardButton("2. Verify upload (auto check)", callback_data="verify_channel"),
        InlineKeyboardButton("Developer", url=f"tg://user?id={ADMIN_ID}"))
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("Open Control Panel", callback_data="main_menu"))
    bot.send_message(message.chat.id, MSGS["welcome"], reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "Verified. Welcome.", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "You have not joined all channels yet.", show_alert=True)

# ============================================================
#                    UPLOAD VERIFY
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    notify_instruction(call)
    channel_id = user_channels.get(str(call.from_user.id))
    if not channel_id:
        msg = bot.send_message(call.message.chat.id, MSGS["verify_ask"], parse_mode='HTML')
        bot.register_next_step_handler(msg, manual_verify, call.from_user.id)
    else:
        perform_verification(call.message.chat.id, call.from_user.id, channel_id)

def manual_verify(message, user_id):
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    user_channels[str(user_id)] = channel_input
    save_json(DB_FILE, user_channels)
    perform_verification(message.chat.id, user_id, channel_input)

def perform_verification(chat_id, user_id, channel_id):
    msg_loading = bot.send_message(chat_id, MSGS["verifying"], parse_mode='HTML')
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        if bot_member.status in ['administrator', 'creator'] and getattr(bot_member, 'can_post_messages', False):
            success_text = MSGS["verify_ok"].format(title=chat_info.title)
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Open Control Panel", callback_data="main_menu"))
            bot.edit_message_text(success_text, chat_id=chat_id, message_id=msg_loading.message_id, reply_markup=markup, parse_mode='HTML')
        else:
            bot.edit_message_text(MSGS["verify_fail"], chat_id=chat_id, message_id=msg_loading.message_id, parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(MSGS["verify_error"].format(error=e), chat_id=chat_id, message_id=msg_loading.message_id, parse_mode='HTML')

@bot.my_chat_member_handler()
def bot_added_to_channel(update: telebot.types.ChatMemberUpdated):
    new_status = update.new_chat_member.status
    if new_status in ('administrator', 'member') and update.chat.type == 'channel':
        adder_id = update.from_user.id
        channel_identifier = f"@{update.chat.username}" if update.chat.username else str(update.chat.id)
        user_channels[str(adder_id)] = channel_identifier
        save_json(DB_FILE, user_channels)
        try:
            bot.send_message(adder_id, f"Bot added to: {update.chat.title}\nPlease press Verify Upload.", parse_mode='HTML')
        except: pass
            # ============================================================
#                    CONTROL PANEL
# ============================================================
def get_main_panel(user_id):
    settings = user_settings.get(user_id, get_default_settings())
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Publishing OFF" if settings["status"] == "ON" else "Publishing ON", callback_data="toggle_status"),
        InlineKeyboardButton("Text Mode OFF" if settings["text_only_mode"] else "Text Mode ON", callback_data="toggle_text_mode"),
        InlineKeyboardButton("Phrase Categories", callback_data="menu_categories"),
        InlineKeyboardButton(f"Language: {settings['language']}", callback_data="menu_lang"),
        InlineKeyboardButton("Long Phrases", callback_data="generate_long_text"),
        InlineKeyboardButton("Short Phrases", callback_data="generate_short_text"),
        InlineKeyboardButton("Create Promo Ad", callback_data="start_ad_builder"),
        InlineKeyboardButton("Audio Copyright", callback_data="start_audio_edit"),
        InlineKeyboardButton("Weekly Report", callback_data="show_stats"),
        InlineKeyboardButton("Source", callback_data="show_source"),
        InlineKeyboardButton("Leave Channel", callback_data="leave_channel"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    bot.answer_callback_query(call.id, "Control Room opened.")
    try:
        bot.edit_message_text(MSGS["control_panel"], chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    except:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "toggle_status")
def toggle_status(call):
    notify_instruction(call)
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["status"] = "OFF" if settings["status"] == "ON" else "ON"
    user_settings[call.from_user.id] = settings
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=get_main_panel(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "toggle_text_mode")
def toggle_text_mode(call):
    notify_instruction(call)
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["text_only_mode"] = not settings["text_only_mode"]
    user_settings[call.from_user.id] = settings
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=get_main_panel(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "menu_lang")
def menu_lang(call):
    notify_instruction(call)
    markup = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("Arabic", callback_data="lang_Arabic"),
        InlineKeyboardButton("English", callback_data="lang_English"),
        InlineKeyboardButton("Mixed", callback_data="lang_Mixed"),
        InlineKeyboardButton("Back", callback_data="main_menu"))
    bot.edit_message_text("<b>Choose language:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["language"] = call.data.replace("lang_", "")
    user_settings[call.from_user.id] = settings
    bot.answer_callback_query(call.id, f"Language set to {settings['language']}", show_alert=True)
    bot.edit_message_text(MSGS["lang_updated"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "menu_categories")
def menu_categories(call):
    notify_instruction(call)
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("Sad", callback_data="cat_sad"),
        InlineKeyboardButton("Optimistic", callback_data="cat_optimistic"),
        InlineKeyboardButton("Philosophical", callback_data="cat_philosophical"),
        InlineKeyboardButton("Mysterious", callback_data="cat_mysterious"),
        InlineKeyboardButton("Back", callback_data="main_menu"))
    bot.edit_message_text("<b>Choose category:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def set_cat(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["category"] = call.data.replace("cat_", "")
    user_settings[call.from_user.id] = settings
    bot.answer_callback_query(call.id, f"Category: {settings['category']}", show_alert=True)
    bot.edit_message_text(MSGS["cat_updated"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

# ============================================================
#                    TEXT GENERATION
# ============================================================
def build_lang_instruction(language):
    if language == "Mixed":
        return "one short Arabic sentence then its English translation on the next line"
    return f"in {language} language"

@bot.callback_query_handler(func=lambda call: call.data in ["generate_long_text", "generate_short_text"])
def generate_text(call):
    notify_instruction(call)
    settings = user_settings.get(call.from_user.id, get_default_settings())
    bot.answer_callback_query(call.id, "Generating...")
    lang_instr = build_lang_instruction(settings['language'])
    length = "detailed 3-4 line phrase" if call.data == 'generate_long_text' else "very short one-line phrase"
    prompt = f"Write a {length} in {settings['category']} style ({lang_instr}). No emojis, no asterisks, no quotes."
    try:
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL, max_tokens=500)
        raw_text = res.choices[0].message.content.strip()
        msg_id = str(int(time.time()))
        generated_texts[msg_id] = {"raw": raw_text, "bold": False, "italic": False,
                                   "strike": False, "quote": False,
                                   "chat_id": call.message.chat.id}
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_formatting_panel(call.message.chat.id, msg_id)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {e}")

def send_formatting_panel(chat_id, msg_id):
    data = generated_texts[msg_id]
    text = apply_formatting(data["raw"], data)
    markup = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("Bold [ON]" if data["bold"] else "Bold", callback_data=f"fmt_bold_{msg_id}"),
        InlineKeyboardButton("Italic [ON]" if data["italic"] else "Italic", callback_data=f"fmt_italic_{msg_id}"),
        InlineKeyboardButton("Strike [ON]" if data["strike"] else "Strike", callback_data=f"fmt_strike_{msg_id}"),
        InlineKeyboardButton("Quote [ON]" if data["quote"] else "Quote", callback_data=f"fmt_quote_{msg_id}"),
        InlineKeyboardButton("Publish to Channel", callback_data=f"fmt_publish_{msg_id}"),
        InlineKeyboardButton("Cancel", callback_data=f"fmt_cancel_{msg_id}"))
    bot.send_message(chat_id, MSGS["text_preview"].format(text=text), reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('fmt_'))
def formatting_handler(call):
    parts = call.data.split('_')
    action, msg_id = parts[1], parts[2]
    if msg_id not in generated_texts: return
    data = generated_texts[msg_id]
    if action == "cancel":
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        del generated_texts[msg_id]
        bot.answer_callback_query(call.id, "Cancelled.")
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    elif action == "publish":
        text = apply_formatting(data["raw"], data)
        target_channel = user_channels.get(str(call.from_user.id))
        if not target_channel:
            return bot.answer_callback_query(call.id, "Channel not linked.", show_alert=True)
        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'text', 'caption': text, 'channel': target_channel}
        markup = InlineKeyboardMarkup(row_width=3).add(
            InlineKeyboardButton("Publish Now", callback_data=f"confirm_{post_id}"),
            InlineKeyboardButton("Schedule", callback_data=f"schedule_{post_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"cancel_{post_id}"))
        bot.answer_callback_query(call.id, "Ready to publish.")
        bot.edit_message_text(MSGS["text_before_publish"].format(text=text),
                              chat_id=call.message.chat.id, message_id=call.message.message_id,
                              reply_markup=markup, parse_mode='HTML')
    else:
        if action == "bold": data["bold"] = not data["bold"]
        elif action == "italic": data["italic"] = not data["italic"]
        elif action == "strike": data["strike"] = not data["strike"]
        elif action == "quote": data["quote"] = not data["quote"]
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_formatting_panel(call.message.chat.id, msg_id)
        bot.answer_callback_query(call.id)

# ============================================================
#       FIXED: IMAGE UPLOAD + SHORT PHRASE GENERATION
# ============================================================
def process_image_for_generation(message, is_regen=False):
    """Unified image handling that works for both first-time and regen"""
    uid = message.from_user.id if not is_regen else message
    settings = user_settings.get(uid, get_default_settings())
    # ... (handled inline below)
    # ============================================================
#       FIXED: IMAGE + SHORT PHRASE
# ============================================================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.from_user.id
    # Audio cover stage
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_cover':
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            audio_edit_state[uid]['cover_data'] = bot.download_file(file_info.file_path)
            audio_edit_state[uid]['step'] = 'waiting_for_audio'
            bot.send_message(message.chat.id, MSGS["audio_wait_track"], parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"Cover download failed: {e}")
        return
    # Ad builder media stage
    if uid in ad_builder_state and ad_builder_state[uid]['step'] == 'waiting_media':
        ad_builder_state[uid]['media_file_id'] = message.photo[-1].file_id
        ad_builder_state[uid]['media_type'] = 'photo'
        return finish_ad_preview(message.chat.id, uid)
    # Block if in another flow
    if uid in ad_builder_state or uid in audio_edit_state:
        return
    # Access check
    if uid != ADMIN_ID and str(uid) not in user_channels:
        return bot.send_message(message.chat.id, MSGS["not_verified"],
                                reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Verify", callback_data="verify_channel")),
                                parse_mode='HTML')
    settings = user_settings.get(uid, get_default_settings())
    if settings["status"] == "OFF":
        return bot.send_message(message.chat.id, "Publishing is OFF.",
                                reply_markup=get_main_panel(uid), parse_mode='HTML')
    msg_loading = bot.send_message(message.chat.id, "<i>Analyzing image...</i>", parse_mode='HTML')
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        photo_bytes = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        lang_instr = build_lang_instruction(settings['language'])
        prompt = f"Write a very short one-line caption in {settings['category']} style ({lang_instr}). No emojis, no asterisks."
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model=GROQ_MODEL, max_tokens=300)
        ai_text = res.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>\n\n{settings['hashtags']}" if settings["add_hashtags"] else f"<b>{ai_text}</b>"
        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'photo', 'file_id': message.photo[-1].file_id,
                                   'caption': final_caption, 'channel': user_channels.get(str(uid))}
        saved_images[post_id] = {'photo_id': message.photo[-1].file_id, 'user_id': uid,
                                  'settings': settings, 'channel': user_channels.get(str(uid))}
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("Publish Now", callback_data=f"confirm_{post_id}"),
            InlineKeyboardButton("Schedule", callback_data=f"schedule_{post_id}"),
            InlineKeyboardButton("Change Phrase", callback_data=f"regen_image_{post_id}"),
            InlineKeyboardButton("Add Audio", callback_data=f"add_audio_to_post_{post_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"cancel_{post_id}"))
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id,
                       caption=MSGS["photo_preview"].format(caption=final_caption),
                       reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_message(message.chat.id, f"Error: {e}", reply_markup=get_main_panel(uid))

# ============================================================
#                    AUDIO COPYRIGHT (FIXED)
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    notify_instruction(call)
    audio_edit_state[call.from_user.id] = {'step': 'waiting_for_cover'}
    bot.edit_message_text(MSGS["audio_wait_cover"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    uid = message.from_user.id
    # Audio merge into photo post
    if uid in pending_audio_merge:
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg':
            file_id = message.document.file_id
        if not file_id: return bot.reply_to(message, "Send MP3 only.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, b'')
            pending_audio_merge[uid]['audio_data'] = rebuilt
            pending_audio_merge[uid]['cover'] = cover_jpg
            data = pending_audio_merge[uid]
            bot.send_photo(data['channel'], data['photo_id'], caption=data['caption'],
                           parse_mode='HTML')
            bot.send_audio(data['channel'], io.BytesIO(rebuilt),
                           title="Red World", performer="@Eror_7", thumb=cover_jpg)
            del pending_audio_merge[uid]
            bot.send_message(message.chat.id, "Posted photo + audio.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Error: {e}")
        return
    # Audio copyright stage
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_audio':
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg':
            file_id = message.document.file_id
        if not file_id: return bot.reply_to(message, "Send MP3 only.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            cover_data = audio_edit_state[uid].get('cover_data', b'')
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data)
            audio_cache[uid] = {'data': rebuilt, 'cover': cover_jpg}
            markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(CHANNEL_NAME, url=CHANNEL_LINK),
                InlineKeyboardButton("Publish to Channel", callback_data=f"publish_standalone_audio_{uid}"))
            bot.send_audio(message.chat.id, io.BytesIO(rebuilt),
                           title="Red World", performer="@Eror_7", thumb=cover_jpg)
            bot.send_message(message.chat.id, MSGS["audio_done"], reply_markup=markup, parse_mode='HTML')
            audio_edit_state[uid]['step'] = 'ready'
        except Exception as e:
            bot.send_message(message.chat.id, f"Error: {e}")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_standalone_audio_"))
def publish_standalone_audio(call):
    uid = int(call.data.split("_")[3])
    target_channel = user_channels.get(str(uid))
    if not target_channel:
        return bot.answer_callback_query(call.id, "Channel not linked.", show_alert=True)
    if uid not in audio_cache:
        return bot.answer_callback_query(call.id, "Expired.", show_alert=True)
    try:
        cached = audio_cache[uid]
        bot.send_audio(target_channel, io.BytesIO(cached['data']),
                       title="Red World", performer="@Eror_7", thumb=cached['cover'])
        stats["published_count"] += 1; save_json(STATS_FILE, stats)
        bot.answer_callback_query(call.id, "Published successfully.", show_alert=True)
        if uid in audio_edit_state: del audio_edit_state[uid]
        if uid in audio_cache: del audio_cache[uid]
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(uid), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_audio_to_post_"))
def add_audio_to_post(call):
    post_id = call.data.split("_")[4]
    if post_id not in pending_posts:
        return bot.answer_callback_query(call.id, "Expired.", show_alert=True)
    pending_audio_merge[call.from_user.id] = {
        'post_id': post_id,
        'photo_id': pending_posts[post_id]['file_id'],
        'caption': pending_posts[post_id]['caption'],
        'channel': pending_posts[post_id]['channel']}
    bot.answer_callback_query(call.id, "Send MP3 to merge.")
    bot.edit_message_caption(MSGS["audio_ask_merge"], chat_id=call.message.chat.id,
                             message_id=call.message.message_id, parse_mode='HTML')

# ============================================================
#     AD BUILDER - NEW FLOW WITH GROUP ID + LINK BUTTONS
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    notify_instruction(call)
    ad_builder_state[call.from_user.id] = {
        'step': 'waiting_group_name',
        'group_name': None, 'group_type': None,
        'group_link': None, 'group_id': None,
        'owner_username': None, 'channel_username': None,
        'media_file_id': None, 'media_type': None,
        'language': 'English'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Cancel", callback_data="ad_cancel"))
    bot.edit_message_text(MSGS["ad_q1"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_cancel")
def ad_cancel(call):
    if call.from_user.id in ad_builder_state: del ad_builder_state[call.from_user.id]
    bot.answer_callback_query(call.id, "Cancelled.")
    bot.send_message(call.message.chat.id, MSGS["control_panel"],
                     reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

@bot.message_handler(func=lambda m: m.from_user.id in ad_builder_state)
def ad_step_handler(message):
    uid = message.from_user.id
    data = ad_builder_state[uid]
    step = data['step']

    if step == 'waiting_group_name':
        data['group_name'] = message.text.strip()
        data['step'] = 'waiting_group_type'
        markup = InlineKeyboardMarkup(row_width=3).add(
            InlineKeyboardButton("Public", callback_data="ad_type_public"),
            InlineKeyboardButton("Private", callback_data="ad_type_private"),
            InlineKeyboardButton("Mixed", callback_data="ad_type_mixed"))
        bot.send_message(message.chat.id, MSGS["ad_q2"], reply_markup=markup, parse_mode='HTML')

    elif step == 'waiting_group_link':
        data['group_link'] = message.text.strip()
        data['group_id'] = extract_group_id(data['group_link'])
        data['step'] = 'waiting_owner'
        bot.send_message(message.chat.id, MSGS["ad_q4"], parse_mode='HTML')

    elif step == 'waiting_owner':
        data['owner_username'] = message.text.strip()
        data['step'] = 'waiting_channel_choice'
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("Yes", callback_data="ad_ch_yes"),
            InlineKeyboardButton("No", callback_data="ad_ch_no"))
        bot.send_message(message.chat.id, MSGS["ad_q5"], reply_markup=markup, parse_mode='HTML')

    elif step == 'waiting_channel_username':
        uname = message.text.strip()
        if not uname.startswith('@'): uname = '@' + uname
        data['channel_username'] = uname
        data['step'] = 'waiting_language'
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("Arabic", callback_data="ad_lang_Arabic"),
            InlineKeyboardButton("English", callback_data="ad_lang_English"))
        bot.send_message(message.chat.id, "<b>Choose ad language:</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_set_type(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[uid]['step'] = 'waiting_group_link'
    bot.answer_callback_query(call.id, f"Type: {ad_builder_state[uid]['group_type']}")
    bot.edit_message_text(MSGS["ad_q3"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_ch_yes")
def ad_ch_yes(call):
    if call.from_user.id not in ad_builder_state: return
    ad_builder_state[call.from_user.id]['step'] = 'waiting_channel_username'
    bot.answer_callback_query(call.id)
    bot.edit_message_text(MSGS["ad_q5_input"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_ch_no")
def ad_ch_no(call):
    if call.from_user.id not in ad_builder_state: return
    ad_builder_state[call.from_user.id]['channel_username'] = None
    ad_builder_state[call.from_user.id]['step'] = 'waiting_language'
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("Arabic", callback_data="ad_lang_Arabic"),
        InlineKeyboardButton("English", callback_data="ad_lang_English"))
    bot.answer_callback_query(call.id)
    bot.edit_message_text("<b>Choose ad language:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_lang_"))
def ad_set_lang(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['language'] = call.data.replace("ad_lang_", "")
    ad_builder_state[uid]['step'] = 'waiting_media'
    bot.answer_callback_query(call.id, f"Language: {ad_builder_state[uid]['language']}")
    bot.edit_message_text(MSGS["ad_q6"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode='HTML')

def finish_ad_preview(chat_id, uid):
    data = ad_builder_state[uid]
    lang = data['language']
    prompt = (
        f"Write a short promotional Telegram ad in {lang} language.\n"
        f"Group name: {data['group_name']}\n"
        f"Group type: {data['group_type']}\n"
        f"Owner: {data['owner_username']}\n"
        "No emojis, no asterisks. Keep it elegant and inviting."
    )
    try:
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL, max_tokens=400)
        body = res.choices[0].message.content.strip().replace("**", "").replace("*", "")
    except Exception as e:
        body = f"{data['group_name']} - {data['group_type']}"

    # Build final caption with all required elements
    caption_parts = [
        f"<b>{data['group_name']}</b>",
        f"<i>{body}</i>",
        "",
        f"<b>Group ID:</b> <code>{data['group_id']}</code>",
        f"<b>Owner:</b> {data['owner_username']}",
    ]
    if data.get('channel_username'):
        caption_parts.append(f"<b>Channel:</b> {data['channel_username']}")
    caption = "\n".join(caption_parts)

    # Buttons: group link + owner
    markup = InlineKeyboardMarkup(row_width=1)
    if data.get('group_link'):
        markup.add(InlineKeyboardButton(f"Join {data['group_name']}", url=data['group_link']))
    owner_clean = data['owner_username'].lstrip('@')
    markup.add(InlineKeyboardButton(f"Owner: {data['owner_username']}", url=f"https://t.me/{owner_clean}"))
    markup.add(InlineKeyboardButton("Confirm Publish", callback_data="ad_confirm_publish"))

    data['final_caption'] = caption
    data['final_markup'] = markup

    if data.get('media_file_id') and data['media_type'] == 'photo':
        bot.send_photo(chat_id, data['media_file_id'], caption=caption,
                       reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, caption, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(content_types=['video'])
def handle_video(message):
    uid = message.from_user.id
    if uid in ad_builder_state and ad_builder_state[uid]['step'] == 'waiting_media':
        ad_builder_state[uid]['media_file_id'] = message.video.file_id
        ad_builder_state[uid]['media_type'] = 'video'
        return finish_ad_preview(message.chat.id, uid)

@bot.callback_query_handler(func=lambda call: call.data == "ad_confirm_publish")
def ad_confirm_publish(call):
    uid = call.from_user.id
    if uid not in ad_builder_state:
        return bot.answer_callback_query(call.id, "Expired.", show_alert=True)
    target_channel = user_channels.get(str(uid))
    if not target_channel:
        return bot.answer_callback_query(call.id, "Channel not linked.", show_alert=True)
    data = ad_builder_state[uid]
    try:
        if data.get('media_file_id') and data['media_type'] == 'photo':
            bot.send_photo(target_channel, data['media_file_id'],
                           caption=data['final_caption'], reply_markup=data['final_markup'],
                           parse_mode='HTML')
        elif data.get('media_file_id') and data['media_type'] == 'video':
            bot.send_video(target_channel, data['media_file_id'],
                           caption=data['final_caption'], reply_markup=data['final_markup'],
                           parse_mode='HTML')
        else:
            bot.send_message(target_channel, data['final_caption'],
                             reply_markup=data['final_markup'], parse_mode='HTML')
        stats["published_count"] += 1; save_json(STATS_FILE, stats)
        bot.answer_callback_query(call.id, "Published.", show_alert=True)
        del ad_builder_state[uid]
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(uid), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)

# ============================================================
#                    SCHEDULE + CONFIRM
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_"))
def schedule(call):
    post_id = call.data.split("_")[1]
    bot.answer_callback_query(call.id, "Send minutes.")
    msg = bot.send_message(call.message.chat.id, MSGS["schedule_ask"], parse_mode='HTML')
    bot.register_next_step_handler(msg, execute_schedule, post_id)

def execute_schedule(message, post_id):
    try:
        minutes = int(message.text.strip())
        if post_id not in pending_posts:
            return bot.send_message(message.chat.id, MSGS["expired"], parse_mode='HTML')
        data = pending_posts[post_id]
        def do_publish():
            try:
                if data['type'] == 'photo':
                    bot.send_photo(data['channel'], data['file_id'], caption=data['caption'], parse_mode='HTML')
                else:
                    bot.send_message(data['channel'], data['caption'], parse_mode='HTML')
                stats["published_count"] += 1; save_json(STATS_FILE, stats)
            except Exception as e:
                print("schedule publish error:", e)
        timer = threading.Timer(minutes * 60, do_publish); timer.daemon = True; timer.start()
        bot.send_message(message.chat.id, MSGS["schedule_done"].format(minutes=minutes), parse_mode='HTML')
        del pending_posts[post_id]
    except ValueError:
        bot.send_message(message.chat.id, "Send a valid number.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_post(call):
    post_id = call.data.split("_")[1]
    if post_id not in pending_posts:
        return bot.answer_callback_query(call.id, "Expired.")
    data = pending_posts[post_id]
    try:
        if data['type'] == 'photo':
            bot.send_photo(data['channel'], data['file_id'], caption=data['caption'], parse_mode='HTML')
        else:
            bot.send_message(data['channel'], data['caption'], parse_mode='HTML')
        stats["published_count"] += 1; save_json(STATS_FILE, stats)
        bot.answer_callback_query(call.id, "Published.", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
        del pending_posts[post_id]
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel_post(call):
    post_id = call.data.split("_")[1]
    if post_id in pending_posts: del pending_posts[post_id]
    bot.answer_callback_query(call.id, "Cancelled.")
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, MSGS["control_panel"],
                     reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("regen_image_"))
def regen_image(call):
    post_id = call.data.split("_")[2]
    if post_id not in saved_images:
        return bot.answer_callback_query(call.id, "Expired.", show_alert=True)
    data = saved_images[post_id]
    try:
        file_info = bot.get_file(data['photo_id'])
        base64_image = base64.b64encode(bot.download_file(file_info.file_path)).decode('utf-8')
        lang_instr = build_lang_instruction(data['settings']['language'])
        prompt = f"Write a very short one-line caption in {data['settings']['category']} style ({lang_instr}). No emojis."
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model=GROQ_MODEL, max_tokens=300)
        ai_text = res.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>\n\n{data['settings']['hashtags']}" if data['settings']['add_hashtags'] else f"<b>{ai_text}</b>"
        new_post_id = str(int(time.time()))
        pending_posts[new_post_id] = {'type': 'photo', 'file_id': data['photo_id'],
                                       'caption': final_caption, 'channel': data['channel']}
        saved_images[new_post_id] = data
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("Publish Now", callback_data=f"confirm_{new_post_id}"),
            InlineKeyboardButton("Schedule", callback_data=f"schedule_{new_post_id}"),
            InlineKeyboardButton("Change Phrase", callback_data=f"regen_image_{new_post_id}"),
            InlineKeyboardButton("Add Audio", callback_data=f"add_audio_to_post_{new_post_id}"),
            InlineKeyboardButton("Cancel", callback_data=f"cancel_{new_post_id}"))
        bot.answer_callback_query(call.id, "Regenerated.")
        bot.send_photo(call.message.chat.id, photo=data['photo_id'],
                       caption=MSGS["photo_regenerated"].format(caption=final_caption),
                       reply_markup=markup, parse_mode='HTML')
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {e}")
        # ============================================================
#     SOURCE CARD (ENGLISH) WITH CHANNEL PHOTO + FULL INFO
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "show_source")
def show_source(call):
    notify_instruction(call)
    uid = call.from_user.id
    try:
        dev_chat = bot.get_chat(ADMIN_ID)
        dev_name = dev_chat.first_name or "Developer"
        dev_username = dev_chat.username
    except:
        dev_name = "Developer"; dev_username = None

    channel_id = user_channels.get(str(uid))
    channel_info = None
    channel_photo = None
    if channel_id:
        try:
            channel_info = bot.get_chat(channel_id)
            if channel_info.photo:
                file_info = bot.get_file(channel_info.photo.big_file_id)
                channel_photo = bot.download_file(file_info.file_path)
        except: pass

    bot_username = bot.get_me().username

    if channel_info:
        title = channel_info.title
        ch_username = f"@{channel_info.username}" if channel_info.username else "Private"
        ch_id = channel_info.id
        ch_link = f"https://t.me/{channel_info.username}" if channel_info.username else "Private"
        text = (
            "<b>SOURCE CARD</b>\n"
            "────────────────────\n\n"
            f"<b>Channel:</b> <a href='{ch_link}'>{title}</a>\n"
            f"<b>Username:</b> {ch_username}\n"
            f"<b>Channel ID:</b> <code>{ch_id}</code>\n\n"
            f"<b>Developer:</b> {dev_name}\n"
            f"<b>Bot:</b> @{bot_username}\n"
            f"<b>Version:</b> v2.1\n\n"
            "<blockquote>"
            "Crafted in the shadows of Red World,\n"
            "where every word leaves a mark.\n"
            "Power. Silence. Precision."
            "</blockquote>"
        )
        markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton(f"Channel: {title}", url=ch_link if ch_link != "Private" else f"https://t.me/{bot_username}"),
            InlineKeyboardButton(f"Developer: {dev_name}", url=f"tg://user?id={ADMIN_ID}"),
            InlineKeyboardButton("Back", callback_data="main_menu"))
    else:
        text = (
            "<b>SOURCE CARD</b>\n"
            "────────────────────\n\n"
            f"<b>Developer:</b> {dev_name}\n"
            f"<b>Bot:</b> @{bot_username}\n"
            f"<b>Version:</b> v2.1\n\n"
            "<blockquote>"
            "Crafted in the shadows of Red World,\n"
            "where every word leaves a mark."
            "</blockquote>"
        )
        markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton(f"Developer: {dev_name}", url=f"tg://user?id={ADMIN_ID}"),
            InlineKeyboardButton("Back", callback_data="main_menu"))

    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    if channel_photo:
        bot.send_photo(call.message.chat.id, photo=channel_photo, caption=text,
                       reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ============================================================
#                    MISC BUTTONS
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    notify_instruction(call)
    if str(call.from_user.id) in user_channels:
        del user_channels[str(call.from_user.id)]
        save_json(DB_FILE, user_channels)
        bot.answer_callback_query(call.id, "Unlinked.", show_alert=True)
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "No channel linked.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "show_stats")
def show_stats(call):
    notify_instruction(call)
    cid = user_channels.get(str(call.from_user.id))
    if not cid:
        return bot.answer_callback_query(call.id, "Channel not linked.", show_alert=True)
    try:
        text = MSGS["stats"].format(
            title=bot.get_chat(cid).title,
            members=bot.get_chat_member_count(cid),
            posts=stats['published_count'])
        bot.edit_message_text(text, chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Back", callback_data="main_menu")),
                              parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)

# ============================================================
#                    TEXT PUBLISH MODE
# ============================================================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'): return
    uid = message.from_user.id
    if uid in ad_builder_state: return  # handled above
    if uid in audio_edit_state: return
    if uid in pending_audio_merge: return
    if uid != ADMIN_ID and str(uid) not in user_channels:
        return bot.send_message(message.chat.id, MSGS["not_verified"], parse_mode='HTML')
    settings = user_settings.get(uid, get_default_settings())
    if settings["text_only_mode"] and settings["status"] == "ON":
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        try:
            lang_instr = build_lang_instruction(settings['language'])
            res = client.chat.completions.create(
                messages=[{"role": "user", "content": f"Write a very short one-line phrase in {settings['category']} style ({lang_instr}). No emojis."}],
                model=GROQ_MODEL, max_tokens=300)
            final_caption = f"<b>{res.choices[0].message.content.strip()}</b>\n\n{settings['hashtags']}"
            post_id = str(int(time.time()))
            pending_posts[post_id] = {'type': 'text', 'caption': final_caption,
                                       'channel': user_channels.get(str(uid))}
            markup = InlineKeyboardMarkup(row_width=3).add(
                InlineKeyboardButton("Publish Now", callback_data=f"confirm_{post_id}"),
                InlineKeyboardButton("Schedule", callback_data=f"schedule_{post_id}"),
                InlineKeyboardButton("Cancel", callback_data=f"cancel_{post_id}"))
            bot.send_message(message.chat.id, f"<b>Preview:</b>\n\n{final_caption}",
                             reply_markup=markup, parse_mode='HTML')
        except: pass

# ============================================================
#                    RUN
# ============================================================
print("Bot is running...")
bot.infinity_polling()
