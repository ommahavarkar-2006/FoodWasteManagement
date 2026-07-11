from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import time
import secrets

# Load .env file
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Secret Key
app.secret_key = os.getenv("SECRET_KEY", "development-secret-key")

# ==================== MySQL CONFIG ====================
app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "localhost")
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER", "root")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "")
app.config["MYSQL_DB"] = os.getenv("MYSQL_DB", "wastenofood")
app.config["MYSQL_PORT"] = int(os.getenv("MYSQL_PORT", 3306))
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

# ==================== Upload Configuration ====================
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==================== MySQL ====================
mysql = MySQL(app)

# ==================== Stripe ====================
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
# ==================== Mail ====================
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_donation_id():
    """Generate a unique donation ID in format FD12345"""
    import random
    unique_num = str(random.randint(10000, 99999))
    return f"FD{unique_num}"

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(secrets.randbelow(900000) + 100000)  # Generates 6-digit number

# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ngo-donation', methods=['GET', 'POST'])
def ngo_donation():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        ngo_id = request.form.get('ngo_id')
        ngo_name = request.form.get('ngo_name')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')
        message = request.form.get('message')
        
        # Validate required fields
        if not all([ngo_id, ngo_name, amount, payment_method]):
            flash('All required fields must be filled!', 'danger')
            return redirect(url_for('ngo_donation'))
        
        try:
            amount = float(amount)
            if amount < 10:
                flash('Minimum donation amount is ₹10!', 'danger')
                return redirect(url_for('ngo_donation'))
        except ValueError:
            flash('Please enter a valid amount!', 'danger')
            return redirect(url_for('ngo_donation'))
        
        try:
            cur = mysql.connection.cursor()
            
            # Insert donation record
            cur.execute("""
                INSERT INTO donations 
                (user_id, ngo_id, amount, payment_method, status, message)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session['user_id'], ngo_id, amount, payment_method, 'completed', message))
            
            donation_id = cur.lastrowid
            mysql.connection.commit()
            cur.close()
            
            flash(f'Donation of ₹{amount} to {ngo_name} recorded successfully! Status: Completed', 'success')
            return redirect(url_for('user_dashboard'))
            
        except Exception as e:
            flash(f'Error processing donation: {str(e)}', 'danger')
            return redirect(url_for('ngo_donation'))
    
    # GET request - show NGO selection page
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, address, description FROM ngos WHERE is_verified = TRUE ORDER BY name")
        ngos = cur.fetchall()
        cur.close()
        
        return render_template('ngo_donation.html', ngos=ngos)
        
    except Exception as e:
        flash(f'Error loading NGOs: {str(e)}', 'danger')
        return redirect(url_for('user_dashboard'))

@app.route('/report-leftover-food', methods=['GET', 'POST'])
def report_leftover_food():
    if request.method == 'POST':
        # Get form data
        event_type = request.form.get('event_type')
        event_date = request.form.get('event_date')
        event_time = request.form.get('event_time')
        location = request.form.get('location')
        people_invited = request.form.get('people_invited')
        people_ate = request.form.get('people_ate')
        food_left_kg = request.form.get('food_left_kg')
        food_left_plates = request.form.get('food_left_plates')
        food_type = request.form.get('food_type')
        organizer_name = request.form.get('organizer_name')
        contact_number = request.form.get('contact_number')
        food_photo = request.files.get('food_photo')
        kitchen_photo = request.files.get('kitchen_photo')
        
        # Validate required fields
        if not all([event_type, event_date, event_time, location, people_invited, 
                   people_ate, food_left_kg, food_left_plates, food_type, 
                   organizer_name, contact_number]):
            flash('All fields are required!', 'danger')
            return redirect(url_for('report_leftover_food'))
        
        # Validate numbers
        try:
            people_invited = int(people_invited)
            people_ate = int(people_ate)
            food_left_kg = float(food_left_kg)
            food_left_plates = int(food_left_plates)
            
            if people_ate > people_invited:
                flash('People who ate cannot exceed people invited!', 'danger')
                return redirect(url_for('report_leftover_food'))
        except ValueError:
            flash('Please enter valid numbers!', 'danger')
            return redirect(url_for('report_leftover_food'))
        
        # Handle file uploads
        food_photo_path = None
        kitchen_photo_path = None
        
        if food_photo and food_photo.filename != '':
            if not allowed_file(food_photo.filename):
                flash('Invalid file type for food photo. Please upload JPG or PNG.', 'danger')
                return redirect(url_for('report_leftover_food'))
            filename = secure_filename(food_photo.filename)
            unique_filename = f"food_{int(time.time())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            food_photo.save(file_path)
            food_photo_path = unique_filename
        
        if kitchen_photo and kitchen_photo.filename != '':
            if not allowed_file(kitchen_photo.filename):
                flash('Invalid file type for kitchen photo. Please upload JPG or PNG.', 'danger')
                return redirect(url_for('report_leftover_food'))
            filename = secure_filename(kitchen_photo.filename)
            unique_filename = f"kitchen_{int(time.time())}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            kitchen_photo.save(file_path)
            kitchen_photo_path = unique_filename
        
        try:
            cur = mysql.connection.cursor()
            
            # Insert into leftover_food_reports table
            user_id = session.get('user_id')
            cur.execute("""
                INSERT INTO leftover_food_reports 
                (event_type, event_date, event_time, location, people_invited, people_ate,
                 food_left_kg, food_left_plates, food_type, food_photo_path, kitchen_photo_path,
                 organizer_name, contact_number, user_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (event_type, event_date, event_time, location, people_invited, people_ate,
                  food_left_kg, food_left_plates, food_type, food_photo_path, kitchen_photo_path,
                  organizer_name, contact_number, user_id, 'Reported'))
            
            report_id = cur.lastrowid
            mysql.connection.commit()
            
            # Get nearby NGOs (for now, get all active NGOs)
            cur.execute("SELECT id, name, address FROM ngos WHERE is_verified = TRUE ORDER BY name")
            nearby_ngos = cur.fetchall()
            
            cur.close()
            
            flash('Leftover food reported successfully! Finding nearby NGOs...', 'success')
            return render_template('ngo_selection.html', report_id=report_id, ngos=nearby_ngos)
            
        except Exception as e:
            flash(f'Error submitting report: {str(e)}', 'danger')
            return redirect(url_for('report_leftover_food'))
    
    return render_template('report_leftover_food.html')

@app.route('/assign-ngo-to-report', methods=['POST'])
def assign_ngo_to_report():
    if request.method == 'POST':
        report_id = request.form.get('report_id')
        ngo_id = request.form.get('ngo_id')
        
        if not report_id or not ngo_id:
            flash('Invalid request!', 'danger')
            return redirect(url_for('report_leftover_food'))
        
        try:
            cur = mysql.connection.cursor()
            
            # Get NGO details
            cur.execute("SELECT name FROM ngos WHERE id = %s", (ngo_id,))
            ngo = cur.fetchone()
            
            if not ngo:
                flash('NGO not found!', 'danger')
                return redirect(url_for('report_leftover_food'))
            
            # Update the report with NGO assignment
            cur.execute("""
                UPDATE leftover_food_reports 
                SET ngo_id = %s, ngo_name = %s, status = 'NGO_Assigned'
                WHERE id = %s
            """, (ngo_id, ngo['name'], report_id))
            
            mysql.connection.commit()
            cur.close()
            
            flash(f'Successfully assigned to {ngo["name"]}! They will contact you soon.', 'success')
            return redirect(url_for('report_success', report_id=report_id))
            
        except Exception as e:
            flash(f'Error assigning NGO: {str(e)}', 'danger')
            return redirect(url_for('report_leftover_food'))
    
    return redirect(url_for('report_leftover_food'))

@app.route('/report-success/<int:report_id>')
def report_success(report_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM leftover_food_reports WHERE id = %s", (report_id,))
        report = cur.fetchone()
        cur.close()
        
        if not report:
            flash('Report not found!', 'danger')
            return redirect(url_for('index'))
        
        return render_template('report_success.html', report=report)
        
    except Exception as e:
        flash(f'Error loading report: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/track-leftover-report/<int:report_id>')
def track_leftover_report(report_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT lfr.*, n.name as ngo_full_name, n.contact_phone as ngo_phone
            FROM leftover_food_reports lfr
            LEFT JOIN ngos n ON lfr.ngo_id = n.id
            WHERE lfr.id = %s
        """, (report_id,))
        report = cur.fetchone()
        cur.close()
        
        if not report:
            flash('Report not found!', 'danger')
            return redirect(url_for('index'))
        
        return render_template('track_leftover_report.html', report=report)
        
    except Exception as e:
        flash(f'Error tracking report: {str(e)}', 'danger')
        return redirect(url_for('index'))

# ==================== AUTH ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        user_type = request.form.get('user_type', 'Individual')

        if not all([name, email, phone, password]):
            flash('All fields are required!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cur.fetchone()

            if existing_user:
                flash('Email already registered! Please login.', 'warning')
                cur.close()
                return redirect(url_for('login'))

            cur.execute("""
                INSERT INTO users (name, email, phone, password, user_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, email, phone, hashed_password, user_type, datetime.now()))
            mysql.connection.commit()
            cur.close()

            flash('Registration Successful! Please login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('register'))

    return render_template('user_registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type', 'user')

        if not email or not password:
            flash('Email and password are required!', 'danger')
            return redirect(url_for('login'))

        try:
            cur = mysql.connection.cursor()
            table = 'admins' if user_type == 'admin' else 'users'
            cur.execute(f"SELECT * FROM {table} WHERE email = %s", (email,))
            user = cur.fetchone()
            cur.close()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                session['user_type'] = user_type

                flash('Login Successful!', 'success')
                return redirect(url_for('admin_dashboard') if user_type == 'admin' else url_for('index'))
            else:
                flash('Invalid email or password!', 'danger')
                return redirect(url_for('login'))

        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
            return redirect(url_for('login'))

    return render_template('user_login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

# ==================== DASHBOARDS ====================

@app.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))

    try:
        cur = mysql.connection.cursor()
        user_id = session['user_id']
        user_name = session.get('user_name')

        # Ensure food_donations table exists and has ngo_id column
        cur.execute("""
            CREATE TABLE IF NOT EXISTS food_donations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                donor_name VARCHAR(100),
                donor_phone VARCHAR(15),
                donor_address TEXT,
                food_type VARCHAR(50),
                quantity VARCHAR(50),
                time_available VARCHAR(50),
                note TEXT,
                ngo_id INT,
                status VARCHAR(20) DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (ngo_id) REFERENCES ngos(id) ON DELETE SET NULL
            )
        """)
        
        # Check if ngo_id column exists (in case table existed before)
        cur.execute("SHOW COLUMNS FROM food_donations LIKE 'ngo_id'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE food_donations ADD COLUMN ngo_id INT, ADD FOREIGN KEY (ngo_id) REFERENCES ngos(id) ON DELETE SET NULL")
        
        mysql.connection.commit()

        # Summary stats
        cur.execute("""
            SELECT 
                COALESCE(SUM(amount), 0) AS total_donated,
                COUNT(*) AS total_donations
            FROM donations WHERE user_id = %s
        """, (user_id,))
        stats = cur.fetchone()

        # Recent donations (monetary)
        cur.execute("""
            SELECT d.*, n.name AS ngo_name 
            FROM donations d
            LEFT JOIN ngos n ON d.ngo_id = n.id
            WHERE d.user_id = %s
            ORDER BY d.created_at DESC
            LIMIT 5
        """, (user_id,))
        recent_donations = cur.fetchall()
        
        # Sync food_donations status with donations_tracking status
        cur.execute("""
            UPDATE food_donations fd
            JOIN donations_tracking dt ON fd.user_id = dt.donor_id OR fd.donor_name = dt.donor_name
            SET fd.status = dt.status
            WHERE dt.status = 'Completed' AND fd.status = 'Pending'
        """)
        
        cur.close()

        # Pass only monetary donations to template (food_donations no longer displayed on dashboard)
        return render_template('dashboard.html', stats=stats, donations=recent_donations)

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Admin access required!', 'danger')
        return redirect(url_for('admin_login'))

    try:
        cur = mysql.connection.cursor()
        # Counts
        cur.execute("SELECT COUNT(*) AS total_users FROM users")
        total_users = cur.fetchone()['total_users']

        cur.execute("SELECT COUNT(*) AS total_ngos FROM ngos")
        total_ngos = cur.fetchone()['total_ngos']

        cur.execute("SELECT COALESCE(SUM(amount),0) AS total_donations FROM donations")
        total_donations = cur.fetchone()['total_donations']

        cur.execute("SELECT COUNT(*) AS total_deliveries FROM deliveries")
        total_deliveries = cur.fetchone()['total_deliveries']

        # Food donation statistics
        # Check if food_donations table exists
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'wastenofood' AND table_name = 'food_donations'
        """)
        result = cur.fetchone()
        table_exists = result['COUNT(*)'] if result['COUNT(*)'] is not None else 0
        
        if table_exists > 0:
            # Check if user_id column exists
            cur.execute("SHOW COLUMNS FROM food_donations LIKE 'user_id'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE food_donations ADD COLUMN user_id INT, ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL")
                mysql.connection.commit()

            cur.execute("SELECT COUNT(DISTINCT donor_name) AS food_donors_count FROM food_donations")
            food_donors_count = cur.fetchone()['food_donors_count']
            
            cur.execute("SELECT COUNT(*) AS total_food_donations FROM food_donations")
            total_food_donations = cur.fetchone()['total_food_donations']
            
            cur.execute("""
                SELECT * FROM food_donations 
                ORDER BY created_at DESC 
                LIMIT 10
            """)
            recent_food_donations = cur.fetchall()
        else:
            # Create food_donations table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS food_donations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    donor_name VARCHAR(100),
                    donor_phone VARCHAR(15),
                    donor_address TEXT,
                    food_type VARCHAR(50),
                    quantity VARCHAR(50),
                    time_available VARCHAR(50),
                    note TEXT,
                    status VARCHAR(20) DEFAULT 'Pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            mysql.connection.commit()
            food_donors_count = 0
            total_food_donations = 0
            recent_food_donations = []

        # Transaction statistics
        cur.execute("SELECT COUNT(*) AS total_transactions FROM donations")
        total_transactions = cur.fetchone()['total_transactions']
        
        cur.execute("SELECT COUNT(*) AS completed_transactions FROM donations WHERE status = 'completed'")
        completed_transactions = cur.fetchone()['completed_transactions']
        
        cur.execute("SELECT COUNT(*) AS pending_transactions FROM donations WHERE status = 'pending'")
        pending_transactions = cur.fetchone()['pending_transactions']
        
        cur.execute("""
            SELECT d.*, u.name AS user_name, n.name AS ngo_name,
                   (SELECT COUNT(*) FROM donations d2 WHERE d2.user_id = d.user_id) AS user_donation_count
            FROM donations d
            LEFT JOIN users u ON d.user_id = u.id
            LEFT JOIN ngos n ON d.ngo_id = n.id
            ORDER BY d.created_at DESC
        """)
        all_transactions = cur.fetchall()

        # Recent activities
        cur.execute("""
            SELECT d.*, u.name AS user_name, n.name AS ngo_name
            FROM donations d
            LEFT JOIN users u ON d.user_id = u.id
            LEFT JOIN ngos n ON d.ngo_id = n.id
            ORDER BY d.created_at DESC
            LIMIT 10
        """)
        recent_activities = cur.fetchall()

        # User transaction counts
        cur.execute("""
            SELECT u.name, COUNT(d.id) AS transaction_count, COALESCE(SUM(d.amount), 0) AS total_amount
            FROM users u
            LEFT JOIN donations d ON u.id = d.user_id
            GROUP BY u.id, u.name
            ORDER BY transaction_count DESC
        """)
        user_transaction_stats = cur.fetchall()

        cur.close()

        return render_template('admin_dashboard.html',
                               total_users=total_users,
                               total_ngos=total_ngos,
                               total_donations=total_donations,
                               total_deliveries=total_deliveries,
                               food_donors_count=food_donors_count,
                               total_food_donations=total_food_donations,
                               recent_food_donations=recent_food_donations,
                               total_transactions=total_transactions,
                               completed_transactions=completed_transactions,
                               pending_transactions=pending_transactions,
                               all_transactions=all_transactions,
                               activities=recent_activities,
                               user_transaction_stats=user_transaction_stats)

    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('index'))

# ==================== NGO & Donation ====================

@app.route('/ngos')
def ngos():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM ngos ORDER BY name")
        ngos_list = cur.fetchall()
        cur.close()
        return render_template('ngos.html', ngos=ngos_list)
    except Exception as e:
        flash(f'Error loading NGOs: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/ngo/<int:ngo_id>')
def ngo_detail(ngo_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM ngos WHERE id = %s", (ngo_id,))
        ngo = cur.fetchone()
        cur.close()

        if not ngo:
            flash('NGO not found!', 'danger')
            return redirect(url_for('ngos'))

        return render_template('ngo_detail.html', ngo=ngo)
    except Exception as e:
        flash(f'Error loading NGO details: {str(e)}', 'danger')
        return redirect(url_for('ngos'))


@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Please login to make a donation!', 'warning')
            return redirect(url_for('login'))

        amount = request.form.get('amount')
        ngo_id = request.form.get('ngo_id')
        if not ngo_id:  # Convert empty string to None for DB
            ngo_id = None
        payment_method = request.form.get('payment_method', 'card')

        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO donations (user_id, ngo_id, amount, payment_method, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session['user_id'], ngo_id, amount, payment_method, 'completed', datetime.now()))
            mysql.connection.commit()
            cur.close()

            return redirect(url_for('payment_success'))

        except Exception as e:
            flash(f'Payment failed: {str(e)}', 'danger')
            return redirect(url_for('payment'))

    ngo_name = request.args.get('ngo', '')
    ngo_id = request.args.get('ngo_id', '')
    return render_template('payment.html', ngo_name=ngo_name, ngo_id=ngo_id)


@app.route('/payment_success')
def payment_success():
    return render_template('payment_success.html')


@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM admins WHERE email = %s", (email,))
            admin = cur.fetchone()
            cur.close()
            if admin and check_password_hash(admin['password'], password):
                session['user_id'] = admin['id']
                session['user_name'] = admin['name']
                session['user_type'] = 'admin'
                flash('Admin Login Successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials!', 'danger')
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
    return render_template('admin_login.html')


@app.route('/food_donation', methods=['GET', 'POST'])
def food_donation():
    if request.method == "POST":
        # Get data from either the original form or the new modal form
        donor_name = request.form.get("donor_name") or session.get('user_name', 'Guest')
        donor_phone = request.form.get("donor_phone") or request.form.get("phone")
        donor_address = request.form.get("donor_address") or request.form.get("address")
        food_type = request.form.get("food_type")
        quantity = request.form.get("quantity")
        time_available = request.form.get("time_available") or request.form.get("expiry")
        note = request.form.get("note") or request.form.get("food_name")
        ngo_id = request.form.get("ngo_id")  # Get selected NGO
        
        try:
            cur = mysql.connection.cursor()
            user_id = session.get('user_id')
            
            # Get NGO name for success message
            ngo_name = "N/A"
            if ngo_id:
                cur.execute("SELECT name FROM ngos WHERE id = %s", (ngo_id,))
                ngo = cur.fetchone()
                if ngo:
                    ngo_name = ngo['name']
            
            # Insert into food_donations table (for simple tracking)
            cur.execute("""
                INSERT INTO food_donations 
                (user_id, donor_name, donor_phone, donor_address, food_type, quantity, time_available, note, ngo_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, donor_name, donor_phone, donor_address, food_type, quantity, time_available, note, ngo_id))
            
            # Also insert into donations_tracking table (for full tracking with OTP)
            if ngo_id:
                # Generate unique donation ID
                donation_id = generate_unique_donation_id()
                # Generate OTP for verification
                otp_code = generate_otp()
                
                cur.execute("""
                    INSERT INTO donations_tracking 
                    (donation_id, donor_name, donor_id, ngo_id, food_quantity, location, otp_code)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (donation_id, donor_name, user_id, ngo_id, f"{quantity} {food_type}", donor_address, otp_code))
            
            mysql.connection.commit()
            cur.close()
            
            # Flash success message with NGO information
            if ngo_id:
                flash(f"Your food donation has been submitted successfully! It will be donated to {ngo_name}. You can track it in 'Your Donations'.", "success")
            else:
                flash("Your food donation has been submitted successfully!", "success")
                
        except Exception as e:
            flash(f"Error submitting donation: {str(e)}", "danger")
            return redirect(url_for('food_donation'))
            
        return redirect(url_for('food_donation', success=1))
    
    # For GET request, get NGOs for the dropdown
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name FROM ngos WHERE is_active = TRUE AND is_verified = TRUE ORDER BY name")
        ngos = cur.fetchall()
        cur.close()
        
        # Get selected NGO from URL parameters
        selected_ngo_id = request.args.get('ngo_id', type=int)
        selected_ngo_name = request.args.get('ngo_name', '')
        
        return render_template("food_donation.html", ngos=ngos, selected_ngo_id=selected_ngo_id, selected_ngo_name=selected_ngo_name)
    except Exception as e:
        flash(f"Error loading page: {str(e)}", "danger")
        return render_template("food_donation.html", ngos=[])


@app.route('/donate-food-track', methods=['GET', 'POST'])
def donate_food_track():
    if request.method == "POST":
        # Get form data
        donor_name = session.get('user_name', request.form.get('donor_name', 'Anonymous'))
        donor_id = session.get('user_id')
        ngo_id = request.form.get('ngo_id')
        food_quantity = request.form.get('food_quantity')
        location = request.form.get('location') or request.form.get('address')
        
        # Generate unique donation ID
        donation_id = generate_unique_donation_id()
        
        # Generate OTP for verification
        otp_code = generate_otp()
        
        try:
            cur = mysql.connection.cursor()
            
            # Insert into donations_tracking table
            cur.execute("""
                INSERT INTO donations_tracking 
                (donation_id, donor_name, donor_id, ngo_id, food_quantity, location, otp_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (donation_id, donor_name, donor_id, ngo_id, food_quantity, location, otp_code))
            
            mysql.connection.commit()
            cur.close()
            
            flash(f"Food donation tracked successfully! Your Donation ID is {donation_id}", "success")
            return redirect(url_for('donor_dashboard'))
        
        except Exception as e:
            flash(f"Error tracking donation: {str(e)}", "danger")
            return redirect(url_for('donate_food_track'))
    
    # For GET request, get all verified NGOs
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, contact_email FROM ngos WHERE is_active = TRUE AND is_verified = TRUE ORDER BY name")
        ngos = cur.fetchall()
        cur.close()
        return render_template("donate_food_track.html", ngos=ngos, selected_ngo=None)
    except Exception as e:
        flash(f"Error loading page: {str(e)}", "danger")
        return redirect(url_for('index'))


@app.route('/composite')
def composite():
    return render_template('composite.html')


@app.route('/eco')
def eco():
    return render_template('eco.html')


@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    try:
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '')
        user_id = session.get('user_id')
        
        if not rating or rating < 1 or rating > 5:
            flash('Please provide a valid rating (1-5 stars)', 'danger')
            return redirect(url_for('support'))
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO feedback (user_id, rating, comment, created_at)
            VALUES (%s, %s, %s, %s)
        """, (user_id, rating, comment, datetime.now()))
        mysql.connection.commit()
        cur.close()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('support'))
        
    except Exception as e:
        flash(f'Error submitting feedback: {str(e)}', 'danger')
        return redirect(url_for('support'))

@app.route('/submit_issue', methods=['POST'])
def submit_issue():
    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        user_id = session.get('user_id')
        
        if not title or not description:
            flash('Please provide both title and description', 'danger')
            return redirect(url_for('support'))
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO issues (user_id, title, description, status, priority, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, title, description, 'new', 'medium', datetime.now()))
        mysql.connection.commit()
        cur.close()
        
        flash('Issue submitted successfully! Our team will look into it.', 'success')
        return redirect(url_for('support'))
        
    except Exception as e:
        flash(f'Error submitting issue: {str(e)}', 'danger')
        return redirect(url_for('support'))

@app.route('/admin/feedback')
def admin_feedback():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Admin access required!', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        cur = mysql.connection.cursor()
        
        # Get feedback
        cur.execute("""
            SELECT f.*, u.name as user_name, u.email as user_email
            FROM feedback f
            LEFT JOIN users u ON f.user_id = u.id
            ORDER BY f.created_at DESC
        """)
        feedback_list = cur.fetchall()
        
        # Get issues
        cur.execute("""
            SELECT i.*, u.name as user_name, u.email as user_email
            FROM issues i
            LEFT JOIN users u ON i.user_id = u.id
            ORDER BY i.created_at DESC
        """)
        issues_list = cur.fetchall()
        
        # Get statistics
        cur.execute("SELECT COUNT(*) as total_feedback FROM feedback")
        total_feedback = cur.fetchone()['total_feedback']
        
        cur.execute("SELECT COUNT(*) as total_issues FROM issues")
        total_issues = cur.fetchone()['total_issues']
        
        cur.execute("SELECT AVG(rating) as avg_rating FROM feedback")
        avg_rating = cur.fetchone()['avg_rating']
        
        cur.close()
        
        return render_template('admin_feedback.html', 
                             feedback=feedback_list, 
                             issues=issues_list,
                             total_feedback=total_feedback,
                             total_issues=total_issues,
                             avg_rating=round(avg_rating or 0, 1))
        
    except Exception as e:
        flash(f'Error loading feedback: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))


# ==================== NGO REGISTRATION & VERIFICATION ====================

@app.route('/ngo/register', methods=['GET', 'POST'])
def ngo_register():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        address = request.form.get('address')
        registration_number = request.form.get('registration_number')
        contact_person = request.form.get('contact_person')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Handle file upload
        government_id = request.files.get('government_id')
        
        # Validate required fields
        if not all([name, address, registration_number, contact_person, phone, email, password]):
            flash('All fields are required!', 'danger')
            return redirect(url_for('ngo_register'))
        
        # Validate file upload
        if not government_id or government_id.filename == '':
            flash('Government ID document is required!', 'danger')
            return redirect(url_for('ngo_register'))
        
        if not allowed_file(government_id.filename):
            flash('Invalid file type. Please upload PDF, JPG, or PNG.', 'danger')
            return redirect(url_for('ngo_register'))
        
        # Save the file
        filename = secure_filename(government_id.filename)
        unique_filename = f"ngo_{registration_number}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        government_id.save(file_path)
        
        # Hash password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        try:
            cur = mysql.connection.cursor()
            
            # Check if email or registration number already exists
            cur.execute("SELECT * FROM unverified_ngos WHERE email = %s OR registration_number = %s", (email, registration_number))
            existing_ngo = cur.fetchone()
            
            if existing_ngo:
                flash('Email or registration number already exists!', 'danger')
                cur.close()
                return redirect(url_for('ngo_register'))
            
            # Insert directly into verified ngos table
            cur.execute("""
                INSERT INTO ngos 
                (name, description, mission, process, activities, impact, contact_email, contact_phone, address, website, logo_url, image_url, is_active, is_verified, registration_number, contact_person, government_id_path, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, '', '', '', '', '', email, phone, address, '', '', '', True, True, registration_number, contact_person, unique_filename, hashed_password))
            
            mysql.connection.commit()
            cur.close()
            
            flash('NGO registration submitted successfully! Awaiting admin approval.', 'success')
            return redirect(url_for('ngo_login'))
        
        except Exception as e:
            flash(f'NGO registration failed: {str(e)}', 'danger')
            return redirect(url_for('ngo_register'))
    
    return render_template('ngo_registration.html')


@app.route('/ngo/login', methods=['GET', 'POST'])
def ngo_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required!', 'danger')
            return redirect(url_for('ngo_login'))
        
        try:
            cur = mysql.connection.cursor()
            
            # First check in unverified_ngos table
            cur.execute("SELECT * FROM unverified_ngos WHERE email = %s", (email,))
            unverified_ngo = cur.fetchone()
            
            if unverified_ngo:
                # No approval check - all registered NGOs can login
                # Check password directly
                if check_password_hash(unverified_ngo['password'], password):
                    session['ngo_id'] = unverified_ngo['id']
                    session['ngo_name'] = unverified_ngo['name']
                    session['ngo_email'] = unverified_ngo['email']
                    session['user_type'] = 'ngo'
                    
                    flash('NGO Login Successful!', 'success')
                    cur.close()
                    return redirect(url_for('ngo_dashboard'))
                else:
                    flash('Invalid email or password!', 'danger')
                    cur.close()
                    return redirect(url_for('ngo_login'))
            
            # If not found in unverified, check in verified ngos table
            cur.execute("SELECT * FROM ngos WHERE contact_email = %s AND is_verified = TRUE", (email,))
            verified_ngo = cur.fetchone()
            
            if verified_ngo:
                # Check if the verified NGO has a password set
                if verified_ngo['password']:
                    # Compare the password
                    if check_password_hash(verified_ngo['password'], password):
                        session['ngo_id'] = verified_ngo['id']
                        session['ngo_name'] = verified_ngo['name']
                        session['ngo_email'] = verified_ngo['contact_email']  # Updated to use contact_email
                        session['user_type'] = 'ngo'
                        
                        flash('NGO Login Successful!', 'success')
                        cur.close()
                        return redirect(url_for('ngo_dashboard'))
                    else:
                        flash('Invalid email or password!', 'danger')
                else:
                    flash('This NGO does not have a password set. Contact admin to reset your password.', 'warning')
            else:
                flash('Invalid email or password!', 'danger')
            
            cur.close()
            return redirect(url_for('ngo_login'))
        
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'danger')
            return redirect(url_for('ngo_login'))
    
    return render_template('ngo_login.html')


@app.route('/ngo/dashboard')
def ngo_dashboard():
    if 'ngo_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('ngo_login'))
    
    # No approval check needed - any registered NGO can access dashboard
    try:
        cur = mysql.connection.cursor()
        ngo_id = session['ngo_id']
        
        # Simply verify NGO exists either in unverified or verified table
        cur.execute("SELECT id FROM unverified_ngos WHERE id = %s", (ngo_id,))
        unverified_ngo = cur.fetchone()
        
        if not unverified_ngo:
            # Check if NGO exists in verified table
            cur.execute("SELECT id FROM ngos WHERE id = %s", (ngo_id,))
            verified_ngo = cur.fetchone()
            if not verified_ngo:
                flash('Access denied. NGO not found.', 'danger')
                cur.close()
                return redirect(url_for('ngo_login'))
        
        # Get pending donations for this NGO (food donations)
        cur.execute("""
            SELECT dt.*, u.name as donor_name
            FROM donations_tracking dt
            LEFT JOIN users u ON dt.donor_id = u.id
            WHERE dt.ngo_id = %s
            ORDER BY dt.created_at DESC
        """, (ngo_id,))
        food_donations = cur.fetchall()
        
        # Get leftover food reports assigned to this NGO
        cur.execute("""
            SELECT lfr.*, u.name as reporter_name
            FROM leftover_food_reports lfr
            LEFT JOIN users u ON lfr.contact_number = u.phone
            WHERE lfr.ngo_id = %s
            ORDER BY lfr.created_at DESC
        """, (ngo_id,))
        leftover_reports = cur.fetchall()
        
        # Get combined stats
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM donations_tracking WHERE ngo_id = %s) +
                (SELECT COUNT(*) FROM leftover_food_reports WHERE ngo_id = %s) as total_donations,
                (SELECT SUM(CASE WHEN status = 'Pending' OR status = 'Reported' OR status = 'NGO_Assigned' THEN 1 ELSE 0 END) 
                 FROM (SELECT status FROM donations_tracking WHERE ngo_id = %s 
                       UNION ALL SELECT status FROM leftover_food_reports WHERE ngo_id = %s) as all_statuses) as pending_donations,
                (SELECT SUM(CASE WHEN status = 'Completed' OR status = 'Picked_Up' THEN 1 ELSE 0 END) 
                 FROM (SELECT status FROM donations_tracking WHERE ngo_id = %s 
                       UNION ALL SELECT status FROM leftover_food_reports WHERE ngo_id = %s) as all_statuses) as completed_donations
        """, (ngo_id, ngo_id, ngo_id, ngo_id, ngo_id, ngo_id))
        stats = cur.fetchone()
        
        cur.close()
        
        return render_template('ngo_dashboard.html', food_donations=food_donations, leftover_reports=leftover_reports, stats=stats)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('ngo_login'))


@app.route('/ngo/logout')
def ngo_logout():
    session.pop('ngo_id', None)
    session.pop('ngo_name', None)
    session.pop('ngo_email', None)
    session.pop('user_type', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))


@app.route('/ngo/<int:ngo_id>/donations')
def ngo_donations_dashboard(ngo_id):
    # Check if NGO is logged in and matches the requested NGO
    if 'ngo_id' not in session or session['ngo_id'] != ngo_id:
        flash('Access denied. Please login as the NGO.', 'warning')
        return redirect(url_for('ngo_login'))
    
    try:
        cur = mysql.connection.cursor()
        
        # Get NGO details
        cur.execute("SELECT name, description FROM ngos WHERE id = %s", (ngo_id,))
        ngo = cur.fetchone()
        
        if not ngo:
            flash('NGO not found!', 'danger')
            return redirect(url_for('ngo_login'))
        
        # Get donations made to this NGO
        cur.execute("""
            SELECT d.*, u.name as donor_name, u.email as donor_email
            FROM donations d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.ngo_id = %s
            ORDER BY d.created_at DESC
        """, (ngo_id,))
        donations = cur.fetchall()
        
        # Get statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_donations,
                COALESCE(SUM(amount), 0) as total_amount,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_donations,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_donations
            FROM donations 
            WHERE ngo_id = %s
        """, (ngo_id,))
        stats = cur.fetchone()
        
        cur.close()
        
        return render_template('ngo_donations_dashboard.html', ngo=ngo, donations=donations, stats=stats)
        
    except Exception as e:
        flash(f'Error loading NGO dashboard: {str(e)}', 'danger')
        return redirect(url_for('ngo_login'))


@app.route('/admin/ngos/pending')
def admin_pending_ngos():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Admin access required!', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM unverified_ngos ORDER BY created_at DESC")
        pending_ngos = cur.fetchall()
        cur.close()
        
        return render_template('admin_pending_ngos.html', ngos=pending_ngos)
    
    except Exception as e:
        flash(f'Error loading pending NGOs: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/ngos/approve/<int:ngo_id>', methods=['POST'])
def admin_approve_ngo(ngo_id):
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Admin access required!', 'danger')
        return redirect(url_for('admin_login'))
    
    try:
        print(f"Approve route hit for NGO ID: {ngo_id}")  # Debug print
        cur = mysql.connection.cursor()
        
        # Get NGO details from unverified table
        cur.execute("SELECT * FROM unverified_ngos WHERE id = %s", (ngo_id,))
        ngo = cur.fetchone()
        
        if not ngo:
            flash('NGO not found!', 'danger')
            cur.close()
            return redirect(url_for('admin_pending_ngos'))
        
        # Check if NGO already exists in verified table to avoid duplicates
        cur.execute("SELECT id FROM ngos WHERE email = %s", (ngo['email'],))
        existing_ngo = cur.fetchone()
        
        if not existing_ngo:
            # Move NGO to verified ngos table
            cur.execute("""
                INSERT INTO ngos (name, description, mission, process, activities, impact, contact_email, contact_phone, address, website, logo_url, image_url, is_active, is_verified, registration_number, contact_person, government_id_path, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ngo['name'], '', '', '', '', '', ngo['email'], ngo['phone'], ngo['address'], '', '', '', True, True,
                ngo['registration_number'], ngo['contact_person'], ngo['government_id_path'], ngo['password']
            ))
        
        # Delete from unverified table after moving to verified table
        cur.execute("DELETE FROM unverified_ngos WHERE id = %s", (ngo_id,))
        
        mysql.connection.commit()
        cur.close()
        
        flash('NGO approved successfully and moved to verified list!', 'success')
        return redirect(url_for('admin_pending_ngos'))
    
    except Exception as e:
        flash(f'Error approving NGO: {str(e)}', 'danger')
        return redirect(url_for('admin_pending_ngos'))


@app.route('/admin/ngos/reject/<int:ngo_id>', methods=['POST'])
def admin_reject_ngo(ngo_id):
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Admin access required!', 'danger')
        return redirect(url_for('admin_login'))
    
    reason = request.form.get('reason', '')
    
    try:
        print(f"Reject route hit for NGO ID: {ngo_id}")  # Debug print
        cur = mysql.connection.cursor()
        
        # Delete from unverified table after rejection
        cur.execute("DELETE FROM unverified_ngos WHERE id = %s", (ngo_id,))
        
        mysql.connection.commit()
        cur.close()
        
        flash('NGO rejected successfully and removed from pending list!', 'success')
        return redirect(url_for('admin_pending_ngos'))
    
    except Exception as e:
        flash(f'Error rejecting NGO: {str(e)}', 'danger')
        return redirect(url_for('admin_pending_ngos'))


@app.route('/ngo/proof-of-delivery', methods=['GET', 'POST'])
def ngo_proof_of_delivery():
    if 'ngo_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('ngo_login'))
    
    if request.method == 'POST':
        donation_id = request.form.get('donation_id')
        ngo_representative = request.form.get('ngo_representative')
        otp_code = request.form.get('otp_code')
        proof_image = request.files.get('proof_image')
        
        # Validate required fields
        if not all([donation_id, ngo_representative]):
            flash('All required fields must be filled!', 'danger')
            return redirect(url_for('ngo_proof_of_delivery'))
        
        # Handle proof image upload
        proof_image_path = None
        if proof_image and proof_image.filename != '':
            if not allowed_file(proof_image.filename):
                flash('Invalid file type for proof image. Please upload PDF, JPG, or PNG.', 'danger')
                return redirect(url_for('ngo_proof_of_delivery'))
            
            filename = secure_filename(proof_image.filename)
            unique_filename = f"proof_{donation_id}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            proof_image.save(file_path)
            proof_image_path = unique_filename
        
        try:
            cur = mysql.connection.cursor()
            
            # Update donation status to 'Completed'
            cur.execute("""
                UPDATE donations_tracking 
                SET status = 'Completed', collected_at = %s, proof_image_path = %s, ngo_representative = %s, otp_verified = TRUE
                WHERE donation_id = %s AND status != 'Completed'
            """, (datetime.now(), proof_image_path, ngo_representative, donation_id))
            
            # Also update the food_donations table status if it exists
            cur.execute("""
                UPDATE food_donations fd
                JOIN donations_tracking dt ON fd.user_id = dt.donor_id OR fd.donor_name = dt.donor_name
                SET fd.status = 'Completed'
                WHERE dt.donation_id = %s AND fd.status = 'Pending'
            """, (donation_id,))
            
            mysql.connection.commit()
            cur.close()
            
            flash('Delivery confirmed successfully! Status updated to Completed.', 'success')
            return redirect(url_for('ngo_dashboard'))
        
        except Exception as e:
            flash(f'Error confirming delivery: {str(e)}', 'danger')
            return redirect(url_for('ngo_proof_of_delivery'))
    
    # For GET request, show pending donations
    try:
        cur = mysql.connection.cursor()
        ngo_id = session['ngo_id']
        
        # Get pending donations assigned to this NGO
        cur.execute("""
            SELECT * FROM donations_tracking 
            WHERE ngo_id = %s AND status = 'Pending'
            ORDER BY created_at ASC
        """, (ngo_id,))
        pending_donations = cur.fetchall()
        
        cur.close()
        
        return render_template('proof_of_delivery.html', donations=pending_donations)
    
    except Exception as e:
        flash(f'Error loading delivery page: {str(e)}', 'danger')
        return redirect(url_for('ngo_dashboard'))


@app.route('/donor/dashboard')
def donor_dashboard():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    try:
        cur = mysql.connection.cursor()
        user_id = session['user_id']
        user_name = session.get('user_name')
        
        # Get all donations made by this donor
        cur.execute("""
            SELECT dt.*, n.name as ngo_name, u.name as donor_name
            FROM donations_tracking dt
            LEFT JOIN ngos n ON dt.ngo_id = n.id
            LEFT JOIN users u ON dt.donor_id = u.id
            WHERE dt.donor_id = %s OR dt.donor_name = %s
            ORDER BY dt.created_at DESC
        """, (user_id, user_name))
        donations = cur.fetchall()
        
        # Get stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_donations,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_donations,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_donations
            FROM donations_tracking 
            WHERE donor_id = %s OR donor_name = %s
        """, (user_id, user_name))
        stats = cur.fetchone()
        
        cur.close()
        
        return render_template('donor_dashboard.html', donations=donations, stats=stats)
    
    except Exception as e:
        flash(f'Error loading donor dashboard: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/user/donation-tracking')
def user_donation_tracking():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    try:
        cur = mysql.connection.cursor()
        user_id = session['user_id']
        user_name = session.get('user_name')
        
        # Get all donations made by this user
        cur.execute("""
            SELECT dt.*, n.name as ngo_name, u.name as donor_name
            FROM donations_tracking dt
            LEFT JOIN ngos n ON dt.ngo_id = n.id
            LEFT JOIN users u ON dt.donor_id = u.id
            WHERE dt.donor_id = %s OR dt.donor_name = %s
            ORDER BY dt.created_at DESC
        """, (user_id, user_name))
        donations = cur.fetchall()
        
        # Get stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_donations,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_donations,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_donations
            FROM donations_tracking 
            WHERE donor_id = %s OR donor_name = %s
        """, (user_id, user_name))
        stats = cur.fetchone()
        
        cur.close()
        
        return render_template('user_donation_tracking.html', donations=donations, stats=stats)
    
    except Exception as e:
        flash(f'Error loading donation tracking: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/user/leftover-reports')
def user_leftover_reports():
    if 'user_id' not in session:
        flash('Please login first!', 'warning')
        return redirect(url_for('login'))
    
    try:
        cur = mysql.connection.cursor()
        user_id = session['user_id']
        
        # Get all leftover food reports by this user
        cur.execute("""
            SELECT lfr.*, n.name as ngo_name
            FROM leftover_food_reports lfr
            LEFT JOIN ngos n ON lfr.ngo_id = n.id
            WHERE lfr.user_id = %s
            ORDER BY lfr.created_at DESC
        """, (user_id,))
        reports = cur.fetchall()
        
        # Get stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_reports,
                SUM(CASE WHEN status IN ('Reported', 'NGO_Assigned') THEN 1 ELSE 0 END) as pending_reports,
                SUM(CASE WHEN status IN ('Picked_Up', 'Completed') THEN 1 ELSE 0 END) as completed_reports
            FROM leftover_food_reports 
            WHERE user_id = %s
        """, (user_id,))
        stats = cur.fetchone()
        
        cur.close()
        
        return render_template('user_leftover_reports.html', reports=reports, stats=stats)
        
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/ngo/accept-leftover-report', methods=['POST'])
def accept_leftover_report():
    if 'ngo_id' not in session:
        flash('Please login as NGO first!', 'warning')
        return redirect(url_for('ngo_login'))
    
    report_id = request.form.get('report_id')
    if not report_id:
        flash('Invalid request!', 'danger')
        return redirect(url_for('ngo_dashboard'))
    
    try:
        cur = mysql.connection.cursor()
        ngo_id = session['ngo_id']
        
        # Verify that this report is assigned to this NGO
        cur.execute("""
            SELECT * FROM leftover_food_reports 
            WHERE id = %s AND ngo_id = %s
        """, (report_id, ngo_id))
        report = cur.fetchone()
        
        if not report:
            flash('Report not found or not assigned to your NGO!', 'danger')
            cur.close()
            return redirect(url_for('ngo_dashboard'))
        
        # Update status to Completed
        cur.execute("""
            UPDATE leftover_food_reports 
            SET status = 'Completed', updated_at = NOW()
            WHERE id = %s
        """, (report_id,))
        
        mysql.connection.commit()
        cur.close()
        
        flash('Report marked as completed successfully!', 'success')
        return redirect(url_for('ngo_dashboard'))
        
    except Exception as e:
        flash(f'Error updating report: {str(e)}', 'danger')
        return redirect(url_for('ngo_dashboard'))


@app.route('/api/calculate_impact', methods=['POST'])
def calculate_impact():
    data = request.get_json()
    weekly_waste = float(data.get('weekly_waste', 5))
    annual_waste = weekly_waste * 52
    return jsonify({
        'annual_waste': round(annual_waste, 2),
        'money_saved': round(annual_waste * 150, 2),
        'co2_impact': round(annual_waste * 2.5, 2),
        'meals_equiv': round(annual_waste * 3, 2)
    })


@app.route('/donate-to-ngo/<int:ngo_id>')
def donate_to_ngo(ngo_id):
    try:
        cur = mysql.connection.cursor()
        
        # Get NGO details
        cur.execute("SELECT id, name FROM ngos WHERE id = %s AND is_active = TRUE AND is_verified = TRUE", (ngo_id,))
        ngo = cur.fetchone()
        
        if not ngo:
            flash('Selected NGO not found or not active.', 'danger')
            return redirect(url_for('ngos'))
        
        cur.close()
        
        # Redirect to food donation page with NGO pre-selected
        return redirect(url_for('food_donation') + f'?ngo_id={ngo_id}&ngo_name={ngo["name"]}')
    
    except Exception as e:
        flash(f"Error loading donation page: {str(e)}", "danger")
        return redirect(url_for('ngos'))

# ==================== RUN APP ====================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
