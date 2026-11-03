import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time
import base64
import platform
import datetime
import threading

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAH6GWopP1_8jWCVZvUj_Yix1pjYNt_zGts'
GROQ_API_KEY = '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'
CHANNEL_ID = '@Eror_7'
ADMIN_ID = 8456056018 # <--- ضع الايدي الخاص بك هنا (رقمك)

bot = telebot.TeleBot(TELEGRAM_TOKEN)
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
pending_posts = {} # لتخزين المنشورات المؤقتة (المعاينة والجدولة)

# ================= إشعار الرفع التلقائي =================
def check_admin_status_and_notify():
    time.sleep(3)
    try:
        bot_info = bot.get_me()
        chat_info = bot.get_chat(CHANNEL_ID)
        
        notification_text = (
            f"<b>⟨ تقرير حالة البوت | Bot Status ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote>"
            f"<b>اسم البوت:</b> @{bot_info.username}\n"
            f"<b>اسم القناة:</b> {chat_info.title}\n"
            f"<b>حالة الاتصال:</b> <i>متصل بنجاح (Online)</i>\n"
            f"<b>الوقت:</b> {datetime.datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}"
            f"</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<i>ملاحظة: تأكد يدوياً من أن البوت مشرف (Admin) في القناة لكي يتمكن من النشر.</i>"
        )
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("مشاركة البوت", url=f"https://t.me/share/url?url=https://t.me/{bot_info.username}"))
        bot.send_message(ADMIN_ID, notification_text, reply_markup=markup, parse_mode='HTML')
        
    except Exception as e:
        try: 
            bot.send_message(ADMIN_ID, f"⚠️ تنبيه: البوت غير قادر على الاتصال بالقناة.\nالسبب: {e}\n\nتأكد من إضافة البوت إلى القناة أولاً.")
        except: 
            pass

threading.Thread(target=check_admin_status_and_notify, daemon=True).start()

# ================= دالة النشر المجدول =================
def schedule_post(post_id, delay_minutes):
    time.sleep(delay_minutes * 60)
    if post_id in pending_posts:
        data = pending_posts[post_id]
        try:
            if data['type'] == 'photo':
                bot.send_photo(chat_id=CHANNEL_ID, photo=data['file_id'], caption=data['caption'], parse_mode='HTML')
            elif data['type'] == 'text':
                bot.send_message(CHANNEL_ID, data['caption'], parse_mode='HTML')
            
            bot.send_message(ADMIN_ID, "✅ تم النشر المجدول بنجاح في القناة.")
            del pending_posts[post_id]
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ فشل النشر المجدول: {e}")

# ================= لوحة التحكم الرئيسية =================
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

def get_lang_panel():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(InlineKeyboardButton("عربي", callback_data="lang_عربي"), InlineKeyboardButton("إنجليزي", callback_data="lang_إنجليزي"), InlineKeyboardButton("مختلط", callback_data="lang_مختلط"))
    markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return markup

def get_categories_panel():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("حزين", callback_data="cat_حزين"), InlineKeyboardButton("تفاؤل", callback_data="cat_تفاؤل"))
    markup.add(InlineKeyboardButton("فلسفي", callback_data="cat_فلسفي"), InlineKeyboardButton("غامض", callback_data="cat_غامض"))
    markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return markup

def get_formatting_panel_markup(data, msg_id):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("غامق [مفعل]" if data["bold"] else "غامق", callback_data=f"fmt_bold_{msg_id}"),
        InlineKeyboardButton("مائل [مفعل]" if data["italic"] else "مائل", callback_data=f"fmt_italic_{msg_id}"),
        InlineKeyboardButton("مشطوب [مفعل]" if data["strike"] else "مشطوب", callback_data=f"fmt_strike_{msg_id}")
    )
    markup.add(InlineKeyboardButton("اقتباس [مفعل]" if data["quote"] else "اقتباس", callback_data=f"fmt_quote_{msg_id}"))
    markup.add(InlineKeyboardButton("نسخ النص", callback_data=f"fmt_copy_{msg_id}"), InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}"))
    return markup

# ================= الدالة المفقودة التي سببت الخطأ =================
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

# ================= أوامر البداية =================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    welcome_text = "<b>نظام إدارة عالم الأحمر</b>\n━━━━━━━━━━━━━━━━━━\nمرحباً بك. أرسل صورة أو نصاً (في وضع النشر النصي) للمعاينة والنشر."
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_panel(), parse_mode='HTML')

# ================= معالجة الأزرار =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID: return

    # --- أزرار المعاينة (نشر فوري، جدولة، إلغاء) ---
    if call.data.startswith("confirm_"):
        post_id = call.data.split("_")[1]
        if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت صلاحية هذا المنشور.")
        
        data = pending_posts[post_id]
        try:
            if data['type'] == 'photo':
                bot.send_photo(CHANNEL_ID, data['file_id'], caption=data['caption'], parse_mode='HTML')
            else:
                bot.send_message(CHANNEL_ID, data['caption'], parse_mode='HTML')
            
            bot.edit_message_text("✅ تم النشر في القناة بنجاح.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            del pending_posts[post_id]
        except Exception as e:
            bot.answer_callback_query(call.id, f"خطأ: {e}")

    elif call.data.startswith("schedule_"):
        post_id = call.data.split("_")[1]
        msg = bot.send_message(call.message.chat.id, "⏳ أرسل عدد الدقائق التي تريد تأجيل النشر إليها (مثال: 30):")
        bot.register_next_step_handler(msg, process_schedule_time, post_id)

    elif call.data.startswith("cancel_"):
        post_id = call.data.split("_")[1]
        if post_id in pending_posts: del pending_posts[post_id]
        bot.edit_message_text("❌ تم إلغاء المنشور وحذفه.", chat_id=call.message.chat.id, message_id=call.message.message_id)

    # --- القائمة الرئيسية والتحكم ---
    elif call.data == "main_menu":
        bot.edit_message_text("<b>نظام إدارة عالم الأحمر</b>\n━━━━━━━━━━━━━━━━━━\nاختر ما تريد:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(), parse_mode='HTML')
    elif call.data == "toggle_status":
        settings["status"] = "OFF" if settings["status"] == "ON" else "ON"
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_panel())
        bot.answer_callback_query(call.id, f"تم {'تفعيل' if settings['status'] == 'ON' else 'تعطيل'} النشر.")
    elif call.data == "toggle_text_mode":
        settings["text_only_mode"] = not settings["text_only_mode"]
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_main_panel())
        bot.answer_callback_query(call.id, f"تم {'تفعيل' if settings['text_only_mode'] else 'تعطيل'} النشر النصي.")
    elif call.data == "menu_lang":
        bot.edit_message_text("اختر اللغة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_lang_panel())
    elif call.data.startswith("lang_"):
        settings["language"] = call.data.replace("lang_", "")
        bot.edit_message_text("تم التحديث.", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel())
        bot.answer_callback_query(call.id, f"اللغة: {settings['language']}")
    elif call.data == "menu_categories":
        text = "<b>الفئات:</b>\nاختر الفئة:"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_categories_panel(), parse_mode='HTML')
    elif call.data.startswith("cat_"):
        settings["category"] = call.data.replace("cat_", "")
        bot.edit_message_text(f"تم اختيار: <b>{settings['category']}</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(), parse_mode='HTML')
    
    # --- السورس ---
    elif call.data == "show_source":
        source_text = (
            f"<b>⟨ RED WORLD | عالم الأحمر ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote><b>المطور:</b> Hasan\n<b>اليوزر:</b> @YourUsernameHere\n<b>الآيدي:</b> <code>123456789</code>\n<b>القناة:</b> @Eror_7</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<i>مساحة لمشاركة الخواطر، اللحظات الجميلة، وتأملات الحياة.</i>"
        )
        markup = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("المطور", url="https://t.me/YourUsernameHere"), InlineKeyboardButton("مشاركة", url="https://t.me/share/url?url=https://t.me/Eror_7"))
        bot.send_message(call.message.chat.id, source_text, reply_markup=markup, parse_mode='HTML')

    # --- توليد العبارة المستقلة ---
    elif call.data == "generate_text":
        bot.answer_callback_query(call.id, "جاري التوليد...")
        lang_prompt = f"باللغة {settings['language']}" if settings['language'] != "مختلط" else "مزيج بين العربية والإنجليزية"
        prompt = f"اكتب عبارة قصيرة جداً بأسلوب {settings['category']} {lang_prompt} تناسب قناة اسمها عالم الأحمر. بدون إيموجي."
        try:
            chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="qwen/qwen3.8-27b")
            raw_text = chat_completion.choices[0].message.content.strip()
            msg_id = str(int(time.time()))
            generated_texts[msg_id] = {"raw": raw_text, "bold": False, "italic": False, "strike": False, "quote": False}
            send_formatting_panel(call.message.chat.id, msg_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"خطأ: {e}")

    # --- أزرار التنسيق والنشر النهائي للعبارة ---
    elif call.data.startswith('fmt_'):
        parts = call.data.split('_')
        action, msg_id = parts[1], parts[2]
        if msg_id not in generated_texts: return
        data = generated_texts[msg_id]

        if action == "copy":
            bot.send_message(call.message.chat.id, f"`{data['raw']}`", parse_mode='MarkdownV2')
            bot.answer_callback_query(call.id, "تم إرسال النص للنسخ")
        elif action == "publish":
            final_text = apply_formatting(data)
            if settings["add_hashtags"]: final_text += f"\n\n{settings['hashtags']}"
            
            post_id = str(int(time.time()))
            pending_posts[post_id] = {'type': 'text', 'caption': final_text}
            
            markup = InlineKeyboardMarkup(row_width=3)
            markup.add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
            
            bot.send_message(call.message.chat.id, f"<b>معاينة قبل النشر:</b>\n\n{final_text}", reply_markup=markup, parse_mode='HTML')
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            if action == "bold": data["bold"] = not data["bold"]
            elif action == "italic": data["italic"] = not data["italic"]
            elif action == "strike": data["strike"] = not data["strike"]
            elif action == "quote": data["quote"] = not data["quote"]
            new_text = apply_formatting(data)
            markup = get_formatting_panel_markup(data, msg_id)
            try: bot.edit_message_text(f"معاينة النص:\n\n{new_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
            except: pass
            bot.answer_callback_query(call.id, "تم التحديث")

# ================= دالة استلام وقت الجدولة =================
def process_schedule_time(message, post_id):
    if message.from_user.id != ADMIN_ID: return
    try:
        minutes = int(message.text)
        if post_id in pending_posts:
            bot.reply_to(message, f"✅ تم جدولة المنشور للنشر بعد {minutes} دقيقة.")
            threading.Thread(target=schedule_post, args=(post_id, minutes), daemon=True).start()
        else:
            bot.reply_to(message, "❌ حدث خطأ، المنشور غير موجود.")
    except ValueError:
        bot.reply_to(message, "❌ يرجى إرسال رقم صحيح (مثال: 30).")

# ================= استقبال الصور (معاينة قبل النشر) =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.from_user.id != ADMIN_ID: return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

    if settings["status"] == "OFF":
        return bot.send_message(message.chat.id, "النظام معطل حالياً.", reply_markup=get_main_panel())

    msg_loading = bot.send_message(message.chat.id, "جاري تحليل الصورة...")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')

        bot.edit_message_text("جاري كتابة العبارة...", chat_id=message.chat.id, message_id=msg_loading.message_id)
        lang_prompt = f"باللغة {settings['language']}" if settings['language'] != "مختلط" else "مزيج بين العربية والإنجليزية"
        prompt = f"اكتب تعليقاً قصيراً جداً بأسلوب {settings['category']} {lang_prompt} يناسب الصورة. بدون إيموجي."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="qwen/qwen3.8-27b",
        )
        ai_text = chat_completion.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"

        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'photo', 'file_id': message.photo[-1].file_id, 'caption': final_caption}
        
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
        
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=f"<b>معاينة قبل النشر:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')

    except Exception as e:
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_message(message.chat.id, f"حدث خطأ: {e}", reply_markup=get_main_panel())

# ================= استقبال النصوص (للنشر النصي) =================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.from_user.id != ADMIN_ID: return
    if message.text.startswith('/'): return
    if settings["text_only_mode"] and settings["status"] == "ON":
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        
        text_to_publish = f"<b>{message.text}</b>"
        if settings["add_hashtags"]: text_to_publish += f"\n\n{settings['hashtags']}"
        
        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'text', 'caption': text_to_publish}
        
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
        
        bot.send_message(message.chat.id, f"<b>معاينة قبل النشر:</b>\n\n{text_to_publish}", reply_markup=markup, parse_mode='HTML')

print("البوت الرسمي يعمل الآن (مع نظامي المعاينة والجدولة)...")
bot.infinity_polling()
