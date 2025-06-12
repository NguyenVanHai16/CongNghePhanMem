from datetime import datetime, time
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # customer, shop_owner, admin
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    bookings = db.relationship('Booking', backref='customer', lazy=True, foreign_keys='Booking.customer_id')
    owned_shops = db.relationship('Shop', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    opening_time = db.Column(db.Time, nullable=False, default=time(8, 0))
    closing_time = db.Column(db.Time, nullable=False, default=time(20, 0))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    distance_from_university = db.Column(db.Float)  # in kilometers
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    average_rating = db.Column(db.Float, default=0.0)

    # Relationships
    services = db.relationship('Service', backref='shop', lazy=True, cascade='all, delete-orphan')
    barbers = db.relationship('Barber', backref='shop', lazy=True, cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='shop', lazy=True)
    promotions = db.relationship('Promotion', backref='shop', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='shop_ref', lazy=True)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Integer, nullable=False)  # Price in VND
    duration = db.Column(db.Integer, nullable=False)  # Duration in minutes
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)

class Barber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    bookings = db.relationship('Booking', backref='barber', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    barber_id = db.Column(db.Integer, db.ForeignKey('barber.id'))
    booking_date = db.Column(db.Date, nullable=False)
    booking_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    service = db.relationship('Service', backref='bookings')

class Promotion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    discount_percent = db.Column(db.Integer, nullable=False)  # Discount percentage
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Shop is defined in the Shop model

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=True)
    shop_response = db.Column(db.Text, nullable=True)
    
    # Relationships - sửa lại để tránh xung đột backref
    shop = db.relationship('Shop')
    customer = db.relationship('User', backref=db.backref('reviews', lazy=True))
    booking = db.relationship('Booking', backref=db.backref('review', uselist=False, lazy=True))

class Support(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # technical, billing, complaint, other
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, resolved
    admin_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    shop = db.relationship('Shop', backref=db.backref('support_tickets', lazy=True))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('support_tickets', lazy=True))
    resolved_by_user = db.relationship('User', foreign_keys=[resolved_by])

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('User', backref='favorites')
    shop = db.relationship('Shop', backref='favorited_by')
    
    # Đảm bảo mỗi khách hàng chỉ có thể yêu thích một tiệm một lần
    __table_args__ = (db.UniqueConstraint('customer_id', 'shop_id'),)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')






