import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from utils import (
    is_admin, 
    format_room_details_message,
    format_winner_announcement,
    format_player_list,
    format_earnings_report
)
from config import ADMIN_ID, CHANNEL_ID

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states for room details
ROOM_ID_INPUT, ROOM_PASSWORD_INPUT = range(2)

# Conversation states for winner declaration
FIRST_PLACE, SECOND_PLACE, THIRD_PLACE = range(3)

class RoomSender:
    def __init__(self):
        self.tournament_id = None
        self.room_id = None
        self.room_password = None

class WinnerDeclaration:
    def __init__(self):
        self.tournament_id = None
        self.winners = []

async def send_room_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sendroom command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return ConversationHandler.END
        
        # Get active tournaments
        tournaments = db.get_active_tournaments()
        
        if not tournaments:
            await update.message.reply_text("❌ No active tournaments found.")
            return ConversationHandler.END
        
        # Create tournament selection keyboard
        keyboard = []
        for tournament in tournaments:
            tournament_id = str(tournament["_id"])
            name = tournament.get("name", "Unnamed Tournament")
            confirmed_count = len(tournament.get("confirmed_players", []))
            keyboard.append([
                InlineKeyboardButton(
                    f"🎮 {name} ({confirmed_count} players)", 
                    callback_data=f"select_tournament_room_{tournament_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎮 **Select Tournament to Send Room Details:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in send_room_command: {e}")
        await update.message.reply_text("❌ Error starting room details process.")
        return ConversationHandler.END

async def handle_tournament_room_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tournament selection for room details"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("select_tournament_room_"):
            tournament_id = data.replace("select_tournament_room_", "")
            
            # Initialize room sender
            context.user_data['room_sender'] = RoomSender()
            context.user_data['room_sender'].tournament_id = tournament_id
            
            tournament = db.get_tournament(tournament_id)
            if not tournament:
                await query.edit_message_text("❌ Tournament not found.")
                return
            
            await query.edit_message_text(
                f"🎮 **Tournament:** {tournament.get('name', 'Unknown')}\n\n🆔 Please enter the Room ID:",
                parse_mode='Markdown'
            )
            
            return ROOM_ID_INPUT
            
    except Exception as e:
        logger.error(f"Error in handle_tournament_room_selection: {e}")
        await query.edit_message_text("❌ Error processing tournament selection.")
        return ConversationHandler.END

async def get_room_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get room ID input"""
    try:
        room_id = update.message.text.strip()
        
        if not room_id:
            await update.message.reply_text("❌ Please enter a valid Room ID:")
            return ROOM_ID_INPUT
        
        context.user_data['room_sender'].room_id = room_id
        
        await update.message.reply_text(
            f"✅ Room ID: **{room_id}**\n\n🔑 Please enter the Room Password:",
            parse_mode='Markdown'
        )
        
        return ROOM_PASSWORD_INPUT
        
    except Exception as e:
        logger.error(f"Error in get_room_id: {e}")
        await update.message.reply_text("❌ Error processing Room ID.")
        return ConversationHandler.END

async def get_room_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get room password and send details to all confirmed players"""
    try:
        room_password = update.message.text.strip()
        
        if not room_password:
            await update.message.reply_text("❌ Please enter a valid Room Password:")
            return ROOM_PASSWORD_INPUT
        
        room_sender = context.user_data['room_sender']
        tournament_id = room_sender.tournament_id
        room_id = room_sender.room_id
        
        # Get tournament details
        tournament = db.get_tournament(tournament_id)
        if not tournament:
            await update.message.reply_text("❌ Tournament not found.")
            return ConversationHandler.END
        
        confirmed_players = tournament.get("confirmed_players", [])
        
        if not confirmed_players:
            await update.message.reply_text("❌ No confirmed players found for this tournament.")
            return ConversationHandler.END
        
        # Format room details message
        tournament_time = f"{tournament.get('date', 'TBD')} at {tournament.get('time', 'TBD')}"
        room_message = format_room_details_message(room_id, room_password, tournament_time)
        
        # Send room details to all confirmed players
        sent_count = 0
        failed_count = 0
        
        for user_id in confirmed_players:
            try:
                await context.bot.send_message(
                    user_id,
                    room_message,
                    parse_mode='Markdown'
                )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send room details to user {user_id}: {e}")
                failed_count += 1
        
        # Update tournament with room details
        db.update_tournament(tournament_id, {
            "room_id": room_id,
            "room_password": room_password,
            "room_details_sent": True
        })
        
        # Send confirmation to admin
        confirmation_message = f"""
✅ **Room Details Sent Successfully!**

🎮 **Tournament:** {tournament.get('name', 'Unknown')}
🆔 **Room ID:** {room_id}
🔑 **Password:** {room_password}

📊 **Delivery Status:**
✅ Sent to: {sent_count} players
❌ Failed: {failed_count} players

⚠️ **Important:** No refunds will be given after room details are shared.
"""
        
        await update.message.reply_text(
            confirmation_message,
            parse_mode='Markdown'
        )
        
        # Clean up conversation data
        if 'room_sender' in context.user_data:
            del context.user_data['room_sender']
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in get_room_password: {e}")
        await update.message.reply_text("❌ Error sending room details.")
        return ConversationHandler.END

async def list_players_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /listplayers command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        
        # Get active tournaments
        tournaments = db.get_active_tournaments()
        
        if not tournaments:
            await update.message.reply_text("❌ No active tournaments found.")
            return
        
        # Create tournament selection keyboard
        keyboard = []
        for tournament in tournaments:
            tournament_id = str(tournament["_id"])
            name = tournament.get("name", "Unnamed Tournament")
            confirmed_count = len(tournament.get("confirmed_players", []))
            keyboard.append([
                InlineKeyboardButton(
                    f"👥 {name} ({confirmed_count} players)", 
                    callback_data=f"list_players_{tournament_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👥 **Select Tournament to View Players:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in list_players_command: {e}")
        await update.message.reply_text("❌ Error retrieving player list.")

async def handle_list_players(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle player list display"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("list_players_"):
            tournament_id = data.replace("list_players_", "")
            
            tournament = db.get_tournament(tournament_id)
            if not tournament:
                await query.edit_message_text("❌ Tournament not found.")
                return
            
            confirmed_players = tournament.get("confirmed_players", [])
            
            if not confirmed_players:
                await query.edit_message_text(
                    f"🎮 **{tournament.get('name', 'Tournament')}**\n\n🚫 No confirmed players yet.",
                    parse_mode='Markdown'
                )
                return
            
            # Get user data for confirmed players
            users_data = []
            for user_id in confirmed_players:
                user_data = db.get_user(user_id)
                if user_data:
                    users_data.append(user_data)
            
            player_list = format_player_list(confirmed_players, users_data)
            
            await query.edit_message_text(
                f"🎮 **{tournament.get('name', 'Tournament')}**\n\n{player_list}",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in handle_list_players: {e}")
        await query.edit_message_text("❌ Error displaying player list.")

async def declare_winners_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /declarewinners command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return ConversationHandler.END
        
        # Get active tournaments
        tournaments = db.get_active_tournaments()
        
        if not tournaments:
            await update.message.reply_text("❌ No active tournaments found.")
            return ConversationHandler.END
        
        # Create tournament selection keyboard
        keyboard = []
        for tournament in tournaments:
            tournament_id = str(tournament["_id"])
            name = tournament.get("name", "Unnamed Tournament")
            keyboard.append([
                InlineKeyboardButton(
                    f"🏆 {name}", 
                    callback_data=f"declare_winners_{tournament_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏆 **Select Tournament to Declare Winners:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in declare_winners_command: {e}")
        await update.message.reply_text("❌ Error starting winner declaration.")
        return ConversationHandler.END

async def handle_winner_tournament_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tournament selection for winner declaration"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("declare_winners_"):
            tournament_id = data.replace("declare_winners_", "")
            
            # Initialize winner declaration
            context.user_data['winner_declaration'] = WinnerDeclaration()
            context.user_data['winner_declaration'].tournament_id = tournament_id
            
            tournament = db.get_tournament(tournament_id)
            if not tournament:
                await query.edit_message_text("❌ Tournament not found.")
                return
            
            await query.edit_message_text(
                f"🏆 **Tournament:** {tournament.get('name', 'Unknown')}\n\n🥇 Please enter 1st place details:\nFormat: @username points prize_amount\nExample: @player1 25 500",
                parse_mode='Markdown'
            )
            
            return FIRST_PLACE
            
    except Exception as e:
        logger.error(f"Error in handle_winner_tournament_selection: {e}")
        await query.edit_message_text("❌ Error processing tournament selection.")
        return ConversationHandler.END

async def get_first_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get first place winner details"""
    try:
        winner_text = update.message.text.strip()
        
        # Parse winner details
        parts = winner_text.split()
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Invalid format. Please use:\n@username points prize_amount\nExample: @player1 25 500"
            )
            return FIRST_PLACE
        
        username = parts[0].replace("@", "")
        try:
            points = int(parts[1])
            prize = int(parts[2])
        except ValueError:
            await update.message.reply_text("❌ Points and prize must be numbers. Please try again:")
            return FIRST_PLACE
        
        winner_data = {
            "position": 1,
            "username": username,
            "points": points,
            "prize": prize
        }
        
        context.user_data['winner_declaration'].winners.append(winner_data)
        
        await update.message.reply_text(
            f"✅ 1st Place: @{username} - {points} pts - ₹{prize}\n\n🥈 Please enter 2nd place details:",
            parse_mode='Markdown'
        )
        
        return SECOND_PLACE
        
    except Exception as e:
        logger.error(f"Error in get_first_place: {e}")
        await update.message.reply_text("❌ Error processing first place winner.")
        return ConversationHandler.END

async def get_second_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get second place winner details"""
    try:
        winner_text = update.message.text.strip()
        
        # Parse winner details
        parts = winner_text.split()
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Invalid format. Please use:\n@username points prize_amount\nExample: @player2 20 300"
            )
            return SECOND_PLACE
        
        username = parts[0].replace("@", "")
        try:
            points = int(parts[1])
            prize = int(parts[2])
        except ValueError:
            await update.message.reply_text("❌ Points and prize must be numbers. Please try again:")
            return SECOND_PLACE
        
        winner_data = {
            "position": 2,
            "username": username,
            "points": points,
            "prize": prize
        }
        
        context.user_data['winner_declaration'].winners.append(winner_data)
        
        await update.message.reply_text(
            f"✅ 2nd Place: @{username} - {points} pts - ₹{prize}\n\n🥉 Please enter 3rd place details:",
            parse_mode='Markdown'
        )
        
        return THIRD_PLACE
        
    except Exception as e:
        logger.error(f"Error in get_second_place: {e}")
        await update.message.reply_text("❌ Error processing second place winner.")
        return ConversationHandler.END

async def get_third_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get third place winner details and complete declaration"""
    try:
        winner_text = update.message.text.strip()
        
        # Parse winner details
        parts = winner_text.split()
        if len(parts) < 3:
            await update.message.reply_text(
                "❌ Invalid format. Please use:\n@username points prize_amount\nExample: @player3 18 200"
            )
            return THIRD_PLACE
        
        username = parts[0].replace("@", "")
        try:
            points = int(parts[1])
            prize = int(parts[2])
        except ValueError:
            await update.message.reply_text("❌ Points and prize must be numbers. Please try again:")
            return THIRD_PLACE
        
        winner_data = {
            "position": 3,
            "username": username,
            "points": points,
            "prize": prize
        }
        
        winner_declaration = context.user_data['winner_declaration']
        winner_declaration.winners.append(winner_data)
        
        # Get tournament details
        tournament = db.get_tournament(winner_declaration.tournament_id)
        if not tournament:
            await update.message.reply_text("❌ Tournament not found.")
            return ConversationHandler.END
        
        # Save winners to database
        db.add_winners(winner_declaration.tournament_id, winner_declaration.winners)
        
        # Mark tournament as completed
        db.update_tournament(winner_declaration.tournament_id, {"status": "completed"})
        
        # Generate winner announcement
        tournament_name = tournament.get("name", "Tournament")
        announcement = format_winner_announcement(winner_declaration.winners, tournament_name)
        
        # Send announcement to channel
        try:
            await context.bot.send_message(
                CHANNEL_ID,
                announcement,
                parse_mode='Markdown'
            )
            
            await update.message.reply_text(
                f"✅ **Winners declared successfully!**\n\n{announcement}\n\n📢 Announcement posted to channel.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error posting to channel: {e}")
            await update.message.reply_text(
                f"✅ **Winners declared!**\n\n{announcement}\n\n❌ Could not post to channel. Please post manually.",
                parse_mode='Markdown'
            )
        
        # Clean up conversation data
        if 'winner_declaration' in context.user_data:
            del context.user_data['winner_declaration']
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in get_third_place: {e}")
        await update.message.reply_text("❌ Error processing third place winner.")
        return ConversationHandler.END

async def clear_tournament_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        
        # Get active tournaments
        tournaments = db.get_active_tournaments()
        
        if not tournaments:
            await update.message.reply_text("❌ No active tournaments found.")
            return
        
        # Create tournament selection keyboard
        keyboard = []
        for tournament in tournaments:
            tournament_id = str(tournament["_id"])
            name = tournament.get("name", "Unnamed Tournament")
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {name}", 
                    callback_data=f"clear_tournament_{tournament_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🗑️ **Select Tournament to Clear/Remove:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in clear_tournament_command: {e}")
        await update.message.reply_text("❌ Error starting tournament cleanup.")

async def handle_clear_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tournament clearing"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("clear_tournament_"):
            tournament_id = data.replace("clear_tournament_", "")
            
            tournament = db.get_tournament(tournament_id)
            if not tournament:
                await query.edit_message_text("❌ Tournament not found.")
                return
            
            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm Delete", callback_data=f"confirm_clear_{tournament_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_clear")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⚠️ **Confirm Tournament Deletion**\n\n🎮 **Tournament:** {tournament.get('name', 'Unknown')}\n\n❗ This action cannot be undone. All participant data will be lost.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data.startswith("confirm_clear_"):
            tournament_id = data.replace("confirm_clear_", "")
            
            # Delete tournament
            result = db.delete_tournament(tournament_id)
            
            if result and result.deleted_count > 0:
                await query.edit_message_text("✅ **Tournament deleted successfully.**")
            else:
                await query.edit_message_text("❌ **Error deleting tournament.**")
        elif data == "cancel_clear":
            await query.edit_message_text("❌ **Tournament deletion cancelled.**")
            
    except Exception as e:
        logger.error(f"Error in handle_clear_tournament: {e}")
        await query.edit_message_text("❌ Error processing tournament deletion.")

# Financial reporting commands
async def today_earnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Today earnings command received from user {user_id}, admin_id is {ADMIN_ID}")
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            logger.warning(f"Unauthorized access attempt for /today from user {user_id}")
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        
        total_amount, total_payments = db.get_earnings_by_period("today")
        report = format_earnings_report("today", total_amount, total_payments)
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in today_earnings_command: {e}")
        await update.message.reply_text("❌ Error generating today's earnings report.")

async def week_earnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /thisweek command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        
        total_amount, total_payments = db.get_earnings_by_period("week")
        report = format_earnings_report("week", total_amount, total_payments)
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in week_earnings_command: {e}")
        await update.message.reply_text("❌ Error generating weekly earnings report.")

async def month_earnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /thismonth command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        
        total_amount, total_payments = db.get_earnings_by_period("month")
        report = format_earnings_report("month", total_amount, total_payments)
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in month_earnings_command: {e}")
        await update.message.reply_text("❌ Error generating monthly earnings report.")

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to check user info"""
    try:
        user = update.effective_user
        user_id = user.id
        username = user.username
        first_name = user.first_name
        
        debug_info = f"""
🔍 **DEBUG INFO**

👤 **User ID:** {user_id}
🏷️ **Username:** @{username if username else 'No username'}
📝 **First Name:** {first_name if first_name else 'No name'}
🔧 **Admin ID:** {ADMIN_ID}
✅ **Is Admin:** {'Yes' if is_admin(user_id, ADMIN_ID) else 'No'}

**For admin access, your User ID must match the configured Admin ID.**
"""
        
        await update.message.reply_text(debug_info, parse_mode='Markdown')
        logger.info(f"Debug info sent to user {user_id} (@{username})")
        
    except Exception as e:
        logger.error(f"Error in debug_command: {e}")
        await update.message.reply_text("❌ Error getting debug info.")
