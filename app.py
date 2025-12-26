import os
from flask import Flask, render_template, url_for, flash, redirect, request
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from difflib import SequenceMatcher  # Built-in "AI" for text comparison

# Import Custom Modules
from database import db, User, Item, Notification
from ai_matcher import find_matches

app = Flask(__name__)

# --- CONFIGURATION & PATHS ---
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
upload_path = os.path.join(basedir, 'static', 'uploads')

if not os.path.exists(instance_path):
    os.makedirs(instance_path)

if not os.path.exists(upload_path):
    os.makedirs(upload_path)

app.config['SECRET_KEY'] = 'hackathon-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'database.db')
app.config['UPLOAD_FOLDER'] = upload_path

# --- EMAIL CONFIGURATION ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # <--- ENTER YOUR REAL GMAIL ADDRESS HERE
app.config['MAIL_PASSWORD'] = 'duyu vnlq bqkm kmtc'     # <--- I ADDED YOUR PASSWORD HERE
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

# Initialize Extensions
db.init_app(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==========================================
#  AI MATCHING & EMAIL LOGIC HELPER FUNCTIONS
# ==========================================

def calculate_similarity(a, b):
    """Returns a ratio (0.0 to 1.0) of similarity between two strings."""
    if not a or not b: return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def check_for_matches_and_notify_email(new_found_item):
    """
    Background logic to find matches and email users.
    Prints debug messages to the terminal so you can see if it works.
    """
    print("\n---------------------------------------------------")
    print(f"🔎 AI AUTO-MATCHING STARTED FOR: '{new_found_item.title}'")
    
    try:
        # 1. Get Lost items in same category
        potential_matches = Item.query.filter_by(type='lost', category=new_found_item.category).all()
        print(f"📊 Found {len(potential_matches)} lost items in category: {new_found_item.category}")

        found_any_match = False

        for lost_item in potential_matches:
            # 2. Compare Text
            title_score = calculate_similarity(new_found_item.title, lost_item.title)
            desc_score = calculate_similarity(new_found_item.description, lost_item.description)
            total_score = (title_score + desc_score) / 2
            
            print(f"   - Checking against '{lost_item.title}'... Score: {total_score:.2f}")

            # 3. If Match > 50%
            if total_score > 0.5:
                found_any_match = True
                loser = User.query.get(lost_item.user_id)
                
                if loser and loser.email:
                    print(f"   ✅ MATCH FOUND! Sending email to: {loser.email}")
                    send_notification_email(loser.email, new_found_item, lost_item.title)
                else:
                    print("   ❌ Match found, but user has no email in DB.")

        if not found_any_match:
            print("⚠️ No matches passed the 50% similarity threshold.")

    except Exception as e:
        print(f"❌ ERROR IN MATCHING LOGIC: {e}")
    
    print("---------------------------------------------------\n")

def send_notification_email(recipient_email, found_item, lost_item_title):
    """Sends an email to the user who lost the item."""
    try:
        msg = Message('Good News! Potential Match Found',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[recipient_email])
        
        msg.html = f"""
        <h3>Hi there,</h3>
        <p>We noticed you reported a lost item: <b>{lost_item_title}</b>.</p>
        <p>Great news! Someone just reported finding a similar item.</p>
        <hr>
        <h4>Found Item Details:</h4>
        <ul>
            <li><b>Item:</b> {found_item.title}</li>
            <li><b>Location Found:</b> {found_item.location}</li>
            <li><b>Description:</b> {found_item.description}</li>
        </ul>
        <p>Please login to your dashboard to view the image and claim it if it's yours.</p>
        <br>
        <p>Best,<br>Lost & Found Team</p>
        """
        mail.send(msg)
        print("   📧 EMAIL SENT SUCCESSFULLY!")
    except Exception as e:
        print(f"   ❌ FAILED TO SEND EMAIL: {e}")
        print("   (Check if your Email Address on line 35 is correct)")


# --- ROUTES ---

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html') 

@app.route("/dashboard")
@login_required
def dashboard():
    # 1. Get user's reported items
    user_items = Item.query.filter_by(user_id=current_user.id).all()
    
    # 2. Get unread notifications for this user (Newest first)
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                    .order_by(Notification.timestamp.desc()).all()
    
    return render_template('dashboard.html', items=user_items, notifications=notifications)

# --- REPORT LOST ITEM ---
@app.route("/report_lost", methods=['GET', 'POST'])
@login_required
def report_lost():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        category = request.form.get('category')
        
        image = request.files.get('image')
        filename = 'default.jpg'
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_item = Item(title=title, description=description, location=location, 
                        category=category, type='lost', image_file=filename, user_id=current_user.id)
        
        db.session.add(new_item)
        db.session.commit()
        
        # --- INTERNAL AI MATCHING (For Dashboard Notifications) ---
        all_items = Item.query.all()
        search_data = {'title': title, 'description': description, 'category': category, 'type': 'lost'}
        
        # Existing match logic for UI display
        matches = find_matches(search_data, all_items)
        
        if matches:
            flash(f'AI found {len(matches)} potential matches!', 'success')
            for match in matches:
                if match.user_id != current_user.id:
                    msg = f"AI Alert: Someone lost a '{title}' that looks like the '{match.title}' you found!"
                    notif = Notification(user_id=match.user_id, message=msg, match_item_id=new_item.id)
                    db.session.add(notif)
            
            db.session.commit()
            return render_template('matches.html', matches=matches, current_item=new_item)
            
        return redirect(url_for('dashboard'))
        
    return render_template('report_lost.html')

# --- RESOLVE ITEM (DELETE) ---
@app.route('/resolve_item/<int:item_id>', methods=['POST'])
@login_required
def resolve_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    # Security Check
    if item.user_id != current_user.id:
        flash('You do not have permission to delete this item.', 'error')
        return redirect(url_for('dashboard'))
    
    db.session.delete(item)
    db.session.commit()
    
    flash('Item marked as resolved and removed from dashboard!', 'success')
    return redirect(url_for('dashboard'))

# --- REPORT FOUND ITEM ---
@app.route("/report_found", methods=['GET', 'POST'])
@login_required
def report_found():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        category = request.form.get('category')
        
        image = request.files.get('image')
        filename = 'default.jpg'
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_item = Item(title=title, description=description, location=location, 
                        category=category, type='found', image_file=filename, user_id=current_user.id)
        
        db.session.add(new_item)
        db.session.commit()
        
        # --- 1. EMAIL NOTIFICATION LOGIC (NEW & DEBUGGED) ---
        check_for_matches_and_notify_email(new_item)

        # --- 2. INTERNAL DASHBOARD NOTIFICATION LOGIC (EXISTING) ---
        all_items = Item.query.all()
        search_data = {'title': title, 'description': description, 'category': category, 'type': 'found'}
        matches = find_matches(search_data, all_items)
        
        if matches:
            for match in matches:
                if match.user_id != current_user.id:
                    msg = f"AI Alert: Good news! A '{title}' was found that matches your lost '{match.title}'!"
                    notif = Notification(user_id=match.user_id, message=msg, match_item_id=new_item.id)
                    db.session.add(notif)

            db.session.commit()
            return render_template('matches.html', matches=matches, current_item=new_item)
            
        return redirect(url_for('dashboard'))

    return render_template('report_found.html')

# --- AUTH ROUTES ---

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Login failed. Check your email and password.', 'danger')
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        raw_password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', 'warning')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(raw_password)
        
        new_user = User(email=email, name=name, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('dashboard'))
        
    return render_template('register.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# 👇 NO SPACES at the start of this line!
with app.app_context():
    # Creates database tables if they don't exist
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
