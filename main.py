import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAH6GWopP1_8jWCVZvUj_Yix1pjYNt_zGts'
# ضع مفتاح Groq هنا (يبدأ بـ gsk_)
GROQ_API_KEY ='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' 
CHANNEL_ID = '@Eror_7'
ADMIN_ID = 8456056018 # ضع الايدي الخاص بك هنا

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# إعداد عميل Groq
client = Groq(api_key=GROQ_API_KEY)

# ================= حالة النظام =================
settings = {
    "status": "ON",             
    "text_only_mode": False,    
    "category": "فلسفي",        
    "language": "عربي",         
    "add_hashtags": True,
    "hashtags": "#RedWorld #عالم_الأحمر"
}

generated_texts = {}

# ================= لوحة التحكم الرئيسية (Inline) =================
def get_main_panel():
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
        InlineKeyboardButton("توليد عبارة مستقلة", callback_data="generate_text"),
        InlineKeyboardButton("السورس", callback_data="show_source")
    )
    return markup

# ... (نفس دوال اللوحات السابقة: get_lang_panel, get_categories_panel) ...
def get_lang_panel():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("عربي", callback_data="lang_عربي"),
        InlineKeyboardButton("إنجليزي", callback_data="lang_إنجليزي"),
        InlineKeyboardButton("مختلط", callback_data="lang_مختلط")
    )
    markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return markup

def get_categories_panel():
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
    return markup

# ================= أوامر البداية =================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "لوحة تحكم عالم الأحمر. مرحباً بك.", reply_markup=get_main_panel())

# ================= معالجة الأزرار =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID: return

    if call.data == "main_menu":
        bot.edit_message_text("لوحة تحكم عالم الأحمر. مرحباً بك.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel())

    elif call.data == "toggle_status":
        settings["status"] = "OFF" if settings["status"] == "ON" else "ON"
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_panel())
        bot.answer_callback_query(call.id, "تم التغيير.")

    elif call.data == "toggle_text_mode":
        settings["text_only_mode"] = not settings["text_only_mode"]
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_panel())
        bot.answer_callback_query(call.id, "تم التغيير.")

    elif call.data == "menu_lang":
        bot.edit_message_text("اختر لغة توليد العبارات:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_lang_panel())
    elif call.data.startswith("lang_"):
        settings["language"] = call.data.replace("lang_", "")
        bot.edit_message_text("لوحة تحكم عالم الأحمر. مرحباً بك.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel())
        bot.answer_callback_query(call.id, f"تم اختيار: {settings['language']}")

    elif call.data == "menu_categories":
        bot.edit_message_text("اختر الفئة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_categories_panel())
    elif call.data.startswith("cat_"):
        settings["category"] = call.data.replace("cat_", "")
        bot.edit_message_text("لوحة تحكم عالم الأحمر. مرحباً بك.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel())
        bot.answer_callback_query(call.id, f"تم اختيار: {settings['category']}")

    elif call.data == "show_source":
        source_text = (
            "**عالم الأحمر | Red World**\n\n"
            "مساحة عامة لمشاركة الخواطر الشخصية، تحديثات الحياة، واللحظات الجميلة.\n"
            "شكراً لكونك جزءاً من رحلتي.\n\n"
            "تابع القناة للمزيد."
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("المالك", url="https://t.me/YourUsernameHere"),
            InlineKeyboardButton("مشاركة", url="https://t.me/share/url?url=https://t.me/Eror_7")
        )
        try:
            bot.send_photo(call.message.chat.id, photo="https://t.me/Eror_7", caption=source_text, reply_markup=markup, parse_mode='Markdown')
        except:
            bot.send_message(call.message.chat.id, source_text, reply_markup=markup, parse_mode='Markdown')
        bot.answer_callback_query(call.id)

    elif call.data == "generate_text":
        bot.answer_callback_query(call.id, "جاري التوليد...")
        lang_prompt = f"باللغة {settings['language']}" if settings['language'] != "مختلط" else "مزيج بين العربية والإنجليزية"
        prompt = f"اكتب عبارة قصيرة جداً بأسلوب {settings['category']} {lang_prompt} تناسب قناة اسمها عالم الأحمر. بدون إيموجي."
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
            )
            raw_text = chat_completion.choices[0].message.content.strip()
            
            msg_id = str(int(time.time()))
            generated_texts[msg_id] = {"raw": raw_text, "bold": False, "italic": False, "strike": False, "quote": False}
            send_formatting_panel(call.message.chat.id, msg_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"حدث خطأ أثناء التوليد: {e}")

    # ... (باقي كود التنسيق fmt_ ...) ...
    elif call.data.startswith('fmt_'):
        parts = call.data.split('_')
        action = parts[1]
        msg_id = parts[2]
        if msg_id not in generated_texts: return
        data = generated_texts[msg_id]

        if action == "copy":
            bot.send_message(call.message.chat.id, f"`{data['raw']}`", parse_mode='MarkdownV2')
            bot.answer_callback_query(call.id, "تم إرسال النص للنسخ")
        elif action == "publish":
            final_text = apply_formatting(data)
            if settings["add_hashtags"]: final_text += f"\n\n{settings['hashtags']}"
            try:
                bot.send_message(CHANNEL_ID, final_text, parse_mode='HTML')
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, "تم النشر في القناة.", reply_markup=get_main_panel())
                del generated_texts[msg_id]
            except Exception as e:
                bot.answer_callback_query(call.id, f"خطأ: {e}")
        else:
            if action == "bold": data["bold"] = not data["bold"]
            elif action == "italic": data["italic"] = not data["italic"]
            elif action == "strike": data["strike"] = not data["strike"]
            elif action == "quote": data["quote"] = not data["quote"]
            
            new_text = apply_formatting(data)
            markup = get_formatting_panel_markup(data, msg_id)
            try:
                bot.edit_message_text(f"معاينة النص:\n\n{new_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
            except: pass
            bot.answer_callback_query(call.id, "تم التحديث")

# ... (دوال التنسيق send_formatting_panel, get_formatting_panel_markup, apply_formatting) ...
def send_formatting_panel(chat_id, msg_id):
    data = generated_texts[msg_id]
    text = apply_formatting(data)
    markup = get_formatting_panel_markup(data, msg_id)
    bot.send_message(chat_id, f"معاينة النص:\n\n{text}", reply_markup=markup, parse_mode='HTML')

def get_formatting_panel_markup(data, msg_id):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}"),
        InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}"),
        InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}")
    )
    markup.add(InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}"))
    markup.add(
        InlineKeyboardButton("نسخ النص", callback_data=f"fmt_copy_{msg_id}"),
        InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}")
    )
    return markup

def apply_formatting(data):
    text = data["raw"]
    if data["strike"]: text = f"<s>{text}</s>"
    if data["italic"]: text = f"<i>{text}</i>"
    if data["bold"]: text = f"<b>{text}</b>"
    if data["quote"]: text = f"<blockquote>{text}</blockquote>"
    return text

# ================= استقبال الصور (مع Groq Vision) =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.from_user.id != ADMIN_ID: return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

    if settings["status"] == "OFF":
        bot.send_message(message.chat.id, "النظام معطل حالياً.", reply_markup=get_main_panel())
        return

    msg_loading = bot.send_message(message.chat.id, "جاري تحليل الصورة...")
    
    try:
        # تحميل الصورة وتحويلها إلى Base64
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        import base64
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')

        bot.edit_message_text("جاري كتابة العبارة...", chat_id=message.chat.id, message_id=msg_loading.message_id)

        lang_prompt = f"باللغة {settings['language']}" if settings['language'] != "مختلط" else "مزيج بين العربية والإنجليزية"
        prompt = f"اكتب تعليقاً قصيراً جداً بأسلوب {settings['category']} {lang_prompt} يناسب الصورة. بدون إيموجي."
        
        # إرسال الصورة إلى Groq Vision
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        ai_text = chat_completion.choices[0].message.content.strip()

        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"

        bot.edit_message_text("جاري النشر...", chat_id=message.chat.id, message_id=msg_loading.message_id)
        bot.send_photo(chat_id=CHANNEL_ID, photo=message.photo[-1].file_id, caption=final_caption, parse_mode='HTML')

        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_message(message.chat.id, "تم النشر بنجاح.", reply_markup=get_main_panel())

    except Exception as e:
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_message(message.chat.id, f"حدث خطأ: {e}", reply_markup=get_main_panel())

# ... (handle_text يبقى كما هو) ...
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.from_user.id != ADMIN_ID: return
    if message.text.startswith('/'): return
    if settings["text_only_mode"] and settings["status"] == "ON":
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        text_to_publish = f"<b>{message.text}</b>"
        if settings["add_hashtags"]: text_to_publish += f"\n\n{settings['hashtags']}"
        bot.send_message(CHANNEL_ID, text_to_publish, parse_mode='HTML')
        bot.send_message(message.chat.id, "تم نشر النص.", reply_markup=get_main_panel())

print("البوت الرسمي يعمل الآن (Groq)...")
bot.infinity_polling()
