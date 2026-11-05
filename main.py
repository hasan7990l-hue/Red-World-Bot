import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time, base64, threading, json, os, io, re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error as ID3Error
from PIL import Image

# للاختبار فقط
TELEGRAM_TOKEN = "8180650384:AAHX37rerimsZIWBEc71HleexJKWqSaSsZ0"
GROQ_API_KEY   = "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"

ADMIN_ID = 8456056018
FORCE_CHANNELS = ["@Eror_7", "@lb2_c"]
CHANNEL_NAME = "عالم الأحمر | Red world"
CHANNEL_LINK = "https://t.me/Eror_7"
GROQ_MODEL = "qwen/qwen3.8-27b" # الموديل المحدث

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
DB_FILE, STATS_FILE = "user_channels.json", "stats.json"
audio_edit_state, pending_audio_merge, ad_builder_state = {}, {}, {}
audio_cache = {}

# ============================================================
#              الرسائل العربية (بدون إيموجي)
# ============================================================
MSGS = {
    "welcome": (
        "<b>بوابة عالم الأحمر</b>\n"
        "────────────────────\n\n"
        "<blockquote>"
        "أهلاً بك في <b>R W | Bot</b>\n"
        "نظام إدارة قنوات تيليجرام باحترافية.\n\n"
        "توليد عبارات بالذكاء الاصطناعي\n"
        "جدولة ونشر تلقائي\n"
        "إعلانات ترويجية بصور مغوشة\n"
        "ختم حقوق صوتية احترافية"
        "</blockquote>\n\n"
        "<i>اختر من الأسفل للبدء</i>"
    ),
    "force_sub": (
        "<b>بوابة مغلقة</b>\n"
        "────────────────────\n\n"
        "<blockquote>"
        "للدخول إلى <b>عالم الأحمر</b>،\n"
        "يجب الانضمام إلى قنواتنا أولاً:\n\n"
        "<a href='https://t.me/Eror_7'>@Eror_7</a>\n"
        "<a href='https://t.me/lb2_c'>@lb2_c</a>"
        "</blockquote>\n\n"
        "<i>بعد الاشتراك، اضغط زر التحقق بالأسفل.</i>"
    ),
    "control_panel": (
        "<b>غرفة التحكم</b>\n"
        "────────────────────\n\n"
        "<blockquote>مرحباً بك في مركز إدارة عالم الأحمر.\n"
        "كل شيء تحت سيطرتك الآن.</blockquote>"
    ),
    "verify_ok": (
        "<b>تم التحقق</b>\n\n"
        "<blockquote><b>الحالة:</b> ناجح\n"
        "<b>القناة:</b> {title}\n"
        "<b>الصلاحيات:</b> مشرف + صلاحية النشر.</blockquote>"
    ),
    "verify_fail": "<b>فشل الفحص</b>\n\n<blockquote>البوت ليس مشرفاً في القناة،\nأو لا يملك صلاحية النشر.</blockquote>",
    "verify_error": "<b>خطأ غير متوقع</b>\n\n<blockquote>{error}</blockquote>",
    "verify_ask": "<b>إدخال معرف القناة</b>\n\n<blockquote>أرسل معرف القناة الآن\nمثال: <code>@Eror_7</code></blockquote>",
    "verifying": "<i>جاري فحص القناة...</i>",
    "text_preview": "<b>مخطوطة جديدة</b>\n────────────────────\n\n{text}",
    "text_before_publish": "<b>مراجعة قبل النشر</b>\n\n{text}",
    "photo_preview": "<b>مشهد بصري</b>\n────────────────────\n\n{caption}",
    "photo_regenerated": "<b>مشهد بصري - نسخة جديدة</b>\n\n{caption}",
    "audio_wait_cover": (
        "<b>ختم الحقوق الصوتي</b>\n"
        "────────────────────\n\n"
        "<blockquote>الخطوة 1 من 2\n"
        "أرسل صورة الغلاف</blockquote>"
    ),
    "audio_wait_track": "<b>الخطوة 2 من 2</b>\n\n<blockquote>أرسل ملف الصوت الآن\nبصيغة <code>MP3</code></blockquote>",
    "audio_done": "<b>تم الختم بنجاح</b>\n\n<blockquote>أضيفت الحقوق صوتياً وبصرياً.\nالأغنية جاهزة للنشر في عالم الأحمر.</blockquote>",
    "audio_ask_merge": "<b>إضافة صوت للمنشور</b>\n\n<blockquote>أرسل ملف MP3 لإضافته\nمع المنشور الحالي.</blockquote>",
    "ad_q1": "<b>بروتوكول الإعلان - 1/7</b>\n\n<blockquote>أرسل اسم المجموعة</blockquote>",
    "ad_q2": "<b>بروتوكول الإعلان - 2/7</b>\n\n<blockquote>اختر نوع المجموعة</blockquote>",
    "ad_q3": "<b>بروتوكول الإعلان - 3/7</b>\n\n<blockquote>أرسل رابط المجموعة\nلاستخراج الآيدي منه</blockquote>",
    "ad_q4": "<b>بروتوكول الإعلان - 4/7</b>\n\n<blockquote>أرسل يوزر مالك المجموعة\nمثال: <code>@user</code></blockquote>",
    "ad_q5": "<b>بروتوكول الإعلان - 5/7</b>\n\n<blockquote>هل تريد إضافة يوزر قناة؟</blockquote>",
    "ad_q5_input": "<b>يوزر القناة</b>\n\n<blockquote>أرسل يوزر القناة\nمثال: <code>@mychannel</code></blockquote>",
    "ad_q6": "<b>بروتوكول الإعلان - 6/7</b>\n\n<blockquote>أرسل الوسائط\nصورة أو فيديو</blockquote>",
    "ad_q7": "<b>بروتوكول الإعلان - 7/7</b>\n\n<blockquote>اختر لغة كليشة الإعلان</blockquote>",
    "ad_publish_ok": "<b>تم النشر</b>\n\n<blockquote>الإعلان الآن في عالم الأحمر.</blockquote>",
    "schedule_ask": "<b>جدولة النشر</b>\n\n<blockquote>أرسل عدد الدقائق\nمثال: <code>30</code></blockquote>",
    "schedule_done": "<b>تمت الجدولة</b>\n\n<blockquote>سيُنشر بعد {minutes} دقيقة.</blockquote>",
    "stats": (
        "<b>سجل المملكة</b>\n"
        "────────────────────\n\n"
        "<blockquote><b>القناة:</b> {title}\n"
        "<b>المشتركين:</b> {members}\n"
        "<b>المنشورات:</b> {posts}</blockquote>"
    ),
    "not_verified": "<b>وصول مرفوض</b>\n\n<blockquote>يجب التحقق من رفع البوت أولاً.</blockquote>",
    "channel_unlinked": "<b>القناة غير مرتبطة</b>\n\n<blockquote>افتح فحص الرفع أولاً.</blockquote>",
    "expired": "<i>انتهت صلاحية هذه العملية.</i>",
    "left_channel": "<b>تم فك الارتباط</b>\n\n<blockquote>لم تعد مرتبطاً بأي قناة.</blockquote>",
    "no_channel": "<i>لا توجد قناة مرتبطة.</i>",
    "status_on": "النشر مفعل",
    "status_off": "النشر معطل",
    "text_mode_on": "النشر النصي مفعل",
    "text_mode_off": "النشر النصي معطل",
    "lang_updated": "<b>تم تحديث اللغة</b>",
    "cat_updated": "<b>تم تحديث الفئة</b>",
}

# ============================================================
#                    أدوات مساعدة
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
    return {"status": "ON", "text_only_mode": False, "category": "فلسفي",
            "language": "عربي", "add_hashtags": True,
            "hashtags": "#RedWorld #عالم_الأحمر"}

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
        cover_data_jpg = convert_to_jpg(cover_bytes) if cover_bytes else b''
        if cover_data_jpg:
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
    link = link.strip()
    m = re.search(r'(?:t\.me/|telegram\.me/)(?:\+)?([A-Za-z0-9_-]+)', link)
    return m.group(1) if m else link

def build_lang_instruction(language):
    if language == "مختلط":
        return "جملة عربية قصيرة ثم ترجمتها الإنجليزية في السطر التالي"
    elif language == "إنجليزي":
        return "باللغة الإنجليزية"
    else:
        return "باللغة العربية"

def check_subscription(user_id):
    for channel in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def send_force_sub_message(chat_id):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("اشترك في القناة الأولى", url="https://t.me/Eror_7"),
        InlineKeyboardButton("اشترك في القناة الثانية", url="https://t.me/lb2_c"),
        InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_sub"))
    bot.send_message(chat_id, MSGS["force_sub"], reply_markup=markup, parse_mode='HTML')

# ============================================================
#                    الأوامر الأساسية
# ============================================================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID and not check_subscription(user_id):
        return send_force_sub_message(message.chat.id)
    if user_id not in user_settings: user_settings[user_id] = get_default_settings()
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("1. إضافة البوت لقناتك (مشرف)", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
        InlineKeyboardButton("2. التحقق من الرفع (فحص تلقائي)", callback_data="verify_channel"),
        InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
    bot.send_message(message.chat.id, MSGS["welcome"], reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "تم التحقق بنجاح، أهلاً بك.")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "لم تشترك في جميع القنوات بعد.")

# ============================================================
#                    فحص الرفع
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id)
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
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
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
            bot.send_message(adder_id, f"تمت إضافة البوت إلى القناة: {update.chat.title}\nيرجى الضغط على زر التحقق من الرفع.", parse_mode='HTML')
        except: pass
            # ============================================================
#                    لوحة التحكم
# ============================================================
def get_main_panel(user_id):
    settings = user_settings.get(user_id, get_default_settings())
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("تعطيل النشر" if settings["status"] == "ON" else "تفعيل النشر", callback_data="toggle_status"),
        InlineKeyboardButton("تعطيل النشر النصي" if settings["text_only_mode"] else "تفعيل النشر النصي", callback_data="toggle_text_mode"),
        InlineKeyboardButton("فئات العبارات", callback_data="menu_categories"),
        InlineKeyboardButton(f"اللغة: {settings['language']}", callback_data="menu_lang"),
        InlineKeyboardButton("عبارات طويلة", callback_data="generate_long_text"),
        InlineKeyboardButton("عبارات مختصرة", callback_data="generate_short_text"),
        InlineKeyboardButton("إنشاء إعلان ترويجي", callback_data="start_ad_builder"),
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit"),
        InlineKeyboardButton("التقرير الأسبوعي", callback_data="show_stats"),
        InlineKeyboardButton("السورس", callback_data="show_source"),
        InlineKeyboardButton("مغادرة القناة", callback_data="leave_channel"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    bot.answer_callback_query(call.id)
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
    bot.answer_callback_query(call.id)
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["status"] = "OFF" if settings["status"] == "ON" else "ON"
    user_settings[call.from_user.id] = settings
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=get_main_panel(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "toggle_text_mode")
def toggle_text_mode(call):
    bot.answer_callback_query(call.id)
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["text_only_mode"] = not settings["text_only_mode"]
    user_settings[call.from_user.id] = settings
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=get_main_panel(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "menu_lang")
def menu_lang(call):
    bot.answer_callback_query(call.id)
    markup = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("عربي", callback_data="lang_عربي"),
        InlineKeyboardButton("إنجليزي", callback_data="lang_إنجليزي"),
        InlineKeyboardButton("مختلط", callback_data="lang_مختلط"),
        InlineKeyboardButton("رجوع", callback_data="main_menu"))
    bot.edit_message_text("<b>اختر اللغة:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["language"] = call.data.replace("lang_", "")
    user_settings[call.from_user.id] = settings
    bot.answer_callback_query(call.id)
    bot.edit_message_text(MSGS["lang_updated"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "menu_categories")
def menu_categories(call):
    bot.answer_callback_query(call.id)
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("حزين", callback_data="cat_حزين"),
        InlineKeyboardButton("تفاؤل", callback_data="cat_تفاؤل"),
        InlineKeyboardButton("فلسفي", callback_data="cat_فلسفي"),
        InlineKeyboardButton("غامض", callback_data="cat_غامض"),
        InlineKeyboardButton("رجوع", callback_data="main_menu"))
    bot.edit_message_text("<b>اختر الفئة:</b>", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def set_cat(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["category"] = call.data.replace("cat_", "")
    user_settings[call.from_user.id] = settings
    bot.answer_callback_query(call.id)
    bot.edit_message_text(MSGS["cat_updated"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

# ============================================================
#                    توليد النصوص
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data in ["generate_long_text", "generate_short_text"])
def generate_text(call):
    bot.answer_callback_query(call.id, "جاري التوليد...")
    settings = user_settings.get(call.from_user.id, get_default_settings())
    lang_instr = build_lang_instruction(settings['language'])
    length = "عبارة مفصلة من 3 إلى 4 أسطر" if call.data == 'generate_long_text' else "عبارة قصيرة جداً من سطر واحد"
    prompt = f"اكتب {length} بأسلوب {settings['category']} ({lang_instr}). بدون إيموجي، بدون نجوم، بدون علامات اقتباس."
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
        bot.send_message(call.message.chat.id, f"خطأ: {e}")

def send_formatting_panel(chat_id, msg_id):
    data = generated_texts[msg_id]
    text = apply_formatting(data["raw"], data)
    markup = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}"),
        InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}"),
        InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}"),
        InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}"),
        InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}"),
        InlineKeyboardButton("إلغاء", callback_data=f"fmt_cancel_{msg_id}"))
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
        bot.answer_callback_query(call.id, "تم الإلغاء.")
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    elif action == "publish":
        text = apply_formatting(data["raw"], data)
        target_channel = user_channels.get(str(call.from_user.id))
        if not target_channel:
            return bot.answer_callback_query(call.id, "القناة غير مرتبطة.")
        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'text', 'caption': text, 'channel': target_channel}
        markup = InlineKeyboardMarkup(row_width=3).add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"),
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"),
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
        bot.answer_callback_query(call.id, "جاهز للنشر.")
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
#     معالجة الصور (إعلان أولاً - ثم غلاف صوت - ثم توليد عادي)
# ============================================================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.from_user.id

    if uid in ad_builder_state and ad_builder_state[uid].get('step') == 'waiting_media':
        ad_builder_state[uid]['media_file_id'] = message.photo[-1].file_id
        ad_builder_state[uid]['media_type'] = 'photo'
        return finish_ad_preview(message.chat.id, uid)

    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_cover':
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            audio_edit_state[uid]['cover_data'] = bot.download_file(file_info.file_path)
            audio_edit_state[uid]['step'] = 'waiting_for_audio'
            bot.send_message(message.chat.id, MSGS["audio_wait_track"], parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ في تحميل الغلاف: {e}")
        return

    if uid in ad_builder_state or uid in audio_edit_state or uid in pending_audio_merge:
        return

    if uid != ADMIN_ID and str(uid) not in user_channels:
        return bot.send_message(message.chat.id, MSGS["not_verified"],
                                reply_markup=InlineKeyboardMarkup().add(
                                    InlineKeyboardButton("التحقق", callback_data="verify_channel")),
                                parse_mode='HTML')

    settings = user_settings.get(uid, get_default_settings())
    if settings["status"] == "OFF":
        return bot.send_message(message.chat.id, "النشر معطل.",
                                reply_markup=get_main_panel(uid), parse_mode='HTML')
    msg_loading = bot.send_message(message.chat.id, "<i>جاري تحليل الصورة...</i>", parse_mode='HTML')
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        photo_bytes = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        lang_instr = build_lang_instruction(settings['language'])
        prompt = f"اكتب تعليقاً قصيراً جداً من سطر واحد بأسلوب {settings['category']} ({lang_instr}). بدون إيموجي."
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
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"),
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"),
            InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_image_{post_id}"),
            InlineKeyboardButton("إضافة ملف صوتي", callback_data=f"add_audio_to_post_{post_id}"),
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id,
                       caption=MSGS["photo_preview"].format(caption=final_caption),
                       reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_message(message.chat.id, f"خطأ: {e}", reply_markup=get_main_panel(uid))

@bot.message_handler(content_types=['video'])
def handle_video(message):
    uid = message.from_user.id
    if uid in ad_builder_state and ad_builder_state[uid].get('step') == 'waiting_media':
        ad_builder_state[uid]['media_file_id'] = message.video.file_id
        ad_builder_state[uid]['media_type'] = 'video'
        return finish_ad_preview(message.chat.id, uid)

# ============================================================
#                    حقوق النشر الصوتي
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    bot.answer_callback_query(call.id)
    audio_edit_state[call.from_user.id] = {'step': 'waiting_for_cover', 'cover_data': None}
    bot.edit_message_text(MSGS["audio_wait_cover"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    uid = message.from_user.id

    if uid in pending_audio_merge:
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg':
            file_id = message.document.file_id
        if not file_id: return bot.reply_to(message, "أرسل ملفاً بصيغة MP3.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, b'')
            data = pending_audio_merge[uid]
            bot.send_photo(data['channel'], data['photo_id'], caption=data['caption'], parse_mode='HTML')
            bot.send_audio(data['channel'], io.BytesIO(rebuilt),
                           title="Red World", performer="@Eror_7",
                           thumb=cover_jpg if cover_jpg else None)
            stats["published_count"] += 1; save_json(STATS_FILE, stats)
            del pending_audio_merge[uid]
            bot.send_message(message.chat.id, "تم نشر الصورة مع الصوت.")
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ: {e}")
        return

    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_audio':
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg':
            file_id = message.document.file_id
        if not file_id: return bot.reply_to(message, "أرسل ملفاً بصيغة MP3.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            cover_data = audio_edit_state[uid].get('cover_data') or b''
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data)
            audio_cache[uid] = {'data': rebuilt, 'cover': cover_jpg}
            
            markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("Red World Channel", url=CHANNEL_LINK),
                InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{uid}"))
                
            bot.send_audio(message.chat.id, io.BytesIO(rebuilt),
                           title="Red World", performer="@Eror_7",
                           thumb=cover_jpg if cover_jpg else None,
                           reply_markup=markup)
            bot.send_message(message.chat.id, MSGS["audio_done"], parse_mode='HTML')
            audio_edit_state[uid]['step'] = 'ready'
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ: {e}")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_standalone_audio_"))
def publish_standalone_audio(call):
    uid = int(call.data.split("_")[3])
    target_channel = user_channels.get(str(uid))
    if not target_channel:
        return bot.answer_callback_query(call.id, "القناة غير مرتبطة.")
    if uid not in audio_cache:
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    try:
        cached = audio_cache[uid]
        
        # 1. إرسال الملف الصوتي فقط
        bot.send_audio(target_channel, io.BytesIO(cached['data']),
                       title="Red World", performer="@Eror_7",
                       thumb=cached['cover'] if cached['cover'] else None)
        
        # 2. إرسال الأزرار في رسالة نصية منفصلة تحته
        markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("Red World Channel", url=CHANNEL_LINK),
            InlineKeyboardButton(CHANNEL_NAME, url=CHANNEL_LINK)
        )
        bot.send_message(target_channel, "<b>حقوق النشر محفوظة | Red World</b>", reply_markup=markup, parse_mode='HTML')

        stats["published_count"] += 1; save_json(STATS_FILE, stats)
        bot.answer_callback_query(call.id, "تم النشر بنجاح.")
        
        if uid in audio_edit_state: del audio_edit_state[uid]
        if uid in audio_cache: del audio_cache[uid]
        
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(uid), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_audio_to_post_"))
def add_audio_to_post(call):
    post_id = call.data.split("_")[4]
    if post_id not in pending_posts:
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    pending_audio_merge[call.from_user.id] = {
        'post_id': post_id,
        'photo_id': pending_posts[post_id]['file_id'],
        'caption': pending_posts[post_id]['caption'],
        'channel': pending_posts[post_id]['channel']}
    bot.answer_callback_query(call.id, "أرسل ملف MP3 الآن.")
    # ============================================================
#     بناء الإعلان - 7 خطوات
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    bot.answer_callback_query(call.id)
    ad_builder_state[call.from_user.id] = {
        'step': 'waiting_group_name',
        'group_name': None, 'group_type': None,
        'group_link': None, 'group_id': None,
        'owner_username': None, 'channel_username': None,
        'media_file_id': None, 'media_type': None,
        'language': 'عربي'}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="ad_cancel"))
    bot.edit_message_text(MSGS["ad_q1"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_cancel")
def ad_cancel(call):
    if call.from_user.id in ad_builder_state: del ad_builder_state[call.from_user.id]
    bot.answer_callback_query(call.id, "تم الإلغاء.")
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
        # تعديل أنواع الكروب هنا
        markup = InlineKeyboardMarkup(row_width=3).add(
            InlineKeyboardButton("تمبلر", callback_data="ad_type_تمبلر"),
            InlineKeyboardButton("فري", callback_data="ad_type_فري"),
            InlineKeyboardButton("مزج", callback_data="ad_type_مزج"))
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
            InlineKeyboardButton("نعم", callback_data="ad_ch_yes"),
            InlineKeyboardButton("لا", callback_data="ad_ch_no"))
        bot.send_message(message.chat.id, MSGS["ad_q5"], reply_markup=markup, parse_mode='HTML')

    elif step == 'waiting_channel_username':
        uname = message.text.strip()
        if not uname.startswith('@'): uname = '@' + uname
        data['channel_username'] = uname
        data['step'] = 'waiting_media'
        bot.send_message(message.chat.id, MSGS["ad_q6"], parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_set_type(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[uid]['step'] = 'waiting_group_link'
    bot.answer_callback_query(call.id)
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
    ad_builder_state[call.from_user.id]['step'] = 'waiting_media'
    bot.answer_callback_query(call.id)
    bot.edit_message_text(MSGS["ad_q6"], chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode='HTML')

def finish_ad_preview(chat_id, uid):
    data = ad_builder_state[uid]
    data['step'] = 'waiting_ad_language'
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("عربي", callback_data="ad_lang_عربي"),
        InlineKeyboardButton("إنجليزي", callback_data="ad_lang_إنجليزي"))
    bot.send_message(chat_id, MSGS["ad_q7"], reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_lang_"))
def ad_set_lang(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['language'] = call.data.replace("ad_lang_", "")
    bot.answer_callback_query(call.id)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    build_ad_preview(call.message.chat.id, uid)

def build_ad_preview(chat_id, uid):
    data = ad_builder_state[uid]
    lang = data['language']

    owner_real_name = data['owner_username']
    try:
        owner_clean = data['owner_username'].lstrip('@')
        owner_chat = bot.get_chat(f"@{owner_clean}")
        if owner_chat.first_name:
            owner_real_name = owner_chat.first_name
    except: pass

    channel_real_name = data.get('channel_username')
    if data.get('channel_username'):
        try:
            ch_clean = data['channel_username'].lstrip('@')
            ch_chat = bot.get_chat(f"@{ch_clean}")
            if ch_chat.title:
                channel_real_name = ch_chat.title
        except: pass

    if lang == "عربي":
        prompt = (
            "اكتب نصاً ترويجياً قصيراً وأنيقاً لمجموعة تيليجرام باللغة العربية.\n"
            f"اسم المجموعة: {data['group_name']}\n"
            f"نوع المجموعة: {data['group_type']}\n"
            f"مالك المجموعة: {data['owner_username']}\n"
            "بدون إيموجي، بدون نجوم، بدون علامات اقتباس."
        )
    else:
        prompt = (
            "Write a short elegant promotional text for a Telegram group in English.\n"
            f"Group name: {data['group_name']}\n"
            f"Group type: {data['group_type']}\n"
            f"Group owner: {data['owner_username']}\n"
            "No emojis, no asterisks, no quotes."
        )

    try:
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL, max_tokens=400)
        body = res.choices[0].message.content.strip().replace("**", "").replace("*", "")
    except Exception as e:
        body = f"{data['group_name']} - {data['group_type']}"

    caption = (
        f"<b>{data['group_name']}</b>\n"
        "────────────────────\n\n"
        f"<blockquote>{body}</blockquote>\n\n"
        f"<b>نوع المجموعة:</b> {data['group_type']}\n"
        f"<b>آيدي المجموعة:</b> <code>{data['group_id']}</code>\n"
        f"<b>المالك:</b> {data['owner_username']}\n"
    )
    if data.get('channel_username'):
        caption += f"<b>القناة:</b> {data['channel_username']}\n"

    # أزرار القناة فقط
    pub_markup = InlineKeyboardMarkup(row_width=1)
    if data.get('group_link'):
        pub_markup.add(InlineKeyboardButton(f"رابط {data['group_name']}", url=data['group_link']))
    
    owner_clean = data['owner_username'].lstrip('@')
    pub_markup.add(InlineKeyboardButton(f"المالك: {owner_real_name}", url=f"https://t.me/{owner_clean}"))
    
    if data.get('channel_username'):
        ch_clean = data['channel_username'].lstrip('@')
        pub_markup.add(InlineKeyboardButton(f"القناة: {channel_real_name}", url=f"https://t.me/{ch_clean}"))

    # أزرار المعاينة (نشر/إلغاء)
    preview_markup = InlineKeyboardMarkup(row_width=1)
    for btn in pub_markup.keyboard:
        preview_markup.add(btn[0])
    preview_markup.add(InlineKeyboardButton("نشر الإعلان", callback_data="ad_confirm_publish"))
    preview_markup.add(InlineKeyboardButton("إلغاء", callback_data="ad_cancel"))

    data['final_caption'] = caption
    data['final_markup'] = pub_markup

    if data.get('media_file_id') and data['media_type'] == 'photo':
        bot.send_photo(chat_id, data['media_file_id'], caption=caption,
                       reply_markup=preview_markup, parse_mode='HTML')
    elif data.get('media_file_id') and data['media_type'] == 'video':
        bot.send_video(chat_id, data['media_file_id'], caption=caption,
                       reply_markup=preview_markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, caption, reply_markup=preview_markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_confirm_publish")
def ad_confirm_publish(call):
    uid = call.from_user.id
    if uid not in ad_builder_state:
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    target_channel = user_channels.get(str(uid))
    if not target_channel:
        return bot.answer_callback_query(call.id, "القناة غير مرتبطة.")
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
        bot.answer_callback_query(call.id, "تم النشر.")
        del ad_builder_state[uid]
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(uid), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}")

# ============================================================
#                    جدولة + تأكيد + إلغاء
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_"))
def schedule(call):
    post_id = call.data.split("_")[1]
    bot.answer_callback_query(call.id)
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
        timer = threading.Timer(minutes * 60, do_publish)
        timer.daemon = True
        timer.start()
        bot.send_message(message.chat.id, MSGS["schedule_done"].format(minutes=minutes), parse_mode='HTML')
        del pending_posts[post_id]
    except ValueError:
        bot.send_message(message.chat.id, "أرسل رقماً صحيحاً.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_post(call):
    post_id = call.data.split("_")[1]
    if post_id not in pending_posts:
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    data = pending_posts[post_id]
    try:
        if data['type'] == 'photo':
            bot.send_photo(data['channel'], data['file_id'], caption=data['caption'], parse_mode='HTML')
        else:
            bot.send_message(data['channel'], data['caption'], parse_mode='HTML')
        stats["published_count"] += 1; save_json(STATS_FILE, stats)
        bot.answer_callback_query(call.id, "تم النشر.")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, MSGS["control_panel"],
                         reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
        del pending_posts[post_id]
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel_post(call):
    post_id = call.data.split("_")[1]
    if post_id in pending_posts: del pending_posts[post_id]
    bot.answer_callback_query(call.id, "تم الإلغاء.")
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, MSGS["control_panel"],
                     reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("regen_image_"))
def regen_image(call):
    post_id = call.data.split("_")[2]
    if post_id not in saved_images:
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    data = saved_images[post_id]
    try:
        file_info = bot.get_file(data['photo_id'])
        base64_image = base64.b64encode(bot.download_file(file_info.file_path)).decode('utf-8')
        lang_instr = build_lang_instruction(data['settings']['language'])
        prompt = f"اكتب تعليقاً قصيراً جداً من سطر واحد بأسلوب {data['settings']['category']} ({lang_instr}). بدون إيموجي."
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
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{new_post_id}"),
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{new_post_id}"),
            InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_image_{new_post_id}"),
            InlineKeyboardButton("إضافة ملف صوتي", callback_data=f"add_audio_to_post_{new_post_id}"),
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{new_post_id}"))
        bot.answer_callback_query(call.id, "تم التوليد من جديد.")
        bot.send_photo(call.message.chat.id, photo=data['photo_id'],
                       caption=MSGS["photo_regenerated"].format(caption=final_caption),
                       reply_markup=markup, parse_mode='HTML')
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    except Exception as e:
        bot.send_message(call.message.chat.id, f"خطأ: {e}")

# ============================================================
#                    السورس (إنجليزي + صورة)
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "show_source")
def show_source(call):
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    try:
        dev_chat = bot.get_chat(ADMIN_ID)
        dev_name = dev_chat.first_name or "Developer"
    except:
        dev_name = "Developer"

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

    # الكليشة الإنجليزية
    text = (
        "<b>What can this bot do?</b>\n\n"
        "<blockquote>"
        "Red World | عالم الأحمر\n"
        "Your world for premium services.\n"
        "Fast - Secure - Professional\n"
        f"Developer: @{dev_name}\n"
        "</blockquote>"
    )

    markup = InlineKeyboardMarkup(row_width=1)
    if channel_info:
        ch_link = f"https://t.me/{channel_info.username}" if channel_info.username else CHANNEL_LINK
        markup.add(InlineKeyboardButton(f"Channel: {channel_info.title}", url=ch_link))
    
    markup.add(InlineKeyboardButton(f"Developer: {dev_name}", url=f"tg://user?id={ADMIN_ID}"))
    markup.add(InlineKeyboardButton("Back", callback_data="main_menu"))

    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    if channel_photo:
        bot.send_photo(call.message.chat.id, photo=channel_photo, caption=text,
                       reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ============================================================
#                    أزرار متنوعة
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    bot.answer_callback_query(call.id)
    if str(call.from_user.id) in user_channels:
        del user_channels[str(call.from_user.id)]
        save_json(DB_FILE, user_channels)
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "لا توجد قناة مرتبطة.")

@bot.callback_query_handler(func=lambda call: call.data == "show_stats")
def show_stats(call):
    bot.answer_callback_query(call.id)
    cid = user_channels.get(str(call.from_user.id))
    if not cid:
        return bot.answer_callback_query(call.id, "القناة غير مرتبطة.")
    try:
        text = MSGS["stats"].format(
            title=bot.get_chat(cid).title,
            members=bot.get_chat_member_count(cid),
            posts=stats['published_count'])
        bot.edit_message_text(text, chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu")),
                              parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}")

# ============================================================
#                    النشر النصي التلقائي
# ============================================================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'): return
    uid = message.from_user.id
    if uid in ad_builder_state: return
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
                messages=[{"role": "user", "content": f"اكتب عبارة قصيرة جداً من سطر واحد بأسلوب {settings['category']} ({lang_instr}). بدون إيموجي."}],
                model=GROQ_MODEL, max_tokens=300)
            final_caption = f"<b>{res.choices[0].message.content.strip()}</b>\n\n{settings['hashtags']}"
            post_id = str(int(time.time()))
            pending_posts[post_id] = {'type': 'text', 'caption': final_caption,
                                       'channel': user_channels.get(str(uid))}
            markup = InlineKeyboardMarkup(row_width=3).add(
                InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"),
                InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"),
                InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
            bot.send_message(message.chat.id, f"<b>معاينة:</b>\n\n{final_caption}",
                             reply_markup=markup, parse_mode='HTML')
        except: pass

# ============================================================
#                    التشغيل
# ============================================================
print("Bot is running...")
bot.infinity_polling()
