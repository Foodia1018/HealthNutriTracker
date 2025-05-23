import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import blockchain

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///coinmama.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Import models after db initialization
from models import User, Transaction

# Create database tables
with app.app_context():
    db.create_all()

# Wallet address for deposits (fixed as per requirements)
WALLET_ADDRESS = "39zhvRrvyxKEA6cfGQiQGErhLiMXkArcNE"

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered", "danger")
            return redirect(url_for("signup"))
        
        # Create new user
        new_user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            btc_balance=50.0,  # $50 signup bonus
            last_deposit_time=None,
            confirmed_deposit=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Add signup bonus transaction
        bonus_transaction = Transaction(
            user_id=new_user.id,
            tx_hash="signup_bonus",
            amount=50.0,
            tx_type="bonus",
            confirmations=3,
            status="completed",
            timestamp=datetime.now()
        )
        db.session.add(bonus_transaction)
        db.session.commit()
        
        flash("Account created successfully! $50 BTC bonus added to your account.", "success")
        return redirect(url_for("login"))
    
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "danger")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard", "danger")
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
    
    # Check for deposits that should be doubled (every 3 days)
    if user.last_deposit_time:
        days_since_deposit = (datetime.now() - user.last_deposit_time).days
        doubles_due = days_since_deposit // 3
        
        if doubles_due > 0 and user.confirmed_deposit:
            # Update last deposit time to reflect the doubles already applied
            new_last_deposit_time = user.last_deposit_time + timedelta(days=doubles_due * 3)
            
            # Add transaction for each doubling
            for i in range(doubles_due):
                growth_transaction = Transaction(
                    user_id=user.id,
                    tx_hash=f"growth_{datetime.now().timestamp()}_{i}",
                    amount=user.btc_balance,  # Double the current balance
                    tx_type="growth",
                    confirmations=3,
                    status="completed",
                    timestamp=user.last_deposit_time + timedelta(days=(i+1) * 3)
                )
                db.session.add(growth_transaction)
                
                # Double the balance
                user.btc_balance *= 2
            
            user.last_deposit_time = new_last_deposit_time
            db.session.commit()
            
            flash(f"Your balance has been doubled {doubles_due} time(s)!", "success")
            # Refresh transactions after update
            transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
    
    # Check for pending deposits and update confirmations
    pending_deposits = Transaction.query.filter_by(
        user_id=user.id, 
        status="pending"
    ).all()
    
    for deposit in pending_deposits:
        # Simulate blockchain API check for confirmations
        confirmations = blockchain.check_confirmations(deposit.tx_hash)
        if confirmations >= 3 and deposit.confirmations < 3:
            deposit.confirmations = confirmations
            deposit.status = "completed"
            user.confirmed_deposit = True
            flash(f"Your deposit of ${deposit.amount} BTC has been confirmed!", "success")
            db.session.commit()
    
    # Serialize transactions for JavaScript chart
    serialized_transactions = []
    if transactions:
        for tx in transactions:
            if hasattr(tx, 'tx_type') and hasattr(tx, 'amount') and hasattr(tx, 'status') and hasattr(tx, 'timestamp'):
                serialized_transactions.append({
                    'tx_type': str(tx.tx_type),
                    'amount': float(tx.amount),
                    'status': str(tx.status),
                    'timestamp': tx.timestamp.strftime('%Y-%m-%d %H:%M:%S') if tx.timestamp else ''
                })
    
    return render_template(
        "dashboard.html", 
        user=user, 
        transactions=transactions,
        serialized_transactions=serialized_transactions,
        wallet_address=WALLET_ADDRESS
    )

@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if "user_id" not in session:
        flash("Please log in to make a deposit", "danger")
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    
    if request.method == "POST":
        amount = float(request.form.get("amount", 0))
        
        if amount < 150:
            flash("Minimum deposit amount is $150", "danger")
            return redirect(url_for("deposit"))
            
        # Simulate blockchain transaction
        tx_hash = blockchain.generate_tx_hash()
        
        # Create pending transaction
        new_deposit = Transaction(
            user_id=user.id,
            tx_hash=tx_hash,
            amount=amount,
            tx_type="deposit",
            confirmations=0,
            status="pending",
            timestamp=datetime.now()
        )
        
        db.session.add(new_deposit)
        user.last_deposit_time = datetime.now()
        db.session.commit()
        
        flash("Deposit initiated! We'll monitor for 3 confirmations.", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("deposit.html", wallet_address=WALLET_ADDRESS)

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw():
    if "user_id" not in session:
        flash("Please log in to withdraw funds", "danger")
        return redirect(url_for("login"))
    
    user = User.query.get(session["user_id"])
    
    if not user.confirmed_deposit:
        flash("You need to make a confirmed deposit before withdrawing", "warning")
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        amount = float(request.form.get("amount", 0))
        address = request.form.get("address", "")
        
        if amount <= 0 or amount > user.btc_balance:
            flash("Invalid withdrawal amount", "danger")
            return redirect(url_for("withdraw"))
        
        if not address:
            flash("Please enter a valid Bitcoin address", "danger")
            return redirect(url_for("withdraw"))
            
        # Create withdrawal transaction
        withdrawal = Transaction(
            user_id=user.id,
            tx_hash=blockchain.generate_tx_hash(),
            amount=amount,
            tx_type="withdrawal",
            confirmations=3,
            status="completed",
            timestamp=datetime.now()
        )
        
        # Update user balance
        user.btc_balance -= amount
        
        db.session.add(withdrawal)
        db.session.commit()
        
        flash(f"Withdrawal of ${amount} BTC to {address} completed successfully!", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("withdraw.html", user=user)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
