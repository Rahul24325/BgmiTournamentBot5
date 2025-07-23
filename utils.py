import re
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CHANNEL_URL, ADMIN_USERNAME

def is_admin(user_id, admin_id):
    """Check if user is admin"""
    return user_id == admin_id

def format_currency(amount):
    """Format amount as Indian currency"""
    return f"₹{amount:,.0f}"

def format_datetime(dt):
    """Format datetime for display"""
    return dt.strftime("%d/%m/%Y %I:%M %p")

def validate_upi_id(upi_id):
    """Validate UPI ID format"""
    pattern = r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$'
    return re.match(pattern, upi_id) is not None

def create_main_menu_keyboard():
    """Create main menu inline keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎯 Active Tournaments", callback_data="active_tournaments")],
        [InlineKeyboardButton("📜 Terms & Conditions", callback_data="terms_conditions")],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_channel_join_keyboard():
    """Create channel join verification keyboard"""
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ I've Joined", callback_data="verify_membership")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_tournament_keyboard(tournament_id):
    """Create tournament action keyboard"""
    keyboard = [
        [InlineKeyboardButton("✅ Join Now", callback_data=f"join_tournament_{tournament_id}")],
        [InlineKeyboardButton("📜 Rules", callback_data="rules")],
        [InlineKeyboardButton("⚠️ Disclaimer", callback_data="disclaimer")]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_admin_payment_keyboard(user_id, tournament_id):
    """Create admin payment confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_payment_{user_id}_{tournament_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_payment_{user_id}_{tournament_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_tournament_list_keyboard(tournaments):
    """Create keyboard with list of tournaments"""
    keyboard = []
    for tournament in tournaments:
        tournament_id = str(tournament["_id"])
        name = tournament.get("name", "Unnamed Tournament")
        keyboard.append([InlineKeyboardButton(f"🎮 {name}", callback_data=f"view_tournament_{tournament_id}")])
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("🚫 No Active Tournaments", callback_data="no_tournaments")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def format_tournament_message(tournament):
    """Format tournament details message"""
    name = tournament.get("name", "Unnamed Tournament")
    date = tournament.get("date", "TBD")
    time = tournament.get("time", "TBD")
    entry_fee = tournament.get("entry_fee", 0)
    prize_pool = tournament.get("prize_pool", 0)
    map_name = tournament.get("map", "TBD")
    tournament_type = tournament.get("type", "solo")
    
    message = f"""
🎮 **TOURNAMENT ALERT**

🏆 **{name}**
📅 **Date:** {date}
🕘 **Time:** {time}
📍 **Map:** {map_name}
🎯 **Type:** {tournament_type.title()}
💰 **Entry Fee:** {format_currency(entry_fee)}
🎁 **Prize Pool:** {format_currency(prize_pool)}

👇 **Click to Join**
"""
    return message

def format_payment_request_message(user, tournament, payment_amount):
    """Format payment request message for admin"""
    username = user.get("username", "No username")
    first_name = user.get("first_name", "User")
    tournament_name = tournament.get("name", "Unknown Tournament")
    
    message = f"""
🧾 **PAYMENT REQUEST**

👤 **Player:** @{username} ({first_name})
🎮 **Tournament:** {tournament_name}
💰 **Amount:** {format_currency(payment_amount)}
⏰ **Time:** Just now
🔄 **Status:** Awaiting Confirmation

Use buttons below to approve or decline.
"""
    return message

def format_room_details_message(room_id, room_password, tournament_time):
    """Format room details message"""
    message = f"""
🎮 **ROOM DETAILS**

🆔 **Room ID:** `{room_id}`
🔑 **Password:** `{room_password}`
🕘 **Time:** {tournament_time}

⚠️ **IMPORTANT:**
• Do not share these details
• No refunds after room details are sent
• Be punctual - room closes on time
"""
    return message

def format_winner_announcement(winners_data, tournament_name):
    """Format winner announcement message"""
    message = f"""
🏆 **TOURNAMENT WINNERS**
🎮 **{tournament_name}**

"""
    
    positions = ["🥇", "🥈", "🥉"]
    
    for i, winner in enumerate(winners_data[:3]):
        position = positions[i] if i < len(positions) else f"{i+1}."
        username = winner.get("username", "Unknown")
        points = winner.get("points", 0)
        prize = winner.get("prize", 0)
        
        message += f"{position} @{username} — {points} pts — {format_currency(prize)}\n"
    
    message += "\n🎉 **Congratulations to all winners!**"
    return message

def format_player_list(confirmed_players, users_data):
    """Format confirmed players list"""
    if not confirmed_players:
        return "🚫 No confirmed players yet."
    
    message = "👥 **CONFIRMED PLAYERS**\n\n"
    
    for i, user_id in enumerate(confirmed_players, 1):
        user_data = next((u for u in users_data if u["user_id"] == user_id), None)
        if user_data:
            username = user_data.get("username", "No username")
            first_name = user_data.get("first_name", "User")
            message += f"{i}. @{username} ({first_name})\n"
        else:
            message += f"{i}. User ID: {user_id}\n"
    
    return message

def format_earnings_report(period, total_amount, total_payments):
    """Format earnings report message"""
    period_text = {
        "today": "Today's",
        "week": "This Week's",
        "month": "This Month's"
    }.get(period, "Total")
    
    message = f"""
💰 **{period_text.upper()} EARNINGS REPORT**

💵 **Total Collection:** {format_currency(total_amount)}
📊 **Total Payments:** {total_payments}
📈 **Average per Payment:** {format_currency(total_amount / total_payments if total_payments > 0 else 0)}

📅 **Generated:** {datetime.now().strftime("%d/%m/%Y %I:%M %p")}
"""
    return message

def escape_markdown(text):
    """Escape special characters for Telegram markdown"""
    if not text:
        return ""
    
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def generate_tournament_post(tournament_data):
    """Generate tournament post with AI formatting"""
    try:
        name = tournament_data.get("name", "Epic Tournament")
        date = tournament_data.get("date", "TBD")
        time = tournament_data.get("time", "TBD")
        entry_fee = tournament_data.get("entry_fee", 0)
        prize_pool = tournament_data.get("prize_pool", 0)
        map_name = tournament_data.get("map", "TBD")
        tournament_type = tournament_data.get("type", "solo")
        
        post = f"""
🔥🎮 **TOURNAMENT ALERT** 🎮🔥

🏆 **{name}**
📅 **Date:** {date}
🕘 **Time:** {time}
📍 **Map:** {map_name}
🎯 **Mode:** {tournament_type.title()}
💰 **Entry Fee:** {format_currency(entry_fee)}
🎁 **Prize Pool:** {format_currency(prize_pool)}

⚡ **LIMITED SLOTS AVAILABLE** ⚡

🎯 **How to Join:**
1️⃣ Click "Join Now" button
2️⃣ Pay entry fee via UPI
3️⃣ Send payment screenshot
4️⃣ Get confirmation from admin

🏅 **Prize Distribution:**
🥇 1st Place - 50% of prize pool
🥈 2nd Place - 30% of prize pool  
🥉 3rd Place - 20% of prize pool

⚠️ **Rules & Conditions Apply**

👇 **JOIN NOW** 👇
"""
        return post
        
    except Exception as e:
        return f"Error generating post: {e}"

def create_back_to_menu_keyboard():
    """Create back to menu keyboard"""
    keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)
