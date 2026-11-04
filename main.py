import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time
import base64
import datetime
import threading

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAH6GWopP1_8jWCVZvUj_Yix1pjYNt_zGts'
GROQ_API_KEY = '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'
CHANNEL_ID = '@Eror_7'
ADMIN_ID = 8456056018 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

settings = {
    "status": "ON",             
    "text_only_mode": False,    
    "category": "فلسفي",        
    "language": "عربي",         
    "add_hashtags": True,
    "hashtags": "#RedWorld #عالم_الأحمر"
}

generated_texts = {}
pending_posts = {}
saved_images = {} # لتخزين الصور لاستخدامها في البحث عن أغنية

# ================= 1. الترحيب الذكي للمستخدمين الجدد =================
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_members(message):
    for member in message.new_chat_members:
        try:
            dev_info = bot.get_chat(ADMIN_ID)
            dev_name = dev_info.first_name
        except:
            dev_name = "المطور"

        welcome_text = (
            f"<b>⟨ مرحباً بك في عالم الأحمر ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote>"
            f"أهلاً بك يا <b>{member.first_name}</b>!\n"
            f"هذه مساحة هادئة لمشاركة الخواطر واللحظات الجميلة.\n"
            f"تم تصميم هذا النظام بعناية فائقة."
            f"</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<i>المطور: {dev_name}</i>"
        )
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("إضافة البوت لقناتك", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
            InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}")
        )
        markup.add(InlineKeyboardButton("تم رفع البوت (فحص)", callback_data="check_bot_status"))
        
        try:
            bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='HTML')
        except:
            pass

# ================= 2. نظام الفحص الذكي =================
@bot.callback_query_handler(func=lambda call: call.data == "check_bot_status")
def check_bot_status(call):
    msg_loading = bot.send_message(call.message.chat.id, "⏳ جاري فحص الاتصال بالقناة والصلاحيات...")
    time.sleep(1.5)
    try:
        test_msg = bot.send_message(CHANNEL_ID, "System Check...")
        bot.delete_message(CHANNEL_ID, test_msg.message_id)
        success_text = (
            f"<b>⟨ نتيجة الفحص ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote><b>الحالة:</b> ✅ ناجح\n<b>الاتصال:</b> البوت مرفوع ومشرف في القناة.\n<b>الصلاحيات:</b> يمتلك صلاحية النشر.</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<i>يمكنك الآن استخدام لوحة التحكم لإدارة القناة.</i>"
        )
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("فتح القائمة الرئيسية", callback_data="main_menu"))
        bot.edit_message_text(success_text, chat_id=call.message.chat.id, message_id=msg_loading.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id, "✅ البوت يعمل بنجاح!")
    except Exception as e:
        error_text = (
            f"<b>⟨ نتيجة الفحص ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote><b>الحالة:</b> ❌ فشل\n<b>السبب:</b> البوت ليس مشرفاً في القناة أو تم طرده.</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<i>يرجى رفع البوت كمشرف وإعطائه صلاحية 'نشر الرسائل' ثم إعادة الفحص.</i>"
        )
        markup = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("إعادة الفحص", callback_data="check_bot_status"),
            InlineKeyboardButton("إضافة البوت للقناة", url=f"https://t.me/{bot.get_me().username}?startchannel=true"),
            InlineKeyboardButton("رجوع للقائمة", callback_data="main_menu")
        )
        bot.edit_message_text(error_text, chat_id=call.message.chat.id, message_id=msg_loading.message_id, reply_markup=markup, parse_mode='HTML')
        bot.answer_callback_query(call.id, "❌ فشل الفحص.")

# ================= 3. لوحات التحكم =================
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
    markup.add(InlineKeyboardButton("فحص حالة البوت", callback_data="check_bot_status"))
    return markup

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
    markup.add(InlineKeyboardButton("نسخ النص", callback_data=f"fmt_copy_{msg_id}"), InlineKeyboardButton("نشر في القناة", callback_data=f"fmt_publish_{msg_id}"))
    markup.add(InlineKeyboardButton("إلغاء وحذف", callback_data=f"fmt_cancel_{msg_id}"))
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

# ================= 4. الترحيب بالمدير =================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    welcome_text = "<b>مرحباً بك في نظام إدارة عالم الأحمر</b>\n\nهذه هي لوحة التحكم الرئيسية. اختر الإجراء الذي تريده:"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_panel(), parse_mode='HTML')

# ================= 5. معالجة الأزرار =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID: return

    # 1. زر الرجوع
    if call.data == "main_menu":
        main_text = "<b>مرحباً بك في نظام إدارة عالم الأحمر</b>\n\nاختر الإجراء الذي تريده:"
        if call.message.content_type == 'photo':
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            bot.send_message(call.message.chat.id, main_text, reply_markup=get_main_panel(), parse_mode='HTML')
        else:
            bot.edit_message_text(main_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(), parse_mode='HTML')
        return bot.answer_callback_query(call.id)

    # 2. التفعيل والتعطيل
    elif call.data == "toggle_status":
        settings["status"] = "OFF" if settings["status"] == "ON" else "ON"
        bot.edit_message_text("‎", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel())
        return bot.answer_callback_query(call.id, text=f"حالة النشر: {'مفعل' if settings['status'] == 'ON' else 'معطل'}", show_alert=False)

    elif call.data == "toggle_text_mode":
        settings["text_only_mode"] = not settings["text_only_mode"]
        bot.edit_message_text("‎", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel())
        return bot.answer_callback_query(call.id, text=f"النشر النصي: {'مفعل' if settings['text_only_mode'] else 'معطل'}", show_alert=False)

    # 3. اللغة
    elif call.data == "menu_lang":
        bot.edit_message_text("<b>إعدادات اللغة:</b>\n\nاختر اللغة التي تريدها:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_lang_panel(), parse_mode='HTML')
        return bot.answer_callback_query(call.id)

    elif call.data.startswith("lang_"):
        settings["language"] = call.data.replace("lang_", "")
        bot.edit_message_text("<b>مرحباً بك في نظام إدارة عالم الأحمر</b>\n\nاختر الإجراء الذي تريده:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(), parse_mode='HTML')
        return bot.answer_callback_query(call.id, text=f"تم اختيار اللغة: {settings['language']}", show_alert=False)

    # 4. الفئات
    elif call.data == "menu_categories":
        bot.edit_message_text("<b>فئات العبارات:</b>\n\nاختر الفئة التي تناسب جو القناة:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_categories_panel(), parse_mode='HTML')
        return bot.answer_callback_query(call.id)

    elif call.data.startswith("cat_"):
        settings["category"] = call.data.replace("cat_", "")
        bot.edit_message_text("<b>مرحباً بك في نظام إدارة عالم الأحمر</b>\n\nاختر الإجراء الذي تريده:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(), parse_mode='HTML')
        return bot.answer_callback_query(call.id, text=f"تم اختيار الفئة: {settings['category']}", show_alert=False)

    # 5. السورس
    elif call.data == "show_source":
        try:
            dev_info = bot.get_chat(ADMIN_ID)
            dev_name = dev_info.first_name
        except:
            dev_name = "المطور"

        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass

        source_text = (
            f"<b>⟨ RED WORLD | عالم الأحمر ⟩</b>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<blockquote><b>المطور:</b> {dev_name}\n<b>القناة:</b> @Eror_7</blockquote>\n"
            f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
            f"<i>مساحة لمشاركة الخواطر، اللحظات الجميلة، وتأملات الحياة.</i>"
        )
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton(f"المطور: {dev_name}", url=f"tg://user?id={ADMIN_ID}"), 
            InlineKeyboardButton("مشاركة القناة", url="https://t.me/share/url?url=https://t.me/Eror_7"),
            InlineKeyboardButton("رجوع للقائمة", callback_data="main_menu")
        )
        
        try:
            chat_info = bot.get_chat(CHANNEL_ID)
            if chat_info.photo:
                file_info = bot.get_file(chat_info.photo.big_file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                bot.send_photo(call.message.chat.id, photo=downloaded_file, caption=source_text, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_message(call.message.chat.id, source_text, reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            bot.send_message(call.message.chat.id, source_text + f"\n\n(تعذر جلب الصورة: {e})", reply_markup=markup, parse_mode='HTML')
            
        return bot.answer_callback_query(call.id)

    # 6. توليد العبارة
    elif call.data == "generate_text":
        bot.answer_callback_query(call.id, text="جاري التوليد...", show_alert=False)
        
        if settings['language'] == "مختلط":
            lang_prompt = "اكتب العبارة باللغة العربية أولاً، ثم اترك سطراً فارغاً، ثم اكتب ترجمتها باللغة الإنجليزية تحت العربية."
        else:
            lang_prompt = f"باللغة {settings['language']}"

        prompt = f"اكتب عبارة قصيرة جداً بأسلوب {settings['category']} {lang_prompt} تناسب قناة اسمها عالم الأحمر. بدون إيموجي."
        
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}], 
                model="qwen/qwen3.8-27b",
                max_tokens=500
            )
            raw_text = chat_completion.choices[0].message.content.strip()
            msg_id = str(int(time.time()))
            generated_texts[msg_id] = {"raw": raw_text, "bold": False, "italic": False, "strike": False, "quote": False}
            send_formatting_panel(call.message.chat.id, msg_id)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"خطأ: {e}")

    # 7. أزرار التنسيق
    elif call.data.startswith('fmt_'):
        parts = call.data.split('_')
        action, msg_id = parts[1], parts[2]
        if msg_id not in generated_texts: return
        data = generated_texts[msg_id]

        if action == "cancel":
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            bot.answer_callback_query(call.id, text="تم إلغاء العبارة وحذفها", show_alert=False)
            bot.send_message(call.message.chat.id, "<b>مرحباً بك في نظام إدارة عالم الأحمر</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(), parse_mode='HTML')
            return

        elif action == "copy":
            bot.send_message(call.message.chat.id, f"`{data['raw']}`", parse_mode='MarkdownV2')
            return bot.answer_callback_query(call.id, text="تم إرسال النص للنسخ", show_alert=False)

        elif action == "publish":
            final_text = apply_formatting(data)
            if settings["add_hashtags"]: final_text += f"\n\n{settings['hashtags']}"
            post_id = str(int(time.time()))
            pending_posts[post_id] = {'type': 'text', 'caption': final_text}
            
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

    # 8. البحث عن أغنية
    elif call.data.startswith("find_song_"):
        post_id = call.data.split("_")[2]
        if post_id not in saved_images: return bot.answer_callback_query(call.id, "انتهت الصلاحية")
        
        bot.answer_callback_query(call.id, text="جاري البحث عن أغنية تناسب الصورة...", show_alert=False)
        msg_loading = bot.send_message(call.message.chat.id, "⏳ جاري تحليل الصورة واقتراح أغنية...")
        
        try:
            file_info = bot.get_file(saved_images[post_id])
            downloaded_file = bot.download_file(file_info.file_path)
            base64_image = base64.b64encode(downloaded_file).decode('utf-8')
            
            prompt = "انظر إلى هذه الصورة واقترح اسم أغنية (عربية أو إنجليزية) تناسب جوها ومزاجها. اكتب اسم الأغنية والفنان فقط، بدون أي كلام إضافي."
            
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                model="qwen/qwen3.8-27b",
                max_tokens=200
            )
            song_suggestion = chat_completion.choices[0].message.content.strip()
            
            bot.delete_message(call.message.chat.id, msg_loading.message_id)
            bot.send_message(call.message.chat.id, f"<b>🎵 الأغنية المقترحة:</b>\n\n{song_suggestion}", parse_mode='HTML')
            
        except Exception as e:
            bot.delete_message(call.message.chat.id, msg_loading.message_id)
            bot.send_message(call.message.chat.id, f"حدث خطأ أثناء البحث: {e}")

    # 9. تأكيد النشر
    elif call.data.startswith("confirm_"):
        post_id = call.data.split("_")[1]
        if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية")
        data = pending_posts[post_id]
        try:
            if data['type'] == 'photo': bot.send_photo(CHANNEL_ID, data['file_id'], caption=data['caption'], parse_mode='HTML')
            else: bot.send_message(CHANNEL_ID, data['caption'], parse_mode='HTML')
            
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            
            bot.answer_callback_query(call.id, text="تم النشر في القناة", show_alert=False)
            bot.send_message(call.message.chat.id, "<b>مرحباً بك في نظام إدارة عالم الأحمر</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(), parse_mode='HTML')
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
        bot.send_message(call.message.chat.id, "<b>مرحباً بك في نظام إدارة عالم الأحمر</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(), parse_mode='HTML')

# ================= 6. الدوال المساعدة =================
def schedule_post(post_id, delay_minutes):
    time.sleep(delay_minutes * 60)
    if post_id in pending_posts:
        data = pending_posts[post_id]
        try:
            if data['type'] == 'photo': bot.send_photo(CHANNEL_ID, data['file_id'], caption=data['caption'], parse_mode='HTML')
            else: bot.send_message(CHANNEL_ID, data['caption'], parse_mode='HTML')
            bot.send_message(ADMIN_ID, "✅ تم النشر المجدول.")
            del pending_posts[post_id]
        except Exception as e: bot.send_message(ADMIN_ID, f"❌ فشل النشر: {e}")

def process_schedule_time(message, post_id):
    try:
        minutes = int(message.text)
        if post_id in pending_posts:
            bot.reply_to(message, f"✅ تم الجدولة بعد {minutes} دقيقة.")
            threading.Thread(target=schedule_post, args=(post_id, minutes), daemon=True).start()
    except: bot.reply_to(message, "❌ أرسل رقماً صحيحاً.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.from_user.id != ADMIN_ID: return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    if settings["status"] == "OFF": return bot.send_message(message.chat.id, "معطل.", reply_markup=get_main_panel())

    msg_loading = bot.send_message(message.chat.id, "جاري التحليل...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        # الترتيب في حالة اللغة المختلطة
        if settings['language'] == "مختلط":
            lang_prompt = "اكتب التعليق باللغة العربية أولاً، ثم اترك سطراً فارغاً، ثم اكتب ترجمته باللغة الإنجليزية تحت العربية."
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب تعليقاً قصيراً بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            model="qwen/qwen3.8-27b",
            max_tokens=500
        )
        ai_text = chat_completion.choices[0].message.content.strip()
        final_caption = f"<b>{ai_text}</b>"
        if settings["add_hashtags"]: final_caption += f"\n\n{settings['hashtags']}"

        post_id = str(int(time.time()))
        pending_posts[post_id] = {'type': 'photo', 'file_id': message.photo[-1].file_id, 'caption': final_caption}
        saved_images[post_id] = message.photo[-1].file_id # حفظ الصورة للبحث عن الأغنية
        
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
            InlineKeyboardButton("البحث عن أغنية", callback_data=f"find_song_{post_id}"),
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
        )
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_message(message.chat.id, f"خطأ: {e}", reply_markup=get_main_panel())

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.from_user.id != ADMIN_ID or message.text.startswith('/'): return
    if settings["text_only_mode"] and settings["status"] == "ON":
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        
        # الترتيب في حالة اللغة المختلطة للنصوص
        if settings['language'] == "مختلط":
            lang_prompt = "اكتب العبارة باللغة العربية أولاً، ثم اترك سطراً فارغاً، ثم اكتب ترجمتها باللغة الإنجليزية تحت العربية."
        else:
            lang_prompt = f"باللغة {settings['language']}"
            
        prompt = f"اكتب عبارة قصيرة بأسلوب {settings['category']} {lang_prompt}. بدون إيموجي."
        
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
            pending_posts[post_id] = {'type': 'text', 'caption': final_caption}
            markup = InlineKeyboardMarkup(row_width=3).add(
                InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
                InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
                InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
            )
            bot.send_message(message.chat.id, f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ: {e}")

print("البوت يعمل...")
bot.infinity_polling()
