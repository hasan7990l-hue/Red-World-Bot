import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
import time
import base64
import datetime
import threading
import json
import os

# ================= الإعدادات =================
TELEGRAM_TOKEN = '8386513995:AAH6GWopP1_8jWCVZvUj_Yix1pjYNt_zGts'
GROQ_API_KEY = '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'
ADMIN_ID = 8456056018 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

DB_FILE = "user_channels.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

user_channels = load_db()

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
        f"هذا البوت مخصص لإدارة قنوات تيليجرام باحترافية.\n\n"
        f"<b>الخطوات:</b>\n"
        f"1. أضف البوت إلى قناتك (كـ مشرف).\n"
        f"2. ارجع هنا واضغط على زر (التحقق من الرفع).\n"
        f"3. ابدأ بإرسال الصور أو النصوص."
    )
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("1. إضافة البوت لقناتك", url=f"https://t.me/{bot.get_me().username}?startchannel=true"))
    markup.add(InlineKeyboardButton("2. التحقق من الرفع (فحص تلقائي)", callback_data="verify_channel"))
    markup.add(InlineKeyboardButton("المبرمج", url=f"tg://user?id={ADMIN_ID}"))
    
    # زر لوحة التحكم يظهر فقط إذا كان المستخدم قد تحقق مسبقاً أو كان المالك
    if user_id == ADMIN_ID or str(user_id) in user_channels:
        markup.add(InlineKeyboardButton("فتح لوحة التحكم", callback_data="main_menu"))

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode='HTML')

# ================= 2. التحقق التلقائي =================
@bot.callback_query_handler(func=lambda call: call.data == "verify_channel")
def verify_channel(call):
    user_id = call.from_user.id
    channel_id = user_channels.get(str(user_id))
    
    if not channel_id:
        return bot.answer_callback_query(call.id, "⚠️ لم يتم العثور على القناة. يرجى إزالة البوت من القناة وإضافته مرة أخرى يدوياً (وليس من خلال الرابط).", show_alert=True)

    msg_loading = bot.send_message(call.message.chat.id, "⏳ جاري فحص القناة والصلاحيات...")

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
            bot.edit_message_text(success_text, chat_id=call.message.chat.id, message_id=msg_loading.message_id, reply_markup=markup, parse_mode='HTML')
            bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح!")
        else:
            bot.edit_message_text("❌ البوت موجود في القناة، لكنه لا يملك صلاحية 'نشر الرسائل'. يرجى تعديل صلاحيات البوت في القناة والمحاولة مرة أخرى.", chat_id=call.message.chat.id, message_id=msg_loading.message_id)
            
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ: {e}", chat_id=call.message.chat.id, message_id=msg_loading.message_id)

# ================= 3. حفظ القناة تلقائياً عند إضافتها =================
@bot.message_handler(content_types=['new_chat_members'])
def bot_added_to_channel(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            adder_id = message.from_user.id
            channel_identifier = f"@{message.chat.username}" if message.chat.username else str(message.chat.id)
            
            user_channels[str(adder_id)] = channel_identifier
            save_db(user_channels)
            
            text = (
                f"✅ <b>تمت إضافة البوت إلى القناة:</b> {message.chat.title}\n\n"
                f"تم حفظ القناة. يرجى العودة للبوت والضغط على (التحقق من الرفع) لفتح لوحة التحكم."
            )
            try: bot.send_message(adder_id, text, parse_mode='HTML')
            except: pass

# ================= 4. لوحة التحكم =================
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

# ================= 5. القفل الأمني (لا يُسمح بالمرور بدون تحقق) =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    # التحقق من القفل: إذا لم يكن مالكاً ولم يتم التحقق من قناته
    if user_id != ADMIN_ID and str(user_id) not in user_channels:
        # استثناء زر التحقق وزر الإضافة
        if call.data not in ["verify_channel", "main_menu"]:
            return bot.answer_callback_query(call.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت في قناتك أولاً لتتمكن من استخدام الأزرار.", show_alert=True)

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
            if data['type'] == 'photo': bot.send_photo(target_channel, data['file_id'], caption=data['caption'], parse_mode='HTML')
            else: bot.send_message(target_channel, data['caption'], parse_mode='HTML')
            
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

# ================= 6. استقبال الصور مع القفل الأمني =================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    # القفل الأمني
    if user_id != ADMIN_ID and str(user_id) not in user_channels:
        return bot.send_message(message.chat.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت في قناتك أولاً لتتمكن من إرسال الصور.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel")))

    settings = user_settings.get(user_id, get_default_settings())
    target_channel = user_channels.get(str(user_id))

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
        pending_posts[post_id] = {'type': 'photo', 'file_id': message.photo[-1].file_id, 'caption': final_caption, 'channel': target_channel}
        
        markup = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
            InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
            InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
        )
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_photo(message.chat.id, photo=message.photo[-1].file_id, caption=f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
    except Exception as e:
        bot.delete_message(message.chat.id, msg_loading.message_id)
        bot.send_message(message.chat.id, f"خطأ: {e}", reply_markup=get_main_panel(user_id))

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    settings = user_settings.get(user_id, get_default_settings())
    
    if message.text.startswith('/'): return
    
    # القفل الأمني
    if user_id != ADMIN_ID and str(user_id) not in user_channels:
        return bot.send_message(message.chat.id, "⛔ عذراً، يجب عليك التحقق من رفع البوت في قناتك أولاً.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("التحقق من الرفع", callback_data="verify_channel")))
    
    if settings["text_only_mode"] and settings["status"] == "ON":
        target_channel = user_channels.get(str(user_id))
            
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        
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
            pending_posts[post_id] = {'type': 'text', 'caption': final_caption, 'channel': target_channel}
            markup = InlineKeyboardMarkup(row_width=3).add(
                InlineKeyboardButton("نشر الآن", callback_data=f"confirm_{post_id}"), 
                InlineKeyboardButton("جدولة", callback_data=f"schedule_{post_id}"), 
                InlineKeyboardButton("إلغاء", callback_data=f"cancel_{post_id}")
            )
            bot.send_message(message.chat.id, f"<b>معاينة:</b>\n\n{final_caption}", reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"خطأ: {e}")

# ================= 7. لوحات مساعدة =================
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
            else: bot.send_message(target_channel, data['caption'], parse_mode='HTML')
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
