from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Email configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USERNAME = 'aventroedutechsolutions@gmail.com'
MAIL_PASSWORD = 'bwpi kgzp ukqg prny'
MAIL_DEFAULT_SENDER = 'aventroedutechsolutions@gmail.com'

# WhatsApp group link (shown after OTP verification; admin can override in portal)
WHATSAPP_GROUP_LINK = 'https://chat.whatsapp.com/'

# MongoDB configuration
MONGO_URI = 'mongodb+srv://umiraoutlook_db_user:umira123@cluster0.x4b4h0j.mongodb.net/?appName=Cluster0'
client = MongoClient(MONGO_URI)
db = client.get_database('aventro')

# Cloudinary configuration
cloudinary.config(
    cloud_name="w91wfelr",
    api_key="766564212762779",
    api_secret="rPH5pl2eubva0Qvr5oXkTZfbDGo"
)

# Upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# MongoDB Collections
users_collection = db.users
courses_collection = db.courses
blogs_collection = db.blogs
gallery_collection = db.gallery
orders_collection = db.orders
settings_collection = db.settings
otps_collection = db.otps

CURRENCY_SYMBOLS = {'INR': '₹', 'USD': '$', 'EUR': '€'}
OTP_EXPIRY_MINUTES = 10


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please register or login to access courses.', 'error')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def get_setting(key, default=''):
    doc = settings_collection.find_one({'key': key})
    return doc['value'] if doc else default


def set_setting(key, value):
    settings_collection.update_one(
        {'key': key},
        {'$set': {'key': key, 'value': value, 'updated_at': datetime.utcnow()}},
        upsert=True
    )


def send_email(to_email, subject, html_body, reply_to=None):
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print(f'Email not configured. Would send to {to_email}: {subject}')
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = MAIL_DEFAULT_SENDER
        msg['To'] = to_email
        if reply_to:
            msg['Reply-To'] = reply_to
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD.replace(' ', ''))
            server.sendmail(MAIL_DEFAULT_SENDER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'Email send failed: {e}')
        return False


def send_thank_you_email(email, username):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px;">
        <h2 style="color: #003366;">Welcome to Aventro Edu Tech!</h2>
        <p>Hi <strong>{username}</strong>,</p>
        <p>Thank you for joining Aventro Edu Tech. We're excited to have you on board!</p>
        <p>Explore our courses, enroll in programs that match your goals, and start your learning journey with us.</p>
        <p style="margin-top: 24px; color: #666;">Best regards,<br><strong>Aventro Edu Tech Team</strong></p>
    </div>
    """
    return send_email(email, 'Thank You for Joining Aventro Edu Tech!', html)


def send_otp_email(email, username, otp_code, course_title):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px;">
        <h2 style="color: #003366;">Payment Verification OTP</h2>
        <p>Hi <strong>{username}</strong>,</p>
        <p>Your OTP for enrolling in <strong>{course_title}</strong> is:</p>
        <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #004a99; text-align: center; padding: 20px; background: #e8f0fe; border-radius: 8px;">{otp_code}</p>
        <p>This OTP is valid for {OTP_EXPIRY_MINUTES} minutes. Do not share it with anyone.</p>
        <p style="color: #666; font-size: 14px;">If you did not request this, please ignore this email.</p>
    </div>
    """
    return send_email(email, f'Your OTP for {course_title} - Aventro Edu Tech', html)


def send_invoice_email(to_email, username, course_title, amount, currency, order_id):
    currency_symbols = {'INR': 'Rs. ', 'USD': '$', 'EUR': '€'}
    sym = currency_symbols.get(currency, currency + ' ')
    price_formatted = f"{sym}{amount:,.2f}"
    date_str = datetime.utcnow().strftime('%B %d, %Y')
    
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 440px; margin: 0 auto; padding: 20px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; color: #0f172a; font-size: 14px; line-height: 1.5;">
        <div style="text-align: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #e2e8f0;">
            <h2 style="color: #003366; font-size: 18px; font-weight: 700; margin: 0;">Aventro Edu Tech</h2>
            <p style="font-size: 12px; color: #64748b; margin: 4px 0 0 0;">Course Purchase Receipt</p>
        </div>
        
        <p style="margin: 0 0 12px 0;">Hi <strong>{username}</strong>,</p>
        <p style="color: #475569; margin: 0 0 20px 0;">Your payment is verified! Here are your purchase details:</p>
        
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <tr>
                    <td style="color: #64748b; padding: 4px 0;">Order ID:</td>
                    <td style="text-align: right; font-weight: 600; color: #0f172a; padding: 4px 0; font-family: monospace;">{order_id}</td>
                </tr>
                <tr>
                    <td style="color: #64748b; padding: 4px 0;">Date:</td>
                    <td style="text-align: right; color: #0f172a; padding: 4px 0;">{date_str}</td>
                </tr>
                <tr>
                    <td style="color: #64748b; padding: 4px 0;">Course:</td>
                    <td style="text-align: right; font-weight: 600; color: #003366; padding: 4px 0;">{course_title}</td>
                </tr>
                <tr style="border-top: 1px dashed #cbd5e1; margin-top: 8px;">
                    <td style="color: #0f172a; font-weight: 700; padding: 10px 0 0 0; font-size: 14px;">Total Paid:</td>
                    <td style="text-align: right; font-weight: 700; color: #10b981; padding: 10px 0 0 0; font-size: 16px;">{price_formatted}</td>
                </tr>
            </table>
        </div>
        
        <p style="color: #475569; font-size: 13px; margin: 0 0 20px 0;">Please join the official WhatsApp group via the link in your student portal dashboard to access your live classes.</p>
        
        <div style="text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px; font-size: 11px; color: #94a3b8;">
            <p style="margin: 0;">Automated email. For support, contact <a href="mailto:aventroedutechsolutions@gmail.com" style="color: #004a99; text-decoration: none;">aventroedutechsolutions@gmail.com</a>.</p>
        </div>
    </div>
    """
    return send_email(to_email, f'Official Purchase Invoice - {course_title} - Aventro', html)


def generate_otp():
    return str(random.randint(100000, 999999))


def format_course_price(course):
    amount = course.get('amount')
    currency = course.get('currency', 'INR')
    if amount is not None:
        symbol = CURRENCY_SYMBOLS.get(currency, currency + ' ')
        return f"{symbol}{amount:,.0f}"
    return course.get('price', 'Contact for price')


def parse_course_form(form):
    amount_raw = form.get('amount', '').strip()
    try:
        amount = float(amount_raw) if amount_raw else None
    except ValueError:
        amount = None

    currency = form.get('currency', 'INR')
    short_description = form.get('short_description', '').strip()
    full_description = form.get('full_description', '').strip()
    description = form.get('description', '').strip()

    if not short_description:
        short_description = description[:200] + ('...' if len(description) > 200 else '')
    if not full_description:
        full_description = description

    price_display = form.get('price', '').strip()
    if not price_display and amount is not None:
        symbol = CURRENCY_SYMBOLS.get(currency, currency + ' ')
        price_display = f"{symbol}{amount:,.0f}"

    return {
        'title': form.get('title'),
        'description': description or short_description,
        'short_description': short_description,
        'full_description': full_description,
        'amount': amount,
        'currency': currency,
        'price': price_display,
        'duration': form.get('duration'),
        'level': form.get('level'),
        'category': form.get('category'),
        'highlights': form.get('highlights'),
        'instructor': form.get('instructor', '').strip(),
        'what_you_learn': form.get('what_you_learn', '').strip(),
        'requirements': form.get('requirements', '').strip(),
        'is_active': form.get('is_active') == 'on',
    }


def upload_gallery_image(file):
    if file and file.filename and allowed_file(file.filename):
        upload_result = cloudinary.uploader.upload(
            file,
            folder="aventro_gallery",
            allowed_formats=['png', 'jpg', 'jpeg', 'gif', 'webp'],
            max_file_size=16000000
        )
        return upload_result['secure_url']
    return None


def upload_course_image(file):
    if file and file.filename and allowed_file(file.filename):
        upload_result = cloudinary.uploader.upload(
            file,
            folder="aventro_courses",
            allowed_formats=['png', 'jpg', 'jpeg', 'gif', 'webp'],
            max_file_size=16000000
        )
        return upload_result['secure_url']
    return None


def upload_payment_screenshot(file):
    if file and file.filename and allowed_file(file.filename):
        upload_result = cloudinary.uploader.upload(
            file,
            folder="aventro_payments",
            allowed_formats=['png', 'jpg', 'jpeg', 'gif', 'webp'],
            max_file_size=16000000
        )
        return upload_result['secure_url']
    return None


def delete_cloudinary_image(image_url, folder):
    if image_url:
        try:
            public_id = image_url.split('/')[-1].split('.')[0]
            cloudinary.uploader.destroy(f"{folder}/{public_id}")
        except Exception:
            pass


@app.route('/')
def index():
    courses = list(courses_collection.find({'is_active': {'$ne': False}}).sort('created_at', -1))
    blogs = list(blogs_collection.find().sort('created_at', -1))
    gallery_preview = list(gallery_collection.find({'is_active': {'$ne': False}}).sort('created_at', -1).limit(6))
    return render_template(
        'index.html',
        courses=courses,
        blogs=blogs,
        gallery_preview=gallery_preview,
        format_price=format_course_price
    )


@app.route('/gallery')
def gallery():
    items = list(gallery_collection.find({'is_active': {'$ne': False}}).sort('created_at', -1))
    return render_template('gallery.html', items=items)


@app.route('/blog/<blog_id>')
def blog_detail(blog_id):
    blog = blogs_collection.find_one({'_id': ObjectId(blog_id)})
    if not blog:
        flash('Blog not found.', 'error')
        return redirect(url_for('index'))
    return render_template('blog_detail.html', blog=blog)


@app.route('/course/<course_id>')
@login_required
def course_detail(course_id):
    course = courses_collection.find_one({'_id': ObjectId(course_id)})
    if not course or course.get('is_active') is False:
        flash('Course not found.', 'error')
        return redirect(url_for('index'))
    return render_template('course_detail.html', course=course, format_price=format_course_price)


@app.route('/course/<course_id>/purchase')
@login_required
def purchase_course(course_id):
    course = courses_collection.find_one({'_id': ObjectId(course_id)})
    if not course or course.get('is_active') is False:
        flash('Course not found.', 'error')
        return redirect(url_for('index'))

    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    whatsapp_link = get_setting('whatsapp_group_link', WHATSAPP_GROUP_LINK)

    return render_template(
        'payment.html',
        course=course,
        user=user,
        format_price=format_course_price,
        whatsapp_link=whatsapp_link
    )


@app.route('/course/<course_id>/purchase/upload', methods=['POST'])
@login_required
def upload_payment(course_id):
    course = courses_collection.find_one({'_id': ObjectId(course_id)})
    if not course or course.get('is_active') is False:
        return jsonify({'success': False, 'message': 'Course not found.'}), 404

    user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        return jsonify({'success': False, 'message': 'User not found.'}), 401

    screenshot = request.files.get('screenshot')
    if not screenshot or not screenshot.filename:
        return jsonify({'success': False, 'message': 'Please upload a payment screenshot.'}), 400

    try:
        screenshot_url = upload_payment_screenshot(screenshot)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

    if not screenshot_url:
        return jsonify({'success': False, 'message': 'Invalid file format. Use PNG, JPG, or JPEG.'}), 400

    amount = course.get('amount', 0) or 0
    order = {
        'course_id': str(course['_id']),
        'course_title': course['title'],
        'user_id': str(user['_id']),
        'customer_name': user.get('username', ''),
        'customer_email': user.get('email', ''),
        'customer_phone': request.form.get('phone', '').strip(),
        'amount': amount,
        'currency': course.get('currency', 'INR'),
        'payment_method': 'upi',
        'payment_screenshot': screenshot_url,
        'status': 'pending_verification',
        'created_at': datetime.utcnow()
    }
    result = orders_collection.insert_one(order)
    order_id = str(result.inserted_id)

    otp_code = generate_otp()
    otps_collection.insert_one({
        'order_id': order_id,
        'email': user['email'],
        'otp': otp_code,
        'expires_at': datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        'verified': False,
        'created_at': datetime.utcnow()
    })

    email_sent = send_otp_email(user['email'], user['username'], otp_code, course['title'])
    if not email_sent:
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Screenshot uploaded. OTP could not be sent — please contact support.',
            'otp_sent': False
        })

    return jsonify({
        'success': True,
        'order_id': order_id,
        'message': f'OTP sent to {user["email"]}. Check your inbox.',
        'otp_sent': True
    })


@app.route('/course/<course_id>/purchase/verify', methods=['POST'])
@login_required
def verify_payment_otp(course_id):
    data = request.get_json(silent=True) or {}
    order_id = data.get('order_id', '').strip()
    otp_input = data.get('otp', '').strip()

    if not order_id or not otp_input:
        return jsonify({'success': False, 'message': 'Order ID and OTP are required.'}), 400

    order = orders_collection.find_one({'_id': ObjectId(order_id)})
    if not order or order.get('course_id') != course_id:
        return jsonify({'success': False, 'message': 'Invalid order.'}), 404

    if order.get('user_id') != session.get('user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized.'}), 403

    otp_record = otps_collection.find_one({
        'order_id': order_id,
        'verified': False
    }, sort=[('created_at', -1)])

    if not otp_record:
        return jsonify({'success': False, 'message': 'No pending OTP found. Please upload screenshot again.'}), 400

    if datetime.utcnow() > otp_record['expires_at']:
        return jsonify({'success': False, 'message': 'OTP has expired. Please upload screenshot again to get a new OTP.'}), 400

    if otp_record['otp'] != otp_input:
        return jsonify({'success': False, 'message': 'Incorrect OTP. Please try again.'}), 400

    otps_collection.update_one({'_id': otp_record['_id']}, {'$set': {'verified': True}})
    orders_collection.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': 'confirmed', 'verified_at': datetime.utcnow()}}
    )

    try:
        send_invoice_email(
            to_email=order.get('customer_email', ''),
            username=order.get('customer_name', ''),
            course_title=order.get('course_title', ''),
            amount=order.get('amount', 0),
            currency=order.get('currency', 'INR'),
            order_id=order_id
        )
    except Exception as e:
        print(f"Failed to send invoice email: {e}")

    whatsapp_link = get_setting('whatsapp_group_link', WHATSAPP_GROUP_LINK)

    return jsonify({
        'success': True,
        'message': 'Payment verified successfully!',
        'whatsapp_link': whatsapp_link
    })


@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next') or request.form.get('next', '')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = users_collection.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['is_admin'] = user.get('is_admin', False)
            session['username'] = user['username']

            if not user.get('is_admin', False):
                send_thank_you_email(user['email'], user['username'])

            if user.get('is_admin', False):
                return redirect(url_for('admin_dashboard'))

            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html', next=next_page)


@app.route('/register', methods=['GET', 'POST'])
def register():
    next_page = request.args.get('next', '')

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        next_page = request.form.get('next', next_page)

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register', next=next_page))

        if users_collection.find_one({'username': username}):
            flash('Username already exists', 'error')
            return redirect(url_for('register', next=next_page))

        if users_collection.find_one({'email': email}):
            flash('Email already exists', 'error')
            return redirect(url_for('register', next=next_page))

        hashed_password = generate_password_hash(password)
        new_user = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'is_admin': False,
            'created_at': datetime.utcnow()
        }

        users_collection.insert_one(new_user)

        flash('Registration successful! Please login.', 'success')
        login_url = url_for('login')
        if next_page:
            login_url += f'?next={next_page}'
        return redirect(login_url)

    return render_template('register.html', next=next_page)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# Admin Routes
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    courses = list(courses_collection.find().sort('created_at', -1))
    blogs = list(blogs_collection.find().sort('created_at', -1))
    gallery_items = list(gallery_collection.find().sort('created_at', -1))
    orders = list(orders_collection.find().sort('created_at', -1).limit(50))
    whatsapp_link = get_setting('whatsapp_group_link', WHATSAPP_GROUP_LINK)

    return render_template(
        'admin.html',
        courses=courses,
        blogs=blogs,
        gallery_items=gallery_items,
        orders=orders,
        format_price=format_course_price,
        whatsapp_link=whatsapp_link
    )


@app.route('/admin/settings/whatsapp', methods=['POST'])
def update_whatsapp_link():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    link = request.form.get('whatsapp_group_link', '').strip()
    set_setting('whatsapp_group_link', link)
    flash('WhatsApp group link updated.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add-course', methods=['GET', 'POST'])
def add_course():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        course_data = parse_course_form(request.form)

        try:
            image_url = upload_course_image(request.files.get('image'))
        except Exception as e:
            flash(f'Error uploading image: {str(e)}', 'error')
            image_url = None

        new_course = {
            **course_data,
            'image': image_url,
            'created_at': datetime.utcnow()
        }

        courses_collection.insert_one(new_course)

        flash('Course added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_course.html')


@app.route('/admin/edit-course/<course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    course = courses_collection.find_one({'_id': ObjectId(course_id)})

    if request.method == 'POST':
        update_data = parse_course_form(request.form)

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                try:
                    delete_cloudinary_image(course.get('image'), 'aventro_courses')
                    image_url = upload_course_image(file)
                    if image_url:
                        update_data['image'] = image_url
                except Exception as e:
                    flash(f'Error uploading image: {str(e)}', 'error')

        courses_collection.update_one({'_id': ObjectId(course_id)}, {'$set': update_data})

        flash('Course updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_course.html', course=course)


@app.route('/admin/delete-course/<course_id>')
def delete_course(course_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    course = courses_collection.find_one({'_id': ObjectId(course_id)})

    delete_cloudinary_image(course.get('image'), 'aventro_courses')

    courses_collection.delete_one({'_id': ObjectId(course_id)})

    flash('Course deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add-blog', methods=['GET', 'POST'])
def add_blog():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        date = request.form.get('date')
        time = request.form.get('time')
        mode = request.form.get('mode')

        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                try:
                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="aventro_blogs",
                        allowed_formats=['png', 'jpg', 'jpeg', 'gif', 'webp'],
                        max_file_size=16000000
                    )
                    image_url = upload_result['secure_url']
                except Exception as e:
                    flash(f'Error uploading image: {str(e)}', 'error')

        new_blog = {
            'title': title,
            'content': content,
            'category': category,
            'date': date,
            'time': time,
            'mode': mode,
            'image': image_url,
            'created_at': datetime.utcnow()
        }

        blogs_collection.insert_one(new_blog)

        flash('Blog added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_blog.html')


@app.route('/admin/edit-blog/<blog_id>', methods=['GET', 'POST'])
def edit_blog(blog_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    blog = blogs_collection.find_one({'_id': ObjectId(blog_id)})

    if request.method == 'POST':
        update_data = {
            'title': request.form.get('title'),
            'content': request.form.get('content'),
            'category': request.form.get('category'),
            'date': request.form.get('date'),
            'time': request.form.get('time'),
            'mode': request.form.get('mode')
        }

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                try:
                    if blog.get('image'):
                        try:
                            public_id = blog['image'].split('/')[-1].split('.')[0]
                            cloudinary.uploader.destroy(f"aventro_blogs/{public_id}")
                        except Exception:
                            pass

                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="aventro_blogs",
                        allowed_formats=['png', 'jpg', 'jpeg', 'gif', 'webp'],
                        max_file_size=16000000
                    )
                    update_data['image'] = upload_result['secure_url']
                except Exception as e:
                    flash(f'Error uploading image: {str(e)}', 'error')

        blogs_collection.update_one({'_id': ObjectId(blog_id)}, {'$set': update_data})

        flash('Blog updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_blog.html', blog=blog)


@app.route('/admin/order/<order_id>/status/<status>')
def update_order_status(order_id, status):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    if status not in ('pending', 'pending_verification', 'confirmed', 'cancelled'):
        flash('Invalid order status.', 'error')
        return redirect(url_for('admin_dashboard'))

    orders_collection.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
    )
    flash(f'Order marked as {status}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add-gallery', methods=['GET', 'POST'])
def add_gallery():
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        caption = request.form.get('caption', '').strip()

        try:
            image_url = upload_gallery_image(request.files.get('image'))
        except Exception as e:
            flash(f'Error uploading image: {str(e)}', 'error')
            return redirect(url_for('add_gallery'))

        if not image_url:
            flash('Please upload a valid image.', 'error')
            return redirect(url_for('add_gallery'))

        gallery_collection.insert_one({
            'title': title or 'Gallery Image',
            'caption': caption,
            'image': image_url,
            'is_active': True,
            'created_at': datetime.utcnow()
        })

        flash('Gallery image added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_gallery.html')


@app.route('/admin/edit-gallery/<item_id>', methods=['GET', 'POST'])
def edit_gallery(item_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    item = gallery_collection.find_one({'_id': ObjectId(item_id)})
    if not item:
        flash('Gallery item not found.', 'error')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        update_data = {
            'title': request.form.get('title', '').strip() or 'Gallery Image',
            'caption': request.form.get('caption', '').strip(),
            'is_active': request.form.get('is_active') == 'on',
        }

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                try:
                    delete_cloudinary_image(item.get('image'), 'aventro_gallery')
                    image_url = upload_gallery_image(file)
                    if image_url:
                        update_data['image'] = image_url
                except Exception as e:
                    flash(f'Error uploading image: {str(e)}', 'error')

        gallery_collection.update_one({'_id': ObjectId(item_id)}, {'$set': update_data})
        flash('Gallery item updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_gallery.html', item=item)


@app.route('/admin/delete-gallery/<item_id>')
def delete_gallery(item_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    item = gallery_collection.find_one({'_id': ObjectId(item_id)})
    if item:
        delete_cloudinary_image(item.get('image'), 'aventro_gallery')
        gallery_collection.delete_one({'_id': ObjectId(item_id)})

    flash('Gallery item deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete-blog/<blog_id>')
def delete_blog(blog_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    blog = blogs_collection.find_one({'_id': ObjectId(blog_id)})

    if blog and blog.get('image'):
        try:
            public_id = blog['image'].split('/')[-1].split('.')[0]
            cloudinary.uploader.destroy(f"aventro_blogs/{public_id}")
        except Exception:
            pass

    blogs_collection.delete_one({'_id': ObjectId(blog_id)})

    flash('Blog deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/contact', methods=['POST'])
def contact():
    from_name = request.form.get('from_name', '').strip()
    reply_to = request.form.get('reply_to', '').strip()
    phone = request.form.get('phone', '').strip()
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()

    if not from_name or not reply_to or not subject or not message:
        flash('All required fields (Name, Email, Subject, Message) must be filled.', 'error')
        return redirect(url_for('index', _anchor='contact'))

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fafbfc;">
        <h2 style="color: #003366; margin-top: 0;">New Contact Message Received!</h2>
        <p style="font-size: 15px; color: #334155; margin-bottom: 24px;">Someone has submitted a message via the Aventro Edu Tech contact form.</p>
        
        <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 24px;">
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 0; font-weight: bold; color: #64748b; width: 120px;">Name:</td>
                <td style="padding: 10px 0; color: #0f172a;">{from_name}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 0; font-weight: bold; color: #64748b;">Email:</td>
                <td style="padding: 10px 0; color: #0f172a;"><a href="mailto:{reply_to}">{reply_to}</a></td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 0; font-weight: bold; color: #64748b;">Phone:</td>
                <td style="padding: 10px 0; color: #0f172a;">{phone or 'Not provided'}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 10px 0; font-weight: bold; color: #64748b;">Subject:</td>
                <td style="padding: 10px 0; color: #0f172a; font-weight: 600;">{subject}</td>
            </tr>
        </table>
        
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; font-size: 14px; color: #334155; line-height: 1.6; white-space: pre-wrap;">
            {message}
        </div>
        
        <p style="font-size: 12px; color: #94a3b8; margin-top: 32px; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px;">Sent from the Aventro Educational Tech Solutions website.</p>
    </div>
    """
    
    email_sent = send_email(MAIL_USERNAME, f"Contact Inquiry: {subject}", html, reply_to=reply_to)
    if email_sent:
        flash('Message sent successfully. We will reply soon.', 'success')
    else:
        flash('Could not send message. Please contact us directly.', 'error')

    return redirect(url_for('index', _anchor='contact'))


def create_admin():
    if not users_collection.find_one({'username': 'admin'}):
        admin = {
            'username': 'admin',
            'email': 'aventroedutechsolutions@gmail.com',
            'password': generate_password_hash('admin123'),
            'is_admin': True,
            'created_at': datetime.utcnow()
        }
        users_collection.insert_one(admin)
        print("Admin user created successfully!")


if __name__ == '__main__':
    create_admin()
    app.run(host='192.168.29.121', port=5000, debug=True)
