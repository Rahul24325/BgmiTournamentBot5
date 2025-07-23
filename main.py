import logging
import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from telegram.error import TelegramError

# Import handlers
from bot_handlers import (
    start_command, 
    button_callback, 
    error_handler
)
from payment_handlers import (
    paid_command, 
    handle_payment_confirmation,
    confirm_user_command,
    decline_user_command
)
from tournament_handlers import (
    create_tournament_solo_command,
    create_tournament_squad_command,
    get_tournament_name,
    get_tournament_date,
    get_tournament_time,
    get_entry_fee,
    handle_prize_type_selection,
    get_prize_pool,
    get_map_name,
    get_upi_id,
    handle_tournament_post,
    cancel_creation,
    TOURNAMENT_NAME,
    TOURNAMENT_DATE,
    TOURNAMENT_TIME,
    ENTRY_FEE,
    PRIZE_TYPE,
    PRIZE_POOL,
    MAP_NAME,
    UPI_ID
)
from admin_handlers import (
    send_room_command,
    handle_tournament_room_selection,
    get_room_id,
    get_room_password,
    list_players_command,
    handle_list_players,
    declare_winners_command,
    handle_winner_tournament_selection,
    get_first_place,
    get_second_place,
    get_third_place,
    clear_tournament_command,
    handle_clear_tournament,
    today_earnings_command,
    week_earnings_command,
    month_earnings_command,
    debug_command,
    ROOM_ID_INPUT,
    ROOM_PASSWORD_INPUT,
    FIRST_PLACE,
    SECOND_PLACE,
    THIRD_PLACE
)

from config import BOT_TOKEN
from database import db

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def cleanup_old_tournaments():
    """Cleanup old tournaments - called periodically"""
    try:
        count = db.cleanup_old_tournaments(days=7)
        if count > 0:
            logger.info(f"Cleaned up {count} old tournaments")
        return count
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return 0

def main():
    """Start the bot"""
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Basic command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("paid", paid_command))
        application.add_handler(CommandHandler("confirm", confirm_user_command))
        application.add_handler(CommandHandler("decline", decline_user_command))
        application.add_handler(CommandHandler("debug", debug_command))
        
        # Admin command handlers
        application.add_handler(CommandHandler("listplayers", list_players_command))
        application.add_handler(CommandHandler("clear", clear_tournament_command))
        application.add_handler(CommandHandler("today", today_earnings_command))
        application.add_handler(CommandHandler("thisweek", week_earnings_command))
        application.add_handler(CommandHandler("thismonth", month_earnings_command))
        
        # Tournament creation conversation handlers
        solo_tournament_handler = ConversationHandler(
            entry_points=[CommandHandler("createtournamentsolo", create_tournament_solo_command)],
            states={
                TOURNAMENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tournament_name)],
                TOURNAMENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tournament_date)],
                TOURNAMENT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tournament_time)],
                ENTRY_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_entry_fee)],
                PRIZE_TYPE: [CallbackQueryHandler(handle_prize_type_selection, pattern="^prize_")],
                PRIZE_POOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prize_pool)],
                MAP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_map_name)],
                UPI_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_upi_id)]
            },
            fallbacks=[CommandHandler("cancel", cancel_creation)],
            allow_reentry=True
        )
        
        squad_tournament_handler = ConversationHandler(
            entry_points=[CommandHandler("createtournamentsquad", create_tournament_squad_command)],
            states={
                TOURNAMENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tournament_name)],
                TOURNAMENT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tournament_date)],
                TOURNAMENT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tournament_time)],
                ENTRY_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_entry_fee)],
                PRIZE_POOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prize_pool)],
                MAP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_map_name)],
                UPI_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_upi_id)]
            },
            fallbacks=[CommandHandler("cancel", cancel_creation)],
            allow_reentry=True
        )
        
        # Room details conversation handler
        room_details_handler = ConversationHandler(
            entry_points=[CommandHandler("sendroom", send_room_command)],
            states={
                ROOM_ID_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_room_id)],
                ROOM_PASSWORD_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_room_password)]
            },
            fallbacks=[CommandHandler("cancel", cancel_creation)],
            allow_reentry=True
        )
        
        # Winner declaration conversation handler
        winner_declaration_handler = ConversationHandler(
            entry_points=[CommandHandler("declarewinners", declare_winners_command)],
            states={
                FIRST_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_first_place)],
                SECOND_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_second_place)],
                THIRD_PLACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_third_place)]
            },
            fallbacks=[CommandHandler("cancel", cancel_creation)],
            allow_reentry=True
        )
        
        # Add conversation handlers
        application.add_handler(solo_tournament_handler)
        application.add_handler(squad_tournament_handler)
        application.add_handler(room_details_handler)
        application.add_handler(winner_declaration_handler)
        
        # Callback query handlers (must be after conversation handlers)
        application.add_handler(CallbackQueryHandler(handle_tournament_post, pattern="^(post_tournament_|edit_tournament_|cancel_tournament_)"))
        application.add_handler(CallbackQueryHandler(handle_payment_confirmation, pattern="^(confirm_payment_|decline_payment_)"))
        application.add_handler(CallbackQueryHandler(handle_tournament_room_selection, pattern="^select_tournament_room_"))
        application.add_handler(CallbackQueryHandler(handle_list_players, pattern="^list_players_"))
        application.add_handler(CallbackQueryHandler(handle_winner_tournament_selection, pattern="^declare_winners_"))
        application.add_handler(CallbackQueryHandler(handle_clear_tournament, pattern="^(clear_tournament_|confirm_clear_|cancel_clear)"))
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        logger.info("Bot is starting...")
        
        # Run the bot
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
    finally:
        # Close database connection
        db.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
