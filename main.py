import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time, json, os, io, re, html
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error as ID3Error
from PIL import Image
import base64

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
TELEGRAM_TOKEN = "8180650384:AAHX37rerimsZIWBEc71HleexJKWqSaSsZ0"
GROQ_API_KEY   = "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"
ADMIN_ID = 8456056018
CHANNEL_LINK = "https://t.me/Eror_7"
GROQ_MODEL = "qwen/qwen3.8-27b" 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

CONFIG_FILE = "bot_config.json"
RIGHTS_CONFIG_FILE = "rights_config.json"
SETTINGS_FILE = "bot_settings.json"
BANNED_FILE = "banned_users.json"
CUSTOM_BTNS_FILE = "custom_buttons.json"

audio_edit_state, ad_builder_state = {}, {}
image_gen_state, video_gen_state, chat_state = {}, {}, {}
audio_cache, user_channels, stats, user_settings, pending_posts = {}, {}, {}, {}, {}
media_save_state, temp_messages = {}, {}
banned_users = {}
custom_buttons = {}
button_builder_state = {}
content_step_state = {}

default_bot_settings = {
    "contact_enabled": True, "notify_login": True, "notify_ban": True, "notify_promote": True, "notify_sub": True,
    "stats": {"total_logins": 0, "total_bans": 0, "total_promotes": 0, "total_subs": 0},
    "logged_users": []
}

# ==========================================
# 2. إدارة الإعدادات والحفظ
# ==========================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channels": [], "media": {"welcome": None, "create": None, "tools": None, "chat": None, "admin": None, "force_sub": None, "source": None}}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

config_data = load_config()
if "media" not in config_data: config_data["media"] = {}
for k in ["welcome", "create", "tools", "chat", "admin", "force_sub", "source"]:
    if k not in config_data["media"]: config_data["media"][k] = None

def load_json(file, default=None):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    return default if default is not None else {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

user_channels = load_json("user_channels.json")
stats = load_json("stats.json")
rights_config = load_json(RIGHTS_CONFIG_FILE)
banned_users = load_json(BANNED_FILE)
custom_buttons = load_json(CUSTOM_BTNS_FILE)

bot_settings = load_json(SETTINGS_FILE, default_bot_settings.copy())
if "logged_users" not in bot_settings: bot_settings["logged_users"] = []
if "published_count" not in stats: stats["published_count"] = 0

def get_default_settings():
    return {"status": "ON", "category": "فلسفي", "language": "عربي", "hashtags": "#RedWorld #عالم_الأحمر"}

# ==========================================
# 3. الكليشات
# ==========================================
MENU_TEXTS = {
    "main_menu": "<b>لوحة التحكم الرئيسية</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ إنشاء محتوى:</b> <b>لتصميم منشوراتك.</b>\n<b>↺ التوليد النصي:</b> <b>لإنشاء إعلاناتك.</b>\n<b>↺ دردشة Gaski:</b> <b>للتحدث مع الذكاء.</b>\n<b>↺ رابط الدعوة:</b> <b>لمشاركة البوت.</b>\n<b>↺ السورس:</b> <b>معلومات النظام.</b>\n<b>↺ مغادرة القناة:</b> <b>لفك الارتباط.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>",
    "menu_create": "<b>استوديو المحتوى</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ إرسال صورة:</b> <b>لتصميم صورة مع عبارة.</b>\n<b>↺ إرسال فيديو:</b> <b>لتصميم فيديو مع عبارة.</b>\n<b>↺ إرسال متحركة:</b> <b>لتصميم GIF مع عبارة.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>",
    "menu_tools": "<b>أدوات النشر</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ إعلان ترويجي:</b> <b>لبناء إعلان.</b>\n<b>↺ حقوق النشر:</b> <b>لإضافة غلاف صوتي.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>",
    "start_chat_gaski": "<b>دردشة Gaski</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ أهلاً بك في العقل المدبر.</b>\n<b>↺ تحدث معي بحرية.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>",
    "start_ad_builder": "<b>بروتوكول الإعلان</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الخطوة 1/4: أرسل الكليشة (نص الإعلان) الآن.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>",
    "start_audio_edit": "<b>ختم الحقوق</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ أرسل صورة الغلاف أولاً.</b>\n<b>↺ ثم أرسل ملف الصوت MP3.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>",
    "send_photo_mode": "<b>أرسل الصورة الآن:</b>\n\n<b>↺ سيتم تصميمها وإضافة العبارة.</b>",
    "send_video_mode": "<b>أرسل الفيديو الآن:</b>\n\n<b>↺ سيتم تصميمه وإضافة العبارة.</b>",
    "send_animation_mode": "<b>أرسل المتحركة (GIF) الآن:</b>\n\n<b>↺ سيتم تصميمها وإضافة العبارة.</b>",
    "waiting_for_photo": "<b>في انتظار الصورة:</b>\n\n<b>↺ يرجى إرسال الصورة الآن.</b>",
    "waiting_for_video": "<b>في انتظار الفيديو:</b>\n\n<b>↺ يرجى إرسال الفيديو الآن.</b>",
    "waiting_for_animation": "<b>في انتظار المتحركة:</b>\n\n<b>↺ يرجى إرسال الصورة المتحركة (GIF) الآن.</b>",
    "welcome": "<b>بوابة عالم الأحمر</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>مرحباً بك في R W | Bot</b>\n\n<b>↺ تصميم المحتوى:</b> <b>صور وفيديوهات.</b>\n<b>↺ التوليد النصي:</b> <b>إعلانات وحقوق.</b>\n<b>↺ حماية القنوات:</b> <b>اشتراك إجباري.</b>\n<b>↺ دردشة مباشرة:</b> <b>مع الذكاء الاصطناعي.</b>\n\n<b>↺ اضغط على زر التحقق للبدء.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>",
    "admin_panel": "<b>لوحة المطور</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الإحصائيات:</b> <b>أرقام البوت.</b>\n<b>↺ قنوات الاشتراك:</b> <b>إدارة القنوات.</b>\n<b>↺ الإعدادات:</b> <b>البوت والإشعارات.</b>\n<b>↺ الإذاعة:</b> <b>رسالة للجميع.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>"
}

# ==========================================
# 4. دوال مساعدة
# ==========================================
def convert_to_jpg(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((200, 200))
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=75)
        return output.getvalue()
    except: return image_bytes

def rebuild_audio_with_cover(original_audio_bytes, cover_bytes, title="Red World", artist="@Eror_7"):
    try:
        audio_buffer = io.BytesIO(original_audio_bytes)
        audio = MP3(audio_buffer, ID3=ID3)
        try: audio.delete()
        except ID3Error: pass
        audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TPE1(encoding=3, text=artist))
        cover_data_jpg = convert_to_jpg(cover_bytes) if cover_bytes else b''
        if cover_data_jpg:
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data_jpg))
        audio.save(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.getvalue(), cover_data_jpg
    except: return original_audio_bytes, cover_bytes

def check_subscription(user_id):
    channels = config_data.get("channels", [])
    if not channels: return True
    for channel in channels:
        try:
            member = bot.get_chat_member(channel["id"], user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def safe_delete(chat_id, message_id):
    try: bot.delete_message(chat_id, message_id)
    except: pass

def get_mention(user):
    name = html.escape(user.first_name)
    return f"<a href='tg://user?id={user.id}'><b>{name}</b></a>"

def track_temp(uid, message_id):
    temp_messages.setdefault(uid, []).append(message_id)

def clear_temp(chat_id, uid):
    for mid in temp_messages.get(uid, []):
        safe_delete(chat_id, mid)
    temp_messages[uid] = []

def send_temp(chat_id, uid, text, markup=None, media_key=None):
    file_id = config_data.get("media", {}).get(media_key) if media_key else None
    sent = None
    if file_id:
        try:
            sent = bot.send_photo(chat_id, file_id, caption=text, reply_markup=markup, parse_mode='HTML')
        except:
            try:
                sent = bot.send_video(chat_id, file_id, caption=text, reply_markup=markup, parse_mode='HTML')
            except: pass
    if not sent:
        sent = bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
    track_temp(uid, sent.message_id)
    return sent

def send_or_edit(call, text, markup, media_key=None):
    uid = call.from_user.id
    clear_temp(call.message.chat.id, uid)
    safe_delete(call.message.chat.id, call.message.message_id)
    send_temp(call.message.chat.id, uid, text, markup, media_key)

def format_ai_response(text):
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    return text

def send_admin_notification(user, action_type, custom_text):
    if getattr(user, 'is_bot', False): return
    if not bot_settings.get(f"notify_{action_type}", True): return
    stat_key = f"total_{action_type}s"
    if action_type == "login": stat_key = "total_logins"
    elif action_type == "ban": stat_key = "total_bans"
    elif action_type == "promote": stat_key = "total_promotes"
    elif action_type == "sub": stat_key = "total_subs"
    bot_settings["stats"][stat_key] = bot_settings["stats"].get(stat_key, 0) + 1
    save_json(SETTINGS_FILE, bot_settings)
    count = bot_settings["stats"].get(stat_key, 0)
    mention = get_mention(user)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(user.first_name, url=f"tg://user?id={user.id}"))
    text = f"<b>{custom_text}</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الاسم:</b> {mention}\n<b>↺ المعرف:</b> @{user.username if user.username else 'لا يوجد'}\n<b>↺ الآيدي:</b> <code>{user.id}</code>\n<b>↺ العدد الإجمالي:</b> <code>{count}</code>"
    try: bot.send_message(ADMIN_ID, text, reply_markup=markup, parse_mode='HTML')
    except: pass

# ==========================================
# 5. أوامر البداية والتحقق
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    clear_temp(message.chat.id, user_id)
    
    if str(user_id) in banned_users:
        return send_temp(message.chat.id, user_id, "<b>عذراً، أنت محظور من استخدام البوت.</b>")

    if str(user_id) not in bot_settings["logged_users"]:
        send_admin_notification(message.from_user, "login", "إشعار دخول جديد")
        bot_settings["logged_users"].append(str(user_id))
        save_json(SETTINGS_FILE, bot_settings)
    
    mention = get_mention(message.from_user)
    
    if user_id != ADMIN_ID and not check_subscription(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        for ch in config_data.get("channels", []):
            markup.add(InlineKeyboardButton(f"اشترك في {ch['name']}", url=f"https://t.me/{ch['id'].replace('@', '')}"))
        markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_sub"))
        return send_temp(message.chat.id, user_id, f"<b>بوابة مغلقة</b>\n\n<b>عذراً {mention}، يجب عليك الاشتراك في القنوات التالية أولاً لتتمكن من استخدام البوت.</b>", markup, media_key="force_sub")
    
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel"),
        InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    
    welcome_text = MENU_TEXTS["welcome"].replace("مرحباً بك", f"مرحباً بك {mention}")
    send_temp(message.chat.id, user_id, welcome_text, markup, media_key="welcome")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "تم التحقق بنجاح!", show_alert=True)
        send_admin_notification(call.from_user, "sub", "اشتراك جديد تم التحقق منه")
        safe_delete(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)
    else: 
        bot.answer_callback_query(call.id, "لم تشترك في جميع القنوات بعد.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id, "جاري الفحص...")
    uid = call.from_user.id
    channel_id = user_channels.get(str(uid))
    if not channel_id:
        clear_temp(call.message.chat.id, uid)
        safe_delete(call.message.chat.id, call.message.message_id)
        msg = send_temp(call.message.chat.id, uid, "<b>أرسل معرف القناة:</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="main_menu")))
        bot.register_next_step_handler(msg, manual_verify, uid, msg.message_id)
    else: 
        perform_verification(call.message.chat.id, uid, channel_id, call.message.message_id)

def manual_verify(message, user_id, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if not message.text or message.text == "إلغاء": return
    clear_temp(message.chat.id, user_id)
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    is_new = str(user_id) not in user_channels
    user_channels[str(user_id)] = channel_input
    save_json("user_channels.json", user_channels)
    safe_delete(message.chat.id, msg_id_to_delete)
    perform_verification(message.chat.id, user_id, channel_input, None, is_new)

def perform_verification(chat_id, user_id, channel_id, msg_id_to_delete, is_new=False):
    msg = send_temp(chat_id, user_id, "<b>جاري الفحص...</b>")
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        if bot_member.status in ['administrator', 'creator'] and getattr(bot_member, 'can_post_messages', False):
            safe_delete(chat_id, msg.message_id)
            if msg_id_to_delete: safe_delete(chat_id, msg_id_to_delete)
            clear_temp(chat_id, user_id)
            if is_new: send_admin_notification(bot.get_chat(user_id), "promote", "تم رفع البوت مشرفاً في قناة جديدة")
            markup = get_main_panel(user_id)
            send_temp(chat_id, user_id, MENU_TEXTS["main_menu"], markup, media_key="welcome")
        else:
            bot.edit_message_text("<b>فشل:</b> البوت ليس مشرفاً أو لا يملك صلاحية النشر.", chat_id=chat_id, message_id=msg.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu")), parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(f"<b>خطأ:</b> {e}", chat_id=chat_id, message_id=msg.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu")), parse_mode='HTML')

# ==========================================
# 6. لوحة التحكم الرئيسية
# ==========================================
def get_main_panel(user_id): 
    markup = InlineKeyboardMarkup(row_width=1); 
    markup.add(
        InlineKeyboardButton("إنشاء محتوى (صورة/فيديو/متحركة)", callback_data="menu_create"), 
        InlineKeyboardButton("التوليد النصي والإعلانات", callback_data="menu_tools"), 
        InlineKeyboardButton("دردشة Gaski", callback_data="start_chat_gaski"), 
        InlineKeyboardButton("لمحة عن البوت", callback_data="bot_glance"),
        InlineKeyboardButton("رابط دعوة البوت", callback_data="invite_link"),
        InlineKeyboardButton("السورس", callback_data="show_source"),
        InlineKeyboardButton("مغادرة القناة", callback_data="leave_channel")
    )
    for btn_id, btn_data in custom_buttons.items():
        markup.add(InlineKeyboardButton(btn_data['text'], url=btn_data['url']))
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("لوحة تحكم المطور", callback_data="admin_panel"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    uid = call.from_user.id
    if uid in chat_state: del chat_state[uid]
    bot.answer_callback_query(call.id)
    markup = get_main_panel(uid)
    send_or_edit(call, MENU_TEXTS["main_menu"], markup, media_key="welcome")

@bot.callback_query_handler(func=lambda call: call.data == "bot_glance")
def bot_glance(call):
    bot_info = bot.get_me()
    total_users = len(user_settings)
    posts = stats.get("published_count", 0)
    channels_count = len(config_data.get("channels", []))
    text = (
        f"<b>لمحة عن البوت</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"<b>↺ الاسم:</b> {bot_info.first_name}\n"
        f"<b>↺ المعرف:</b> @{bot_info.username}\n"
        f"<b>↺ المستخدمين:</b> <code>{total_users}</code>\n"
        f"<b>↺ المنشورات:</b> <code>{posts}</code>\n"
        f"<b>↺ القنوات المربوطة:</b> <code>{channels_count}</code>\n\n"
        f"<b>↺ المطور:</b> <a href='tg://user?id={ADMIN_ID}'>اضغط هنا</a>"
    )
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    send_or_edit(call, text, markup, media_key="welcome")

@bot.callback_query_handler(func=lambda call: call.data == "invite_link")
def invite_link(call):
    bot_username = bot.get_me().username
    link = f"https://t.me/{bot_username}?start=ref_{call.from_user.id}"
    text = f"<b>رابط الدعوة الخاص بك</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ شارك هذا الرابط لدعوة أصدقائك:</b>\n<code>{link}</code>\n\n<b>↺ يمكنك نسخ الرابط بالضغط عليه.</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    send_or_edit(call, text, markup, media_key="welcome")

# ==========================================
# 7. لوحة المطور
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    if call.from_user.id != ADMIN_ID: return bot.answer_callback_query(call.id, "للمطور فقط!", show_alert=True)
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("الإحصائيات", callback_data="admin_stats"),
        InlineKeyboardButton("قنوات الاشتراك", callback_data="admin_channels"),
        InlineKeyboardButton("إعدادات البوت", callback_data="admin_bot_settings"),
        InlineKeyboardButton("إعدادات الكلايش", callback_data="admin_templates"),
        InlineKeyboardButton("إعدادات الوسائط", callback_data="admin_media_settings"),
        InlineKeyboardButton("المحظورين", callback_data="admin_banned"),
        InlineKeyboardButton("الأزرار المخصصة", callback_data="admin_custom_buttons"),
        InlineKeyboardButton("الإشعارات", callback_data="admin_notifications"),
        InlineKeyboardButton("الإذاعة", callback_data="admin_broadcast"),
        InlineKeyboardButton("رجوع", callback_data="main_menu")
    )
    send_or_edit(call, MENU_TEXTS["admin_panel"], markup, media_key="admin")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id != ADMIN_ID: return
    total_users = len(user_settings)
    posts = stats.get("published_count", 0)
    channels_count = len(config_data.get("channels", []))
    text = f"<b>إحصائيات البوت</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>- إجمالي المستخدمين:</b> <code>{total_users}</code>\n<b>- المنشورات:</b> <code>{posts}</code>\n<b>- قنوات الاشتراك:</b> <code>{channels_count}</code>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_panel"))
    send_or_edit(call, text, markup)

# --- إعدادات البوت ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_bot_settings")
def admin_bot_settings(call):
    if call.from_user.id != ADMIN_ID: return
    status = "مفعل ✅" if bot_settings.get("contact_enabled") else "معطل ❌"
    text = f"<b>إعدادات البوت</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ حالة التواصل:</b> {status}\n\n<b>اختر الإجراء المطلوب:</b>"
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("تفعيل التواصل", callback_data="toggle_contact_on"),
        InlineKeyboardButton("تعطيل التواصل", callback_data="toggle_contact_off"),
        InlineKeyboardButton("تحديث البوت", callback_data="refresh_bot"),
        InlineKeyboardButton("رجوع", callback_data="admin_panel")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_contact_"))
def toggle_contact(call):
    if call.from_user.id != ADMIN_ID: return
    state = True if call.data == "toggle_contact_on" else False
    bot_settings["contact_enabled"] = state
    save_json(SETTINGS_FILE, bot_settings)
    bot.answer_callback_query(call.id, "تم التحديث.")
    admin_bot_settings(call)

@bot.callback_query_handler(func=lambda call: call.data == "refresh_bot")
def refresh_bot(call):
    if call.from_user.id != ADMIN_ID: return
    bot.answer_callback_query(call.id, "جاري التحديث...")
    send_or_edit(call, "<b>تم تحديث البوت وإعادة تشغيله بنجاح ✅</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_panel")))

# --- إعدادات الإشعارات ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_notifications")
def admin_notifications(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>إعدادات الإشعارات</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>تحكم في الإشعارات التي تصلك:</b>"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("تفعيل اشعار الدخول", callback_data="notif_login_on"), InlineKeyboardButton("تعطيل اشعار الدخول", callback_data="notif_login_off"))
    markup.add(InlineKeyboardButton("تفعيل اشعار الحظر", callback_data="notif_ban_on"), InlineKeyboardButton("تعطيل اشعار الحظر", callback_data="notif_ban_off"))
    markup.add(InlineKeyboardButton("تفعيل اشعار الرفع", callback_data="notif_promote_on"), InlineKeyboardButton("تعطيل اشعار الرفع", callback_data="notif_promote_off"))
    markup.add(InlineKeyboardButton("تفعيل اشعار الاشتراك", callback_data="notif_sub_on"), InlineKeyboardButton("تعطيل اشعار الاشتراك", callback_data="notif_sub_off"))
    markup.add(InlineKeyboardButton("رجوع", callback_data="admin_panel"))
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("notif_"))
def toggle_notification(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    notif_type = parts[1]
    state = True if parts[2] == "on" else False
    bot_settings[f"notify_{notif_type}"] = state
    save_json(SETTINGS_FILE, bot_settings)
    status_text = "مفعل ✅" if state else "معطل ❌"
    bot.answer_callback_query(call.id, f"تم {status_text} إشعار {notif_type}.")
    admin_notifications(call)

# --- إعدادات الوسائط ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_media_settings")
def admin_media_settings(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>إعدادات الوسائط</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر القسم الذي تريد تعيين صورة أو فيديو له:</b>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("كليشة الترحيب", callback_data="media_set_welcome"),
        InlineKeyboardButton("كليشة إنشاء محتوى", callback_data="media_set_create"),
        InlineKeyboardButton("كليشة الأدوات والإعلانات", callback_data="media_set_tools"),
        InlineKeyboardButton("كليشة دردشة Gaski", callback_data="media_set_chat"),
        InlineKeyboardButton("كليشة لوحة التحكم", callback_data="media_set_admin"),
        InlineKeyboardButton("كليشة الاشتراك الإجباري", callback_data="media_set_force_sub"),
        InlineKeyboardButton("كليشة السورس", callback_data="media_set_source"),
        InlineKeyboardButton("رجوع", callback_data="admin_panel")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("media_set_"))
def media_set_choice(call):
    if call.from_user.id != ADMIN_ID: return
    key = call.data.replace("media_set_", "")
    text = f"<b>تعيين وسائط لـ {key}</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>هل تريد تعيين صورة أم فيديو؟</b>"
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("صورة", callback_data=f"media_upload_{key}_photo"),
        InlineKeyboardButton("فيديو", callback_data=f"media_upload_{key}_video"),
        InlineKeyboardButton("رجوع", callback_data="admin_media_settings")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("media_upload_"))
def media_upload_choice(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    media_type = parts[-1]
    key = "_".join(parts[2:-1])
    media_save_state[call.from_user.id] = {'key': key, 'type': media_type}
    text = f"<b>أرسل الـ{media_type} الآن</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>سيتم حفظ الوسائط وتعيينها.</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="admin_media_settings"))
    send_or_edit(call, text, markup)

# --- إعدادات الكلايش ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_templates")
def admin_templates(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>إعدادات الكلايش</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر القسم الذي تريد تعديل كليشته:</b>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("كليشة الترحيب", callback_data="tpl_welcome"),
        InlineKeyboardButton("كليشة لوحة التحكم", callback_data="tpl_admin"),
        InlineKeyboardButton("كليشة السورس", callback_data="tpl_source"),
        InlineKeyboardButton("كليشة الاشتراك الإجباري", callback_data="tpl_force_sub"),
        InlineKeyboardButton("رجوع", callback_data="admin_panel")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tpl_") and not call.data.startswith("tpl_del_") and not call.data.startswith("tpl_change_"))
def tpl_action(call):
    if call.from_user.id != ADMIN_ID: return
    key = call.data.replace("tpl_", "")
    media_key_map = {"welcome": "welcome", "admin": "admin", "source": "source", "force_sub": "force_sub"}
    media_key = media_key_map.get(key, key)
    has_media = config_data["media"].get(media_key) is not None
    status = "موجودة ✅" if has_media else "غير موجودة ❌"
    text = f"<b>إدارة كليشة: {key}</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الحالة:</b> {status}\n\n<b>اختر الإجراء:</b>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("حذف الكليشة الحالية", callback_data=f"tpl_del_{key}"),
        InlineKeyboardButton("تغيير الكليشة", callback_data=f"tpl_change_{key}"),
        InlineKeyboardButton("رجوع", callback_data="admin_templates")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tpl_del_"))
def tpl_delete(call):
    if call.from_user.id != ADMIN_ID: return
    key = call.data.replace("tpl_del_", "")
    media_key_map = {"welcome": "welcome", "admin": "admin", "source": "source", "force_sub": "force_sub"}
    media_key = media_key_map.get(key, key)
    config_data["media"][media_key] = None
    save_config(config_data)
    bot.answer_callback_query(call.id, "تم حذف الكليشة بنجاح.")
    call.data = f"tpl_{key}"
    tpl_action(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("tpl_change_"))
def tpl_change(call):
    if call.from_user.id != ADMIN_ID: return
    key = call.data.replace("tpl_change_", "")
    media_save_state[ADMIN_ID] = {'key': key, 'type': 'any'}
    text = "<b>أرسل الكليشة الجديدة الآن (صورة أو فيديو):</b>\n\n<b>ملاحظة: يجب أن يحتوي النص المرافق (Caption) على تاك للمستخدم.</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="admin_templates"))
    send_or_edit(call, text, markup)

# --- إدارة الاشتراك الإجباري والإذاعة ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_channels")
def admin_channels(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>إدارة قنوات الاشتراك الإجباري</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر القناة للإدارة أو أضف قناة جديدة.</b>"
    markup = InlineKeyboardMarkup(row_width=1)
    channels = config_data.get("channels", [])
    for i, ch in enumerate(channels):
        markup.add(InlineKeyboardButton(f"{ch['name']}", callback_data=f"manage_ch_{i}"))
    markup.add(InlineKeyboardButton("إضافة قناة جديدة", callback_data="add_ch"))
    markup.add(InlineKeyboardButton("رجوع", callback_data="admin_panel"))
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("manage_ch_"))
def manage_channel(call):
    if call.from_user.id != ADMIN_ID: return
    idx = int(call.data.split("_")[2])
    channels = config_data.get("channels", [])
    if idx >= len(channels): return
    ch = channels[idx]
    text = f"<b>إدارة القناة: {ch['name']}</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر الإجراء المطلوب:</b>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("دخول للقناة", url=f"https://t.me/{ch['id'].replace('@', '')}"),
        InlineKeyboardButton("حذف القناة", callback_data=f"del_ch_{idx}"),
        InlineKeyboardButton("رجوع", callback_data="admin_channels")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_ch_"))
def del_ch(call):
    if call.from_user.id != ADMIN_ID: return
    idx = int(call.data.split("_")[2])
    config_data["channels"].pop(idx)
    save_config(config_data)
    bot.answer_callback_query(call.id, "تم حذف القناة.")
    admin_channels(call)

@bot.callback_query_handler(func=lambda call: call.data == "add_ch")
def add_ch(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>إضافة قناة جديدة</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>أرسل معرف القناة الآن (مثلاً: @MyChannel).</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="admin_channels"))
    send_or_edit(call, text, markup)
    msg = send_temp(call.message.chat.id, call.from_user.id, "<b>في انتظار معرف القناة...</b>", None)
    bot.register_next_step_handler(msg, save_new_channel, msg.message_id)

def save_new_channel(message, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if message.from_user.id != ADMIN_ID: return
    if not message.text or message.text == "إلغاء": return
    clear_temp(message.chat.id, ADMIN_ID)
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    try:
        chat = bot.get_chat(channel_input)
        channel_name = chat.title
    except:
        channel_name = channel_input
    config_data["channels"].append({"id": channel_input, "name": channel_name})
    save_config(config_data)
    safe_delete(message.chat.id, msg_id_to_delete)
    send_temp(message.chat.id, ADMIN_ID, f"<b>تم إضافة القناة:</b> {channel_name}", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_channels")))

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>الإذاعة</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين.</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="admin_panel"))
    send_or_edit(call, text, markup)
    msg = send_temp(call.message.chat.id, ADMIN_ID, "<b>في انتظار نص الإذاعة...</b>", None)
    bot.register_next_step_handler(msg, do_broadcast, msg.message_id)

def do_broadcast(message, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if message.from_user.id != ADMIN_ID: return
    if not message.text or message.text == "إلغاء": return
    clear_temp(message.chat.id, ADMIN_ID)
    success, failed = 0, 0
    msg = send_temp(message.chat.id, ADMIN_ID, "<b>جاري الإذاعة...</b>")
    for uid in user_settings.keys():
        try:
            bot.send_message(uid, f"<b>إعلان من المطور:</b>\n\n{message.text}", parse_mode='HTML')
            success += 1
            time.sleep(0.1)
        except: failed += 1
    safe_delete(message.chat.id, msg_id_to_delete)
    bot.edit_message_text(f"<b>تم الإرسال لـ {success} مستخدم.\nفشل لـ {failed}.</b>", chat_id=message.chat.id, message_id=msg.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_panel")), parse_mode='HTML')
    # ==========================================
# 8. المحظورين والأزرار المخصصة
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "admin_banned")
def admin_banned(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>إعدادات المحظورين</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر الإجراء المطلوب:</b>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("حظر مستخدم", callback_data="ban_user"),
        InlineKeyboardButton("إلغاء حظر مستخدم", callback_data="unban_user"),
        InlineKeyboardButton("عرض عدد المحظورين", callback_data="show_banned"),
        InlineKeyboardButton("رجوع", callback_data="admin_panel")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data == "ban_user")
def ban_user(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>حظر مستخدم</b>\n\n<b>أرسل آيدي المستخدم أو معرفه (@username) لحظره:</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_banned"))
    send_or_edit(call, text, markup)
    msg = send_temp(call.message.chat.id, ADMIN_ID, "<b>في انتظار الآيدي أو المعرف...</b>", None)
    bot.register_next_step_handler(msg, process_ban_user, msg.message_id)

def process_ban_user(message, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if message.from_user.id != ADMIN_ID: return
    if not message.text or message.text == "إلغاء": return
    clear_temp(message.chat.id, ADMIN_ID)
    target = message.text.strip()
    try:
        if target.startswith('@'):
            chat = bot.get_chat(target)
            uid = str(chat.id)
            name = chat.first_name
            username = target
        else:
            uid = target
            name = "مستخدم محظور"
            username = "لا يوجد"
        banned_users[uid] = {"name": name, "username": username}
        save_json(BANNED_FILE, banned_users)
        send_temp(message.chat.id, ADMIN_ID, f"<b>تم حظر المستخدم:</b> {name} (الآيدي: <code>{uid}</code>)", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_banned")))
    except Exception as e:
        send_temp(message.chat.id, ADMIN_ID, f"<b>خطأ في العثور على المستخدم:</b> {e}", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_banned")))

@bot.callback_query_handler(func=lambda call: call.data == "unban_user")
def unban_user(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>إلغاء حظر</b>\n\n<b>أرسل آيدي المستخدم لحذفه من قائمة المحظورين:</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_banned"))
    send_or_edit(call, text, markup)
    msg = send_temp(call.message.chat.id, ADMIN_ID, "<b>في انتظار الآيدي...</b>", None)
    bot.register_next_step_handler(msg, process_unban_user, msg.message_id)

def process_unban_user(message, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if message.from_user.id != ADMIN_ID: return
    if not message.text or message.text == "إلغاء": return
    clear_temp(message.chat.id, ADMIN_ID)
    uid = message.text.strip()
    if uid in banned_users:
        del banned_users[uid]
        save_json(BANNED_FILE, banned_users)
        send_temp(message.chat.id, ADMIN_ID, f"<b>تم إلغاء حظر المستخدم:</b> <code>{uid}</code>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_banned")))
    else:
        send_temp(message.chat.id, ADMIN_ID, "<b>هذا المستخدم غير موجود في قائمة المحظورين.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_banned")))

@bot.callback_query_handler(func=lambda call: call.data == "show_banned")
def show_banned(call):
    if call.from_user.id != ADMIN_ID: return
    if not banned_users:
        text = "<b>قائمة المحظورين فارغة.</b>"
    else:
        text = "<b>قائمة المحظورين:</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        for uid, data in banned_users.items():
            text += f"<b>↺ الاسم:</b> {data['name']}\n<b>↺ الآيدي:</b> <code>{uid}</code>\n<b>↺ المعرف:</b> <code>{data['username']}</code>\n\n"
        text += f"<b>↺ العدد الإجمالي:</b> <code>{len(banned_users)}</code>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_banned"))
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_custom_buttons")
def admin_custom_buttons(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>الأزرار المخصصة</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر الإجراء المطلوب:</b>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إنشاء زر جديد", callback_data="create_custom_btn"),
        InlineKeyboardButton("حذف زر", callback_data="delete_custom_btn"),
        InlineKeyboardButton("رجوع", callback_data="admin_panel")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data == "create_custom_btn")
def create_custom_btn(call):
    if call.from_user.id != ADMIN_ID: return
    button_builder_state[ADMIN_ID] = {'step': 'waiting_btn_name'}
    text = "<b>إنشاء زر جديد</b>\n\n<b>الخطوة 1/2: أرسل اسم الزر:</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="admin_custom_buttons"))
    send_or_edit(call, text, markup)
    msg = send_temp(call.message.chat.id, ADMIN_ID, "<b>في انتظار اسم الزر...</b>", None)
    bot.register_next_step_handler(msg, process_btn_name, msg.message_id)

def process_btn_name(message, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if message.from_user.id != ADMIN_ID or ADMIN_ID not in button_builder_state: return
    if not message.text or message.text == "إلغاء": return
    clear_temp(message.chat.id, ADMIN_ID)
    button_builder_state[ADMIN_ID]['name'] = message.text.strip()
    button_builder_state[ADMIN_ID]['step'] = 'waiting_btn_url'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="admin_custom_buttons"))
    msg = send_temp(message.chat.id, ADMIN_ID, "<b>الخطوة 2/2: أرسل الرابط (يبدأ بـ http أو tg):</b>", markup)
    bot.register_next_step_handler(msg, process_btn_url, msg.message_id)

def process_btn_url(message, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if message.from_user.id != ADMIN_ID or ADMIN_ID not in button_builder_state: return
    if not message.text or message.text == "إلغاء": return
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("tg://")):
        return send_temp(message.chat.id, ADMIN_ID, "<b>الرابط غير صحيح.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="admin_custom_buttons")))
    clear_temp(message.chat.id, ADMIN_ID)
    name = button_builder_state[ADMIN_ID]['name']
    btn_id = str(int(time.time()))
    custom_buttons[btn_id] = {"text": name, "url": url}
    save_json(CUSTOM_BTNS_FILE, custom_buttons)
    del button_builder_state[ADMIN_ID]
    send_temp(message.chat.id, ADMIN_ID, f"<b>تم إنشاء الزر بنجاح ✅</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_custom_buttons")))

@bot.callback_query_handler(func=lambda call: call.data == "delete_custom_btn")
def delete_custom_btn(call):
    if call.from_user.id != ADMIN_ID: return
    if not custom_buttons:
        return send_or_edit(call, "<b>لا توجد أزرار مخصصة للحذف.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_custom_buttons")))
    markup = InlineKeyboardMarkup(row_width=1)
    for btn_id, btn_data in custom_buttons.items():
        markup.add(InlineKeyboardButton(btn_data['text'], callback_data=f"confirm_del_btn_{btn_id}"))
    markup.add(InlineKeyboardButton("رجوع", callback_data="admin_custom_buttons"))
    send_or_edit(call, "<b>اختر الزر الذي تريد حذفه:</b>", markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_del_btn_"))
def confirm_delete_btn(call):
    if call.from_user.id != ADMIN_ID: return
    btn_id = call.data.replace("confirm_del_btn_", "")
    text = f"<b>تأكيد الحذف</b>\n\n<b>هل أنت متأكد من حذف الزر؟</b>"
    markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("نعم، احذف", callback_data=f"execute_del_btn_{btn_id}"), InlineKeyboardButton("إلغاء", callback_data="admin_custom_buttons"))
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("execute_del_btn_"))
def execute_delete_btn(call):
    if call.from_user.id != ADMIN_ID: return
    btn_id = call.data.replace("execute_del_btn_", "")
    if btn_id in custom_buttons:
        del custom_buttons[btn_id]
        save_json(CUSTOM_BTNS_FILE, custom_buttons)
    bot.answer_callback_query(call.id, "تم حذف الزر بنجاح.")
    call.data = "admin_custom_buttons"
    admin_custom_buttons(call)

# ==========================================
# 9. إنشاء المحتوى (صورة، فيديو، متحركة)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "menu_create")
def menu_create(call):
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("إرسال صورة", callback_data="send_photo_mode"),
        InlineKeyboardButton("إرسال فيديو", callback_data="send_video_mode"),
        InlineKeyboardButton("إرسال متحركة", callback_data="send_animation_mode"),
        InlineKeyboardButton("رجوع", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["menu_create"], markup, media_key="create")

@bot.callback_query_handler(func=lambda call: call.data == "send_photo_mode")
def trigger_photo_mode(call):
    image_gen_state[call.from_user.id] = {'step': 'waiting_for_photo'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_create"))
    send_or_edit(call, MENU_TEXTS["waiting_for_photo"], markup, media_key="create")

@bot.callback_query_handler(func=lambda call: call.data == "send_video_mode")
def trigger_video_mode(call):
    video_gen_state[call.from_user.id] = {'step': 'waiting_for_video'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_create"))
    send_or_edit(call, MENU_TEXTS["waiting_for_video"], markup, media_key="create")

@bot.callback_query_handler(func=lambda call: call.data == "send_animation_mode")
def trigger_animation_mode(call):
    video_gen_state[call.from_user.id] = {'step': 'waiting_for_animation'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_create"))
    send_or_edit(call, MENU_TEXTS["waiting_for_animation"], markup, media_key="create")

@bot.message_handler(content_types=['photo', 'video', 'video_note', 'animation'])
def handle_media(message):
    uid = message.from_user.id
    
    if uid == ADMIN_ID and uid in media_save_state and media_save_state[uid].get('type') != 'any':
        state = media_save_state[uid]
        key = state['key']
        mtype = state['type']
        file_id = None
        if mtype == "photo" and message.photo: file_id = message.photo[-1].file_id
        elif mtype == "video":
            if message.video: file_id = message.video.file_id
            elif message.video_note: file_id = message.video_note.file_id
            elif message.animation: file_id = message.animation.file_id
        if not file_id:
            safe_delete(message.chat.id, message.message_id)
            return send_temp(message.chat.id, uid, "<b>نوع الملف غير صحيح.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_media_settings")))
        config_data["media"][key] = file_id
        save_config(config_data)
        del media_save_state[uid]
        safe_delete(message.chat.id, message.message_id)
        clear_temp(message.chat.id, uid)
        send_temp(message.chat.id, uid, "<b>تم حفظ الوسائط بنجاح ✅</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_media_settings")))
        return

    if uid in image_gen_state and image_gen_state[uid].get('step') == 'waiting_for_photo':
        if message.photo:
            safe_delete(message.chat.id, message.message_id)
            clear_temp(message.chat.id, uid)
            image_gen_state[uid]['file_id'] = message.photo[-1].file_id
            image_gen_state[uid]['step'] = 'waiting_category'
            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("حزين", callback_data="img_cat_حزين"), InlineKeyboardButton("فلسفي", callback_data="img_cat_فلسفي"),
                InlineKeyboardButton("حب", callback_data="img_cat_حب"), InlineKeyboardButton("اقتباس", callback_data="img_cat_اقتباس"),
                InlineKeyboardButton("اشتياق", callback_data="img_cat_اشتياق"), InlineKeyboardButton("خذلان", callback_data="img_cat_خذلان"),
                InlineKeyboardButton("وحدة", callback_data="img_cat_وحدة"), InlineKeyboardButton("صمود", callback_data="img_cat_صمود"),
                InlineKeyboardButton("غموض", callback_data="img_cat_غموض"), InlineKeyboardButton("أمل", callback_data="img_cat_أمل"),
                InlineKeyboardButton("عتاب", callback_data="img_cat_عتاب"), InlineKeyboardButton("سخرية", callback_data="img_cat_سخرية"),
                InlineKeyboardButton("ندم", callback_data="img_cat_ندم"), InlineKeyboardButton("تحدي", callback_data="img_cat_تحدي"),
                InlineKeyboardButton("ذكرى", callback_data="img_cat_ذكرى"), InlineKeyboardButton("صمت", callback_data="img_cat_صمت"),
                InlineKeyboardButton("فخم", callback_data="img_cat_فخم"), InlineKeyboardButton("الشعر الثقافي", callback_data="img_cat_الشعر الثقافي"),
                InlineKeyboardButton("شعر عراقي", callback_data="img_cat_شعر عراقي"), InlineKeyboardButton("الجوكر", callback_data="img_cat_الجوكر"),
                InlineKeyboardButton("القصف", callback_data="img_cat_القصف"),
                InlineKeyboardButton("رجوع", callback_data="menu_create"))
            category_text = "<b>تم استلام الصورة بنجاح ✅</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الخطوة التالية:</b>\n<b>اختر الفئة المناسبة لتصميم العبارة على صورتك.</b>"
            send_temp(message.chat.id, uid, category_text, markup)
            return

    if uid in video_gen_state and video_gen_state[uid].get('step') in ['waiting_for_video', 'waiting_for_animation']:
        if message.video or message.video_note or message.animation:
            safe_delete(message.chat.id, message.message_id)
            clear_temp(message.chat.id, uid)
            if message.video: file_id = message.video.file_id
            elif message.video_note: file_id = message.video_note.file_id
            else: file_id = message.animation.file_id
            
            video_gen_state[uid]['file_id'] = file_id
            video_gen_state[uid]['step'] = 'waiting_category'
            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("حزين", callback_data="vid_cat_حزين"), InlineKeyboardButton("فلسفي", callback_data="vid_cat_فلسفي"),
                InlineKeyboardButton("حب", callback_data="vid_cat_حب"), InlineKeyboardButton("اقتباس", callback_data="vid_cat_اقتباس"),
                InlineKeyboardButton("فخم", callback_data="vid_cat_فخم"), InlineKeyboardButton("الشعر الثقافي", callback_data="vid_cat_الشعر الثقافي"),
                InlineKeyboardButton("شعر عراقي", callback_data="vid_cat_شعر عراقي"), InlineKeyboardButton("الجوكر", callback_data="vid_cat_الجوكر"),
                InlineKeyboardButton("القصف", callback_data="vid_cat_القصف"),
                InlineKeyboardButton("رجوع", callback_data="menu_create"))
            category_text = "<b>تم استلام الفيديو/المتحركة بنجاح ✅</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الخطوة التالية:</b>\n<b>اختر الفئة المناسبة لتصميم العبارة.</b>"
            send_temp(message.chat.id, uid, category_text, markup)
            return

@bot.callback_query_handler(func=lambda call: call.data.startswith("img_cat_") or call.data.startswith("vid_cat_"))
def media_category(call):
    uid = call.from_user.id
    is_img = call.data.startswith("img_cat_")
    cat = call.data.replace("img_cat_", "").replace("vid_cat_", "")
    if is_img and uid in image_gen_state: image_gen_state[uid]['category'] = cat
    elif not is_img and uid in video_gen_state: video_gen_state[uid]['category'] = cat
    prefix = "img" if is_img else "vid"
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("عربي فقط", callback_data=f"{prefix}_lang_عربي"),
        InlineKeyboardButton("مختلط", callback_data=f"{prefix}_lang_مختلط"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    text = f"<b>الفئة: {cat}</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر لغة العبارة.</b>"
    send_or_edit(call, text, markup, media_key="create")

@bot.callback_query_handler(func=lambda call: call.data.startswith("img_lang_") or call.data.startswith("vid_lang_"))
def media_language(call):
    uid = call.from_user.id
    is_img = call.data.startswith("img_lang_")
    lang_choice = call.data.replace("img_lang_", "").replace("vid_lang_", "")
    if is_img and uid in image_gen_state: image_gen_state[uid]['language'] = lang_choice
    elif not is_img and uid in video_gen_state: video_gen_state[uid]['language'] = lang_choice
    prefix = "img" if is_img else "vid"
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("خط مائل", callback_data=f"{prefix}_fmt_italic"),
        InlineKeyboardButton("خط غامض", callback_data=f"{prefix}_fmt_bold"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    text = f"<b>اللغة: {lang_choice}</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>اختر تنسيق النص.</b>"
    send_or_edit(call, text, markup, media_key="create")

@bot.callback_query_handler(func=lambda call: call.data.startswith("img_fmt_") or call.data.startswith("vid_fmt_"))
def media_format_and_desc(call):
    uid = call.from_user.id
    is_img = call.data.startswith("img_fmt_")
    fmt = call.data.split("_")[-1]
    
    if is_img and uid in image_gen_state: image_gen_state[uid]['format'] = fmt
    elif not is_img and uid in video_gen_state: video_gen_state[uid]['format'] = fmt
    else: return bot.answer_callback_query(call.id, "انتهت الجلسة.", show_alert=True)
    
    content_step_state[uid] = {'is_img': is_img}
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("تخطي الوصف", callback_data="skip_desc"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    text = "<b>تغيير الوصف (اختياري)</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ أرسل النص الذي تريده أن يظهر أسفل العبارة.</b>\n\n<b>↺ أو اضغط على زر التخطي للنشر بدون وصف.</b>"
    send_or_edit(call, text, markup, media_key="create")

@bot.message_handler(func=lambda m: m.from_user.id in content_step_state and 'is_img' in content_step_state[m.from_user.id], content_types=['text'])
def process_custom_desc(message):
    uid = message.from_user.id
    if not message.text or message.text.startswith('/'): return
    if message.text == "إلغاء": 
        del content_step_state[uid]
        return
    desc_text = message.text.strip()
    clear_temp(message.chat.id, uid)
    safe_delete(message.chat.id, message.message_id)
    is_img = content_step_state[uid]['is_img']
    del content_step_state[uid]
    generate_final_preview(message.chat.id, uid, is_img, custom_desc=desc_text)

@bot.callback_query_handler(func=lambda call: call.data == "skip_desc")
def skip_desc_step(call):
    uid = call.from_user.id
    if uid not in content_step_state: return
    is_img = content_step_state[uid]['is_img']
    del content_step_state[uid]
    generate_final_preview(call.message.chat.id, uid, is_img, custom_desc=None)

def generate_final_preview(chat_id, uid, is_img, custom_desc=None):
    if is_img and uid in image_gen_state: state = image_gen_state[uid]; file_id = state['file_id']; category = state.get('category', 'فلسفي'); lang = state.get('language', 'عربي'); fmt = state.get('format', 'bold'); media_type = 'photo'
    elif not is_img and uid in video_gen_state: state = video_gen_state[uid]; file_id = state['file_id']; category = state.get('category', 'فلسفي'); lang = state.get('language', 'عربي'); fmt = state.get('format', 'bold'); media_type = 'video'
    else: return
    
    msg = send_temp(chat_id, uid, "<b>جاري توليد العبارة...</b>")
    category_prompts = {
        "فخم": "اكتب عبارة فخمة، راقية، وملكية تعكس الفخامة والهيبة (بأسلوب سينمائي).",
        "الشعر الثقافي": "اكتب بيت شعر ثقافي عميق وهادف يمس القلب والفكر.",
        "شعر عراقي": "اكتب بيت شعر عراقي أصيل (شعبي أو فصيح) يعكس الطابع العراقي الدافئ.",
        "الجوكر": "اكتب عبارة جوكرية، مظلمة، ساخرة بجنون، وساخرة من الواقع.",
        "القصف": "اكتب عبارة قوية جداً، حادة، وقاصفة (بدون شتائم) تعكس القوة والسيطرة."
    }
    specific_prompt = category_prompts.get(category, f"اكتب عبارة قصيرة جداً بأسلوب {category}.")
    lang_instr = "جملة عربية قصيرة ثم ترجمتها الإنجليزية في السطر التالي" if lang == "مختلط" else "باللغة العربية الفصحى"
    prompt = f"{specific_prompt} ({lang_instr}). بدون إيموجي."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=150)
        raw_text = res.choices[0].message.content.strip()
    except: raw_text = "عبارة تجريبية."
    final_text = f"<i>{raw_text}</i>" if fmt == "italic" else f"<b>{raw_text}</b>"
    final_caption = f"<b>{final_text}</b>"
    if custom_desc: final_caption += f"\n\n{custom_desc}"
    
    post_id = str(int(time.time()))
    pending_posts[post_id] = {'type': media_type, 'file_id': file_id, 'caption': final_caption, 'channel': user_channels.get(str(uid)), 'category': category, 'language': lang, 'format': fmt, 'is_img': is_img, 'custom_button': None, 'custom_desc': custom_desc}
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة زر مخصص للمنشور", callback_data=f"add_btn_{post_id}"),
        InlineKeyboardButton("تغيير العبارة", callback_data=f"change_caption_{post_id}"),
        InlineKeyboardButton("تغيير الوصف", callback_data=f"change_desc_{post_id}"),
        InlineKeyboardButton("تخطي وإكمال النشر", callback_data=f"confirm_{post_id}"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    safe_delete(chat_id, msg.message_id)
    if media_type == 'photo': bot.send_photo(chat_id, file_id, caption=f"<b>معاينة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(chat_id, file_id, caption=f"<b>معاينة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("change_caption_"))
def change_caption(call):
    post_id = call.data.split("_")[2]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    data = pending_posts[post_id]
    bot.answer_callback_query(call.id, "جاري توليد عبارة جديدة...")
    category = data.get('category', 'فلسفي'); lang = data.get('language', 'عربي'); fmt = data.get('format', 'bold'); file_id = data['file_id']; media_type = data['type']; custom_desc = data.get('custom_desc')
    
    category_prompts = {
        "فخم": "اكتب عبارة فخمة، راقية، وملكية تعكس الفخامة والهيبة (بأسلوب سينمائي).",
        "الشعر الثقافي": "اكتب بيت شعر ثقافي عميق وهادف يمس القلب والفكر.",
        "شعر عراقي": "اكتب بيت شعر عراقي أصيل (شعبي أو فصيح) يعكس الطابع العراقي الدافئ.",
        "الجوكر": "اكتب عبارة جوكرية، مظلمة، ساخرة بجنون، وساخرة من الواقع.",
        "القصف": "اكتب عبارة قوية جداً، حادة، وقاصفة (بدون شتائم) تعكس القوة والسيطرة."
    }
    specific_prompt = category_prompts.get(category, f"اكتب عبارة قصيرة جداً بأسلوب {category}.")
    lang_instr = "جملة عربية قصيرة ثم ترجمتها الإنجليزية في السطر التالي" if lang == "مختلط" else "باللغة العربية الفصحى"
    prompt = f"{specific_prompt} ({lang_instr}). بدون إيموجي."
    
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=150)
        raw_text = res.choices[0].message.content.strip()
    except: raw_text = "عبارة تجريبية."
    final_text = f"<i>{raw_text}</i>" if fmt == "italic" else f"<b>{raw_text}</b>"
    final_caption = f"<b>{final_text}</b>"
    if custom_desc: final_caption += f"\n\n{custom_desc}"
    
    data['caption'] = final_caption
    pending_posts[post_id] = data
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة زر مخصص للمنشور", callback_data=f"add_btn_{post_id}"),
        InlineKeyboardButton("تغيير العبارة", callback_data=f"change_caption_{post_id}"),
        InlineKeyboardButton("تغيير الوصف", callback_data=f"change_desc_{post_id}"),
        InlineKeyboardButton("تخطي وإكمال النشر", callback_data=f"confirm_{post_id}"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    safe_delete(call.message.chat.id, call.message.message_id)
    if media_type == 'photo': bot.send_photo(call.message.chat.id, file_id, caption=f"<b>معاينة جديدة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(call.message.chat.id, file_id, caption=f"<b>معاينة جديدة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("change_desc_"))
def change_desc(call):
    post_id = call.data.split("_")[2]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    uid = call.from_user.id
    data = pending_posts[post_id]
    content_step_state[uid] = {'is_img': data['is_img'], 'editing_post_id': post_id}
    
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("تخطي وحذف الوصف", callback_data=f"skip_edit_desc_{post_id}"),
        InlineKeyboardButton("إلغاء", callback_data=f"confirm_{post_id}"))
    text = "<b>تغيير الوصف</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ أرسل الوصف الجديد الآن.</b>\n\n<b>↺ أو اضغط على زر التخطي لحذف الوصف.</b>"
    send_or_edit(call, text, markup)
    msg = send_temp(call.message.chat.id, uid, "<b>في انتظار الوصف الجديد...</b>", None)
    bot.register_next_step_handler(msg, process_edit_desc, post_id, msg.message_id)

def process_edit_desc(message, post_id, msg_id_to_delete):
    uid = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    safe_delete(message.chat.id, msg_id_to_delete)
    if not message.text or post_id not in pending_posts: return
    clear_temp(message.chat.id, uid)
    data = pending_posts[post_id]
    data['custom_desc'] = message.text.strip()
    base_caption = data['caption'].split('\n\n')[0]
    data['caption'] = f"{base_caption}\n\n{data['custom_desc']}"
    pending_posts[post_id] = data
    if uid in content_step_state: del content_step_state[uid]
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة زر مخصص للمنشور", callback_data=f"add_btn_{post_id}"),
        InlineKeyboardButton("تغيير العبارة", callback_data=f"change_caption_{post_id}"),
        InlineKeyboardButton("تغيير الوصف", callback_data=f"change_desc_{post_id}"),
        InlineKeyboardButton("تخطي وإكمال النشر", callback_data=f"confirm_{post_id}"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    if data['type'] == 'photo': bot.send_photo(message.chat.id, data['file_id'], caption=f"<b>معاينة بعد التعديل</b>\n\n{data['caption']}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(message.chat.id, data['file_id'], caption=f"<b>معاينة بعد التعديل</b>\n\n{data['caption']}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("skip_edit_desc_"))
def skip_edit_desc(call):
    post_id = call.data.replace("skip_edit_desc_", "")
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    data = pending_posts[post_id]
    data['custom_desc'] = None
    data['caption'] = data['caption'].split('\n\n')[0]
    pending_posts[post_id] = data
    bot.answer_callback_query(call.id, "تم حذف الوصف.")
    call.data = f"confirm_{post_id}"
    confirm_post(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_btn_"))
def ask_button_text(call):
    post_id = call.data.split("_")[2]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = send_temp(call.message.chat.id, uid, "<b>أرسل اسم الزر (النص الذي سيظهر عليه):</b>\n\n<b>مثال: انضم للقناة</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu")))
    bot.register_next_step_handler(msg, ask_button_link, post_id, msg.message_id)

def ask_button_link(message, post_id, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if not message.text or message.text == "إلغاء" or post_id not in pending_posts: return
    uid = message.from_user.id
    pending_posts[post_id]['temp_btn_text'] = message.text.strip()
    clear_temp(message.chat.id, uid)
    safe_delete(message.chat.id, msg_id_to_delete)
    msg = send_temp(message.chat.id, uid, "<b>أرسل رابط الزر (يجب أن يبدأ بـ http أو https):</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu")))
    bot.register_next_step_handler(msg, save_button_and_preview, post_id, msg.message_id)

def save_button_and_preview(message, post_id, msg_id_to_delete):
    safe_delete(message.chat.id, message.message_id)
    if not message.text or message.text == "إلغاء" or post_id not in pending_posts: return
    uid = message.from_user.id
    link = message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        return send_temp(message.chat.id, uid, "<b>الرابط غير صحيح. يجب أن يبدأ بـ http أو https.</b>")
    data = pending_posts[post_id]
    data['custom_button'] = {'text': data['temp_btn_text'], 'url': link}
    clear_temp(message.chat.id, uid)
    safe_delete(message.chat.id, msg_id_to_delete)
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(data['custom_button']['text'], url=data['custom_button']['url']))
    markup.add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    if data['type'] == 'photo': bot.send_photo(message.chat.id, data['file_id'], caption=f"<b>معاينة نهائية</b>\n\n{data['caption']}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(message.chat.id, data['file_id'], caption=f"<b>معاينة نهائية</b>\n\n{data['caption']}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_post(call):
    post_id = call.data.split("_")[1]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    data = pending_posts[post_id]
    markup = None
    if data.get('custom_button'):
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(data['custom_button']['text'], url=data['custom_button']['url']))
    try:
        if data['type'] == 'photo': bot.send_photo(data['channel'], data['file_id'], caption=data['caption'], reply_markup=markup, parse_mode='HTML')
        else: bot.send_video(data['channel'], data['file_id'], caption=data['caption'], reply_markup=markup, parse_mode='HTML')
        stats["published_count"] += 1; save_json("stats.json", stats)
        bot.answer_callback_query(call.id, "تم النشر.")
        del pending_posts[post_id]
        main_menu(call)
    except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

# ==========================================
# 10. نظام الإعلانات
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "menu_tools")
def menu_tools(call):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إنشاء إعلان ترويجي", callback_data="start_ad_builder"),
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit"),
        InlineKeyboardButton("رجوع", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["menu_tools"], markup, media_key="tools")

@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    uid = call.from_user.id
    ad_builder_state[uid] = {'step': 'waiting_ad_text'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_tools"))
    send_or_edit(call, MENU_TEXTS["start_ad_builder"], markup, media_key="tools")

@bot.message_handler(func=lambda m: m.from_user.id in ad_builder_state and ad_builder_state[m.from_user.id].get('step') in ['waiting_ad_text', 'waiting_ad_btn_text', 'waiting_ad_btn_url'], content_types=['text'])
def ad_builder_text_steps(message):
    uid = message.from_user.id
    data = ad_builder_state[uid]
    step = data['step']
    safe_delete(message.chat.id, message.message_id)
    if not message.text or message.text == "إلغاء": return
    clear_temp(message.chat.id, uid)
    
    if step == 'waiting_ad_text':
        data['ad_text'] = message.text.strip()
        data['step'] = 'waiting_ad_btn_text'
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_tools"))
        msg = send_temp(message.chat.id, uid, "<b>الخطوة 2/4: أرسل الاسم الذي سيظهر على الزر:</b>", markup)
        bot.register_next_step_handler(msg, ad_builder_text_steps)
    elif step == 'waiting_ad_btn_text':
        data['btn_text'] = message.text.strip()
        data['step'] = 'waiting_ad_btn_url'
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_tools"))
        msg = send_temp(message.chat.id, uid, "<b>الخطوة 3/4: أرسل الرابط (تليجرام أو ويب):</b>", markup)
        bot.register_next_step_handler(msg, ad_builder_text_steps)
    elif step == 'waiting_ad_btn_url':
        link = message.text.strip()
        if not (link.startswith("http://") or link.startswith("https://") or link.startswith("tg://")):
            return send_temp(message.chat.id, uid, "<b>الرابط غير صحيح. يجب أن يبدأ بـ http أو https أو tg.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools")))
        data['btn_url'] = link
        data['step'] = 'waiting_ad_media_type'
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("صورة", callback_data="ad_media_photo"),
            InlineKeyboardButton("فيديو", callback_data="ad_media_video"),
            InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_tools"))
        send_temp(message.chat.id, uid, "<b>الخطوة 4/4: اختر نوع الوسائط للإعلان:</b>", markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_media_"))
def ad_media_choice(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    media_type = call.data.replace("ad_media_", "")
    ad_builder_state[uid]['media_type'] = media_type
    ad_builder_state[uid]['step'] = 'waiting_ad_media_file'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_tools"))
    send_or_edit(call, f"<b>أرسل الـ{('صورة' if media_type == 'photo' else 'فيديو')} الآن لإكمال الإعلان:</b>", markup)

@bot.message_handler(content_types=['photo', 'video', 'video_note'], func=lambda m: m.from_user.id in ad_builder_state and ad_builder_state[m.from_user.id].get('step') == 'waiting_ad_media_file')
def ad_builder_media_step(message):
    uid = message.from_user.id
    data = ad_builder_state[uid]
    media_type = data['media_type']
    file_id = None
    if media_type == 'photo' and message.photo: file_id = message.photo[-1].file_id
    elif media_type == 'video':
        if message.video: file_id = message.video.file_id
        elif message.video_note: file_id = message.video_note.file_id
    if not file_id:
        return send_temp(message.chat.id, uid, "<b>عذراً، نوع الملف المرسل لا يطابق اختيارك.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools")))
    safe_delete(message.chat.id, message.message_id)
    clear_temp(message.chat.id, uid)
    
    data['file_id'] = file_id
    data['step'] = 'waiting_ad_confirmation'
    proposed_caption = f"<b>{data['ad_text']}</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ اضغط على الزر بالأسفل للمزيد.</b>\n\n<b>━━━━━━━━━━━━━━━━━━━━</b>"
    data['proposed_caption'] = proposed_caption
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(data['btn_text'], url=data['btn_url']),
        InlineKeyboardButton("نعم، تأكيد النشر ✅", callback_data=f"ad_confirm_yes_{uid}"),
        InlineKeyboardButton("لا، إلغاء ❌", callback_data=f"ad_confirm_no_{uid}"),
        InlineKeyboardButton("تعديل الكليشة 📝", callback_data=f"ad_confirm_edit_{uid}"),
        InlineKeyboardButton("الرجوع للخلف ⬅️", callback_data="menu_tools"))
    
    if media_type == 'photo': bot.send_photo(message.chat.id, file_id, caption=proposed_caption, reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(message.chat.id, file_id, caption=proposed_caption, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_confirm_"))
def ad_confirm_action(call):
    parts = call.data.split("_")
    action = parts[2]
    uid = int(parts[3])
    if uid not in ad_builder_state: return bot.answer_callback_query(call.id, "انتهت الصلاحية.", show_alert=True)
    data = ad_builder_state[uid]
    target_channel = user_channels.get(str(uid))
    
    if action == "yes":
        if not target_channel: return bot.answer_callback_query(call.id, "لم تربط قناة! استخدم (التحقق من الرفع) أولاً.", show_alert=True)
        try:
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton(data['btn_text'], url=data['btn_url']))
            if data['media_type'] == 'photo': bot.send_photo(target_channel, data['file_id'], caption=data['proposed_caption'], reply_markup=markup, parse_mode='HTML')
            else: bot.send_video(target_channel, data['file_id'], caption=data['proposed_caption'], reply_markup=markup, parse_mode='HTML')
            stats["published_count"] += 1; save_json("stats.json", stats)
            bot.answer_callback_query(call.id, "تم نشر الإعلان بنجاح! ✅", show_alert=True)
            del ad_builder_state[uid]
            safe_delete(call.message.chat.id, call.message.message_id)
            markup = get_main_panel(uid)
            send_temp(call.message.chat.id, uid, MENU_TEXTS["main_menu"], markup, media_key="welcome")
        except Exception as e: bot.answer_callback_query(call.id, f"خطأ أثناء النشر: {e}", show_alert=True)
    elif action == "no":
        del ad_builder_state[uid]
        bot.answer_callback_query(call.id, "تم إلغاء الإعلان.")
        safe_delete(call.message.chat.id, call.message.message_id)
        markup = get_main_panel(uid)
        send_temp(call.message.chat.id, uid, MENU_TEXTS["main_menu"], markup, media_key="welcome")
    elif action == "edit":
        data['step'] = 'waiting_ad_text'
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_tools"))
        msg = send_temp(call.message.chat.id, uid, "<b>تعديل الإعلان:</b>\n\n<b>أرسل الكليشة (نص الإعلان) الجديدة:</b>", markup)
        bot.register_next_step_handler(msg, ad_builder_text_steps)

# ==========================================
# 11. نظام الحقوق الصوتي (تم إصلاحه ليعمل قبل معالج الصور)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    uid = call.from_user.id
    saved = rights_config.get(str(uid))
    if saved and saved.get("artist"):
        audio_edit_state[uid] = {'step': 'waiting_for_cover', 'cover_data': None, 'artist': saved['artist'], 'title': saved['title'], 'desc': saved['desc']}
        text = f"<b>ختم الحقوق</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الفنان:</b> <code>{saved['artist']}</code>\n<b>↺ الاسم:</b> <code>{saved['title']}</code>\n<b>↺ الوصف:</b> <code>{saved['desc'][:30]}...</code>\n\n<b>↺ أرسل صورة الغلاف الآن (ستستخدم البيانات المحفوظة تلقائياً).</b>"
    else:
        audio_edit_state[uid] = {'step': 'waiting_for_cover', 'cover_data': None}
        text = MENU_TEXTS["start_audio_edit"]
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
    send_or_edit(call, text, markup, media_key="tools")

@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in audio_edit_state and audio_edit_state[m.from_user.id].get('step') == 'waiting_for_cover')
def handle_cover_photo(message):
    uid = message.from_user.id
    if not message.photo: return
    safe_delete(message.chat.id, message.message_id)
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        cover_data = bot.download_file(file_info.file_path)
        audio_edit_state[uid]['cover_data'] = cover_data
        
        if audio_edit_state[uid].get('artist'):
            audio_edit_state[uid]['step'] = 'waiting_for_audio'
            clear_temp(message.chat.id, uid)
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
            send_temp(message.chat.id, uid, "<b>تم استلام الغلاف ✅</b>\n\n<b>الآن أرسل ملف الصوت MP3.</b>", markup)
        else:
            audio_edit_state[uid]['step'] = 'waiting_for_artist'
            clear_temp(message.chat.id, uid)
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
            msg = send_temp(message.chat.id, uid, "<b>تم استلام الغلاف ✅</b>\n\n<b>الخطوة 2/5: أرسل اسم الفنان:</b>", markup)
            bot.register_next_step_handler(msg, ask_audio_title, uid)
    except Exception as e:
        send_temp(message.chat.id, uid, f"<b>خطأ: {e}</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="menu_tools")))

def ask_audio_title(message, uid):
    safe_delete(message.chat.id, message.message_id)
    if not message.text or uid not in audio_edit_state: return
    if message.text == "إلغاء": return
    audio_edit_state[uid]['artist'] = message.text.strip()
    audio_edit_state[uid]['step'] = 'waiting_for_title'
    clear_temp(message.chat.id, uid)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
    msg = send_temp(message.chat.id, uid, "<b>الخطوة 3/5: أرسل اسم الملف (الأغنية):</b>", markup)
    bot.register_next_step_handler(msg, ask_audio_desc, uid)

def ask_audio_desc(message, uid):
    safe_delete(message.chat.id, message.message_id)
    if not message.text or uid not in audio_edit_state: return
    if message.text == "إلغاء": return
    audio_edit_state[uid]['title'] = message.text.strip()
    audio_edit_state[uid]['step'] = 'waiting_for_desc'
    clear_temp(message.chat.id, uid)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
    msg = send_temp(message.chat.id, uid, "<b>الخطوة 4/5: أرسل الوصف (كليشة الحقوق أسفل الملف):</b>", markup)
    bot.register_next_step_handler(msg, ask_audio_file, uid)

def ask_audio_file(message, uid):
    safe_delete(message.chat.id, message.message_id)
    if not message.text or uid not in audio_edit_state: return
    if message.text == "إلغاء": return
    audio_edit_state[uid]['desc'] = message.text.strip()
    audio_edit_state[uid]['step'] = 'waiting_for_audio'
    clear_temp(message.chat.id, uid)
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
    send_temp(message.chat.id, uid, "<b>الخطوة 5/5: أرسل ملف الصوت MP3 الآن.</b>", markup)

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    uid = message.from_user.id
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_audio':
        safe_delete(message.chat.id, message.message_id)
        file_id = message.audio.file_id if message.content_type == 'audio' else (message.document.file_id if message.document.mime_type == 'audio/mpeg' else None)
        if not file_id: return send_temp(message.chat.id, uid, "<b>أرسل MP3.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="menu_tools")))
        try:
            clear_temp(message.chat.id, uid)
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            cover_data = audio_edit_state[uid].get('cover_data')
            artist = audio_edit_state[uid].get('artist', '@Eror_7')
            title = audio_edit_state[uid].get('title', 'Red World')
            desc = audio_edit_state[uid].get('desc', '')
            
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data, title, artist)
            audio_cache[uid] = {'data': rebuilt, 'cover': cover_jpg, 'artist': artist, 'title': title, 'desc': desc}
            
            markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("حفظ الحقوق والنشر", callback_data=f"save_publish_audio_{uid}"),
                InlineKeyboardButton("النشر بدون حفظ", callback_data=f"publish_only_audio_{uid}"),
                InlineKeyboardButton("التراجع", callback_data="menu_tools"))
            preview_text = f"<b>معاينة الحقوق</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>↺ الفنان:</b> {artist}\n<b>↺ الاسم:</b> {title}\n<b>↺ الوصف:</b> {desc}\n\n<b>هل تريد حفظ هذه البيانات للمرات القادمة؟</b>"
            
            bot.send_audio(message.chat.id, io.BytesIO(rebuilt), title=title, performer=artist, caption=preview_text, thumb=cover_jpg if cover_jpg else None, reply_markup=markup, parse_mode='HTML')
        except Exception as e: 
            send_temp(message.chat.id, uid, f"<b>خطأ: {e}</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="menu_tools")))

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_publish_audio_") or call.data.startswith("publish_only_audio_"))
def publish_audio_action(call):
    action = "save" if call.data.startswith("save") else "only"
    uid = int(call.data.split("_")[-1])
    if uid not in audio_cache: return bot.answer_callback_query(call.id, "انتهت صلاحية الجلسة.", show_alert=True)
    cached = audio_cache[uid]
    target_channel = user_channels.get(str(uid))
    if not target_channel: return bot.answer_callback_query(call.id, "لم تقم بربط قناة! استخدم زر (التحقق من الرفع) أولاً.", show_alert=True)
    try:
        markup_channel = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("Red World | عالم الأحمر", url=CHANNEL_LINK))
        bot.send_audio(target_channel, io.BytesIO(cached['data']), title=cached['title'], performer=cached['artist'], caption=cached['desc'] if cached['desc'] else None, thumb=cached['cover'] if cached['cover'] else None, reply_markup=markup_channel, parse_mode='HTML')
        if action == "save":
            rights_config[str(uid)] = {"artist": cached['artist'], "title": cached['title'], "desc": cached['desc']}
            save_json(RIGHTS_CONFIG_FILE, rights_config)
            bot.answer_callback_query(call.id, "تم حفظ الحقوق والنشر بنجاح ✅", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "تم النشر بدون حفظ الإعدادات.", show_alert=True)
        if uid in audio_cache: del audio_cache[uid]
        if uid in audio_edit_state: del audio_edit_state[uid]
        safe_delete(call.message.chat.id, call.message.message_id)
        markup = get_main_panel(uid)
        send_temp(call.message.chat.id, uid, MENU_TEXTS["main_menu"], markup, media_key="welcome")
    except Exception as e: 
        bot.answer_callback_query(call.id, f"خطأ أثناء النشر: {e}", show_alert=True)

# ==========================================
# 12. الدردشة Gaski والسورس
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "start_chat_gaski")
def start_gaski_chat(call):
    chat_state[call.from_user.id] = True
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إنهاء الدردشة", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["start_chat_gaski"], markup, media_key="chat")

@bot.message_handler(func=lambda m: m.from_user.id in chat_state, content_types=['text', 'photo'])
def handle_chat_message(message):
    if message.text and message.text.startswith('/'): return
    uid = message.from_user.id
    if not bot_settings.get("contact_enabled", True):
        return send_temp(message.chat.id, uid, "<b>عذراً، تم تعطيل التواصل من قبل المطور مؤقتاً.</b>", InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu")))
    safe_delete(message.chat.id, message.message_id)
    clear_temp(message.chat.id, uid)
    msg = send_temp(message.chat.id, uid, "<b>يفكر...</b>")

    try:
        content = []
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            base64_image = base64.b64encode(downloaded_file).decode('utf-8')
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
            user_text = message.caption if message.caption else "ماذا في هذه الصورة؟"
        else:
            user_text = message.text
        system_instruction = "أنت مساعد ذكي. استخدم دائماً النجوم المزدوجة (**النص**) لجعل الكلمات المهمة بخط عريض. اكتب باللغة العربية بأسلوب واضح ومختصر."
        content.append({"type": "text", "text": user_text})

        res = client.chat.completions.create(messages=[{"role": "system", "content": system_instruction}, {"role": "user", "content": content}], model=GROQ_MODEL, max_tokens=500)
        answer = res.choices[0].message.content
        formatted_answer = format_ai_response(answer)
        
        safe_delete(message.chat.id, msg.message_id)
        if uid in temp_messages and msg.message_id in temp_messages[uid]:
            temp_messages[uid].remove(msg.message_id)
            
        sent_reply = bot.send_message(message.chat.id, formatted_answer, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إنهاء الدردشة", callback_data="main_menu")), parse_mode='HTML')
        track_temp(uid, sent_reply.message_id)
    except Exception as e:
        safe_delete(message.chat.id, msg.message_id)
        bot.send_message(message.chat.id, f"<b>خطأ: {e}</b>", parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "show_source")
def show_source(call):
    bot.answer_callback_query(call.id)
    try: dev_name = bot.get_chat(ADMIN_ID).first_name or "Developer"
    except: dev_name = "Developer"
    ch_id = user_channels.get(str(call.from_user.id))
    text = "<b>[ SYSTEM INFO ]</b>\n\n"
    if ch_id:
        try:
            ch = bot.get_chat(ch_id)
            text += f"<b>Channel:</b> {ch.title}\n<b>ID:</b> <code>{ch.id}</code>\n\n"
        except: pass
    text += f"<b>Developer:</b> {dev_name}\n<b>Bot:</b> @{bot.get_me().username}"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    send_or_edit(call, text, markup, media_key="source")

@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    if str(call.from_user.id) in user_channels:
        del user_channels[str(call.from_user.id)]
        save_json("user_channels.json", user_channels)
    bot.answer_callback_query(call.id, "تم فك الارتباط.")
    main_menu(call)

# ==========================================
# 13. التشغيل
# ==========================================
print("Red World Bot is running...")
bot.infinity_polling()
