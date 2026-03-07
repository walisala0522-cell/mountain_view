import uuid
from flask import Flask, render_template, request, redirect, session, url_for, flash, make_response
from google_auth_oauthlib.flow import Flow
import requests
import os
import mysql.connector
from functools import wraps
from datetime import datetime, date, timedelta
from werkzeug.utils import secure_filename
import json
import tempfile

import qrcode

app = Flask(__name__)
app.secret_key = "mountainview_secret"
UPLOAD_FOLDER = 'static/slips'
ROOM_IMAGES_FOLDER = 'static/room_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ROOM_IMAGES_FOLDER'] = ROOM_IMAGES_FOLDER

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ROOM_IMAGES_FOLDER'], exist_ok=True)
os.makedirs('static/qr', exist_ok=True)

ADMIN_EMAIL = "mountainview.bungalow0522@gmail.com"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# ข้อมูลธุรกิจ - แก้ที่นี่ทีเดียว ใช้ทั้งเว็บ
BUSINESS_INFO = {
    "name": "Mountain View Bungalow",
    "phone": "052-234-567",           # เบอร์โทรที่พัก (แสดง)
    "phone_tel": "052234567",         # เบอร์สำหรับลิงก์โทร (ไม่มีขีด)
    "location": "จ.พังงา",
    "bank_account": "น.ส. วริศรา สมนึก",
    "bank_name": "พร้อมเพย์ / ธนาคารกสิกรไทย",
    "promptpay_id": "052234567",     # เบอร์พร้อมเพย์ สำหรับ QR (10 หลัก)
}

def _crc16_ccitt(data: bytes, init_val: int = 0xFFFF) -> int:
    """CRC16-CCITT (XMODEM) pure Python - ใช้กับ EMVCo PromptPay"""
    poly = 0x1021
    crc = init_val
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def _generate_promptpay_payload(phone: str, amount: float) -> str:
    """สร้าง EMVCo PromptPay payload ตามมาตรฐาน ธปท. (ธนาคารสแกนได้)"""
    import re
    target = re.sub(r"\D", "", phone)
    n = len(target)
    target_type = "01" if n < 13 else ("03" if n >= 15 else "02")
    if n < 13:
        target = re.sub(r"^0", "66", target) if target.startswith("0") else target
        target = ("0000000000000" + target)[-13:]
    guid = "A000000677010111"
    amount_str = f"{amount:.2f}" if amount else ""
    def _tag(tid: str, val: str) -> str:
        return tid + ("00" + str(len(val)))[-2:] + val
    parts = [
        _tag("00", "01"),
        _tag("01", "12" if amount_str else "11"),
        _tag("29", _tag("00", guid) + _tag(target_type, target)),
        _tag("58", "TH"),
        _tag("53", "764"),
    ]
    if amount_str:
        parts.append(_tag("54", amount_str))
    data2crc = "".join(parts) + "6304"
    crc = _crc16_ccitt(data2crc.encode("ascii"))
    return data2crc + ("0000" + hex(crc)[2:].upper())[-4:]

def _fallback_qr(booking_id, amount, qr_path):
    """สร้าง QR PromptPay มาตรฐาน EMVCo (ธนาคารสแกนได้)"""
    pid = BUSINESS_INFO.get("promptpay_id", "052234567")
    payload = _generate_promptpay_payload(pid, float(amount))
    img = qrcode.make(payload)
    img.save(qr_path)
    return os.path.basename(qr_path)

OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]

# Store Flow per OAuth session (state) - กัน code_verifier หายเมื่อ callback
_oauth_flows = {}

def _get_oauth_redirect_uri():
    """Get OAuth redirect URI - dynamic for different environments"""
    if os.environ.get('FLASK_ENV') == 'production':
        # For Render: use the actual domain
        return f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost:5000')}/callback"
    else:
        # Local development
        return "http://127.0.0.1:5000/callback"

def _create_flow():
    """Create Google OAuth Flow - supports file, environment variable, and Render Secret Files"""
    try:
        # Try Render Secret Files path first (highest priority)
        secret_file_paths = [
            "/etc/secrets/client_secret.json",  # Render Secret Files
            "client_secret.json",                # Local development
        ]
        
        for secret_path in secret_file_paths:
            if os.path.exists(secret_path):
                return Flow.from_client_secrets_file(
                    secret_path,
                    scopes=OAUTH_SCOPES,
                    redirect_uri=_get_oauth_redirect_uri()
                )
        
        # Fall back to environment variable
        if os.environ.get('GOOGLE_CLIENT_SECRET_JSON'):
            client_secret_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
            return Flow.from_client_config(
                json.loads(client_secret_json),
                scopes=OAUTH_SCOPES,
                redirect_uri=_get_oauth_redirect_uri()
            )
        
        print("⚠️ Google Auth Error: client_secret.json not found in any location")
        return None
    except Exception as e:
        print(f"⚠️ Google Auth Warning: {e}")
        return None

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="mountain_view"
    )

def get_room_statistics():
    """Get consistent room statistics for all pages - checks actual bookings"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) AS c FROM rooms WHERE is_active = 1")
        total_rooms = cursor.fetchone()['c']
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Occupied = has paid booking that includes today and hasn't checked out
        # occupied if there's a paid booking that started on/before today
        # and hasn't been checked out yet (actual checkout must be > today)
        # scheduled check-outs on today still count until actual checkout occurs.
        cursor.execute("""
            SELECT COUNT(DISTINCT room_id) AS c
            FROM bookings
            WHERE payment_status = 'paid'
              AND check_in <= %s
              AND (
                    (actual_checkout_date IS NULL AND check_out >= %s)
                 OR (actual_checkout_date > %s)
                  )
        """, (today_str, today_str, today_str))
        occupied_rooms = cursor.fetchone()['c']
        
        # Available = total - occupied
        available_rooms = total_rooms - occupied_rooms
        
        cursor.close()
        conn.close()
        
        return {
            'total': total_rooms,
            'available': available_rooms,
            'occupied': occupied_rooms
        }
    except Exception as e:
        return {
            'total': 0,
            'available': 0,
            'occupied': 0
        }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login", next=request.url))
        # เติม user_id ถ้ายังไม่มี (กรณี session เก่า)
        if "user_id" not in session and session.get("user"):
            session["user_id"] = session["user"].get("id")
        if not session.get("user_id"):
            session.clear()
            flash("กรุณาเข้าสู่ระบบใหม่", "error")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    return {
        "current_year": datetime.now().year,
        "business": BUSINESS_INFO,
    }

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        
        # Check role from session or DB
        role = session.get("role")
        if role != "admin":
             return "⛔ คุณไม่มีสิทธิ์เข้าแอดมิน"
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route("/")
def home():
    # Get consistent room statistics from shared helper
    room_stats = get_room_statistics()

    response = make_response(render_template(
        "home.html",
        total_rooms=room_stats['total'],
        available_rooms=room_stats['available']
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/login")
def login():
    next_page = request.args.get("next")
    if next_page:
        session["next"] = next_page
    return render_template("login.html")

@app.route("/login/google")
def login_google():
    flow_instance = _create_flow()
    if not flow_instance:
        return "Google Auth not configured", 500
    authorization_url, state = flow_instance.authorization_url()
    session["state"] = state
    _oauth_flows[state] = flow_instance  # เก็บ flow ตาม state เพื่อใช้ code_verifier ตอน callback
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    state = request.args.get("state")
    if not state or session.get("state") != state:
        return "State mismatch", 400

    flow_instance = _oauth_flows.pop(state, None)
    if not flow_instance:
        flash("Session หมดอายุ กรุณาลองเข้าสู่ระบบใหม่", "error")
        return redirect(url_for("login"))

    flow_instance.fetch_token(authorization_response=request.url)
    credentials = flow_instance.credentials
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    ).json()

    name = userinfo.get("name")
    email = userinfo.get("email")
    google_id = userinfo.get("id")

    if not email:
        return "Email not available", 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        role = "admin" if email == ADMIN_EMAIL else "customer"
        try:
            cursor.execute(
                "INSERT INTO users (name, email, role, google_id) VALUES (%s, %s, %s, %s)",
                (name, email, role, google_id)
            )
        except Exception:
            cursor.execute(
                "INSERT INTO users (name, email, role) VALUES (%s, %s, %s)",
                (name, email, role)
            )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
    
    # Update google_id if missing (column must exist)
    if not user.get('google_id') and google_id:
        try:
            cursor.execute("UPDATE users SET google_id = %s WHERE id = %s", (google_id, user['id']))
            conn.commit()
        except Exception:
            pass

    cursor.close()
    conn.close()

    session["user"] = user
    session["user_id"] = user["id"] # Important for bookings
    session["username"] = user["name"]
    session["role"] = user["role"]

    next_page = session.pop("next", None)
    if user["role"] == "admin":
        return redirect(url_for("admin"))
    
    return redirect(next_page or url_for("rooms"))

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("ออกจากระบบเรียบร้อยแล้ว", "success")
    return redirect(url_for("login"))

@app.route("/rooms")
def rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch rooms
    cursor.execute("""
        SELECT id, room_name, price, is_available 
        FROM rooms 
        WHERE is_active = 1
        ORDER BY id ASC
    """)
    db_rooms = cursor.fetchall()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    rooms_data = []
    for r in db_rooms:
        # Check if room has active booking (paid + today is in stay period)
        cursor.execute("""
            SELECT 1 FROM bookings 
            WHERE room_id = %s AND payment_status = 'paid'
              AND check_in <= %s 
              AND (
                    (actual_checkout_date IS NULL AND check_out >= %s)
                 OR (actual_checkout_date > %s)
                  )
            LIMIT 1
        """, (r['id'], today_str, today_str, today_str))
        has_booking = cursor.fetchone() is not None
        
        status = "ว่าง" if not has_booking else "มีคนใช้งานอยู่"

        # Fetch facilities
        cursor.execute("""
            SELECT f.icon_class, f.name 
            FROM facilities f 
            JOIN room_facilities rf ON f.id = rf.facility_id 
            WHERE rf.room_id = %s
        """, (r['id'],))
        facilities = cursor.fetchall()
        
        # Fetch images (take first one as main)
        cursor.execute("SELECT filename FROM room_images WHERE room_id = %s ORDER BY id ASC LIMIT 1", (r['id'],))
        img_data = cursor.fetchone()
        
        # Fallback logic
        if img_data:
            img = f"room_images/{img_data['filename']}"
        else:
            try:
                 num = ''.join(filter(str.isdigit, r['room_name']))
                 img = f"images/a{num}.jpg" if num else "images/default.jpg"
            except:
                 img = "images/default.jpg"
        
        rooms_data.append({
            "room_id": r['id'],
            "name": r['room_name'],
            "price": r['price'],
            "status": status,
            "image": img,
            "facilities": facilities
        })

    cursor.close()
    conn.close()
    
    response = make_response(render_template("rooms.html", rooms=rooms_data))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/room_details/<int:room_id>")
def room_details(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
    room = cursor.fetchone()
    
    if not room:
        return "Room not found", 404
        
    cursor.execute("SELECT filename FROM room_images WHERE room_id = %s", (room_id,))
    images = [row['filename'] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return {
        "name": room['room_name'],
        "price": room['price'],
        "images": images
    }

@app.route("/book/<int:room_id>", methods=["GET", "POST"])
@login_required
def book(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch room details
    cursor.execute("SELECT * FROM rooms WHERE id = %s AND is_active = 1", (room_id,))
    room = cursor.fetchone()
    
    if not room:
        cursor.close()
        conn.close()
        flash("ไม่พบห้องพัก")
        return redirect(url_for("rooms"))
        
    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT 1 FROM bookings 
        WHERE room_id = %s AND payment_status = 'paid'
        AND check_in <= %s 
        AND (
              (actual_checkout_date IS NULL AND check_out >= %s)
           OR (actual_checkout_date > %s)
              )
        LIMIT 1
    """, (room_id, today_str, today_str, today_str))
    has_staying = cursor.fetchone() is not None
    if has_staying and request.method == "GET":
        cursor.close()
        conn.close()
        flash("ห้องนี้ไม่ว่าง — มีคนใช้งานอยู่")
        return redirect(url_for("rooms"))

    # Image logic
    cursor.execute("SELECT filename FROM room_images WHERE room_id = %s ORDER BY id ASC LIMIT 1", (room_id,))
    img_data = cursor.fetchone()
    if img_data:
        room_image = f"room_images/{img_data['filename']}"
    else:
        try:
             num = ''.join(filter(str.isdigit, room['room_name']))
             room_image = f"images/a{num}.jpg" if num else "images/default.jpg"
        except:
             room_image = "images/default.jpg"

    # Pre-fill phone & name if available
    user_id = session.get("user_id")
    cursor.execute("SELECT phone, name FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    user_phone = user_data.get('phone', '') if user_data else ''
    user_name = user_data.get('name', '') if user_data else ''

    if request.method == "POST":
        checkin = request.form.get("checkin")
        checkout = request.form.get("checkout")
        name = request.form.get("name")
        phone = request.form.get("phone")
        guests = request.form.get("guests")
        # ตอนนี้ให้จองทีละ 1 ห้อง เพื่อลดความสับสนของผู้ใช้
        room_count = 1
        
        try:
            d1 = datetime.strptime(checkin, "%Y-%m-%d")
            d2 = datetime.strptime(checkout, "%Y-%m-%d")
            nights = (d2 - d1).days
            if nights <= 0: raise ValueError
            
            total_price = room['price'] * nights * int(room_count)
            
            # Check for overlapping bookings for the requested date range
            # Overlap condition: NOT (new_checkout <= existing_check_in OR new_checkin >= existing_checkout)
            cursor.execute("""
                SELECT 1 FROM bookings
                WHERE room_id = %s
                  AND payment_status IN ('paid','pending_verify','waiting_cash','pending')
                  AND NOT ( %s <= check_in OR %s >= COALESCE(actual_checkout_date, check_out) )
                LIMIT 1
            """, (room_id, checkout, checkin))
            conflict = cursor.fetchone() is not None
            if conflict:
                flash("ห้องนี้ไม่ว่างสำหรับวันที่เลือก — มีการจองทับซ้อน")
                cursor.close()
                conn.close()
                return redirect(request.url)

            # Insert Booking
            cursor.execute("""
                INSERT INTO bookings (
                    user_id, room_id, check_in, check_out, 
                    customer_name, phone, guest_count, room_count, 
                    total_price, payment_status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                session['user_id'], room_id, checkin, checkout,
                name, phone, guests, room_count,
                total_price, 'pending_verify' # Default status
            ))
            booking_id = cursor.lastrowid
            
            # Update user phone if empty
            if not user_phone and phone:
                cursor.execute("UPDATE users SET phone = %s WHERE id = %s", (phone, session['user_id']))
                
            conn.commit()
            cursor.close()
            conn.close()
            
            return redirect(url_for('payment', booking_id=booking_id))
            
        except Exception as e:
            flash("ข้อมูลการจองไม่ถูกต้อง")
            return redirect(request.url)
            
    cursor.close()
    conn.close()
    return render_template("book.html", room_id=room['id'], room_name=room['room_name'], room_image=room_image, user_phone=user_phone, user_name=user_name)

@app.route("/payment/<int:booking_id>", methods=["GET", "POST"])
@login_required
def payment(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT b.*, r.room_name 
        FROM bookings b 
        JOIN rooms r ON b.room_id = r.id 
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, session['user_id']))
    booking = cursor.fetchone()
    
    if not booking:
        cursor.close()
        conn.close()
        flash("ไม่พบรายการจอง")
        return redirect(url_for("rooms"))

    # Calculate nights for display
    d1 = booking['check_in'] # might be date object
    d2 = booking['check_out']
    if isinstance(d1, str): d1 = datetime.strptime(d1, "%Y-%m-%d").date()
    if isinstance(d2, str): d2 = datetime.strptime(d2, "%Y-%m-%d").date()
    nights = (d2 - d1).days

    # Prepare data for template
    booking_data = {
        "room": booking['room_name'],
        "customer": booking['customer_name'],
        "phone": booking['phone'],
        "checkin": booking['check_in'],
        "checkout": booking['check_out'],
        "nights": nights,
        "guests": booking['guest_count'],
        "rooms": booking['room_count']
    }
    
    if request.method == "POST":
        # กรณีแค่สลับวิธีชำระ (radio) ไม่บันทึก
        if request.form.get("keep_method"):
            pass  # จะ re-render ด้านล่างด้วย payment_method จาก form
        else:
            method = request.form.get("payment_method")
            if method == "qr":
                file = request.files.get("slip")
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_name = f"{uuid.uuid4()}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
                    cursor.execute("""
                        UPDATE bookings SET 
                        payment_method = 'qr', 
                        payment_status = 'pending_verify', 
                        slip_image = %s 
                        WHERE id = %s
                    """, (unique_name, booking_id))
                    conn.commit()
                    flash("แจ้งชำระเงินเรียบร้อยแล้ว", "success")
                    return redirect(url_for('my_bookings'))
                # ส่ง QR แต่ไม่มีไฟล์สลิป → แสดง error
                flash("กรุณาเลือกไฟล์สลิปการโอนเงิน", "error")
            elif method == "cash":
                cursor.execute("""
                    UPDATE bookings SET 
                    payment_method = 'cash', 
                    payment_status = 'waiting_cash' 
                    WHERE id = %s
                """, (booking_id,))
                conn.commit()
                flash("ยืนยันการชำระเงินสดแล้ว", "success")
                return redirect(url_for('my_bookings'))
            
    # QR Code Generation (PromptPay เบอร์ 052234567 ตามจำนวนเงิน)
    amount = float(booking['total_price'] or 0)
    qr_filename = f"qr_{booking_id}_{int(amount)}.png"
    qr_path = os.path.join("static", "qr", qr_filename)
    _fallback_qr(booking_id, amount, qr_path)
        
    cursor.close()
    conn.close()
    
    pm = request.form.get("payment_method", "qr") if request.method == "POST" else "qr"
    return render_template(
        "payment.html", 
        booking=booking_data, 
        total=booking['total_price'], 
        qr_filename=qr_filename,
        payment_method=pm
    )

@app.route("/my_bookings")
@login_required
def my_bookings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT b.*, r.room_name 
        FROM bookings b 
        JOIN rooms r ON b.room_id = r.id 
        WHERE b.user_id = %s 
        ORDER BY b.created_at DESC
    """, (session['user_id'],))
    
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template("my_bookings.html", bookings=bookings)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == "POST":
        phone = request.form.get("phone")
        name = request.form.get("name")
        cursor.execute("UPDATE users SET phone = %s, name = %s WHERE id = %s", (phone, name, session['user_id']))
        conn.commit()
        session['username'] = name # Update session
        flash("บันทึกข้อมูลเรียบร้อย", "success")
    
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template("profile.html", user=user)

# --- Admin Routes ---

@app.route("/admin")
@login_required
@admin_required
def admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Stats
    cursor.execute("SELECT COUNT(*) as c FROM bookings")
    total_bookings = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM bookings WHERE payment_status = 'paid'")
    paid_count = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM bookings WHERE payment_status = 'pending_verify'")
    pending_verify_count = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM bookings WHERE payment_status = 'waiting_cash'")
    waiting_cash_count = cursor.fetchone()['c']
    
    cursor.execute("SELECT COUNT(*) as c FROM bookings WHERE payment_status = 'pending'")
    pending_count = cursor.fetchone()['c']
    
    cursor.execute("SELECT SUM(total_price) as s FROM bookings WHERE payment_status = 'paid'")
    total_revenue = cursor.fetchone()['s'] or 0

    # Get consistent room statistics from shared helper function
    room_stats = get_room_statistics()
    total_rooms = room_stats['total']
    available_rooms_now = room_stats['available']
    occupied_rooms_now = room_stats['occupied']
    
    # Daily Revenue for Chart (Last 7 days)
    cursor.execute("""
        SELECT DATE(paid_at) as date, SUM(total_price) as total
        FROM bookings 
        WHERE payment_status = 'paid' AND paid_at >= DATE(NOW()) - INTERVAL 7 DAY
        GROUP BY DATE(paid_at)
        ORDER BY date ASC
    """)
    revenue_data = cursor.fetchall()
    
    # Daily Bookings Count (Last 7 days)
    cursor.execute("""
        SELECT DATE(paid_at) as date, COUNT(*) as count
        FROM bookings 
        WHERE payment_status = 'paid' AND paid_at >= DATE(NOW()) - INTERVAL 7 DAY
        GROUP BY DATE(paid_at)
        ORDER BY date ASC
    """)
    bookings_count_data = cursor.fetchall()
    
    # Combine data for chart
    dashboard_data = []
    for i in range(7):
        d = datetime.now() - timedelta(days=6-i)
        date_str = d.strftime("%Y-%m-%d")
        
        revenue = next((r['total'] for r in revenue_data if str(r['date']) == date_str), 0)
        count = next((b['count'] for b in bookings_count_data if str(b['date']) == date_str), 0)
        
        dashboard_data.append({
            "date": date_str,
            "date_display": d.strftime("%d/%m"),
            "revenue": revenue or 0,
            "bookings": count or 0
        })
    
    # Recent Bookings
    cursor.execute("""
        SELECT b.*, r.room_name 
        FROM bookings b 
        LEFT JOIN rooms r ON b.room_id = r.id 
        ORDER BY b.created_at DESC LIMIT 20
    """)
    bookings = cursor.fetchall()
    
    # Adapt for template
    today = datetime.now().date()
    display_bookings = []
    for b in bookings:
        status_map = {
            'paid': 'ชำระเงินแล้ว',
            'pending_verify': 'รอตรวจสอบสลิป',
            'waiting_cash': 'รอชำระเงินสด',
            'pending': 'รอชำระเงิน'
        }
        d1 = b['check_in'] if isinstance(b['check_in'], str) else b['check_in']
        d2_raw = b.get('actual_checkout_date') or b['check_out']
        d2 = d2_raw if isinstance(d2_raw, str) else d2_raw
        if isinstance(d1, str): d1 = datetime.strptime(str(d1)[:10], "%Y-%m-%d").date()
        if isinstance(d2, str): d2 = datetime.strptime(str(d2)[:10], "%Y-%m-%d").date()
        nights = (d2 - d1).days if d1 and d2 else 0
        pm = b.get('payment_method') or ''
        payment_label = 'โอน/QR' if pm == 'qr' else ('เงินสด' if pm == 'cash' else pm or '-')
        created = b.get('created_at')
        paid = b.get('paid_at')
        created_str = created.strftime('%d/%m/%y %H:%M') if created else '-'
        paid_str = paid.strftime('%d/%m/%y') if paid else '-'
        actual_checkout = b.get('actual_checkout_date')
        checkout_time = b.get('checkout_time') or '12:00'
        
        # Check if currently staying: paid + check_in <= today + (check_out OR actual_checkout) >= today
        # derive checkout_date and then apply logic similar to get_room_statistics
        # if actual_checkout is set, they count as staying only if that date is > today
        checkout_date = actual_checkout if actual_checkout else b['check_out']
        if isinstance(checkout_date, str):
            checkout_date = datetime.strptime(str(checkout_date)[:10], "%Y-%m-%d").date()
        if b['payment_status'] == 'paid' and d1 and checkout_date:
            if actual_checkout:
                is_staying = d1 <= today < checkout_date  # actual_checkout must be in future
            else:
                is_staying = d1 <= today <= checkout_date
        else:
            is_staying = False
        
        # Determine display status
        if actual_checkout is not None:
            # Person has already checked out
            status = "เช็คเอาท์แล้ว"
        else:
            status = status_map.get(b['payment_status'], b['payment_status'])
        checkout_display = (actual_checkout.strftime('%Y-%m-%d') if isinstance(actual_checkout, date) else str(actual_checkout)) if actual_checkout else (b['check_out'].strftime('%Y-%m-%d') if isinstance(b['check_out'], date) else str(b['check_out']))
        checkout_full = f"{checkout_display} {checkout_time}" if checkout_time else checkout_display

        display_bookings.append({
            "id": b['id'],
            "customer": b['customer_name'],
            "phone": b['phone'],
            "room": b['room_name'],
            "checkin": b['check_in'],
            "checkout": b['check_out'],
            "actual_checkout": actual_checkout,
            "checkout_time": checkout_time,
            "checkout_full": checkout_full,
            "room_id": b.get('room_id'),
            "nights": nights,
            "guests": b.get('guest_count') or 0,
            "rooms": b.get('room_count') or 1,
            "price": b['total_price'] or 0,
            "payment_method": pm,
            "payment_label": payment_label,
            "status": status,
            "status_raw": b['payment_status'],
            "is_staying": is_staying,
            "slip_image": b['slip_image'],
            "created_at": created_str,
            "paid_at": paid_str
        })
        
    latest = display_bookings[0] if display_bookings else None
    
    cursor.close()
    conn.close()
    
    return render_template(
        "admin.html",
        booking=latest,
        bookings=display_bookings,
        total_bookings=total_bookings,
        paid_count=paid_count,
        pending_verify_count=pending_verify_count,
        waiting_cash_count=waiting_cash_count,
        pending_count=pending_count,
        total_revenue=total_revenue,
        total_rooms=total_rooms,
        available_rooms_now=available_rooms_now,
        occupied_rooms_now=occupied_rooms_now,
        revenue_data=revenue_data,
        dashboard_data=dashboard_data
    )

@app.route("/admin/rooms", methods=["GET", "POST"])
@login_required
@admin_required
def admin_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # ➕ Add Room
    if request.method == "POST" and "add_room" in request.form:
        name = request.form.get("room_name")
        price = request.form.get("price")
        if name and price:
            cursor.execute("INSERT INTO rooms (room_name, price, is_available, is_active) VALUES (%s, %s, 1, 1)", (name, price))
            conn.commit()
        return redirect(url_for("admin_rooms"))
        
    # 📸 Upload Images
    if request.method == "POST" and "upload_image" in request.form:
        room_id = request.form.get("room_id")
        files = request.files.getlist("images")
        
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4()}_{filename}"
                file.save(os.path.join(app.config['ROOM_IMAGES_FOLDER'], unique_name))
                
                cursor.execute("INSERT INTO room_images (room_id, filename) VALUES (%s, %s)", (room_id, unique_name))
        conn.commit()
        return redirect(url_for("admin_rooms"))

    # 🛠️ Manage Facilities
    if request.method == "POST" and "update_facilities" in request.form:
        room_id = request.form.get("room_id")
        facility_ids = request.form.getlist("facilities") # list of facility IDs
        
        # Clear existing
        cursor.execute("DELETE FROM room_facilities WHERE room_id = %s", (room_id,))
        
        # Add new
        for fid in facility_ids:
            cursor.execute("INSERT INTO room_facilities (room_id, facility_id) VALUES (%s, %s)", (room_id, fid))
        conn.commit()
        return redirect(url_for("admin_rooms"))

    cursor.execute("SELECT * FROM rooms WHERE is_active = 1 ORDER BY id ASC")
    rooms = cursor.fetchall()
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Fetch all facilities for the modal
    cursor.execute("SELECT * FROM facilities")
    all_facilities = cursor.fetchall()
    
    rooms_available = []
    rooms_occupied = []
    for r in rooms:
        # determine occupancy by looking for an active paid booking that covers today
        cursor.execute(
            """
            SELECT 1 FROM bookings
            WHERE room_id = %s AND payment_status = 'paid'
              AND check_in <= %s
              AND (
                    (actual_checkout_date IS NULL AND check_out >= %s)
                 OR (actual_checkout_date > %s)
                  )
            LIMIT 1
            """,
            (r['id'], today_str, today_str, today_str)
        )
        occupied_flag = cursor.fetchone() is not None
        
        cursor.execute("SELECT facility_id FROM room_facilities WHERE room_id = %s", (r['id'],))
        my_facilities = [row['facility_id'] for row in cursor.fetchall()]
        cursor.execute("SELECT COUNT(*) as c FROM room_images WHERE room_id = %s", (r['id'],))
        img_count = cursor.fetchone()['c']
        
        # check for manual override mismatch
        note = ''
        if r.get('is_available') == 0 and not occupied_flag:
            note = ' (ปิดใช้งานชั่วคราว)'
        elif r.get('is_available') == 1 and occupied_flag:
            note = ' (มีการจองแล้วแต่ยังไม่ได้เช็คเอาท์)'
        
        room_item = {
            "room_id": r['id'],
            "room_name": r['room_name'] + note,
            "price": r['price'],
            "status": "มีคนใช้งานอยู่" if occupied_flag else "ว่าง",
            "my_facilities": my_facilities,
            "img_count": img_count
        }
        if occupied_flag:
            rooms_occupied.append(room_item)
        else:
            rooms_available.append(room_item)
        
    cursor.close()
    conn.close()
    
    response = make_response(render_template("admin_rooms.html", rooms_available=rooms_available, rooms_occupied=rooms_occupied, all_facilities=all_facilities))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/admin/toggle_status/<int:room_id>")
@login_required
@admin_required
def toggle_status(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rooms SET is_available = NOT is_available WHERE id = %s", (room_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("admin_rooms"))

@app.route("/admin/update_price/<int:room_id>", methods=["POST"])
@login_required
@admin_required
def update_price(room_id):
    price = request.form.get("price")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rooms SET price = %s WHERE id = %s", (price, room_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("admin_rooms"))

@app.route("/admin/delete_room/<int:room_id>")
@login_required
@admin_required
def delete_room(room_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Soft delete
    cursor.execute("UPDATE rooms SET is_active = 0 WHERE id = %s", (room_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("admin_rooms"))

@app.route("/admin_logout") # Matches template
def admin_logout():
    return redirect(url_for("logout"))
    
@app.route("/confirm_qr_payment/<int:id>")
@login_required
@admin_required
def confirm_qr_payment(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET payment_status = 'paid', paid_at = NOW() WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("ยืนยันการชำระเงิน (QR) แล้ว", "success")
    return redirect(url_for("admin"))

@app.route("/admin/checkout_now/<int:booking_id>")
@login_required
@admin_required
def checkout_now(booking_id):
    """เช็คเอาท์ทันที — ลูกค้าออกก่อนเวลา"""
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        checkout_time_val = datetime.now().strftime("%H:%M")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First, verify the booking exists and is paid, get room_id
        cursor.execute("""
            SELECT id, payment_status, customer_name, total_price, room_id FROM bookings WHERE id = %s
        """, (booking_id,))
        booking = cursor.fetchone()
        
        if not booking:
            flash("ไม่พบการจอง", "error")
            cursor.close()
            conn.close()
            return redirect(url_for("admin"))
        
        if booking['payment_status'] != 'paid':
            flash(f"❌ ยังไม่ชำระเงิน (สถานะ: {booking['payment_status']})", "error")
            cursor.close()
            conn.close()
            return redirect(url_for("admin"))
        
        # Update checkout info
        cursor.execute("""
            UPDATE bookings 
            SET actual_checkout_date = %s, checkout_time = %s 
            WHERE id = %s
        """, (today_str, checkout_time_val, booking_id))
        
        conn.commit()
        affected = cursor.rowcount
        
        # Mark room as available if checkout was successful
        if affected > 0 and booking['room_id']:
            cursor.execute("""
                UPDATE rooms SET is_available = 1 WHERE id = %s
            """, (booking['room_id'],))
            conn.commit()
        
        # Verify the update worked
        if affected > 0:
            cursor.execute("""
                SELECT actual_checkout_date, checkout_time FROM bookings WHERE id = %s
            """, (booking_id,))
            updated = cursor.fetchone()
            if updated:
                flash(f"✅ เช็คเอาท์เรียบร้อยแล้ว ({updated['actual_checkout_date']} {updated['checkout_time']}) — ห้องว่างแล้ว", "success")
            else:
                flash("⚠️ อัพเดทแล้วแต่ตรวจสอบไม่ได้", "warning")
        else:
            flash("❌ ไม่สามารถอัพเดทข้อมูลได้", "error")
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"❌ เกิดข้อผิดพลาด: {str(e)}", "error")
    
    return redirect(url_for("admin"))

@app.route("/admin/update_checkout/<int:booking_id>", methods=["POST"])
@login_required
@admin_required
def update_checkout(booking_id):
    try:
        actual_date = request.form.get("actual_checkout_date")
        checkout_time_val = request.form.get("checkout_time", "12:00")
        
        # Validate time format
        if checkout_time_val and not checkout_time_val.replace(":", "").isdigit():
            flash("❌ เวลาไม่ถูกต้อง (ใช้รูปแบบ HH:MM)", "error")
            return redirect(url_for("booking_detail", booking_id=booking_id))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get booking info to update room status
        cursor.execute("""
            SELECT id, room_id, check_in, check_out FROM bookings WHERE id = %s
        """, (booking_id,))
        booking = cursor.fetchone()
        
        if actual_date:
            cursor.execute("""
                UPDATE bookings 
                SET actual_checkout_date = %s, checkout_time = %s 
                WHERE id = %s
            """, (actual_date, checkout_time_val or "12:00", booking_id))
            # Mark room as available when checkout date is set
            if booking and booking['room_id']:
                cursor.execute("""
                    UPDATE rooms SET is_available = 1 WHERE id = %s
                """, (booking['room_id'],))
        else:
            cursor.execute("""
                UPDATE bookings 
                SET actual_checkout_date = NULL, checkout_time = %s 
                WHERE id = %s
            """, (checkout_time_val or "12:00", booking_id))
            # Mark room as NOT available when checkout date is cleared (person still staying)
            if booking and booking['room_id']:
                cursor.execute("""
                    UPDATE rooms SET is_available = 0 WHERE id = %s
                """, (booking['room_id'],))
        
        conn.commit()
        affected = cursor.rowcount
        
        if affected > 0:
            if actual_date:
                flash(f"✅ บันทึกเช็คเอาท์แล้ว (วัน: {actual_date}, เวลา: {checkout_time_val}) — ห้องว่างแล้ว", "success")
            else:
                flash(f"✅ ยกเลิกเช็คเอาท์ — ห้องว่างจนถึง {booking['check_out']}", "success")
        else:
            flash("⚠️ ไม่พบรายการ หรือไม่มีการเปลี่ยนแปลง", "warning")
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"❌ เกิดข้อผิดพลาด: {str(e)}", "error")
    
    return redirect(url_for("booking_detail", booking_id=booking_id))

@app.route("/admin/booking/<int:booking_id>")
@login_required
@admin_required
def booking_detail(booking_id):
    """ดูรายละเอียดการจอง + ประวัติ"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get booking details
    cursor.execute("""
        SELECT b.*, r.room_name
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.id
        WHERE b.id = %s
    """, (booking_id,))
    booking = cursor.fetchone()
    
    if not booking:
        cursor.close()
        conn.close()
        flash("ไม่พบการจอง", "error")
        return redirect(url_for("admin"))
    
    # Compute derived data
    d1 = datetime.strptime(str(booking['check_in'])[:10], "%Y-%m-%d").date()
    d2_raw = booking.get('actual_checkout_date') or booking['check_out']
    d2 = datetime.strptime(str(d2_raw)[:10], "%Y-%m-%d").date()
    nights = (d2 - d1).days
    
    today = datetime.now().date()
    # for detail page use same rule: if actual checkout date exists, treat it as exclusive
    if booking['payment_status'] == 'paid':
        if booking.get('actual_checkout_date'):
            is_staying = d1 <= today < d2
        else:
            is_staying = d1 <= today <= d2
    else:
        is_staying = False
    
    status_map = {
        'paid': 'ชำระเงินแล้ว',
        'pending_verify': 'รอตรวจสอบสลิป',
        'waiting_cash': 'รอชำระเงินสด',
        'pending': 'รอชำระเงิน'
    }
    
    checkout_time = booking.get('checkout_time') or '12:00'
    
    booking_data = {
        "id": booking['id'],
        "customer": booking['customer_name'],
        "phone": booking['phone'],
        "email": booking.get('email', '-'),
        "room": booking['room_name'],
        "room_id": booking.get('room_id'),
        "checkin": booking['check_in'],
        "checkout": booking['check_out'],
        "actual_checkout": booking.get('actual_checkout_date'),
        "checkout_time": checkout_time,
        "nights": nights,
        "guests": booking.get('guest_count') or 0,
        "rooms": booking.get('room_count') or 1,
        "price": booking['total_price'] or 0,
        "payment_method": booking.get('payment_method') or '-',
        "status": status_map.get(booking['payment_status'], booking['payment_status']),
        "is_staying": is_staying,
        "slip_image": booking.get('slip_image'),
        "created_at": booking.get('created_at'),
        "paid_at": booking.get('paid_at')
    }
    
    cursor.close()
    conn.close()
    
    # Convert dates for display
    booking_data['checkin_display'] = d1.strftime('%d/%m/%Y')
    booking_data['checkout_display'] = d2.strftime('%d/%m/%Y')
    
    return render_template("admin_booking_detail.html", booking=booking_data)

@app.route("/confirm_cash_payment/<int:id>")
@login_required
@admin_required
def confirm_cash_payment(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bookings 
        SET payment_status = 'paid', paid_at = NOW() 
        WHERE id = %s AND payment_method = 'cash'
    """, (id,))
    conn.commit()
    affected = cursor.rowcount
    cursor.close()
    conn.close()
    if affected:
        flash("ยืนยันรับเงินสดแล้ว", "success")
    else:
        flash("ไม่พบรายการหรือไม่ใช่การจองแบบเงินสด", "error")
    return redirect(url_for("admin"))

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(debug=True)
