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
from PIL import Image, ImageFilter

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAEB3MxUUzZDXuYAoYiKNaLNvPAh80mt6i8'
GROQ_API_KEY = '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'
ADMIN_ID = 8456056018 

# قنوات الاشتراك الإجباري
FORCE_CHANNELS = ["@Eror_7", "@lb2_c"]
CHANNEL_NAME = "عالم الأحمر | Red world"
CHANNEL_LINK = "https://t.me/Eror_7"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

DB_FILE = "user_channels.json"
STATS_FILE = "stats.json"

# متغيرات لحفظ الحالة مؤقتاً
audio_edit_state = {} 
pending_audio_merge = {} 
ad_builder_state = {} 

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

# ================= دوال مساعدة =================
def convert_to_jpg(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((200, 200)) 
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=75)
        return output.getvalue()
    except Exception as e:
        print(f"Error converting image: {e}")
        return image_bytes

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
    except Exception as e:
        print(f"Error rebuilding audio: {e}")
        return original_audio_bytes, cover_bytes

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
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
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
        InlineKeyboardButton("إنشاء إعلان ترويجي", callback_data="start_ad_builder"),
        InlineKeyboardButton("حقوق النشر الصوتي", callback_data="start_audio_edit")
    )
    markup.add(
        InlineKeyboardButton("التقرير الأسبوعي", callback_data="show_stats"),
        InlineKeyboardButton("السورس", callback_data="show_source")
    )
    markup.add(InlineKeyboardButton("مغادرة القناة", callback_data="leave_channel"))
    return markup

# ================= 6. الفئات واللغة =================
@bot.callback_query_handler(func=lambda call: call.data == "menu_lang")
def menu_lang(call):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("عربي", callback_data="lang_عربي"),
        InlineKeyboardButton("إنجليزي", callback_data="lang_إنجليزي"),
        InlineKeyboardButton("مختلط", callback_data="lang_مختلط")
    )
    markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    bot.edit_message_text("<b>اختر اللغة:</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def set_lang(call):
    user_id = call.from_user.id
    settings = user_settings.get(user_id, get_default_settings())
    settings["language"] = call.data.replace("lang_", "")
    user_settings[user_id] = settings
    bot.edit_message_text("<b>تم تحديث اللغة.</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id), parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "menu_categories")
def menu_categories(call):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("حزين", callback_data="cat_حزين"),
        InlineKeyboardButton("تفاؤل", callback_data="cat_تفاؤل")
    )
    markup.add(
        InlineKeyboardButton("فلسفي", callback_data="cat_فلسفي"),
        InlineKeyboardButton("غامض", callback_data="cat_غامض")
    )
    markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    bot.edit_message_text("<b>اختر الفئة:</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def set_cat(call):
    user_id = call.from_user.id
    settings = user_settings.get(user_id, get_default_settings())
    settings["category"] = call.data.replace("cat_", "")
    user_settings[user_id] = settings
    bot.edit_message_text("<b>تم تحديث الفئة.</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id), parse_mode='HTML')
    bot.answer_callback_query(call.id)

# ================= 7. توليد العبارات =================
@bot.callback_query_handler(func=lambda call: call.data in ["generate_long_text", "generate_short_text"])
def generate_text(call):
    user_id = call.from_user.id
    settings = user_settings.get(user_id, get_default_settings())
    bot.answer_callback_query(call.id, "جاري التوليد...")
    
    if settings['language'] == "مختلط":
        lang_prompt = (
            "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). "
            "ثم اكتب ترجمتها الإنجليزية في سطر واحد فقط تحت العربية. "
            "لا تزد عن سطرين في المجموع. بدون إيموجي."
        )
    else:
        lang_prompt = f"باللغة {settings['language']}"

    if call.data == "generate_long_text":
        prompt = f"اكتب عبارة مفصلة (من 3 إلى 4 أسطر) بأسلوب {settings['category']} {lang_prompt} تناسب قناة اسمها {bot.get_me().first_name}. بدون إيموجي."
    else:
        prompt = f"اكتب عبارة قصيرة جداً (سطر واحد فقط) بأسلوب {settings['category']} {lang_prompt} تناسب قناة اسمها {bot.get_me().first_name}. بدون إيموجي."

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model="qwen/qwen3.8-27b",
            max_tokens=500
        )
        raw_text = chat_completion.choices[0].message.content.strip()
        msg_id = str(int(time.time()))
        generated_texts[msg_id] = {"raw": raw_text, "bold": False, "italic": False, "strike": False, "quote": False, "user_id": user_id}
        send_formatting_panel(call.message.chat.id, msg_id)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
    except Exception as e:
        bot.send_message(call.message.chat.id, f"خطأ: {e}")

def send_formatting_panel(chat_id, msg_id):
    data = generated_texts[msg_id]
    text = apply_formatting(data)
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}"),
        InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}"),
        InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}")
    )
    markup.add(InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}"))
    markup.add(InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}"), InlineKeyboardButton("إلغاء", callback_data=f"fmt_cancel_{msg_id}"))
    bot.send_message(chat_id, f"معاينة النص:\n\n{text}", reply_markup=markup, parse_mode='HTML')

def apply_formatting(data):
    text = data["raw"]
    if data["strike"]: text = f"<s>{text}</s>"
    if data["italic"]: text = f"<i>{text}</i>"
    if data["bold"]: text = f"<b>{text}</b>"
    if data["quote"]: text = f"<blockquote>{text}</blockquote>"
    return text

@bot.callback_query_handler(func=lambda call: call.data.startswith('fmt_'))
def formatting_handler(call):
    parts = call.data.split('_')
    action, msg_id = parts[1], parts[2]
    if msg_id not in generated_texts: return
    data = generated_texts[msg_id]

    if action == "cancel":
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.answer_callback_query(call.id, text="تم الإلغاء", show_alert=False)
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
        return

    elif action == "publish":
        final_text = apply_formatting(data)
        target_channel = user_channels.get(str(call.from_user.id))
        if not target_channel:
            return bot.answer_callback_query(call.id, "⚠️ يرجى التحقق من رفع البوت في قناتك أولاً.", show_alert=True)
        
        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'text', 'caption': final_text, 'channel': target_channel}
        
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
        )
        bot.edit_message_text(f"<b>معاينة قبل النشر:</b>\n\n{final_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
        return bot.answer_callback_query(call.id, "جاهز للنشر")

    else:
        if action == "bold": data["bold"] = not data["bold"]
        elif action == "italic": data["italic"] = not data["italic"]
        elif action == "strike": data["strike"] = not data["strike"]
        elif action == "quote": data["quote"] = not data["quote"]
        new_text = apply_formatting(data)
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}"),
            InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}"),
            InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}")
        )
        markup.add(InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}"))
        markup.add(InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}"), InlineKeyboardButton("إلغاء", callback_data=f"fmt_cancel_{msg_id}"))
        bot.edit_message_text(f"معاينة النص:\n\n{new_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
        return bot.answer_callback_query(call.id, "تم التحديث")

# ================= 8. نظام بناء الإعلان =================
@bot.callback_query_handler(func=lambda call: call.data == "start_ad_builder")
def start_ad_builder(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    ad_builder_state[user_id] = {
        'step': 1, 'group_type': None, 'has_channel': None, 'group_link': None,
        'channel_username': None, 'user_id_handle': None, 'custom_text': None,
        'media_type': None, 'media_file_id': None, 'add_blur': False
    }
    
    text = (
        "<b>⟨ بناء إعلان ترويجي ⟩</b>\n"
        "<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        "<b>السؤال 1:</b> ما هو نوع المجموعة التي تريد الترويج لها؟"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Furry", callback_data="ad_type_furry"),
        InlineKeyboardButton("Tumblr", callback_data="ad_type_tumblr"),
        InlineKeyboardButton("Mixed", callback_data="ad_type_mixed")
    )
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("ad_type_"))
def ad_type_selected(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    
    ad_builder_state[user_id]['group_type'] = call.data.replace("ad_type_", "")
    ad_builder_state[user_id]['step'] = 2
    
    text = "<b>⟨ بناء إعلان ترويجي ⟩</b>\n\n<b>السؤال 2:</b> هل لديك قناة مرتبطة بهذه المجموعة؟"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("نعم، لدي قناة", callback_data="ad_has_channel_yes"),
        InlineKeyboardButton("لا، ليس لدي", callback_data="ad_has_channel_no")
    )
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_has_channel_yes")
def ad_has_channel_yes(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['has_channel'] = True
    ad_builder_state[user_id]['step'] = 2.5
    bot.edit_message_text("أرسل الآن **يوزر القناة** المرتبطة بالمجموعة (مثال: @MyChannel):", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_has_channel_no")
def ad_has_channel_no(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['has_channel'] = False
    ad_builder_state[user_id]['step'] = 3
    text = "<b>⟨ بناء إعلان ترويجي ⟩</b>\n\n<b>السؤال 3:</b> أرسل رابط المجموعة التي تريد الترويج لها:"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step3_continue"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in ad_builder_state and ad_builder_state[message.from_user.id]['step'] == 2.5)
def ad_receive_channel_username(message):
    user_id = message.from_user.id
    ad_builder_state[user_id]['channel_username'] = message.text.strip()
    ad_builder_state[user_id]['step'] = 3
    text = "<b>⟨ بناء إعلان ترويجي ⟩</b>\n\n<b>السؤال 3:</b> أرسل رابط المجموعة التي تريد الترويج لها:"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step3_continue"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_step3_continue")
def ad_step3_continue(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['step'] = 4
    text = "<b>⟨ بناء إعلان ترويجي ⟩</b>\n\n<b>السؤال 4:</b> أرسل **معرف حسابك** (مثال: @MyUser):"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step4_continue"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_step4_continue")
def ad_step4_continue(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['step'] = 5
    text = "<b>⟨ بناء إعلان ترويجي ⟩</b>\n\n<b>السؤال 5:</b> أرسل **رسالة ترويجية** قصيرة تصف مجموعتك:"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("متابعة", callback_data="ad_step5_continue"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_step5_continue")
def ad_step5_continue(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['step'] = 6
    text = "<b>⟨ بناء إعلان ترويجي ⟩</b>\n\n<b>السؤال 6:</b> هل تريد إرسال صورة أو فيديو للترويج؟"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("صورة", callback_data="ad_media_photo"), InlineKeyboardButton("فيديو", callback_data="ad_media_video"))
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_media_photo")
def ad_media_photo(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['media_type'] = 'photo'
    ad_builder_state[user_id]['step'] = 6.5
    bot.edit_message_text("أرسل الصورة الآن:", chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_media_video")
def ad_media_video(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['media_type'] = 'video'
    ad_builder_state[user_id]['step'] = 6.5
    bot.edit_message_text("أرسل الفيديو الآن:", chat_id=call.message.chat.id, message_id=call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['photo', 'video'])
def ad_receive_media(message):
    user_id = message.from_user.id
    if user_id not in ad_builder_state or ad_builder_state[user_id]['step'] != 6.5: return
    
    if message.content_type == 'photo':
        ad_builder_state[user_id]['media_file_id'] = message.photo[-1].file_id
    else:
        ad_builder_state[user_id]['media_file_id'] = message.video.file_id
    
    ad_builder_state[user_id]['step'] = 7
    text = "<b>⟨ بناء إعلان ترويجي ⟩</b>\n\n<b>السؤال 7:</b> هل تريد أن أقوم بتغويش (Blur) الصورة/الفيديو؟"
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("نعم، غوش", callback_data="ad_blur_yes"), InlineKeyboardButton("تخطي", callback_data="ad_blur_no"))
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_blur_yes")
def ad_blur_yes(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['add_blur'] = True
    ad_builder_state[user_id]['step'] = 8
    finalize_ad(call.message, user_id)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "ad_blur_no")
def ad_blur_no(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    ad_builder_state[user_id]['add_blur'] = False
    ad_builder_state[user_id]['step'] = 8
    finalize_ad(call.message, user_id)
    bot.answer_callback_query(call.id)

def finalize_ad(message, user_id):
    data = ad_builder_state[user_id]
    
    prompt = f"""
    You are a professional Telegram ad copywriter. 
    Write a short, engaging promotional message based on these details:
    - Group Type: {data['group_type']}
    - Group Link: {data['group_link']}
    - Owner ID: {data['user_id_handle']}
    - User's Custom Text: {data['custom_text']}
    - Channel: {data['channel_username'] if data['channel_username'] else 'None'}
    
    IMPORTANT RULES:
    1. DO NOT use any emojis.
    2. DO NOT use asterisks (**) for bold. Use HTML tags like <b>text</b> if you need bold.
    3. Put the most important sentence (the invitation) inside <blockquote> ... </blockquote> tags.
    4. Keep it professional, elegant, and short.
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="qwen/qwen3.8-27b",
            max_tokens=400
        )
        ad_text = chat_completion.choices[0].message.content.strip()
        ad_text = ad_text.replace("**", "").replace("*", "")
    except:
        ad_text = data['custom_text']
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("تأكيد النشر في القناة", callback_data="ad_publish_final"))
    
    if data['media_file_id']:
        if data['media_type'] == 'photo':
            if data['add_blur']:
                try:
                    file_info = bot.get_file(data['media_file_id'])
                    img_data = bot.download_file(file_info.file_path)
                    img = Image.open(io.BytesIO(img_data))
                    blurred = img.filter(ImageFilter.GaussianBlur(radius=15))
                    output = io.BytesIO()
                    blurred.save(output, format="JPEG")
                    output.seek(0)
                    bot.send_photo(message.chat.id, output, caption=ad_text, reply_markup=markup, parse_mode='HTML')
                except:
                    bot.send_photo(message.chat.id, data['media_file_id'], caption=ad_text, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_photo(message.chat.id, data['media_file_id'], caption=ad_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_video(message.chat.id, data['media_file_id'], caption=ad_text, reply_markup=markup, parse_mode='HTML', has_spoiler=data['add_blur'])
    else:
        bot.send_message(message.chat.id, ad_text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "ad_publish_final")
def ad_publish_final(call):
    user_id = call.from_user.id
    if user_id not in ad_builder_state: return
    
    target_channel = user_channels.get(str(user_id))
    if not target_channel:
        return bot.answer_callback_query(call.id, "⚠️ القناة غير مرتبطة. يرجى التحقق من الرفع.", show_alert=True)
    
    bot.answer_callback_query(call.id, "✅ تم النشر بنجاح.", show_alert=True)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    del ad_builder_state[user_id]
    bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(user_id), parse_mode='HTML')

# ================= 9. حقوق النشر الصوتي =================
@bot.callback_query_handler(func=lambda call: call.data == "start_audio_edit")
def start_audio_edit(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    audio_edit_state[user_id] = {'step': 'waiting_for_cover'}
    bot.edit_message_text("<b>⟨ حقوق النشر الصوتي ⟩</b>\n\nالخطوة 1: أرسل الصورة التي تريدها كغلاف:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(content_types=['audio', 'document'])
def handle_audio_merge(message):
    user_id = message.from_user.id
    
    if user_id in audio_edit_state and audio_edit_state[user_id]['step'] == 'waiting_for_audio':
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg': file_id = message.document.file_id
        
        if not file_id: return bot.reply_to(message, "❌ يرجى إرسال ملف بصيغة MP3.")
        
        msg_loading = bot.send_message(message.chat.id, "⏳ جاري معالجة الملف...")
        try:
            file_info = bot.get_file(file_id)
            audio_data = bot.download_file(file_info.file_path)
            cover_data = audio_edit_state[user_id]['cover_data']
            rebuilt_audio_data, cover_jpg = rebuild_audio_with_cover(audio_data, cover_data)
            
            audio_edit_state[user_id]['original_audio'] = audio_data
            audio_edit_state[user_id]['cover_data'] = cover_data
            audio_buffer = io.BytesIO(rebuilt_audio_data)
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(f"{CHANNEL_NAME}", url=CHANNEL_LINK))
            markup.add(InlineKeyboardButton("نشر في القناة", callback_data=f"publish_standalone_audio_{user_id}"))
            
            try: bot.delete_message(message.chat.id, msg_loading.message_id)
            except: pass
            
            bot.send_audio(message.chat.id, audio_buffer, title="Red world | عالم الأحمر", performer="@Eror_7", thumb=cover_jpg)
            bot.send_message(message.chat.id, f"تم إضافة الحقوق بنجاح.", reply_markup=markup)
        except Exception as e:
            try: bot.delete_message(message.chat.id, msg_loading.message_id)
            except: pass
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
        return

    if user_id in pending_audio_merge:
        data = pending_audio_merge[user_id]
        file_id = None
        if message.content_type == 'audio': file_id = message.audio.file_id
        elif message.content_type == 'document' and message.document.mime_type == 'audio/mpeg': file_id = message.document.file_id
        
        if not file_id: return bot.reply_to(message, "❌ يرجى إرسال ملف بصيغة MP3.")
        
        msg_loading = bot.send_message(message.chat.id, "⏳ جاري معالجة الملف...")
        try:
            file_info = bot.get_file(file_id)
            audio_data = bot.download_file(file_info.file_path)
            photo_file_info = bot.get_file(data['photo_id'])
            photo_data = bot.download_file(photo_file_info.file_path)
            
            rebuilt_audio_data, cover_jpg = rebuild_audio_with_cover(audio_data, photo_data)
            
            pending_audio_merge[user_id]['original_audio'] = audio_data
            pending_audio_merge[user_id]['cover_data'] = photo_data
            audio_buffer = io.BytesIO(rebuilt_audio_data)
            
            markup = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton(f"{CHANNEL_NAME}", url=CHANNEL_LINK),
                InlineKeyboardButton("نشر في القناة", callback_data=f"publish_audio_{user_id}"),
                InlineKeyboardButton("إلغاء", callback_data=f"cancel_audio_{user_id}")
            )
            
            try: bot.delete_message(message.chat.id, msg_loading.message_id)
            except: pass
            
            bot.send_audio(message.chat.id, audio_buffer, title="Red world | عالم الأحمر", performer="@Eror_7", thumb=cover_jpg)
            bot.send_message(message.chat.id, "تم دمج الصورة مع الصوت. اختر الإجراء:", reply_markup=markup)
            
        except Exception as e:
            try: bot.delete_message(message.chat.id, msg_loading.message_id)
            except: pass
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
        return

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_standalone_audio_"))
def publish_standalone_audio(call):
    user_id = int(call.data.split("_")[3])
    if user_id not in audio_edit_state or 'original_audio' not in audio_edit_state[user_id]:
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.", show_alert=True)
    
    data = audio_edit_state[user_id]
    target_channel = user_channels.get(str(user_id))
    
    if not target_channel:
        return bot.answer_callback_query(call.id, "⚠️ القناة غير مرتبطة.", show_alert=True)
    
    try:
        rebuilt_audio_data, cover_jpg = rebuild_audio_with_cover(data['original_audio'], data['cover_data'])
        audio_buffer = io.BytesIO(rebuilt_audio_data)
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(f"{CHANNEL_NAME}", url=CHANNEL_LINK))
        
        bot.send_audio(target_channel, audio_buffer, title="Red world | عالم الأحمر", performer="@Eror_7", thumb=cover_jpg, reply_markup=markup)
        
        stats["published_count"] += 1
        save_json(STATS_FILE, stats)
        
        bot.answer_callback_query(call.id, "✅ تم النشر بنجاح!", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        del audio_edit_state[user_id]
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(user_id), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("publish_audio_"))
def publish_audio(call):
    user_id = int(call.data.split("_")[2])
    if user_id not in pending_audio_merge or 'original_audio' not in pending_audio_merge[user_id]: 
        return bot.answer_callback_query(call.id, "انتهت الصلاحية.")
    
    data = pending_audio_merge[user_id]
    
    try:
        rebuilt_audio_data, cover_jpg = rebuild_audio_with_cover(data['original_audio'], data['cover_data'])
        audio_buffer = io.BytesIO(rebuilt_audio_data)
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(f"{CHANNEL_NAME}", url=CHANNEL_LINK))
        
        bot.send_audio(data['channel'], audio_buffer, title="Red world | عالم الأحمر", performer="@Eror_7", caption=data['caption'], parse_mode='HTML', thumb=cover_jpg, reply_markup=markup)
        
        stats["published_count"] += 1
        save_json(STATS_FILE, stats)
        
        bot.answer_callback_query(call.id, "✅ تم النشر بنجاح!", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        del pending_audio_merge[user_id]
        
        if data['post_id'] in pending_posts: del pending_posts[data['post_id']]
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(user_id), parse_mode='HTML')
    except Exception as e:
        bot.answer_callback_query(call.id, f"خطأ: {e}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_audio_"))
def cancel_audio(call):
    user_id = int(call.data.split("_")[2])
    if user_id in pending_audio_merge:
        del pending_audio_merge[user_id]
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.answer_callback_query(call.id, "تم الإلغاء.")

# ================= 10. استقبال الصور العادية (العبارات) =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    if user_id in audio_edit_state and audio_edit_state[user_id]['step'] == 'waiting_for_cover':
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        audio_edit_state[user_id]['cover_data'] = downloaded_file
        audio_edit_state[user_id]['step'] = 'waiting_for_audio'
        bot.send_message(message.chat.id, "<b>الخطوة 2:</b> أرسل ملف الصوت (MP3):", parse_mode='HTML')
        return

    if user_id in ad_builder_state and ad_builder_state[user_id]['step'] == 6.5:
        return

    if user_id != ADMIN_ID and str(user_id) not in user_channels:
        return bot.send_message(message.chat.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت في قناتك أولاً.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel")))

    settings = user_settings.get(user_id, get_default_settings())
    target_channel = user_channels.get(str(user_id))

    if settings["status"] == "OFF": return bot.send_message(message.chat.id, "معطل.", reply_markup=get_main_panel(user_id))

    if message.media_group_id:
        if message.media_group_id not in media_groups:
            media_groups[message.media_group_id] = {'photos': [], 'user_id': user_id, 'channel': target_channel, 'settings': settings}
        media_groups[message.media_group_id]['photos'].append(message.photo[-1].file_id)
        threading.Timer(2.0, process_album, args=[message.media_group_id, message.chat.id]).start()
        return

    msg_loading = bot.send_message(message.chat.id, "جاري التحليل...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        if settings['language'] == "مختلط":
            lang_prompt = "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). ثم اكتب ترجمتها الإنجليزية في سطر واحد فقط. بدون إيموجي."
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب تعليقاً قصيراً جداً (سطر واحد فقط) بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="qwen/qwen3.8-27b", max_tokens=500
        )
        ai_text = chat_completion.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"

        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'photo', 'file_id': message.photo[-1].file_id, 'caption': final_caption, 'channel': target_channel}
        saved_images[post_id] = {'photo_id': message.photo[-1].file_id, 'user_id': user_id, 'settings': settings, 'channel': target_channel}
        
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
            InlineKeyboardButton("تغيير العبارة", callback_data=f"regen_image_{post_id}"),
            InlineKeyboardButton("إضافة ملف صوتي", callback_data=f"add_audio_to_post_{post_id}"),
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
        )
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        try: bot.delete_message(message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_message(message.chat.id, f"خطأ: {e}", reply_markup=get_main_panel(user_id))

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
            lang_prompt = "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). ثم اكتب ترجمتها الإنجليزية في سطر واحد. بدون إيموجي."
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب تعليقاً قصيراً جداً بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="qwen/qwen3.8-27b", max_tokens=500
        )
        ai_text = chat_completion.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"
        
        post_id = str(int(time.time()))
        media = []
        for i, photo_id in enumerate(photos):
            if i == 0: media.append(telebot.types.InputMediaPhoto(photo_id, caption=final_caption, parse_mode='HTML'))
            else: media.append(telebot.types.InputMediaPhoto(photo_id))
                
        pending_posts[post_id] = {'type': 'album', 'media': media, 'channel': target_channel}
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
        )
        try: bot.delete_message(chat_id, msg_loading.message_id)
        except: pass
        bot.send_media_group(chat_id, media)
        bot.send_message(chat_id, "هل تريد نشر هذا الألبوم؟", reply_markup=markup)
    except Exception as e:
        try: bot.delete_message(chat_id, msg_loading.message_id)
        except: pass
        bot.send_message(chat_id, f"خطأ: {e}")

# ================= 11. أزرار المعاينة =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm_post(call):
    post_id = call.data.split("_")[1]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية")
    data = pending_posts[post_id]
    try:
        target_channel = data['channel']
        if data['type'] == 'photo': bot.send_photo(target_channel, data['file_id'], caption=data['caption'], parse_mode='HTML')
        elif data['type'] == 'album': bot.send_media_group(target_channel, data['media'])
        else: bot.send_message(target_channel, data['caption'], parse_mode='HTML')
        
        stats["published_count"] += 1
        save_json(STATS_FILE, stats)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.answer_callback_query(call.id, text="تم النشر في القناة")
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')
        del pending_posts[post_id]
    except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_"))
def cancel_post(call):
    post_id = call.data.split("_")[1]
    if post_id in pending_posts: del pending_posts[post_id]
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.answer_callback_query(call.id, text="تم إلغاء المنشور")
    bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>", reply_markup=get_main_panel(call.from_user.id), parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith("regen_image_"))
def regen_image(call):
    post_id = call.data.split("_")[2]
    if post_id not in saved_images: return bot.answer_callback_query(call.id, "انتهت الصلاحية", show_alert=True)
    data = saved_images[post_id]
    photo_id = data['photo_id']
    settings = data['settings']
    target_channel = data['channel']
    
    bot.answer_callback_query(call.id, "جاري التوليد...")
    msg_loading = bot.send_message(call.message.chat.id, "⏳ جاري إعادة التحليل...")
    
    try:
        file_info = bot.get_file(photo_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        if settings['language'] == "مختلط":
            lang_prompt = "اكتب جملة واحدة فقط باللغة العربية (لا تتجاوز 10 كلمات). ثم اكتب ترجمتها الإنجليزية في سطر واحد. بدون إيموجي."
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب تعليقاً قصيراً جداً بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="qwen/qwen3.8-27b", max_tokens=500
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
        
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        try: bot.delete_message(call.message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_photo(call.message.chat.id, photo=photo_id, caption=f"<b>معاينة جديدة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        try: bot.delete_message(call.message.chat.id, msg_loading.message_id)
        except: pass
        bot.send_message(call.message.chat.id, f"خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_audio_to_post_"))
def add_audio_to_post(call):
    post_id = call.data.split("_")[4]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية", show_alert=True)
    user_id = call.from_user.id
    pending_audio_merge[user_id] = {
        'post_id': post_id, 'photo_id': pending_posts[post_id]['file_id'],
        'caption': pending_posts[post_id]['caption'], 'channel': pending_posts[post_id]['channel']
    }
    bot.answer_callback_query(ca
