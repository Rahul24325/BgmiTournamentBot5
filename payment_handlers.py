import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils import (
    is_admin, 
    format_payment_request_message,
    create_admin_payment_keyboard
)
from config import ADMIN_ID, ADMIN_USERNAME

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def paid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /paid command"""
    try:
        user = update.effective_user
        user_id = user.id
        
        # Check if user has any pending payments
        user_data = db.get_user(user_id)
        if not user_data:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        # Get active tournaments user has joined
        active_tournaments = db.get_active_tournaments()
        user_tournaments = []
        
        for tournament in active_tournaments:
            if user_id in tournament.get("participants", []):
                payment = db.get_user_payment(user_id, str(tournament["_id"]))
                if not payment:
                    user_tournaments.append(tournament)
        
        if not user_tournaments:
            await update.message.reply_text(
                "❌ **No pending payments found**\n\nYou haven't joined any tournaments or have already submitted payment confirmation.",
                parse_mode='Markdown'
            )
            return
        
        # If multiple tournaments, ask user to specify
        if len(user_tournaments) > 1:
            tournament_list = "\n".join([f"• {t.get('name', 'Unnamed')}" for t in user_tournaments])
            await update.message.reply_text(
                f"📋 **Multiple tournaments found:**\n\n{tournament_list}\n\nPlease contact {ADMIN_USERNAME} and specify which tournament payment you've made.",
                parse_mode='Markdown'
            )
            return
        
        # Single tournament - process payment confirmation
        tournament = user_tournaments[0]
        tournament_id = str(tournament["_id"])
        entry_fee = tournament.get("entry_fee", 0)
        
        # Add payment request to database
        payment_id = db.add_payment_request(user_id, tournament_id, entry_fee)
        
        if payment_id:
            # Notify admin
            await notify_admin_payment_request(context, user, tournament, entry_fee)
            
            await update.message.reply_text(
                "✅ **Payment confirmation submitted!**\n\n⏳ Your payment is now pending admin approval.\n📱 You'll be notified once confirmed.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Error submitting payment confirmation. Please try again.")
            
    except Exception as e:
        logger.error(f"Error in paid_command: {e}")
        await update.message.reply_text("❌ An error occurred. Please contact admin.")

async def notify_admin_payment_request(context, user, tournament, amount):
    """Notify admin about payment request"""
    try:
        user_data = {
            "username": user.username or "no_username",
            "first_name": user.first_name or "User"
        }
        
        message = format_payment_request_message(user_data, tournament, amount)
        keyboard = create_admin_payment_keyboard(user.id, str(tournament["_id"]))
        
        await context.bot.send_message(
            ADMIN_ID,
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")

async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment confirmation by admin"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await query.answer("❌ Unauthorized access!")
            return
        
        data = query.data
        
        if data.startswith("confirm_payment_"):
            parts = data.replace("confirm_payment_", "").split("_")
            if len(parts) >= 2:
                target_user_id = int(parts[0])
                tournament_id = parts[1]
                await confirm_payment(query, context, target_user_id, tournament_id)
                
        elif data.startswith("decline_payment_"):
            parts = data.replace("decline_payment_", "").split("_")
            if len(parts) >= 2:
                target_user_id = int(parts[0])
                tournament_id = parts[1]
                await decline_payment(query, context, target_user_id, tournament_id)
                
    except Exception as e:
        logger.error(f"Error in payment confirmation: {e}")
        await query.edit_message_text("❌ Error processing payment confirmation.")

async def confirm_payment(query, context, target_user_id, tournament_id):
    """Confirm user payment"""
    try:
        # Update payment status
        result = db.update_payment_status(target_user_id, tournament_id, "confirmed")
        
        if result.modified_count > 0:
            # Add user to confirmed players
            db.confirm_participant(tournament_id, target_user_id)
            
            # Get tournament details
            tournament = db.get_tournament(tournament_id)
            tournament_name = tournament.get("name", "Tournament") if tournament else "Tournament"
            
            # Notify user
            try:
                await context.bot.send_message(
                    target_user_id,
                    f"✅ **Payment Confirmed!**\n\n🎮 You're confirmed for **{tournament_name}**\n\n🏠 Room details will be shared before match time.\n\n🎯 Good luck!",
                    parse_mode='Markdown'
                )
            except:
                logger.warning(f"Could not notify user {target_user_id}")
            
            # Update admin message
            await query.edit_message_text(
                f"✅ **Payment Confirmed**\n\n👤 User ID: {target_user_id}\n🎮 Tournament: {tournament_name}\n⏰ Confirmed at: Just now",
                parse_mode='Markdown'
            )
            
        else:
            await query.edit_message_text("❌ Error confirming payment. Payment may not exist.")
            
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        await query.edit_message_text("❌ Error processing confirmation.")

async def decline_payment(query, context, target_user_id, tournament_id):
    """Decline user payment"""
    try:
        # Update payment status
        result = db.update_payment_status(target_user_id, tournament_id, "declined")
        
        if result.modified_count > 0:
            # Get tournament details
            tournament = db.get_tournament(tournament_id)
            tournament_name = tournament.get("name", "Tournament") if tournament else "Tournament"
            
            # Notify user
            try:
                await context.bot.send_message(
                    target_user_id,
                    f"❌ **Payment Declined**\n\n🎮 Tournament: **{tournament_name}**\n\n📞 Please contact {ADMIN_USERNAME} for assistance.\n\n💡 Make sure you've sent the correct payment screenshot.",
                    parse_mode='Markdown'
                )
            except:
                logger.warning(f"Could not notify user {target_user_id}")
            
            # Update admin message
            await query.edit_message_text(
                f"❌ **Payment Declined**\n\n👤 User ID: {target_user_id}\n🎮 Tournament: {tournament_name}\n⏰ Declined at: Just now",
                parse_mode='Markdown'
            )
            
        else:
            await query.edit_message_text("❌ Error declining payment. Payment may not exist.")
            
    except Exception as e:
        logger.error(f"Error declining payment: {e}")
        await query.edit_message_text("❌ Error processing decline.")

async def confirm_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /confirm @username command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        
        # Parse command arguments
        args = context.args
        if not args:
            await update.message.reply_text("❌ Usage: /confirm @username")
            return
        
        username = args[0].replace("@", "")
        
        # Find user by username
        # Note: MongoDB doesn't have a direct way to search by username efficiently
        # This is a simplified approach - in production, consider indexing usernames
        all_users = list(db.users.find({"username": username}))
        
        if not all_users:
            await update.message.reply_text(f"❌ User @{username} not found.")
            return
        
        target_user = all_users[0]
        target_user_id = target_user["user_id"]
        
        # Get active tournaments for this user
        active_tournaments = db.get_active_tournaments()
        user_tournaments = []
        
        for tournament in active_tournaments:
            if target_user_id in tournament.get("participants", []):
                payment = db.get_user_payment(target_user_id, str(tournament["_id"]))
                if payment and payment.get("status") == "pending":
                    user_tournaments.append(tournament)
        
        if not user_tournaments:
            await update.message.reply_text(f"❌ No pending payments found for @{username}.")
            return
        
        # Confirm payment for the first pending tournament
        tournament = user_tournaments[0]
        tournament_id = str(tournament["_id"])
        
        # Update payment status
        db.update_payment_status(target_user_id, tournament_id, "confirmed")
        db.confirm_participant(tournament_id, target_user_id)
        
        # Notify user
        try:
            await context.bot.send_message(
                target_user_id,
                f"✅ **Payment Confirmed!**\n\n🎮 You're confirmed for **{tournament.get('name', 'Tournament')}**\n\nRoom details will be shared before match time.",
                parse_mode='Markdown'
            )
        except:
            pass
        
        await update.message.reply_text(f"✅ Payment confirmed for @{username}")
        
    except Exception as e:
        logger.error(f"Error in confirm_user_command: {e}")
        await update.message.reply_text("❌ Error processing confirmation.")

async def decline_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /decline @username command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        
        # Parse command arguments
        args = context.args
        if not args:
            await update.message.reply_text("❌ Usage: /decline @username")
            return
        
        username = args[0].replace("@", "")
        
        # Find user by username
        all_users = list(db.users.find({"username": username}))
        
        if not all_users:
            await update.message.reply_text(f"❌ User @{username} not found.")
            return
        
        target_user = all_users[0]
        target_user_id = target_user["user_id"]
        
        # Get active tournaments for this user
        active_tournaments = db.get_active_tournaments()
        user_tournaments = []
        
        for tournament in active_tournaments:
            if target_user_id in tournament.get("participants", []):
                payment = db.get_user_payment(target_user_id, str(tournament["_id"]))
                if payment and payment.get("status") == "pending":
                    user_tournaments.append(tournament)
        
        if not user_tournaments:
            await update.message.reply_text(f"❌ No pending payments found for @{username}.")
            return
        
        # Decline payment for the first pending tournament
        tournament = user_tournaments[0]
        tournament_id = str(tournament["_id"])
        
        # Update payment status
        db.update_payment_status(target_user_id, tournament_id, "declined")
        
        # Notify user
        try:
            await context.bot.send_message(
                target_user_id,
                f"❌ **Payment Declined**\n\n🎮 Tournament: **{tournament.get('name', 'Tournament')}**\n\nPlease contact {ADMIN_USERNAME} for assistance.",
                parse_mode='Markdown'
            )
        except:
            pass
        
        await update.message.reply_text(f"❌ Payment declined for @{username}")
        
    except Exception as e:
        logger.error(f"Error in decline_user_command: {e}")
        await update.message.reply_text("❌ Error processing decline.")
