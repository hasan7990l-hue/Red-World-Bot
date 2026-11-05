import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time, base64, threading, json, os, io, re
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error as ID3Error
from PIL import Image

# ==========================================
#               الإعدادات
# ==========================================
TELEGRAM_TOKEN = "8180650384:AAHX37rerimsZIWBEc71HleexJKWqSaSsZ0"
GROQ_API_KEY   = "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"

ADMIN_ID = 8456056018
FORCE_CHANNELS = ["@Eror_7", "@lb2_c"]
CHANNEL_NAME = "عالم الأحمر | Red world"
CHANNEL_LINK = "https://t.me/Eror_7"
GROQ_MODEL = "openai/gpt-oss-120b" 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
DB_FILE, STATS_FILE = "user_channels.json", "stats.json"

# الحالات
audio_edit_state, pending_audio_merge, ad_builder_state = {}, {}, {}
image_gen_state, video_gen_state, chat_state, welcome_media_state = {}, {}, {}, {}
audio_cache = {}
user_channels, stats, user_settings = {}, {}, {}
generated_texts, pending_posts, saved_images = {}, {}, {}

MENU_TEXTS = {
    "main_menu": "<b>⟨ غرفة التحكم ⟩</b>\n────────────────────\n\n<blockquote>مرحباً بك في مركز إدارة عالم الأحمر.\nاختر القسم الذي ترغب في إدارته من الأسفل.</blockquote>",
    "menu_create": "<b>⟨ استوديو المحتوى ⟩</b>\n────────────────────\n\n<blockquote>من هنا يمكنك إنشاء منشوراتك.\nاختر إرسال صورة أو فيديو، وسيقوم الذكاء الاصطناعي بتوليد عبارة مناسبة لك بناءً على الفئة التي تختارها.</blockquote>",
    "menu_tools": "<b>⟨ أدوات التوليد والنشر ⟩</b>\n────────────────────\n\n<blockquote>هنا تجد أدوات التوليد النصي بالذكاء الاصطناعي، وبناء الإعلانات الترويجية، وختم الحقوق الصوتية للملفات.</blockquote>",
    "start_chat_gaski": "<b>⟨ دردشة Gaski ⟩</b>\n────────────────────\n\n<blockquote>أهلاً بك في العقل المدبر.\nتحدث معي بحرية، اسألني أي شيء، وسأجيبك بأفضل ما لدي.</blockquote>",
    "start_ad_builder": "<b>⟨ بروتوكول الإعلان ⟩</b>\n────────────────────\n\n<blockquote>سنقوم ببناء إعلان احترافي لمجموعتك.\nأجب على الأسئلة خطوة بخطوة، وسيتولى الذكاء الاصطناعي صياغة الإعلان.</blockquote>",
    "start_audio_edit": "<b>⟨ ختم الحقوق الصوتي ⟩</b>\n────────────────────\n\n<blockquote>أضف غلافك وحقوقك إلى ملفاتك الصوتية.\nأرسل صورة الغلاف أولاً، ثم أرسل ملف الصوت MP3.</blockquote>",
    "send_photo_mode": "<b>⟨ إرسال صورة ⟩</b>\n────────────────────\n\n<blockquote>أرسل الصورة التي تريد إنشاء عبارة عليها.\nسيتم تحليل الصورة واقتراح عبارة مناسبة لها بناءً على الفئة التي تختارها لاحقاً.</blockquote>",
    "send_video_mode": "<b>⟨ إرسال فيديو ⟩</b>\n────────────────────\n\n<blockquote>أرسل الفيديو الذي تريد إنشاء عبارة عليه.\nسيتم تحليل الفيديو واقتراح عبارة مناسبة له بناءً على الفئة التي تختارها لاحقاً.</blockquote>",
    "waiting_for_photo": "<b>⟨ في انتظار الصورة ⟩</b>\n────────────────────\n\n<blockquote>يرجى إرسال الصورة الآن في المحادثة.\nاضغط على زر (رجوع) إذا غيرت رأيك.</blockquote>",
    "waiting_for_video": "<b>⟨ في انتظار الفيديو ⟩</b>\n────────────────────\n\n<blockquote>يرجى إرسال الفيديو الآن في المحادثة.\nاضغط على زر (رجوع) إذا غيرت رأيك.</blockquote>",
    "welcome": "<b>⟨ بوابة عالم الأحمر ⟩</b>\n────────────────────\n\n<blockquote>مرحباً بك في <b>R W | Bot</b>\nالنظام المتكامل لإدارة قنوات تيليجرام باحترافية.\n\nتوليد منشورات بالذكاء الاصطناعي\nإنشاء إعلانات ترويجية\nختم الحقوق الصوتية\nوالمزيد من الأدوات في لوحة التحكم.</blockquote>\n\n<i>اضغط على زر لوحة التحكم للبدء.</i>"
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
    for channel in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']: return False
        except: return False
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID and not check_subscription(user_id):
        markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("اشترك 1", url="https://t.me/Eror_7"),
            InlineKeyboardButton("اشترك 2", url="https://t.me/lb2_c"),
            InlineKeyboardButton("تحقق", callback_data="check_sub"))
        return bot.send_message(message.chat.id, "<b>بوابة مغلقة</b>\nاشترك أولاً.", reply_markup=markup, parse_mode='HTML')
    
    if user_id not in user_settings: user_settings[user_id] = get_default_settings()
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إضافة البوت لقناتك", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
        InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel"),
        InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
        
    settings = user_settings[user_id]
    if settings.get("welcome_photo"):
        bot.send_photo(message.chat.id, settings["welcome_photo"], caption=MENU_TEXTS["welcome"], reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, MENU_TEXTS["welcome"], reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "تم التحقق.", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        send_welcome(call.message)
    else: bot.answer_callback_query(call.id, "لم تشترك بعد.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id, "جاري الفحص...")
    channel_id = user_channels.get(str(call.from_user.id))
    if not channel_id:
        msg = bot.send_message(call.message.chat.id, "<b>أرسل معرف القناة:</b>\nمثال: <code>@Eror_7</code>", parse_mode='HTML')
        bot.register_next_step_handler(msg, manual_verify, call.from_user.id)
    else: perform_verification(call.message.chat.id, call.from_user.id, channel_id)

def manual_verify(message, user_id):
    channel_input = message.text.strip()
    if not channel_input.startswith('@'): channel_input = '@' + channel_input
    user_channels[str(user_id)] = channel_input
    save_json(DB_FILE, user_channels)
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
            bot.edit_message_text("<b>فشل:</b> البوت ليس مشرفاً.", chat_id=chat_id, message_id=msg.message_id, parse_mode='HTML')
    except Exception as e:
        bot.edit_message_text(f"<b>خطأ:</b> {e}", chat_id=chat_id, message_id=msg.message_id, parse_mode='HTML')

def get_main_panel(user_id): settings = user_settings.get(user_id, get_default_settings()); welcome_btn = "تغيير صورة الترحيب (مفعلة)" if settings.get("welcome_photo") else "تعيين صورة الترحيب"; markup = InlineKeyboardMarkup(row_width=1); markup.add(InlineKeyboardButton("إنشاء محتوى (صورة/فيديو)", callback_data="menu_create"), InlineKeyboardButton("التوليد النصي والإعلانات", callback_data="menu_tools"), InlineKeyboardButton(welcome_btn, callback_data="set_welcome_photo"), InlineKeyboardButton("دردشة Gaski", callback_data="start_chat_gaski"), InlineKeyboardButton("السورس", callback_data="show_source"), InlineKeyboardButton("مغادرة القناة", callback_data="leave_channel")); return markup

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(MENU_TEXTS["main_menu"], chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
    except:
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, MENU_TEXTS["main_menu"], reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "menu_create")
def menu_create(call):
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("إرسال صورة", callback_data="send_photo_mode"),
        InlineKeyboardButton("إرسال فيديو", callback_data="send_video_mode"),
        InlineKeyboardButton("رجوع", callback_data="main_menu")
    )
    bot.edit_message_text(MENU_TEXTS["menu_create"], chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "menu_tools")
def menu_tools(call):
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("إنشاء إعلان ترويجي", callback_data="start_ad_builder"),
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit"),
        InlineKeyboardButton("رجوع", callback_data="main_menu")
    )
    bot.edit_message_text(MENU_TEXTS["menu_tools"], chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "send_photo_mode")
def trigger_photo_mode(call):
    image_gen_state[call.from_user.id] = {'step': 'waiting_for_photo'}
    bot.edit_message_text(MENU_TEXTS["waiting_for_photo"], chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="menu_create")), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "send_video_mode")
def trigger_video_mode(call):
    video_gen_state[call.from_user.id] = {'step': 'waiting_for_video'}
    bot.edit_message_text(MENU_TEXTS["waiting_for_video"], chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="menu_create")), parse_mode='HTML')

@bot.message_handler(content_types=['photo'])
def handle_all_photos(message):
    uid = message.from_user.id
    if uid in audio_edit_state and audio_edit_state[uid].get('step') == 'waiting_for_cover':
        try:
            file_path = bot.get_file(message.photo[-1].file_id).file_path
            audio_edit_state[uid]['cover_data'] = bot.download_file(file_path)
            audio_edit_state[uid]['step'] = 'waiting_for_audio'
            bot.send_message(message.chat.id, "<b>⟨ تم حفظ الغلاف ⟩</b>\n\n<blockquote>الآن أرسل ملف الصوت MP3.</blockquote>", parse_mode='HTML')
        except Exception as e: bot.send_message(message.chat.id, f"خطأ: {e}")
        return
    if uid in welcome_media_state:
        settings = user_settings.get(uid, get_default_settings())
        settings["welcome_photo"] = message.photo[-1].file_id
        user_settings[uid] = settings
        del welcome_media_state[uid]
        bot.send_message(message.chat.id, "تم تعيين صورة الترحيب.", reply_markup=get_main_panel(uid))
        return
    if uid in image_gen_state and image_gen_state[uid].get('step') == 'waiting_for_photo':
        image_gen_state[uid]['file_id'] = message.photo[-1].file_id
        image_gen_state[uid]['step'] = 'waiting_category'
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("حزين", callback_data="img_cat_حزين"), InlineKeyboardButton("فلسفي", callback_data="img_cat_فلسفي"),
            InlineKeyboardButton("حب", callback_data="img_cat_حب"), InlineKeyboardButton("اقتباس", callback_data="img_cat_اقتباس"),
            InlineKeyboardButton("رجوع", callback_data="menu_create")
        )
        bot.send_message(message.chat.id, "<b>اختر الفئة:</b>", reply_markup=markup, parse_mode='HTML')

@bot.message_handler(content_types=['video'])
def handle_video_new(message):
    uid = message.from_user.id
    if uid in video_gen_state and video_gen_state[uid].get('step') == 'waiting_for_video':
        video_gen_state[uid]['file_id'] = message.video.file_id
        video_gen_state[uid]['step'] = 'waiting_category'
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("حزين", callback_data="vid_cat_حزين"), InlineKeyboardButton("فلسفي", callback_data="vid_cat_فلسفي"),
            InlineKeyboardButton("حب", callback_data="vid_cat_حب"), InlineKeyboardButton("اقتباس", callback_data="vid_cat_اقتباس"),
            InlineKeyboardButton("رجوع", callback_data="menu_create")
        )
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
        InlineKeyboardButton("إلغاء", callback_data="main_menu")
    )
    bot.edit_message_text(f"<b>⟨ الفئة: {cat} ⟩</b>\n────────────────────\n\n<blockquote>اختر لغة العبارة التي تريد توليدها.</blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

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
        InlineKeyboardButton("إلغاء", callback_data="main_menu")
    )
    bot.edit_message_text(f"<b>⟨ اللغة: {lang_choice} ⟩</b>\n────────────────────\n\n<blockquote>اختر تنسيق النص المطلوب.</blockquote>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("img_fmt_") or call.data.startswith("vid_fmt_"))
def media_format_and_publish(call):
    uid = call.from_user.id
    is_img = call.data.startswith("img_fmt_")
    fmt = call.data.split("_")[-1]
    if is_img and uid in image_gen_state: state = image_gen_state[uid]; file_id = state['file_id']; category = state.get('category', 'فلسفي'); lang = state.get('language', 'عربي'); media_type = 'photo'
    elif not is_img and uid in video_gen_state: state = video_gen_state[uid]; file_id = state['file_id']; category = state.get('category', 'فلسفي'); lang = state.get('language', 'عربي'); media_type = 'video'
    else: return bot.answer_callback_query(call.id, "انتهت الجلسة.", show_alert=True)
    bot.edit_message_text("⏳ جاري توليد العبارة...", chat_id=call.message.chat.id, message_id=call.message.message_id)
    lang_instr = "جملة عربية قصيرة ثم ترجمتها الإنجليزية في السطر التالي" if lang == "مختلط" else "باللغة العربية الفصحى"
    prompt = f"اكتب عبارة قصيرة جداً من سطر واحد بأسلوب {category} ({lang_instr}). بدون إيموجي، بدون نجوم، بدون علامات اقتباس."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=150)
        raw_text = res.choices[0].message.content.strip()
    except: raw_text = "عبارة تجريبية."
    final_text = f"<i>{raw_text}</i>" if fmt == "italic" else f"<b>{raw_text}</b>"
    settings = user_settings.get(uid, get_default_settings())
    final_caption = f"{final_text}\n\n{settings.get('hashtags', '')}"
    post_id = str(int(time.time()))
    pending_posts[post_id] = {'type': media_type, 'file_id': file_id, 'caption': final_caption, 'channel': user_channels.get(str(uid)), 'category': category, 'language': lang, 'format': fmt, 'is_img': is_img}
    markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_{post_id}"), InlineKeyboardButton("نشر الآن في القناة", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    if media_type == 'photo': bot.send_photo(call.message.chat.id, file_id, caption=f"<b>⟨ معاينة ⟩</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    else: bot.send_video(call.message.chat.id, file_id, caption=f"<b>⟨ معاينة ⟩</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "start_chat_gaski")
def start_gaski_chat(call):
    chat_state[call.from_user.id] = True
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("إنهاء الدردشة", callback_data="main_menu"))
    bot.edit_message_text(MENU_TEXTS["start_chat_gaski"], chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.from_user.id in chat_state, content_types=['text'])
def handle_chat_message(message):
    if message.text.startswith('/'): return
    msg = bot.reply_to(message, "<i>يفكر...</i>", parse_mode='HTML')
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": message.text}], model=GROQ_MODEL, max_tokens=500)
        bot.edit_message_text(res.choices[0].message.content, chat_id=message.chat.id, message_id=msg.message_id)
    except Exception as e: bot.edit_message_text(f"خطأ: {e}", chat_id=message.chat.id, message_id=msg.message_id)
        @bot.callback_query_handler(func=lambda call: call.data == "set_welcome_photo")
def set_welcome_photo(call):
    welcome_media_state[call.from_user.id] = True
    bot.edit_message_text("<b>أرسل الصورة:</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("إلغاء", callback_data="main_menu")), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    audio_edit_state[call.from_user.id] = {'step': 'waiting_for_cover', 'cover_data': None}
    bot.edit_message_text(MENU_TEXTS["start_audio_edit"], chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio(message):
    uid = message.from_user.id
    if uid in audio_edit_state and audio_edit_state[uid]['step'] == 'waiting_for_audio':
        file_id = message.audio.file_id if message.content_type == 'audio' else (message.document.file_id if message.document.mime_type == 'audio/mpeg' else None)
        if not file_id: return bot.reply_to(message, "أرسل MP3.")
        try:
            audio_data = bot.download_file(bot.get_file(file_id).file_path)
            cover_data = audio_edit_state[uid].get('cover_data')
            if not cover_data: return bot.reply_to(message, "لم يتم العثور على الغلاف.")
            rebuilt, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data)
            audio_cache[uid] = {'data': rebuilt, 'cover': cover_jpg}
            markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{uid}"))
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
        bot.send_audio(target_channel, io.BytesIO(cached['data']), title="Red World", performer="@Eror_7", thumb=cached['cover'] if cached['cover'] else None)
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("Red World | عالم الأحمر", url=CHANNEL_LINK))
        bot.send_message(target_channel, "<b>حقوق النشر محفوظة | Red World</b>", reply_markup=markup, parse_mode='HTML')
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
    prompt = f"اكتب عبارة قصيرة جداً من سطر واحد بأسلوب {category} ({lang_instr}). بدون إيموجي، استخدم أسلوباً مختلفاً."
    try:
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=GROQ_MODEL, max_tokens=150)
        raw_text = res.choices[0].message.content.strip()
    except: raw_text = "عبارة تجريبية."
    final_text = f"<i>{raw_text}</i>" if fmt == "italic" else f"<b>{raw_text}</b>"
    settings = user_settings.get(call.from_user.id, get_default_settings())
    final_caption = f"{final_text}\n\n{settings.get('hashtags', '')}"
    data['caption'] = final_caption
    pending_posts[post_id] = data
    markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_{post_id}"), InlineKeyboardButton("نشر الآن في القناة", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("إلغاء", callback_data="main_menu"))
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
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
        stats["published_count"] += 1; save_json(STATS_FILE, stats)
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
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "leave_channel")
def leave_channel(call):
    if str(call.from_user.id) in user_channels:
        del user_channels[str(call.from_user.id)]
        save_json(DB_FILE, user_channels)
    bot.answer_callback_query(call.id, "تم فك الارتباط.")
    main_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    ad_builder_state[call.from_user.id] = {'step': 'waiting_group_name'}
    bot.edit_message_text(MENU_TEXTS["start_ad_builder"], chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.from_user.id in ad_builder_state)
def ad_step_handler(message):
    uid = message.from_user.id
    data = ad_builder_state[uid]
    step = data.get('step')
    if step == 'waiting_group_name':
        data['group_name'] = message.text.strip()
        data['step'] = 'waiting_group_type'
        markup = InlineKeyboardMarkup(row_width=3).add(InlineKeyboardButton("تمبلر", callback_data="ad_type_تمبلر"), InlineKeyboardButton("فري", callback_data="ad_type_فري"), InlineKeyboardButton("مزج", callback_data="ad_type_مزج"))
        bot.send_message(message.chat.id, "<b>⟨ 2/7 ⟩ اختر نوع المجموعة:</b>", reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_set_type(call):
    uid = call.from_user.id
    if uid not in ad_builder_state: return
    ad_builder_state[uid]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[uid]['step'] = 'waiting_group_link'
    bot.edit_message_text("<b>⟨ 3/7 ⟩ أرسل رابط المجموعة:</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

print("Red World Bot is running...")
bot.infinity_polling()
