# 🩸 RaktDhara (रक्त धारा) — Smart Blood Donation & Request Portal

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**RaktDhara** is a full-featured, automated blood donation and emergency request management platform built with Python (Flask) and MySQL. It bridges the gap between blood requesters and eligible donors in real time by leveraging a **smart blood compatibility matrix**, **GPS-based proximity matching (Haversine algorithm)**, **one-click email response triggers**, and **automated ticket lifecycle management**.

---

## 📑 Table of Contents

- [Key Features](#-key-features)
- [Blood Compatibility Matrix](#-blood-compatibility-matrix)
- [System Architecture & Workflow](#-system-architecture--workflow)
- [Tech Stack](#-tech-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Database Setup & Schema](#-database-setup--schema)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [Application Routes & Endpoints](#-application-routes--endpoints)
- [Default Admin Credentials](#-default-admin-credentials)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Key Features

### 1. 🧑‍🤝‍🧑 Donor Registration & Verification
- Comprehensive donor profile recording: personal details, contact, blood group, Aadhar number, medical background, medication history, and GPS coordinates.
- **Email OTP Verification**: 6-digit one-time password with a 10-minute expiry window.
- **Automated Password Generation**: Secure random credentials auto-generated and emailed upon successful verification.

### 2. 📍 Smart Blood Request & Proximity Matching
- Requesters can submit an emergency blood request with hospital/location details and GPS coordinates.
- Generates a unique tracking ID (`TKT-XXXXXXXX`).
- **Haversine Distance Formula**: Automatically scans and ranks verified compatible donors within a **50 km radius**.
- Dispatches emergency email alerts to nearest donors with one-click **Accept (`YES`)** or **Decline (`NO`)** action links.

### 3. 🎫 Real-Time Ticket Tracking & Donor Status
- Requesters and donors can track live responses for any ticket ID.
- Displays donor acceptance statuses, response timestamps, and direct contact details.
- **Star Donors Recognition**: Highlights donors who have successfully fulfilled blood donation requests.
- Live public counters: Total Registered Donors, Total Requests, and Closed/Fulfilled Requests.

### 4. ⏰ Automated Background Scheduler (APScheduler)
- Background worker checks active tickets periodically.
- Automatically finalizes and closes expired requests older than **48 hours**.
- Dispatches automated completion/status notifications to requester, donors, and the administrator.

### 5. 🛡️ User & Administrator Dashboards
- **Donor Dashboard**: View personal donation stats, track active/past requests, update password, and manage tickets.
- **Admin Portal (`/admin`)**:
  - Verify / Unverify donors manually.
  - Reset donor passwords.
  - Delete donor records or expired blood requests.
  - Review and moderate user feedback.

---

## 🩸 Blood Compatibility Matrix

RaktDhara enforces medical compatibility rules to ensure requests are routed only to medically suitable donors:

| Receiver Blood Group | Eligible Donor Blood Groups |
| :---: | :--- |
| **A+** | `A+`, `A-`, `O+`, `O-` |
| **A-** | `A-`, `O-` |
| **B+** | `B+`, `B-`, `O+`, `O-` |
| **B-** | `B-`, `O-` |
| **AB+** (Universal Recipient) | `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-` |
| **AB-** | `A-`, `B-`, `AB-`, `O-` |
| **O+** | `O+`, `O-` |
| **O-** (Universal Donor) | `O-` |

---

## 🔄 System Architecture & Workflow

```
[ Requester creates request ]
             │
             ▼
[ Generate Ticket ID (TKT-XXXXXXXX) ]
             │
             ▼
[ Filter Compatible Blood Groups ]
             │
             ▼
[ Calculate Distance using Haversine (<= 50 km) ]
             │
             ▼
[ Send Email Alerts to Nearest Donors ]
             │
      ┌──────┴──────┐
      ▼             ▼
[ Donor Accepts ] [ Donor Declines ]
      │             │
      ▼             ▼
[ Notify Requester ] [ Log in DB ]
      │
      ▼
[ Auto-Close after 48 hrs / Manual Close ]
```

---

## 💻 Tech Stack

- **Backend**: Python 3.8+, Flask
- **Security & Hashing**: Werkzeug (`generate_password_hash`, `check_password_hash`)
- **Database**: MySQL 8.0+ / MariaDB via `mysql-connector-python`
- **Email Delivery**: SMTP via Python `smtplib` and `email.mime` (TLS port 587)
- **Task Scheduling**: `APScheduler` (BackgroundScheduler)
- **Frontend**: HTML5, CSS3, JavaScript, Jinja2 Templates, FontAwesome, Bootstrap

---

## 📂 Project Directory Structure

```text
RaktDhara/
├── app.py                      # Core Flask application, routing, and background jobs
├── static/                     # Static media and assets
│   ├── logo.ico                # Application favicon
│   ├── logo_circular.ico       # Circular favicon variant
│   ├── logo.jpeg               # Branding logo
│   ├── Developer.jpg           # Team asset
│   ├── Marketing_Head.jpeg     # Team asset
│   ├── Programmer1.jpeg        # Team asset
│   ├── images/                 # Image assets
│   └── images1/                # UI icons and graphics
├── templates/                  # Jinja2 HTML templates
│   ├── admin_dashboard.html    # Administrative management panel
│   ├── admin_feedback.html     # Admin feedback overview
│   ├── admin_login.html        # Admin authentication
│   ├── admin_logout.html       # Admin session termination
│   ├── change_password.html    # Password update page
│   ├── dashboard.html          # User/donor portal
│   ├── donor_status.html       # Live ticket tracking & donor responses
│   ├── error.html              # Generic error page
│   ├── feedback.html           # Public user feedback submission
│   ├── forgot_password.html    # Password reset request via OTP
│   ├── home.html               # Home / Landing page
│   ├── index.html              # Index template
│   ├── login.html              # User login page
│   ├── my_requests.html        # Personal user request history
│   ├── register.html           # Donor registration form
│   ├── search.html             # Search donors / requests
│   ├── submit_feedback.html    # Feedback confirmation
│   ├── success.html            # Generic success view
│   ├── thank_you.html          # Response acknowledgment view
│   ├── user_logout.html        # User logout confirmation
│   ├── verify.html             # OTP entry page for registration
│   └── verify_reset.html       # OTP entry page for password reset
└── README.md                   # Project documentation
```

---

## ⚙️ Prerequisites

Ensure you have the following installed on your machine:
- **Python 3.8 or higher**: [Download Python](https://www.python.org/downloads/)
- **MySQL Server 8.0+**: [Download MySQL](https://dev.mysql.com/downloads/installer/) or XAMPP / MariaDB
- **Git**: [Download Git](https://git-scm.com/)

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/RaktDhara.git
cd RaktDhara
```

### 2. Create and Activate a Virtual Environment
- **Windows (PowerShell)**:
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- **macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Required Dependencies
```bash
pip install Flask mysql-connector-python werkzeug apscheduler
```

---

## 🗄️ Database Setup & Schema

1. Open your MySQL client (Command Line, MySQL Workbench, or phpMyAdmin).
2. Create the database:
   ```sql
   CREATE DATABASE uit_bloodbank22 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   USE uit_bloodbank22;
   ```
3. Run the following DDL script to create the necessary tables:

```sql
-- 1. Donors Table
CREATE TABLE IF NOT EXISTS donors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    occupation VARCHAR(100),
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    dob DATE NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    permanent_address TEXT NOT NULL,
    gender VARCHAR(20) NOT NULL,
    weight FLOAT NOT NULL,
    aadhar_number VARCHAR(20) NOT NULL UNIQUE,
    whatsapp_number VARCHAR(20),
    travel_history TEXT,
    current_location VARCHAR(255),
    health_condition TEXT,
    medications TEXT,
    latitude DECIMAL(10, 8) DEFAULT NULL,
    longitude DECIMAL(11, 8) DEFAULT NULL,
    verified BOOLEAN DEFAULT FALSE,
    password_code VARCHAR(255) DEFAULT NULL,
    age_consent BOOLEAN DEFAULT TRUE,
    donation_consent BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. OTP Verification Table
CREATE TABLE IF NOT EXISTS otp_verification (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(150) NOT NULL,
    otp VARCHAR(10) NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Blood Requests Table
CREATE TABLE IF NOT EXISTS blood_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id VARCHAR(50) NOT NULL UNIQUE,
    requester_name VARCHAR(150) NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    location VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(150) NOT NULL,
    message TEXT,
    status VARCHAR(20) DEFAULT 'OPEN',
    requester_closed BOOLEAN DEFAULT FALSE,
    donor_closed BOOLEAN DEFAULT FALSE,
    closed_at DATETIME DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Donor Responses Table
CREATE TABLE IF NOT EXISTS donor_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    donor_email VARCHAR(150) NOT NULL,
    response ENUM('YES', 'NO') NOT NULL,
    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES blood_requests(id) ON DELETE CASCADE,
    UNIQUE KEY unique_request_donor (request_id, donor_email)
);

-- 5. Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 Configuration

Update the connection and mail parameters in [`app.py`](app.py) or set them using environment variables:

### 1. Database Credentials
In `app.py`:
```python
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # Your MySQL username
        password="your_password",  # Your MySQL password
        database="uit_bloodbank22"
    )
```

### 2. SMTP Email Setup (Gmail)
To send OTP verification emails and notifications:
1. Enable **2-Step Verification** in your Google Account.
2. Generate an **App Password** from [Google App Passwords](https://myaccount.google.com/apppasswords).
3. Set your credentials in `app.py`:
   ```python
   EMAIL_ADDRESS = "your_email@gmail.com"
   EMAIL_PASSWORD = "your_16_char_app_password"
   ```

---

## 🏃 Running the Application

Once your virtual environment is active and the database is running:

```powershell
python app.py
```

The Flask development server will start at:
```text
http://127.0.0.1:5000/
```

Access the application in your browser:
- **Public Home / Request Blood**: `http://localhost:5000/`
- **Donor Registration**: `http://localhost:5000/register`
- **Live Ticket Tracker**: `http://localhost:5000/donor_status`
- **User Dashboard**: `http://localhost:5000/login`
- **Admin Portal**: `http://localhost:5000/admin`

---

## 🧭 Application Routes & Endpoints

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/` | `GET` | Home page & landing view |
| `/register` | `GET`, `POST` | New donor registration form |
| `/verify` / `/verify_otp` | `GET`, `POST` | OTP verification step for new donors |
| `/request_blood` | `POST` | Submit emergency blood request & alert donors |
| `/accept_request` | `GET` | Donor response acceptance link from email |
| `/decline_request` | `GET` | Donor response decline link from email |
| `/donor_status` | `GET`, `POST` | Public ticket status and donor responses view |
| `/close_ticket/<id>` | `POST` | Mark an active ticket as fulfilled/closed |
| `/login` | `GET`, `POST` | User authentication |
| `/dashboard` | `GET` | Authenticated user profile and donation panel |
| `/my_requests` | `GET` | History of requests submitted by current user |
| `/reset_password` | `GET`, `POST` | Forgot password initiation |
| `/change_password` | `GET`, `POST` | Update user password |
| `/feedback` | `GET`, `POST` | Submit feedback/inquiries |
| `/admin` | `GET`, `POST` | Administrator authentication |
| `/admin/dashboard` | `GET` | Full management dashboard for donors & requests |
| `/admin/feedback` | `GET` | Admin feedback overview |

---

## 🔑 Default Admin Credentials

- **Email**: `uitbloodbank@gmail.com`
- **Password**: `Admin@123`
- **URL**: `http://localhost:5000/admin`

> [!TIP]
> Make sure to update `ADMIN_EMAIL` and `ADMIN_PASSWORD_HASH` in `app.py` before deploying to production.

---

## 🤝 Contributing

Contributions make the open-source community a better place to learn, inspire, and create:
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m "Add some AmazingFeature"`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<p align="center">
  Made with ❤️ by <b>RaktDhara Team</b> — <i>Together, we save lives.</i>
</p>
