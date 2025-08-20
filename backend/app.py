from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "hello" 

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",      # Change if not local
        user="root",           # Your MySQL username
        password="G1234512345",  # Your MySQL password
        database="arogyam",
    )


# Home Page
@app.route("/")
def home():
    return render_template("1main.html")

# Doctor Consultation Page
@app.route("/doctor")
def doctor_consultation():
    return render_template("2dp.html")

# AI Consultation Page (optional)
@app.route("/ai")
def ai_consultation():
    return "<h1>AI Consultation Page Coming Soon</h1>"

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

# 🔹 Patient Dashboard Route
@app.route("/patient_dashboard")
def patient_dashboard():
    specialists = get_specialists()
    return render_template("mainpatientpage.html", specialists=specialists)

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
            conn.commit()
            cursor.close()
            conn.close()

            flash("Registration successful! Welcome to your dashboard.", "success")
            return redirect(url_for("patient_dashboard"))

        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("login_patient"))

    return render_template("mainpatientpage.html") # Show the signup form

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

        # Check if the user exists with given name & password
        cursor.execute("SELECT * FROM patients WHERE name = %s AND password = %s", (name, password))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:  # Found a match
            # ✅ Redirect to dashboard, just like signup
            return redirect(url_for("patient_dashboard"))
        else:
            return render_template("pl.html", error="Invalid name or password. Please sign up.")

    # If method is GET → just show login page
    return render_template("pl.html")

@app.route("/specialist/<specialization>")
def show_specialist(specialization):
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

    return render_template("specialist_doctors.html", specialization=specialization, doctors=doctors)

@app.route("/logindoctor")
def dl():
    return render_template("dl.html")

@app.route("/doctor_login")
def dal():
    return render_template("dal.html")


@app.route("/doctor_dashboard")
def doctordashboard():
    license_number = request.args.get("license")
    if not license_number:
        flash("You must log in first", "danger")
        return redirect(url_for("dl"))  # or your login/signup page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM doctors WHERE license_number = %s", (license_number,))
    doctor = cursor.fetchone()

    cursor.close()
    conn.close()

    if not doctor:
        flash("Doctor not found", "danger")
        return redirect(url_for("dl"))

    return render_template("doctordashboard.html", doctor=doctor)

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
            flash(f"Welcome Dr. {doctor['name']}!", "success")
            return redirect(url_for("doctordashboard", license=doctor['license_number']))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for("doctor_login"))

    # GET request → just render the login form
    return render_template("dal.html")

@app.route("/chat/<int:doctor_id>")
def chat(doctor_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM doctors WHERE id = %s", (doctor_id,))
    doctor = cursor.fetchone()
    cursor.close()

    if not doctor:
        return "Doctor not found", 404

    return render_template("chat_doctor.html", doctor=doctor)


if __name__ == "__main__":
    app.run(debug=True)
