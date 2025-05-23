from datetime import datetime
from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    btc_balance = db.Column(db.Float, default=0.0)
    last_deposit_time = db.Column(db.DateTime, nullable=True)
    confirmed_deposit = db.Column(db.Boolean, default=False)
    transactions = db.relationship("Transaction", backref="user", lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<User {self.username}>"

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tx_hash = db.Column(db.String(128), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tx_type = db.Column(db.String(20), nullable=False)  # deposit, withdrawal, bonus, growth
    confirmations = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="pending")  # pending, completed, failed
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Transaction {self.tx_type} {self.amount}>"
