import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time, json, os, io, re, html
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error as ID3Error
from PIL import Image

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
TELEGRAM_TOKEN = "8180650384:AAHX37rerimsZIWBEc71HleexJKWqSaSsZ0"
GROQ_API_KEY   = "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"
ADMIN_ID = 8456056018
CHANNEL_LINK = "https://t.me/Eror_7"
GROQ_MODEL = "openai/gpt-oss-120b" 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

CONFIG_FILE = "bot_config.json"
audio_edit_state, ad_builder_state = {}, {}
image_gen_state, video_gen_state, chat_state = {}, {}, {}
audio_cache, user_channels, stats, user_settings, pending_posts = {}, {}, {}, {}, {}
media_save_state = {}

# ==========================================
# 2. إدارة الإعدادات والحفظ
# ==========================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channels": [], "media": {"welcome": None, "create": None, "tools": None, "chat": None, "admin": None, "force_sub": None}}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

config_data = load_config()
if "media" not in config_data: 
    config_data["media"] = {"welcome": None, "create": None, "tools": None, "chat": None, "admin": None, "force_sub": None}
if "force_sub" not in config_data["media"]:
    config_data["media"]["force_sub"] = None

def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f: return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

user_channels = load_json("user_channels.json")
stats = load_json("stats.json")
if "published_count" not in stats: stats["published_count"] = 0

def get_default_settings():
    return {"status": "ON", "category": "فلسفي", "language": "عربي", "hashtags": "#RedWorld #عالم_الأحمر"}

# ==========================================
# 3. الكليشات
# ==========================================
MENU_TEXTS = {
    "main_menu": (
        "<b>لوحة التحكم الرئيسية</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>مرحباً بك في مركز إدارة عالم الأحمر.</b>\n\n"
        "<b>↺ إنشاء محتوى:</b> <b>لتصميم منشوراتك.</b>\n"
        "<b>↺ التوليد النصي:</b> <b>لإنشاء إعلاناتك.</b>\n"
        "<b>↺ دردشة Gaski:</b> <b>للتحدث مع الذكاء.</b>\n"
        "<b>↺ السورس:</b> <b>معلومات النظام.</b>\n"
        "<b>↺ مغادرة القناة:</b> <b>لفك الارتباط.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    ),
    "menu_create": (
        "<b>استوديو المحتوى</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>↺ إرسال صورة:</b> <b>لتصميم صورة مع عبارة.</b>\n"
        "<b>↺ إرسال فيديو:</b> <b>لتصميم فيديو مع عبارة.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    ),
    "menu_tools": (
        "<b>أدوات النشر</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>↺ إعلان ترويجي:</b> <b>لبناء إعلان.</b>\n"
        "<b>↺ حقوق النشر:</b> <b>لإضافة غلاف صوتي.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    ),
    "start_chat_gaski": (
        "<b>دردشة Gaski</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>↺ أهلاً بك في العقل المدبر.</b>\n"
        "<b>↺ تحدث معي بحرية.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    ),
    "start_ad_builder": (
        "<b>بروتوكول الإعلان</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>↺ أرسل اسم المجموعة الآن لبدء الإعلان.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    ),
    "start_audio_edit": (
        "<b>ختم الحقوق</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>↺ أرسل صورة الغلاف أولاً.</b>\n"
        "<b>↺ ثم أرسل ملف الصوت MP3.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    ),
    "send_photo_mode": "<b>أرسل الصورة الآن:</b>\n\n<b>↺ سيتم تصميمها وإضافة العبارة.</b>",
    "send_video_mode": "<b>أرسل الفيديو الآن:</b>\n\n<b>↺ سيتم تصميمه وإضافة العبارة.</b>",
    "waiting_for_photo": "<b>في انتظار الصورة:</b>\n\n<b>↺ يرجى إرسال الصورة الآن.</b>",
    "waiting_for_video": "<b>في انتظار الفيديو:</b>\n\n<b>↺ يرجى إرسال الفيديو الآن.</b>",
    "welcome": (
        "<b>بوابة عالم الأحمر</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>مرحباً بك في R W | Bot</b>\n\n"
        "<b>↺ تصميم المحتوى:</b> <b>صور وفيديوهات.</b>\n"
        "<b>↺ التوليد النصي:</b> <b>إعلانات وحقوق.</b>\n"
        "<b>↺ حماية القنوات:</b> <b>اشتراك إجباري.</b>\n"
        "<b>↺ دردشة مباشرة:</b> <b>مع الذكاء الاصطناعي.</b>\n\n"
        "<b>↺ اضغط على زر لوحة التحكم للبدء.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    ),
    "admin_panel": (
        "<b>لوحة المطور</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>↺ الإحصائيات:</b> <b>أرقام البوت.</b>\n"
        "<b>↺ قنوات الاشتراك:</b> <b>إدارة القنوات.</b>\n"
        "<b>↺ إعدادات الوسائط:</b> <b>كليشات البوت.</b>\n"
        "<b>↺ الإذاعة:</b> <b>رسالة للجميع.</b>\n\n"
        "<b>━━━━━━━━━━━━━━━━━━━━</b>"
    )
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

def rebuild_audio_with_cover(original_audio_bytes, cover_bytes):
    try:
        audio_buffer = io.BytesIO(original_audio_bytes)
        audio = MP3(audio_buffer, ID3=ID3)
        try: audio.delete()
        except ID3Error: pass
        audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text="Red World"))
        audio.tags.add(TPE1(encoding=3, text="@Eror_7"))
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

def send_panel(chat_id, text, markup, media_key=None):
    file_id = config_data.get("media", {}).get(media_key) if media_key else None
    if file_id:
        try:
            bot.send_photo(chat_id, file_id, caption=text, reply_markup=markup, parse_mode='HTML')
            return
        except:
            try:
                bot.send_video(chat_id, file_id, caption=text, reply_markup=markup, parse_mode='HTML')
                return
            except: pass
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

def send_or_edit(call, text, markup, media_key=None):
    safe_delete(call.message.chat.id, call.message.message_id)
    send_panel(call.message.chat.id, text, markup, media_key)

# ==========================================
# 5. أوامر البداية والاشتراك
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    mention = get_mention(message.from_user)
    
    if user_id != ADMIN_ID and not check_subscription(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        for ch in config_data.get("channels", []):
            markup.add(InlineKeyboardButton(f"اشترك في {ch['name']}", url=f"https://t.me/{ch['id'].replace('@', '')}"))
        markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_sub"))
        return send_panel(message.chat.id, f"<b>بوابة مغلقة</b>\n\n<b>عذراً {mention}، يجب عليك الاشتراك في القنوات التالية أولاً لتتمكن من استخدام البوت.</b>", markup, media_key="force_sub")
    
    if user_id not in user_settings: user_settings[user_id] = get_default_settings()
    
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel"),
        InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
    
    welcome_text = MENU_TEXTS["welcome"].replace("مرحباً بك", f"مرحباً بك {mention}")
    send_panel(message.chat.id, welcome_text, markup, media_key="welcome")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "تم التحقق بنجاح!", show_alert=True)
        safe_delete(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)
    else: 
        bot.answer_callback_query(call.id, "لم تشترك في جميع القنوات بعد.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id, "جاري الفحص...")
    channel_id = user_channels.get(str(call.from_user.id))
    if not channel_id:
        safe_delete(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "<b>أرسل معرف القناة:</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="main_menu")), parse_mode='HTML')
        bot.register_next_step_handler(msg, manual_verify, call.from_user.id, msg.message_id)
    else: 
        perform_verification(call.message.chat.id, call.from_user.id, channel_id, call.message.message_id)

def manual_verify(message, user_id, msg_id_to_delete):
    if message.text == "إلغاء": return
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    user_channels[str(user_id)] = channel_input
    save_json("user_channels.json", user_channels)
    safe_delete(message.chat.id, message.message_id)
    safe_delete(message.chat.id, msg_id_to_delete)
    perform_verification(message.chat.id, user_id, channel_input, None)

def perform_verification(chat_id, user_id, channel_id, msg_id_to_delete):
    msg = bot.send_message(chat_id, "<b>جاري الفحص...</b>", parse_mode='HTML')
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        if bot_member.status in ['administrator', 'creator'] and getattr(bot_member, 'can_post_messages', False):
            safe_delete(chat_id, msg.message_id)
            if msg_id_to_delete: safe_delete(chat_id, msg_id_to_delete)
            markup = get_main_panel(user_id)
            send_panel(chat_id, MENU_TEXTS["main_menu"], markup, media_key="welcome")
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
        InlineKeyboardButton("إنشاء محتوى (صورة/فيديو)", callback_data="menu_create"), 
        InlineKeyboardButton("التوليد النصي والإعلانات", callback_data="menu_tools"), 
        InlineKeyboardButton("دردشة Gaski", callback_data="start_chat_gaski"), 
        InlineKeyboardButton("السورس", callback_data="show_source"),
        InlineKeyboardButton("مغادرة القناة", callback_data="leave_channel")
    )
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("لوحة تحكم المطور", callback_data="admin_panel"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    bot.answer_callback_query(call.id)
    markup = get_main_panel(call.from_user.id)
    send_or_edit(call, MENU_TEXTS["main_menu"], markup, media_key="welcome")

# ==========================================
# 7. لوحة تحكم المطور
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    if call.from_user.id != ADMIN_ID: return bot.answer_callback_query(call.id, "للمطور فقط!", show_alert=True)
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("الإحصائيات", callback_data="admin_stats"),
        InlineKeyboardButton("قنوات الاشتراك", callback_data="admin_channels"),
        InlineKeyboardButton("إعدادات الوسائط", callback_data="admin_media_settings"),
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

# ==========================================
# 8. إعدادات الوسائط
# ==========================================
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
    
    safe_delete(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ==========================================
# 9. إدارة الاشتراك الإجباري
# ==========================================
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
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    bot.register_next_step_handler(msg, save_new_channel, msg.message_id)

def save_new_channel(message, msg_id_to_delete):
    if message.from_user.id != ADMIN_ID: return
    if message.text and message.text == "إلغاء": return
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    
    try:
        chat = bot.get_chat(channel_input)
        channel_name = chat.title
    except:
        channel_name = channel_input
        
    config_data["channels"].append({"id": channel_input, "name": channel_name})
    save_config(config_data)
    
    safe_delete(message.chat.id, message.message_id)
    safe_delete(message.chat.id, msg_id_to_delete)
    bot.send_message(message.chat.id, f"<b>تم إضافة القناة:</b> {channel_name}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_channels")), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>الإذاعة</b>\n<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n<b>أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين.</b>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="admin_panel"))
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    bot.register_next_step_handler(msg, do_broadcast, msg.message_id)

def do_broadcast(message, msg_id_to_delete):
    if message.from_user.id != ADMIN_ID: return
    if message.text and message.text == "إلغاء": return
    success, failed = 0, 0
    msg = bot.send_message(message.chat.id, "<b>جاري الإذاعة...</b>", parse_mode='HTML')
    for uid in user_settings.keys():
        try:
            bot.send_message(uid, f"<b>إعلان من المطور:</b>\n\n{message.text}", parse_mode='HTML')
            success += 1
            time.sleep(0.1)
        except: failed += 1
    safe_delete(message.chat.id, message.message_id)
    safe_delete(message.chat.id, msg_id_to_delete)
    bot.edit_message_text(f"<b>تم الإرسال لـ {success} مستخدم.\nفشل لـ {failed}.</b>", chat_id=message.chat.id, message_id=msg.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_panel")), parse_mode='HTML')

# ==========================================
# 10. إنشاء المحتوى
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "menu_create")
def menu_create(call):
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("إرسال صورة", callback_data="send_photo_mode"),
        InlineKeyboardButton("إرسال فيديو", callback_data="send_video_mode"),
        InlineKeyboardButton("رجوع", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["menu_create"], markup, media_key="create")

@bot.callback_query_handler(func=lambda call: call.data == "send_photo_mode")
def trigger_photo_mode(call):
    image_gen_state[call.from_user.id] = {'step': 'waiting_for_photo'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_create"))
    send_or_edit(call, MENU_TEXTS["waiting_for_photo"], markup)

@bot.callback_query_handler(func=lambda call: call.data == "send_video_mode")
def trigger_video_mode(call):
    video_gen_state[call.from_user.id] = {'step': 'waiting_for_video'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="menu_create"))
    send_or_edit(call, MENU_TEXTS["waiting_for_video"], markup)

# ==========================================
# 11. معالج الوسائط الشامل
# ==========================================
@bot.message_handler(content_types=['photo', 'video', 'video_note'])
def handle_media(message):
    uid = message.from_user.id
    
    if uid == ADMIN_ID and uid in media_save_state:
        state = media_save_state[uid]
        key = state['key']
        mtype = state['type']
        
        file_id = None
        if mtype == "photo" and message.photo: file_id = message.photo[-1].file_id
        elif mtype == "video":
            if message.video: file_id = message.video.file_id
            elif message.video_note: file_id = message.video_note.file_id
            
        if not file_id:
            return bot.reply_to(message, "<b>نوع الملف غير صحيح. يرجى إرسال الصورة أو الفيديو المطلوب.</b>", parse_mode='HTML')
            
        config_data["media"][key] = file_id
        save_config(config_data)
        del media_save_state[uid]
        
        safe_delete(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "<b>تم حفظ الوسائط بنجاح.</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="admin_media_settings")), parse_mode='HTML')
        return

    if uid in image_gen_state and image_gen_state[uid].get('step') == 'waiting_for_photo':
        if message.photo:
            safe_delete(message.chat.id, message.message_id)
            image_gen_state[uid]['file_id'] = message.photo[-1].file_id
            image_gen_state[uid]['step'] = 'waiting_category'
            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("حزين", callback_data="img_cat_حزين"), 
                InlineKeyboardButton("فلسفي", callback_data="img_cat_فلسفي"),
                InlineKeyboardButton("حب", callback_data="img_cat_حب"), 
                InlineKeyboardButton("اقتباس", callback_data="img_cat_اقتباس"),
                InlineKeyboardButton("اشتياق", callback_data="img_cat_اشتياق"),
                InlineKeyboardButton("خذلان", callback_data="img_cat_خذلان"),
                InlineKeyboardButton("وحدة", callback_data="img_cat_وحدة"),
                InlineKeyboardButton("صمود", callback_data="img_cat_صمود"),
                InlineKeyboardButton("غموض", callback_data="img_cat_غموض"),
                InlineKeyboardButton("أمل", callback_data="img_cat_أمل"),
                InlineKeyboardButton("عتاب", callback_data="img_cat_عتاب"),
                InlineKeyboardButton("سخرية", callback_data="img_cat_سخرية"),
                InlineKeyboardButton("ندم", callback_data="img_cat_ندم"),
                InlineKeyboardButton("تحدي", callback_data="img_cat_تحدي"),
                InlineKeyboardButton("ذكرى", callback_data="img_cat_ذكرى"),
                InlineKeyboardButton("صمت", callback_data="img_cat_صمت"),
                InlineKeyboardButton("رجوع", callback_data="menu_create")
            )
            bot.send_message(message.chat.id, "<b>اختر الفئة:</b>", reply_markup=markup, parse_mode='HTML')
            return

    if uid in video_gen_state and video_gen_state[uid].get('step') == 'waiting_for_video':
        if message.video or message.video_note:
            safe_delete(message.chat.id, message.message_id)
            file_id = message.video.file_id if message.video else message.video_note.file_id
            video_gen_state[uid]['file_id'] = file_id
            video_gen_state[uid]['step'] = 'waiting_category'
            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("حزين", callback_data="vid_cat_حزين"), 
                InlineKeyboardButton("فلسفي", callback_data="vid_cat_فلسفي"),
                InlineKeyboardButton("حب", callback_data="vid_cat_حب"), 
                InlineKeyboardButton("اقتباس", callback_data="vid_cat_اقتباس"),
                InlineKeyboardButton("رجوع", callback_data="menu_create"))
            bot.send_message(message.chat.id, "<b>اختر الفئة:</b>", reply_markup=markup, parse_mode='HTML')
            return

# ==========================================
# 12. باقي الأزرار
# ==========================================
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
    send_or_edit(call, text, markup)

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
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("img_fmt_") or call.data.startswith("vid_fmt_"))
def media_format_and_publish(call):
    uid = call.from_user.id
    is_img = call.data.startswith("img_fmt_")
    fmt = call.data.split("_")[-1]
    if is_img and uid in image_gen_state: state = image_gen_state[uid]; file_id = state['file_id']; category = state.get('category', 'فلسفي'); lang = state.get('language', 'عربي'); media_type = 'photo'
    elif not is_img and uid in video_gen_state: state = video_gen_state[uid]; file_id = state['file_id']; category = state.get('category', 'فلسفي'); lang = state.get('language', 'عربي'); media_type = 'video'
    else: return bot.answer_callback_query(call.id, "انتهت الجلسة.", show_alert=True)
    
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, "<b>جاري توليد العبارة...</b>", parse_mode='HTML')
    
    lang_instr = "جملة عربية قصيرة ثم ترجمتها الإنجليزية في السطر التالي" if lang == "مختلط" else "باللغة العربية الفصحى"
    prompt = f"اكتب عبارة قصيرة جداً من سطر واحد بأسلوب {category} ({lang_instr}). بدون إيموجي."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=150)
        raw_text = res.choices[0].message.content.strip()
    except: raw_text = "عبارة تجريبية."
    final_text = f"<i>{raw_text}</i>" if fmt == "italic" else f"<b>{raw_text}</b>"
    settings = user_settings.get(uid, get_default_settings())
    final_caption = f"<b>{final_text}</b>\n\n<b>{settings.get('hashtags', '')}</b>"
    
    post_id = str(int(time.time()))
    pending_posts[post_id] = {'type': media_type, 'file_id': file_id, 'caption': final_caption, 'channel': user_channels.get(str(uid)), 'category': category, 'language': lang, 'format': fmt, 'is_img': is_img, 'custom_button': None}
    
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة زر مخصص للمنشور", callback_data=f"add_btn_{post_id}"),
        InlineKeyboardButton("تغيير العبارة", callback_data=f"change_caption_{post_id}"),
        InlineKeyboardButton("تخطي وإكمال النشر", callback_data=f"confirm_{post_id}"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu")
    )
    
    safe_delete(call.message.chat.id, msg.message_id)
    if media_type == 'photo': bot.send_photo(call.message.chat.id, file_id, caption=f"<b>معاينة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(call.message.chat.id, file_id, caption=f"<b>معاينة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("change_caption_"))
def change_caption(call):
    post_id = call.data.split("_")[2]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    data = pending_posts[post_id]
    
    bot.answer_callback_query(call.id, "جاري توليد عبارة جديدة...")
    category = data.get('category', 'فلسفي'); lang = data.get('language', 'عربي'); fmt = data.get('format', 'bold'); file_id = data['file_id']; media_type = data['type']
    lang_instr = "جملة عربية قصيرة ثم ترجمتها الإنجليزية في السطر التالي" if lang == "مختلط" else "باللغة العربية الفصحى"
    prompt = f"اكتب عبارة قصيرة جداً بأسلوب {category} ({lang_instr}). بدون إيموجي."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=150)
        raw_text = res.choices[0].message.content.strip()
    except: raw_text = "عبارة تجريبية."
    final_text = f"<i>{raw_text}</i>" if fmt == "italic" else f"<b>{raw_text}</b>"
    settings = user_settings.get(call.from_user.id, get_default_settings())
    final_caption = f"<b>{final_text}</b>\n\n<b>{settings.get('hashtags', '')}</b>"
    data['caption'] = final_caption
    pending_posts[post_id] = data
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة زر مخصص للمنشور", callback_data=f"add_btn_{post_id}"),
        InlineKeyboardButton("تغيير العبارة", callback_data=f"change_caption_{post_id}"),
        InlineKeyboardButton("تخطي وإكمال النشر", callback_data=f"confirm_{post_id}"),
        InlineKeyboardButton("إلغاء", callback_data="main_menu")
    )
    safe_delete(call.message.chat.id, call.message.message_id)
    if media_type == 'photo': bot.send_photo(call.message.chat.id, file_id, caption=f"<b>معاينة جديدة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(call.message.chat.id, file_id, caption=f"<b>معاينة جديدة</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_btn_"))
def ask_button_text(call):
    post_id = call.data.split("_")[2]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    
    bot.answer_callback_query(call.id)
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, "<b>أرسل اسم الزر (النص الذي سيظهر عليه):</b>\n\n<b>مثال: انضم للقناة</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu")), parse_mode='HTML')
    bot.register_next_step_handler(msg, ask_button_link, post_id, msg.message_id)

def ask_button_link(message, post_id, msg_id_to_delete):
    if message.text == "إلغاء": return
    if post_id not in pending_posts: return
    pending_posts[post_id]['temp_btn_text'] = message.text.strip()
    
    safe_delete(message.chat.id, message.message_id)
    safe_delete(message.chat.id, msg_id_to_delete)
    msg = bot.send_message(message.chat.id, "<b>أرسل رابط الزر (يجب أن يبدأ بـ http أو https):</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu")), parse_mode='HTML')
    bot.register_next_step_handler(msg, save_button_and_preview, post_id, msg.message_id)

def save_button_and_preview(message, post_id, msg_id_to_delete):
    if message.text == "إلغاء": return
    if post_id not in pending_posts: return
    
    link = message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        return bot.send_message(message.chat.id, "<b>الرابط غير صحيح. يجب أن يبدأ بـ http أو https.</b>")
        
    data = pending_posts[post_id]
    data['custom_button'] = {'text': data['temp_btn_text'], 'url': link}
    
    safe_delete(message.chat.id, message.message_id)
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
# 13. معالجات إضافية (تمت إضافتها)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "menu_tools")
def menu_tools(call):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إنشاء إعلان ترويجي", callback_data="start_ad_builder"),
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit"),
        InlineKeyboardButton("رجوع", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["menu_tools"], markup, media_key="tools")

@bot.callback_query_handler(func=lambda call: call.data == "start_chat_gaski")
def start_gaski_chat(call):
    chat_state[call.from_user.id] = True
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إنهاء الدردشة", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["start_chat_gaski"], markup, media_key="chat")

@bot.message_handler(func=lambda m: m.from_user.id in chat_state, content_types=['text'])
def handle_chat_message(message):
    if message.text.startswith('/'): return
    msg = bot.reply_to(message, "<b>يفكر...</b>", parse_mode='HTML')
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": message.text}], model=GROQ_MODEL, max_tokens=500)
        bot.edit_message_text(res.choices[0].message.content, chat_id=message.chat.id, message_id=msg.message_id)
    except Exception as e: bot.edit_message_text(f"<b>خطأ: {e}</b>", chat_id=message.chat.id, message_id=msg.message_id, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    audio_edit_state[call.from_user.id] = {'step': 'waiting_for_cover', 'cover_data': None}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
    send_or_edit(call, MENU_TEXTS["start_audio_edit"], markup)

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    uid = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_audio':
        file_id = message.audio.file_id if message.content_type == 'audio' else (message.document.file_id if message.document.mime_type == 'audio/mpeg' else None)
        if not file_id: return bot.reply_to(message, "<b>أرسل MP3.</b>", parse_mode='HTML')
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            cover_data = audio_edit_state[uid].get('cover_data')
            if not cover_data: return bot.reply_to(message, "<b>لم يتم العثور على الغلاف.</b>", parse_mode='HTML')
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data)
            audio_cache[uid] = {'data': rebuilt, 'cover': cover_jpg}
            markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{uid}"), InlineKeyboardButton("رجوع", callback_data="main_menu"))
            bot.send_audio(message.chat.id, io.BytesIO(rebuilt), title="Red World", performer="@Eror_7", thumb=cover_jpg if cover_jpg else None)
            bot.send_message(message.chat.id, "<b>جاهز للنشر</b>", reply_markup=markup, parse_mode='HTML')
            del audio_edit_state[uid]
        except Exception as e: bot.send_message(message.chat.id, f"<b>خطأ: {e}</b>", parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_standalone_audio_"))
def publish_standalone_audio(call):
    uid = int(call.data.split("_")[3])
    target_channel = user_channels.get(str(uid))
    if not target_channel or uid not in audio_cache: return bot.answer_callback_query(call.id, "خطأ.", show_alert=True)
    try:
        cached = audio_cache[uid]
        markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("Red World | عالم الأحمر", url=CHANNEL_LINK))
        bot.send_audio(target_channel, io.BytesIO(cached['data']), title="Red World", performer="@Eror_7", thumb=cached['cover'] if cached['cover'] else None, reply_markup=markup)
        bot.answer_callback_query(call.id, "تم النشر.")
        if uid in audio_cache: del audio_cache[uid]
        main_menu(call)
    except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

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
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    if str(call.from_user.id) in user_channels:
        del user_channels[str(call.from_user.id)]
        save_json("user_channels.json", user_channels)
    bot.answer_callback_query(call.id, "تم فك الارتباط.")
    main_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    ad_builder_state[call.from_user.id] = {'step': 'waiting_group_name'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="menu_tools"))
    send_or_edit(call, MENU_TEXTS["start_ad_builder"], markup)

@bot.message_handler(func=lambda m: m.from_user.id in ad_builder_state)
def ad_step_handler(message):
    uid = message.from_user.id
    data = ad_builder_state[uid]
    step = data.get('step')
    if step == 'waiting_group_name':
        if message.text and message.text == "إلغاء": return
        data['group_name'] = message.text.strip()
        data['step'] = 'waiting_group_type'
        safe_delete(message.chat.id, message.message_id)
        markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("تمبلر", callback_data="ad_type_تمبلر"), InlineKeyboardButton("فري", callback_data="ad_type_فري"), InlineKeyboardButton("مزج", callback_data="ad_type_مزج"), InlineKeyboardButton("إلغاء", callback_data="main_menu"))
        bot.send_message(message.chat.id, "<b>الخطوة 2/7: اختر نوع المجموعة:</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_set_type(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[uid]['step'] = 'waiting_group_link'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    send_or_edit(call, "<b>الخطوة 3/7: أرسل رابط المجموعة:</b>", markup)

# ==========================================
# 14. التشغيل
# ==========================================
print("Red World Bot is running...")
bot.infinity_polling()
