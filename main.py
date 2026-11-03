import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai
import time

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAH6GWopP1_8jWCVZvUj_Yix1pjYNt_zGts'
GEMINI_API_KEY = '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'
CHANNEL_ID = '@Eror_7'
ADMIN_ID = 8456056018 # <--- ضع الايدي الخاص بك هنا

bot = telebot.TeleBot(TELEGRAM_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

# ================= حالة النظام =================
settings = {
    "status": "ON",             
    "text_only_mode": False,    
    "category": "فلسفي",        
    "language": "عربي",         
    "add_hashtags": True,
    "hashtags": "#RedWorld #عالم_الأحمر"
}

# ذاكرة مؤقتة لحفظ النصوص المولدة وتنسيقاتها
generated_texts = {}

# ================= لوحة التحكم الرئيسية =================
def get_main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    status_txt = "تعطيل النشر" if settings["status"] == "ON" else "تفعيل النشر"
    text_mode_txt = "تعطيل النشر النصي" if settings["text_only_mode"] else "تفعيل النشر النصي"
    markup.add(KeyboardButton(status_txt), KeyboardButton(text_mode_txt))
    markup.add(KeyboardButton("فئات العبارات"), KeyboardButton(f"اللغة: {settings['language']}"))
    markup.add(KeyboardButton("توليد عبارة مستقلة"), KeyboardButton("تغيير الهاشتاقات"))
    return markup

# ================= لوحة اللغات =================
def get_lang_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(KeyboardButton("عربي"), KeyboardButton("إنجليزي"), KeyboardButton("مختلط"))
    markup.add(KeyboardButton("عودة للقائمة الرئيسية"))
    return markup

# ================= لوحة فئات العبارات =================
def get_categories_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("حزين"), KeyboardButton("تفاؤل"))
    markup.add(KeyboardButton("فلسفي"), KeyboardButton("غامض"))
    markup.add(KeyboardButton("عودة للقائمة الرئيسية"))
    return markup

def send_clean_message(chat_id, text, reply_markup=None):
    return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode='HTML')

# ================= أوامر البداية =================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "لوحة تحكم عالم الأحمر. مرحباً بك.", reply_markup=get_main_keyboard())

# ================= التحكم بالأزرار =================
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID)
def handle_admin_buttons(message):
    text = message.text
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

    if text == "تعطيل النشر":
        settings["status"] = "OFF"
        send_clean_message(message.chat.id, "تم تعطيل النظام.", get_main_keyboard())
    elif text == "تفعيل النشر":
        settings["status"] = "ON"
        send_clean_message(message.chat.id, "تم تفعيل النظام.", get_main_keyboard())
    elif text == "تفعيل النشر النصي":
        settings["text_only_mode"] = True
        send_clean_message(message.chat.id, "تم تفعيل وضع النشر النصي.", get_main_keyboard())
    elif text == "تعطيل النشر النصي":
        settings["text_only_mode"] = False
        send_clean_message(message.chat.id, "تم تعطيل وضع النشر النصي.", get_main_keyboard())
    elif text.startswith("اللغة:"):
        send_clean_message(message.chat.id, "اختر لغة توليد العبارات:", get_lang_keyboard())
    elif text in ["عربي", "إنجليزي", "مختلط"]:
        settings["language"] = text
        send_clean_message(message.chat.id, f"تم اختيار اللغة: {text}.", get_main_keyboard())
    elif text == "فئات العبارات":
        send_clean_message(message.chat.id, "اختر الفئة:", get_categories_keyboard())
    elif text in ["حزين", "تفاؤل", "فلسفي", "غامض"]:
        settings["category"] = text
        send_clean_message(message.chat.id, f"تم اختيار فئة: {text}.", get_main_keyboard())
    elif text == "عودة للقائمة الرئيسية":
        send_clean_message(message.chat.id, "القائمة الرئيسية.", get_main_keyboard())
    elif text == "تغيير الهاشتاقات":
        msg = bot.send_message(message.chat.id, "أرسل الهاشتاقات الجديدة:")
        bot.register_next_step_handler(msg, save_hashtags)

    elif text == "توليد عبارة مستقلة":
        bot.send_chat_action(message.chat.id, 'typing')
        lang_prompt = f"باللغة {settings['language']}" if settings['language'] != "مختلط" else "مزيج بين العربية والإنجليزية"
        prompt = f"اكتب عبارة قصيرة جداً بأسلوب {settings['category']} {lang_prompt} تناسب قناة اسمها عالم الأحمر. بدون إيموجي."
        try:
            response = ai_model.generate_content(prompt)
            raw_text = response.text.strip()
            
            msg_id = str(int(time.time()))
            # حفظ النص الخام وحالة كل تنسيق
            generated_texts[msg_id] = {
                "raw": raw_text, 
                "bold": False, 
                "italic": False, 
                "strike": False, 
                "quote": False
            }
            
            send_formatting_panel(message.chat.id, msg_id)
        except Exception as e:
            send_clean_message(message.chat.id, "حدث خطأ أثناء التوليد.", get_main_keyboard())

def save_hashtags(message):
    settings["hashtags"] = message.text
    send_clean_message(message.chat.id, "تم حفظ الهاشتاقات.", get_main_keyboard())

# ================= لوحة التنسيق =================
def send_formatting_panel(chat_id, msg_id):
    data = generated_texts[msg_id]
    text = apply_formatting(data)
    
    markup = InlineKeyboardMarkup(row_width=3)
    # الأزرار تتغير حسب الحالة (مفعل/معطل)
    btn_bold = InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}")
    btn_italic = InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}")
    btn_strike = InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}")
    btn_quote = InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}")
    
    btn_copy = InlineKeyboardButton("نسخ النص", callback_data=f"fmt_copy_{msg_id}")
    btn_publish = InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}")
    
    markup.add(btn_bold, btn_italic, btn_strike)
    markup.add(btn_quote)
    markup.add(btn_copy, btn_publish)
    
    try:
        bot.send_message(chat_id, f"معاينة النص:\n\n{text}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.send_message(chat_id, f"خطأ في التنسيق: {e}")

def apply_formatting(data):
    text = data["raw"]
    # تطبيق التنسيقات بترتيب صحيح (من الداخل للخارج)
    if data["strike"]: text = f"<s>{text}</s>"
    if data["italic"]: text = f"<i>{text}</i>"
    if data["bold"]: text = f"<b>{text}</b>"
    if data["quote"]: text = f"<blockquote>{text}</blockquote>"
    return text

# ================= معالجة الأزرار =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('fmt_'))
def callback_formatting(call):
    if call.from_user.id != ADMIN_ID: return
    
    parts = call.data.split('_')
    action = parts[1]
    msg_id = parts[2]
    
    if msg_id not in generated_texts:
        bot.answer_callback_query(call.id, "انتهت صلاحية هذه العبارة.")
        return

    data = generated_texts[msg_id]

    # نظام النسخ
    if action == "copy":
        # إرسال النص الخام بدون أي تنسيقات ليكون جاهزاً للنسخ
        bot.send_message(call.message.chat.id, f"النص الجاهز للنسخ:\n\n`{data['raw']}`", parse_mode='MarkdownV2')
        bot.answer_callback_query(call.id, "تم إرسال النص للنسخ")
        return

    # نظام النشر
    elif action == "publish":
        final_text = apply_formatting(data)
        if settings["add_hashtags"]:
            final_text += f"\n\n{settings['hashtags']}"
        try:
            bot.send_message(CHANNEL_ID, final_text, parse_mode='HTML')
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_clean_message(call.message.chat.id, "تم النشر في القناة.", get_main_keyboard())
            del generated_texts[msg_id]
        except Exception as e:
            bot.answer_callback_query(call.id, f"خطأ: {e}")
        return

    # تفعيل/تعطيل التنسيقات
    elif action == "bold": data["bold"] = not data["bold"]
    elif action == "italic": data["italic"] = not data["italic"]
    elif action == "strike": data["strike"] = not data["strike"]
    elif action == "quote": data["quote"] = not data["quote"]

    # تحديث الرسالة بالمعاينة الجديدة والأزرار الجديدة
    new_text = apply_formatting(data)
    
    markup = InlineKeyboardMarkup(row_width=3)
    btn_bold = InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}")
    btn_italic = InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}")
    btn_strike = InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}")
    btn_quote = InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}")
    btn_copy = InlineKeyboardButton("نسخ النص", callback_data=f"fmt_copy_{msg_id}")
    btn_publish = InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}")
    markup.add(btn_bold, btn_italic, btn_strike)
    markup.add(btn_quote)
    markup.add(btn_copy, btn_publish)

    try:
        bot.edit_message_text(f"معاينة النص:\n\n{new_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
    except Exception:
        pass
    bot.answer_callback_query(call.id, "تم تحديث التنسيق")

# ================= استقبال الصور =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.from_user.id != ADMIN_ID: return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

    if settings["status"] == "OFF":
        send_clean_message(message.chat.id, "النظام معطل حالياً.", get_main_keyboard())
        return

    msg_loading = bot.send_message(message.chat.id, "جاري تحليل الصورة...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_data = {'mime_type': 'image/jpeg', 'data': downloaded_file}

        bot.edit_message_text("جاري كتابة العبارة...", chat_id=message.chat.id, message_id=msg_loading.message_id)

        lang_prompt = f"باللغة {settings['language']}" if settings['language'] != "مختلط" else "مزيج بين العربية والإنجليزية"
        prompt = f"اكتب تعليقاً قصيراً جداً بأسلوب {settings['category']} {lang_prompt} يناسب الصورة المرفقة. بدون إيموجي."
        response = ai_model.generate_content([prompt, image_data])
        ai_text = response.text.strip()

        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]:
            final_caption += f"\n\n{settings['hashtags']}"

        bot.edit_message_text("جاري النشر...", chat_id=message.chat.id, message_id=msg_loading.message_id)
        bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id, caption=final_caption, parse_mode='HTML')

        bot.delete_message(message.chat.id, msg_loading.message_id)
        send_clean_message(message.chat.id, "تم النشر بنجاح.", get_main_keyboard())

    except Exception as e:
        bot.delete_message(message.chat.id, msg_loading.message_id)
        send_clean_message(message.chat.id, f"حدث خطأ: {e}", get_main_keyboard())

# ================= استقبال النصوص =================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.from_user.id != ADMIN_ID: return
    if message.text.startswith('/'): return

    if settings["text_only_mode"] and settings["status"] == "ON":
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
            
        text_to_publish = f"<b>{message.text}</b>"
        if settings["add_hashtags"]:
            text_to_publish += f"\n\n{settings['hashtags']}"

        bot.send_message(CHANNEL_ID, text_to_publish, parse_mode='HTML')
        send_clean_message(message.chat.id, "تم نشر النص.", get_main_keyboard())

print("البوت الرسمي يعمل الآن...")
bot.infinity_polling()
