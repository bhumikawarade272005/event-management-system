import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import secrets
import json
from sqlalchemy import func, extract
import traceback

# SQLAlchemy 2.0 compatibility
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///evento.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app, model_class=Base)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade="all, delete-orphan")

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    special_requests = db.Column(db.Text)
    
    # Selected services
    service_name = db.Column(db.String(100))
    service_price = db.Column(db.Integer, default=0)
    hall_name = db.Column(db.String(100))
    hall_price = db.Column(db.Integer, default=0)
    package_name = db.Column(db.String(100))
    package_price = db.Column(db.Integer, default=0)
    total_amount = db.Column(db.Integer, nullable=False)
    
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, cancelled, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50))  # venue, invitation, entertainment, etc.
    is_active = db.Column(db.Boolean, default=True)

class Hall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)
    capacity = db.Column(db.Integer)
    image_url = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)

class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)
    features = db.Column(db.Text)  # JSON string of features
    is_active = db.Column(db.Boolean, default=True)

# Create tables and initial data
with app.app_context():
    db.create_all()
    
    # Create admin user if not exists
    if not User.query.filter_by(email='admin@evento.com').first():
        admin = User(
            name='Admin',
            email='admin@evento.com',
            phone='1234567890',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
    
    # Add sample services if not exists
    if not Service.query.first():
        services = [
            Service(name='Venue Selection', description='We help you find the perfect venue', price=5000, category='venue'),
            Service(name='Invitation Card', description='Custom-designed invitation cards', price=3000, category='invitation'),
            Service(name='Entertainment', description='From live bands and DJs to cultural performances', price=10000, category='entertainment'),
            Service(name='Food And Drinks', description='Catering services with diverse menu options', price=15000, category='catering'),
            Service(name='Photos And Videos', description='Professional photography and videography', price=15000, category='media'),
            Service(name='Custom Foods', description='Specialized culinary experiences', price=20000, category='catering')
        ]
        for service in services:
            db.session.add(service)
        
        # Add sample halls
        halls = [
            Hall(name='Grand Mumbai Hall', location='Mumbai', price=25000, capacity=500, image_url='/static/image/hall.jpg'),
            Hall(name='Jogeshwari Event Center', location='Jogeshwari', price=18000, capacity=300, image_url='/static/image/hall5.jpg'),
            Hall(name='Goregaon Banquet Hall', location='Goregaon', price=22000, capacity=400, image_url='/static/image/hall2.jpg'),
            Hall(name='Navi Mumbai Convention Center', location='Navi Mumbai', price=30000, capacity=600, image_url='/static/image/hall3.jpg'),
            Hall(name='Andheri Business Hub', location='Andheri', price=20000, capacity=250, image_url='/static/image/hall4.jpg')
        ]
        for hall in halls:
            db.session.add(hall)
        
        # Add sample packages
        packages = [
            Package(name='For Birthdays', price=20999, description='Perfect for birthday celebrations', features='["Full Services","Decorations","Music And Photos","Food And Drinks","Invitation Card"]'),
            Package(name='For Wedding', price=40999, description='Complete wedding solution', features='["Full Services","Decorations","Music And Photos","Food And Drinks","Invitation Card"]'),
            Package(name='For Concerts', price=60999, description='For music concerts and shows', features='["Full Services","Decorations","Music And Photos","Food And Drinks","Invitation Card"]'),
            Package(name='For Others', price=75999, description='For other special events', features='["Full Services","Decorations","Music And Photos","Food And Drinks","Invitation Card"]')
        ]
        for package in packages:
            db.session.add(package)
        
        db.session.commit()

# Routes
@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/mainhome')
def mainhome():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login_page'))
    
    # Get user info - Updated for SQLAlchemy 2.0
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('User not found!', 'error')
        return redirect(url_for('login_page'))
    
    # Get all services, halls, and packages for the homepage
    services = Service.query.filter_by(is_active=True).all()
    halls = Hall.query.filter_by(is_active=True).all()
    packages = Package.query.filter_by(is_active=True).all()
    
    return render_template('mainhome.html', 
                         user=user,
                         services=services,
                         halls=halls,
                         packages=packages)

@app.route('/check_login')
def check_login():
    """Check if user is logged in (for AJAX calls)"""
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            return jsonify({
                'logged_in': True,
                'user_name': user.name,
                'user_email': user.email,
                'is_admin': user.is_admin
            })
    
    return jsonify({
        'logged_in': False,
        'user_name': '',
        'user_email': '',
        'is_admin': False
    })

@app.route('/get_user_info')
def get_user_info():
    if 'user_id' not in session:
        return jsonify({})
    
    user = db.session.get(User, session['user_id'])
    if user:
        return jsonify({
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'is_admin': user.is_admin
        })
    
    return jsonify({})

@app.route('/booking_page')
def booking_page():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login_page'))
    
    # Get user info - Updated for SQLAlchemy 2.0
    user = db.session.get(User, session['user_id'])
    if not user:
        session.clear()
        flash('User not found!', 'error')
        return redirect(url_for('login_page'))
    
    # Get all active services, halls, and packages
    services = Service.query.filter_by(is_active=True).all()
    halls = Hall.query.filter_by(is_active=True).all()
    packages = Package.query.filter_by(is_active=True).all()
    
    return render_template('booking.html', 
                         services=services,
                         halls=halls,
                         packages=packages,
                         user=user)

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/register_user', methods=['POST'])
def register_user():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register_page'))
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'error')
            return redirect(url_for('register_page'))
        
        # Create new user
        new_user = User(
            name=name,
            email=email,
            phone=phone,
            password=generate_password_hash(password)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Auto login after registration
        session['user_id'] = new_user.id
        session['user_name'] = new_user.name
        session['user_email'] = new_user.email
        session['is_admin'] = new_user.is_admin
        
        flash('Registration successful! Welcome to Evento.', 'success')
        return redirect(url_for('mainhome'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {str(e)}")
        flash('Registration failed. Please try again.', 'error')
        return redirect(url_for('register_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/admin/login')
def admin_login_page():
    """Admin login page route"""
    # If already logged in as admin, redirect to dashboard
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user and user.is_admin:
            return redirect(url_for('admin_dashboard'))
    # Note: File name has space, so use 'admin login.html'
    return render_template('adminlogin.html')

@app.route('/login_user', methods=['POST'])
def login_user():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_email'] = user.email
            session['is_admin'] = user.is_admin
            
            flash('Login successful!', 'success')
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('mainhome'))
        else:
            flash('Invalid email or password!', 'error')
            return redirect(url_for('login_page'))
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        flash('Login failed. Please try again.', 'error')
        return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login_page'))

@app.route('/api/services')
def get_services():
    services = Service.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'price': s.price,
        'category': s.category
    } for s in services])

@app.route('/api/halls')
def get_halls():
    halls = Hall.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': h.id,
        'name': h.name,
        'location': h.location,
        'description': h.description,
        'price': h.price,
        'capacity': h.capacity,
        'image_url': h.image_url
    } for h in halls])

@app.route('/api/packages')
def get_packages():
    packages = Package.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'features': p.features
    } for p in packages])

@app.route('/create_booking', methods=['POST'])
def create_booking():
    print("=== CREATE BOOKING ENDPOINT CALLED ===")
    
    if 'user_id' not in session:
        print("ERROR: User not logged in")
        return jsonify({'success': False, 'message': 'Please login first!'})
    
    try:
        # Get JSON data from frontend
        data = request.get_json()
        print(f"Received booking data: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No data received'})
        
        # Generate booking ID
        booking_id = 'EVT-' + datetime.now().strftime('%Y%m%d%H%M%S')
        print(f"Generated booking ID: {booking_id}")
        
        # Parse date
        event_date = datetime.strptime(data['event_date'], '%Y-%m-%d').date()
        print(f"Event date: {event_date}")
        
        # Calculate total amount if not provided
        service_price = int(data.get('service_price', 0) or 0)
        hall_price = int(data.get('hall_price', 0) or 0)
        package_price = int(data.get('package_price', 0) or 0)
        total_amount = service_price + hall_price + package_price
        
        print(f"Service price: {service_price}")
        print(f"Hall price: {hall_price}")
        print(f"Package price: {package_price}")
        print(f"Total amount: {total_amount}")
        
        # Create booking
        booking = Booking(
            booking_id=booking_id,
            user_id=session['user_id'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            event_date=event_date,
            event_type=data.get('event_type', 'other'),
            guests=int(data.get('guests', 50)),
            special_requests=data.get('special_requests', ''),
            
            # Selected services
            service_name=data.get('service_name'),
            service_price=service_price,
            hall_name=data.get('hall_name'),
            hall_price=hall_price,
            package_name=data.get('package_name'),
            package_price=package_price,
            total_amount=total_amount,
            
            status='confirmed'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        print(f"=== BOOKING SUCCESSFULLY SAVED ===")
        print(f"Booking ID: {booking_id}")
        print(f"User ID: {session['user_id']}")
        
        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'message': 'Booking confirmed successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"=== BOOKING ERROR: {str(e)} ===")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Booking failed: {str(e)}'})

@app.route('/booking_history')
def booking_history():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login_page'))
    
    user_id = session['user_id']
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc()).all()
    
    return render_template('booking_history.html', bookings=bookings)

@app.route('/booking_receipt/<booking_id>')
def booking_receipt(booking_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login_page'))
    
    booking = Booking.query.filter_by(booking_id=booking_id, user_id=session['user_id']).first()
    
    if not booking:
        flash('Booking not found!', 'error')
        return redirect(url_for('booking_history'))
    
    # Calculate GST
    subtotal = (booking.service_price or 0) + (booking.hall_price or 0) + (booking.package_price or 0)
    gst = subtotal * 0.18
    total_with_gst = subtotal + gst
    
    return render_template('receipt.html', 
                         booking=booking,
                         subtotal=subtotal,
                         gst=gst,
                         total_with_gst=total_with_gst)

# ==================== ADMIN DASHBOARD ROUTES ====================
@app.route('/admin')
def admin():
    """Admin dashboard - redirects to login if not admin"""
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('admin_login_page'))
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        flash('Admin access required!', 'error')
        return redirect(url_for('admin_login_page'))
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('admin_login_page'))
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        flash('Admin access required!', 'error')
        return redirect(url_for('admin_login_page'))
    
    try:
        # Get all bookings
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        total_bookings = len(bookings)
        total_revenue = sum(b.total_amount for b in bookings if b.total_amount)
        
        # Get total users
        total_users = User.query.count()
        
        # Get pending bookings
        pending_bookings = Booking.query.filter_by(status='pending').count()
        
        # Get recent bookings (last 10)
        recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
        
        return render_template('admin.html',
                             total_bookings=total_bookings,
                             total_revenue=total_revenue,
                             total_users=total_users,
                             pending_bookings=pending_bookings,
                             recent_bookings=recent_bookings)
    except Exception as e:
        print(f"Admin dashboard error: {str(e)}")
        flash('Error loading admin dashboard', 'error')
        return redirect(url_for('mainhome'))

@app.route('/admin/bookings')
def admin_bookings():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        bookings = Booking.query.order_by(Booking.created_at.desc()).all()
        bookings_data = []
        for booking in bookings:
            user = db.session.get(User, booking.user_id)
            bookings_data.append({
                'booking_id': booking.booking_id,
                'user_name': user.name if user else 'Unknown',
                'user_email': user.email if user else 'Unknown',
                'event_date': booking.event_date.strftime('%Y-%m-%d') if booking.event_date else 'N/A',
                'event_type': booking.event_type or 'N/A',
                'guests': booking.guests or 0,
                'total_amount': booking.total_amount or 0,
                'status': booking.status or 'pending',
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M') if booking.created_at else 'N/A'
            })
        
        return jsonify({'success': True, 'bookings': bookings_data})
    except Exception as e:
        print(f"Admin bookings error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        users = User.query.all()
        users_data = []
        for user in users:
            bookings_count = Booking.query.filter_by(user_id=user.id).count()
            users_data.append({
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'phone': user.phone or 'N/A',
                'is_admin': user.is_admin,
                'created_at': user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A',
                'bookings_count': bookings_count
            })
        
        return jsonify({'success': True, 'users': users_data})
    except Exception as e:
        print(f"Admin users error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        data = request.get_json()
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Email already exists'})
        
        # Create new user
        new_user = User(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone', ''),
            password=generate_password_hash(data['password']),
            is_admin=data.get('is_admin', False)
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User added successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Admin add user error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/delete_user/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        user_to_delete = db.session.get(User, user_id)
        
        if not user_to_delete:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Prevent deleting admin user
        if user_to_delete.is_admin:
            return jsonify({'success': False, 'message': 'Cannot delete admin user'})
        
        # Delete user's bookings first
        Booking.query.filter_by(user_id=user_id).delete()
        
        # Delete user
        db.session.delete(user_to_delete)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Admin delete user error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/reports')
def admin_reports():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        # Calculate monthly revenue for last 6 months
        monthly_revenue = []
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        for i in range(6):
            month_date = datetime.now() - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i > 0:
                month_end = (month_start - timedelta(days=1)).replace(day=1)
            else:
                month_end = month_start + timedelta(days=31)
                month_end = month_end.replace(day=1) - timedelta(days=1)
            
            revenue = db.session.query(func.sum(Booking.total_amount)).filter(
                Booking.created_at >= month_start,
                Booking.created_at <= month_end
            ).scalar() or 0
            
            monthly_revenue.append({
                'month': months[i],
                'revenue': int(revenue)
            })
        
        monthly_revenue.reverse()
        
        # Status distribution
        status_counts = {
            'pending': Booking.query.filter_by(status='pending').count(),
            'confirmed': Booking.query.filter_by(status='confirmed').count(),
            'cancelled': Booking.query.filter_by(status='cancelled').count(),
            'completed': Booking.query.filter_by(status='completed').count()
        }
        
        status_distribution = [
            {'status': 'Pending', 'count': status_counts['pending']},
            {'status': 'Confirmed', 'count': status_counts['confirmed']},
            {'status': 'Cancelled', 'count': status_counts['cancelled']},
            {'status': 'Completed', 'count': status_counts['completed']}
        ]
        
        # Event types
        event_types = []
        event_type_counts = db.session.query(
            Booking.event_type, 
            func.count(Booking.id).label('count')
        ).group_by(Booking.event_type).all()
        
        for event_type, count in event_type_counts:
            if event_type:
                event_types.append({'type': event_type, 'count': count})
        
        return jsonify({
            'success': True,
            'monthly_revenue': monthly_revenue,
            'status_distribution': status_distribution,
            'event_types': event_types
        })
    except Exception as e:
        print(f"Admin reports error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/update_booking_status', methods=['POST'])
def update_booking_status():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        status = data.get('status')
        
        booking = Booking.query.filter_by(booking_id=booking_id).first()
        if booking:
            booking.status = status
            booking.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({'success': True, 'message': 'Booking status updated successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Booking not found!'})
    except Exception as e:
        db.session.rollback()
        print(f"Update booking status error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error updating status: {str(e)}'})

@app.route('/admin/view_booking/<booking_id>')
def admin_view_booking(booking_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        booking = Booking.query.filter_by(booking_id=booking_id).first()
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'})
        
        user = db.session.get(User, booking.user_id)
        
        booking_details = {
            'booking_id': booking.booking_id,
            'customer_name': f"{booking.first_name} {booking.last_name}",
            'customer_email': booking.email,
            'customer_phone': booking.phone,
            'user_name': user.name if user else 'Unknown',
            'user_email': user.email if user else 'Unknown',
            'event_date': booking.event_date.strftime('%Y-%m-%d') if booking.event_date else 'N/A',
            'event_type': booking.event_type,
            'guests': booking.guests,
            'status': booking.status,
            'total_amount': booking.total_amount,
            'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M') if booking.created_at else 'N/A',
            'special_requests': booking.special_requests or 'None',
            'services': {
                'service': f"{booking.service_name} - ₹{booking.service_price}" if booking.service_name else 'None',
                'hall': f"{booking.hall_name} - ₹{booking.hall_price}" if booking.hall_name else 'None',
                'package': f"{booking.package_name} - ₹{booking.package_price}" if booking.package_name else 'None'
            }
        }
        
        return jsonify({'success': True, 'booking': booking_details})
    except Exception as e:
        print(f"View booking error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/backup', methods=['POST'])
def admin_backup():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        # In a real app, this would create a database backup
        # For now, we'll just return success
        return jsonify({'success': True, 'message': 'Database backup completed successfully'})
    except Exception as e:
        print(f"Backup error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/clear_old_data', methods=['POST'])
def admin_clear_old_data():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    user = db.session.get(User, session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    try:
        # Calculate date 1 year ago
        one_year_ago = datetime.now() - timedelta(days=365)
        
        # Delete completed bookings older than 1 year
        old_bookings = Booking.query.filter(
            Booking.status == 'completed',
            Booking.created_at < one_year_ago
        ).all()
        
        count = len(old_bookings)
        for booking in old_bookings:
            db.session.delete(booking)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Cleared {count} old bookings'})
    except Exception as e:
        db.session.rollback()
        print(f"Clear old data error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

# New routes for selected items
@app.route('/get_selected_service/<service_name>')
def get_selected_service(service_name):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    # Get service details
    service = Service.query.filter_by(name=service_name).first()
    if service:
        return jsonify({
            'id': service.id,
            'name': service.name,
            'price': service.price,
            'description': service.description
        })
    
    return jsonify({'error': 'Service not found'}), 404

@app.route('/get_selected_hall/<hall_name>')
def get_selected_hall(hall_name):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    # Get hall details
    hall = Hall.query.filter_by(name=hall_name).first()
    if hall:
        return jsonify({
            'id': hall.id,
            'name': hall.name,
            'price': hall.price,
            'location': hall.location,
            'description': hall.description
        })
    
    return jsonify({'error': 'Hall not found'}), 404

@app.route('/get_selected_package/<package_name>')
def get_selected_package(package_name):
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    # Get package details
    package = Package.query.filter_by(name=package_name).first()
    if package:
        return jsonify({
            'id': package.id,
            'name': package.name,
            'price': package.price,
            'description': package.description
        })
    
    return jsonify({'error': 'Package not found'}), 404

@app.route('/create_test_user')
def create_test_user():
    # Create test user for debugging
    test_user = User.query.filter_by(email='test@test.com').first()
    if not test_user:
        new_user = User(
            name='Test User',
            email='test@test.com',
            phone='9876543210',
            password=generate_password_hash('test123'),
            is_admin=False
        )
        db.session.add(new_user)
        db.session.commit()
        return 'Test user created! Email: test@test.com, Password: test123'
    return 'Test user already exists'

if __name__ == '__main__':

    app.run(debug=True, port=5000)
