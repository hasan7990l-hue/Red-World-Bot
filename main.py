import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time, json, os, io, re
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
image_gen_state, video_gen_state, chat_state, welcome_media_state = {}, {}, {}, {}
audio_cache, user_channels, stats, user_settings, pending_posts = {}, {}, {}, {}, {}

# ==========================================
# 2. إدارة الإعدادات والحفظ
# ==========================================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channels": ["@Eror_7", "@lb2_c"], "media": {"welcome": None, "create": None, "tools": None, "chat": None, "admin": None}}

def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

config_data = load_config()
if "media" not in config_data: config_data["media"] = {"welcome": None, "create": None, "tools": None, "chat": None, "admin": None}

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
# 3. النصوص التعليمية (الكلايش)
# ==========================================
MENU_TEXTS = {
    "main_menu": "<b>⟨ لوحة التحكم الرئيسية ⟩</b>\n────────────────────\n\n<blockquote>مرحباً بك في مركز إدارة عالم الأحمر.\n\n• <b>إنشاء محتوى:</b> لتصميم منشورات (صورة/فيديو).\n• <b>التوليد النصي:</b> لإنشاء إعلانات وحقوق صوتية.\n• <b>دردشة Gaski:</b> للتحدث مع الذكاء الاصطناعي.\n• <b>السورس:</b> معلومات النظام.</blockquote>",
    "menu_create": "<b>⟨ استوديو المحتوى ⟩</b>\n────────────────────\n\n<blockquote>من هنا يمكنك إنشاء منشوراتك.\nاختر إرسال صورة أو فيديو، وسيقوم الذكاء الاصطناعي بتوليد عبارة مناسبة لك بناءً على الفئة التي تختارها.</blockquote>",
    "menu_tools": "<b>⟨ أدوات التوليد والنشر ⟩</b>\n────────────────────\n\n<blockquote>هنا تجد أدوات التوليد النصي، وبناء الإعلانات، وختم الحقوق الصوتية.</blockquote>",
    "start_chat_gaski": "<b>⟨ دردشة Gaski ⟩</b>\n────────────────────\n\n<blockquote>أهلاً بك في العقل المدبر.\nتحدث معي بحرية، اسألني أي شيء.</blockquote>",
    "start_ad_builder": "<b>⟨ بروتوكول الإعلان ⟩</b>\n────────────────────\n\n<blockquote>سنقوم ببناء إعلان احترافي لمجموعتك.</blockquote>",
    "start_audio_edit": "<b>⟨ ختم الحقوق الصوتي ⟩</b>\n────────────────────\n\n<blockquote>أرسل صورة الغلاف أولاً، ثم أرسل ملف الصوت MP3.</blockquote>",
    "send_photo_mode": "<b>⟨ إرسال صورة ⟩</b>\n────────────────────\n\n<blockquote>أرسل الصورة التي تريد إنشاء عبارة عليها.</blockquote>",
    "send_video_mode": "<b>⟨ إرسال فيديو ⟩</b>\n────────────────────\n\n<blockquote>أرسل الفيديو الذي تريد إنشاء عبارة عليه.</blockquote>",
    "waiting_for_photo": "<b>⟨ في انتظار الصورة ⟩</b>\n────────────────────\n\n<blockquote>يرجى إرسال الصورة الآن.</blockquote>",
    "waiting_for_video": "<b>⟨ في انتظار الفيديو ⟩</b>\n────────────────────\n\n<blockquote>يرجى إرسال الفيديو الآن.</blockquote>",
    "welcome": "<b>⟨ بوابة عالم الأحمر ⟩</b>\n────────────────────\n\n<blockquote>مرحباً بك في <b>R W | Bot</b>\nالنظام المتكامل لإدارة قنوات تيليجرام باحترافية.</blockquote>\n\n<i>اضغط على زر لوحة التحكم للبدء.</i>",
    "admin_panel": "<b>🛡️ لوحة التحكم الأمنية</b>\n────────────────────\n\n<blockquote>مرحباً بك أيها المالك.\nمن هنا يمكنك التحكم في إعدادات البوت، قنوات الاشتراك، والوسائط.</blockquote>"
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
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def safe_delete(chat_id, message_id):
    try: bot.delete_message(chat_id, message_id)
    except: pass

def send_or_edit(call, text, markup, media_key=None):
    """دالة ذكية: تحذف الرسالة السابقة وترسل رسالة جديدة (صورة أو نص)"""
    safe_delete(call.message.chat.id, call.message.message_id)
    file_id = config_data.get("media", {}).get(media_key) if media_key else None
    if file_id:
        try:
            bot.send_photo(call.message.chat.id, file_id, caption=text, reply_markup=markup, parse_mode='HTML')
            return
        except:
            try:
                bot.send_video(call.message.chat.id, file_id, caption=text, reply_markup=markup, parse_mode='HTML')
                return
            except: pass
    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ==========================================
# 5. أوامر البداية والاشتراك
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    
    if user_id != ADMIN_ID and not check_subscription(user_id):
        markup = InlineKeyboardMarkup(row_width=1)
        for ch in config_data.get("channels", []):
            markup.add(InlineKeyboardButton(f"اشترك في {ch}", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
        return bot.send_message(message.chat.id, "<b>⛔ بوابة مغلقة</b>\n\nعذراً، يجب عليك الاشتراك في القنوات التالية أولاً لتتمكن من استخدام البوت.", reply_markup=markup, parse_mode='HTML')
    
    if user_id not in user_settings: user_settings[user_id] = get_default_settings()
    
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة البوت لقناتك", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
        InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel"),
        InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
    
    file_id = config_data.get("media", {}).get("welcome")
    if file_id:
        try: bot.send_photo(message.chat.id, file_id, caption=MENU_TEXTS["welcome"], reply_markup=markup, parse_mode='HTML')
        except: bot.send_video(message.chat.id, file_id, caption=MENU_TEXTS["welcome"], reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, MENU_TEXTS["welcome"], reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح!", show_alert=True)
        safe_delete(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)
    else: 
        bot.answer_callback_query(call.id, "❌ لم تشترك في جميع القنوات بعد.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id, "جاري الفحص...")
    channel_id = user_channels.get(str(call.from_user.id))
    if not channel_id:
        safe_delete(call.message.chat.id, call.message.message_id)
        msg = bot.send_message(call.message.chat.id, "<b>أرسل معرف القناة:</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء والرجوع", callback_data="main_menu")), parse_mode='HTML')
        bot.register_next_step_handler(msg, manual_verify, call.from_user.id)
    else: 
        perform_verification(call.message.chat.id, call.from_user.id, channel_id)

def manual_verify(message, user_id):
    if message.text == "إلغاء": return
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    user_channels[str(user_id)] = channel_input
    save_json("user_channels.json", user_channels)
    perform_verification(message.chat.id, user_id, channel_input)

def perform_verification(chat_id, user_id, channel_id):
    msg = bot.send_message(chat_id, "<i>جاري الفحص...</i>", parse_mode='HTML')
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        if bot_member.status in ['administrator', 'creator'] and getattr(bot_member, 'can_post_messages', False):
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("لوحة التحكم", callback_data="main_menu"))
            bot.edit_message_text(f"<b>تم التحقق:</b> {chat_info.title}", chat_id=chat_id, message_id=msg.message_id, reply_markup=markup, parse_mode='HTML')
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
        markup.add(InlineKeyboardButton("🛡️ لوحة تحكم المطور", callback_data="admin_panel"))
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
        InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
        InlineKeyboardButton("📡 قنوات الاشتراك", callback_data="admin_channels"),
        InlineKeyboardButton("🖼️ إعدادات الوسائط", callback_data="admin_media_settings"),
        InlineKeyboardButton("📢 الإذاعة", callback_data="admin_broadcast"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
    )
    send_or_edit(call, MENU_TEXTS["admin_panel"], markup, media_key="admin")

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if call.from_user.id != ADMIN_ID: return
    total_users = len(user_settings)
    posts = stats.get("published_count", 0)
    channels_count = len(config_data.get("channels", []))
    text = f"<b>📊 إحصائيات البوت</b>\n────────────────────\n\n<b>- إجمالي المستخدمين:</b> <code>{total_users}</code>\n<b>- المنشورات:</b> <code>{posts}</code>\n<b>- قنوات الاشتراك:</b> <code>{channels_count}</code>\n<b>- الحالة:</b> ✅ يعمل بكفاءة"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
    send_or_edit(call, text, markup)

# ==========================================
# 8. إعدادات الوسائط (المطور)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "admin_media_settings")
def admin_media_settings(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>🖼️ إعدادات الوسائط</b>\n────────────────────\n\n<blockquote>اختر القسم الذي تريد تعيين صورة أو فيديو له:</blockquote>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("كليشة الترحيب", callback_data="media_set_welcome"),
        InlineKeyboardButton("كليشة إنشاء محتوى", callback_data="media_set_create"),
        InlineKeyboardButton("كليشة الأدوات والإعلانات", callback_data="media_set_tools"),
        InlineKeyboardButton("كليشة دردشة Gaski", callback_data="media_set_chat"),
        InlineKeyboardButton("كليشة لوحة التحكم", callback_data="media_set_admin"),
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("media_set_"))
def media_set_choice(call):
    if call.from_user.id != ADMIN_ID: return
    key = call.data.replace("media_set_", "")
    text = f"<b>🖼️ تعيين وسائط لـ {key}</b>\n────────────────────\n\n<blockquote>هل تريد تعيين صورة أم فيديو؟</blockquote>"
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("📷 صورة", callback_data=f"media_upload_{key}_photo"),
        InlineKeyboardButton("🎬 فيديو", callback_data=f"media_upload_{key}_video"),
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_media_settings")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("media_upload_"))
def media_upload_choice(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    key = parts[2]
    media_type = parts[3]
    
    text = f"<b>📤 أرسل الـ{media_type} الآن</b>\n────────────────────\n\n<blockquote>سيتم حفظ الوسائط وتعيينها.</blockquote>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="admin_media_settings"))
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    bot.register_next_step_handler(msg, save_media, key, media_type)

def save_media(message, key, media_type):
    if message.from_user.id != ADMIN_ID: return
    if message.text and message.text == "إلغاء": return
    
    if media_type == "photo" and message.photo:
        file_id = message.photo[-1].file_id
    elif media_type == "video" and message.video:
        file_id = message.video.file_id
    else:
        return bot.send_message(message.chat.id, "❌ نوع الملف غير صحيح. يرجى إرسال الصورة أو الفيديو المطلوب.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_media_settings")))
        
    config_data["media"][key] = file_id
    save_config(config_data)
    safe_delete(message.chat.id, message.message_id)
    bot.send_message(message.chat.id, "✅ تم حفظ الوسائط بنجاح.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_media_settings")))

# ==========================================
# 9. إدارة الاشتراك الإجباري (المطور)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "admin_channels")
def admin_channels(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>📡 إدارة قنوات الاشتراك الإجباري</b>\n────────────────────\n\n<blockquote>اختر القناة للإدارة أو أضف قناة جديدة.</blockquote>"
    markup = InlineKeyboardMarkup(row_width=1)
    channels = config_data.get("channels", [])
    for i, ch in enumerate(channels):
        markup.add(InlineKeyboardButton(f"📢 {ch}", callback_data=f"manage_ch_{i}"))
    markup.add(InlineKeyboardButton("➕ إضافة قناة جديدة", callback_data="add_ch"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("manage_ch_"))
def manage_channel(call):
    if call.from_user.id != ADMIN_ID: return
    idx = int(call.data.split("_")[2])
    channels = config_data.get("channels", [])
    if idx >= len(channels): return
    ch = channels[idx]
    
    text = f"<b>📢 إدارة القناة: {ch}</b>\n────────────────────\n\n<blockquote>اختر الإجراء المطلوب:</blockquote>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔗 دخول للقناة", url=f"https://t.me/{ch.replace('@', '')}"),
        InlineKeyboardButton("❌ حذف القناة", callback_data=f"del_ch_{idx}"),
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_channels")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_ch_"))
def del_ch(call):
    if call.from_user.id != ADMIN_ID: return
    idx = int(call.data.split("_")[2])
    channels = config_data.get("channels", [])
    if idx >= len(channels): return
    ch = channels[idx]
    
    text = f"<b>⚠️ تأكيد الحذف</b>\n────────────────────\n\n<blockquote>هل أنت متأكد من حذف القناة {ch}؟</blockquote>"
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_del_{idx}"),
        InlineKeyboardButton("❌ لا، إلغاء", callback_data="admin_channels")
    )
    send_or_edit(call, text, markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_del_"))
def confirm_del(call):
    if call.from_user.id != ADMIN_ID: return
    idx = int(call.data.split("_")[2])
    config_data["channels"].pop(idx)
    save_config(config_data)
    bot.answer_callback_query(call.id, "✅ تم حذف القناة بنجاح.")
    admin_channels(call)

@bot.callback_query_handler(func=lambda call: call.data == "add_ch")
def add_ch(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>➕ إضافة قناة جديدة</b>\n────────────────────\n\n<blockquote>أرسل يوزر القناة الآن (مثال: @MyChannel).</blockquote>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="admin_channels"))
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    bot.register_next_step_handler(msg, save_new_channel)

def save_new_channel(message):
    if message.from_user.id != ADMIN_ID: return
    if message.text and message.text == "إلغاء": return
    channel = message.text.strip()
    if not channel.startswith('@'): channel = '@' + channel
    
    config_data["channels"].append(channel)
    save_config(config_data)
    safe_delete(message.chat.id, message.message_id)
    bot.send_message(message.chat.id, f"<b>✅ تم إضافة القناة:</b> {channel}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_channels")), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if call.from_user.id != ADMIN_ID: return
    text = "<b>📢 الإذاعة</b>\n────────────────────\n\n<blockquote>أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين.</blockquote>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="admin_panel"))
    safe_delete(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    bot.register_next_step_handler(msg, do_broadcast)

def do_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    if message.text and message.text == "إلغاء": return
    success, failed = 0, 0
    msg = bot.send_message(message.chat.id, "<b>⏳ جاري الإذاعة...</b>", parse_mode='HTML')
    for uid in user_settings.keys():
        try:
            bot.send_message(uid, f"<b>📢 إعلان من المطور:</b>\n\n{message.text}", parse_mode='HTML')
            success += 1
            time.sleep(0.1)
        except: failed += 1
    bot.edit_message_text(f"<b>✅ تم الإرسال لـ {success} مستخدم.\n❌ فشل لـ {failed}.</b>", chat_id=message.chat.id, message_id=msg.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")), parse_mode='HTML')

# ==========================================
# 10. أزرار البوت والفئات
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "menu_create")
def menu_create(call):
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("إرسال صورة", callback_data="send_photo_mode"),
        InlineKeyboardButton("إرسال فيديو", callback_data="send_video_mode"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["menu_create"], markup, media_key="create")

@bot.callback_query_handler(func=lambda call: call.data == "menu_tools")
def menu_tools(call):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إنشاء إعلان ترويجي", callback_data="start_ad_builder"),
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit"),
        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["menu_tools"], markup, media_key="tools")

@bot.callback_query_handler(func=lambda call: call.data == "send_photo_mode")
def trigger_photo_mode(call):
    image_gen_state[call.from_user.id] = {'step': 'waiting_for_photo'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="menu_create"))
    send_or_edit(call, MENU_TEXTS["waiting_for_photo"], markup)

@bot.callback_query_handler(func=lambda call: call.data == "send_video_mode")
def trigger_video_mode(call):
    video_gen_state[call.from_user.id] = {'step': 'waiting_for_video'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="menu_create"))
    send_or_edit(call, MENU_TEXTS["waiting_for_video"], markup)

@bot.message_handler(content_types=['photo'])
def handle_all_photos(message):
    uid = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    
    if uid in welcome_media_state:
        return
    
    if uid in image_gen_state and image_gen_state[uid].get('step') == 'waiting_for_photo':
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
            InlineKeyboardButton("🔙 رجوع", callback_data="menu_create")
        )
        bot.send_message(message.chat.id, "<b>اختر الفئة:</b>", reply_markup=markup, parse_mode='HTML')

@bot.message_handler(content_types=['video'])
def handle_video_new(message):
    uid = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    if uid in video_gen_state and video_gen_state[uid].get('step') == 'waiting_for_video':
        video_gen_state[uid]['file_id'] = message.video.file_id
        video_gen_state[uid]['step'] = 'waiting_category'
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("حزين", callback_data="vid_cat_حزين"), 
            InlineKeyboardButton("فلسفي", callback_data="vid_cat_فلسفي"),
            InlineKeyboardButton("حب", callback_data="vid_cat_حب"), 
            InlineKeyboardButton("اقتباس", callback_data="vid_cat_اقتباس"),
            InlineKeyboardButton("🔙 رجوع", callback_data="menu_create"))
        bot.send_message(message.chat.id, "<b>اختر الفئة:</b>", reply_markup=markup, parse_mode='HTML')

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
        InlineKeyboardButton("مختلط (عربي + إنجليزي)", callback_data=f"{prefix}_lang_مختلط"),
        InlineKeyboardButton("🔙 إلغاء", callback_data="main_menu"))
    text = f"<b>⟨ الفئة: {cat} ⟩</b>\n────────────────────\n\n<blockquote>اختر لغة العبارة.</blockquote>"
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
        InlineKeyboardButton("🔙 إلغاء", callback_data="main_menu"))
    text = f"<b>⟨ اللغة: {lang_choice} ⟩</b>\n────────────────────\n\n<blockquote>اختر تنسيق النص.</blockquote>"
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
    msg = bot.send_message(call.message.chat.id, "⏳ جاري توليد العبارة...", parse_mode='HTML')
    
    lang_instr = "جملة عربية قصيرة ثم ترجمتها الإنجليزية في السطر التالي" if lang == "مختلط" else "باللغة العربية الفصحى"
    prompt = f"اكتب عبارة قصيرة جداً من سطر واحد بأسلوب {category} ({lang_instr}). بدون إيموجي."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=150)
        raw_text = res.choices[0].message.content.strip()
    except: raw_text = "عبارة تجريبية."
    final_text = f"<i>{raw_text}</i>" if fmt == "italic" else f"<b>{raw_text}</b>"
    settings = user_settings.get(uid, get_default_settings())
    final_caption = f"{final_text}\n\n{settings.get('hashtags', '')}"
    post_id = str(int(time.time()))
    pending_posts[post_id] = {'type': media_type, 'file_id': file_id, 'caption': final_caption, 'channel': user_channels.get(str(uid)), 'category': category, 'language': lang, 'format': fmt, 'is_img': is_img}
    markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_{post_id}"), InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    
    safe_delete(call.message.chat.id, msg.message_id)
    if media_type == 'photo': bot.send_photo(call.message.chat.id, file_id, caption=f"<b>⟨ معاينة ⟩</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(call.message.chat.id, file_id, caption=f"<b>⟨ معاينة ⟩</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "start_chat_gaski")
def start_gaski_chat(call):
    chat_state[call.from_user.id] = True
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إنهاء الدردشة والرجوع", callback_data="main_menu"))
    send_or_edit(call, MENU_TEXTS["start_chat_gaski"], markup, media_key="chat")

@bot.message_handler(func=lambda m: m.from_user.id in chat_state, content_types=['text'])
def handle_chat_message(message):
    if message.text.startswith('/'): return
    msg = bot.reply_to(message, "<i>يفكر...</i>", parse_mode='HTML')
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": message.text}], model=GROQ_MODEL, max_tokens=500)
        bot.edit_message_text(res.choices[0].message.content, chat_id=message.chat.id, message_id=msg.message_id)
    except Exception as e: bot.edit_message_text(f"خطأ: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    audio_edit_state[call.from_user.id] = {'step': 'waiting_for_cover', 'cover_data': None}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="menu_tools"))
    send_or_edit(call, MENU_TEXTS["start_audio_edit"], markup)

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    uid = message.from_user.id
    safe_delete(message.chat.id, message.message_id)
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_audio':
        file_id = message.audio.file_id if message.content_type == 'audio' else (message.document.file_id if message.document.mime_type == 'audio/mpeg' else None)
        if not file_id: return bot.reply_to(message, "أرسل MP3.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            cover_data = audio_edit_state[uid].get('cover_data')
            if not cover_data: return bot.reply_to(message, "لم يتم العثور على الغلاف.")
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data)
            audio_cache[uid] = {'data': rebuilt, 'cover': cover_jpg}
            markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{uid}"), InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
            bot.send_audio(message.chat.id, io.BytesIO(rebuilt), title="Red World", performer="@Eror_7", thumb=cover_jpg if cover_jpg else None)
            bot.send_message(message.chat.id, "<b>⟨ جاهز للنشر ⟩</b>", reply_markup=markup, parse_mode='HTML')
            del audio_edit_state[uid]
        except Exception as e: bot.send_message(message.chat.id, f"خطأ: {e}")

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

@bot.callback_query_handler(func=lambda call: call.data.startswith("regen_"))
def regenerate_caption(call):
    post_id = call.data.split("_")[1]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.", show_alert=True)
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
    final_caption = f"{final_text}\n\n{settings.get('hashtags', '')}"
    data['caption'] = final_caption
    pending_posts[post_id] = data
    markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_{post_id}"), InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    safe_delete(call.message.chat.id, call.message.message_id)
    if media_type == 'photo': bot.send_photo(call.message.chat.id, file_id, caption=f"<b>⟨ معاينة جديدة ⟩</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(call.message.chat.id, file_id, caption=f"<b>⟨ معاينة جديدة ⟩</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_post(call):
    post_id = call.data.split("_")[1]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    data = pending_posts[post_id]
    try:
        if data['type'] == 'photo': bot.send_photo(data['channel'], data['file_id'], caption=data['caption'], parse_mode='HTML')
        else: bot.send_video(data['channel'], data['file_id'], caption=data['caption'], parse_mode='HTML')
        stats["published_count"] += 1; save_json("stats.json", stats)
        bot.answer_callback_query(call.id, "تم النشر.")
        del pending_posts[post_id]
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
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
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
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء والرجوع", callback_data="menu_tools"))
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
        markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("تمبلر", callback_data="ad_type_تمبلر"), InlineKeyboardButton("فري", callback_data="ad_type_فري"), InlineKeyboardButton("مزج", callback_data="ad_type_مزج"), InlineKeyboardButton("🔙 إلغاء", callback_data="main_menu"))
        bot.send_message(message.chat.id, "<b>⟨ 2/7 ⟩ اختر نوع المجموعة:</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_set_type(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[uid]['step'] = 'waiting_group_link'
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 إلغاء", callback_data="main_menu"))
    send_or_edit(call, "<b>⟨ 3/7 ⟩ أرسل رابط المجموعة:</b>", markup)

# ==========================================
# 11. التشغيل
# ==========================================
print("Red World Bot is running...")
bot.infinity_polling()
