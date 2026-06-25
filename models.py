# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import secrets

db = SQLAlchemy()

def utc_now():
    """Get naive UTC datetime (safe for database columns and datetime comparisons)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Token(db.Model):
    __tablename__ = 'tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    batch_id = db.Column(db.String(36), nullable=True)
    assigned_user = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    def is_valid(self):
        """Check if token is usable (active, not expired)"""
        return self.is_active and utc_now() < self.expires_at
    
    def is_assigned(self):
        """Check if token has been claimed by a user"""
        return self.assigned_user is not None
    
    @classmethod
    def generate_token_code(cls):
        """Generate unique random 6-digit token like TKN-882143"""
        attempts = 0
        while attempts < 1000:
            token_code = f"TKN-{secrets.randbelow(900000) + 100000}"
            if not cls.query.filter_by(code=token_code).first():
                return token_code
            attempts += 1
        raise ValueError("Could not generate a unique token code after 1000 attempts.")

