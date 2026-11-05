import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time, base64, datetime, threading, json, os, io
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error as ID3Error
from PIL import Image, ImageFilter

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAEB3MxUUzZDXuYAoYiKNaLNvPAh80mt6i8'
GROQ_API_KEY = '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'
ADMIN_ID = 8456056018 
FORCE_CHANNELS = ["@Eror_7", "@lb2_c"]
CHANNEL_NAME = "عالم الأحمر | Red world"
CHANNEL_LINK = "https://t.me/Eror_7"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

DB_FILE, STATS_FILE = "user_channels.json", "stats.json"
audio_edit_state, pending_audio_merge, ad_builder_state = {}, {}, {}

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
    return {"status": "ON", "text_only_mode": False, "category": "فلسفي", "language": "عربي", "add_hashtags": True, "hashtags": "#RedWorld #عالم_الأحمر"}

user_settings, generated_texts, pending_posts, media_groups, saved_images = {}, {}, {}, {}, {}

# ================= دوال مساعدة =================
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
        audio.tags.add(TIT2(encoding=3, text="Red world | عالم الأحمر"))
        audio.tags.add(TPE1(encoding=3, text="@Eror_7"))
        cover_data_jpg = convert_to_jpg(cover_bytes)
        audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data_jpg))
        audio.save(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.getvalue(), cover_data_jpg
    except: return original_audio_bytes, cover_bytes

def check_subscription(user_id):
    for channel in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

def send_force_sub_message(chat_id):
    text = "<b>⟨ بوابة عالم الأحمر ⟩</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n<blockquote>أهلاً بك. للوصول إلى النظام، يجب عليك الانضمام إلى قنواتنا أولاً.\n\n🔴 <b>القناة الأولى:</b> @Eror_7\n🔴 <b>القناة الثانية:</b> @lb2_c</blockquote>\n\n<i>بعد الاشتراك، اضغط على زر التحقق.</i>"
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("اشترك في القناة الأولى", url="https://t.me/Eror_7"),
        InlineKeyboardButton("اشترك في القناة الثانية", url="https://t.me/lb2_c"),
        InlineKeyboardButton("تحقق من الاشتراك ✅", callback_data="check_sub"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

# ================= 1. الترحيب والتحقق =================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID and not check_subscription(user_id): return send_force_sub_message(message.chat.id)
    if user_id not in user_settings: user_settings[user_id] = get_default_settings()
    welcome_text = "<b>⟨ مرحباً بك في R W | Bot ⟩</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\nهذا البوت مخصص لإدارة قنوات تيليجرام باحترافية."
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("1. إضافة البوت لقناتك (مشرف)", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
        InlineKeyboardButton("2. التحقق من الرفع (فحص تلقائي)", callback_data="verify_channel"),
        InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    if user_id == ADMIN_ID or str(user_id) in user_channels: markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح! أهلاً بك.", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_welcome(call.message)
    else: bot.answer_callback_query(call.id, "❌ لم تشترك في جميع القنوات بعد.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id, "جاري الفحص...")
    channel_id = user_channels.get(str(call.from_user.id))
    if not channel_id:
        msg = bot.send_message(call.message.chat.id, "⚠️ يرجى إرسال معرف القناة (مثال: @Eror_7):")
        bot.register_next_step_handler(msg, manual_verify, call.from_user.id)
    else: perform_verification(call.message.chat.id, call.from_user.id, channel_id)

def manual_verify(message, user_id):
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    user_channels[str(user_id)] = channel_input
    save_json(DB_FILE, user_channels)
    perform_verification(message.chat.id, user_id, channel_input)

def perform_verification(chat_id, user_id, channel_id):
    msg_loading = bot.send_message(chat_id, "⏳ جاري فحص القناة...")
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        if bot_member.status in ['administrator', 'creator'] and bot_member.can_post_messages:
            success_text = f"<b>⟨ نتيجة الفحص ⟩</b>\n<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n<blockquote><b>الحالة:</b> ✅ ناجح\n<b>القناة:</b> {chat_info.title}\n<b>الصلاحيات:</b> مشرف + يملك صلاحية النشر.</blockquote>"
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
            bot.edit_message_text(success_text, chat_id=chat_id, message_id=msg_loading.message_id, reply_markup=markup, parse_mode='HTML')
        else: bot.edit_message_text("❌ البوت ليس مشرفاً أو لا يملك صلاحية النشر.", chat_id=chat_id, message_id=msg_loading.message_id)
    except Exception as e: bot.edit_message_text(f"❌ حدث خطأ: {e}", chat_id=chat_id, message_id=msg_loading.message_id)

@bot.message_handler(content_types=['new_chat_members'])
def bot_added_to_channel(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            adder_id = message.from_user.id
            channel_identifier = f"@{message.chat.username}" if message.chat.username else str(message.chat.id)
            user_channels[str(adder_id)] = channel_identifier
            save_json(DB_FILE, user_channels)
            try: bot.send_message(adder_id, f"✅ تمت إضافة البوت إلى القناة: {message.chat.title}\nيرجى الضغط على (التحقق من الرفع).", parse_mode='HTML')
            except: pass
                # ================= 2. لوحة التحكم =================
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
    try: bot.edit_message_text("<b>مرحباً بك في لوحة التحكم</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    except: 
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "toggle_status")
def toggle_status(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["status"] = "OFF" if settings["status"] == "ON" else "ON"
    user_settings[call.from_user.id] = settings
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_panel(call.from_user.id))
    bot.answer_callback_query(call.id, text=f"حالة النشر: {'مفعل' if settings['status'] == 'ON' else 'معطل'}")

@bot.callback_query_handler(func=lambda call: call.data == "toggle_text_mode")
def toggle_text_mode(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["text_only_mode"] = not settings["text_only_mode"]
    user_settings[call.from_user.id] = settings
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_panel(call.from_user.id))
    bot.answer_callback_query(call.id, text=f"النشر النصي: {'مفعل' if settings['text_only_mode'] else 'معطل'}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_lang")
def menu_lang(call):
    markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("عربي", callback_data="lang_عربي"), InlineKeyboardButton("إنجليزي", callback_data="lang_إنجليزي"), InlineKeyboardButton("مختلط", callback_data="lang_مختلط"), InlineKeyboardButton("رجوع", callback_data="main_menu"))
    bot.edit_message_text("<b>اختر اللغة:</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["language"] = call.data.replace("lang_", "")
    user_settings[call.from_user.id] = settings
    bot.edit_message_text("<b>تم تحديث اللغة.</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "menu_categories")
def menu_categories(call):
    markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("حزين", callback_data="cat_حزين"), InlineKeyboardButton("تفاؤل", callback_data="cat_تفاؤل"), InlineKeyboardButton("فلسفي", callback_data="cat_فلسفي"), InlineKeyboardButton("غامض", callback_data="cat_غامض"), InlineKeyboardButton("رجوع", callback_data="main_menu"))
    bot.edit_message_text("<b>اختر الفئة:</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def set_cat(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    settings["category"] = call.data.replace("cat_", "")
    user_settings[call.from_user.id] = settings
    bot.edit_message_text("<b>تم تحديث الفئة.</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

# ================= 3. توليد العبارات =================
@bot.callback_query_handler(func=lambda call: call.data in ["generate_long_text", "generate_short_text"])
def generate_text(call):
    settings = user_settings.get(call.from_user.id, get_default_settings())
    bot.answer_callback_query(call.id, "جاري التوليد...")
    lang = "جملة عربية واحدة (لا تتجاوز 10 كلمات) ثم ترجمتها الإنجليزية في سطر واحد" if settings['language'] == "مختلط" else f"باللغة {settings['language']}"
    prompt = f"اكتب {'عبارة مفصلة (3-4 أسطر)' if call.data == 'generate_long_text' else 'عبارة قصيرة جداً (سطر واحد)'} بأسلوب {settings['category']} ({lang}). بدون إيموجي."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="qwen/qwen3.8-27b", max_tokens=500)
        raw_text = res.choices[0].message.content.strip()
        msg_id = str(int(time.time()))
        generated_texts[msg_id] = {"raw": raw_text, "bold": False, "italic": False, "strike": False, "quote": False}
        send_formatting_panel(call.message.chat.id, msg_id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    except Exception as e: bot.send_message(call.message.chat.id, f"خطأ: {e}")

def send_formatting_panel(chat_id, msg_id):
    data = generated_texts[msg_id]
    text = data["raw"]
    if data["strike"]: text = f"<s>{text}</s>"
    if data["italic"]: text = f"<i>{text}</i>"
    if data["bold"]: text = f"<b>{text}</b>"
    if data["quote"]: text = f"<blockquote>{text}</blockquote>"
    markup = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}"),
        InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}"),
        InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}"),
        InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}"),
        InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}"), InlineKeyboardButton("إلغاء", callback_data=f"fmt_cancel_{msg_id}"))
    bot.send_message(chat_id, f"معاينة النص:\n\n{text}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('fmt_'))
def formatting_handler(call):
    action, msg_id = call.data.split('_')[1], call.data.split('_')[2]
    if msg_id not in generated_texts: return
    data = generated_texts[msg_id]
    if action == "cancel":
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    elif action == "publish":
        text = data["raw"]
        if data["strike"]: text = f"<s>{text}</s>"
        if data["italic"]: text = f"<i>{text}</i>"
        if data["bold"]: text = f"<b>{text}</b>"
        if data["quote"]: text = f"<blockquote>{text}</blockquote>"
        target_channel = user_channels.get(str(call.from_user.id))
        if not target_channel: return bot.answer_callback_query(call.id, "⚠️ يرجى التحقق من رفع البوت أولاً.", show_alert=True)
        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'text', 'caption': text, 'channel': target_channel}
        markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
        bot.edit_message_text(f"<b>معاينة قبل النشر:</b>\n\n{text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    else:
        if action == "bold": data["bold"] = not data["bold"]
        elif action == "italic": data["italic"] = not data["italic"]
        elif action == "strike": data["strike"] = not data["strike"]
        elif action == "quote": data["quote"] = not data["quote"]
        send_formatting_panel(call.message.chat.id, msg_id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
            # ================= 4. بناء الإعلان =================
@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    ad_builder_state[call.from_user.id] = {'step': 1, 'media_file_id': None, 'add_blur': False, 'group_type': None, 'group_link': None, 'user_id_handle': None, 'custom_text': None, 'channel_username': None}
    markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("Furry", callback_data="ad_type_furry"), InlineKeyboardButton("Tumblr", callback_data="ad_type_tumblr"), InlineKeyboardButton("Mixed", callback_data="ad_type_mixed"))
    bot.edit_message_text("<b>السؤال 1:</b> نوع المجموعة؟", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_type(call):
    ad_builder_state[call.from_user.id]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[call.from_user.id]['step'] = 2
    markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("نعم", callback_data="ad_has_channel_yes"), InlineKeyboardButton("لا", callback_data="ad_has_channel_no"))
    bot.edit_message_text("<b>السؤال 2:</b> هل لديك قناة؟", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_has_channel_yes")
def ad_ch_yes(call):
    ad_builder_state[call.from_user.id]['step'] = 2.5
    bot.edit_message_text("أرسل يوزر القناة:", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_has_channel_no")
def ad_ch_no(call):
    ad_builder_state[call.from_user.id]['step'] = 3
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step3"))
    bot.edit_message_text("<b>السؤال 3:</b> أرسل رابط المجموعة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.from_user.id in ad_builder_state and ad_builder_state[m.from_user.id]['step'] == 2.5)
def ad_receive_channel(message):
    ad_builder_state[message.from_user.id]['channel_username'] = message.text.strip()
    ad_builder_state[message.from_user.id]['step'] = 3
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step3"))
    bot.send_message(message.chat.id, "<b>السؤال 3:</b> أرسل رابط المجموعة:", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_step3")
def ad_s3(call):
    ad_builder_state[call.from_user.id]['step'] = 4
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step4"))
    bot.edit_message_text("<b>السؤال 4:</b> أرسل معرف حسابك:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_step4")
def ad_s4(call):
    ad_builder_state[call.from_user.id]['step'] = 5
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step5"))
    bot.edit_message_text("<b>السؤال 5:</b> أرسل رسالة ترويجية:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_step5")
def ad_s5(call):
    ad_builder_state[call.from_user.id]['step'] = 6
    markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("صورة", callback_data="ad_media_photo"), InlineKeyboardButton("فيديو", callback_data="ad_media_video"))
    bot.edit_message_text("<b>السؤال 6:</b> صورة أم فيديو؟", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_media_photo")
def ad_mp(call):
    ad_builder_state[call.from_user.id]['step'] = 6.5
    bot.edit_message_text("أرسل الصورة:", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_media_video")
def ad_mv(call):
    ad_builder_state[call.from_user.id]['step'] = 6.5
    bot.edit_message_text("أرسل الفيديو:", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(content_types=['photo', 'video'])
def ad_media(message):
    uid = message.from_user.id
    if uid in ad_builder_state and ad_builder_state[uid]['step'] == 6.5:
        ad_builder_state[uid]['media_file_id'] = message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id
        ad_builder_state[uid]['step'] = 7
        markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("تغويش", callback_data="ad_blur_yes"), InlineKeyboardButton("تخطي", callback_data="ad_blur_no"))
        bot.send_message(message.chat.id, "<b>السؤال 7:</b> هل تريد تغويش الوسائط؟", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data in ["ad_blur_yes", "ad_blur_no"])
def ad_blur(call):
    ad_builder_state[call.from_user.id]['add_blur'] = (call.data == "ad_blur_yes")
    ad_builder_state[call.from_user.id]['step'] = 8
    finalize_ad(call.message, call.from_user.id)

def finalize_ad(message, uid):
    data = ad_builder_state[uid]
    prompt = f"Write a short Telegram ad (no emojis, no asterisks) based on: Type: {data['group_type']}, Link: {data['group_link']}, Owner: {data['user_id_handle']}, Text: {data['custom_text']}. Put the invitation in <blockquote>."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="qwen/qwen3.8-27b", max_tokens=400)
        ad_text = res.choices[0].message.content.strip().replace("**", "").replace("*", "")
    except: ad_text = data['custom_text']
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("تأكيد النشر", callback_data="ad_publish_final"))
    if data['media_file_id']:
        try:
            bot.send_video(message.chat.id, data['media_file_id'], caption=ad_text, reply_markup=markup, parse_mode='HTML', has_spoiler=data['add_blur'])
        except: bot.send_photo(message.chat.id, data['media_file_id'], caption=ad_text, reply_markup=markup, parse_mode='HTML')
    else: bot.send_message(message.chat.id, ad_text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_publish_final")
def ad_publish(call):
    target_channel = user_channels.get(str(call.from_user.id))
    if not target_channel: return bot.answer_callback_query(call.id, "⚠️ القناة غير مرتبطة.", show_alert=True)
    bot.answer_callback_query(call.id, "✅ تم النشر بنجاح.", show_alert=True)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    del ad_builder_state[call.from_user.id]
    bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

# ================= 5. استقبال الصور العادية =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = message.from_user.id
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_cover':
        audio_edit_state[uid]['cover_data'] = bot.download_file(bot.get_file(message.photo[-1].file_id).file_path)
        audio_edit_state[uid]['step'] = 'waiting_for_audio'
        bot.send_message(message.chat.id, "<b>الخطوة 2:</b> أرسل ملف الصوت (MP3):", parse_mode='HTML')
        return
    if uid in ad_builder_state and ad_builder_state[uid]['step'] == 6.5: return
    if uid != ADMIN_ID and str(uid) not in user_channels:
        return bot.send_message(message.chat.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت أولاً.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("التحقق", callback_data="verify_channel")))
    settings = user_settings.get(uid, get_default_settings())
    if settings["status"] == "OFF": return bot.send_message(message.chat.id, "معطل.", reply_markup=get_main_panel(uid))
    msg_loading = bot.send_message(message.chat.id, "جاري التحليل...")
    try:
        base64_image = base64.b64encode(bot.download_file(bot.get_file(message.photo[-1].file_id).file_path)).decode('utf-8')
        lang = "جملة عربية واحدة (لا تتجاوز 10 كلمات) ثم ترجمتها الإنجليزية في سطر واحد" if settings['language'] == "مختلط" else f"باللغة {settings['language']}"
        prompt = f"اكتب تعليقاً قصيراً جداً (سطر واحد) بأسلوب {settings['category']} ({lang}). بدون إيموجي."
        res = client.chat.completions.create(messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}], model="qwen/qwen3.8-27b", max_tokens=500)
        ai_text = res.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>\n\n{settings['hashtags']}" if settings["add_hashtags"] else f"<b>{ai_text}</b>"
        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'photo', 'file_id': message.photo[-1].file_id, 'caption': final_caption, 'channel': user_channels.get(str(uid))}
        saved_images[post_id] = {'photo_id': message.photo[-1].file_id, 'user_id': uid, 'settings': settings, 'channel': user_channels.get(str(uid))}
        markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_image_{post_id}"), InlineKeyboardButton("إضافة ملف صوتي", callback_data=f"add_audio_to_post_{post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_message(message.chat.id, f"خطأ: {e}", reply_markup=get_main_panel(uid))

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio_merge(message):
    uid = message.from_user.id
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_audio':
        file_id = message.audio.file_id if message.content_type == 'audio' else (message.document.file_id if message.document.mime_type == 'audio/mpeg' else None)
        if not file_id: return bot.reply_to(message, "❌ يرجى إرسال ملف بصيغة MP3.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, audio_edit_state[uid]['cover_data'])
            audio_buffer = io.BytesIO(rebuilt)
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton(f"{CHANNEL_NAME}", url=CHANNEL_LINK)).add(InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{uid}"))
            bot.send_audio(message.chat.id, audio_buffer, title="Red world | عالم الأحمر", performer="@Eror_7", thumb=cover_jpg)
            bot.send_message(message.chat.id, f"تم إضافة الحقوق بنجاح.", reply_markup=markup)
        except Exception as e: bot.send_message(message.chat.id, f"❌ خطأ: {e}")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_standalone_audio_"))
def publish_standalone_audio(call):
    uid = int(call.data.split("_")[3])
    target_channel = user_channels.get(str(uid))
    if not target_channel: return bot.answer_callback_query(call.id, "⚠️ القناة غير مرتبطة.", show_alert=True)
    bot.answer_callback_query(call.id, "✅ تم النشر بنجاح!", show_alert=True)
    del audio_edit_state[uid]
    bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(uid), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_audio_to_post_"))
def add_audio_to_post(call):
    post_id = call.data.split("_")[4]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية", show_alert=True)
    pending_audio_merge[call.from_user.id] = {'post_id': post_id, 'photo_id': pending_posts[post_id]['file_id'], 'caption': pending_posts[post_id]['caption'], 'channel': pending_posts[post_id]['channel']}
    bot.edit_message_text("<b>⟨ إضافة ملف صوتي ⟩</b>\n\nأرسل ملف الصوت (MP3) الآن:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("schedule_"))
def schedule(call):
    post_id = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, "⏳ أرسل عدد الدقائق للتأجيل (مثال: 30):")
    bot.register_next_step_handler(msg, lambda m: (time.sleep(int(m.text)*60), bot.send_message(user_channels.get(str(m.from_user.id)), pending_posts[post_id]['caption'], parse_mode='HTML') if post_id in pending_posts else None, send_welcome(m)))

# ================= 6. الأزرار الأساسية =================
@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    if str(call.from_user.id) in user_channels:
        del user_channels[str(call.from_user.id)]
        save_json(DB_FILE, user_channels)
        bot.answer_callback_query(call.id, text="✅ تم إلغاء الارتباط.", show_alert=True)
        send_welcome(call.message)
    else: bot.answer_callback_query(call.id, "⚠️ لا توجد قناة مرتبطة.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "show_stats")
def show_stats(call):
    cid = user_channels.get(str(call.from_user.id))
    if not cid: return bot.answer_callback_query(call.id, "⚠️ القناة غير مرتبطة.", show_alert=True)
    try: bot.edit_message_text(f"<b>⟨ التقرير ⟩</b>\n\n<blockquote><b>القناة:</b> {bot.get_chat(cid).title}\n<b>المشتركين:</b> {bot.get_chat_member_count(cid)}\n<b>المنشورات:</b> {stats['published_count']}</blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu")), parse_mode='HTML')
    except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "show_source")
def show_source(call):
    try: dev_name = bot.get_chat(ADMIN_ID).first_name
    except: dev_name = "المطور"
    bot.edit_message_text(f"<b>⟨ RED WORLD ⟩</b>\n\n<blockquote><b>المطور:</b> {dev_name}\n<b>البوت:</b> @{bot.get_me().username}</blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton(f"المطور: {dev_name}", url=f"tg://user?id={ADMIN_ID}"), InlineKeyboardButton("رجوع", callback_data="main_menu")), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_post(call):
    post_id = call.data.split("_")[1]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية")
    data = pending_posts[post_id]
    try:
        if data['type'] == 'photo': bot.send_photo(data['channel'], data['file_id'], caption=data['caption'], parse_mode='HTML')
        else: bot.send_message(data['channel'], data['caption'], parse_mode='HTML')
        stats["published_count"] += 1; save_json(STATS_FILE, stats)
        bot.answer_callback_query(call.id, text="تم النشر")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
        del pending_posts[post_id]
    except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel_post(call):
    post_id = call.data.split("_")[1]
    if post_id in pending_posts: del pending_posts[post_id]
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("regen_image_"))
def regen_image(call):
    post_id = call.data.split("_")[2]
    if post_id not in saved_images: return bot.answer_callback_query(call.id, "انتهت الصلاحية", show_alert=True)
    data = saved_images[post_id]
    try:
        base64_image = base64.b64encode(bot.download_file(bot.get_file(data['photo_id']).file_path)).decode('utf-8')
        lang = "جملة عربية واحدة (لا تتجاوز 10 كلمات) ثم ترجمتها الإنجليزية في سطر واحد" if data['settings']['language'] == "مختلط" else f"باللغة {data['settings']['language']}"
        prompt = f"اكتب تعليقاً قصيراً جداً (سطر واحد) بأسلوب {data['settings']['category']} ({lang}). بدون إيموجي."
        res = client.chat.completions.create(messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}], model="qwen/qwen3.8-27b", max_tokens=500)
        final_caption = f"<b>{res.choices[0].message.content.strip()}</b>\n\n{data['settings']['hashtags']}" if data['settings']['add_hashtags'] else f"<b>{res.choices[0].message.content.strip()}</b>"
        new_post_id = str(int(time.time()))
        pending_posts[new_post_id] = {'type': 'photo', 'file_id': data['photo_id'], 'caption': final_caption, 'channel': data['channel']}
        saved_images[new_post_id] = data
        markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{new_post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{new_post_id}"), InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_image_{new_post_id}"), InlineKeyboardButton("إضافة ملف صوتي", callback_data=f"add_audio_to_post_{new_post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{new_post_id}"))
        bot.send_photo(call.message.chat.id, photo=data['photo_id'], caption=f"<b>معاينة جديدة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    except Exception as e: bot.send_message(call.message.chat.id, f"خطأ: {e}")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.startswith('/'): return
    if message.from_user.id != ADMIN_ID and str(message.from_user.id) not in user_channels:
        return bot.send_message(message.chat.id, "⛔ عذراً، يجب التحقق أولاً.")
    settings = user_settings.get(message.from_user.id, get_default_settings())
    if settings["text_only_mode"] and settings["status"] == "ON":
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        try:
            res = client.chat.completions.create(messages=[{"role": "user", "content": f"اكتب عبارة قصيرة جداً (سطر واحد) بأسلوب {settings['category']}. بدون إيموجي."}], model="qwen/qwen3.8-27b", max_tokens=500)
            final_caption = f"<b>{res.choices[0].message.content.strip()}</b>\n\n{settings['hashtags']}"
            post_id = str(int(time.time()))
            pending_posts[post_id] = {'type': 'text', 'caption': final_caption, 'channel': user_channels.get(str(message.from_user.id))}
            markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
            bot.send_message(message.chat.id, f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
        except: pass

@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    audio_edit_state[call.from_user.id] = {'step': 'waiting_for_cover'}
    bot.edit_message_text("<b>⟨ حقوق النشر الصوتي ⟩</b>\n\nالخطوة 1: أرسل الصورة (Cover):", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

print("Bot is running...")
bot.infinity_polling()
