import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import get_db_connection, ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def add_notification(message, user_id=None, provider_id=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notifications (user_id, provider_id, message) VALUES (%s, %s, %s)",
            (user_id, provider_id, message)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
@app.route('/')
def home():
    return render_template('home.html')


# ---------------------------------------------------------
# USER AUTH
# ---------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (name, email, password, phone) VALUES (%s, %s, %s, %s)",
                (name, email, password, phone)
            )
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception:
            conn.rollback()
            flash('Email already registered.', 'error')
        finally:
            cur.close()
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT b.id, s.name AS service_name, s.price, b.status,
               b.booking_date, b.payment_method, b.is_confirmed,
               p.name AS provider_name, p.phone AS provider_phone,
               p.location AS provider_location,
               (SELECT COUNT(*) FROM ratings r WHERE r.booking_id = b.id) AS rated
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        LEFT JOIN service_providers p ON b.provider_id = p.id
        WHERE b.user_id = %s
        ORDER BY b.booking_date DESC
    """, (session['user_id'],))
    bookings = cur.fetchall()

    # Unread notifications
    cur.execute("""
        SELECT * FROM notifications WHERE user_id = %s AND is_read = 0
        ORDER BY created_at DESC
    """, (session['user_id'],))
    notifications = cur.fetchall()

    # Mark notifications as read
    cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session['user_id'],))
    conn.commit()

    cur.close()
    conn.close()
    return render_template('user_dashboard.html', bookings=bookings, notifications=notifications)


# ---------------------------------------------------------
# PROVIDER AUTH
# ---------------------------------------------------------
@app.route('/provider/register', methods=['GET', 'POST'])
def provider_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        service_type = request.form['service_type']
        phone = request.form.get('phone', '')
        location = request.form.get('location', '')
        aadhar = request.form.get('aadhar_number', '')
        password = generate_password_hash(request.form['password'])

        photo_filename = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                photo_filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO service_providers (name, email, password, service_type, phone, location, aadhar_number, photo) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (name, email, password, service_type, phone, location, aadhar, photo_filename)
            )
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('provider_login'))
        except Exception:
            conn.rollback()
            flash('Email already registered.', 'error')
        finally:
            cur.close()
            conn.close()
    return render_template('provider_register.html')


@app.route('/provider/login', methods=['GET', 'POST'])
def provider_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM service_providers WHERE email = %s", (email,))
        provider = cur.fetchone()
        cur.close()
        conn.close()
        if provider and check_password_hash(provider['password'], password):
            session['provider_id'] = provider['id']
            session['provider_name'] = provider['name']
            return redirect(url_for('provider_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('provider_login.html')


@app.route('/provider/logout')
def provider_logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/provider/dashboard')
def provider_dashboard():
    if 'provider_id' not in session:
        return redirect(url_for('provider_login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT b.id, s.name AS service_name, u.name AS user_name,
               u.phone, b.status, b.booking_date, b.payment_method, b.is_confirmed
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        JOIN users u ON b.user_id = u.id
        WHERE b.provider_id = %s
        ORDER BY b.booking_date DESC
    """, (session['provider_id'],))
    my_bookings = cur.fetchall()

    cur.execute("""
        SELECT b.id, s.name AS service_name, u.name AS user_name, b.booking_date
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        JOIN users u ON b.user_id = u.id
        WHERE b.provider_id IS NULL AND b.status = 'pending'
        ORDER BY b.booking_date DESC
    """)
    available_bookings = cur.fetchall()

    # Provider avg rating
    cur.execute("""
        SELECT ROUND(AVG(stars), 1) AS avg_rating, COUNT(*) AS total_ratings
        FROM ratings WHERE provider_id = %s
    """, (session['provider_id'],))
    rating_info = cur.fetchone()

    # Unread notifications
    cur.execute("""
        SELECT * FROM notifications WHERE provider_id = %s AND is_read = 0
        ORDER BY created_at DESC
    """, (session['provider_id'],))
    notifications = cur.fetchall()
    cur.execute("UPDATE notifications SET is_read=1 WHERE provider_id=%s", (session['provider_id'],))
    conn.commit()

    cur.close()
    conn.close()
    return render_template('provider_dashboard.html',
                           my_bookings=my_bookings,
                           available_bookings=available_bookings,
                           rating_info=rating_info,
                           notifications=notifications)


@app.route('/provider/accept/<int:booking_id>')
def provider_accept_booking(booking_id):
    if 'provider_id' not in session:
        return redirect(url_for('provider_login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT b.*, u.id AS uid, s.name AS sname FROM bookings b JOIN users u ON b.user_id=u.id JOIN services s ON b.service_id=s.id WHERE b.id=%s", (booking_id,))
    booking = cur.fetchone()
    cur.execute(
        "UPDATE bookings SET provider_id=%s, status='accepted' WHERE id=%s AND provider_id IS NULL",
        (session['provider_id'], booking_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    if booking:
        add_notification(
            f"Your booking for '{booking['sname']}' has been accepted by a provider!",
            user_id=booking['uid']
        )
    flash('Booking accepted!', 'success')
    return redirect(url_for('provider_dashboard'))


@app.route('/provider/complete/<int:booking_id>')
def provider_complete_booking(booking_id):
    if 'provider_id' not in session:
        return redirect(url_for('provider_login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT b.*, u.id AS uid, s.name AS sname FROM bookings b JOIN users u ON b.user_id=u.id JOIN services s ON b.service_id=s.id WHERE b.id=%s", (booking_id,))
    booking = cur.fetchone()
    cur.execute(
        "UPDATE bookings SET status='completed' WHERE id=%s AND provider_id=%s",
        (booking_id, session['provider_id'])
    )
    conn.commit()
    cur.close()
    conn.close()
    if booking:
        add_notification(
            f"Your booking for '{booking['sname']}' is completed! Please rate your experience.",
            user_id=booking['uid']
        )
    flash('Booking marked as completed!', 'success')
    return redirect(url_for('provider_dashboard'))


# ---------------------------------------------------------
# SERVICES + BOOKING
# ---------------------------------------------------------
@app.route('/services')
def services():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM services ORDER BY department")
    all_services = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('services.html', services=all_services)


@app.route('/book/<int:service_id>', methods=['GET', 'POST'])
def book_service(service_id):
    if 'user_id' not in session:
        flash('Please log in to book a service.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM services WHERE id=%s", (service_id,))
    service = cur.fetchone()

    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'cash')
        cur.execute(
            "INSERT INTO bookings (user_id, service_id, status, payment_method) VALUES (%s, %s, 'pending', %s)",
            (session['user_id'], service_id, payment_method)
        )
        conn.commit()
        booking_id = cur.lastrowid
        cur.close()
        conn.close()
        return redirect(url_for('booking_confirmation', booking_id=booking_id))

    cur.close()
    conn.close()
    return render_template('book_service.html', service=service)


@app.route('/booking/confirmation/<int:booking_id>')
def booking_confirmation(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT b.*, s.name AS service_name, s.price, s.equipment
        FROM bookings b JOIN services s ON b.service_id=s.id
        WHERE b.id=%s AND b.user_id=%s
    """, (booking_id, session['user_id']))
    booking = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('booking_confirmation.html', booking=booking)


# ---------------------------------------------------------
# RATINGS
# ---------------------------------------------------------
@app.route('/rate/<int:booking_id>', methods=['GET', 'POST'])
def rate_booking(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT b.*, s.name AS service_name, p.name AS provider_name
        FROM bookings b JOIN services s ON b.service_id=s.id
        LEFT JOIN service_providers p ON b.provider_id=p.id
        WHERE b.id=%s AND b.user_id=%s AND b.status='completed'
    """, (booking_id, session['user_id']))
    booking = cur.fetchone()

    if not booking:
        flash('Booking not found or not completed.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        stars = int(request.form['stars'])
        review = request.form.get('review', '')
        try:
            cur.execute(
                "INSERT INTO ratings (booking_id, user_id, provider_id, stars, review) VALUES (%s,%s,%s,%s,%s)",
                (booking_id, session['user_id'], booking['provider_id'], stars, review)
            )
            conn.commit()
            add_notification(
                f"You received a {stars}⭐ rating!",
                provider_id=booking['provider_id']
            )
            flash('Thank you for your rating!', 'success')
            return redirect(url_for('dashboard'))
        except Exception:
            flash('Already rated this booking.', 'error')
        finally:
            cur.close()
            conn.close()

    cur.close()
    conn.close()
    return render_template('rate_booking.html', booking=booking)


# ---------------------------------------------------------
# ADMIN
# ---------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['email'] == ADMIN_EMAIL and request.form['password'] == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'error')
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('home'))


def admin_required():
    return session.get('is_admin', False)


@app.route('/admin/dashboard')
def admin_dashboard():
    if not admin_required():
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS count FROM users")
    user_count = cur.fetchone()['count']
    cur.execute("SELECT COUNT(*) AS count FROM service_providers")
    provider_count = cur.fetchone()['count']
    cur.execute("SELECT COUNT(*) AS count FROM bookings")
    booking_count = cur.fetchone()['count']
    cur.execute("SELECT COUNT(*) AS count FROM bookings WHERE status='pending'")
    pending_count = cur.fetchone()['count']
    cur.close()
    conn.close()
    return render_template('admin_dashboard.html',
                           user_count=user_count,
                           provider_count=provider_count,
                           booking_count=booking_count,
                           pending_count=pending_count)


@app.route('/admin/users')
def admin_users():
    if not admin_required():
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, name, email, phone, created_at FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_users.html', users=users)


@app.route('/admin/providers')
def admin_providers():
    if not admin_required():
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.*, ROUND(AVG(r.stars),1) AS avg_rating
        FROM service_providers p
        LEFT JOIN ratings r ON r.provider_id=p.id
        GROUP BY p.id
    """)
    providers = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_providers.html', providers=providers)


@app.route('/admin/bookings')
def admin_bookings():
    if not admin_required():
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT b.id, u.name AS user_name, s.name AS service_name,
               p.name AS provider_name, b.status, b.booking_date,
               b.payment_method, b.is_confirmed
        FROM bookings b
        JOIN users u ON b.user_id=u.id
        JOIN services s ON b.service_id=s.id
        LEFT JOIN service_providers p ON b.provider_id=p.id
        ORDER BY b.booking_date DESC
    """)
    bookings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin_bookings.html', bookings=bookings)


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', '0') == '1')
