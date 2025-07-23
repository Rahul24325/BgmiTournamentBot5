import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from database import db
from utils import (
    create_main_menu_keyboard, 
    create_channel_join_keyboard,
    create_tournament_list_keyboard,
    create_back_to_menu_keyboard,
    format_tournament_message
)
from config import (
    WELCOME_MESSAGE, 
    MAIN_MENU_MESSAGE, 
    RULES_MESSAGE, 
    DISCLAIMER_MESSAGE, 
    TERMS_CONDITIONS,
    CHANNEL_URL,
    CHANNEL_ID,
    ADMIN_USERNAME
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        user = update.effective_user
        
        # Add user to database
        db.add_user(user.id, user.username, user.first_name)
        
        # Check if user is already a member
        user_data = db.get_user(user.id)
        if user_data and user_data.get("is_member", False):
            # User is already a member, show main menu
            await update.message.reply_text(
                MAIN_MENU_MESSAGE,
                reply_markup=create_main_menu_keyboard(),
                parse_mode='Markdown'
            )
        else:
            # User needs to join channel
            welcome_text = WELCOME_MESSAGE.format(channel_url=CHANNEL_URL)
            await update.message.reply_text(
                welcome_text,
                reply_markup=create_channel_join_keyboard(),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        if data == "verify_membership":
            await handle_membership_verification(query, context)
        elif data == "main_menu":
            await show_main_menu(query, context)
        elif data == "active_tournaments":
            await show_active_tournaments(query, context)
        elif data == "terms_conditions":
            await show_terms_conditions(query, context)
        elif data == "help":
            await show_help(query, context)
        elif data == "rules":
            await show_rules(query, context)
        elif data == "disclaimer":
            await show_disclaimer(query, context)
        elif data.startswith("view_tournament_"):
            tournament_id = data.replace("view_tournament_", "")
            await show_tournament_details(query, context, tournament_id)
        elif data.startswith("join_tournament_"):
            tournament_id = data.replace("join_tournament_", "")
            await handle_tournament_join(query, context, tournament_id)
        elif data == "no_tournaments":
            await query.edit_message_text("🚫 No active tournaments available at the moment.")
            
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        try:
            await query.edit_message_text("❌ An error occurred. Please try again.")
        except:
            pass

async def handle_membership_verification(query, context):
    """Verify user channel membership"""
    try:
        user_id = query.from_user.id
        
        # Check if user is member of the channel
        try:
            member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                # User is a member
                db.update_user_membership(user_id, True)
                
                await query.edit_message_text(
                    MAIN_MENU_MESSAGE,
                    reply_markup=create_main_menu_keyboard(),
                    parse_mode='Markdown'
                )
                
                # Send welcome confirmation
                await context.bot.send_message(
                    user_id,
                    "✅ **Membership Verified!**\n\nWelcome to our BGMI Tournament community! 🎮",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    "❌ **Not a member yet!**\n\nPlease join our channel first, then click 'I've Joined'.",
                    reply_markup=create_channel_join_keyboard(),
                    parse_mode='Markdown'
                )
        except TelegramError:
            # User is not a member or channel not accessible
            await query.edit_message_text(
                "❌ **Membership verification failed!**\n\nPlease make sure you've joined our channel and try again.",
                reply_markup=create_channel_join_keyboard(),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in membership verification: {e}")
        await query.edit_message_text("❌ Verification failed. Please try again.")

async def show_main_menu(query, context):
    """Show main menu"""
    await query.edit_message_text(
        MAIN_MENU_MESSAGE,
        reply_markup=create_main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def show_active_tournaments(query, context):
    """Show active tournaments"""
    try:
        tournaments = db.get_active_tournaments()
        
        if not tournaments:
            await query.edit_message_text(
                "🚫 **No Active Tournaments**\n\nThere are no active tournaments at the moment. Check back later!",
                reply_markup=create_back_to_menu_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "🎮 **ACTIVE TOURNAMENTS**\n\nSelect a tournament to view details:",
                reply_markup=create_tournament_list_keyboard(tournaments),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error showing active tournaments: {e}")
        await query.edit_message_text("❌ Error loading tournaments. Please try again.")

async def show_tournament_details(query, context, tournament_id):
    """Show specific tournament details"""
    try:
        tournament = db.get_tournament(tournament_id)
        
        if not tournament:
            await query.edit_message_text(
                "❌ **Tournament Not Found**\n\nThis tournament may have ended or been removed.",
                reply_markup=create_back_to_menu_keyboard(),
                parse_mode='Markdown'
            )
            return
        
        # Format tournament message
        message = format_tournament_message(tournament)
        
        # Create keyboard with join button
        from utils import create_tournament_keyboard
        keyboard = create_tournament_keyboard(tournament_id)
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing tournament details: {e}")
        await query.edit_message_text("❌ Error loading tournament details.")

async def handle_tournament_join(query, context, tournament_id):
    """Handle tournament join request"""
    try:
        user_id = query.from_user.id
        user = query.from_user
        
        # Check if tournament exists
        tournament = db.get_tournament(tournament_id)
        if not tournament:
            await query.edit_message_text("❌ Tournament not found.")
            return
        
        # Check if user already joined
        user_payment = db.get_user_payment(user_id, tournament_id)
        if user_payment:
            status = user_payment.get("status", "pending")
            if status == "confirmed":
                await query.answer("✅ You're already confirmed for this tournament!")
                return
            elif status == "pending":
                await query.answer("⏳ Your payment is pending admin approval.")
                return
        
        # Add user as participant
        db.add_participant(tournament_id, user_id)
        
        # Send payment instructions privately
        entry_fee = tournament.get("entry_fee", 0)
        from config import UPI_ID
        
        payment_message = f"""
💰 **PAYMENT INSTRUCTIONS**

🎮 **Tournament:** {tournament.get("name", "Tournament")}
💵 **Amount:** ₹{entry_fee}
💳 **UPI ID:** `{UPI_ID}`

📱 **Steps:**
1️⃣ Pay ₹{entry_fee} to the UPI ID above
2️⃣ Take a screenshot of payment
3️⃣ Send the screenshot to {ADMIN_USERNAME}
4️⃣ Use /paid command after payment

⚠️ **Important:** Payment confirmation is manual. Please be patient.
"""
        
        try:
            await context.bot.send_message(
                user_id,
                payment_message,
                parse_mode='Markdown'
            )
            
            await query.answer("📱 Payment instructions sent to your private chat!")
            
        except TelegramError:
            # User blocked the bot or chat not available
            await query.edit_message_text(
                f"❌ **Cannot send private message!**\n\nPlease start a private chat with the bot first, then try joining again.\n\n{payment_message}",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error handling tournament join: {e}")
        await query.answer("❌ Error processing join request. Please try again.")

async def show_terms_conditions(query, context):
    """Show terms and conditions"""
    await query.edit_message_text(
        TERMS_CONDITIONS,
        reply_markup=create_back_to_menu_keyboard(),
        parse_mode='Markdown'
    )

async def show_help(query, context):
    """Show help information"""
    help_message = f"""
❓ **HELP & SUPPORT**

For any assistance, contact our admin:
👤 **Admin:** {ADMIN_USERNAME}

📞 **Common Issues:**
• Payment not confirmed: Contact admin with screenshot
• Tournament questions: Ask in admin chat
• Technical issues: Report to admin

⏰ **Response Time:** Usually within 2-4 hours

📱 **Bot Commands:**
• /start - Start the bot
• /paid - Confirm payment made

🔗 **Useful Links:**
• Channel: {CHANNEL_URL}
• Admin: {ADMIN_USERNAME}
"""
    
    await query.edit_message_text(
        help_message,
        reply_markup=create_back_to_menu_keyboard(),
        parse_mode='Markdown'
    )

async def show_rules(query, context):
    """Show tournament rules"""
    await query.edit_message_text(
        RULES_MESSAGE,
        reply_markup=create_back_to_menu_keyboard(),
        parse_mode='Markdown'
    )

async def show_disclaimer(query, context):
    """Show disclaimer"""
    await query.edit_message_text(
        DISCLAIMER_MESSAGE,
        reply_markup=create_back_to_menu_keyboard(),
        parse_mode='Markdown'
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again or contact support."
            )
    except:
        pass
