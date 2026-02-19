import telebot
from telebot import types
import json
import os
import time
import openpyxl  # Excel রিড করার জন্য লাইব্রেরি

# --- CONFIGURATION ---
BOT_TOKEN = '8146777195:AAHGE_1mAIxxYWB-Mu_fNkZOkwLDqdwmg_k'
ADMIN_ID = 6343266992  
DATA_FILE = 'bot_data_final.json'

bot = telebot.TeleBot(BOT_TOKEN)

# --- DATA MANAGEMENT ---
default_data = {
    "users": {},
    "stock_items": {
        "gmail": [],
        "hotmail": [],
        "outlook": [],
        "edu": []
    },
    "prices": {
        "gmail": 6.0,
        "hotmail": 1.0,
        "outlook": 1.0,
        "edu": 3.0
    },
    "pay_bkash": "01xxxxxxxxx (Send Money)",
    "pay_rocket": "01xxxxxxxxx (Send Money)",
    "pay_binance": "Pay ID: xxxxxxxx",
    "deposit_on": True,
    "notification_on": True,
    "exchange_rate": 124.0,  # 1 USD = 124 BDT (Added for Binance)
    
    # --- PAYMENT STATUS & SEPARATE LIMITS ---
    "pay_status": {
        "bKash": True,
        "Rocket": True,
        "Binance": True
    },
    "limits": {
        "bKash": {"min": 50.0, "max": 25000.0},
        "Rocket": {"min": 50.0, "max": 25000.0},
        "Binance": {"min": 0.10, "max": 1000.0} # Binance Limit in USD
    }
}

# গ্লোবাল ভেরিয়েবল স্টক আপলোড ট্র্যাকিং এর জন্য
admin_state = {} 

def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(default_data)
        return default_data
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            d = json.load(f)
            # Ensure keys exist
            if "stock_items" not in d: d["stock_items"] = {k: [] for k in ["gmail", "hotmail", "outlook", "edu"]}
            if "deposit_on" not in d: d["deposit_on"] = True
            if "exchange_rate" not in d: d["exchange_rate"] = 124.0
            if "pay_bkash" not in d: d["pay_bkash"] = default_data["pay_bkash"]
            if "pay_rocket" not in d: d["pay_rocket"] = default_data["pay_rocket"]
            if "pay_binance" not in d: d["pay_binance"] = default_data["pay_binance"]
            if "pay_status" not in d: d["pay_status"] = default_data["pay_status"]
            
            # --- MIGRATION FOR SEPARATE LIMITS ---
            if "limits" not in d or "min_deposit" in d["limits"]:
                d["limits"] = default_data["limits"]
            
            return d
    except:
        return default_data

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving data: {e}")

data = load_data()

# --- HELPER FUNCTIONS ---

def register_user_if_new(user):
    user_id = str(user.id)
    first_name = user.first_name
    username = user.username if user.username else "No Username"
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "balance": 0.0, 
            "banned": False, 
            "name": first_name,
            "username": username
        }
        save_data(data)
        if data.get('notification_on', True):
            try:
                safe_name = first_name.replace("_", "\\_").replace("*", "\\*")
                msg = (f"👤 **New User Joined!**\n\n"
                       f"👤 User: [{safe_name}](tg://user?id={user_id})\n"
                       f"🆔 ID: `{user_id}`\n"
                       f"👤 Username: @{username}\n"
                       f"💰 Balance: 0.0 TK")
                bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
            except: pass
    else:
        data["users"][user_id]["name"] = first_name
        data["users"][user_id]["username"] = username
        save_data(data)

def get_user_data(user_id):
    return data["users"].get(str(user_id))

def is_banned(user_id):
    user = get_user_data(user_id)
    if user:
        return user.get("banned", False)
    return False

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def get_stock_count(item_type):
    return len(data['stock_items'].get(item_type, []))

def send_ban_message(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 Owner", url="https://t.me/King_ABIR_FF"))
    msg_text = ("⚠️ **Access Denied!**\n\n"
                "দুঃখিত, আপনাকে অ্যাডমিন প্যানেল থেকে **ব্যান (Banned)** করা হয়েছে।")
    bot.reply_to(message, msg_text, parse_mode="Markdown", reply_markup=markup)

# --- FORMATTING FUNCTION ---
def format_delivery_message(item_type, account_string):
    account_string = account_string.strip()
    if item_type in ['hotmail', 'outlook']:
        try:
            if '|' in account_string: email = account_string.split('|')[0].strip()
            elif ':' in account_string: email = account_string.split(':')[0].strip()
            else: email = account_string.split()[0].strip()
        except: email = "Account"
        return (f"📧 Mail\n`{email}`\n\n📧 Details:\n`{account_string}`")
    elif item_type in ['gmail', 'edu']:
        email = account_string
        password = "Check Full Details"
        delimiters = [':', '|', ' ']
        for d in delimiters:
            if d in account_string:
                parts = account_string.split(d, 1)
                email = parts[0].strip()
                password = parts[1].strip()
                break
        return (f"📧 Mail\n`{email}`\n\n🔑 Pass:\n`{password}`")
    else:
        return f"📧 {item_type.capitalize()}: `{account_string}`"

# --- KEYBOARDS ---
def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📮 Get Mail", "💳 Balance")
    markup.add("💲 Deposit", "🗣️ Price")
    markup.add("☎️ Support")
    if is_admin(user_id):
        markup.add("👑 Admin Panel")
    return markup

def cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("❌ Cancel")
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btns = [
        "📊 Stats", "📤 Upload Stock",
        "🗑️ Remove Stock", 
        "🔨 Ban User", "🔓 Unban User",
        "🚫 Banned List", "👥 All Users",
        "💰 Add Balance", "💸 Remove Balance",
        "📢 Broadcast", "✏️ Edit Price", 
        "⚙️ Pay Settings", "✏️ Set Payment Info", # Added Button Here
        "🔌 Control Deposit",
        "🔙 Back to Menu"
    ]
    markup.add(*[types.KeyboardButton(b) for b in btns])
    return markup

def back_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("🔙 Back")
    return markup

def item_select_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    markup.add("gmail", "hotmail", "outlook", "edu")
    markup.add("🔙 Back")
    return markup

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    register_user_if_new(message.from_user)
    if is_banned(message.from_user.id):
        send_ban_message(message)
        return
    bot.reply_to(message, f"Welcome {message.from_user.first_name}! \nসার্ভিস সিলেক্ট করুন।", reply_markup=main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "❌ Cancel")
def handle_global_cancel(message):
    if is_admin(message.from_user.id):
        admin_state.pop(message.from_user.id, None) # Clear admin state
    bot.reply_to(message, "❌ Cancelled", reply_markup=main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text == "📮 Get Mail")
def get_mail_menu(message):
    if is_banned(message.from_user.id): 
        send_ban_message(message)
        return

    p = data['prices']
    s_gmail = get_stock_count('gmail')
    s_hotmail = get_stock_count('hotmail')
    s_outlook = get_stock_count('outlook')
    s_edu = get_stock_count('edu')

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"📧 FB Gmail ({s_gmail} pcs) - {p['gmail']} TK", callback_data="ask_gmail"),
        types.InlineKeyboardButton(f"📧 Hotmail ({s_hotmail} pcs) - {p['hotmail']} TK", callback_data="ask_hotmail"),
        types.InlineKeyboardButton(f"📧 Outlook ({s_outlook} pcs) - {p['outlook']} TK", callback_data="ask_outlook"),
        types.InlineKeyboardButton(f"📧 Edu Mail ({s_edu} pcs) - {p['edu']} TK", callback_data="ask_edu")
    )
    bot.reply_to(message, "যে মেইলটি কিনতে চান তা সিলেক্ট করুন:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💳 Balance")
def show_balance(message):
    if is_banned(message.from_user.id): 
        send_ban_message(message)
        return
    user = get_user_data(message.from_user.id)
    if not user: return 
    text = (f"💳 Balance: {user['balance']:.2f} TK\n\n"
            f"Gmail Stock: {get_stock_count('gmail')}\n"
            f"Hotmail Stock: {get_stock_count('hotmail')}\n"
            f"Outlook Stock: {get_stock_count('outlook')}\n"
            f"Edu Stock: {get_stock_count('edu')}")
    bot.reply_to(message, text)

@bot.message_handler(func=lambda m: m.text == "🗣️ Price")
def show_price(message):
    if is_banned(message.from_user.id): 
        send_ban_message(message)
        return
    p = data['prices']
    text = (f"💵 **Current Price List:**\n"
            f"Gmail: {p['gmail']} TK\n"
            f"Hotmail: {p['hotmail']} TK\n"
            f"Outlook: {p['outlook']} TK\n"
            f"Edu Mail: {p['edu']} TK")
    bot.reply_to(message, text, parse_mode="Markdown")

# --- ADVANCED DEPOSIT SYSTEM ---

@bot.message_handler(func=lambda m: m.text == "💲 Deposit")
def deposit_info_menu(message):
    if is_banned(message.from_user.id): 
        send_ban_message(message)
        return
    if not data.get('deposit_on', True):
        bot.reply_to(message, "⚠️ **দুঃখিত!**\nবর্তমানে ডিপোজিট সিস্টেম সাময়িকভাবে বন্ধ আছে।", parse_mode="Markdown")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    s_bkash = "✅" if data['pay_status']['bKash'] else "❌ (OFF)"
    s_rocket = "✅" if data['pay_status']['Rocket'] else "❌ (OFF)"
    s_binance = "✅" if data['pay_status']['Binance'] else "❌ (OFF)"
    
    btn_bkash = types.InlineKeyboardButton(f"🟣 bKash {s_bkash}", callback_data="dep_sel_bKash")
    btn_rocket = types.InlineKeyboardButton(f"🚀 Rocket {s_rocket}", callback_data="dep_sel_Rocket")
    btn_binance = types.InlineKeyboardButton(f"🔶 Binance {s_binance}", callback_data="dep_sel_Binance")
    
    markup.add(btn_bkash, btn_rocket)
    markup.add(btn_binance)
    
    bot.reply_to(message, "💲 **পেমেন্ট মেথড সিলেক্ট করুন:**", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('dep_sel_'))
def handle_deposit_selection(call):
    if is_banned(call.from_user.id): return
    method = call.data.split('_')[2]
    
    if not data['pay_status'].get(method, True):
        bot.answer_callback_query(call.id, f"⚠️ {method} payment is currently OFF.", show_alert=True)
        return
    
    pay_details = ""
    if method == "bKash": pay_details = data.get("pay_bkash", "Not Set")
    elif method == "Rocket": pay_details = data.get("pay_rocket", "Not Set")
    elif method == "Binance": pay_details = data.get("pay_binance", "Not Set")
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Get Specific Limits
    min_dep = data['limits'][method]['min']
    
    # Logic for Binance vs Others
    if method == "Binance":
        msg_text = (f"💳 **Method:** {method}\n"
                    f"📝 **Details:** `{pay_details}`\n\n"
                    f"💱 **Exchange Rate:** 1 USD = {data.get('exchange_rate', 124)} BDT\n"
                    f"⚠️ Minimum Deposit: **${min_dep}**\n\n"
                    f"💰 **আপনি কত ডলার (USD) সেন্ড করেছেন?**\n(যেমন: 0.10 বা 5)")
    else:
        msg_text = (f"💳 **Method:** {method}\n"
                    f"📝 **Details:** `{pay_details}`\n\n"
                    f"⚠️ Minimum Deposit: **{min_dep} TK**\n"
                    f"⚠️ উপরের নাম্বারে টাকা পাঠিয়ে নিচে টাকার পরিমাণ লিখুন।\n\n"
                    f"💰 **আপনি কত টাকা ডিপোজিট করেছেন?**")
    
    msg = bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(msg, process_deposit_amount, method)

def process_deposit_amount(message, method):
    if message.text == "❌ Cancel":
        bot.send_message(message.chat.id, "❌ Deposit Cancelled", reply_markup=main_keyboard(message.from_user.id))
        return
    
    try:
        amount = float(message.text)
        # Check Specific Limits
        min_limit = data['limits'][method]['min']
        max_limit = data['limits'][method]['max']
        
        # Currency Symbol Logic
        currency = "$" if method == "Binance" else "TK"
        
        if amount < min_limit:
            bot.reply_to(message, f"⚠️ **দুঃখিত!**\nসর্বনিম্ন ডিপোজিট: **{min_limit} {currency}**\nএর কম ডিপোজিট গ্রহণ করা হয় না।", reply_markup=cancel_keyboard())
            msg = bot.send_message(message.chat.id, "সঠিক পরিমাণ লিখুন (অথবা Cancel করুন):")
            bot.register_next_step_handler(msg, process_deposit_amount, method)
            return
            
        if amount > max_limit:
            bot.reply_to(message, f"⚠️ **দুঃখিত!**\nসর্বোচ্চ ডিপোজিট: **{max_limit} {currency}**\nএর বেশি একবারে ডিপোজিট করা যাবে না।", reply_markup=cancel_keyboard())
            msg = bot.send_message(message.chat.id, "সঠিক পরিমাণ লিখুন (অথবা Cancel করুন):")
            bot.register_next_step_handler(msg, process_deposit_amount, method)
            return
            
    except:
        msg = bot.send_message(message.chat.id, "❌ ভুল ইনপুট! দয়া করে শুধু সংখ্যা লিখুন (যেমন: 0.10 বা 100):", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_deposit_amount, method)
        return

    msg = bot.send_message(message.chat.id, "🔎 **Enter Transaction ID:**\n(নিচে ট্রানজেকশন আইডি লিখুন)", parse_mode="Markdown", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(msg, process_deposit_trx, method, amount)

def process_deposit_trx(message, method, amount):
    if message.text == "❌ Cancel":
        bot.send_message(message.chat.id, "❌ Deposit Cancelled", reply_markup=main_keyboard(message.from_user.id))
        return
        
    trx_id = message.text.strip()
    
    msg = bot.send_message(message.chat.id, 
                           "📸 **Send Screenshot**\n\n"
                           "Please send the screenshot of the successful payment for verification.\n"
                           "(Send it as a **Photo**, not a document)", 
                           parse_mode="Markdown", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(msg, process_deposit_proof, method, amount, trx_id)

def process_deposit_proof(message, method, amount, trx_id):
    if message.text == "❌ Cancel":
        bot.send_message(message.chat.id, "❌ Deposit Cancelled", reply_markup=main_keyboard(message.from_user.id))
        return

    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ দয়া করে **Photo** আকারে স্ক্রিনশট দিন।", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_deposit_proof, method, amount, trx_id)
        return

    bot.send_message(message.chat.id, "✅ **Request Submitted!**\nঅ্যাডমিন চেক করে অ্যাপ্রুভ করলে ব্যালেন্স যোগ হয়ে যাবে।", parse_mode="Markdown", reply_markup=main_keyboard(message.from_user.id))

    file_id = message.photo[-1].file_id
    user = message.from_user
    uid = user.id
    
    safe_first_name = user.first_name.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    
    # Binance Logic for Admin Calculation
    final_credit_amount = amount
    amount_display = f"{amount} TK"
    
    if method == "Binance":
        rate = data.get('exchange_rate', 124.0)
        final_credit_amount = round(amount * rate, 2)
        amount_display = (f"💵 USD: ${amount}\n"
                          f"💱 Rate: 1$ = {rate} TK\n"
                          f"🇧🇩 Credit: **{final_credit_amount} TK**")
    
    caption = (f"🔔 **New Deposit Request!**\n\n"
               f"👤 User: [{safe_first_name}](tg://user?id={uid})\n"
               f"🆔 UID: `{uid}`\n"
               f"💳 Method: {method}\n"
               f"{amount_display}\n"
               f"🧾 TrxID: `{trx_id}`")
    
    markup = types.InlineKeyboardMarkup()
    # Pass the calculated BDT amount in callback
    btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"d_app_{uid}_{final_credit_amount}")
    btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"d_rej_{uid}")
    markup.add(btn_approve, btn_reject)
    
    try:
        bot.send_photo(ADMIN_ID, file_id, caption=caption, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        print(f"Markdown Error: {e}")
        try:
            plain_caption = caption.replace('*', '').replace('`', '').replace('\\', '').replace('[', '').replace(']', '').replace(f"(tg://user?id={uid})", "")
            bot.send_photo(ADMIN_ID, file_id, caption=plain_caption, reply_markup=markup)
        except Exception as e2:
            print(f"Final Error: {e2}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('d_'))
def handle_deposit_decision(call):
    try:
        data_parts = call.data.split('_')
        action = data_parts[1] 
        uid_str = data_parts[2]
        
        original_caption = call.message.caption if call.message.caption else "Deposit Request"

        if action == "app":
            amount = float(data_parts[3]) # This is now the Converted BDT amount for Binance
            if uid_str in data['users']:
                data['users'][uid_str]['balance'] += amount
                save_data(data)
                
                try:
                    bot.edit_message_caption(f"{original_caption}\n\n✅ APPROVED by Admin", 
                                            call.message.chat.id, call.message.message_id)
                except Exception as e:
                    print(f"Edit Error: {e}")
                
                try:
                    bot.send_message(uid_str, 
                                     f"✅ **Deposit Approved!**\n\n"
                                     f"💰 Added: {amount} TK\n"
                                     f"💳 New Balance: {data['users'][uid_str]['balance']} TK\n"
                                     f"ধন্যবাদ আমাদের সাথে থাকার জন্য।", parse_mode="Markdown")
                except: pass
            else:
                bot.answer_callback_query(call.id, "User not found in DB!")

        elif action == "rej":
            try:
                bot.edit_message_caption(f"{original_caption}\n\n❌ REJECTED by Admin", 
                                         call.message.chat.id, call.message.message_id)
            except: pass
            try:
                bot.send_message(uid_str, "❌ **Deposit Rejected!**\nআপনার দেওয়া তথ্য সঠিক নয় অথবা টাকা পাওয়া যায়নি।", parse_mode="Markdown")
            except: pass
            
    except Exception as e:
        print(f"Callback Error: {e}")
        bot.answer_callback_query(call.id, "Error processing request")

# --- OTHER HANDLERS ---

@bot.message_handler(func=lambda m: m.text == "☎️ Support")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👤 Owner", url="https://t.me/King_ABIR_FF"),
               types.InlineKeyboardButton("🔉 Channel", url="https://t.me/+BGFQjLrPS5IwMTll"))
    bot.reply_to(message, "📞 Contact Support:", reply_markup=markup)

# --- BUYING FLOW ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('ask_'))
def handle_buy_click(call):
    if is_banned(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 You are BANNED!", show_alert=True)
        return
    item_type = call.data.split('_')[1] 
    user_id = str(call.from_user.id)
    user = get_user_data(user_id)
    if not user:
        register_user_if_new(call.from_user)
        user = get_user_data(user_id)
    unit_price = data['prices'][item_type]
    if get_stock_count(item_type) <= 0:
        bot.answer_callback_query(call.id, "Stock Not Available ⚠️", show_alert=True)
        return
    if user['balance'] < unit_price:
        bot.answer_callback_query(call.id, "Insufficient Balance ❌", show_alert=True)
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("❌ Cancel")
    msg = bot.send_message(call.message.chat.id, 
                     f"🔢 আপনি কয়টি **{item_type}** নিতে চান?\n(সংখ্যা লিখুন, যেমন: 1, 5, 10)", 
                     parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(msg, process_quantity, item_type)

def process_quantity(message, item_type):
    if message.text == "❌ Cancel":
        bot.send_message(message.chat.id, "❌ Cancelled", reply_markup=main_keyboard(message.from_user.id))
        return
    if message.text.startswith('/'): return 
    try:
        qty = int(message.text)
        if qty <= 0: raise ValueError
    except:
        bot.reply_to(message, "❌ ভুল ইনপুট। দয়া করে শুধু সংখ্যা লিখুন।")
        msg = bot.send_message(message.chat.id, "সংখ্যা লিখুন (যেমন: 1, 5):")
        bot.register_next_step_handler(msg, process_quantity, item_type)
        return
    available = get_stock_count(item_type)
    if qty > available:
        bot.reply_to(message, f"❌ পর্যাপ্ত স্টক নেই। বর্তমানে আছে: {available} টি।", reply_markup=main_keyboard(message.from_user.id))
        return
    unit_price = data['prices'][item_type]
    total_cost = unit_price * qty
    user = get_user_data(message.from_user.id)
    if user['balance'] < total_cost:
        bot.reply_to(message, f"❌ অপর্যাপ্ত ব্যালেন্স।\nপ্রয়োজন: {total_cost} TK\nআছে: {user['balance']} TK", reply_markup=main_keyboard(message.from_user.id))
        return
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ হ্যাঁ (Confirm)", callback_data=f"confirm_{item_type}_{qty}")
    btn_no = types.InlineKeyboardButton("❌ না (Cancel)", callback_data="cancel_buy")
    markup.add(btn_yes, btn_no)
    bot.send_message(message.chat.id, "🔄 Processing...", reply_markup=types.ReplyKeyboardRemove())
    bot.send_message(message.chat.id, 
                 f"📝 **অর্ডার কনফার্মেশন:**\n\n"
                 f"📦 আইটেম: {item_type}\n"
                 f"🔢 পরিমাণ: {qty} টি\n"
                 f"💰 মোট দাম: {total_cost} TK\n"
                 f"💳 বর্তমান ব্যালেন্স: {user['balance']} TK\n\n"
                 f"আপনি কি কিনতে চান?", 
                 reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def execute_purchase(call):
    if is_banned(call.from_user.id):
        bot.answer_callback_query(call.id, "Banned!", show_alert=True)
        return
    try:
        _, item_type, qty_str = call.data.split('_')
        qty = int(qty_str)
        user_id = str(call.from_user.id)
        user = data['users'].get(user_id)
        unit_price = data['prices'][item_type]
        total_cost = unit_price * qty
        
        # Final Verification
        if user['balance'] < total_cost:
            bot.answer_callback_query(call.id, "Insufficient Balance ❌", show_alert=True)
            return
        if get_stock_count(item_type) < qty:
            bot.answer_callback_query(call.id, "Stock Out ❌", show_alert=True)
            return
            
        data['users'][user_id]['balance'] -= total_cost
        accounts_to_give = data['stock_items'][item_type][:qty]
        data['stock_items'][item_type] = data['stock_items'][item_type][qty:]
        save_data(data)
        
        formatted_accounts = [format_delivery_message(item_type, acc) for acc in accounts_to_give]
        final_msg_body = "\n\n➖➖➖➖➖➖➖➖➖➖\n\n".join(formatted_accounts)
        
        delivery_msg = (f"✅ **Purchase Successful!**\n"
                        f"🔢 Quantity: {qty}\n"
                        f"💰 Total Cost: {total_cost} TK\n\n"
                        f"{final_msg_body}")
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, delivery_msg, parse_mode="Markdown", reply_markup=main_keyboard(call.from_user.id))
        
        if data['notification_on']:
            try:
                safe_name = call.from_user.first_name.replace("_", "\\_").replace("*", "\\*")
                msg = (f"🔔 **New Sale!**\n"
                       f"👤 User: [{safe_name}](tg://user?id={user_id})\n"
                       f"📦 Item: {item_type} x{qty}\n"
                       f"💰 Amount: {total_cost} TK\n"
                       f"🆔 UID: `{user_id}`")
                bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
            except: pass
            
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_buy")
def cancel_buy(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "❌ Cancelled")
    bot.send_message(call.message.chat.id, "❌ Order Cancelled", reply_markup=main_keyboard(call.from_user.id))

# --- ADMIN FUNCTIONS ---
@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_p(m): 
    if is_admin(m.from_user.id): bot.reply_to(m, "👑 **Admin Panel:**", reply_markup=admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔙 Back to Menu")
def back(m): bot.reply_to(m, "Main Menu", reply_markup=main_keyboard(m.from_user.id))

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def back_admin(m): 
    if is_admin(m.from_user.id): bot.reply_to(m, "🔙 Returned to Admin Panel", reply_markup=admin_keyboard())

# --- REMOVE STOCK FEATURE ---
@bot.message_handler(func=lambda m: m.text == "🗑️ Remove Stock")
def remove_stock_menu(m):
    if not is_admin(m.from_user.id): return
    msg = bot.reply_to(m, "কোন ক্যাটাগরির স্টক ডিলিট করতে চান?", reply_markup=item_select_keyboard())
    bot.register_next_step_handler(msg, ask_remove_confirmation)

def ask_remove_confirmation(m):
    if m.text == "🔙 Back": return admin_p(m)
    item_type = m.text
    if item_type in data['stock_items']:
        count = len(data['stock_items'][item_type])
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(f"✅ Delete All {count} Items", "🔙 Cancel")
        msg = bot.reply_to(m, f"⚠️ **WARNING:**\n\nCategory: {item_type}\nTotal Items: {count}\n\nআপনি কি সত্যি সব স্টক ডিলিট করতে চান?", parse_mode="Markdown", reply_markup=markup)
        bot.register_next_step_handler(msg, execute_remove_stock, item_type)
    else:
        bot.reply_to(m, "❌ ভুল ক্যাটাগরি।", reply_markup=admin_keyboard())

def execute_remove_stock(m, item_type):
    if m.text.startswith("✅ Delete"):
        data['stock_items'][item_type] = []
        save_data(data)
        bot.reply_to(m, f"✅ {item_type} এর সব স্টক ডিলিট করা হয়েছে।", reply_markup=admin_keyboard())
    else:
        bot.reply_to(m, "❌ Cancelled.", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔌 Control Deposit")
def control_deposit_menu(m):
    if not is_admin(m.from_user.id): return
    current_status = "✅ ON" if data.get('deposit_on', True) else "❌ OFF"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Turn ON", callback_data="dep_sys_on"),
               types.InlineKeyboardButton("❌ Turn OFF", callback_data="dep_sys_off"))
    bot.reply_to(m, f"🔌 **Deposit Control**\nStatus: {current_status}", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('dep_sys_'))
def handle_dep_toggle(call):
    if not is_admin(call.from_user.id): return
    data['deposit_on'] = (call.data == "dep_sys_on")
    save_data(data)
    status = "ON" if data['deposit_on'] else "OFF"
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, f"Deposit System is now **{status}**.", parse_mode="Markdown")

# --- ADMIN PAYMENT SETTINGS (UPDATED WITH METHOD SELECTION) ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Pay Settings")
def pay_settings_menu(m):
    if not is_admin(m.from_user.id): return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    s_bk = "✅" if data['pay_status']['bKash'] else "❌"
    s_rk = "✅" if data['pay_status']['Rocket'] else "❌"
    s_bn = "✅" if data['pay_status']['Binance'] else "❌"
    
    markup.add(types.InlineKeyboardButton(f"bKash {s_bk}", callback_data="tog_bKash"),
               types.InlineKeyboardButton(f"Rocket {s_rk}", callback_data="tog_Rocket"),
               types.InlineKeyboardButton(f"Binance {s_bn}", callback_data="tog_Binance"))
    
    markup.add(types.InlineKeyboardButton("🔧 Set Limits (bKash)", callback_data="lim_bKash"),
               types.InlineKeyboardButton("🔧 Set Limits (Rocket)", callback_data="lim_Rocket"),
               types.InlineKeyboardButton("🔧 Set Limits (Binance)", callback_data="lim_Binance"))
    
    bot.reply_to(m, "⚙️ **Payment Settings:**\n\nON/OFF এবং আলাদা লিমিট সেট করতে নিচের বাটন ব্যবহার করুন।", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('tog_'))
def toggle_payment_method(call):
    if not is_admin(call.from_user.id): return
    method = call.data.split('_')[1]
    
    data['pay_status'][method] = not data['pay_status'][method]
    save_data(data)
    
    s_bk = "✅" if data['pay_status']['bKash'] else "❌"
    s_rk = "✅" if data['pay_status']['Rocket'] else "❌"
    s_bn = "✅" if data['pay_status']['Binance'] else "❌"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(f"bKash {s_bk}", callback_data="tog_bKash"),
               types.InlineKeyboardButton(f"Rocket {s_rk}", callback_data="tog_Rocket"),
               types.InlineKeyboardButton(f"Binance {s_bn}", callback_data="tog_Binance"))
    markup.add(types.InlineKeyboardButton("🔧 Set Limits (bKash)", callback_data="lim_bKash"),
               types.InlineKeyboardButton("🔧 Set Limits (Rocket)", callback_data="lim_Rocket"),
               types.InlineKeyboardButton("🔧 Set Limits (Binance)", callback_data="lim_Binance"))
    
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lim_'))
def handle_limit_menu(call):
    if not is_admin(call.from_user.id): return
    method = call.data.split('_')[1]
    
    cur_min = data['limits'][method]['min']
    cur_max = data['limits'][method]['max']
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(f"⬇️ Min: {cur_min}", callback_data=f"setmin_{method}"),
               types.InlineKeyboardButton(f"⬆️ Max: {cur_max}", callback_data=f"setmax_{method}"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Settings", callback_data="back_pay_set"))
    
    bot.edit_message_text(f"🔧 **{method} Limits:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_pay_set")
def back_pay_set(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    pay_settings_menu(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set'))
def handle_limit_input(call):
    if not is_admin(call.from_user.id): return
    action, method = call.data.split('_') # action=setmin, method=bKash
    
    limit_type = "min" if "min" in action else "max"
    
    msg = bot.send_message(call.message.chat.id, f"📝 **Set {limit_type.upper()} Limit for {method}:**\n\nনতুন অ্যামাউন্ট লিখুন:", reply_markup=back_keyboard())
    bot.register_next_step_handler(msg, save_deposit_limit, method, limit_type)

def save_deposit_limit(m, method, limit_type):
    if m.text == "🔙 Back": return admin_p(m)
    try:
        val = float(m.text)
        if val < 0: raise ValueError
        
        data['limits'][method][limit_type] = val
        save_data(data)
        bot.reply_to(m, f"✅ {method} {limit_type.capitalize()} Limit set to {val} TK", reply_markup=admin_keyboard())
    except:
        bot.reply_to(m, "❌ ভুল ইনপুট।", reply_markup=admin_keyboard())

# --- ADMIN SET PAYMENT INFO ---
@bot.message_handler(func=lambda m: m.text == "✏️ Set Payment Info")
def set_payment_menu(m):
    if not is_admin(m.from_user.id): return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("bKash", "Rocket", "Binance", "🔙 Back")
    bot.reply_to(m, "কোন মেথড এডিট করবেন?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["bKash", "Rocket", "Binance"])
def set_payment_ask(m):
    if not is_admin(m.from_user.id): return
    method_map = {"bKash": "pay_bkash", "Rocket": "pay_rocket", "Binance": "pay_binance"}
    key = method_map[m.text]
    msg = bot.reply_to(m, f"📝 **{m.text}** এর নতুন নাম্বার/ডিটেইলস লিখুন:", reply_markup=back_keyboard())
    bot.register_next_step_handler(msg, save_payment_info, key)

def save_payment_info(m, key):
    if m.text == "🔙 Back": return admin_p(m)
    data[key] = m.text
    save_data(data)
    bot.reply_to(m, "✅ Payment Details Updated!", reply_markup=admin_keyboard())

# --- REST OF ADMIN ---

@bot.message_handler(func=lambda m: m.text == "👥 All Users")
def all_users(message):
    if not is_admin(message.from_user.id): return
    msg_buffer = "👥 **All Users List:**\n\n"
    for uid, udata in data['users'].items():
        line = f"🆔 `{uid}` | {udata.get('name')} | {udata.get('balance')} TK\n"
        if len(msg_buffer) + len(line) > 4000:
            bot.send_message(message.chat.id, msg_buffer, parse_mode="Markdown")
            msg_buffer = ""
        msg_buffer += line
    if msg_buffer: bot.send_message(message.chat.id, msg_buffer, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🚫 Banned List")
def show_banned_list(message):
    if not is_admin(message.from_user.id): return
    msg_buffer = "🚫 **Banned Users List:**\n\n"
    found = False
    for uid, udata in data['users'].items():
        if udata.get('banned', False):
            found = True
            line = f"🆔 `{uid}` | 👤 Name: {udata.get('name', 'Unknown')}\n"
            msg_buffer += line
    if found: bot.send_message(message.chat.id, msg_buffer, parse_mode="Markdown")
    else: bot.reply_to(message, "✅ Currently, there are no banned users.")

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
def broadcast_step1(m):
    if not is_admin(m.from_user.id): return
    msg = bot.reply_to(m, "📢 ব্রডকাস্ট মেসেজটি লিখুন:", reply_markup=back_keyboard())
    bot.register_next_step_handler(msg, broadcast_step2)

def broadcast_step2(m):
    if m.text == "🔙 Back": return admin_p(m)
    count, failed = 0, 0
    status = bot.reply_to(m, "⏳ Sending Broadcast...")
    for uid in data['users']:
        try:
            bot.send_message(uid, f"📢 **NOTICE:**\n\n{m.text}", parse_mode="Markdown")
            count += 1
            time.sleep(0.05)
        except: failed += 1
    bot.edit_message_text(f"✅ Sent: {count}\n❌ Failed: {failed}", m.chat.id, status.message_id)

@bot.message_handler(func=lambda m: m.text == "✏️ Edit Price")
def edit_price_menu(m):
    if not is_admin(m.from_user.id): return
    msg = bot.reply_to(m, "কোন আইটেমের দাম পরিবর্তন করতে চান?", reply_markup=item_select_keyboard())
    bot.register_next_step_handler(msg, edit_price_ask)

def edit_price_ask(m):
    if m.text == "🔙 Back": return admin_p(m)
    item = m.text
    if item in data['prices']:
        msg = bot.reply_to(m, f"💰 {item} এর নতুন দাম লিখুন:", reply_markup=back_keyboard())
        bot.register_next_step_handler(msg, lambda tm: edit_price_save(tm, item))
    else: bot.reply_to(m, "❌ ভুল আইটেম।", reply_markup=admin_keyboard())

def edit_price_save(m, item):
    if m.text == "🔙 Back": return admin_p(m)
    try:
        data['prices'][item] = float(m.text)
        save_data(data)
        bot.reply_to(m, f"✅ {item} Price Updated to {m.text} TK.", reply_markup=admin_keyboard())
    except: bot.reply_to(m, "❌ ভুল ভ্যালু।", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def admin_stats(m):
    if not is_admin(m.from_user.id): return
    total_users = len(data['users'])
    stock = "\n".join([f"{k.capitalize()}: {len(v)} pcs" for k, v in data['stock_items'].items()])
    bot.reply_to(m, f"👥 Total Users: {total_users}\n\n📦 **Current Stock:**\n{stock}", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔨 Ban User")
def ban_user(m):
    if is_admin(m.from_user.id):
        msg = bot.reply_to(m, "User ID দিন:", reply_markup=back_keyboard())
        bot.register_next_step_handler(msg, lambda tm: toggle_ban(tm, True))

@bot.message_handler(func=lambda m: m.text == "🔓 Unban User")
def unban_user(m):
    if is_admin(m.from_user.id):
        msg = bot.reply_to(m, "User ID দিন:", reply_markup=back_keyboard())
        bot.register_next_step_handler(msg, lambda tm: toggle_ban(tm, False))

def toggle_ban(m, status):
    if m.text == "🔙 Back": return admin_p(m)
    uid = m.text.strip()
    if uid in data['users']:
        data['users'][uid]['banned'] = status
        save_data(data)
        bot.reply_to(m, f"✅ User {'Banned' if status else 'Unbanned'} Successfully.", reply_markup=admin_keyboard())
        try:
            if status:
                bot.send_message(uid, "🚫 **Account Alert**\n\nআপনাকে অ্যাডমিন প্যানেল থেকে **ব্যান (Banned)** করা হয়েছে।")
            else:
                bot.send_message(uid, "✅ **Account Alert**\n\nআপনার অ্যাকাউন্ট **আনব্যান (Unbanned)** করা হয়েছে।")
        except: pass 
    else: 
        bot.reply_to(m, "❌ User Not Found.", reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "💰 Add Balance")
def add_bal(m):
    if is_admin(m.from_user.id): ask_user_id_balance(m, 1)

@bot.message_handler(func=lambda m: m.text == "💸 Remove Balance")
def rem_bal(m):
    if is_admin(m.from_user.id): ask_user_id_balance(m, -1)

def ask_user_id_balance(message, multiplier):
    msg = bot.reply_to(message, "👤 ব্যবহারকারীর ID দিন:", reply_markup=back_keyboard())
    bot.register_next_step_handler(msg, process_balance_user_id, multiplier)

def process_balance_user_id(message, multiplier):
    if message.text == "🔙 Back": return admin_p(message)
    user_id = message.text.strip()
    if user_id not in data['users']:
        bot.reply_to(message, "🚫 ইউজার পাওয়া যায়নি!", reply_markup=back_keyboard())
        return
    msg = bot.reply_to(message, f"💵 কত টাকা {'যোগ' if multiplier > 0 else 'বিয়োগ'} করবেন?", reply_markup=back_keyboard())
    bot.register_next_step_handler(msg, process_balance_amount, user_id, multiplier)

def process_balance_amount(message, user_id, multiplier):
    if message.text == "🔙 Back": return admin_p(message)
    try:
        amount = float(message.text.strip())
        added_amount = amount * multiplier
        data['users'][user_id]['balance'] += added_amount
        save_data(data)
        bot.reply_to(message, f"✅ সফল! বর্তমান ব্যালেন্স: {data['users'][user_id]['balance']} TK", reply_markup=admin_keyboard())
        try:
            if multiplier > 0:
                user_msg = (f"💰 **Balance Added!**\n\n➕ Added: {amount} TK\n💳 New Balance: {data['users'][user_id]['balance']} TK")
            else:
                user_msg = (f"💸 **Balance Deducted!**\n\n➖ Removed: {amount} TK\n💳 New Balance: {data['users'][user_id]['balance']} TK")
            bot.send_message(user_id, user_msg, parse_mode="Markdown")
        except: pass
    except: bot.reply_to(message, "❌ ভুল সংখ্যা।", reply_markup=admin_keyboard())

# --- STOCK UPLOAD (UPDATED WITH EXCEL) ---
@bot.message_handler(func=lambda m: m.text == "📤 Upload Stock")
def up_stock(m):
    if is_admin(m.from_user.id):
        bot.register_next_step_handler(bot.reply_to(m, "কোন আইটেম আপলোড করবেন?", reply_markup=item_select_keyboard()), ask_up_method)

def ask_up_method(m):
    if m.text == "🔙 Back": return admin_p(m)
    item = m.text
    if item in data['stock_items']:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Paste List", "📂 Upload Excel") # Added Option
        markup.add("🔙 Back")
        bot.register_next_step_handler(bot.reply_to(m, "পদ্ধতি সিলেক্ট করুন:", reply_markup=markup), lambda tm: process_up(tm, item))

def process_up(m, item):
    if m.text == "🔙 Back": return admin_p(m)
    
    if m.text == "Paste List":
        bot.register_next_step_handler(bot.reply_to(m, "📜 লিস্ট পেস্ট করুন:", reply_markup=back_keyboard()), lambda tm: save_st(tm, item))
    elif m.text == "📂 Upload Excel":
        admin_state[m.from_user.id] = item # Store item type
        bot.reply_to(m, "📂 **Excel File (.xlsx)** সেন্ড করুন:", reply_markup=back_keyboard())
    else:
        bot.reply_to(m, "❌ ভুল কমান্ড।", reply_markup=admin_keyboard())

# Excel Handler
@bot.message_handler(content_types=['document'])
def handle_excel_upload(message):
    if not is_admin(message.from_user.id): return
    if message.from_user.id not in admin_state: return

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = f"temp_{message.from_user.id}.xlsx"
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        item_type = admin_state[message.from_user.id]
        workbook = openpyxl.load_workbook(file_name)
        sheet = workbook.active
        
        new_items = []
        
        # Parse Logic
        for row in sheet.iter_rows(min_row=1, values_only=True):
            if not row: continue
            
            # Hotmail/Outlook: Column A only
            if item_type in ['hotmail', 'outlook']:
                if row[0]: new_items.append(str(row[0]).strip())
            
            # Gmail/Edu: Column A (Email) + Column B (Pass)
            elif item_type in ['gmail', 'edu']:
                if len(row) >= 2 and row[0] and row[1]:
                    combined = f"{str(row[0]).strip()}:{str(row[1]).strip()}"
                    new_items.append(combined)
        
        # Cleanup
        workbook.close()
        os.remove(file_name)
        admin_state.pop(message.from_user.id) # Clear state
        
        if new_items:
            data['stock_items'][item_type].extend(new_items)
            save_data(data)
            bot.reply_to(message, f"✅ Excel থেকে {len(new_items)} টি আইটেম যোগ করা হয়েছে!", reply_markup=admin_keyboard())
        else:
            bot.reply_to(message, "⚠️ কোনো ডেটা পাওয়া যায়নি বা ফরম্যাট ভুল ছিল।", reply_markup=admin_keyboard())
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}", reply_markup=admin_keyboard())

def save_st(m, item):
    if m.text == "🔙 Back": return admin_p(m)
    new_items = [l.strip() for l in m.text.split('\n') if len(l.strip()) > 5]
    if new_items:
        data['stock_items'][item].extend(new_items)
        save_data(data)
        bot.reply_to(m, f"✅ {len(new_items)} টি আইটেম যোগ করা হয়েছে।", reply_markup=admin_keyboard())
    else: bot.reply_to(m, "⚠️ সঠিক ফরম্যাট দিন।", reply_markup=admin_keyboard())

print("Bot Started with Excel Upload & Binance USD Conversion...")
bot.infinity_polling)
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=10000)

def bot_thread():
    bot.infinity_polling()

threading.Thread(target=bot_thread).start()

if __name__ == "__main__":
    run()
