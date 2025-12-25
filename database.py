from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# --- USER MODEL ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    
    # Relationship for Notifications (So we can do user.notifications)
    notifications = db.relationship('Notification', backref='recipient', lazy=True)

# --- ITEM MODEL ---
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False) # 'lost' or 'found'
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Increased length to 100 to prevent errors
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship to User (Creates 'user.items' list automatically)
    user = db.relationship('User', backref=db.backref('items', lazy=True))

# --- NOTIFICATION MODEL (New) ---
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Who gets the notification?
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Optional: Which item caused the match?
    match_item_id = db.Column(db.Integer, nullable=True)