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
GROQ_MODEL = "openai/gpt-oss-120b" # تم تغييره لتجنب حد Qwen

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
DB_FILE, STATS_FILE = "user_channels.json", "stats.json"

audio_edit_state, pending_audio_merge, ad_builder_state = {}, {}, {}
image_gen_state, video_gen_state, chat_state, welcome_media_state = {}, {}, {}, {}
audio_cache = {}

MSGS = {
    "welcome": "<b>بوابة عالم الأحمر</b>\n────────────────────\n\n<blockquote>أهلاً بك في <b>R W | Bot</b>\nنظام إدارة قنوات تيليجرام باحترافية.</blockquote>",
    "force_sub": "<b>بوابة مغلقة</b>\n────────────────────\n\n<blockquote>للدخول إلى <b>عالم الأحمر</b>،\nيجب الانضمام إلى قنواتنا أولاً:\n\n<a href='https://t.me/Eror_7'>@Eror_7</a>\n<a href='https://t.me/lb2_c'>@lb2_c</a></blockquote>",
    "control_panel": "<b>غرفة التحكم</b>\n────────────────────\n\n<blockquote>مرحباً بك في مركز إدارة عالم الأحمر.</blockquote>",
    "not_verified": "<b>وصول مرفوض</b>\n\n<blockquote>يجب التحقق من رفع البوت أولاً.</blockquote>",
}

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
            "hashtags": "#RedWorld #عالم_الأحمر", "welcome_photo": None}

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

@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID and not check_subscription(user_id):
        return send_force_sub_message(message.chat.id)
    if user_id not in user_settings: user_settings[user_id] = get_default_settings()
    
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة البوت لقناتك (مشرف)", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
        InlineKeyboardButton("التحقق من الرفع (فحص تلقائي)", callback_data="verify_channel"),
        InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
        
    settings = user_settings[user_id]
    if settings.get("welcome_photo"):
        bot.send_photo(message.chat.id, settings["welcome_photo"], caption=MSGS["welcome"], reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, MSGS["welcome"], reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "تم التحقق بنجاح، أهلاً بك.", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "لم تشترك في جميع القنوات بعد.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id, "جاري الفحص...")
    channel_id = user_channels.get(str(call.from_user.id))
    if not channel_id:
        msg = bot.send_message(call.message.chat.id, "<b>إدخال معرف القناة</b>\n\n<blockquote>أرسل معرف القناة الآن\nمثال: <code>@Eror_7</code></blockquote>", parse_mode='HTML')
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
    msg_loading = bot.send_message(chat_id, "<i>جاري فحص القناة...</i>", parse_mode='HTML')
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        if bot_member.status in ['administrator', 'creator'] and getattr(bot_member, 'can_post_messages', False):
            success_text = f"<b>تم التحقق</b>\n\n<blockquote><b>القناة:</b> {chat_info.title}</blockquote>"
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
            bot.edit_message_text(success_text, chat_id=chat_id, message_id=msg_loading.message_id, reply_markup=markup, parse_mode='HTML')
        else:
            bot.edit_message_text("<b>فشل الفحص</b>\n\n<blockquote>البوت ليس مشرفاً أو لا يملك صلاحية النشر.</blockquote>", chat_id=chat_id, message_id=msg_loading.message_id, parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(f"<b>خطأ</b>\n\n<blockquote>{e}</blockquote>", chat_id=chat_id, message_id=msg_loading.message_id, parse_mode='HTML')

@bot.my_chat_member_handler()
def bot_added_to_channel(update: telebot.types.ChatMemberUpdated):
    new_status = update.new_chat_member.status
    if new_status in ('administrator', 'member') and update.chat.type == 'channel':
        adder_id = update.from_user.id
        channel_identifier = f"@{update.chat.username}" if update.chat.username else str(update.chat.id)
        user_channels[str(adder_id)] = channel_identifier
        save_json(DB_FILE, user_channels)
        try:
            bot.send_message(adder_id, f"تمت إضافة البوت إلى القناة: {update.chat.title}", parse_mode='HTML')
        except: pass

def get_main_panel(user_id):
    settings = user_settings.get(user_id, get_default_settings())
    welcome_btn = "تغيير صورة الترحيب (مفعلة)" if settings.get("welcome_photo") else "تعيين صورة الترحيب"
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("إنشاء محتوى (صورة/فيديو)", callback_data="menu_create"),
        InlineKeyboardButton("التوليد النصي والإعلانات", callback_data="menu_tools"),
        InlineKeyboardButton(welcome_btn, callback_data="set_welcome_photo"),
        InlineKeyboardButton("دردشة Gaski", callback_data="start_chat_gaski"),
        InlineKeyboardButton("السورس", callback_data="show_source"),
        InlineKeyboardButton("مغادرة القناة", callback_data="leave_channel")
    )
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    bot.answer_callback_query(call.id, "تم فتح غرفة التحكم.")
    try:
        bot.edit_message_text(MSGS["control_panel"], chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    except:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, MSGS["control_panel"], reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
        @bot.callback_query_handler(func=lambda call: call.data == "menu_create")
def menu_create(call):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("إرسال صورة", callback_data="send_photo_mode"),
        InlineKeyboardButton("إرسال فيديو", callback_data="send_video_mode"),
        InlineKeyboardButton("رجوع", callback_data="main_menu")
    )
    bot.edit_message_text("<b>إنشاء محتوى</b>\nاختر نوع الوسائط التي تريد إرسالها:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "menu_tools")
def menu_tools(call):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("عبارات طويلة", callback_data="generate_long_text"),
        InlineKeyboardButton("عبارات مختصرة", callback_data="generate_short_text"),
        InlineKeyboardButton("إنشاء إعلان ترويجي", callback_data="start_ad_builder"),
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit"),
        InlineKeyboardButton("رجوع", callback_data="main_menu")
    )
    bot.edit_message_text("<b>التوليد والأدوات</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

# --- نظام استقبال الصورة والفيديو ---
@bot.callback_query_handler(func=lambda call: call.data == "send_photo_mode")
def trigger_photo_mode(call):
    image_gen_state[call.from_user.id] = {'step': 'waiting_for_photo'}
    bot.edit_message_text("<b>أرسل الصورة الآن</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="menu_create")))

@bot.callback_query_handler(func=lambda call: call.data == "send_video_mode")
def trigger_video_mode(call):
    video_gen_state[call.from_user.id] = {'step': 'waiting_for_video'}
    bot.edit_message_text("<b>أرسل الفيديو الآن</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="menu_create")))

@bot.message_handler(content_types=['photo'])
def handle_photo_new(message):
    uid = message.from_user.id
    # إذا كان المستخدم يرفع صورة ترحيب
    if uid in welcome_media_state:
        settings = user_settings.get(uid, get_default_settings())
        settings["welcome_photo"] = message.photo[-1].file_id
        user_settings[uid] = settings
        del welcome_media_state[uid]
        bot.send_message(message.chat.id, "تم تعيين الصورة بنجاح كترحيب.", reply_markup=get_main_panel(uid))
        return

    # إذا كان المستخدم يرسل صورة لإنشاء محتوى
    if uid in image_gen_state and image_gen_state[uid]['step'] == 'waiting_for_photo':
        image_gen_state[uid]['file_id'] = message.photo[-1].file_id
        image_gen_state[uid]['step'] = 'waiting_category'
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("حزين", callback_data="img_cat_حزين"), InlineKeyboardButton("فلسفي", callback_data="img_cat_فلسفي"), InlineKeyboardButton("حب", callback_data="img_cat_حب"), InlineKeyboardButton("اقتباس", callback_data="img_cat_اقتباس"), InlineKeyboardButton("رجوع", callback_data="menu_create"))
        bot.send_message(message.chat.id, "<b>اختر فئة العبارة:</b>", reply_markup=markup, parse_mode='HTML')

@bot.message_handler(content_types=['video'])
def handle_video_new(message):
    uid = message.from_user.id
    if uid in video_gen_state and video_gen_state[uid]['step'] == 'waiting_for_video':
        video_gen_state[uid]['file_id'] = message.video.file_id
        video_gen_state[uid]['step'] = 'waiting_category'
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("حزين", callback_data="vid_cat_حزين"), InlineKeyboardButton("فلسفي", callback_data="vid_cat_فلسفي"), InlineKeyboardButton("حب", callback_data="vid_cat_حب"), InlineKeyboardButton("اقتباس", callback_data="vid_cat_اقتباس"), InlineKeyboardButton("رجوع", callback_data="menu_create"))
        bot.send_message(message.chat.id, "<b>اختر فئة العبارة:</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("img_cat_") or call.data.startswith("vid_cat_"))
def media_category(call):
    uid = call.from_user.id
    is_img = call.data.startswith("img_cat_")
    cat = call.data.replace("img_cat_", "").replace("vid_cat_", "")
    
    if is_img and uid in image_gen_state:
        image_gen_state[uid]['category'] = cat
    elif not is_img and uid in video_gen_state:
        video_gen_state[uid]['category'] = cat

    markup = InlineKeyboardMarkup(row_width=2)
    prefix = "img" if is_img else "vid"
    markup.add(InlineKeyboardButton("خط مائل", callback_data=f"{prefix}_fmt_italic"), InlineKeyboardButton("خط غامض", callback_data=f"{prefix}_fmt_bold"), InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    bot.edit_message_text(f"<b>الفئة: {cat}</b>\nاختر التنسيق:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

# --- دردشة Gaski ---
@bot.callback_query_handler(func=lambda call: call.data == "start_chat_gaski")
def start_gaski_chat(call):
    chat_state[call.from_user.id] = True
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إنهاء الدردشة", callback_data="main_menu"))
    bot.edit_message_text("<b>دردشة Gaski</b>\nأرسل رسالتك الآن.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.from_user.id in chat_state, content_types=['text'])
def handle_chat_message(message):
    if message.text.startswith('/'): return
    msg = bot.reply_to(message, "<i>يفكر...</i>", parse_mode='HTML')
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": message.text}], model=GROQ_MODEL, max_tokens=500)
        bot.edit_message_text(res.choices[0].message.content, chat_id=message.chat.id, message_id=msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"خطأ: {e}", chat_id=message.chat.id, message_id=msg.message_id)

# --- صورة الترحيب ---
@bot.callback_query_handler(func=lambda call: call.data == "set_welcome_photo")
def set_welcome_photo(call):
    welcome_media_state[call.from_user.id] = True
    bot.edit_message_text("<b>أرسل الصورة التي تريد تعيينها كترحيب</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu")), parse_mode='HTML')
    # --- حقوق النشر الصوتي ---
@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    audio_edit_state[call.from_user.id] = {'step': 'waiting_for_cover', 'cover_data': None}
    bot.edit_message_text("<b>ختم الحقوق الصوتي</b>\n\n<blockquote>أرسل صورة الغلاف</blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    uid = message.from_user.id
    if uid in audio_edit_state and audio_edit_state[uid]['step'] in ['waiting_for_cover', 'waiting_for_audio']:
        if audio_edit_state[uid]['step'] == 'waiting_for_cover' and message.content_type == 'photo': return
        file_id = message.audio.file_id if message.content_type == 'audio' else (message.document.file_id if message.document and message.document.mime_type == 'audio/mpeg' else None)
        if not file_id: return bot.reply_to(message, "أرسل ملفاً بصيغة MP3.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            cover_data = audio_edit_state[uid].get('cover_data') or b''
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data)
            audio_cache[uid] = {'data': rebuilt, 'cover': cover_jpg}
            
            # زر واحد فقط تحت الملف الصوتي
            markup = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("Red World | عالم الأحمر", url=CHANNEL_LINK),
                InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{uid}")
            )
            bot.send_audio(message.chat.id, io.BytesIO(rebuilt), title="Red World", performer="@Eror_7", thumb=cover_jpg if cover_jpg else None)
            bot.send_message(message.chat.id, "<b>تم الختم.</b>", reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_standalone_audio_"))
def publish_standalone_audio(call):
    uid = int(call.data.split("_")[3])
    target_channel = user_channels.get(str(uid))
    if not target_channel: return bot.answer_callback_query(call.id, "القناة غير مرتبطة.", show_alert=True)
    if uid not in audio_cache: return bot.answer_callback_query(call.id, "انتهت الصلاحية.", show_alert=True)
    try:
        cached = audio_cache[uid]
        # الزر ملتصق بالملف الصوتي هنا
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Red World | عالم الأحمر", url=CHANNEL_LINK))
        bot.send_audio(target_channel, io.BytesIO(cached['data']), title="Red World", performer="@Eror_7", thumb=cached['cover'] if cached['cover'] else None, reply_markup=markup)
        stats["published_count"] += 1; save_json(STATS_FILE, stats)
        bot.answer_callback_query(call.id, "تم النشر.")
        if uid in audio_edit_state: del audio_edit_state[uid]
        if uid in audio_cache: del audio_cache[uid]
        bot.send_message(call.message.chat.id, "<b>غرفة التحكم</b>", reply_markup=get_main_panel(uid), parse_mode='HTML')
    except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

# --- توليد النصوص ---
@bot.callback_query_handler(func=lambda call: call.data in ["generate_long_text", "generate_short_text"])
def generate_text(call):
    bot.answer_callback_query(call.id, "جاري التوليد...")
    settings = user_settings.get(call.from_user.id, get_default_settings())
    length = "عبارة مفصلة من 3 إلى 4 أسطر" if call.data == 'generate_long_text' else "عبارة قصيرة من سطر واحد"
    prompt = f"اكتب {length} بأسلوب {settings['category']} باللغة {settings['language']}. بدون إيموجي."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=500)
        raw_text = res.choices[0].message.content.strip()
        msg_id = str(int(time.time()))
        generated_texts[msg_id] = {"raw": raw_text, "bold": False, "italic": False, "quote": False}
        bot.send_message(call.message.chat.id, f"<b>مخطوطة جديدة</b>\n\n{raw_text}", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu")), parse_mode='HTML')
    except Exception as e: bot.send_message(call.message.chat.id, f"خطأ: {e}")

# --- الإعلان والسورس (مختصر) ---
@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    ad_builder_state[call.from_user.id] = {'step': 'waiting_group_name'}
    bot.edit_message_text("<b>بروتوكول الإعلان 1/7</b>\n\n<blockquote>أرسل اسم المجموعة</blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.from_user.id in ad_builder_state)
def ad_step_handler(message):
    uid = message.from_user.id
    data = ad_builder_state[uid]
    if data['step'] == 'waiting_group_name':
        data['group_name'] = message.text.strip()
        data['step'] = 'waiting_group_type'
        markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("تمبلر", callback_data="ad_type_تمبلر"), InlineKeyboardButton("فري", callback_data="ad_type_فري"), InlineKeyboardButton("مزج", callback_data="ad_type_مزج"))
        bot.send_message(message.chat.id, "<b>2/7</b> اختر نوع المجموعة:", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_set_type(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[uid]['step'] = 'waiting_group_link'
    bot.edit_message_text("<b>3/7</b> أرسل رابط المجموعة:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "show_source")
def show_source(call):
    bot.answer_callback_query(call.id)
    try: dev_name = bot.get_chat(ADMIN_ID).first_name or "Developer"
    except: dev_name = "Developer"
    ch_id = user_channels.get(str(call.from_user.id))
    text = "<b>[ SYSTEM INFO: RED WORLD ]</b>\n────────────────────\n\n"
    if ch_id:
        try:
            ch = bot.get_chat(ch_id)
            text += f"<b>Channel:</b> {ch.title}\n<b>Channel ID:</b> <code>{ch.id}</code>\n\n"
        except: pass
    text += f"<b>Developer:</b> {dev_name}\n<b>Bot:</b> @{bot.get_me().username}\n\n<blockquote>Code. Exploit. Dominate.</blockquote>"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton(f"Developer: {dev_name}", url=f"tg://user?id={ADMIN_ID}"), InlineKeyboardButton("Back", callback_data="main_menu"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    if str(call.from_user.id) in user_channels:
        del user_channels[str(call.from_user.id)]
        save_json(DB_FILE, user_channels)
    bot.answer_callback_query(call.id, "تم فك الارتباط.")
    main_menu(call)

# --- تشغيل البوت ---
print("Red World Bot is running...")
bot.infinity_polling()
