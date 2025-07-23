import os
from datetime import datetime

# Bot Configuration
BOT_TOKEN = "7438267281:AAHzn5fuLbWtJWtqtzXV36bN-XM0pD15a14"
ADMIN_ID = 7891142412
ADMIN_USERNAME = "@Officialbgmi24"
UPI_ID = "8435010927@ybl"
CHANNEL_URL = "https://t.me/KyaTereSquadMeinDumHai"
CHANNEL_ID = "2880573048"

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://rahul7241146384:rahul7241146384@cluster0.qeaogc4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "bgmi_tournament_bot"

# AI Configuration
AI_API_KEY = os.getenv("AI_API_KEY", "d96a2478-7fde-4d76-a28d-b8172e561077")

# Tournament Types
TOURNAMENT_TYPES = {
    'solo': 'Solo Tournament',
    'squad': 'Squad Tournament'
}

# Payment Status
PAYMENT_STATUS = {
    'pending': 'Pending',
    'confirmed': 'Confirmed',
    'declined': 'Declined'
}

# Prize Types
PRIZE_TYPES = {
    'kill': 'Kill Based Prize',
    'rank': 'Rank Based Prize'
}

# Bot Messages
WELCOME_MESSAGE = """
🎮 **Welcome to Official BGMI Tournament Manager** 🎮

🔥 Get ready for epic battles and amazing prizes! 🔥

⚠️ **IMPORTANT**: You must join our official channel to continue:
👉 {channel_url}

After joining, click the button below to verify your membership! 👇
"""

MAIN_MENU_MESSAGE = """
🏆 **Welcome to BGMI Tournament Hub** 🏆

Choose an option below:

🎯 **Active Tournaments** - Join ongoing tournaments
📜 **Terms & Conditions** - Read our rules
❓ **Help** - Contact admin support
"""

RULES_MESSAGE = """
📜 **TOURNAMENT RULES**

1️⃣ No emulator players allowed
2️⃣ No teaming, hacking, or glitching
3️⃣ Kill + Rank = Points calculation
4️⃣ Room closes on time. Be punctual!
5️⃣ Follow admin instructions
6️⃣ Respectful behavior required

🚫 **Violation of rules leads to immediate disqualification**
"""

DISCLAIMER_MESSAGE = """
⚠️ **DISCLAIMER**

🚫 No refunds after room details are shared
📶 Admin not responsible for lag/disconnection issues
🔒 Cheaters will be banned permanently
💰 Prize distribution as per tournament rules
✅ By joining, you accept all rules & risks

**Proceed at your own discretion!**
"""

TERMS_CONDITIONS = """
📋 **TERMS & CONDITIONS**

1. **Payment**: Entry fee must be paid before confirmation
2. **Refunds**: No refunds once room details are shared
3. **Fair Play**: Any form of cheating results in ban
4. **Communication**: Official announcements via this bot only
5. **Disputes**: Admin decision is final
6. **Privacy**: Your data is secure with us

By participating, you agree to these terms.
"""
