from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
import os
import uuid
import json
from dotenv import load_dotenv
from flask_session import Session

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")

# Load environment variables
load_dotenv()

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "hello")
app.secret_key = app.config["SECRET_KEY"]

# Initialize Flask-SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Gokul_12345"),
    "database": os.getenv("DB_NAME", "arogyam"),
}

# Database connection function
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# Import the medical AI modules
from models import (
    GroqChatClient,
    VisionModelClient,
    MedicalRAGPipeline,
    SPECIALIST_PROMPTS
)

# Routes
@app.route("/")
def home():
    return render_template("1main.html")

@app.route("/debug/check-tables")
def debug_check_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check prescriptions table
        cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = 'arogyam' AND TABLE_NAME = 'prescriptions'
        """)
        prescriptions_exists = cursor.fetchone()['count'] > 0

        # Check prescription_medicines table
        cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = 'arogyam' AND TABLE_NAME = 'prescription_medicines'
        """)
        medicines_exists = cursor.fetchone()['count'] > 0

        # Count prescriptions
        if prescriptions_exists:
            cursor.execute("SELECT COUNT(*) as count FROM prescriptions")
            prescription_count = cursor.fetchone()['count']
        else:
            prescription_count = "table doesn't exist"

        cursor.close()
        conn.close()

        return {
            "prescriptions_table_exists": prescriptions_exists,
            "prescription_medicines_table_exists": medicines_exists,
            "total_prescriptions": prescription_count
        }
    except Exception as e:
        return {"error": str(e)}

@app.route("/doctor")
def doctor_consultation():
    return render_template("2dp.html")

@app.route("/patient")
def patient_portal():
    return render_template("pl.html")

@app.route("/pharmacist")
def pharmacist_portal():
    return render_template("pharmacist_registration.html")

@app.route("/register_pharmacist", methods=["POST"])
def register_pharmacist():
    try:
        # Get form data
        pharmacy_name = request.form.get('pharmacy_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        postal_code = request.form.get('postal_code')
        country = request.form.get('country', 'India')
        description = request.form.get('description')
        license_number = request.form.get('license_number')
        website = request.form.get('website', '')
        opening_hours_from = request.form.get('opening_hours_from')
        opening_hours_to = request.form.get('opening_hours_to')

        # Validate required fields
        if not all([pharmacy_name, email, phone, address, city, state, postal_code, description, license_number]):
            return jsonify({"error": "Please fill all required fields"}), 400

        # Check if email or license already exists
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM pharmacists WHERE email = %s OR license_number = %s", (email, license_number))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "A pharmacy with this email or license number already exists"}), 400

        # Insert into database
        insert_query = """
        INSERT INTO pharmacists (
            pharmacy_name, email, phone, address, city, state, postal_code, country,
            description, license_number, website, opening_hours_from, opening_hours_to
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        """

        cursor.execute(insert_query, (
            pharmacy_name, email, phone, address, city, state, postal_code, country,
            description, license_number, website or None,
            opening_hours_from or None, opening_hours_to or None
        ))

        conn.commit()
        pharmacist_id = cursor.lastrowid
        cursor.close()
        conn.close()

        # Redirect to dashboard with success message
        session['pharmacist_id'] = pharmacist_id
        session['success_message'] = f"Welcome {pharmacy_name}! Your pharmacy has been successfully registered."
        
        return redirect(url_for('pharmacist_dashboard', pharmacist_id=pharmacist_id))

    except Exception as e:
        print(f"Error registering pharmacist: {str(e)}")
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route("/pharmacist_dashboard/<int:pharmacist_id>")
def pharmacist_dashboard(pharmacist_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get pharmacist details
        cursor.execute("SELECT * FROM pharmacists WHERE id = %s", (pharmacist_id,))
        pharmacist = cursor.fetchone()

        if not pharmacist:
            cursor.close()
            conn.close()
            return redirect(url_for('home'))

        # Get success message from session
        success_message = session.pop('success_message', None)

        # Get customer orders with prescription details
        cursor.execute("""
            SELECT o.id as order_id, o.status, o.order_date, 
                   p.id as prescription_id, p.diagnosis, p.notes,
                   pm.medicine_name, pm.dosage, pm.duration, pm.instructions,
                   d.name as doctor_name, d.specialization,
                   pa.name as patient_name, pa.age as patient_age, pa.email as patient_email, pa.phone as patient_phone
            FROM orders o
            JOIN prescriptions p ON o.prescription_id = p.id
            JOIN prescription_medicines pm ON p.id = pm.prescription_id
            JOIN doctors d ON p.doctor_id = d.id
            JOIN patients pa ON p.patient_id = pa.id
            WHERE o.pharmacist_id = %s
            ORDER BY o.order_date DESC
        """, (pharmacist_id,))
        
        orders_raw = cursor.fetchall()
        
        # Group medicines by order
        orders = {}
        for row in orders_raw:
            order_id = row['order_id']
            if order_id not in orders:
                orders[order_id] = {
                    'id': order_id,
                    'status': row['status'],
                    'order_date': row['order_date'].strftime('%Y-%m-%d %H:%M') if row['order_date'] else 'N/A',
                    'prescription_id': row['prescription_id'],
                    'diagnosis': row['diagnosis'],
                    'notes': row['notes'],
                    'doctor_name': row['doctor_name'],
                    'doctor_specialization': row['specialization'],
                    'patient_name': row['patient_name'],
                    'patient_age': row['patient_age'],
                    'patient_email': row['patient_email'],
                    'patient_phone': row['patient_phone'],
                    'medicines': []
                }
            
            orders[order_id]['medicines'].append({
                'name': row['medicine_name'],
                'dosage': row['dosage'],
                'duration': row['duration'],
                'instructions': row['instructions']
            })
        
        orders_list = list(orders.values())
        total_orders = len(orders_list)
        
        # Count unique customers
        cursor.execute("""
            SELECT COUNT(DISTINCT p.patient_id) as total_customers
            FROM orders o
            JOIN prescriptions p ON o.prescription_id = p.id
            WHERE o.pharmacist_id = %s
        """, (pharmacist_id,))
        
        customer_count = cursor.fetchone()
        total_customers = customer_count['total_customers'] if customer_count else 0

        cursor.close()
        conn.close()

        return render_template(
            'pharmacist_dashboard.html',
            pharmacist=pharmacist,
            orders=orders_list,
            total_orders=total_orders,
            total_customers=total_customers,
            success_message=success_message
        )

    except Exception as e:
        print(f"Error loading pharmacist dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('home'))

@app.route("/update_pharmacist/<int:pharmacist_id>", methods=["POST"])
def update_pharmacist(pharmacist_id):
    try:
        # Get form data
        pharmacy_name = request.form.get('pharmacy_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        postal_code = request.form.get('postal_code')
        description = request.form.get('description')
        website = request.form.get('website', '')
        opening_hours_from = request.form.get('opening_hours_from')
        opening_hours_to = request.form.get('opening_hours_to')

        # Validate required fields
        if not all([pharmacy_name, email, phone, address, city, state, postal_code, description]):
            flash('Please fill all required fields', 'error')
            return redirect(url_for('pharmacist_dashboard', pharmacist_id=pharmacist_id))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if email already exists for other pharmacists
        cursor.execute("SELECT id FROM pharmacists WHERE email = %s AND id != %s", (email, pharmacist_id))
        if cursor.fetchone():
            flash('This email is already registered', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('pharmacist_dashboard', pharmacist_id=pharmacist_id))

        # Update pharmacist profile
        update_query = """
        UPDATE pharmacists SET
            pharmacy_name = %s,
            email = %s,
            phone = %s,
            address = %s,
            city = %s,
            state = %s,
            postal_code = %s,
            description = %s,
            website = %s,
            opening_hours_from = %s,
            opening_hours_to = %s
        WHERE id = %s
        """

        cursor.execute(update_query, (
            pharmacy_name, email, phone, address, city, state, postal_code, description,
            website or None, opening_hours_from or None, opening_hours_to or None, pharmacist_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('pharmacist_dashboard', pharmacist_id=pharmacist_id))

    except Exception as e:
        print(f"Error updating pharmacist: {str(e)}")
        flash('Error updating profile', 'error')
        return redirect(url_for('pharmacist_dashboard', pharmacist_id=pharmacist_id))

@app.route("/pharmacist_login", methods=["GET", "POST"])
def pharmacist_login():
    if request.method == "GET":
        return render_template("pharmacist_login.html")
    
    elif request.method == "POST":
        try:
            license_number = request.form.get('license_number', '').strip()

            # Validate input
            if not license_number:
                return render_template("pharmacist_login.html", error="Please enter your license number")

            # Query database for pharmacist
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT id FROM pharmacists WHERE license_number = %s", (license_number,))
            pharmacist = cursor.fetchone()

            cursor.close()
            conn.close()

            if not pharmacist:
                # Don't reveal if license exists or not for security
                return render_template("pharmacist_login.html", error="Invalid license number. Please check and try again.")

            # Set session and redirect to dashboard
            session['pharmacist_id'] = pharmacist['id']
            session['success_message'] = "Welcome back! You have successfully logged in to your dashboard."
            
            return redirect(url_for('pharmacist_dashboard', pharmacist_id=pharmacist['id']))

        except Exception as e:
            print(f"Error during pharmacist login: {str(e)}")
            return render_template("pharmacist_login.html", error="An error occurred. Please try again.")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("home"))

@app.route("/ai")
def ai_consultation():
    return redirect(url_for("specialists"))

@app.route("/loginpatient", methods=["GET"])
def login_patient():
    return render_template("pl.html")

def get_specialists():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT specialization, 
               COUNT(*) AS count, 
               MIN(fees) AS min_fee, 
               MAX(fees) AS max_fee, 
               GROUP_CONCAT(DISTINCT available_days) AS days, 
               MIN(time_start) AS earliest_start, 
               MAX(time_end) AS latest_end
        FROM doctors
        GROUP BY specialization
    """)
    specialists = cursor.fetchall()
    cursor.close()
    conn.close()
    return specialists


CARE_REMINDERS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS patient_reminders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id INT NOT NULL,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    medicine_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(120),
    duration VARCHAR(120),
    instructions VARCHAR(255),
    meal_timing VARCHAR(50),
    reminder_time TIME NOT NULL,
    reminder_note VARCHAR(255),
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_patient_time (patient_id, reminder_time),
    INDEX idx_prescription (prescription_id),
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);
"""

CARE_DIET_PLANS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS patient_diet_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prescription_id INT NOT NULL,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    plan_text TEXT NOT NULL,
    generated_by VARCHAR(40) DEFAULT 'rule_based',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_prescription_diet (prescription_id),
    INDEX idx_patient_diet (patient_id),
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);
"""


def ensure_care_tables(cursor):
    cursor.execute(CARE_REMINDERS_TABLE_SQL)
    cursor.execute(CARE_DIET_PLANS_TABLE_SQL)


def _format_db_time(value):
    if value is None:
        return "--:--"

    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds()) % (24 * 3600)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    text_value = str(value)
    return text_value[:5] if len(text_value) >= 5 else text_value


def _infer_meal_timing(instructions):
    instructions_lower = str(instructions or "").lower()
    if "before" in instructions_lower:
        return "before food"
    if "after" in instructions_lower:
        return "after food"
    if "with food" in instructions_lower or "with meal" in instructions_lower:
        return "with food"
    return "as advised"


def _dosage_to_slots(dosage):
    slots = []
    slot_map = [
        ("morning", "08:00:00"),
        ("afternoon", "14:00:00"),
        ("night", "20:00:00"),
    ]

    cleaned = str(dosage or "").strip().replace(" ", "")
    parts = cleaned.split("-") if "-" in cleaned else []
    if len(parts) == 3:
        for idx, value in enumerate(parts):
            try:
                if float(value) > 0:
                    slots.append(slot_map[idx])
            except ValueError:
                continue

    if not slots:
        slots.append(("morning", "09:00:00"))

    return slots


def _build_diet_plan(diagnosis, medicines, notes=""):
    diagnosis_text = str(diagnosis or "General wellness").strip()
    notes_text = str(notes or "").strip()

    avoid_items = {
        "Highly processed packaged foods",
        "Sugary drinks",
        "Deep fried foods",
    }
    timing_notes = []

    diagnosis_lower = diagnosis_text.lower()
    if "diabet" in diagnosis_lower:
        avoid_items.add("Refined sugar and sweets")
    if "pressure" in diagnosis_lower or "hypertension" in diagnosis_lower:
        avoid_items.add("Excess salt and pickles")
    if "gastric" in diagnosis_lower or "acidity" in diagnosis_lower:
        avoid_items.add("Very spicy and acidic foods")

    for medicine in medicines:
        med_name = medicine.get("medicine_name", "Medicine")
        meal_timing = _infer_meal_timing(medicine.get("instructions"))
        if meal_timing == "before food":
            timing_notes.append(f"Take {med_name} 30 minutes before meals.")
        elif meal_timing == "after food":
            timing_notes.append(f"Take {med_name} after a full meal.")
        elif meal_timing == "with food":
            timing_notes.append(f"Take {med_name} with food to reduce stomach irritation.")

    if not timing_notes:
        timing_notes.append("Take medicines exactly as prescribed by your doctor.")

    if notes_text:
        timing_notes.append(f"Doctor advice: {notes_text}")

    return {
        "summary": f"Diet plan generated for: {diagnosis_text}",
        "breakfast": [
            "Idli or oats with vegetables",
            "1 boiled egg or sprouts",
            "Unsweetened milk or buttermilk",
        ],
        "lunch": [
            "1 portion rice or roti with dal",
            "Cooked vegetables and salad",
            "Lean protein (fish/chicken/paneer) in moderate quantity",
        ],
        "dinner": [
            "Light meal: roti + vegetable curry",
            "Soup or steamed vegetables",
            "Avoid heavy meals late night",
        ],
        "hydration": [
            "Drink 2 to 2.5 liters of water daily",
            "Limit caffeinated/sugary beverages",
        ],
        "avoid": sorted(list(avoid_items)),
        "timing_notes": timing_notes,
    }


def _get_patient_notifications(cursor, patient_id, limit=5):
    cursor.execute(
        """
        SELECT pr.id, pr.prescription_id, pr.medicine_name, pr.reminder_time,
               pr.meal_timing, pr.reminder_note, d.name AS doctor_name
        FROM patient_reminders pr
        JOIN doctors d ON pr.doctor_id = d.id
        WHERE pr.patient_id = %s AND pr.is_active = 1
        ORDER BY pr.reminder_time ASC, pr.id DESC
        """,
        (patient_id,),
    )

    reminders = cursor.fetchall() or []
    if not reminders:
        return []

    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute
    notifications = []

    for reminder in reminders:
        time_hhmm = _format_db_time(reminder.get("reminder_time"))
        try:
            hours, minutes = [int(part) for part in time_hhmm.split(":")]
            delta = (hours * 60 + minutes) - now_minutes
        except Exception:
            delta = 999

        status = "later"
        if -30 <= delta <= 45:
            status = "due_now"
        elif 45 < delta <= 360:
            status = "upcoming"

        notifications.append(
            {
                "medicine_name": reminder.get("medicine_name", "Medicine"),
                "doctor_name": reminder.get("doctor_name", "Doctor"),
                "reminder_time": time_hhmm,
                "meal_timing": reminder.get("meal_timing", "as advised"),
                "reminder_note": reminder.get("reminder_note", ""),
                "status": status,
            }
        )

    notifications.sort(key=lambda item: {"due_now": 0, "upcoming": 1, "later": 2}[item["status"]])
    return notifications[:limit]

# 🔹 Patient Dashboard Route
@app.route("/patient_dashboard")
def patient_dashboard():
    specialists = get_specialists()
    patient_id = session.get("patient_id")

    patient_notifications = []
    prescription_care = []

    if patient_id:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            ensure_care_tables(cursor)
            cursor.execute(
                """
                SELECT p.id, p.patient_id, p.doctor_id, p.diagnosis, p.created_date,
                       d.name AS doctor_name, d.specialization,
                       (
                           SELECT COUNT(*)
                           FROM patient_reminders pr
                           WHERE pr.prescription_id = p.id
                             AND pr.patient_id = p.patient_id
                             AND pr.is_active = 1
                       ) AS reminder_count
                FROM prescriptions p
                JOIN doctors d ON p.doctor_id = d.id
                WHERE p.patient_id = %s
                ORDER BY p.created_date DESC
                LIMIT 8
                """,
                (patient_id,),
            )
            prescription_care = cursor.fetchall() or []

            for item in prescription_care:
                if item.get("created_date"):
                    item["created_date"] = item["created_date"].strftime("%Y-%m-%d")
                diagnosis_text = str(item.get("diagnosis") or "")
                item["diagnosis_preview"] = (
                    diagnosis_text[:90] + "..." if len(diagnosis_text) > 90 else diagnosis_text
                )

            patient_notifications = _get_patient_notifications(cursor, patient_id, limit=5)
            conn.commit()
        except Exception as e:
            print(f"Error loading patient care dashboard: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        "mainpatientpage.html",
        specialists=specialists,
        patient_logged_in=bool(patient_id),
        patient_id=patient_id,
        patient_notifications=patient_notifications,
        prescription_care=prescription_care,
    )

# 🔹 Patient Signup
@app.route("/submit", methods=["GET", "POST"])
def submit():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")
        age = request.form.get("age")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if email already exists
            cursor.execute("SELECT * FROM patients WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("You are already registered. Please log in.", "warning")
                return redirect(url_for("login_patient"))

            # Insert new patient
            cursor.execute(
                "INSERT INTO patients (name, email, password, phone, age) VALUES (%s, %s, %s, %s, %s)",
                (name, email, password, phone, age)
            )
            new_patient_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()

            session["patient_id"] = new_patient_id

            flash("Registration successful! Welcome to your dashboard.", "success")
            return redirect(url_for("patient_dashboard"))

        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("login_patient"))

    return render_template("mainpatientpage.html")

# Login Page for registered patients
@app.route("/login")
def login_patient_registered():
    return render_template("pal.html")

@app.route("/pl")
def pl():
    return render_template("pl.html")

@app.route("/pmain", methods=["GET", "POST"])
def check_details():
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM patients WHERE name = %s AND password = %s", (name, password))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session["patient_id"] = user["id"]
            session["patient_name"] = user["name"]
            return redirect(url_for("patient_dashboard"))
        else:
            return render_template("pl.html", error="Invalid name or password. Please sign up.")

@app.route("/specialist/<specialization>")
def show_specialist(specialization):
    # Check if patient is logged in
    patient_id = session.get("patient_id")
    if not patient_id:
        flash("Please login first to view doctors", "warning")
        return redirect(url_for("login_patient"))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Convert back the formatted specialization
    specialization = specialization.replace("_", " ").title()

    cursor.execute("""
        SELECT id, name, specialization, fees, available_days, time_start, time_end
        FROM doctors
        WHERE LOWER(specialization) = %s
    """, (specialization.lower(),))
    doctors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "specialist_doctors.html",
        specialization=specialization,
        doctors=doctors,
        patient_id=patient_id
    )

@app.route("/logindoctor")
def dl():
    return redirect(url_for("doctor_login"))

@app.route("/doctor_dashboard")
def doctordashboard():
    license_number = request.args.get("license")
    if not license_number:
        flash("You must log in first", "danger")
        return redirect(url_for("dl"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    ensure_care_tables(cursor)

    # Get doctor details using license_number
    cursor.execute("SELECT * FROM doctors WHERE license_number = %s", (license_number,))
    doctor = cursor.fetchone()

    if not doctor:
        flash("Doctor not found", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("dl"))

    # Get all patients who have chatted with this doctor
    cursor.execute("""
        SELECT DISTINCT 
            p.id as patient_id,
            p.name as patient_name,
            p.email as patient_email,
            p.phone as patient_phone,
            p.age as patient_age,
            (
                SELECT COUNT(*)
                FROM patient_reminders pr
                WHERE pr.patient_id = p.id
                  AND pr.doctor_id = %s
                  AND pr.is_active = 1
            ) as active_reminders,
            MAX(c.timestamp) as last_message_time,
            COUNT(c.id) as total_messages,
            (SELECT c2.message 
             FROM chats c2 
             WHERE c2.patient_id = p.id AND c2.doctor_id = %s 
             ORDER BY c2.timestamp DESC 
             LIMIT 1) as last_message,
            (SELECT c3.sender 
             FROM chats c3 
             WHERE c3.patient_id = p.id AND c3.doctor_id = %s 
             ORDER BY c3.timestamp DESC 
             LIMIT 1) as last_sender
        FROM patients p
        INNER JOIN chats c ON p.id = c.patient_id
        WHERE c.doctor_id = %s
        GROUP BY p.id, p.name, p.email, p.phone, p.age
        ORDER BY MAX(c.timestamp) DESC
    """, (doctor['id'], doctor['id'], doctor['id'], doctor['id']))
    
    patients_with_chats = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("doctordashboard.html", doctor=doctor, patients=patients_with_chats)

@app.route("/doctor_signup", methods=["GET", "POST"])
def doctor_signup():
    if request.method == "POST":
        name = request.form.get("doctor_name")
        specialization = request.form.get("specialist_type")
        license_number = request.form.get("license")
        fees = request.form.get("fees")
        available_days = ",".join(request.form.getlist("days"))
        time_start = request.form.get("time_start")
        time_end = request.form.get("time_end")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("doctor_signup"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if doctor already exists
            cursor.execute("SELECT * FROM doctors WHERE license_number = %s", (license_number,))
            if cursor.fetchone():
                flash("Doctor already registered. Please log in.", "warning")
                cursor.close()
                conn.close()
                return redirect(url_for("doctor_signup"))

            # Insert new doctor with all fields
            cursor.execute("""
                INSERT INTO doctors 
                (name, specialization, license_number, password, fees, available_days, time_start, time_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, specialization, license_number, password, fees, available_days, time_start, time_end))

            conn.commit()
            cursor.close()
            conn.close()

            flash("Doctor registration successful! Redirecting to dashboard...", "success")
            return redirect(url_for("doctordashboard", license=license_number))

        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("doctor_signup"))

    return render_template("dl.html")

@app.route("/doctor_login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        doctor_name = request.form.get("doctor_name")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if the doctor exists
        cursor.execute(
            "SELECT * FROM doctors WHERE name = %s AND password = %s",
            (doctor_name, password)
        )
        doctor = cursor.fetchone()

        cursor.close()
        conn.close()

        if doctor:
            # Store doctor info in session for better management
            session['doctor_id'] = doctor['id']
            session['doctor_name'] = doctor['name']
            session['doctor_license'] = doctor['license_number']
            
            flash(f"Welcome Dr. {doctor['name']}!", "success")
            return redirect(url_for("doctordashboard", license=doctor['license_number']))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for("doctor_login"))

    return render_template("dal.html")

# EXISTING CHAT ROUTE (for Patient to Doctor - keep as is)
@app.route("/chat/<int:doctor_id>/<int:patient_id>")
def chat(doctor_id, patient_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
    doctor = cursor.fetchone()

    # check payment status
    cursor.execute("""
        SELECT status FROM payments 
        WHERE doctor_id=%s AND patient_id=%s
        ORDER BY payment_date DESC LIMIT 1
    """, (doctor_id, patient_id))
    payment = cursor.fetchone()

    is_paid = payment and payment["status"] == "paid"

    cursor.close()
    conn.close()

    if not doctor:
        return "Doctor not found", 404

    return render_template("chat_doctor.html", doctor=doctor, is_paid=is_paid, patient_id=patient_id)

@app.route("/pay/<int:doctor_id>/<int:patient_id>", methods=["POST"])
def pay(doctor_id, patient_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO payments (doctor_id, patient_id, status)
        VALUES (%s, %s, 'paid')
    """, (doctor_id, patient_id))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Payment successful! You can now start your consultation.", "success")
    return redirect(url_for("chat", doctor_id=doctor_id, patient_id=patient_id))

# UPDATED SEND MESSAGE ROUTE (handles both patient and doctor messages)
@app.route("/send_message", methods=["POST"])
def send_message():
    try:
        data = request.json
        patient_id = data.get("patient_id")
        doctor_id = data.get("doctor_id")
        sender = data.get("sender")   # 'patient' or 'doctor'
        message = data.get("message")

        if not all([patient_id, doctor_id, sender, message]):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO chats (patient_id, doctor_id, sender, message, timestamp) VALUES (%s, %s, %s, %s, %s)",
            (patient_id, doctor_id, sender, message, datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "timestamp": datetime.now().strftime('%H:%M')
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# UPDATED GET MESSAGES ROUTE (works for both patient and doctor chats)
@app.route("/get_messages/<int:doctor_id>/<int:patient_id>")
def get_messages(doctor_id, patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT sender, message, timestamp 
            FROM chats 
            WHERE doctor_id = %s AND patient_id = %s
            ORDER BY timestamp ASC
        """, (doctor_id, patient_id))
        messages = cursor.fetchall()

        # Format timestamps for JSON serialization
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'sender': msg['sender'],
                'message': msg['message'],
                'timestamp': msg['timestamp'].strftime('%H:%M') if msg['timestamp'] else 'Now'
            })

        cursor.close()
        conn.close()
        
        return jsonify(formatted_messages)
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/chat_with_patient/<int:doctor_id>/<int:patient_id>')
def chat_with_patient(doctor_id, patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get doctor information
        cursor.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
        doctor = cursor.fetchone()
        
        if not doctor:
            flash('Doctor not found.', 'error')
            return redirect(url_for('dl'))
        
        # Get patient information
        cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        patient_data = cursor.fetchone()
        
        if not patient_data:
            flash('Patient not found.', 'error')
            return redirect(url_for('doctordashboard', license=doctor['license_number']))
        
        # Get all messages for this conversation
        cursor.execute("""
            SELECT sender, message, timestamp 
            FROM chats 
            WHERE doctor_id = %s AND patient_id = %s
            ORDER BY timestamp ASC
        """, (doctor_id, patient_id))
        
        messages = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Format patient data for template - CORRECTED STRUCTURE
        patient = {
            'patient_id': patient_data['id'],  # Make sure this matches your template
            'patient_name': patient_data['name'],
            'patient_age': patient_data['age'],
            'patient_phone': patient_data.get('phone', ''),
            'patient_email': patient_data.get('email', ''),
            'last_message_time': messages[-1]['timestamp'].strftime('%Y-%m-%d %H:%M') if messages else 'Never'
        }
        
        # Convert messages to the format expected by template
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'sender': msg['sender'],
                'message': msg['message'],  # Changed from 'content' to 'message'
                'timestamp': msg['timestamp']
            })
        
        return render_template('chat_with_patient.html', 
                             doctor=doctor, 
                             patient=patient, 
                             messages=formatted_messages)
                             
    except Exception as e:
        print(f"Error in chat_with_patient route: {str(e)}")  # Add logging
        flash(f'Error loading chat: {str(e)}', 'error')
        return redirect(url_for('doctordashboard'))
    
@app.route('/give_prescription/<int:doctor_id>/<int:patient_id>')
def give_prescription(doctor_id, patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get doctor information
        cursor.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
        doctor = cursor.fetchone()
        
        if not doctor:
            flash('Doctor not found.', 'error')
            return redirect(url_for('dl'))
        
        # Get patient information
        cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        patient_data = cursor.fetchone()
        
        if not patient_data:
            flash('Patient not found.', 'error')
            return redirect(url_for('doctordashboard', license=doctor['license_number']))
        
        cursor.close()
        conn.close()
        
        # Format patient data
        patient = {
            'patient_id': patient_data['id'],
            'patient_name': patient_data['name'],
            'patient_age': patient_data['age'],
            'patient_phone': patient_data.get('phone', ''),
            'patient_email': patient_data.get('email', '')
        }
        
        return render_template('prescription.html', doctor=doctor, patient=patient)
                             
    except Exception as e:
        print(f"Error in give_prescription route: {str(e)}")
        flash(f'Error loading prescription page: {str(e)}', 'error')
        return redirect(url_for('doctordashboard'))

# Save prescription from doctor form
@app.route('/save_prescription', methods=['POST'])
def save_prescription():
    try:
        data = request.json
        doctor_id = data.get('doctor_id')
        patient_id = data.get('patient_id')
        diagnosis = data.get('diagnosis')
        medicines = data.get('medicines', [])
        notes = data.get('notes', '')

        if not all([doctor_id, patient_id, diagnosis]):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert prescription
        cursor.execute("""
            INSERT INTO prescriptions (doctor_id, patient_id, diagnosis, notes)
            VALUES (%s, %s, %s, %s)
        """, (doctor_id, patient_id, diagnosis, notes))
        
        prescription_id = cursor.lastrowid

        # Insert medicines for this prescription
        for medicine in medicines:
            cursor.execute("""
                INSERT INTO prescription_medicines 
                (prescription_id, medicine_name, dosage, duration, instructions)
                VALUES (%s, %s, %s, %s, %s)
            """, (prescription_id, medicine['name'], medicine['dosage'], 
                  medicine['duration'], medicine.get('instructions', '')))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Prescription saved successfully",
            "prescription_id": prescription_id
        })

    except Exception as e:
        print(f"Error saving prescription: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/draft_prescription/<int:doctor_id>/<int:patient_id>', methods=['GET'])
def api_draft_prescription(doctor_id, patient_id):
    """AI Scribe Auto-Drafts Prescription from Chat History"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT sender, message, timestamp FROM chats WHERE doctor_id = %s AND patient_id = %s ORDER BY timestamp ASC LIMIT 20",
            (doctor_id, patient_id)
        )
        chat_history = cursor.fetchall()
        cursor.close()
        conn.close()

        if not chat_history:
            return jsonify({"status": "error", "message": "No chat history found to draft from"}), 404

        # Draft using AI model imported globally
        draft_json_str = groq_client.draft_prescription(chat_history)
        
        # safely parse the string back into JSON
        import json
        try:
            draft_data = json.loads(draft_json_str)
            return jsonify({"status": "success", "draft": draft_data})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to parse AI draft: {str(e)}", "raw": draft_json_str}), 500

    except Exception as e:
        print(f"Error drafting prescription: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/verify_prescription', methods=['POST'])
def api_verify_prescription():
    """AI Medication Safety & Contraindication Checker"""
    try:
        data = request.json
        patient_id = data.get('patient_id')
        diagnosis = data.get('diagnosis', '')
        medicines = data.get('medicines', [])

        if not patient_id or not medicines:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        # Optional: Fetch patient age to pass into the model for better accuracy
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT age FROM patients WHERE id = %s", (patient_id,))
        patient = cursor.fetchone()
        cursor.close()
        conn.close()

        age = str(patient['age']) if patient and patient.get('age') else "Unknown"

        # Verify using AI model
        safety_json_str = groq_client.verify_prescription_safety(diagnosis, age, medicines)
        
        import json
        try:
            safety_data = json.loads(safety_json_str)
            return jsonify({"status": "success", "safety": safety_data})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to parse safety check: {str(e)}", "raw": safety_json_str}), 500

    except Exception as e:
        print(f"Error verifying prescription: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/prescription/<int:prescription_id>/generate_reminders', methods=['POST'])
def generate_prescription_reminders(prescription_id):
    """Generate medicine reminders for a patient's prescription."""
    patient_id = session.get('patient_id')
    if not patient_id:
        return jsonify({"status": "error", "message": "Please login as patient"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        ensure_care_tables(cursor)

        cursor.execute(
            """
            SELECT id, patient_id, doctor_id, diagnosis
            FROM prescriptions
            WHERE id = %s
            """,
            (prescription_id,),
        )
        prescription = cursor.fetchone()

        if not prescription:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Prescription not found"}), 404

        if int(prescription['patient_id']) != int(patient_id):
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Unauthorized for this prescription"}), 403

        cursor.execute(
            """
            SELECT medicine_name, dosage, duration, instructions
            FROM prescription_medicines
            WHERE prescription_id = %s
            """,
            (prescription_id,),
        )
        medicines = cursor.fetchall() or []

        if not medicines:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "No medicines found in prescription"}), 400

        cursor.execute(
            "DELETE FROM patient_reminders WHERE prescription_id = %s AND patient_id = %s",
            (prescription_id, patient_id),
        )

        for medicine in medicines:
            slots = _dosage_to_slots(medicine.get('dosage'))
            meal_timing = _infer_meal_timing(medicine.get('instructions'))

            for slot_name, reminder_time in slots:
                reminder_note = (
                    f"{medicine.get('medicine_name', 'Medicine')} - "
                    f"{slot_name.capitalize()} dose"
                )

                cursor.execute(
                    """
                    INSERT INTO patient_reminders (
                        prescription_id, patient_id, doctor_id,
                        medicine_name, dosage, duration, instructions,
                        meal_timing, reminder_time, reminder_note, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """,
                    (
                        prescription_id,
                        patient_id,
                        prescription['doctor_id'],
                        medicine.get('medicine_name'),
                        medicine.get('dosage'),
                        medicine.get('duration'),
                        medicine.get('instructions'),
                        meal_timing,
                        reminder_time,
                        reminder_note,
                    ),
                )

        conn.commit()

        cursor.execute(
            """
            SELECT id, medicine_name, dosage, duration, meal_timing, reminder_time, reminder_note
            FROM patient_reminders
            WHERE prescription_id = %s AND patient_id = %s AND is_active = 1
            ORDER BY reminder_time ASC, id ASC
            """,
            (prescription_id, patient_id),
        )
        reminders = cursor.fetchall() or []

        for reminder in reminders:
            reminder['reminder_time'] = _format_db_time(reminder.get('reminder_time'))

        cursor.close()
        conn.close()

        return jsonify(
            {
                "status": "success",
                "message": "Reminders generated successfully",
                "reminder_count": len(reminders),
                "reminders": reminders,
            }
        )

    except Exception as e:
        print(f"Error generating reminders: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/prescription/<int:prescription_id>/diet_plan', methods=['GET'])
def get_prescription_diet_plan(prescription_id):
    """Generate a patient-friendly diet plan from prescription context."""
    patient_id = session.get('patient_id')
    if not patient_id:
        return jsonify({"status": "error", "message": "Please login as patient"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        ensure_care_tables(cursor)

        cursor.execute(
            """
            SELECT id, patient_id, doctor_id, diagnosis, notes
            FROM prescriptions
            WHERE id = %s
            """,
            (prescription_id,),
        )
        prescription = cursor.fetchone()

        if not prescription:
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Prescription not found"}), 404

        if int(prescription['patient_id']) != int(patient_id):
            cursor.close()
            conn.close()
            return jsonify({"status": "error", "message": "Unauthorized for this prescription"}), 403

        cursor.execute(
            """
            SELECT medicine_name, dosage, duration, instructions
            FROM prescription_medicines
            WHERE prescription_id = %s
            """,
            (prescription_id,),
        )
        medicines = cursor.fetchall() or []

        diet_plan = _build_diet_plan(
            diagnosis=prescription.get('diagnosis'),
            medicines=medicines,
            notes=prescription.get('notes', ''),
        )

        cursor.execute(
            """
            INSERT INTO patient_diet_plans (
                prescription_id, patient_id, doctor_id, plan_text, generated_by
            )
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                plan_text = VALUES(plan_text),
                generated_by = VALUES(generated_by),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                prescription_id,
                patient_id,
                prescription['doctor_id'],
                json.dumps(diet_plan, ensure_ascii=True),
                'rule_based',
            ),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "diet_plan": diet_plan,
        })

    except Exception as e:
        print(f"Error generating diet plan: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/doctor_patient_care/<int:doctor_id>/<int:patient_id>')
def doctor_patient_care(doctor_id, patient_id):
    """Doctor view of patient reminders and diet plans."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        ensure_care_tables(cursor)

        cursor.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
        doctor = cursor.fetchone()
        if not doctor:
            cursor.close()
            conn.close()
            flash('Doctor not found.', 'error')
            return redirect(url_for('dl'))

        cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        patient = cursor.fetchone()
        if not patient:
            cursor.close()
            conn.close()
            flash('Patient not found.', 'error')
            return redirect(url_for('doctordashboard', license=doctor['license_number']))

        cursor.execute(
            """
            SELECT pr.medicine_name, pr.dosage, pr.duration, pr.instructions,
                   pr.meal_timing, pr.reminder_time, pr.reminder_note,
                   p.id AS prescription_id, p.created_date
            FROM patient_reminders pr
            JOIN prescriptions p ON pr.prescription_id = p.id
            WHERE pr.patient_id = %s AND pr.doctor_id = %s AND pr.is_active = 1
            ORDER BY p.created_date DESC, pr.reminder_time ASC
            """,
            (patient_id, doctor_id),
        )
        reminders = cursor.fetchall() or []

        for reminder in reminders:
            reminder['reminder_time'] = _format_db_time(reminder.get('reminder_time'))
            if reminder.get('created_date'):
                reminder['created_date'] = reminder['created_date'].strftime('%Y-%m-%d')

        cursor.execute(
            """
            SELECT dp.plan_text, dp.created_at, dp.updated_at,
                   p.id AS prescription_id, p.diagnosis
            FROM patient_diet_plans dp
            JOIN prescriptions p ON dp.prescription_id = p.id
            WHERE dp.patient_id = %s AND dp.doctor_id = %s
            ORDER BY dp.updated_at DESC
            """,
            (patient_id, doctor_id),
        )
        diet_plans = cursor.fetchall() or []

        for plan in diet_plans:
            try:
                plan['plan'] = json.loads(plan.get('plan_text', '{}'))
            except Exception:
                plan['plan'] = {
                    'summary': 'Unable to parse diet plan',
                    'timing_notes': [plan.get('plan_text', '')],
                }

            if plan.get('updated_at'):
                plan['updated_at'] = plan['updated_at'].strftime('%Y-%m-%d %H:%M')

        cursor.close()
        conn.close()

        return render_template(
            'doctor_patient_care.html',
            doctor=doctor,
            patient=patient,
            reminders=reminders,
            diet_plans=diet_plans,
        )

    except Exception as e:
        print(f"Error loading doctor patient care page: {str(e)}")
        flash(f'Error loading patient care details: {str(e)}', 'error')
        return redirect(url_for('doctordashboard'))

# Get patient prescriptions
@app.route('/get_prescriptions/<int:patient_id>')
def get_prescriptions(patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get all prescriptions for this patient
        cursor.execute("""
            SELECT p.id, p.doctor_id, p.diagnosis, p.notes, p.created_date,
                   d.name as doctor_name, d.specialization
            FROM prescriptions p
            JOIN doctors d ON p.doctor_id = d.id
            WHERE p.patient_id = %s
            ORDER BY p.created_date DESC
        """, (patient_id,))
        
        prescriptions = cursor.fetchall()

        # Get medicines for each prescription
        for prescription in prescriptions:
            cursor.execute("""
                SELECT medicine_name, dosage, duration, instructions
                FROM prescription_medicines
                WHERE prescription_id = %s
            """, (prescription['id'],))
            prescription['medicines'] = cursor.fetchall()
            # Format date
            prescription['created_date'] = prescription['created_date'].strftime('%Y-%m-%d %H:%M')

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "prescriptions": prescriptions
        })

    except Exception as e:
        print(f"Error getting prescriptions: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# View prescriptions page for patient
@app.route('/view_prescriptions/<int:doctor_id>/<int:patient_id>')
def view_prescriptions(doctor_id, patient_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get doctor info
        cursor.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
        doctor = cursor.fetchone()

        # Get patient info
        cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        patient_data = cursor.fetchone()

        # Get all prescriptions for this patient from this doctor
        cursor.execute("""
            SELECT p.id, p.diagnosis, p.notes, p.created_date,
                   d.name as doctor_name, d.specialization
            FROM prescriptions p
            JOIN doctors d ON p.doctor_id = d.id
            WHERE p.patient_id = %s AND p.doctor_id = %s
            ORDER BY p.created_date DESC
        """, (patient_id, doctor_id))
        
        prescriptions = cursor.fetchall()

        # Get medicines for each prescription
        for prescription in prescriptions:
            cursor.execute("""
                SELECT medicine_name, dosage, duration, instructions
                FROM prescription_medicines
                WHERE prescription_id = %s
            """, (prescription['id'],))
            prescription['medicines'] = cursor.fetchall()
            # Format date properly
            if prescription['created_date']:
                prescription['created_date'] = prescription['created_date'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"DEBUG view_prescriptions - Prescription {prescription['id']}: {prescription}")

        print(f"DEBUG view_prescriptions - Total prescriptions: {len(prescriptions)}")

        cursor.close()
        conn.close()

        return render_template('view_prescriptions.html', 
                             doctor=doctor,
                             patient=patient_data,
                             prescriptions=prescriptions)

    except Exception as e:
        import traceback
        print(f"Error in view_prescriptions: {str(e)}")
        traceback.print_exc()
        flash(f'Error loading prescriptions: {str(e)}', 'error')
        return redirect(url_for('chat', doctor_id=doctor_id, patient_id=patient_id))

# ==========================================
# ORDER MANAGEMENT ROUTES
# ==========================================

@app.route('/api/get_pharmacists')
def get_pharmacists():
    """Get all available pharmacists"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, pharmacy_name, email, phone, address, city, state, 
                   postal_code, country, description, license_number, 
                   website, opening_hours_from, opening_hours_to
            FROM pharmacists
            ORDER BY city, pharmacy_name
        """)
        
        pharmacists = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert time objects to strings for JSON serialization
        for pharmacist in pharmacists:
            if pharmacist['opening_hours_from']:
                pharmacist['opening_hours_from'] = str(pharmacist['opening_hours_from'])
            if pharmacist['opening_hours_to']:
                pharmacist['opening_hours_to'] = str(pharmacist['opening_hours_to'])
        
        return jsonify({
            "pharmacists": pharmacists
        })
    
    except Exception as e:
        print(f"Error getting pharmacists: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/create_order', methods=['POST'])
def create_order():
    """Create a new medicine order"""
    try:
        data = request.json
        prescription_id = data.get('prescription_id')
        pharmacist_id = data.get('pharmacist_id')
        
        if not prescription_id or not pharmacist_id:
            return jsonify({"success": False, "message": "Missing prescription or pharmacist ID"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get prescription details to find patient_id
        cursor.execute("SELECT patient_id FROM prescriptions WHERE id = %s", (prescription_id,))
        prescription = cursor.fetchone()
        
        if not prescription:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Prescription not found"}), 404
        
        patient_id = prescription['patient_id']
        
        # Create order
        insert_query = """
        INSERT INTO orders (prescription_id, pharmacist_id, patient_id, status)
        VALUES (%s, %s, %s, 'pending')
        """
        
        cursor.execute(insert_query, (prescription_id, pharmacist_id, patient_id))
        conn.commit()
        
        order_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Order placed successfully",
            "order_id": order_id
        })
    
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/update_order_status', methods=['POST'])
def update_order_status():
    """Update order status"""
    try:
        data = request.json
        order_id = data.get('order_id')
        status = data.get('status')
        
        if not order_id or not status:
            return jsonify({"success": False, "message": "Missing order ID or status"}), 400
        
        valid_statuses = ['pending', 'confirmed', 'processing', 'ready', 'delivered', 'cancelled']
        if status not in valid_statuses:
            return jsonify({"success": False, "message": "Invalid status"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Update order status
        update_query = "UPDATE orders SET status = %s WHERE id = %s"
        cursor.execute(update_query, (status, order_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"Order status updated to {status}"
        })
    
    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/patient_orders/<int:patient_id>')
def patient_orders(patient_id):
    """Display all orders for a patient"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get patient info
        cursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        patient = cursor.fetchone()
        
        if not patient:
            cursor.close()
            conn.close()
            return "Patient not found", 404
        
        # Get all orders for this patient with pharmacy and prescription details
        cursor.execute("""
            SELECT o.id, o.status, o.order_date, o.confirmed_date, o.delivered_date,
                   ph.pharmacy_name, ph.city, ph.state, ph.phone, ph.email,
                   p.diagnosis, p.doctor_id,
                   d.name as doctor_name, d.specialization
            FROM orders o
            JOIN pharmacists ph ON o.pharmacist_id = ph.id
            JOIN prescriptions p ON o.prescription_id = p.id
            JOIN doctors d ON p.doctor_id = d.id
            WHERE o.patient_id = %s
            ORDER BY o.order_date DESC
        """, (patient_id,))
        
        orders = cursor.fetchall()
        
        # Get medicines for each order
        for order in orders:
            cursor.execute("""
                SELECT medicine_name, dosage, duration, instructions
                FROM prescription_medicines
                WHERE prescription_id = (
                    SELECT prescription_id FROM orders WHERE id = %s
                )
            """, (order['id'],))
            order['medicines'] = cursor.fetchall()
            
            # Format dates
            if order['order_date']:
                order['order_date_formatted'] = order['order_date'].strftime('%d %b %Y %I:%M %p')
            if order['confirmed_date']:
                order['confirmed_date_formatted'] = order['confirmed_date'].strftime('%d %b %Y %I:%M %p')
            if order['delivered_date']:
                order['delivered_date_formatted'] = order['delivered_date'].strftime('%d %b %Y %I:%M %p')
        
        cursor.close()
        conn.close()
        
        return render_template('patient_orders.html', patient=patient, orders=orders)
    
    except Exception as e:
        print(f"Error fetching patient orders: {str(e)}")
        return f"Error: {str(e)}", 500

# ---------------------------
# Video Call Signaling Events
# ---------------------------

@socketio.on('join_room')
def handle_join(data):
    room = f"{data['doctor_id']}_{data['patient_id']}"
    join_room(room)
    emit('room_joined', {'room': room}, room=room)

@socketio.on('start_call')
def handle_start_call(data):
    room = f"{data['doctor_id']}_{data['patient_id']}"
    emit('incoming_call', {'from': data['user_type']}, room=room, include_self=False)

@socketio.on('webrtc_offer')
def handle_offer(data):
    emit('webrtc_offer', data, room=data['room'], include_self=False)

@socketio.on('webrtc_answer')
def handle_answer(data):
    emit('webrtc_answer', data, room=data['room'], include_self=False)

@socketio.on('webrtc_ice_candidate')
def handle_ice_candidate(data):
    emit('webrtc_ice_candidate', data, room=data['room'], include_self=False)
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    
    

###ai

# Configure Flask app with proper settings
app.config['SESSION_TYPE'] = 'filesystem'  # or 'redis' if you prefer
Session(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'dcm'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize AI clients - Using only Groq and Mistral
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

groq_client = GroqChatClient(GROQ_API_KEY)
vision_client = VisionModelClient( 
    mistral_api_key=MISTRAL_API_KEY
)

# Dictionary to store RAG pipelines per session
rag_pipelines = {}

# Specialist information dictionary
SPECIALISTS = {
    'general_practitioner': {
        'name': 'General Practitioner',
        'icon': '🩺',
        'description': 'Provides care for common illnesses, fever, infections, and general health consultation.',
        'type': 'general_practitioner'
    },
    'cardiologist': {
        'name': 'Cardiologist',
        'icon': '❤️',
        'description': 'Specialized in heart health, blood pressure, chest pain, and cardiovascular diseases.',
        'type': 'cardiologist'
    },
    'dermatologist': {
        'name': 'Dermatologist',
        'icon': '🔬',
        'description': 'Expert in skin conditions, acne, rashes, allergies, and cosmetic skin concerns.',
        'type': 'dermatologist'
    },
    'orthopedic': {
        'name': 'Orthopedist',
        'icon': '🦴',
        'description': 'Expert in bones, joints, muscles, fractures, and musculoskeletal problems.',
        'type': 'orthopedic'
    },
    'gynecologist': {
        'name': 'Gynecologist',
        'icon': '👩‍⚕️',
        'description': 'Specialized in women\'s health, reproductive health, and gynecological issues.',
        'type': 'gynecologist'
    },
    'neurologist': {
        'name': 'Neurologist',
        'icon': '🧠',
        'description': 'Specialized in brain, spine, nervous system disorders, and neurological conditions.',
        'type': 'neurologist'
    },
    'pulmonologist': {
        'name': 'Pulmonologist',
        'icon': '🫁',
        'description': 'Specialized in lungs, breathing disorders, asthma, and respiratory infections.',
        'type': 'pulmonologist'
    },
    'dentist': {
        'name': 'Dentist',
        'icon': '🦷',
        'description': 'Specialized in dental pain, gum disease, oral health, and tooth-related conditions.',
        'type': 'dentist'
    },
}

SPECIALIST_ALIASES = {
    'pulmonology': 'pulmonologist',
    'orthopedist': 'orthopedic',
    'general_physician': 'general_practitioner',
}


def normalize_specialist_type(specialist_type):
    if not specialist_type:
        return specialist_type
    normalized = specialist_type.strip().lower()
    return SPECIALIST_ALIASES.get(normalized, normalized)


SESSION_HISTORY_BY_SPECIALIST = 'conversation_history_by_specialist'
SESSION_UPLOADS_BY_SPECIALIST = 'uploaded_files_by_specialist'
SESSION_IDS_BY_SPECIALIST = 'session_ids_by_specialist'


def _get_session_dict(key):
    value = session.get(key)
    if not isinstance(value, dict):
        value = {}
    return value


def _get_specialist_history(specialist_type):
    history_map = _get_session_dict(SESSION_HISTORY_BY_SPECIALIST)
    history = history_map.get(specialist_type, [])
    if not isinstance(history, list):
        history = []
    return history


def _set_specialist_history(specialist_type, history):
    history_map = _get_session_dict(SESSION_HISTORY_BY_SPECIALIST)
    history_map[specialist_type] = history
    session[SESSION_HISTORY_BY_SPECIALIST] = history_map
    session.modified = True


def _get_specialist_uploaded_files(specialist_type):
    uploads_map = _get_session_dict(SESSION_UPLOADS_BY_SPECIALIST)
    specialist_uploads = uploads_map.get(specialist_type, [])
    if not isinstance(specialist_uploads, list):
        specialist_uploads = []
    return specialist_uploads


def _append_specialist_uploaded_file(specialist_type, file_info):
    uploads_map = _get_session_dict(SESSION_UPLOADS_BY_SPECIALIST)
    specialist_uploads = uploads_map.get(specialist_type, [])
    if not isinstance(specialist_uploads, list):
        specialist_uploads = []
    specialist_uploads.append(file_info)
    uploads_map[specialist_type] = specialist_uploads
    session[SESSION_UPLOADS_BY_SPECIALIST] = uploads_map
    session.modified = True


def _find_specialist_file(specialist_type, file_identifier):
    specialist_uploads = _get_specialist_uploaded_files(specialist_type)
    for file_info in specialist_uploads:
        if file_info.get('saved_name') == file_identifier:
            return file_info
        if file_info.get('original_name') == file_identifier:
            return file_info
    return None


def _get_or_create_specialist_session_id(specialist_type):
    session_ids = _get_session_dict(SESSION_IDS_BY_SPECIALIST)
    specialist_session_id = session_ids.get(specialist_type)
    if not specialist_session_id:
        specialist_session_id = str(uuid.uuid4())
        session_ids[specialist_type] = specialist_session_id
        session[SESSION_IDS_BY_SPECIALIST] = session_ids
        session.modified = True
    return specialist_session_id


def _initialize_specialist_state(specialist_type):
    # Ensure specialist-scoped containers are present.
    _set_specialist_history(specialist_type, _get_specialist_history(specialist_type))
    uploads_map = _get_session_dict(SESSION_UPLOADS_BY_SPECIALIST)
    if specialist_type not in uploads_map:
        uploads_map[specialist_type] = []
        session[SESSION_UPLOADS_BY_SPECIALIST] = uploads_map
        session.modified = True
    _get_or_create_specialist_session_id(specialist_type)

    # Remove legacy shared keys to avoid accidental cross-specialist leakage.
    for legacy_key in ('conversation_history', 'uploaded_files', 'session_id'):
        if legacy_key in session:
            session.pop(legacy_key, None)
            session.modified = True

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type for processing"""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        return 'pdf'
    elif ext in ['png', 'jpg', 'jpeg']:
        return 'image'
    elif ext == 'dcm':
        return 'dicom'
    return 'unknown'

def extract_patient_info_from_message(message, specialist_type):
    """Extract patient information from conversational message.
    
    Only includes fields that actually have real values.
    The AI model's system prompt handles asking for missing information
    contextually — we don't need to send 'Not specified' for everything.
    """
    specialist_type = normalize_specialist_type(specialist_type)

    # Core patient data — only include what we actually know
    patient_data = {
        'symptoms': message,
    }

    # Only add name/age/gender if they have real values
    patient_name = session.get('patient_name')
    patient_age = session.get('patient_age')
    patient_gender = session.get('patient_gender')

    if patient_name and patient_name not in ('Patient', ''):
        patient_data['name'] = patient_name
    if patient_age and patient_age not in ('Not specified', ''):
        patient_data['age'] = patient_age
    if patient_gender and patient_gender not in ('Not specified', ''):
        patient_data['gender'] = patient_gender

    return patient_data


def _infer_response_meta(response_text):
    text = str(response_text or '').lower()

    high_urgency_terms = [
        'emergency', 'immediate medical attention', 'go to emergency',
        'stroke', 'heart attack', 'severe bleeding', 'can\'t breathe',
    ]
    medium_urgency_terms = [
        'urgent', 'seek care soon', 'same day', 'within 24 hours',
        'worsening symptoms',
    ]

    urgency = 'low'
    if any(term in text for term in high_urgency_terms):
        urgency = 'high'
    elif any(term in text for term in medium_urgency_terms):
        urgency = 'medium'

    confidence = 'medium'
    low_confidence_terms = [
        'need more information', 'insufficient information',
        'unable to determine', 'cannot determine',
    ]
    if any(term in text for term in low_confidence_terms) or '[low confidence]' in text:
        confidence = 'low'
    elif '[high confidence]' in text:
        confidence = 'high'

    return {
        'urgency': urgency,
        'confidence': confidence,
    }

@app.route('/index')
def index():
    """Render the index page"""
    return render_template('index.html')

@app.route('/specialists')
def specialists():
    """Render the specialists page"""
    return render_template('specialist.html')

@app.route('/chat/<specialist_type>')
def chat_specialist(specialist_type):
    """Render the chat page for selected specialist"""
    specialist_type = normalize_specialist_type(specialist_type)

    # Check if specialist type is valid
    if specialist_type not in SPECIALISTS:
        return "Specialist not found", 404
    
    # Get specialist information
    specialist_info = SPECIALISTS[specialist_type]
    
    # Store in session
    session['specialist_type'] = specialist_type
    _initialize_specialist_state(specialist_type)
    
    return render_template(
        'chat.html',
        specialist_type=specialist_type,
        specialist_name=specialist_info['name'],
        specialist_icon=specialist_info['icon'],
        specialist_description=specialist_info['description']
    )
@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        message = data.get('message', '').strip()
        specialist_type = normalize_specialist_type(data.get('specialist'))
        uploaded_files = data.get('files', [])
        
        print(f"DEBUG: api_chat received - message: {message}, specialist: {specialist_type}, files: {uploaded_files}")
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        if not specialist_type:
            return jsonify({'success': False, 'error': 'Specialist type is required'}), 400
        
        if specialist_type not in SPECIALIST_PROMPTS:
            return jsonify({'success': False, 'error': f'Invalid specialist type: {specialist_type}. Valid types are: {list(SPECIALIST_PROMPTS.keys())}'}), 400
        
        # Keep chat context isolated by specialist.
        session['specialist_type'] = specialist_type
        _initialize_specialist_state(specialist_type)
        conversation_history = _get_specialist_history(specialist_type)
        specialist_session_id = _get_or_create_specialist_session_id(specialist_type)
        
        # EMERGENCY TRIAGE SYSTEM
        emergency_keywords = ["chest pain", "heart attack", "stroke", "can't breathe", "breathing difficulty", "severe bleeding", "unconscious", "suicide", "thunderclap headache", "fainting"]
        msg_lower = message.lower()
        if any(kw in msg_lower for kw in emergency_keywords):
            patient_name = session.get('patient_name', 'A patient')
            try:
                socketio.emit('emergency_triage', {
                    'patient_name': patient_name,
                    'message': message,
                    'specialist': specialist_type
                })
                print(f"🚨 EMERGENCY TRIAGE ALERT triggered for {patient_name}")
            except Exception as e:
                print(f"Socket emit failed: {e}")
        
        response_text = ""
        
        # If files are uploaded, process them
        if uploaded_files:
            response_text += process_uploaded_files(
                uploaded_files,
                message,
                specialist_type,
                specialist_session_id,
                conversation_history,
            )
        else:
            # Regular chat without files
            patient_data = extract_patient_info_from_message(message, specialist_type)
            response_text = groq_client.chat(
                specialist_type,
                patient_data,
                user_message=message,
                conversation_history=conversation_history,
            )
        
        # Store conversation
        conversation_history.append({
            'user': message,
            'assistant': response_text,
            'timestamp': datetime.now().isoformat()
        })
        _set_specialist_history(specialist_type, conversation_history)

        response_meta = _infer_response_meta(response_text)
        
        return jsonify({
            'success': True,
            'response': response_text,
            'meta': response_meta,
        })
        
    except Exception as e:
        print(f"Error in api_chat: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500


@app.route('/api/report', methods=['POST'])
def api_report():
    """Generate a patient-friendly structured consultation report using Groq."""
    try:
        data = request.get_json() or {}
        report_language = str(data.get('language', 'english')).strip().lower()
        report_mode = str(data.get('mode', 'patient_simple')).strip().lower()
        clarity_level = str(data.get('clarity', 'simple')).strip().lower()

        specialist_type = normalize_specialist_type(
            data.get('specialist') or session.get('specialist_type')
        )
        if not specialist_type:
            return jsonify({'success': False, 'error': 'Specialist type is required'}), 400

        if specialist_type not in SPECIALIST_PROMPTS:
            return jsonify({'success': False, 'error': 'Invalid specialist type'}), 400

        provided_history = data.get('history', [])
        if isinstance(provided_history, list) and provided_history:
            conversation_history = provided_history
        else:
            conversation_history = _get_specialist_history(specialist_type)

        if not isinstance(conversation_history, list) or not conversation_history:
            return jsonify({'success': False, 'error': 'No conversation available to generate report'}), 400

        patient_data = {}
        patient_name = session.get('patient_name')
        patient_age = session.get('patient_age')
        patient_gender = session.get('patient_gender')

        if patient_name and patient_name not in ('Patient', ''):
            patient_data['name'] = patient_name
        if patient_age and patient_age not in ('Not specified', ''):
            patient_data['age'] = patient_age
        if patient_gender and patient_gender not in ('Not specified', ''):
            patient_data['gender'] = patient_gender

        report_payload = groq_client.generate_structured_report(
            specialist_type=specialist_type,
            conversation_history=conversation_history,
            patient_data=patient_data,
            report_language=report_language,
            report_mode=report_mode,
            clarity_level=clarity_level,
        )

        return jsonify({
            'success': True,
            'report': report_payload,
        })
    except Exception as e:
        print(f"Error in api_report: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    try:
        specialist_type = normalize_specialist_type(request.form.get('specialist') or session.get('specialist_type'))

        if not specialist_type:
            return jsonify({'success': False, 'error': 'Specialist type is required before upload'}), 400

        if specialist_type not in SPECIALIST_PROMPTS:
            return jsonify({'success': False, 'error': 'Invalid specialist type for upload'}), 400

        _initialize_specialist_state(specialist_type)

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'File type not allowed'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Store file info in specialist-scoped session state.
        _append_specialist_uploaded_file(specialist_type, {
            'original_name': filename,
            'saved_name': unique_filename,
            'filepath': filepath,
            'type': get_file_type(filename),
            'timestamp': timestamp
        })
        
        return jsonify({
            'success': True,
            'filename': filename,
            'saved_name': unique_filename,
            'file_id': unique_filename,
            'specialist': specialist_type,
        })
        
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def process_uploaded_files(file_names, message, specialist_type, session_id, conversation_history=None):
    """Process uploaded files with AI models - Using only Mistral for vision"""
    try:
        conversation_history = conversation_history or []
        response_parts = []
        
        for file_name in file_names:
            # Find file info
            file_info = _find_specialist_file(specialist_type, file_name)
            if not file_info:
                continue
            
            filepath = file_info['filepath']
            file_type = file_info['type']
            
            if file_type == 'pdf':
                # Process PDF with RAG using Groq
                if session_id not in rag_pipelines:
                    rag_pipelines[session_id] = MedicalRAGPipeline(
                        GROQ_API_KEY,
                        collection_name=f"medical_docs_{session_id}"
                    )
                
                rag_pipeline = rag_pipelines[session_id]
                rag_pipeline.process_pdf(filepath, document_id=file_info['saved_name'])
                
                patient_info = {
                    'indication': message,
                }
                # Only include real values
                p_name = session.get('patient_name')
                p_age = session.get('patient_age')
                p_gender = session.get('patient_gender')
                if p_name and p_name not in ('Patient', ''):
                    patient_info['name'] = p_name
                if p_age and p_age not in ('Not specified', ''):
                    patient_info['age'] = p_age
                if p_gender and p_gender not in ('Not specified', ''):
                    patient_info['gender'] = p_gender
                
                rag_response = rag_pipeline.query_documents(
                    question=message,
                    patient_info=patient_info,
                    specialist_type=specialist_type,
                    document_ids=[file_info['saved_name']],
                )
                response_parts.append(f"📄 **Analysis of {file_name}:**\n\n{rag_response}")
                
            elif file_type == 'image':
                # Process image with vision model - Using Mistral with specialist-aware analysis
                patient_info = {
                    'indication': message,
                }
                p_age = session.get('patient_age')
                p_gender = session.get('patient_gender')
                if p_age and p_age not in ('Not specified', ''):
                    patient_info['age'] = p_age
                if p_gender and p_gender not in ('Not specified', ''):
                    patient_info['gender'] = p_gender
                
                # Use specialist-aware image analysis
                image_response = vision_client.analyze_image_specialist_aware(
                    filepath, 
                    patient_info,
                    specialist_type=specialist_type
                )
                
                response_parts.append(f"🔬 **Analysis of {file_name}:**\n\n{image_response}")
        
        # Combine responses
        if response_parts:
            combined_response = "\n\n---\n\n".join(response_parts)
            
            # Add contextual advice from specialist using Groq
            # Pass the patient's actual message, and let image_context integrate the findings
            patient_data = extract_patient_info_from_message(message, specialist_type)
            specialist_advice = groq_client.chat(
                specialist_type,
                patient_data,
                user_message=message,
                conversation_history=conversation_history,
                image_context=combined_response,
            )
            
            return f"{combined_response}\n\n---\n\n**Specialist Consultation:**\n\n{specialist_advice}"
        else:
            # No files found, regular chat
            patient_data = extract_patient_info_from_message(message, specialist_type)
            return groq_client.chat(
                specialist_type,
                patient_data,
                user_message=message,
                conversation_history=conversation_history,
            )
            
    except Exception as e:
        print(f"Error processing files: {str(e)}")
        return f"I encountered an error processing the uploaded files. However, let me address your question: {message}"

@app.route('/api/clear-session', methods=['POST'])
def clear_session():
    """Clear session data and uploaded files"""
    try:
        specialist_uploads = session.get(SESSION_UPLOADS_BY_SPECIALIST, {})
        specialist_session_ids = session.get(SESSION_IDS_BY_SPECIALIST, {})

        # Delete uploaded files from specialist-scoped state.
        if isinstance(specialist_uploads, dict):
            for specialist_files in specialist_uploads.values():
                if not isinstance(specialist_files, list):
                    continue
                for file_info in specialist_files:
                    try:
                        filepath = file_info.get('filepath')
                        if filepath and os.path.exists(filepath):
                            os.remove(filepath)
                    except:
                        pass

        # Delete uploaded files from legacy shared state (backward compatibility).
        legacy_uploaded_files = session.get('uploaded_files', [])
        if isinstance(legacy_uploaded_files, list):
            for file_info in legacy_uploaded_files:
                try:
                    filepath = file_info.get('filepath')
                    if filepath and os.path.exists(filepath):
                        os.remove(filepath)
                except:
                    pass

        # Delete RAG pipelines from specialist-scoped session IDs.
        if isinstance(specialist_session_ids, dict):
            for specialist_session_id in specialist_session_ids.values():
                if specialist_session_id and specialist_session_id in rag_pipelines:
                    try:
                        rag_pipelines[specialist_session_id].delete_collection()
                        del rag_pipelines[specialist_session_id]
                    except:
                        pass

        # Delete legacy RAG pipeline if present.
        legacy_session_id = session.get('session_id')
        if legacy_session_id and legacy_session_id in rag_pipelines:
            try:
                rag_pipelines[legacy_session_id].delete_collection()
                del rag_pipelines[legacy_session_id]
            except:
                pass
        
        # Clear session
        session.clear()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error clearing session: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/patient-info', methods=['POST'])
def save_patient_info():
    """Save patient information to session"""
    try:
        data = request.get_json()
        session['patient_name'] = data.get('name', 'Patient')
        session['patient_age'] = data.get('age', 'Not specified')
        session['patient_gender'] = data.get('gender', 'Not specified')
        session.modified = True
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=8000, debug=True)