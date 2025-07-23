from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
from config import MONGODB_URI, DATABASE_NAME

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(MONGODB_URI)
            self.db = self.client[DATABASE_NAME]
            
            # Collections
            self.users = self.db.users
            self.tournaments = self.db.tournaments
            self.payments = self.db.payments
            self.winners = self.db.winners
            
            # Create indexes for better performance
            self.users.create_index("user_id", unique=True)
            self.tournaments.create_index("created_at")
            self.payments.create_index([("user_id", 1), ("tournament_id", 1)])
            
            logger.info("Database connected successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    # User Management
    def add_user(self, user_id, username=None, first_name=None):
        """Add or update user in database"""
        try:
            user_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "joined_at": datetime.now(),
                "is_member": False,
                "tournaments_joined": 0
            }
            
            self.users.update_one(
                {"user_id": user_id},
                {"$setOnInsert": user_data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    def get_user(self, user_id):
        """Get user by ID"""
        return self.users.find_one({"user_id": user_id})

    def update_user_membership(self, user_id, is_member=True):
        """Update user channel membership status"""
        return self.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_member": is_member, "membership_updated": datetime.now()}}
        )

    # Tournament Management
    def create_tournament(self, tournament_data):
        """Create new tournament"""
        try:
            tournament_data.update({
                "created_at": datetime.now(),
                "status": "active",
                "participants": [],
                "confirmed_players": []
            })
            
            result = self.tournaments.insert_one(tournament_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating tournament: {e}")
            return None

    def get_active_tournaments(self):
        """Get all active tournaments"""
        return list(self.tournaments.find({"status": "active"}).sort("created_at", -1))

    def get_tournament(self, tournament_id):
        """Get tournament by ID"""
        from bson import ObjectId
        try:
            return self.tournaments.find_one({"_id": ObjectId(tournament_id)})
        except:
            return None

    def update_tournament(self, tournament_id, update_data):
        """Update tournament data"""
        from bson import ObjectId
        try:
            return self.tournaments.update_one(
                {"_id": ObjectId(tournament_id)},
                {"$set": update_data}
            )
        except Exception as e:
            logger.error(f"Error updating tournament: {e}")
            return None

    def delete_tournament(self, tournament_id):
        """Delete tournament"""
        from bson import ObjectId
        try:
            return self.tournaments.delete_one({"_id": ObjectId(tournament_id)})
        except Exception as e:
            logger.error(f"Error deleting tournament: {e}")
            return None

    def add_participant(self, tournament_id, user_id):
        """Add participant to tournament"""
        from bson import ObjectId
        try:
            return self.tournaments.update_one(
                {"_id": ObjectId(tournament_id)},
                {"$addToSet": {"participants": user_id}}
            )
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
            return None

    def confirm_participant(self, tournament_id, user_id):
        """Confirm participant in tournament"""
        from bson import ObjectId
        try:
            return self.tournaments.update_one(
                {"_id": ObjectId(tournament_id)},
                {"$addToSet": {"confirmed_players": user_id}}
            )
        except Exception as e:
            logger.error(f"Error confirming participant: {e}")
            return None

    def get_confirmed_players(self, tournament_id):
        """Get confirmed players for tournament"""
        tournament = self.get_tournament(tournament_id)
        return tournament.get("confirmed_players", []) if tournament else []

    # Payment Management
    def add_payment_request(self, user_id, tournament_id, amount, screenshot_file_id=None):
        """Add payment request"""
        try:
            payment_data = {
                "user_id": user_id,
                "tournament_id": tournament_id,
                "amount": amount,
                "screenshot_file_id": screenshot_file_id,
                "status": "pending",
                "created_at": datetime.now()
            }
            
            result = self.payments.insert_one(payment_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error adding payment request: {e}")
            return None

    def get_payment_requests(self, status="pending"):
        """Get payment requests by status"""
        return list(self.payments.find({"status": status}).sort("created_at", -1))

    def update_payment_status(self, user_id, tournament_id, status):
        """Update payment status"""
        return self.payments.update_one(
            {"user_id": user_id, "tournament_id": tournament_id},
            {"$set": {"status": status, "updated_at": datetime.now()}}
        )

    def get_user_payment(self, user_id, tournament_id):
        """Get user payment for specific tournament"""
        return self.payments.find_one({"user_id": user_id, "tournament_id": tournament_id})

    # Financial Reporting
    def get_earnings_by_period(self, period="today"):
        """Get earnings by time period"""
        now = datetime.now()
        
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = datetime.min
        
        pipeline = [
            {
                "$match": {
                    "status": "confirmed",
                    "created_at": {"$gte": start_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_amount": {"$sum": "$amount"},
                    "total_payments": {"$sum": 1}
                }
            }
        ]
        
        result = list(self.payments.aggregate(pipeline))
        if result:
            return result[0]["total_amount"], result[0]["total_payments"]
        return 0, 0

    # Winner Management
    def add_winners(self, tournament_id, winners_data):
        """Add tournament winners"""
        try:
            winner_entry = {
                "tournament_id": tournament_id,
                "winners": winners_data,
                "declared_at": datetime.now()
            }
            
            result = self.winners.insert_one(winner_entry)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error adding winners: {e}")
            return None

    def get_tournament_winners(self, tournament_id):
        """Get winners for a tournament"""
        return self.winners.find_one({"tournament_id": tournament_id})

    # Cleanup operations
    def cleanup_old_tournaments(self, days=7):
        """Remove tournaments older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Mark old tournaments as completed
            result = self.tournaments.update_many(
                {
                    "created_at": {"$lt": cutoff_date},
                    "status": "active"
                },
                {"$set": {"status": "completed"}}
            )
            
            logger.info(f"Marked {result.modified_count} tournaments as completed")
            return result.modified_count
        except Exception as e:
            logger.error(f"Error cleaning up tournaments: {e}")
            return 0

    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()

# Initialize database instance
db = Database()
