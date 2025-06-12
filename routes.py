import os
import logging
from datetime import datetime, date, timedelta
from flask import render_template, redirect, url_for, flash, request, Response
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from app import app, db
from models import User, Shop, Service, Barber, Booking, Promotion, Review, Support, Favorite, Message
import math

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Thai Nguyen University coordinates (approximate)
UNIVERSITY_LAT = 21.5942
UNIVERSITY_LNG = 105.8167

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points using Haversine formula"""
    if not all([lat1, lng1, lat2, lng2]):
        return None
    
    R = 6371  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'shop_owner':
            return redirect(url_for('shop_dashboard'))
        else:
            return redirect(url_for('customer_dashboard'))
    
    # Show approved shops for non-logged in users
    shops = Shop.query.filter_by(is_approved=True).order_by(Shop.distance_from_university).limit(6).all()
    return render_template('index.html', shops=shops)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'shop_owner':
                # Check if shop owner has registered a shop
                shop = Shop.query.filter_by(owner_id=user.id).first()
                if shop:
                    return redirect(url_for('shop_dashboard'))
                else:
                    # Redirect to shop registration if no shop exists
                    flash('Vui lòng đăng ký thông tin tiệm của bạn.', 'info')
                    return redirect(url_for('shop_register'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        full_name = request.form['full_name']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']  # Get selected role
        
        # Validation
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email đã được sử dụng!', 'error')
            return render_template('register.html')
        
        # Create new user with selected role
        user = User(username=username, email=email, phone=phone, full_name=full_name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Log in the user
        login_user(user)
        
        # Redirect based on role
        if role == 'shop_owner':
            flash('Đăng ký thành công! Vui lòng cung cấp thông tin về tiệm của bạn.', 'success')
            return redirect(url_for('shop_register'))
        else:
            flash('Đăng ký thành công!', 'success')
            return redirect(url_for('customer_dashboard'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất thành công!', 'success')
    return redirect(url_for('index'))

@app.route('/customer-dashboard')
@login_required
def customer_dashboard():
    if current_user.role != 'customer':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Get user's bookings
    bookings = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.created_at.desc()).all()
    
    # Get nearby shops
    shops = Shop.query.filter_by(is_approved=True).order_by(Shop.distance_from_university).limit(10).all()
    
    return render_template('customer_dashboard.html', bookings=bookings, shops=shops)

@app.route('/shop-dashboard')
@login_required
def shop_dashboard():
    if current_user.role != 'shop_owner':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.filter_by(owner_id=current_user.id).first()
    if not shop:
        return redirect(url_for('shop_register'))
    
    # Get today's bookings
    today = date.today()
    today_bookings = Booking.query.filter_by(shop_id=shop.id, booking_date=today).order_by(Booking.booking_time).all()
    
    # Get upcoming bookings
    upcoming_bookings = Booking.query.filter(
        Booking.shop_id == shop.id,
        Booking.booking_date > today
    ).order_by(Booking.booking_date, Booking.booking_time).limit(10).all()
    
    # Get pending bookings
    pending_bookings = Booking.query.filter_by(
        shop_id=shop.id, 
        status='pending'
    ).order_by(Booking.booking_date, Booking.booking_time).all()
    
    return render_template('shop/shop_dashboard.html', shop=shop, today_bookings=today_bookings, 
                          upcoming_bookings=upcoming_bookings, pending_bookings=pending_bookings)

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Get pending shops for approval
    pending_shops = Shop.query.filter_by(is_approved=False).all()
    
    # Get statistics
    total_shops = Shop.query.count()
    approved_shops = Shop.query.filter_by(is_approved=True).count()
    total_users = User.query.filter_by(role='customer').count()
    total_bookings = Booking.query.count()
    
    stats = {
        'total_shops': total_shops,
        'approved_shops': approved_shops,
        'total_users': total_users,
        'total_bookings': total_bookings
    }
    
    return render_template('admin_dashboard.html', pending_shops=pending_shops, stats=stats)

@app.route('/shop-register', methods=['GET', 'POST'])
@login_required
def shop_register():
    if current_user.role != 'shop_owner':
        flash('Bạn không có quyền đăng ký tiệm!', 'error')
        return redirect(url_for('index'))
    
    # Check if user already has a shop
    existing_shop = Shop.query.filter_by(owner_id=current_user.id).first()
    if existing_shop:
        flash('Bạn đã đăng ký tiệm rồi!', 'info')
        return redirect(url_for('shop_dashboard'))
    
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']
        description = request.form.get('description', '')
        opening_time = request.form['opening_time']
        closing_time = request.form['closing_time']
        distance_from_university = float(request.form['distance_from_university'])
        
        # Optional fields
        latitude = request.form.get('latitude', None)
        longitude = request.form.get('longitude', None)
        
        # Create new shop
        shop = Shop(
            owner_id=current_user.id,
            name=name,
            phone=phone,
            address=address,
            description=description,
            opening_time=opening_time,
            closing_time=closing_time,
            distance_from_university=distance_from_university,
            is_approved=False  # Shops need admin approval
        )
        
        if latitude:
            shop.latitude = float(latitude)
        if longitude:
            shop.longitude = float(longitude)
        
        # Handle image upload
        if 'shop_image' in request.files and request.files['shop_image'].filename:
            file = request.files['shop_image']
            # Generate a secure filename
            filename = secure_filename(file.filename)
            # Ensure upload folder exists
            upload_folder = app.config.get('UPLOAD_FOLDER', 'static/uploads')
            os.makedirs(upload_folder, exist_ok=True)
            # Save the file
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            # Update the shop image path
            shop.image = os.path.join('uploads', filename)
        
        db.session.add(shop)
        db.session.commit()
        
        flash('Đăng ký tiệm thành công! Tiệm của bạn đang chờ phê duyệt.', 'success')
        return redirect(url_for('shop_dashboard'))
    
    return render_template('shop_register.html')

# Tìm kiếm tiệm
@app.route('/search', methods=['GET'])
def search_shops():
    # Lấy tham số tìm kiếm
    keyword = request.args.get('keyword', '')
    distance = request.args.get('distance', type=float)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    rating = request.args.get('rating', type=int)
    
    # Bắt đầu với tất cả các tiệm đã được phê duyệt
    query = Shop.query.filter_by(is_approved=True)
    
    # Áp dụng các bộ lọc
    if keyword:
        query = query.filter(Shop.name.ilike(f'%{keyword}%') | 
                            Shop.description.ilike(f'%{keyword}%'))
    
    if distance:
        query = query.filter(Shop.distance_from_university <= distance)
    
    if rating:
        query = query.filter(Shop.average_rating >= rating)
    
    # Lọc theo giá cần join với bảng Service
    if min_price is not None or max_price is not None:
        query = query.join(Service)
        if min_price is not None:
            query = query.filter(Service.price >= min_price)
        if max_price is not None:
            query = query.filter(Service.price <= max_price)
        query = query.group_by(Shop.id)
    
    # Sắp xếp theo khoảng cách
    shops = query.order_by(Shop.distance_from_university).all()
    
    return render_template('search_results.html', shops=shops, keyword=keyword)

# Xem chi tiết tiệm
@app.route('/shop/<int:shop_id>')
def shop_detail(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Only show approved shops to non-admin users
    if not shop.is_approved and (not current_user.is_authenticated or current_user.role != 'admin'):
        flash('Tiệm này chưa được phê duyệt!', 'error')
        return redirect(url_for('index'))
    
    # Get services
    services = Service.query.filter_by(shop_id=shop.id).all()
    
    # Get barbers
    barbers = Barber.query.filter_by(shop_id=shop.id).all()
    
    # Get reviews
    reviews = Review.query.filter_by(shop_id=shop.id).order_by(Review.created_at.desc()).all()
    
    # Calculate average rating
    avg_rating = 0
    if reviews:
        avg_rating = sum(review.rating for review in reviews) / len(reviews)
    
    return render_template('shop/shop_detail.html', 
                          shop=shop, 
                          services=services, 
                          barbers=barbers, 
                          reviews=reviews, 
                          avg_rating=avg_rating)

# Đặt lịch cắt tóc
@app.route('/booking/<int:shop_id>', methods=['GET', 'POST'])
@login_required
def create_booking(shop_id):
    if current_user.role != 'customer':
        flash('Chỉ khách hàng mới có thể đặt lịch!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    if not shop.is_approved:
        flash('Cửa hàng này chưa được phê duyệt!', 'error')
        return redirect(url_for('index'))
    
    # Kiểm tra và đặt giờ mở cửa/đóng cửa mặc định nếu không có
    if not shop.opening_time:
        shop.opening_time = datetime.strptime('08:00', '%H:%M').time()
    if not shop.closing_time:
        shop.closing_time = datetime.strptime('18:00', '%H:%M').time()
    
    print(f"Shop hours: {shop.opening_time} - {shop.closing_time}")
    
    services = Service.query.filter_by(shop_id=shop.id).all()
    barbers = Barber.query.filter_by(shop_id=shop.id).all()
    
    # Thêm biến today
    today = date.today().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        service_id = request.form.get('service_id', type=int)
        barber_id = request.form.get('barber_id', type=int)
        booking_date_str = request.form.get('booking_date')
        booking_time_str = request.form.get('booking_time')
        notes = request.form.get('notes', '')
        
        # Validate inputs
        if not all([service_id, booking_date_str, booking_time_str]):
            flash('Vui lòng điền đầy đủ thông tin!', 'error')
            return render_template('booking/create.html', shop=shop, services=services, barbers=barbers, today=today)
        
        # Parse date and time
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        booking_time = datetime.strptime(booking_time_str, '%H:%M').time()
        
        # Check if date is in the past
        if booking_date < date.today():
            flash('Không thể đặt lịch cho ngày trong quá khứ!', 'error')
            return render_template('booking/create.html', shop=shop, services=services, barbers=barbers, today=today)
        
        # Check if shop is open at that time
        # (Giả sử shop có giờ mở cửa và đóng cửa được lưu trong DB)
        
        # Check if barber is available at that time
        existing_booking = Booking.query.filter_by(
            shop_id=shop.id,
            barber_id=barber_id,
            booking_date=booking_date,
            booking_time=booking_time,
            status='confirmed'
        ).first()
        
        if existing_booking:
            flash('Khung giờ này đã được đặt! Vui lòng chọn giờ khác.', 'error')
        else:
            booking_obj = Booking(
                customer_id=current_user.id,
                shop_id=shop.id,
                service_id=service_id,
                barber_id=barber_id,
                booking_date=booking_date,
                booking_time=booking_time,
                notes=notes,
                status='pending'
            )
            
            db.session.add(booking_obj)
            db.session.commit()
            
            # Gửi email thông báo (nếu có)
            # send_booking_confirmation_email(current_user.email, booking_obj)
            
            flash('Đặt lịch thành công! Cửa hàng sẽ xác nhận trong thời gian sớm nhất.', 'success')
            return redirect(url_for('customer_dashboard'))
    
    return render_template('booking/create.html', shop=shop, services=services, barbers=barbers, today=today)

# Đánh giá và phản hồi
@app.route('/review/<int:shop_id>', methods=['GET', 'POST'])
@login_required
def create_review(shop_id):
    if current_user.role != 'customer':
        flash('Chỉ khách hàng mới có thể đánh giá!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    
    # Kiểm tra xem khách hàng đã từng sử dụng dịch vụ của tiệm chưa
    has_booking = Booking.query.filter_by(
        customer_id=current_user.id,
        shop_id=shop.id,
        status='completed'
    ).first()
    
    if not has_booking:
        flash('Bạn cần sử dụng dịch vụ trước khi đánh giá!', 'error')
        return redirect(url_for('shop_detail', shop_id=shop.id))
    
    # Kiểm tra xem khách hàng đã đánh giá tiệm này chưa
    existing_review = Review.query.filter_by(
        customer_id=current_user.id,
        shop_id=shop.id
    ).first()
    
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '')
        
        if not rating or rating < 1 or rating > 5:
            flash('Vui lòng chọn số sao từ 1-5!', 'error')
            return render_template('review/create.html', shop=shop, existing_review=existing_review)
        
        if existing_review:
            # Cập nhật đánh giá cũ
            existing_review.rating = rating
            existing_review.comment = comment
            existing_review.updated_at = datetime.utcnow()
            flash('Đã cập nhật đánh giá của bạn!', 'success')
        else:
            # Tạo đánh giá mới
            review = Review(
                customer_id=current_user.id,
                shop_id=shop.id,
                rating=rating,
                comment=comment
            )
            db.session.add(review)
            flash('Đã gửi đánh giá của bạn!', 'success')
        
        db.session.commit()
        
        # Cập nhật điểm đánh giá trung bình của tiệm
        update_shop_rating(shop.id)
        
        return redirect(url_for('shop_detail', shop_id=shop.id))
    
    return render_template('review/create.html', shop=shop, existing_review=existing_review)

# Hàm cập nhật điểm đánh giá trung bình của tiệm
def update_shop_rating(shop_id):
    """Cập nhật điểm đánh giá trung bình của tiệm"""
    shop = Shop.query.get(shop_id)
    if not shop:
        return
    
    # Lấy tất cả đánh giá đã được duyệt của tiệm
    reviews = Review.query.filter_by(shop_id=shop_id, is_approved=True).all()
    
    # Tính điểm trung bình
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        avg_rating = total_rating / len(reviews)
        shop.average_rating = round(avg_rating, 1)
    else:
        shop.average_rating = 0.0
    
    db.session.commit()

# Xem lịch sử đặt lịch
@app.route('/bookings/history')
@login_required
def booking_history():
    if current_user.role != 'customer':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    bookings = Booking.query.filter_by(customer_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('booking/history.html', bookings=bookings)

# Hủy lịch hẹn
@app.route('/booking/cancel/<int:booking_id>')
@login_required
def cancel_bookingg_request(booking_id):  # Đổi tên từ customer_cancel_booking thành cancel_booking_request
    booking = Booking.query.get_or_404(booking_id)
    
    # Đảm bảo chỉ chủ tiệm hoặc khách hàng mới có thể hủy lịch
    is_owner = current_user.role == 'shop_owner' and booking.shop.owner_id == current_user.id
    is_customer = current_user.role == 'customer' and booking.customer_id == current_user.id
    
    if not (is_owner or is_customer):
        flash('Bạn không có quyền hủy lịch hẹn này!', 'error')
        return redirect(url_for('index'))
    
    if booking.status not in ['pending', 'confirmed']:
        flash('Lịch hẹn này không thể hủy!', 'error')
    else:
        booking.status = 'cancelled'
        db.session.commit()
        flash('Đã hủy lịch hẹn thành công!', 'error')
    
    if is_customer:
        return redirect(url_for('booking_history'))
    else:
        return redirect(url_for('shop_dashboard'))

# Lưu tiệm yêu thích
@app.route('/favorite/<int:shop_id>', methods=['POST'])
@login_required
def toggle_favorite(shop_id):
    if current_user.role != 'customer':
        return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể lưu tiệm yêu thích!'})
    
    shop = Shop.query.get_or_404(shop_id)
    
    # Kiểm tra xem tiệm đã được yêu thích chưa
    favorite = Favorite.query.filter_by(
        customer_id=current_user.id,
        shop_id=shop.id
    ).first()
    
    if favorite:
        # Nếu đã yêu thích, xóa khỏi danh sách
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': False})
    else:
        # Nếu chưa yêu thích, thêm vào danh sách
        favorite = Favorite(customer_id=current_user.id, shop_id=shop.id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True, 'is_favorite': True})

# Xem danh sách tiệm yêu thích
@app.route('/favorites')
@login_required
def view_favorites():
    if current_user.role != 'customer':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    favorites = Favorite.query.filter_by(customer_id=current_user.id).all()
    favorite_shops = [favorite.shop for favorite in favorites]
    
    return render_template('customer/favorites.html', shops=favorite_shops)

# Gửi tin nhắn cho shop
@app.route('/messages/<int:shop_id>', methods=['GET', 'POST'])
@login_required
def shop_messages(shop_id):
    if current_user.role != 'customer':
        flash('Chỉ khách hàng mới có thể gửi tin nhắn cho tiệm!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            message = Message(
                sender_id=current_user.id,
                receiver_id=shop.owner_id,
                content=content,
                is_read=False
            )
            db.session.add(message)
            db.session.commit()
            flash('Đã gửi tin nhắn thành công!', 'success')
    
    # Lấy lịch sử tin nhắn giữa khách hàng và chủ tiệm
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id,
        receiver_id=shop.owner_id
    ).all()
    
    received_messages = Message.query.filter_by(
        sender_id=shop.owner_id,
        receiver_id=current_user.id
    ).all()
    
    # Kết hợp và sắp xếp theo thời gian
    messages = sorted(sent_messages + received_messages, key=lambda x: x.created_at)
    
    # Đánh dấu tin nhắn đã đọc
    for message in received_messages:
        if not message.is_read:
            message.is_read = True
    
    db.session.commit()
    
    return render_template('messages/chat.html', shop=shop, messages=messages)

# Xem tất cả cuộc trò chuyện
@app.route('/messages')
@login_required
def all_conversations():
    if current_user.role == 'customer':
        # Lấy danh sách các chủ tiệm mà khách hàng đã nhắn tin
        shop_owners = db.session.query(User).join(
            Message, 
            ((Message.sender_id == User.id) & (Message.receiver_id == current_user.id)) |
            ((Message.receiver_id == User.id) & (Message.sender_id == current_user.id))
        ).filter(User.role == 'shop_owner').distinct().all()
        
        # Lấy tin nhắn mới nhất và số tin nhắn chưa đọc cho mỗi cuộc trò chuyện
        conversations = []
        for owner in shop_owners:
            shop = Shop.query.filter_by(owner_id=owner.id).first()
            if not shop:
                continue
                
            latest_message = Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == owner.id)) |
                ((Message.receiver_id == current_user.id) & (Message.sender_id == owner.id))
            ).order_by(Message.created_at.desc()).first()
            
            unread_count = Message.query.filter_by(
                sender_id=owner.id,
                receiver_id=current_user.id,
                is_read=False
            ).count()
            
            conversations.append({
                'shop': shop,
                'latest_message': latest_message,
                'unread_count': unread_count
            })
        
        return render_template('messages/conversations.html', conversations=conversations)
    
    elif current_user.role == 'shop_owner':
        # Lấy danh sách khách hàng đã nhắn tin với chủ tiệm
        customers = db.session.query(User).join(
            Message, 
            ((Message.sender_id == User.id) & (Message.receiver_id == current_user.id)) |
            ((Message.receiver_id == User.id) & (Message.sender_id == current_user.id))
        ).filter(User.role == 'customer').distinct().all()
        
        # Lấy tin nhắn mới nhất và số tin nhắn chưa đọc cho mỗi cuộc trò chuyện
        conversations = []
        for customer in customers:
            latest_message = Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == customer.id)) |
                ((Message.receiver_id == current_user.id) & (Message.sender_id == customer.id))
            ).order_by(Message.created_at.desc()).first()
            
            unread_count = Message.query.filter_by(
                sender_id=customer.id,
                receiver_id=current_user.id,
                is_read=False
            ).count()
            
            conversations.append({
                'customer': customer,
                'latest_message': latest_message,
                'unread_count': unread_count
            })
        
        return render_template('messages/shop_conversations.html', conversations=conversations)
    
    else:
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))

@app.route('/approve-shop/<int:shop_id>')
@login_required
def approve_shop(shop_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    shop.is_approved = True
    db.session.commit()
    
    flash(f'Đã phê duyệt tiệm {shop.name}!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/reject-shop/<int:shop_id>')
@login_required
def reject_shop(shop_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    
    # You might want to notify the shop owner here
    
    # Delete the shop
    db.session.delete(shop)
    db.session.commit()
    
    flash(f'Đã từ chối và xóa tiệm {shop.name}!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/shop/booking/confirm/<int:booking_id>')
@login_required
def shop_confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure only the shop owner can confirm the booking
    if current_user.role != 'shop_owner' or booking.shop.owner_id != current_user.id:
        flash('Bạn không có quyền xác nhận lịch hẹn này!', 'error')
        return redirect(url_for('index'))
    
    if booking.status != 'pending':
        flash('Lịch hẹn này không thể xác nhận!', 'error')
    else:
        booking.status = 'confirmed'
        db.session.commit()
        flash('Đã xác nhận lịch hẹn thành công!', 'success')
    
    return redirect(url_for('shop_dashboard'))

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    users = User.query.order_by(User.role, User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.phone = request.form['phone']
        user.full_name = request.form['full_name']
        user.role = request.form['role']
        user.is_active = 'is_active' in request.form
        
        if request.form['password'] and len(request.form['password']) >= 6:
            user.set_password(request.form['password'])
            
        db.session.commit()
        flash(f'Đã cập nhật thông tin người dùng {user.username}!', 'success')
        return redirect(url_for('admin_users'))
        
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/user/create', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        full_name = request.form['full_name']
        password = request.form['password']
        role = request.form['role']
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại!', 'error')
            return render_template('admin/create_user.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email đã tồn tại!', 'error')
            return render_template('admin/create_user.html')
        
        # Create new user
        user = User(
            username=username, 
            email=email, 
            phone=phone, 
            full_name=full_name, 
            role=role,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Đã tạo người dùng mới thành công!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/create_user.html')

@app.route('/admin/user/toggle/<int:user_id>')
@login_required
def admin_toggle_user(user_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        flash('Không thể khóa tài khoản của chính mình!', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = "kích hoạt" if user.is_active else "khóa"
    flash(f'Đã {status} tài khoản {user.username}!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/shops')
@login_required
def admin_shops():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    shops = Shop.query.order_by(Shop.is_approved, Shop.created_at.desc()).all()
    return render_template('admin/shops.html', shops=shops)

@app.route('/admin/shop/<int:shop_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_shop(shop_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    
    if request.method == 'POST':
        shop.name = request.form['name']
        shop.address = request.form['address']
        shop.phone = request.form['phone']
        shop.description = request.form['description']
        shop.opening_time = request.form['opening_time']
        shop.closing_time = request.form['closing_time']
        shop.distance_from_university = float(request.form['distance_from_university'])
        shop.is_approved = 'is_approved' in request.form
        
        db.session.commit()
        flash(f'Đã cập nhật thông tin tiệm {shop.name}!', 'success')
        return redirect(url_for('admin_shops'))
        
    return render_template('admin/edit_shop.html', shop=shop)

@app.route('/admin/shop/toggle/<int:shop_id>')
@login_required
def admin_toggle_shop(shop_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    shop.is_approved = not shop.is_approved
    db.session.commit()
    
    status = "phê duyệt" if shop.is_approved else "hủy phê duyệt"
    flash(f'Đã {status} tiệm {shop.name}!', 'success')
    return redirect(url_for('admin_shops'))

@app.route('/admin/shop/delete/<int:shop_id>')
@login_required
def admin_delete_shop(shop_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    shop = Shop.query.get_or_404(shop_id)
    
    # Delete related records first (services, barbers, bookings)
    Service.query.filter_by(shop_id=shop.id).delete()
    Barber.query.filter_by(shop_id=shop.id).delete()
    Booking.query.filter_by(shop_id=shop.id).delete()
    
    db.session.delete(shop)
    db.session.commit()
    
    flash(f'Đã xóa tiệm {shop.name} và tất cả dữ liệu liên quan!', 'success')
    return redirect(url_for('admin_shops'))

@app.route('/admin/services')
@login_required
def admin_services():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    services = Service.query.join(Shop).order_by(Shop.name, Service.name).all()
    return render_template('admin/services.html', services=services)

@app.route('/admin/service/<int:service_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_service(service_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'POST':
        service.name = request.form['name']
        service.description = request.form['description']
        service.price = float(request.form['price'])
        service.duration = int(request.form['duration'])
        
        db.session.commit()
        flash(f'Đã cập nhật thông tin dịch vụ {service.name}!', 'success')
        return redirect(url_for('admin_services'))
        
    return render_template('admin/edit_service.html', service=service)

@app.route('/admin/announcements', methods=['GET', 'POST'])
@login_required
def admin_announcements():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Add Announcement model if it doesn't exist
    # This is a placeholder - you would need to create the Announcement model
    announcements = []  # Replace with Announcement.query.order_by(Announcement.created_at.desc()).all()
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        is_public = 'is_public' in request.form
        
        # Create new announcement
        # announcement = Announcement(title=title, content=content, is_public=is_public, author_id=current_user.id)
        # db.session.add(announcement)
        # db.session.commit()
        
        flash('Đã đăng thông báo mới!', 'success')
        return redirect(url_for('admin_announcements'))
    
    return render_template('admin/announcements.html', announcements=announcements)

@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Get statistics for reports
    total_users = User.query.count()
    customer_count = User.query.filter_by(role='customer').count()
    shop_owner_count = User.query.filter_by(role='shop_owner').count()
    
    total_shops = Shop.query.count()
    approved_shops = Shop.query.filter_by(is_approved=True).count()
    
    total_bookings = Booking.query.count()
    
    # Get bookings by date (last 30 days)
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    # Create a list of tuples (date, count) instead of a dictionary
    bookings_by_date = []
    for i in range(30):
        day = thirty_days_ago + timedelta(days=i)
        count = Booking.query.filter(Booking.booking_date == day).count()
        bookings_by_date.append((day, count))
    
    # Get top shops by bookings
    top_shops_query = db.session.query(
        Shop.name, db.func.count(Booking.id).label('booking_count')
    ).join(Booking, Shop.id == Booking.shop_id).group_by(Shop.id).order_by(db.desc('booking_count')).limit(5).all()
    
    # Convert query result to a list of dictionaries
    top_shops = []
    for name, count in top_shops_query:
        top_shops.append({
            'name': name,
            'booking_count': count
        })
    
    # Get top services - Fix the join ambiguity by using select_from and explicit joins
    top_services_query = db.session.query(
        Service.name, 
        Shop.name.label('shop_name'), 
        Service.price, 
        db.func.count(Booking.id).label('booking_count')
    ).select_from(Service).join(
        Shop, Service.shop_id == Shop.id
    ).join(
        Booking, Booking.service_id == Service.id
    ).group_by(
        Service.id, Shop.name
    ).order_by(
        db.desc('booking_count')
    ).limit(5).all()
    
    # Convert query result to a list of dictionaries
    top_services = []
    for name, shop_name, price, count in top_services_query:
        top_services.append({
            'name': name,
            'shop_name': shop_name,
            'price': price,
            'booking_count': count
        })
    
    stats = {
        'total_users': total_users,
        'customer_count': customer_count,
        'shop_owner_count': shop_owner_count,
        'total_shops': total_shops,
        'approved_shops': approved_shops,
        'total_bookings': total_bookings,
        'bookings_by_date': bookings_by_date,
        'top_shops': top_shops,
        'top_services': top_services
    }
    
    return render_template('admin/reports.html', stats=stats)

@app.route('/admin/export-data')
@login_required
def admin_export_data():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Create CSV data
    import io
    import csv
    from datetime import datetime
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Khách hàng', 'Email', 'Tiệm', 'Dịch vụ', 'Giá', 'Ngày đặt', 'Giờ đặt', 'Trạng thái'])
    
    # Get all bookings
    bookings = Booking.query.order_by(Booking.booking_date.desc(), Booking.booking_time).all()
    
    # Write data
    for booking in bookings:
        writer.writerow([
            booking.id,
            booking.customer.full_name,
            booking.customer.email,
            booking.shop.name,
            booking.service.name,
            booking.service.price,
            booking.booking_date.strftime('%d/%m/%Y'),
            booking.booking_time.strftime('%H:%M'),
            booking.status
        ])
    
    # Create response
    from flask import Response
    output.seek(0)
    filename = f"bookings_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@app.route('/admin/support')
@login_required
def admin_support():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Add Support model if it doesn't exist
    # This is a placeholder - you would need to create the Support model
    support_tickets = []  # Replace with Support.query.order_by(Support.created_at.desc()).all()
    
    return render_template('admin/support.html', support_tickets=support_tickets)

@app.route('/admin/support/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def admin_support_detail(ticket_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Get support ticket
    # ticket = Support.query.get_or_404(ticket_id)
    ticket = None  # Placeholder
    
    if request.method == 'POST':
        response = request.form['response']
        
        # Update ticket
        # ticket.admin_response = response
        # ticket.status = 'resolved'
        # ticket.resolved_at = datetime.utcnow()
        # ticket.resolved_by = current_user.id
        # db.session.commit()
        
        flash('Đã gửi phản hồi thành công!', 'success')
        return redirect(url_for('admin_support'))
    
    return render_template('admin/support_detail.html', ticket=ticket)

# Create admin user if doesn't exist
def create_admin():
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@barbershop.com',
            phone='0123456789',
            full_name='Quản trị viên hệ thống',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logging.info("Đã tạo tài khoản admin: username=admin, password=admin123")

# Call create_admin on startup
with app.app_context():
    create_admin()






# Shop Management Routes
@app.route('/shop/edit/<int:shop_id>', methods=['GET', 'POST'])
@login_required
def shop_edit(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can edit their shop
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền chỉnh sửa tiệm này!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        shop.name = request.form['name']
        shop.address = request.form['address']
        shop.phone = request.form['phone']
        shop.description = request.form['description']
        shop.opening_time = request.form['opening_time']
        shop.closing_time = request.form['closing_time']
        
        # Optional fields
        if 'latitude' in request.form and request.form['latitude']:
            shop.latitude = float(request.form['latitude'])
        if 'longitude' in request.form and request.form['longitude']:
            shop.longitude = float(request.form['longitude'])
        if 'distance_from_university' in request.form and request.form['distance_from_university']:
            shop.distance_from_university = float(request.form['distance_from_university'])
        
        # Handle image upload
        if 'shop_image' in request.files and request.files['shop_image'].filename:
            file = request.files['shop_image']
            # Generate a secure filename
            filename = secure_filename(file.filename)
            # Save the file
            file_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), filename)
            file.save(file_path)
            # Update the shop image path
            shop.image = os.path.join('uploads', filename)
        
        db.session.commit()
        flash('Thông tin tiệm đã được cập nhật thành công!', 'success')
        return redirect(url_for('shop_dashboard'))
    
    return render_template('shop/edit.html', shop=shop)

@app.route('/shop/service/add/<int:shop_id>', methods=['POST'])
@login_required
def add_service(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can add services
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền thêm dịch vụ cho tiệm này!', 'error')
        return redirect(url_for('index'))
    
    name = request.form['name']
    price = float(request.form['price'])
    duration = int(request.form['duration'])
    description = request.form.get('description', '')
    
    service = Service(
        shop_id=shop.id,
        name=name,
        price=price,
        duration=duration,
        description=description
    )
    
    db.session.add(service)
    db.session.commit()
    
    flash(f'Đã thêm dịch vụ "{name}" thành công!', 'success')
    return redirect(url_for('shop_services', shop_id=shop.id))

@app.route('/shop/service/edit/<int:service_id>', methods=['POST'])
@login_required
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    
    # Ensure only the owner can edit services
    if service.shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền chỉnh sửa dịch vụ này!', 'error')
        return redirect(url_for('index'))
    
    service.name = request.form['name']
    service.price = float(request.form['price'])
    service.duration = int(request.form['duration'])
    service.description = request.form.get('description', '')
    
    db.session.commit()
    
    flash(f'Đã cập nhật dịch vụ "{service.name}" thành công!', 'success')
    return redirect(url_for('shop_services', shop_id=service.shop_id))

@app.route('/shop/service/delete/<int:service_id>')
@login_required
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    
    # Ensure only the owner can delete services
    if service.shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền xóa dịch vụ này!', 'error')
        return redirect(url_for('index'))
    
    shop_id = service.shop_id
    service_name = service.name
    
    db.session.delete(service)
    db.session.commit()
    
    flash(f'Đã xóa dịch vụ "{service_name}" thành công!', 'success')
    return redirect(url_for('shop_services', shop_id=shop_id))

@app.route('/shop/barber/add/<int:shop_id>', methods=['POST'])
@login_required
def add_barber(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can add barbers
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền thêm thợ cắt tóc cho tiệm này!', 'error')
        return redirect(url_for('index'))
    
    name = request.form['name']
    experience = request.form.get('experience', '')
    specialization = request.form.get('specialization', '')
    
    barber = Barber(
        shop_id=shop.id,
        name=name,
        experience=experience,
        specialization=specialization,
        is_active=True
    )
    
    db.session.add(barber)
    db.session.commit()
    
    flash(f'Đã thêm thợ cắt tóc "{name}" thành công!', 'success')
    return redirect(url_for('shop_barbers', shop_id=shop.id))

@app.route('/shop/barber/edit/<int:barber_id>', methods=['POST'])
@login_required
def edit_barber(barber_id):
    barber = Barber.query.get_or_404(barber_id)
    
    # Ensure only the owner can edit barbers
    if barber.shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền chỉnh sửa thông tin thợ cắt tóc này!', 'error')
        return redirect(url_for('index'))
    
    barber.name = request.form['name']
    barber.experience = request.form.get('experience', '')
    barber.specialization = request.form.get('specialization', '')
    barber.is_active = 'is_active' in request.form
    
    db.session.commit()
    
    flash(f'Đã cập nhật thông tin thợ cắt tóc "{barber.name}" thành công!', 'success')
    return redirect(url_for('shop_barbers', shop_id=barber.shop_id))

@app.route('/shop/barber/delete/<int:barber_id>')
@login_required
def delete_barber(barber_id):
    barber = Barber.query.get_or_404(barber_id)
    
    # Ensure only the owner can delete barbers
    if barber.shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền xóa thợ cắt tóc này!', 'error')
        return redirect(url_for('index'))
    
    shop_id = barber.shop_id
    barber_name = barber.name
    
    db.session.delete(barber)
    db.session.commit()
    
    flash(f'Đã xóa thợ cắt tóc "{barber_name}" thành công!', 'success')
    return redirect(url_for('shop_barbers', shop_id=shop_id))

@app.route('/shop/services/<int:shop_id>')
@login_required
def shop_services(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can view their shop's services
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    services = Service.query.filter_by(shop_id=shop.id).all()
    return render_template('shop/services.html', shop=shop, services=services)

@app.route('/shop/barbers/<int:shop_id>')
@login_required
def shop_barbers(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can view their shop's barbers
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    barbers = Barber.query.filter_by(shop_id=shop.id).all()
    return render_template('shop/barbers.html', shop=shop, barbers=barbers)

@app.route('/shop/bookings/<int:shop_id>')
@login_required
def shop_bookings(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can view their shop's bookings
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Base query
    query = Booking.query.filter_by(shop_id=shop.id)
    
    # Apply filters
    if status != 'all':
        query = query.filter_by(status=status)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Booking.booking_date >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Booking.booking_date <= to_date)
        except ValueError:
            pass
    
    # Order by date and time
    bookings = query.order_by(Booking.booking_date.desc(), Booking.booking_time).all()
    
    return render_template('shop/bookings.html', shop=shop, bookings=bookings, 
                          status=status, date_from=date_from, date_to=date_to)

@app.route('/shop/promotions/<int:shop_id>')
@login_required
def shop_promotions(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can view their shop's promotions
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    promotions = Promotion.query.filter_by(shop_id=shop.id).order_by(Promotion.created_at.desc()).all()
    today = date.today()
    
    return render_template('shop/promotions.html', shop=shop, promotions=promotions, today=today)

@app.route('/shop/promotion/add/<int:shop_id>', methods=['POST'])
@login_required
def add_promotion(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can add promotions
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền thêm khuyến mãi cho tiệm này!', 'error')
        return redirect(url_for('index'))
    
    name = request.form['name']
    description = request.form.get('description', '')
    discount_percent = int(request.form['discount_percent'])
    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
    
    # Validate dates
    if start_date > end_date:
        flash('Ngày bắt đầu không thể sau ngày kết thúc!', 'error')
        return redirect(url_for('shop_promotions', shop_id=shop.id))
    
    # Validate discount percent
    if discount_percent < 1 or discount_percent > 100:
        flash('Phần trăm giảm giá phải từ 1% đến 100%!', 'error')
        return redirect(url_for('shop_promotions', shop_id=shop.id))
    
    promotion = Promotion(
        shop_id=shop.id,
        name=name,
        description=description,
        discount_percent=discount_percent,
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    
    db.session.add(promotion)
    db.session.commit()
    
    flash(f'Đã thêm khuyến mãi "{name}" thành công!', 'success')
    return redirect(url_for('shop_promotions', shop_id=shop.id))

@app.route('/shop/promotion/edit/<int:promotion_id>', methods=['POST'])
@login_required
def edit_promotion(promotion_id):
    promotion = Promotion.query.get_or_404(promotion_id)
    
    # Ensure only the owner can edit promotions
    if promotion.shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền chỉnh sửa khuyến mãi này!', 'error')
        return redirect(url_for('index'))
    
    promotion.name = request.form['name']
    promotion.description = request.form.get('description', '')
    promotion.discount_percent = int(request.form['discount_percent'])
    promotion.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
    promotion.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
    promotion.is_active = 'is_active' in request.form
    
    # Validate dates
    if promotion.start_date > promotion.end_date:
        flash('Ngày bắt đầu không thể sau ngày kết thúc!', 'error')
        return redirect(url_for('shop_promotions', shop_id=promotion.shop_id))
    
    # Validate discount percent
    if promotion.discount_percent < 1 or promotion.discount_percent > 100:
        flash('Phần trăm giảm giá phải từ 1% đến 100%!', 'error')
        return redirect(url_for('shop_promotions', shop_id=promotion.shop_id))
    
    db.session.commit()
    
    flash(f'Đã cập nhật khuyến mãi "{promotion.name}" thành công!', 'success')
    return redirect(url_for('shop_promotions', shop_id=promotion.shop_id))

@app.route('/shop/promotion/delete/<int:promotion_id>')
@login_required
def delete_promotion(promotion_id):
    promotion = Promotion.query.get_or_404(promotion_id)
    
    # Ensure only the owner can delete promotions
    if promotion.shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền xóa khuyến mãi này!', 'error')
        return redirect(url_for('index'))
    
    shop_id = promotion.shop_id
    promotion_name = promotion.name
    
    db.session.delete(promotion)
    db.session.commit()
    
    flash(f'Đã xóa khuyến mãi "{promotion_name}" thành công!', 'success')
    return redirect(url_for('shop_promotions', shop_id=shop_id))

@app.route('/shop/reviews/<int:shop_id>')
@login_required
def shop_reviews(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can view their shop's reviews
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Get all reviews for this shop
    reviews = Review.query.filter_by(shop_id=shop.id).order_by(Review.created_at.desc()).all()
    
    # Count ratings by star
    rating_counts = {}
    for review in reviews:
        rating_counts[review.rating] = rating_counts.get(review.rating, 0) + 1
    
    return render_template('shop/reviews.html', shop=shop, reviews=reviews, rating_counts=rating_counts)

@app.route('/shop/reports/<int:shop_id>')
@login_required
def shop_reports(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Check if current user is the shop owner
    if current_user.id != shop.owner_id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Get booking statistics
    total_bookings = Booking.query.filter_by(shop_id=shop_id).count()
    completed_bookings = Booking.query.filter_by(shop_id=shop_id, status='completed').count()
    cancelled_bookings = Booking.query.filter_by(shop_id=shop_id, status='cancelled').count()
    pending_bookings = Booking.query.filter_by(shop_id=shop_id, status='pending').count()
    confirmed_bookings = Booking.query.filter_by(shop_id=shop_id, status='confirmed').count()
    
    # Get popular services
    popular_services = db.session.query(
        Service.id,
        Service.name,
        Service.price,
        db.func.count(Booking.id).label('booking_count')
    ).join(
        Booking, Booking.service_id == Service.id
    ).filter(
        Service.shop_id == shop_id
    ).group_by(
        Service.id
    ).order_by(
        db.func.count(Booking.id).desc()
    ).limit(5).all()
    
    # Get bookings by date (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    
    bookings_by_date = db.session.query(
        Booking.booking_date, 
        db.func.count(Booking.id)
    ).filter(
        Booking.shop_id == shop_id,
        Booking.booking_date >= thirty_days_ago
    ).group_by(
        Booking.booking_date
    ).order_by(
        Booking.booking_date
    ).all()
    
    # Fill in missing dates with zero counts
    date_dict = {date: count for date, count in bookings_by_date}
    complete_dates = []
    
    for i in range(30):
        date = datetime.now().date() - timedelta(days=i)
        count = date_dict.get(date, 0)
        complete_dates.append((date, count))
    
    complete_dates.reverse()
    
    # Calculate revenue
    # For simplicity, we'll assume all completed bookings generate revenue
    # In a real app, you might have a separate payments table
    
    # Total revenue
    total_revenue = db.session.query(
        db.func.sum(Service.price)
    ).join(
        Booking, Booking.service_id == Service.id
    ).filter(
        Booking.shop_id == shop_id,
        Booking.status == 'completed'
    ).scalar() or 0
    
    # Monthly revenue
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = db.session.query(
        db.func.sum(Service.price)
    ).join(
        Booking, Booking.service_id == Service.id
    ).filter(
        Booking.shop_id == shop_id,
        Booking.status == 'completed',
        Booking.booking_date >= current_month_start
    ).scalar() or 0
    
    # Average daily revenue (based on days with at least one booking)
    days_with_bookings = db.session.query(
        db.func.count(db.func.distinct(Booking.booking_date))
    ).filter(
        Booking.shop_id == shop_id,
        Booking.status == 'completed'
    ).scalar() or 1  # Avoid division by zero
    
    avg_daily_revenue = total_revenue / days_with_bookings if days_with_bookings > 0 else 0
    
    # Monthly revenue data for the last 6 months
    monthly_revenue_data = []
    
    for i in range(5, -1, -1):
        month_date = datetime.now().replace(day=1) - timedelta(days=i*30)
        month_name = month_date.strftime('%m/%Y')
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if i > 0:
            next_month = month_date.replace(day=28) + timedelta(days=4)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        else:
            month_end = datetime.now()
            
        month_revenue = db.session.query(
            db.func.sum(Service.price)
        ).join(
            Booking, Booking.service_id == Service.id
        ).filter(
            Booking.shop_id == shop_id,
            Booking.status == 'completed',
            Booking.booking_date >= month_start,
            Booking.booking_date <= month_end
        ).scalar() or 0
        
        monthly_revenue_data.append((month_name, month_revenue))
    
    return render_template('shop/reports.html', shop=shop,
                          total_bookings=total_bookings,
                          completed_bookings=completed_bookings,
                          cancelled_bookings=cancelled_bookings,
                          pending_bookings=pending_bookings,
                          confirmed_bookings=confirmed_bookings,
                          popular_services=popular_services,
                          bookings_by_date=complete_dates,
                          total_revenue=total_revenue,
                          monthly_revenue=monthly_revenue,
                          avg_daily_revenue=avg_daily_revenue,
                          monthly_revenue_data=monthly_revenue_data)

@app.route('/shop/support/<int:shop_id>', methods=['GET'])
@login_required
def shop_support(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can access their shop's support
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Lấy danh sách yêu cầu hỗ trợ của shop này
    support_tickets = Support.query.filter_by(shop_id=shop.id).order_by(Support.created_at.desc()).all()
    
    return render_template('shop/support.html', shop=shop, support_tickets=support_tickets)

@app.route('/shop/support/<int:shop_id>/submit', methods=['POST'])
@login_required
def shop_support_submit(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can submit support requests
    if shop.owner_id != current_user.id:
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    # Lấy dữ liệu từ form
    subject = request.form.get('subject')
    ticket_type = request.form.get('type')
    message = request.form.get('message')
    
    if not subject or not ticket_type or not message:
        flash('Vui lòng điền đầy đủ thông tin!', 'error')
        return redirect(url_for('shop_support', shop_id=shop.id))
    
    # Tạo yêu cầu hỗ trợ mới
    support = Support(
        shop_id=shop.id,
        user_id=current_user.id,
        subject=subject,
        type=ticket_type,
        message=message,
        status='pending'
    )
    db.session.add(support)
    db.session.commit()
    
    flash('Đã gửi yêu cầu hỗ trợ thành công! Chúng tôi sẽ phản hồi sớm nhất có thể.', 'success')
    return redirect(url_for('shop_support', shop_id=shop.id))

@app.route('/shop/support/<int:shop_id>/detail/<int:ticket_id>')
@login_required
def shop_support_detail(shop_id, ticket_id):
    shop = Shop.query.get_or_404(shop_id)
    
    # Ensure only the owner can view their support tickets
    if shop.owner_id != current_user.id and current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Lấy thông tin yêu cầu hỗ trợ
    ticket = Support.query.get_or_404(ticket_id)
    
    # Kiểm tra xem ticket có thuộc về shop này không
    if ticket.shop_id != shop.id:
        flash('Yêu cầu hỗ trợ không tồn tại!', 'error')
        return redirect(url_for('shop_support', shop_id=shop.id))
    
    return render_template('shop/support_detail.html', shop=shop, ticket=ticket)

# Booking Management Routes
@app.route('/booking/detail/<int:booking_id>')
@login_required
def booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Kiểm tra quyền truy cập
    if current_user.role == 'admin':
        # Admin có thể xem tất cả các lịch đặt
        pass
    elif current_user.role == 'shop_owner':
        # Chủ tiệm chỉ có thể xem lịch đặt của tiệm mình
        shop = Shop.query.filter_by(owner_id=current_user.id).first()
        if not shop or booking.shop_id != shop.id:
            flash('Bạn không có quyền xem lịch đặt này!', 'error')
            return redirect(url_for('shop_dashboard'))
    elif current_user.role == 'customer':
        # Khách hàng chỉ có thể xem lịch đặt của mình
        if booking.customer_id != current_user.id:
            flash('Bạn không có quyền xem lịch đặt này!', 'error')
            return redirect(url_for('customer_dashboard'))
    else:
        flash('Bạn không có quyền xem lịch đặt này!', 'error')
        return redirect(url_for('index'))
    
    # Chọn template dựa trên vai trò người dùng
    if current_user.role == 'admin':
        template = 'admin/booking_detail.html'
    elif current_user.role == 'shop_owner':
        template = 'shop/booking_detail.html'
    else:  # customer
        template = 'customer/booking_detail.html'
    
    return render_template(template, booking=booking)

@app.route('/booking/<int:booking_id>/confirm')
@login_required
def confirm_booking(booking_id):
    if current_user.role != 'admin' and current_user.role != 'shop_owner':
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Nếu là chủ tiệm, kiểm tra xem lịch đặt có thuộc về tiệm của họ không
    if current_user.role == 'shop_owner':
        shop = Shop.query.filter_by(owner_id=current_user.id).first()
        if not shop or booking.shop_id != shop.id:
            flash('Bạn không có quyền thực hiện hành động này!', 'error')
            return redirect(url_for('index'))
    
    if booking.status != 'pending':
        flash('Chỉ có thể xác nhận lịch đặt đang chờ xác nhận!', 'error')
        return redirect(url_for('booking_detail', booking_id=booking.id))
    
    booking.status = 'confirmed'
    db.session.commit()
    
    flash('Lịch đặt đã được xác nhận thành công!', 'success')
    return redirect(url_for('booking_detail', booking_id=booking.id))

@app.route('/booking/<int:booking_id>/complete')
@login_required
def complete_booking(booking_id):
    if current_user.role != 'admin' and current_user.role != 'shop_owner':
        flash('Bạn không có quyền thực hiện hành động này!', 'error')
        return redirect(url_for('index'))
    
    booking = Booking.query.get_or_404(booking_id)
    
    # Nếu là chủ tiệm, kiểm tra xem lịch đặt có thuộc về tiệm của họ không
    if current_user.role == 'shop_owner':
        shop = Shop.query.filter_by(owner_id=current_user.id).first()
        if not shop or booking.shop_id != shop.id:
            flash('Bạn không có quyền thực hiện hành động này!', 'error')
            return redirect(url_for('index'))
    
    if booking.status != 'confirmed':
        flash('Chỉ có thể hoàn thành lịch đặt đã được xác nhận!', 'error')
        return redirect(url_for('booking_detail', booking_id=booking.id))
    
    booking.status = 'completed'
    db.session.commit()
    
    flash('Lịch đặt đã được đánh dấu là hoàn thành!', 'success')
    return redirect(url_for('booking_detail', booking_id=booking.id))

@app.route('/booking/cancel/<int:booking_id>')
@login_required
def cancel_booking_request(booking_id):  # Đổi tên từ customer_cancel_booking thành cancel_booking_request
    booking = Booking.query.get_or_404(booking_id)
    
    # Đảm bảo chỉ chủ tiệm hoặc khách hàng mới có thể hủy lịch
    is_owner = current_user.role == 'shop_owner' and booking.shop.owner_id == current_user.id
    is_customer = current_user.role == 'customer' and booking.customer_id == current_user.id
    
    if not (is_owner or is_customer):
        flash('Bạn không có quyền hủy lịch hẹn này!', 'error')
        return redirect(url_for('index'))
    
    if booking.status not in ['pending', 'confirmed']:
        flash('Lịch hẹn này không thể hủy!', 'error')
    else:
        booking.status = 'cancelled'
        db.session.commit()
        flash('Đã hủy lịch hẹn thành công!', 'error')
    
    if is_customer:
        return redirect(url_for('booking_history'))
    else:
        return redirect(url_for('shop_dashboard'))

@app.route('/review/delete/<int:review_id>')
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    shop = Shop.query.get_or_404(review.shop_id)
    
    # Kiểm tra quyền: chỉ admin hoặc chủ tiệm mới có thể xóa đánh giá
    if current_user.role != 'admin' and (current_user.role != 'shop_owner' or shop.owner_id != current_user.id):
        flash('Bạn không có quyền xóa đánh giá này!', 'error')
        return redirect(url_for('index'))
    
    # Xóa đánh giá
    db.session.delete(review)
    db.session.commit()
    
    # Cập nhật điểm đánh giá trung bình của tiệm
    update_shop_rating(shop.id)
    
    flash('Đã xóa đánh giá thành công!', 'success')
    
    # Chuyển hướng về trang phù hợp
    if current_user.role == 'admin':
        return redirect(url_for('admin_reviews'))
    else:
        return redirect(url_for('shop_reviews', shop_id=shop.id))

@app.route('/review/approve/<int:review_id>')
@login_required
def approve_review(review_id):
    review = Review.query.get_or_404(review_id)
    shop = Shop.query.get_or_404(review.shop_id)
    
    # Kiểm tra quyền: chỉ admin hoặc chủ tiệm mới có thể duyệt đánh giá
    if current_user.role != 'admin' and (current_user.role != 'shop_owner' or shop.owner_id != current_user.id):
        flash('Bạn không có quyền duyệt đánh giá này!', 'error')
        return redirect(url_for('index'))
    
    # Duyệt đánh giá
    review.is_approved = True
    db.session.commit()
    
    flash('Đã duyệt đánh giá thành công!', 'success')
    
    # Chuyển hướng về trang phù hợp
    if current_user.role == 'admin':
        return redirect(url_for('admin_reviews'))
    else:
        return redirect(url_for('shop_reviews', shop_id=shop.id))

@app.route('/review/reply/<int:review_id>', methods=['POST'])
@login_required
def reply_to_review(review_id):
    review = Review.query.get_or_404(review_id)
    shop = Shop.query.get_or_404(review.shop_id)
    
    # Kiểm tra quyền: chỉ admin hoặc chủ tiệm mới có thể phản hồi đánh giá
    if current_user.role != 'admin' and (current_user.role != 'shop_owner' or shop.owner_id != current_user.id):
        flash('Bạn không có quyền phản hồi đánh giá này!', 'error')
        return redirect(url_for('index'))
    
    # Lấy nội dung phản hồi
    shop_response = request.form.get('shop_response', '')
    
    # Cập nhật phản hồi
    review.shop_response = shop_response
    db.session.commit()
    
    flash('Đã gửi phản hồi thành công!', 'success')
    
    # Chuyển hướng về trang phù hợp
    if current_user.role == 'admin':
        return redirect(url_for('admin_reviews'))
    else:
        return redirect(url_for('shop_reviews', shop_id=shop.id))

@app.route('/admin/reviews')
@login_required
def admin_reviews():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Lấy tất cả các đánh giá, sắp xếp theo thời gian tạo giảm dần
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    
    return render_template('admin/reviews.html', reviews=reviews)

@app.route('/admin/booking/<int:booking_id>')
@login_required
def admin_booking_detail(booking_id):
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    booking = Booking.query.get_or_404(booking_id)
    
    return render_template('admin/booking_detail.html', booking=booking)

# Route để chủ tiệm xem tin nhắn với một khách hàng cụ thể
@app.route('/shop/messages/customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def shop_customer_messages(customer_id):
    if current_user.role != 'shop_owner':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    customer = User.query.get_or_404(customer_id)
    if customer.role != 'customer':
        flash('Người dùng không phải là khách hàng!', 'error')
        return redirect(url_for('all_conversations'))
    
    # Lấy thông tin shop của chủ tiệm
    shop = Shop.query.filter_by(owner_id=current_user.id).first()
    if not shop:
        flash('Bạn chưa đăng ký tiệm!', 'error')
        return redirect(url_for('shop_dashboard'))
    
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            message = Message(
                sender_id=current_user.id,
                receiver_id=customer_id,
                content=content,
                is_read=False
            )
            db.session.add(message)
            db.session.commit()
            flash('Đã gửi tin nhắn thành công!', 'success')
    
    # Lấy lịch sử tin nhắn giữa chủ tiệm và khách hàng
    sent_messages = Message.query.filter_by(
        sender_id=current_user.id,
        receiver_id=customer_id
    ).all()
    
    received_messages = Message.query.filter_by(
        sender_id=customer_id,
        receiver_id=current_user.id
    ).all()
    
    # Kết hợp và sắp xếp theo thời gian
    messages = sorted(sent_messages + received_messages, key=lambda x: x.created_at)
    
    # Đánh dấu tin nhắn đã đọc
    for message in received_messages:
        if not message.is_read:
            message.is_read = True
    
    db.session.commit()
    
    # Thêm dòng return này
    return render_template('messages/shop_chat.html', customer=customer, shop=shop, messages=messages)

@app.route('/admin/bookings')
@login_required
def admin_bookings():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này!', 'error')
        return redirect(url_for('index'))
    
    # Lấy tất cả các đặt lịch, sắp xếp theo thời gian tạo giảm dần
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    
    # Phân loại đặt lịch theo trạng thái
    pending_bookings = [b for b in bookings if b.status == 'pending']
    confirmed_bookings = [b for b in bookings if b.status == 'confirmed']
    completed_bookings = [b for b in bookings if b.status == 'completed']
    cancelled_bookings = [b for b in bookings if b.status == 'cancelled']
    
    return render_template(
        'admin/bookings.html',
        bookings=bookings,
        pending_count=len(pending_bookings),
        confirmed_count=len(confirmed_bookings),
        completed_count=len(completed_bookings),
        cancelled_count=len(cancelled_bookings)
    )

    return render_template('messages/shop_chat.html', customer=customer, shop=shop, messages=messages)











