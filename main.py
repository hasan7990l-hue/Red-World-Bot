import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time
import base64
import datetime
import threading
import json
import os
import io
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, error as ID3Error

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAEB3MxUUzZDXuYAoYiKNaLNvPAh80mt6i8'
GROQ_API_KEY = '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'
ADMIN_ID = 8456056018 

# قنوات الاشتراك الإجباري
FORCE_CHANNELS = ["@Eror_7", "@lb2_c"]

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

DB_FILE = "user_channels.json"
STATS_FILE = "stats.json"

# متغيرات لحفظ الحالة مؤقتاً
audio_edit_state = {} 
pending_audio_merge = {} 

def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

user_channels = load_json(DB_FILE)
stats = load_json(STATS_FILE)
if "published_count" not in stats:
    stats["published_count"] = 0

def get_default_settings():
    return {
        "status": "ON",             
        "text_only_mode": False,    
        "category": "فلسفي",        
        "language": "عربي",         
        "add_hashtags": True,
        "hashtags": "#RedWorld #عالم_الأحمر"
    }

user_settings = {} 
generated_texts = {}
pending_posts = {}
media_groups = {} 
saved_images = {} 

# ================= دالة فحص الاشتراك الإجباري =================
def check_subscription(user_id):
    for channel in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

def send_force_sub_message(chat_id):
    text = (
        "<b>⟨ بوابة عالم الأحمر ⟩</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<blockquote>"
        "أهلاً بك. للوصول إلى نظام إدارة القناة، يجب عليك الانضمام إلى قنواتنا أولاً.\n\n"
        "🔴 <b>القناة الأولى:</b> @Eror_7\n"
        "🔴 <b>القناة الثانية:</b> @lb2_c"
        "</blockquote>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<i>بعد الاشتراك في القناتين، اضغط على زر (تحقق من الاشتراك).</i>"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("اشترك في القناة الأولى (@Eror_7)", url="https://t.me/Eror_7"))
    markup.add(InlineKeyboardButton("اشترك في القناة الثانية (@lb2_c)", url="https://t.me/lb2_c"))
    markup.add(InlineKeyboardButton("تحقق من الاشتراك ✅", callback_data="check_sub"))
    
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

# ================= 1. الترحيب =================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID and not check_subscription(user_id):
        return send_force_sub_message(message.chat.id)

    if user_id not in user_settings:
        user_settings[user_id] = get_default_settings()

    welcome_text = (
        f"<b>⟨ مرحباً بك في R W | Bot ⟩</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"هذا البوت مخصص لإدارة قنوات تيليجرام باحترافية.\n\n"
        f"<b>الخطوات:</b>\n"
        f"1. أضف البوت إلى قناتك (كـ مشرف).\n"
        f"2. ارجع هنا واضغط على زر (التحقق من الرفع).\n"
        f"3. ابدأ بإرسال الصور أو النصوص."
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("1. إضافة البوت لقناتك (مشرف)", url=f"https://t.me/{bot.get_me().username}?startchannel=true"))
    markup.add(InlineKeyboardButton("2. التحقق من الرفع (فحص تلقائي)", callback_data="verify_channel"))
    markup.add(InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='HTML')

# ================= 2. زر التحقق من الاشتراك =================
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    user_id = call.from_user.id
    
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح! أهلاً بك.", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك في جميع القنوات بعد. يرجى الاشتراك ثم المحاولة.", show_alert=True)

# ================= 3. التحقق المزدوج =================
@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    bot.answer_callback_query(call.id, "جاري الفحص...")
    user_id = call.from_user.id
    channel_id = user_channels.get(str(user_id))
    
    if not channel_id:
        msg = bot.send_message(call.message.chat.id, "⚠️ لم نتمكن من العثور على القناة تلقائياً.\n\nيرجى إرسال معرف القناة (مثال: @Eror_7):")
        bot.register_next_step_handler(msg, manual_verify, user_id)
        return

    perform_verification(call.message.chat.id, user_id, channel_id)

def manual_verify(message, user_id):
    channel_input = message.text.strip()
    if not channel_input.startswith('@'):
        channel_input = '@' + channel_input
    
    user_channels[str(user_id)] = channel_input
    save_json(DB_FILE, user_channels)
    
    perform_verification(message.chat.id, user_id, channel_input)

def perform_verification(chat_id, user_id, channel_id):
    msg_loading = bot.send_message(chat_id, "⏳ جاري فحص القناة والصلاحيات...")
    try:
        chat_info = bot.get_chat(channel_id)
        bot_member = bot.get_chat_member(channel_id, bot.get_me().id)
        
        if bot_member.status in ['administrator', 'creator'] and bot_member.can_post_messages:
            success_text = (
                f"<b>⟨ نتيجة الفحص ⟩</b>\n"
                f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
                f"<blockquote><b>الحالة:</b> ✅ ناجح\n"
                f"<b>القناة:</b> {chat_info.title}\n"
                f"<b>الصلاحيات:</b> مشرف + يملك صلاحية النشر.</blockquote>\n\n"
                f"<i>تم التحقق بنجاح. يمكنك الآن استخدام البوت.</i>"
            )
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))
            bot.edit_message_text(success_text, chat_id=chat_id, message_id=msg_loading.message_id, reply_markup=markup, parse_mode='HTML')
        else:
            bot.edit_message_text("❌ البوت موجود في القناة، لكنه لا يملك صلاحية 'نشر الرسائل'. يرجى تعديل صلاحيات البوت في القناة والمحاولة مرة أخرى.", chat_id=chat_id, message_id=msg_loading.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ: {e}\nتأكد من أن البوت مشرف في القناة ومن صحة المعرف.", chat_id=chat_id, message_id=msg_loading.message_id)

# ================= 4. حفظ القناة تلقائياً =================
@bot.message_handler(content_types=['new_chat_members'])
def bot_added_to_channel(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            adder_id = message.from_user.id
            channel_identifier = f"@{message.chat.username}" if message.chat.username else str(message.chat.id)
            
            user_channels[str(adder_id)] = channel_identifier
            save_json(DB_FILE, user_channels)
            
            text = (
                f"✅ <b>تمت إضافة البوت إلى القناة:</b> {message.chat.title}\n\n"
                f"يرجى العودة للبوت والضغط على (التحقق من الرفع) لفتح لوحة التحكم."
            )
            try: bot.send_message(adder_id, text, parse_mode='HTML')
            except: pass

# ================= 5. لوحة التحكم =================
def get_main_panel(user_id):
    settings = user_settings.get(user_id, get_default_settings())
    markup = InlineKeyboardMarkup(row_width=2)
    status_txt = "تعطيل النشر" if settings["status"] == "ON" else "تفعيل النشر"
    text_mode_txt = "تعطيل النشر النصي" if settings["text_only_mode"] else "تفعيل النشر النصي"
    
    markup.add(
        InlineKeyboardButton(status_txt, callback_data="toggle_status"),
        InlineKeyboardButton(text_mode_txt, callback_data="toggle_text_mode")
    )
    markup.add(
        InlineKeyboardButton("فئات العبارات", callback_data="menu_categories"),
        InlineKeyboardButton(f"اللغة: {settings['language']}", callback_data="menu_lang")
    )
    markup.add(
        InlineKeyboardButton("عبارات طويلة", callback_data="generate_long_text"),
        InlineKeyboardButton("عبارات مختصرة", callback_data="generate_short_text")
    )
    markup.add(
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit"),
        InlineKeyboardButton("التقرير الأسبوعي", callback_data="show_stats")
    )
    markup.add(
        InlineKeyboardButton("السورس", callback_data="show_source")
    )
    markup.add(InlineKeyboardButton("مغادرة القناة (إلغاء الارتباط)", callback_data="leave_channel"))
    return markup

# ================= 6. نظام حقوق النشر الصوتي (المنفصل) =================
@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    audio_edit_state[user_id] = {'step': 'waiting_for_cover'}
    
    bot.edit_message_text(
        "<b>⟨ حقوق النشر الصوتي ⟩</b>\n\n"
        "الخطوة 1: أرسل الصورة التي تريدها كغلاف للملف الصوتي (Cover):",
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id,
        parse_mode='HTML'
    )

# ================= 7. دمج الصورة مع الصوت (النظام الجديد) =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("add_audio_to_post_"))
def add_audio_to_post(call):
    post_id = call.data.split("_")[4]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية", show_alert=True)
    
    user_id = call.from_user.id
    pending_audio_merge[user_id] = {
        'post_id': post_id,
        'photo_id': pending_posts[post_id]['file_id'],
        'caption': pending_posts[post_id]['caption'],
        'channel': pending_posts[post_id]['channel']
    }
    
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        "<b>⟨ إضافة ملف صوتي ⟩</b>\n\n"
        "أرسل ملف الصوت (MP3) الآن، وسأقوم بتعيين الصورة كغلاف له وتغيير حقوقه:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode='HTML'
    )

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio_merge(message):
    user_id = message.from_user.id
    
    # حالة 1: تعديل صوتي منفصل
    if user_id in audio_edit_state and audio_edit_state[user_id]['step'] == 'waiting_for_audio':
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg': file_id = message.document.file_id
        
        if not file_id: return bot.reply_to(message, "❌ يرجى إرسال ملف بصيغة MP3.")
        
        msg_loading = bot.send_message(message.chat.id, "⏳ جاري معالجة الملف وإضافة الحقوق...")
        try:
            file_info = bot.get_file(file_id)
            audio_data = bot.download_file(file_info.file_path)
            audio_buffer = io.BytesIO(audio_data)
            audio = MP3(audio_buffer, ID3=ID3)
            try: audio.add_tags()
            except ID3Error: pass

            audio.tags.add(TIT2(encoding=3, text="Red world | عالم الأحمر"))
            audio.tags.add(TPE1(encoding=3, text="@Eror_7"))
            
            cover_data = audio_edit_state[user_id]['cover_data']
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=cover_data))
            
            audio.save(audio_buffer)
            audio_buffer.seek(0)
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{user_id}"))
            
            audio_edit_state[user_id]['audio_buffer'] = audio_buffer
            
            bot.delete_message(message.chat.id, msg_loading.message_id)
            bot.send_audio(
                message.chat.id, 
                audio_buffer, 
                title="Red world | عالم الأحمر", 
                performer="@Eror_7", 
                reply_markup=markup
            )
        except Exception as e:
            bot.delete_message(message.chat.id, msg_loading.message_id)
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
        return

    # حالة 2: دمج الصورة مع الصوت في منشور واحد
    if user_id in pending_audio_merge:
        data = pending_audio_merge[user_id]
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg': file_id = message.document.file_id
        
        if not file_id: return bot.reply_to(message, "❌ يرجى إرسال ملف بصيغة MP3.")
        
        msg_loading = bot.send_message(message.chat.id, "⏳ جاري معالجة الملف ودمجه مع الصورة...")
        try:
            file_info = bot.get_file(file_id)
            audio_data = bot.download_file(file_info.file_path)
            
            photo_file_info = bot.get_file(data['photo_id'])
            photo_data = bot.download_file(photo_file_info.file_path)
            
            audio_buffer = io.BytesIO(audio_data)
            audio = MP3(audio_buffer, ID3=ID3)
            try: audio.add_tags()
            except ID3Error: pass

            audio.tags.add(TIT2(encoding=3, text="Red world | عالم الأحمر"))
            audio.tags.add(TPE1(encoding=3, text="@Eror_7"))
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=photo_data))
            
            audio.save(audio_buffer)
            audio_buffer.seek(0)

            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("نشر في القناة", callback_data=f"publish_audio_{user_id}"),
                InlineKeyboardButton("إلغاء", callback_data=f"cancel_audio_{user_id}")
            )
            
            pending_audio_merge[user_id]['audio_buffer'] = audio_buffer
            
            bot.delete_message(message.chat.id, msg_loading.message_id)
            bot.send_audio(
                message.chat.id, 
                audio_buffer, 
                title="Red world | عالم الأحمر", 
                performer="@Eror_7",
                caption=data['caption'],
                parse_mode='HTML',
                reply_markup=markup
            )
            
        except Exception as e:
            bot.delete_message(message.chat.id, msg_loading.message_id)
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
        return

# ================= 8. نشر/إلغاء الصوت =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_standalone_audio_"))
def publish_standalone_audio(call):
    user_id = int(call.data.split("_")[3])
    if user_id not in audio_edit_state or 'audio_buffer' not in audio_edit_state[user_id]:
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.", show_alert=True)
    
    data = audio_edit_state[user_id]
    target_channel = user_channels.get(str(user_id))
    
    if not target_channel:
        return bot.answer_callback_query(call.id, "⚠️ القناة غير مرتبطة. يرجى التحقق من الرفع.", show_alert=True)
    
    audio_buffer = data['audio_buffer']
    audio_buffer.seek(0)
    
    try:
        bot.send_audio(
            target_channel, 
            audio_buffer, 
            title="Red world | عالم الأحمر", 
            performer="@Eror_7"
        )
        stats["published_count"] += 1
        save_json(STATS_FILE, stats)
        
        bot.answer_callback_query(call.id, "✅ تم النشر في القناة بنجاح!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        del audio_edit_state[user_id]
        
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(user_id), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_audio_"))
def publish_audio(call):
    user_id = int(call.data.split("_")[2])
    if user_id not in pending_audio_merge: return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    
    data = pending_audio_merge[user_id]
    audio_buffer = data['audio_buffer']
    audio_buffer.seek(0)
    
    try:
        bot.send_audio(
            data['channel'], 
            audio_buffer, 
            title="Red world | عالم الأحمر", 
            performer="@Eror_7",
            caption=data['caption'],
            parse_mode='HTML'
        )
        stats["published_count"] += 1
        save_json(STATS_FILE, stats)
        
        bot.answer_callback_query(call.id, "✅ تم النشر بنجاح!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        del pending_audio_merge[user_id]
        
        if data['post_id'] in pending_posts: del pending_posts[data['post_id']]
        
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(user_id), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_audio_"))
def cancel_audio(call):
    user_id = int(call.data.split("_")[2])
    if user_id in pending_audio_merge:
        del pending_audio_merge[user_id]
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "تم الإلغاء.")

# ================= 9. التقرير الأسبوعي =================
@bot.callback_query_handler(func=lambda call: call.data == "show_stats")
def show_stats(call):
    channel_id = user_channels.get(str(call.from_user.id))
    if not channel_id: return bot.answer_callback_query(call.id, "⚠️ القناة غير مرتبطة.", show_alert=True)
    
    try:
        chat_info = bot.get_chat(channel_id)
        members_count = bot.get_chat_member_count(channel_id)
        
        stats_text = (
            f"<b>⟨ التقرير الأسبوعي ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote>"
            f"<b>القناة:</b> {chat_info.title}\n"
            f"<b>عدد المشتركين:</b> {members_count}\n"
            f"<b>المنشورات المنشورة عبر البوت:</b> {stats['published_count']}\n"
            f"</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>"
        )
        bot.edit_message_text(stats_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("رجوع للقائمة", callback_data="main_menu")), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ في جلب الإحصائيات: {e}", show_alert=True)
    return bot.answer_callback_query(call.id)

# ================= 10. القفل الأمني والأزرار =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if user_id != ADMIN_ID and str(user_id) not in user_channels:
        if call.data not in ["verify_channel", "main_menu", "check_sub"]:
            return bot.answer_callback_query(call.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت في قناتك أولاً لتتمكن من استخدام الأزرار.", show_alert=True)

    settings = user_settings.get(user_id, get_default_settings())

    if call.data.startswith("regen_image_"):
        post_id = call.data.split("_")[2]
        if post_id not in saved_images: return bot.answer_callback_query(call.id, "انتهت الصلاحية", show_alert=True)
        
        data = saved_images[post_id]
        photo_id = data['photo_id']
        settings = data['settings']
        target_channel = data['channel']
        
        bot.answer_callback_query(call.id, "جاري توليد عبارة جديدة...", show_alert=False)
        msg_loading = bot.send_message(call.message.chat.id, "⏳ جاري إعادة التحليل...")
        
        try:
            file_info = bot.get_file(photo_id)
            downloaded_file = bot.download_file(file_info.file_path)
            base64_image = base64.b64encode(downloaded_file).decode('utf-8')
            
            if settings['language'] == "مختلط":
                lang_prompt = (
                    "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). "
                    "ثم اكتب ترجمتها الإنجليزية في سطر واحد فقط تحت العربية. "
                    "لا تزد عن سطرين في المجموع. بدون إيموجي."
                )
            else:
                lang_prompt = f"باللغة {settings['language']}"
                
            prompt = f"اكتب تعليقاً قصيراً جداً (سطر واحد فقط) بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
            
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                model="qwen/qwen3.8-27b",
                max_tokens=500
            )
            ai_text = chat_completion.choices[0].message.content.strip()
            final_caption = f"<b>{ai_text}</b>"
            if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"
            
            new_post_id = str(int(time.time()))
            pending_posts[new_post_id] = {'type': 'photo', 'file_id': photo_id, 'caption': final_caption, 'channel': target_channel}
            saved_images[new_post_id] = data 
            
            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{new_post_id}"), 
                InlineKeyboardButton("جدولة", callback_data=f"schedule_{new_post_id}"), 
                InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_image_{new_post_id}"),
                InlineKeyboardButton("إضافة ملف صوتي", callback_data=f"add_audio_to_post_{new_post_id}"),
                InlineKeyboardButton("إلغاء", callback_data=f"cancel_{new_post_id}")
            )
            
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.delete_message(call.message.chat.id, msg_loading.message_id)
            bot.send_photo(call.message.chat.id, photo=photo_id, caption=f"<b>معاينة جديدة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
            
        except Exception as e:
            bot.delete_message(call.message.chat.id, msg_loading.message_id)
            bot.send_message(call.message.chat.id, f"خطأ: {e}")
        return

    if call.data == "main_menu":
        main_text = "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:"
        if call.message.content_type == 'photo':
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            bot.send_message(call.message.chat.id, main_text, reply_markup=get_main_panel(user_id), parse_mode='HTML')
        else:
            bot.edit_message_text(main_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id), parse_mode='HTML')
        return bot.answer_callback_query(call.id)

    elif call.data == "leave_channel":
        if str(user_id) in user_channels:
            del user_channels[str(user_id)]
            save_json(DB_FILE, user_channels)
            bot.answer_callback_query(call.id, text="✅ تم إلغاء ارتباط القناة.", show_alert=True)
            send_welcome(call.message)
        else:
            bot.answer_callback_query(call.id, "⚠️ لا توجد قناة مرتبطة.", show_alert=True)
        return

    elif call.data == "toggle_status":
        settings["status"] = "OFF" if settings["status"] == "ON" else "ON"
        user_settings[user_id] = settings
        bot.edit_message_text("‎", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id))
        return bot.answer_callback_query(call.id, text=f"حالة النشر: {'مفعل' if settings['status'] == 'ON' else 'معطل'}", show_alert=False)

    elif call.data == "toggle_text_mode":
        settings["text_only_mode"] = not settings["text_only_mode"]
        user_settings[user_id] = settings
        bot.edit_message_text("‎", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id))
        return bot.answer_callback_query(call.id, text=f"النشر النصي: {'مفعل' if settings['text_only_mode'] else 'معطل'}", show_alert=False)

    elif call.data == "menu_lang":
        bot.edit_message_text("<b>إعدادات اللغة:</b>\n\nاختر اللغة التي تريدها:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_lang_panel(), parse_mode='HTML')
        return bot.answer_callback_query(call.id)

    elif call.data.startswith("lang_"):
        settings["language"] = call.data.replace("lang_", "")
        user_settings[user_id] = settings
        bot.edit_message_text("<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id), parse_mode='HTML')
        return bot.answer_callback_query(call.id, text=f"تم اختيار اللغة: {settings['language']}", show_alert=False)

    elif call.data == "menu_categories":
        bot.edit_message_text("<b>فئات العبارات:</b>\n\nاختر الفئة التي تناسب جو القناة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_categories_panel(), parse_mode='HTML')
        return bot.answer_callback_query(call.id)

    elif call.data.startswith("cat_"):
        settings["category"] = call.data.replace("cat_", "")
        user_settings[user_id] = settings
        bot.edit_message_text("<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id), parse_mode='HTML')
        return bot.answer_callback_query(call.id, text=f"تم اختيار الفئة: {settings['category']}", show_alert=False)

    elif call.data == "show_source":
        try:
            dev_info = bot.get_chat(ADMIN_ID)
            dev_name = dev_info.first_name
        except:
            dev_name = "المطور"

        source_text = (
            f"<b>⟨ RED WORLD | عالم الأحمر ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote><b>المطور:</b> {dev_name}\n<b>البوت:</b> @{bot.get_me().username}</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<i>مساحة لمشاركة الخواطر، اللحظات الجميلة، وتأملات الحياة.</i>"
        )
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton(f"المطور: {dev_name}", url=f"tg://user?id={ADMIN_ID}"), 
            InlineKeyboardButton("رجوع للقائمة", callback_data="main_menu")
        )
        bot.edit_message_text(source_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
        return bot.answer_callback_query(call.id)

    elif call.data.startswith('fmt_'):
        parts = call.data.split('_')
        action, msg_id = parts[1], parts[2]
        if msg_id not in generated_texts: return
        data = generated_texts[msg_id]

        if action == "cancel":
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            bot.answer_callback_query(call.id, text="تم إلغاء العبارة", show_alert=False)
            bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(user_id), parse_mode='HTML')
            return

        elif action == "publish":
            final_text = apply_formatting(data)
            if settings["add_hashtags"]: final_text += f"\n\n{settings['hashtags']}"
            post_id = str(int(time.time()))
            
            target_channel = user_channels.get(str(user_id))
            if not target_channel:
                return bot.answer_callback_query(call.id, "⚠️ يرجى التحقق من رفع البوت في قناتك أولاً.", show_alert=True)
            
            pending_posts[post_id] = {'type': 'text', 'caption': final_text, 'channel': target_channel}
            
            markup = InlineKeyboardMarkup(row_width=3)
            markup.add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
            
            bot.edit_message_text(f"<b>معاينة قبل النشر:</b>\n\n{final_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
            return bot.answer_callback_query(call.id, text="جاهز للنشر", show_alert=False)

        else:
            if action == "bold": data["bold"] = not data["bold"]
            elif action == "italic": data["italic"] = not data["italic"]
            elif action == "strike": data["strike"] = not data["strike"]
            elif action == "quote": data["quote"] = not data["quote"]
            new_text = apply_formatting(data)
            markup = get_formatting_panel_markup(data, msg_id)
            bot.edit_message_text(f"معاينة النص:\n\n{new_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
            return bot.answer_callback_query(call.id, text="تم التحديث", show_alert=False)

    elif call.data.startswith("confirm_"):
        post_id = call.data.split("_")[1]
        if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية")
        data = pending_posts[post_id]
        try:
            target_channel = data['channel']
            if data['type'] == 'photo': 
                bot.send_photo(target_channel, data['file_id'], caption=data['caption'], parse_mode='HTML')
            else: 
                bot.send_message(target_channel, data['caption'], parse_mode='HTML')
            
            stats["published_count"] += 1
            save_json(STATS_FILE, stats)
            
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            
            bot.answer_callback_query(call.id, text="تم النشر في القناة", show_alert=False)
            bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(user_id), parse_mode='HTML')
            del pending_posts[post_id]
        except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}")

    elif call.data.startswith("schedule_"):
        post_id = call.data.split("_")[1]
        msg = bot.send_message(call.message.chat.id, "⏳ أرسل عدد الدقائق للتأجيل (مثال: 30):")
        bot.register_next_step_handler(msg, process_schedule_time, post_id)

    elif call.data.startswith("cancel_"):
        post_id = call.data.split("_")[1]
        if post_id in pending_posts: del pending_posts[post_id]
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.answer_callback_query(call.id, text="تم إلغاء المنشور", show_alert=False)
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(user_id), parse_mode='HTML')

# ================= 11. استقبال الصور (مع نظام الألبوم) =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    if user_id in audio_edit_state and audio_edit_state[user_id]['step'] == 'waiting_for_cover':
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        audio_edit_state[user_id]['cover_data'] = downloaded_file
        audio_edit_state[user_id]['step'] = 'waiting_for_audio'
        bot.send_message(message.chat.id, "<b>الخطوة 2:</b> الآن أرسل ملف الصوت (MP3) الذي تريد تعديل حقوقه:", parse_mode='HTML')
        return

    if user_id != ADMIN_ID and str(user_id) not in user_channels:
        return bot.send_message(message.chat.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت في قناتك أولاً لتتمكن من إرسال الصور.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel")))

    settings = user_settings.get(user_id, get_default_settings())
    target_channel = user_channels.get(str(user_id))

    if settings["status"] == "OFF": return bot.send_message(message.chat.id, "معطل.", reply_markup=get_main_panel(user_id))

    if message.media_group_id:
        if message.media_group_id not in media_groups:
            media_groups[message.media_group_id] = {
                'photos': [],
                'user_id': user_id,
                'channel': target_channel,
                'settings': settings
            }
        media_groups[message.media_group_id]['photos'].append(message.photo[-1].file_id)
        threading.Timer(2.0, process_album, args=[message.media_group_id, message.chat.id]).start()
        return

    process_single_photo(message, settings, target_channel)

def process_album(group_id, chat_id):
    if group_id not in media_groups: return
    data = media_groups[group_id]
    del media_groups[group_id] 
    
    photos = data['photos']
    user_id = data['user_id']
    target_channel = data['channel']
    settings = data['settings']
    
    msg_loading = bot.send_message(chat_id, "جاري تحليل الألبوم...")
    
    try:
        file_info = bot.get_file(photos[0])
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        if settings['language'] == "مختلط":
            lang_prompt = (
                "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). "
                "ثم اكتب ترجمتها الإنجليزية في سطر واحد فقط تحت العربية. "
                "لا تزد عن سطرين في المجموع. بدون إيموجي."
            )
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب تعليقاً قصيراً جداً (سطر واحد فقط) بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="qwen/qwen3.8-27b",
            max_tokens=500
        )
        ai_text = chat_completion.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"
        
        post_id = str(int(time.time()))
        
        media = []
        for i, photo_id in enumerate(photos):
            if i == 0:
                media.append(telebot.types.InputMediaPhoto(photo_id, caption=final_caption, parse_mode='HTML'))
            else:
                media.append(telebot.types.InputMediaPhoto(photo_id))
                
        pending_posts[post_id] = {'type': 'album', 'media': media, 'channel': target_channel}
        
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
        )
        
        bot.delete_message(chat_id, msg_loading.message_id)
        bot.send_media_group(chat_id, media) 
        bot.send_message(chat_id, "هل تريد نشر هذا الألبوم؟", reply_markup=markup)
        
    except Exception as e:
        bot.delete_message(chat_id, msg_loading.message_id)
        bot.send_message(chat_id, f"خطأ في تحليل الألبوم: {e}")

def process_single_photo(message, settings, target_channel):
    msg_loading = bot.send_message(message.chat.id, "جاري التحليل...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        if settings['language'] == "مختلط":
            lang_prompt = (
                "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). "
                "ثم اكتب ترجمتها الإنجليزية في سطر واحد فقط تحت العربية. "
                "لا تزد عن سطرين في المجموع. بدون إيموجي."
            )
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب تعليقاً قصيراً جداً (سطر واحد فقط) بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="qwen/qwen3.8-27b",
            max_tokens=500
        )
        ai_text = chat_completion.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"

        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'photo', 'file_id': message.photo[-1].file_id, 'caption': final_caption, 'channel': target_channel}
        saved_images[post_id] = {
            'photo_id': message.photo[-1].file_id,
            'user_id': message.from_user.id,
            'settings': settings,
            'channel': target_channel
        }
        
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
            InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_image_{post_id}"),
            InlineKeyboardButton("إضافة ملف صوتي", callback_data=f"add_audio_to_post_{post_id}"),
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
        )
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_message(message.chat.id, f"خطأ: {e}", reply_markup=get_main_panel(message.from_user.id))

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, get_default_settings())
    
    if message.text.startswith('/'): return
    
    if user_id != ADMIN_ID and str(user_id) not in user_channels:
        return bot.send_message(message.chat.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت في قناتك أولاً.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel")))
    
    if settings["text_only_mode"] and settings["status"] == "ON":
        target_channel = user_channels.get(str(user_id))
            
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        
        if settings['language'] == "مختلط":
            lang_prompt = (
                "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). "
                "ثم اكتب ترجمتها الإنجليزية في سطر واحد فقط تحت العربية. "
                "لا تزد عن سطرين في المجموع. بدون إيموجي."
            )
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب عبارة قصيرة جداً (سطر واحد فقط) بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}], 
                model="qwen/qwen3.8-27b",
                max_tokens=500
            )
            ai_text = chat_completion.choices[0].message.content.strip()
            final_caption = f"<b>{ai_text}</b>"
            if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"
            
            post_id = str(int(time.time()))
            pending_posts[post_id] = {'type': 'text', 'caption': final_caption, 'channel': target_channel}
            markup = InlineKeyboardMarkup(row_width=3).add(
                InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
                InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
                InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
            )
            bot.send_message(message.chat.id, f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ: {e}")

# ================= 12. لوحات مساعدة =================
def get_lang_panel():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(InlineKeyboardButton("عربي", callback_data="lang_عربي"), InlineKeyboardButton("إنجليزي", callback_data="lang_إنجليزي"), InlineKeyboardButton("مختلط", callback_data="lang_مختلط"))
    markup.add(InlineKeyboardButton("رجوع للقائمة", callback_data="main_menu"))
    return markup

def get_categories_panel():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("حزين", callback_data="cat_حزين"), InlineKeyboardButton("تفاؤل", callback_data="cat_تفاؤل"))
    markup.add(InlineKeyboardButton("فلسفي", callback_data="cat_فلسفي"), InlineKeyboardButton("غامض", callback_data="cat_غامض"))
    markup.add(InlineKeyboardButton("رجوع للقائمة", callback_data="main_menu"))
    return markup

def get_formatting_panel_markup(data, msg_id):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}"),
        InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}"),
        InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}")
    )
    markup.add(InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}"))
    markup.add(InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}"), InlineKeyboardButton("إلغاء وحذف", callback_data=f"fmt_cancel_{msg_id}"))
    return markup

def send_formatting_panel(chat_id, msg_id):
    data = generated_texts[msg_id]
    text = apply_formatting(data)
    markup = get_formatting_panel_markup(data, msg_id)
    bot.send_message(chat_id, f"معاينة النص:\n\n{text}", reply_markup=markup, parse_mode='HTML')

def apply_formatting(data):
    text = data["raw"]
    if data["strike"]: text = f"<s>{text}</s>"
    if data["italic"]: text = f"<i>{text}</i>"
    if data["bold"]: text = f"<b>{text}</b>"
    if data["quote"]: text = f"<blockquote>{text}</blockquote>"
    return text

def schedule_post(post_id, delay_minutes):
    time.sleep(delay_minutes * 60)
    if post_id in pending_posts:
        data = pending_posts[post_id]
        try:
            target_channel = data['channel']
            if data['type'] == 'photo': bot.send_photo(target_channel, data['file_id'], caption=data['caption'], parse_mode='HTML')
            elif data['type'] == 'album': bot.send_media_group(target_channel, data['media'])
            else: bot.send_message(target_channel, data['caption'], parse_mode='HTML')
            
            stats["published_count"] += 1
            save_json(STATS_FILE, stats)
            
            del pending_posts[post_id]
        except Exception as e: print(f"فشل النشر المجدول: {e}")

def process_schedule_time(message, post_id):
    try:
        minutes = int(message.text)
        if post_id in pending_posts:
            bot.reply_to(message, f"✅ تم الجدولة بعد {minutes} دقيقة.")
            threading.Thread(target=schedule_post, args=(post_id, minutes), daemon=True).start()
    except: bot.reply_to(message, "❌ أرسل رقماً صحيحاً.")

print("البوت العام يعمل...")
bot.infinity_polling()
