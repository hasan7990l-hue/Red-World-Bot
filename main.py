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
ADMIN_ID = 8456056018 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

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

# ================= 1. الترحيب =================
@bot.message_handler(commands=['start', 'panel'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = get_default_settings()

    welcome_text = (
        f"<b>⟨ مرحباً بك في R W | Bot ⟩</b>\n"
        f"<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n"
        f"هذا البوت مخصص لإدارة قنوات تيليجرام باحترافية.\n"
        f"لإضافة البوت لقناتك، اضغط على الزر أدناه واختر قناتك.\n\n"
        f"<i>ملاحظة: تأكد من إعطاء البوت صلاحية 'نشر الرسائل' كـ مشرف.</i>"
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("إضافة البوت لقناتك", url=f"https://t.me/{bot.get_me().username}?startchannel=true"))
    markup.add(InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='HTML')

# ================= 2. لوحة التحكم =================
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
        InlineKeyboardButton("توليد عبارة مستقلة", callback_data="generate_text"),
        InlineKeyboardButton("السورس", callback_data="show_source")
    )
    return markup

# ================= 3. معالجة الأزرار =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    settings = user_settings.get(user_id, get_default_settings())

    if call.data == "main_menu":
        main_text = "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:"
        if call.message.content_type == 'photo':
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            bot.send_message(call.message.chat.id, main_text, reply_markup=get_main_panel(user_id), parse_mode='HTML')
        else:
            bot.edit_message_text(main_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_main_panel(user_id), parse_mode='HTML')
        return bot.answer_callback_query(call.id)

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

    elif call.data == "generate_text":
        bot.answer_callback_query(call.id, text="جاري التوليد...", show_alert=False)
        if settings['language'] == "مختلط":
            lang_prompt = "اكتب العبارة باللغة العربية أولاً، ثم اترك سطراً فارغاً، ثم اكتب ترجمتها باللغة الإنجليزية تحت العربية."
        else:
            lang_prompt = f"باللغة {settings['language']}"

        prompt = f"اكتب عبارة قصيرة جداً بأسلوب {settings['category']} {lang_prompt} تناسب قناة اسمها {bot.get_me().first_name}. بدون إيموجي."
        
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
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"خطأ: {e}")

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
            
            # نطلب من المستخدم اختيار القناة
            bot.edit_message_text("⏳ جاري البحث عن قنواتك...", chat_id=call.message.chat.id, message_id=call.message.message_id)
            find_and_show_channels(call.message.chat.id, post_id, 'text', None, final_text)
            return bot.answer_callback_query(call.id, text="جاري البحث", show_alert=False)

        else:
            if action == "bold": data["bold"] = not data["bold"]
            elif action == "italic": data["italic"] = not data["italic"]
            elif action == "strike": data["strike"] = not data["strike"]
            elif action == "quote": data["quote"] = not data["quote"]
            new_text = apply_formatting(data)
            markup = get_formatting_panel_markup(data, msg_id)
            bot.edit_message_text(f"معاينة النص:\n\n{new_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode='HTML')
            return bot.answer_callback_query(call.id, text="تم التحديث", show_alert=False)

    # اختيار القناة
    elif call.data.startswith("select_channel_"):
        parts = call.data.split("_")
        channel_id = parts[2]
        post_id = parts[3]
        
        if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية")
        data = pending_posts[post_id]
        
        try:
            if data['type'] == 'photo': bot.send_photo(channel_id, data['file_id'], caption=data['caption'], parse_mode='HTML')
            else: bot.send_message(channel_id, data['caption'], parse_mode='HTML')
            
            try: bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            
            bot.answer_callback_query(call.id, text="تم النشر في القناة", show_alert=False)
            bot.send_message(call.message.chat.id, "<b>مرحباً بك في لوحة التحكم</b>\n\nاختر الإجراء الذي تريده:", reply_markup=get_main_panel(user_id), parse_mode='HTML')
            del pending_posts[post_id]
        except Exception as e: bot.answer_callback_query(call.id, f"خطأ: {e}")

# ================= 4. البحث عن القنوات =================
def find_and_show_channels(chat_id, post_id, post_type, file_id, caption):
    # في البوتات، لا يمكن جلب قائمة القنوات مباشرة إلا إذا كان البوت مشرفاً فيها
    # كحل بديل، نطلب من المستخدم إرسال معرف القناة (الرابط) أو إعادة إضافة البوت
    # لكن لجعلها تعمل تلقائياً، سنستخدم طريقة "طلب الرابط"
    
    prompt_text = (
        "<b>لم نتمكن من العثور على قناتك تلقائياً.</b>\n\n"
        "يرجى إرسال رابط قناتك (مثال: @MyChannel) لكي ننشر فيها:"
    )
    msg = bot.send_message(chat_id, prompt_text, parse_mode='HTML')
    bot.register_next_step_handler(msg, process_channel_link, post_id, post_type, file_id, caption)

def process_channel_link(message, post_id, post_type, file_id, caption):
    channel_username = message.text.strip()
    if not channel_username.startswith('@'):
        channel_username = '@' + channel_username
        
    try:
        # التحقق من أن البوت مشرف في القناة
        chat_info = bot.get_chat(channel_username)
        bot_member = bot.get_chat_member(channel_username, bot.get_me().id)
        
        if bot_member.status in ['administrator', 'creator']:
            # البوت مشرف، يمكنه النشر
            if post_type == 'photo': bot.send_photo(channel_username, file_id, caption=caption, parse_mode='HTML')
            else: bot.send_message(channel_username, caption, parse_mode='HTML')
            
            bot.reply_to(message, "✅ تم النشر في القناة بنجاح!")
        else:
            bot.reply_to(message, "⚠️ البوت ليس مشرفاً في هذه القناة. يرجى إضافته كمشرف أولاً.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: تأكد من أن الرابط صحيح وأن البوت مشرف في القناة.\nالسبب: {e}")

# ================= 5. استقبال الصور =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, get_default_settings())
    
    if settings["status"] == "OFF": return bot.send_message(message.chat.id, "معطل.", reply_markup=get_main_panel(user_id))

    msg_loading = bot.send_message(message.chat.id, "جاري التحليل...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
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
        
        # عرض المعاينة مع خيارات النشر
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("تحديد القناة والنشر", callback_data=f"ask_channel_{post_id}"))
        markup.add(InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}"))
        
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_message(message.chat.id, f"خطأ: {e}", reply_markup=get_main_panel(user_id))

# ================= 6. طلب القناة =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("ask_channel_"))
def ask_channel(call):
    post_id = call.data.split("_")[2]
    if post_id not in pending_posts: return bot.answer_callback_query(call.id, "انتهت الصلاحية")
    data = pending_posts[post_id]
    
    find_and_show_channels(call.message.chat.id, post_id, data['type'], data.get('file_id'), data['caption'])
    bot.answer_callback_query(call.id)

# ================= 7. الدوال المساعدة =================
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

print("البوت العام يعمل...")
bot.infinity_polling()
