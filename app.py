from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import threading
import random
import string
import smtplib
import re
import uuid
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ImportError:
    class BackgroundScheduler:
        def start(self):
            pass

        def scheduled_job(self, *_args, **_kwargs):
            def decorator(func):
                return func
            return decorator


app = Flask(__name__)
app.secret_key = "supersecretkey123"  # Session secret key

# ---------- Blood Group Compatibility ----------
COMPATIBILITY = {
    "A+":  {"donate_to": ["A+", "AB+"], "receive_from": ["A+", "A-", "O+", "O-"]},
    "A-":  {"donate_to": ["A+", "A-", "AB+", "AB-"], "receive_from": ["A-", "O-"]},
    "B+":  {"donate_to": ["B+", "AB+"], "receive_from": ["B+", "B-", "O+", "O-"]},
    "B-":  {"donate_to": ["B+", "B-", "AB+", "AB-"], "receive_from": ["B-", "O-"]},
    "AB+": {"donate_to": ["AB+"], "receive_from": ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]},
    "AB-": {"donate_to": ["AB+", "AB-"], "receive_from": ["A-", "B-", "AB-", "O-"]},
    "O+":  {"donate_to": ["O+", "A+", "B+", "AB+"], "receive_from": ["O+", "O-"]},
    "O-":  {"donate_to": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"], "receive_from": ["O-"]},
}


def get_compatible_donor_groups(receiver_group: str):
    receiver_group = (receiver_group or "").strip().upper()
    if receiver_group not in {k.upper() for k in COMPATIBILITY.keys()}:
        return []
    compatible_donors = []
    for donor_group, rules in COMPATIBILITY.items():
        if receiver_group in [g.upper() for g in rules["donate_to"]]:
            compatible_donors.append(donor_group)
    return compatible_donors


# ---------- Database Connection Setup ----------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Kaularu@1234",
        database="uit_bloodbank22"
    )


# ---------- Email Configuration ----------
EMAIL_ADDRESS = "uitbloodbank@gmail.com"
EMAIL_PASSWORD = "kskomslfkwnsrvsu"

# ---------- OTP storage (used only for password-reset flow) ----------
otp_store = {}


def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "@$!%*?&"
    return ''.join(random.choice(chars) for _ in range(length))


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(to_email, otp):
    try:
        msg = MIMEText(f"Your OTP for Rakt Dhara is {otp}")
        msg['Subject'] = "Rakt Dhara OTP"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        print(f"✅ OTP sent to {to_email}")
        return True
    except Exception as e:
        print("EMAIL ERROR:", e)
        return False


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


def send_registration_success_email(to_email, password):
    subject = "🎉 Registration Successful – Rakt Dhara"
    body = f"""
Dear User,

🎉 Congratulations! You have been successfully registered on the Rakt Dhara portal.

🔐 Login Credentials:
Username: {to_email}
Password: {password}

⚠️ Please login and change your password immediately for security reasons.

🔗 Login here:
http://localhost:5000/login

Thank you for joining Rakt Dhara ❤️
Together, we save lives.

Regards,
Rakt Dhara Team
"""
    return send_email(to_email, subject, body)

# ------------------- Routes -------------------

@app.route('/')
def home():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM blood_requests ORDER BY created_at DESC LIMIT 5")
    blood_requests = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("register.html", blood_requests=blood_requests)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        data = request.form
        email = data["email"]

        db = get_db()
        cur = db.cursor()

        # Check duplicate Aadhar
        cur.execute(
            "SELECT id FROM donors WHERE aadhar_number = %s",
            (data["aadhar_number"],)
        )
        if cur.fetchone():
            flash("This Aadhar number is already registered.", "danger")
            cur.close()
            db.close()
            return redirect("/register")

        # Save donor (unverified)
        # Save donor (unverified) — with location
        cur.execute("""
            INSERT INTO donors
            (full_name, occupation, email, phone, dob, blood_group,
             permanent_address, gender, weight, aadhar_number,
             whatsapp_number, travel_history, current_location,
             health_condition, medications, latitude, longitude)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["name"], data["occupation"], email, data["phone"],
            data["dob"], data["blood_group"], data["permanent_address"],
            data["gender"], data["weight"], data["aadhar_number"],
            data["whatsapp_number"], data.get("travel_history"),
            data.get("current_location"), data.get("health_condition"),
            data.get("medications"),
            data.get("latitude") or None,
            data.get("longitude") or None
        ))

        # OTP
        otp = generate_otp()
        expiry = datetime.now() + timedelta(minutes=10)

        cur.execute("DELETE FROM otp_verification WHERE email=%s", (email,))
        cur.execute("""
            INSERT INTO otp_verification (email, otp, expires_at)
            VALUES (%s,%s,%s)
        """, (email, otp, expiry))

        db.commit()
        cur.close()
        db.close()

        email_sent = send_otp_email(email, otp)

        if not email_sent:
            flash("Failed to send OTP email. Please try again.", "danger")
            return redirect("/register")

        session["verify_email"] = email
        flash("OTP sent to your email", "success")
        return redirect("/verify")

    return render_template("register.html")


@app.route("/verify")
def verify():
    return render_template("verify.html")


@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    otp_entered = request.form["otp"].strip()
    email = session.get("verify_email")

    if not email:
        flash("Session expired. Please register again.", "danger")
        return redirect("/register")

    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT * FROM otp_verification
        WHERE email=%s AND otp=%s
    """, (email, otp_entered))
    record = cur.fetchone()

    if not record:
        flash("Invalid OTP", "danger")
        cur.close()
        db.close()
        return redirect("/verify")

    if datetime.now() > record["expires_at"]:
        flash("OTP expired", "warning")
        cur.close()
        db.close()
        return redirect("/verify")

        raw_password = generate_password()
    hashed_password = generate_password_hash(raw_password)

    cur.execute("""
        UPDATE donors
        SET verified=TRUE, password_code=%s
        WHERE email=%s
    """, (hashed_password, email))

    cur.execute("DELETE FROM otp_verification WHERE email=%s", (email,))
    db.commit()
    cur.close()
    db.close()

    # Send credentials email
    email_sent = send_registration_success_email(email, raw_password)

    session.pop("verify_email", None)

    if email_sent:
        flash("Registration successful! Credentials sent to your email.", "success")
    else:
        # Fallback if email fails
        flash(f"Registration successful! Email failed. Your temporary password is: {raw_password}", "warning")

    return redirect("/login")

@app.route("/resend_otp")
def resend_otp():
    email = session.get("verify_email")
    if not email:
        flash("Session expired. Please register again.", "danger")
        return redirect("/register")

    otp = generate_otp()
    expiry = datetime.now() + timedelta(minutes=10)

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE otp_verification
        SET otp=%s, expires_at=%s
        WHERE email=%s
    """, (otp, expiry, email))
    db.commit()
    cur.close()
    db.close()

    send_otp_email(email, otp)
    flash("OTP resent successfully", "info")
    return redirect("/verify")


# Blood request submission
@app.route('/request_blood', methods=['POST'])
def request_blood():
    name = request.form['requester_name']
    blood_group = request.form['blood_group']
    location = request.form['location']
    phone = request.form['phone']
    email = request.form['email']
    message = request.form.get('message')

    # Get location from form
    try:
        req_lat = float(request.form.get('latitude'))
        req_lng = float(request.form.get('longitude'))
    except (TypeError, ValueError):
        req_lat = req_lng = None

    db = get_db()
    cursor = db.cursor()

    ticket_id = "TKT-" + uuid.uuid4().hex[:8].upper()

    # 1️⃣ Insert blood request
    cursor.execute("""
        INSERT INTO blood_requests
        (requester_name, blood_group, location, phone, email, message, created_at, ticket_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (name, blood_group, location, phone, email, message, datetime.now(), ticket_id))

    request_id = cursor.lastrowid
    db.commit()

    # 2️⃣ Find compatible verified donors (NEAREST FIRST)
    compatible_groups = get_compatible_donor_groups(blood_group)
    donors = []

    if compatible_groups:
        placeholders = ",".join(["%s"] * len(compatible_groups))

        if req_lat is not None and req_lng is not None:
            # Nearest donors first (within 50 km)
            query = f"""
                SELECT email, full_name, phone,
                       (6371 * acos(
                           cos(radians(%s)) * cos(radians(latitude))
                         * cos(radians(longitude) - radians(%s))
                         + sin(radians(%s)) * sin(radians(latitude))
                       )) AS distance_km
                FROM donors
                WHERE blood_group IN ({placeholders})
                  AND verified = TRUE
                  AND latitude IS NOT NULL
                  AND longitude IS NOT NULL
                HAVING distance_km <= 50
                ORDER BY distance_km ASC
                LIMIT 20
            """
            params = [req_lat, req_lng, req_lat] + list(compatible_groups)
        else:
            # Fallback if no location provided
            query = f"""
                SELECT email, full_name, phone, NULL AS distance_km
                FROM donors
                WHERE blood_group IN ({placeholders})
                  AND verified = TRUE
                LIMIT 20
            """
            params = list(compatible_groups)

        cursor.execute(query, params)
        donors = cursor.fetchall()

    cursor.close()
    db.close()

    # 3️⃣ Email requester
    send_email(
        email,
        "🎫 Your Blood Request Ticket ID",
        f"""Dear {name},

Your blood request has been submitted successfully.

🩸 Blood Group: {blood_group}
📍 Location: {location}
🎫 Ticket ID: {ticket_id}

We are notifying the nearest compatible donors first.

Thank you,
Team Rakt Dhara
"""
    )

    # 4️⃣ Email donors (already sorted nearest → farthest)
    BASE_URL = "http://127.0.0.1:5000"   # change after deployment
    subject = f"🩸 Urgent Blood Needed: {blood_group}"

    for donor in donors:
        donor_email = donor[0]
        donor_name  = donor[1]
        distance    = donor[3] if len(donor) > 3 else None

        accept_link  = f"{BASE_URL}/accept_request?request_id={request_id}&donor_email={donor_email}"
        decline_link = f"{BASE_URL}/decline_request?request_id={request_id}&donor_email={donor_email}"

        distance_text = f"{distance:.1f} km away" if distance is not None else "Distance unknown"

        body = f"""Dear {donor_name},

🩸 URGENT BLOOD REQUIREMENT 🩸

Patient Name : {name}
Blood Group  : {blood_group}
Location     : {location}
Distance     : {distance_text}
Ticket ID    : {ticket_id}

You are one of the nearest compatible donors.

Please respond:

✅ ACCEPT  → {accept_link}
❌ DECLINE → {decline_link}

Thank you for saving lives ❤️
— Team Rakt Dhara
"""
        send_email(donor_email, subject, body)

    flash(f"Blood request submitted! Nearest donors are being notified. Ticket ID: {ticket_id}", "success")
    return redirect(url_for("home"))

# Donor accepts request
@app.route('/accept_request')
def accept_request():
    try:
        request_id = int(request.args.get("request_id", 0))
    except (TypeError, ValueError):
        return "Invalid request ID", 400

    donor_email = request.args.get("donor_email")
    if not request_id or not donor_email:
        return "Invalid link", 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO donor_responses (request_id, donor_email, response, responded_at)
        VALUES (%s, %s, 'YES', NOW())
        ON DUPLICATE KEY UPDATE response='YES', responded_at=NOW()
    """, (request_id, donor_email))
    db.commit()

    cursor.execute("SELECT full_name, phone, blood_group FROM donors WHERE email=%s", (donor_email,))
    donor_info = cursor.fetchone()
    cursor.execute("SELECT email, ticket_id FROM blood_requests WHERE id=%s", (request_id,))
    requester = cursor.fetchone()
    cursor.close()
    db.close()

    if requester:
        requester_email, ticket_id = requester
        donor_msg = f"👤 {donor_info[0]}, 📞 {donor_info[1]}, 🩸 {donor_info[2]}" if donor_info else donor_email
        send_email(
            requester_email,
            "✅ Donor Accepted",
            f"A donor has accepted your blood request.\nTicket ID: {ticket_id}\nDonor Details:\n{donor_msg}"
        )

    return "Thank you for agreeing to donate! Requester notified."


# Donor declines request
@app.route('/decline_request')
def decline_request():
    try:
        request_id = int(request.args.get("request_id", 0))
    except (TypeError, ValueError):
        return "Invalid request ID", 400

    donor_email = request.args.get("donor_email")
    if not request_id or not donor_email:
        return "Invalid link", 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO donor_responses (request_id, donor_email, response)
        VALUES (%s, %s, 'NO')
        ON DUPLICATE KEY UPDATE response='NO', responded_at=NOW()
    """, (request_id, donor_email))
    db.commit()
    cursor.close()
    db.close()
    return "You have declined this request."


# Feedback
@app.route('/feedback')
def feedback():
    return render_template("feedback.html", current_year=datetime.now().year)


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO feedback (name, email, message) VALUES (%s, %s, %s)",
        (name, email, message)
    )
    db.commit()
    cursor.close()
    db.close()

    flash("Thank you for your feedback!", "success")
    return redirect(url_for("feedback"))


# -------- Forgot Password Flow --------
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        otp = random.randint(1000, 9999)
        otp_store[email] = {"otp": otp}
        send_otp_email(email, otp)
        flash("OTP sent to your email. Please verify.", "info")
        return render_template("verify_reset.html", email=email)
    return render_template("forgot_password.html")


@app.route('/verify_reset', methods=['POST'])
def verify_reset():
    email = request.form['email']
    otp = request.form['otp']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if email not in otp_store or str(otp_store[email]["otp"]) != otp:
        flash("❌ Invalid OTP", "danger")
        return render_template("verify_reset.html", email=email)

    if new_password != confirm_password:
        flash("❌ Passwords do not match", "danger")
        return render_template("verify_reset.html", email=email)

    if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$', new_password):
        flash("❌ Password must be at least 8 characters, include uppercase, number, and special character", "danger")
        return render_template("verify_reset.html", email=email)

    hashed_pw = generate_password_hash(new_password)
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE donors SET password_code=%s WHERE email=%s", (hashed_pw, email))
    db.commit()
    cursor.close()
    db.close()

    del otp_store[email]
    flash("✅ Password reset successful! Please login with your new password.", "success")
    return redirect(url_for("login"))


# ---------------- User Login ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "SELECT password_code FROM donors WHERE email=%s AND verified=TRUE",
            (email,)
        )
        row = cursor.fetchone()
        cursor.close()
        db.close()

        if row and check_password_hash(row[0], password):
            session['user_email'] = email
            return redirect(url_for('dashboard'))

        flash("Invalid credentials", "danger")
    return render_template("login.html")


# ---------------- Change Password ----------------
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if "user_email" not in session:
        flash("⚠ Please log in first", "warning")
        return redirect(url_for("login"))

    email = session["user_email"]

    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT password_code FROM donors WHERE email=%s", (email,))
            row = cursor.fetchone()

            if not row:
                flash("❌ Email not registered", "danger")
                return render_template("change_password.html")

            if not check_password_hash(row[0], old_password):
                flash("❌ Old password is incorrect", "danger")
                return render_template("change_password.html")

            if new_password != confirm_password:
                flash("❌ Passwords do not match", "danger")
                return render_template("change_password.html")

            if not re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$', new_password):
                flash("❌ Password must be at least 8 characters, include uppercase, number, and special character", "danger")
                return render_template("change_password.html")

            new_pass_hash = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE donors SET password_code=%s WHERE email=%s",
                (new_pass_hash, email)
            )
            db.commit()

            flash("✅ Password changed successfully! Please login again.", "success")
            session.pop("user_email", None)
            return redirect(url_for("login"))

        finally:
            cursor.close()
            db.close()

    return render_template("change_password.html")


# ---------------- Single clean Logout ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))


# ---------------- Admin ----------------
ADMIN_EMAIL = "uitbloodbank@gmail.com"
ADMIN_PASSWORD_HASH = generate_password_hash("Admin@123")


@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == ADMIN_EMAIL and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash("Invalid credentials", "danger")
    return render_template("admin_login.html")


@app.route("/admin/feedback")
def admin_feedback():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, name, email, message, created_at FROM feedback ORDER BY created_at DESC"
    )
    feedbacks = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("admin_feedback.html", feedbacks=feedbacks)


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id, full_name, occupation, dob, gender, blood_group, weight,
            permanent_address, current_location, email, phone, whatsapp_number,
            aadhar_number, health_condition, medications, travel_history,
            verified, age_consent, donation_consent, created_at, updated_at
        FROM donors
        ORDER BY id DESC
    """)
    donors = cursor.fetchall()

    cursor.execute("""
        SELECT
            id, ticket_id, requester_name, blood_group, location, phone, email,
            message, status, requester_closed, donor_closed, closed_at, created_at
        FROM blood_requests
        ORDER BY created_at DESC
    """)
    blood_requests = cursor.fetchall()

    request_responses = {}
    for req in blood_requests:
        cursor.execute("""
            SELECT id, request_id, donor_email, response, responded_at
            FROM donor_responses
            WHERE request_id = %s
            ORDER BY responded_at DESC
        """, (req["id"],))
        request_responses[req["id"]] = cursor.fetchall()

    cursor.execute("""
        SELECT id, name, email, message, created_at
        FROM feedback
        ORDER BY created_at DESC
    """)
    feedbacks = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin_dashboard.html",
        donors=donors,
        blood_requests=blood_requests,
        request_responses=request_responses,
        feedbacks=feedbacks
    )


@app.route("/admin/delete_feedback/<int:feedback_id>")
def admin_delete_feedback(feedback_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM feedback WHERE id=%s", (feedback_id,))
    db.commit()
    cursor.close()
    db.close()

    flash("🗑️ Feedback deleted successfully.", "danger")
    return redirect(url_for("admin_dashboard"))


@app.route('/admin/delete_request/<int:req_id>')
def admin_delete_request(req_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM blood_requests WHERE id=%s", (req_id,))
    db.commit()
    cursor.close()
    db.close()

    flash("✅ Request deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


@app.route("/admin/verify/<int:donor_id>")
def admin_verify(donor_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE donors SET verified=TRUE WHERE id=%s", (donor_id,))
    db.commit()
    cursor.close()
    db.close()

    flash("✅ Donor verified successfully.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/unverify/<int:donor_id>")
def admin_unverify(donor_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE donors SET verified=FALSE WHERE id=%s", (donor_id,))
    db.commit()
    cursor.close()
    db.close()

    flash("❌ Donor unverified successfully.", "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reset_password/<int:donor_id>")
def admin_reset_password(donor_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    # Properly hashed default password
    default_hashed = generate_password_hash("123456")

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE donors SET password_code=%s WHERE id=%s",
        (default_hashed, donor_id)
    )
    db.commit()
    cursor.close()
    db.close()

    flash("🔑 Password reset to default (123456) for donor.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/<int:donor_id>")
def admin_delete(donor_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM donors WHERE id=%s", (donor_id,))
    db.commit()
    cursor.close()
    db.close()

    flash("🗑️ Donor deleted successfully.", "danger")
    return redirect(url_for("admin_dashboard"))


# ---------------- Dashboard Stats Helper ----------------
def get_dashboard_stats():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total_donors FROM donors")
    total_donors = cursor.fetchone()["total_donors"]

    cursor.execute("SELECT COUNT(*) AS open_tickets FROM blood_requests WHERE status='OPEN'")
    open_tickets = cursor.fetchone()["open_tickets"]

    cursor.execute("SELECT COUNT(*) AS closed_tickets FROM blood_requests WHERE status='CLOSED'")
    closed_tickets = cursor.fetchone()["closed_tickets"]

    cursor.execute("SELECT COUNT(DISTINCT email) AS total_requestors FROM blood_requests")
    total_requestors = cursor.fetchone()["total_requestors"]

    cursor.close()
    db.close()

    return {
        "total_donors": total_donors,
        "open_tickets": open_tickets,
        "closed_tickets": closed_tickets,
        "total_requestors": total_requestors,
    }


@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect(url_for("login"))

    user_email = session["user_email"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM donors WHERE email=%s", (user_email,))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM blood_requests ORDER BY created_at DESC")
    blood_requests = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM blood_requests WHERE email=%s ORDER BY created_at DESC",
        (user_email,)
    )
    my_requests = cursor.fetchall()

    cursor.execute("""
        SELECT br.*, dr.responded_at
        FROM blood_requests br
        JOIN donor_responses dr ON br.id = dr.request_id
        WHERE dr.donor_email=%s
        ORDER BY dr.responded_at DESC
    """, (user_email,))
    donor_requests = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total_donors FROM donors WHERE blood_group IS NOT NULL")
    total_donors = cursor.fetchone()["total_donors"]

    cursor.execute("""
        SELECT DISTINCT s.full_name, s.blood_group, s.email, dr.responded_at
        FROM donor_responses dr
        JOIN blood_requests br ON dr.request_id = br.id
        LEFT JOIN donors s ON dr.donor_email = s.email
        WHERE dr.response='YES' AND br.status='CLOSED'
        ORDER BY dr.responded_at DESC
        LIMIT 5
    """)
    star_donors = cursor.fetchall()

    cursor.close()
    db.close()

    stats = get_dashboard_stats()

    return render_template(
        "dashboard.html",
        user=user,
        blood_requests=blood_requests,
        my_requests=my_requests,
        donor_requests=donor_requests,
        compatible_groups=get_compatible_donor_groups(user.get("blood_group") if user else None),
        star_donors=star_donors,
        **stats
    )


@app.route("/my_requests")
def my_requests():
    if "user_email" not in session:
        return redirect(url_for("login"))

    email = session["user_email"]

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM blood_requests WHERE email=%s ORDER BY created_at DESC",
        (email,)
    )
    my_requests = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("my_requests.html", my_requests=my_requests)


@app.route('/get_notifications')
def get_notifications():
    if 'user_email' not in session:
        return {"count": 0}

    email = session['user_email']
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id FROM blood_requests
        WHERE email=%s
        ORDER BY created_at DESC LIMIT 1
    """, (email,))
    latest_req = cursor.fetchone()

    count = 0
    if latest_req:
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM donor_responses
            WHERE request_id=%s
        """, (latest_req['id'],))
        count = cursor.fetchone()['cnt']

    cursor.close()
    db.close()
    return {"count": count}


# -------- Donor Status --------
@app.route("/donor_status", methods=["GET", "POST"])
def donor_status():
    request_data = None
    donors = []
    star_donors = []
    summary = {"yes": 0, "no": 0}
    error = None

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM donors WHERE blood_group IS NOT NULL")
    total_donors = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM blood_requests")
    total_requests = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM blood_requests WHERE status='CLOSED'")
    successful_donations = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT DISTINCT s.full_name, s.phone, s.blood_group, dr.donor_email
        FROM donor_responses dr
        JOIN blood_requests br ON dr.request_id = br.id
        LEFT JOIN donors s ON dr.donor_email = s.email
        WHERE dr.response='YES' AND br.status='CLOSED'
    """)
    star_donors = cursor.fetchall()

    if request.method == "POST":
        ticket_id = request.form.get("ticket_id", "").strip()

        cursor.execute("SELECT * FROM blood_requests WHERE ticket_id=%s", (ticket_id,))
        request_data = cursor.fetchone()

        if request_data:
            cursor.execute("""
                SELECT s.full_name, s.phone, s.blood_group, dr.donor_email, dr.response, dr.responded_at
                FROM donor_responses dr
                LEFT JOIN donors s ON dr.donor_email = s.email
                WHERE dr.request_id=%s
            """, (request_data["id"],))
            donors = cursor.fetchall()

            for d in donors:
                if d["response"] == "YES":
                    summary["yes"] += 1
                elif d["response"] == "NO":
                    summary["no"] += 1
        else:
            error = "❌ Invalid Ticket ID. Please try again."

    cursor.close()
    db.close()

    return render_template(
        "donor_status.html",
        request_data=request_data,
        donors=donors,
        star_donors=star_donors,
        summary=summary,
        error=error,
        total_donors=total_donors,
        total_requests=total_requests,
        successful_donations=successful_donations
    )


# ---------------- Scheduler & Ticket Finalization ----------------
scheduler = BackgroundScheduler()
scheduler.start()


def finalize_ticket(ticket_id, force=False):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM blood_requests WHERE ticket_id=%s", (ticket_id,))
    req = cursor.fetchone()
    if not req or req["status"] == "CLOSED":
        cursor.close()
        db.close()
        return

    if not force and (datetime.now() - req["created_at"]) < timedelta(hours=48):
        cursor.close()
        db.close()
        return

    cursor.execute("UPDATE blood_requests SET status='CLOSED' WHERE ticket_id=%s", (ticket_id,))
    db.commit()

    send_email(
        req["email"],
        "🎫 Ticket Closed",
        f"Dear {req['requester_name']},\n\nYour blood request (Ticket ID: {ticket_id}) has been CLOSED.\n\nThank you."
    )

    cursor.execute(
        "SELECT donor_email, response FROM donor_responses WHERE request_id=%s",
        (req["id"],)
    )
    donors = cursor.fetchall()
    for d in donors:
        send_email(
            d["donor_email"],
            "🎫 Ticket Closed",
            f"Ticket ID {ticket_id} is now CLOSED. Response recorded: {d['response']}."
        )

    send_email(
        "uitbloodbank@gmail.com",
        "🎫 Ticket Closed Notification",
        f"Ticket {ticket_id} was closed at {datetime.now()}."
    )

    cursor.close()
    db.close()


@app.route("/close_ticket/<int:ticket_id>", methods=["POST"])
def close_ticket(ticket_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM blood_requests WHERE id=%s", (ticket_id,))
    req = cursor.fetchone()
    if not req:
        flash("❌ Invalid Ticket ID", "danger")
        cursor.close()
        db.close()
        return redirect(url_for("dashboard"))

    user_email = session.get("user_email")
    if not user_email:
        flash("⚠ Login required to close ticket", "warning")
        cursor.close()
        db.close()
        return redirect(url_for("login"))

    authorized = False
    if user_email == req["email"]:
        authorized = True
    else:
        cursor.execute(
            "SELECT 1 FROM donor_responses WHERE request_id=%s AND donor_email=%s",
            (req["id"], user_email)
        )
        if cursor.fetchone():
            authorized = True

    if authorized:
        cursor.execute(
            "UPDATE blood_requests SET status=%s WHERE id=%s",
            ("CLOSED", ticket_id)
        )
        db.commit()
        flash("✅ Ticket closed successfully!", "success")
    else:
        flash("❌ You are not authorized to close this ticket", "danger")

    cursor.close()
    db.close()

    next_page = request.args.get("next", "dashboard")
    return redirect(url_for(next_page))


@scheduler.scheduled_job("interval", hours=1)
def auto_close_expired_tickets():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT ticket_id FROM blood_requests WHERE status='OPEN'")
    tickets = cursor.fetchall()
    for t in tickets:
        finalize_ticket(t["ticket_id"], force=False)
    cursor.close()
    db.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)