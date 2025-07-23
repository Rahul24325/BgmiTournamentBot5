import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from utils import (
    is_admin, 
    format_tournament_message,
    generate_tournament_post,
    format_room_details_message,
    format_winner_announcement,
    format_player_list
)
from config import ADMIN_ID, CHANNEL_ID, TOURNAMENT_TYPES, PRIZE_TYPES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
(TOURNAMENT_NAME, TOURNAMENT_DATE, TOURNAMENT_TIME, 
 ENTRY_FEE, PRIZE_POOL, PRIZE_TYPE, MAP_NAME, UPI_ID,
 ROOM_ID, ROOM_PASSWORD, WINNER_INPUT) = range(11)

class TournamentCreator:
    def __init__(self):
        self.tournament_data = {}
        self.tournament_type = None

async def create_tournament_solo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /createtournamentsolo command"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Solo tournament command received from user {user_id}, admin_id is {ADMIN_ID}")
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return ConversationHandler.END
        
        # Initialize tournament creator
        context.user_data['tournament_creator'] = TournamentCreator()
        context.user_data['tournament_creator'].tournament_type = 'solo'
        
        await update.message.reply_text(
            "🎮 **Creating Solo Tournament**\n\n📝 Please enter the tournament name:",
            parse_mode='Markdown'
        )
        
        return TOURNAMENT_NAME
        
    except Exception as e:
        logger.error(f"Error in create_tournament_solo_command: {e}")
        await update.message.reply_text("❌ Error starting tournament creation.")
        return ConversationHandler.END

async def create_tournament_squad_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /createtournamentsqaud command"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is admin
        if not is_admin(user_id, ADMIN_ID):
            await update.message.reply_text("❌ You are not authorized to use this command.")
            return ConversationHandler.END
        
        # Initialize tournament creator
        context.user_data['tournament_creator'] = TournamentCreator()
        context.user_data['tournament_creator'].tournament_type = 'squad'
        
        await update.message.reply_text(
            "👥 **Creating Squad Tournament**\n\n📝 Please enter the tournament name:",
            parse_mode='Markdown'
        )
        
        return TOURNAMENT_NAME
        
    except Exception as e:
        logger.error(f"Error in create_tournament_squad_command: {e}")
        await update.message.reply_text("❌ Error starting tournament creation.")
        return ConversationHandler.END

async def get_tournament_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get tournament name"""
    try:
        tournament_name = update.message.text.strip()
        
        if not tournament_name or len(tournament_name) < 3:
            await update.message.reply_text("❌ Tournament name must be at least 3 characters long. Please try again:")
            return TOURNAMENT_NAME
        
        context.user_data['tournament_creator'].tournament_data['name'] = tournament_name
        
        await update.message.reply_text(
            f"✅ Tournament Name: **{tournament_name}**\n\n📅 Please enter the date (format: DD/MM/YYYY):",
            parse_mode='Markdown'
        )
        
        return TOURNAMENT_DATE
        
    except Exception as e:
        logger.error(f"Error in get_tournament_name: {e}")
        await update.message.reply_text("❌ Error processing tournament name.")
        return ConversationHandler.END

async def get_tournament_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get tournament date"""
    try:
        date_text = update.message.text.strip()
        
        # Basic date validation
        if not date_text or len(date_text) < 8:
            await update.message.reply_text("❌ Please enter a valid date in DD/MM/YYYY format:")
            return TOURNAMENT_DATE
        
        context.user_data['tournament_creator'].tournament_data['date'] = date_text
        
        await update.message.reply_text(
            f"✅ Date: **{date_text}**\n\n🕐 Please enter the time (format: HH:MM AM/PM):",
            parse_mode='Markdown'
        )
        
        return TOURNAMENT_TIME
        
    except Exception as e:
        logger.error(f"Error in get_tournament_date: {e}")
        await update.message.reply_text("❌ Error processing date.")
        return ConversationHandler.END

async def get_tournament_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get tournament time"""
    try:
        time_text = update.message.text.strip()
        
        if not time_text:
            await update.message.reply_text("❌ Please enter a valid time:")
            return TOURNAMENT_TIME
        
        context.user_data['tournament_creator'].tournament_data['time'] = time_text
        
        await update.message.reply_text(
            f"✅ Time: **{time_text}**\n\n💰 Please enter the entry fee amount (₹):",
            parse_mode='Markdown'
        )
        
        return ENTRY_FEE
        
    except Exception as e:
        logger.error(f"Error in get_tournament_time: {e}")
        await update.message.reply_text("❌ Error processing time.")
        return ConversationHandler.END

async def get_entry_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get entry fee"""
    try:
        fee_text = update.message.text.strip()
        
        try:
            entry_fee = int(fee_text)
            if entry_fee < 0:
                raise ValueError("Negative fee")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount (numbers only):")
            return ENTRY_FEE
        
        context.user_data['tournament_creator'].tournament_data['entry_fee'] = entry_fee
        
        # For solo tournaments, ask about prize type
        tournament_type = context.user_data['tournament_creator'].tournament_type
        
        if tournament_type == 'solo':
            keyboard = [
                [InlineKeyboardButton("💀 Kill Based Prize", callback_data="prize_kill")],
                [InlineKeyboardButton("🏆 Rank Based Prize", callback_data="prize_rank")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Entry Fee: **₹{entry_fee}**\n\n🎁 Please select prize type:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return PRIZE_TYPE
        else:
            # For squad tournaments, directly ask for prize pool
            await update.message.reply_text(
                f"✅ Entry Fee: **₹{entry_fee}**\n\n🎁 Please enter the total prize pool amount (₹):",
                parse_mode='Markdown'
            )
            
            return PRIZE_POOL
        
    except Exception as e:
        logger.error(f"Error in get_entry_fee: {e}")
        await update.message.reply_text("❌ Error processing entry fee.")
        return ConversationHandler.END

async def handle_prize_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle prize type selection"""
    try:
        query = update.callback_query
        await query.answer()
        
        prize_type = query.data.replace("prize_", "")
        context.user_data['tournament_creator'].tournament_data['prize_type'] = prize_type
        
        prize_text = "Kill Based" if prize_type == "kill" else "Rank Based"
        
        await query.edit_message_text(
            f"✅ Prize Type: **{prize_text}**\n\n🎁 Please enter the total prize pool amount (₹):",
            parse_mode='Markdown'
        )
        
        return PRIZE_POOL
        
    except Exception as e:
        logger.error(f"Error in handle_prize_type_selection: {e}")
        await query.edit_message_text("❌ Error processing prize type.")
        return ConversationHandler.END

async def get_prize_pool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get prize pool"""
    try:
        pool_text = update.message.text.strip()
        
        try:
            prize_pool = int(pool_text)
            if prize_pool < 0:
                raise ValueError("Negative prize pool")
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid amount (numbers only):")
            return PRIZE_POOL
        
        context.user_data['tournament_creator'].tournament_data['prize_pool'] = prize_pool
        
        await update.message.reply_text(
            f"✅ Prize Pool: **₹{prize_pool}**\n\n🗺️ Please enter the map name:",
            parse_mode='Markdown'
        )
        
        return MAP_NAME
        
    except Exception as e:
        logger.error(f"Error in get_prize_pool: {e}")
        await update.message.reply_text("❌ Error processing prize pool.")
        return ConversationHandler.END

async def get_map_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get map name"""
    try:
        map_name = update.message.text.strip()
        
        if not map_name:
            await update.message.reply_text("❌ Please enter a valid map name:")
            return MAP_NAME
        
        context.user_data['tournament_creator'].tournament_data['map'] = map_name
        
        await update.message.reply_text(
            f"✅ Map: **{map_name}**\n\n💳 Please enter UPI ID for payments:",
            parse_mode='Markdown'
        )
        
        return UPI_ID
        
    except Exception as e:
        logger.error(f"Error in get_map_name: {e}")
        await update.message.reply_text("❌ Error processing map name.")
        return ConversationHandler.END

async def get_upi_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get UPI ID and complete tournament creation"""
    try:
        upi_id = update.message.text.strip()
        
        if not upi_id:
            await update.message.reply_text("❌ Please enter a valid UPI ID:")
            return UPI_ID
        
        # Complete tournament data
        tournament_creator = context.user_data['tournament_creator']
        tournament_data = tournament_creator.tournament_data
        tournament_data['upi_id'] = upi_id
        tournament_data['type'] = tournament_creator.tournament_type
        
        # Create tournament in database
        tournament_id = db.create_tournament(tournament_data)
        
        if tournament_id:
            # Generate tournament post
            post_message = generate_tournament_post(tournament_data)
            
            # Create confirmation keyboard
            keyboard = [
                [InlineKeyboardButton("📢 Post to Channel", callback_data=f"post_tournament_{tournament_id}")],
                [InlineKeyboardButton("✏️ Edit Tournament", callback_data=f"edit_tournament_{tournament_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_tournament_{tournament_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Generate summary based on tournament type and prize type
            prize_line = ""
            if tournament_data['type'] == 'solo' and tournament_data.get('prize_type') == 'kill':
                prize_line = f"🏆 **Kills:** ₹{tournament_data['prize_pool']} per kill"
            else:
                prize_line = f"🎁 **Prize Pool:** ₹{tournament_data['prize_pool']}"
            
            summary = f"""
✅ **Tournament Created Successfully!**

📋 **Summary:**
🎮 **Name:** {tournament_data['name']}
📅 **Date:** {tournament_data['date']}
🕐 **Time:** {tournament_data['time']}
💰 **Entry Fee:** ₹{tournament_data['entry_fee']}
{prize_line}
🗺️ **Map:** {tournament_data['map']}
💳 **UPI:** {tournament_data['upi_id']}

What would you like to do?
"""
            
            await update.message.reply_text(
                summary,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Clean up conversation data
            if 'tournament_creator' in context.user_data:
                del context.user_data['tournament_creator']
            
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ Error creating tournament. Please try again.")
            return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in get_upi_id: {e}")
        await update.message.reply_text("❌ Error completing tournament creation.")
        return ConversationHandler.END

async def handle_tournament_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tournament posting to channel"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("post_tournament_"):
            tournament_id = data.replace("post_tournament_", "")
            await post_tournament_to_channel(query, context, tournament_id)
        elif data.startswith("edit_tournament_"):
            tournament_id = data.replace("edit_tournament_", "")
            await edit_tournament(query, context, tournament_id)
        elif data.startswith("cancel_tournament_"):
            tournament_id = data.replace("cancel_tournament_", "")
            await cancel_tournament(query, context, tournament_id)
            
    except Exception as e:
        logger.error(f"Error in handle_tournament_post: {e}")
        await query.edit_message_text("❌ Error processing tournament action.")

async def post_tournament_to_channel(query, context, tournament_id):
    """Post tournament to channel"""
    try:
        tournament = db.get_tournament(tournament_id)
        
        if not tournament:
            await query.edit_message_text("❌ Tournament not found.")
            return
        
        # Generate tournament post
        post_message = generate_tournament_post(tournament)
        
        # Create join keyboard
        from utils import create_tournament_keyboard
        keyboard = create_tournament_keyboard(tournament_id)
        
        # Post to channel
        try:
            await context.bot.send_message(
                CHANNEL_ID,
                post_message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            await query.edit_message_text(
                "✅ **Tournament posted to channel successfully!**\n\n📢 Users can now join the tournament.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error posting to channel: {e}")
            await query.edit_message_text(
                f"❌ **Error posting to channel.**\n\nTournament created but could not post to channel. Error: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"Error in post_tournament_to_channel: {e}")
        await query.edit_message_text("❌ Error posting tournament.")

async def edit_tournament(query, context, tournament_id):
    """Handle tournament editing"""
    try:
        tournament = db.get_tournament(tournament_id)
        
        if not tournament:
            await query.edit_message_text("❌ Tournament not found.")
            return
        
        # Create edit options keyboard
        keyboard = [
            [InlineKeyboardButton("📝 Edit Name", callback_data=f"edit_name_{tournament_id}")],
            [InlineKeyboardButton("📅 Edit Date", callback_data=f"edit_date_{tournament_id}")],
            [InlineKeyboardButton("🕐 Edit Time", callback_data=f"edit_time_{tournament_id}")],
            [InlineKeyboardButton("💰 Edit Entry Fee", callback_data=f"edit_fee_{tournament_id}")],
            [InlineKeyboardButton("🎁 Edit Prize", callback_data=f"edit_prize_{tournament_id}")],
            [InlineKeyboardButton("🗺️ Edit Map", callback_data=f"edit_map_{tournament_id}")],
            [InlineKeyboardButton("💳 Edit UPI", callback_data=f"edit_upi_{tournament_id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_summary_{tournament_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✏️ **Edit Tournament: {tournament['name']}**\n\nSelect what you want to edit:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in edit_tournament: {e}")
        await query.edit_message_text("❌ Error loading tournament edit options.")

async def cancel_tournament(query, context, tournament_id):
    """Cancel tournament creation"""
    try:
        # Delete tournament from database
        result = db.delete_tournament(tournament_id)
        
        if result and result.deleted_count > 0:
            await query.edit_message_text("❌ **Tournament cancelled and deleted.**")
        else:
            await query.edit_message_text("❌ **Error cancelling tournament.**")
            
    except Exception as e:
        logger.error(f"Error in cancel_tournament: {e}")
        await query.edit_message_text("❌ Error cancelling tournament.")

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel tournament creation"""
    await update.message.reply_text("❌ Tournament creation cancelled.")
    
    # Clean up conversation data
    if 'tournament_creator' in context.user_data:
        del context.user_data['tournament_creator']
    
    return ConversationHandler.END

# Conversation handler for tournament creation
def get_tournament_conversation_handler():
    """Get conversation handler for tournament creation"""
    return ConversationHandler(
        entry_points=[],  # Entry points are handled separately
        states={
            TOURNAMENT_NAME: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: TOURNAMENT_DATE
                    }
                )
            ],
            TOURNAMENT_DATE: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: TOURNAMENT_TIME
                    }
                )
            ],
            TOURNAMENT_TIME: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: ENTRY_FEE
                    }
                )
            ],
            ENTRY_FEE: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: PRIZE_TYPE
                    }
                )
            ],
            PRIZE_TYPE: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: PRIZE_POOL
                    }
                )
            ],
            PRIZE_POOL: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: MAP_NAME
                    }
                )
            ],
            MAP_NAME: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: UPI_ID
                    }
                )
            ],
            UPI_ID: [
                ConversationHandler(
                    entry_points=[],
                    states={},
                    fallbacks=[],
                    map_to_parent={
                        ConversationHandler.END: ConversationHandler.END
                    }
                )
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )
