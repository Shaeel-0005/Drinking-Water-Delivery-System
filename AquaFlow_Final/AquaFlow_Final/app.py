from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'water-supply-secret-key-2024'

DATABASE = 'water_supply.db'

# Database helper functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with schema and create admin/van users"""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())

        # Create admin user if not exists
        cursor = db.execute('SELECT * FROM users WHERE email = ?', ('admin@water.com',))
        if cursor.fetchone() is None:
            hashed_password = generate_password_hash('admin123')
            db.execute(
                'INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, ?)',
                ('Admin', 'admin@water.com', '0000000000', hashed_password, 'admin')
            )
        
        # Create delivery user if not exists
        cursor = db.execute('SELECT * FROM users WHERE email = ?', ('delivery@water.com',))
        if cursor.fetchone() is None:
            hashed_password = generate_password_hash('delivery123')
            db.execute(
                'INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, ?)',
                ('Delivery Boy', 'delivery@water.com', '0000000000', hashed_password, 'delivery')
            )

        # Create DELIVERY VAN user if not exists
        cursor = db.execute('SELECT * FROM users WHERE email = ?', ('van@water.com',))
        if cursor.fetchone() is None:
            hashed_password = generate_password_hash('van123')
            db.execute(
                'INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, ?)',
                ('Delivery Van', 'van@water.com', '0000000000', hashed_password, 'van')
            )

        db.commit()

# --- Daily Subscription Automation ---
def generate_subscription_orders():
    """Checks and generates orders for subscriptions if not done today"""
    db = get_db()
    today_str = date.today().isoformat()
    
    # Get all subscriptions
    subscriptions = db.execute('SELECT * FROM subscriptions').fetchall()
    
    for sub in subscriptions:
        # Check if already generated today
        # We need a column last_generated_date in subscriptions. 
        # Since I handle migration in __main__, I assume it exists or will handle error gracefully if I add migration logic there.
        # But efficiently, let's just check if we have a subscription order for this user for today in orders table.
        # This is safer if we don't strictly rely on a new column immediately, but the plan asked for a column.
        # I will use the column approach as planned.
        
        last_gen = sub['last_generated_date'] if 'last_generated_date' in sub.keys() else None
        
        if last_gen != today_str:
            # Get location details
            loc = db.execute('SELECT * FROM locations WHERE id = ?', (sub['location_id'],)).fetchone()
            address = loc['address'] if loc else "Unknown"
            city = loc['city'] if loc else "Unknown"

            # Generate Order
            db.execute(
                '''INSERT INTO orders 
                   (user_id, bottle_type, quantity, total_price, order_type, status, order_date, address, city) 
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)''',
                (sub['user_id'], sub['bottle_type'], sub['quantity'], sub['total_price'], 'subscription', 'pending', address, city)
            )
            
            # Update last_generated_date
            db.execute('UPDATE subscriptions SET last_generated_date = ? WHERE id = ?', (today_str, sub['id']))
            
    db.commit()

@app.before_request
def before_request():
    """Run daily checks before handling request"""
    if request.endpoint and 'static' not in request.endpoint:
        # simple throttling: only checking, logic inside is idempotent per day
        # In production this might be heavy, but for this app it is fine.
        if 'water_supply.db' in os.listdir('.'): # simple check to ensure db exists
             # We need to ensure we are in an app context with DB
             pass # Logic moved to explicit call to avoid circular dependency issues during startup
             # actually, g.db is available here via get_db()
             try:
                 generate_subscription_orders()
             except Exception:
                 # Likely migration hasn't run yet or table issue, ignore to let init handle it
                 pass


# Helper function to check if user is logged in
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to check if user is admin
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to check if user is delivery
def delivery_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        if session.get('user_role') != 'delivery':
            flash('Delivery access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function to check if user is VAN
def van_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        if session.get('user_role') != 'van':
            flash('Delivery Van access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'admin':
            return redirect(url_for('admin_panel'))
        elif role == 'delivery':
            return redirect(url_for('delivery_panel'))
        elif role == 'van':
            return redirect(url_for('van_panel'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        if not name or not email or not phone or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))

        db = get_db()

        # Check if email already exists
        existing_user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('register'))

        # Create user
        hashed_password = generate_password_hash(password)
        db.execute(
            'INSERT INTO users (name, email, phone, password, role) VALUES (?, ?, ?, ?, ?)',
            (name, email, phone, hashed_password, 'user')
        )
        db.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']

            if user['role'] == 'admin':
                return redirect(url_for('admin_panel'))
            elif user['role'] == 'delivery':
                return redirect(url_for('delivery_panel'))
            elif user['role'] == 'van':
                return redirect(url_for('van_panel'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user_id = session['user_id']
    user_role = session.get('user_role')
    
    # Redirect based on role if they hit /dashboard manually
    if user_role == 'delivery':
        return redirect(url_for('delivery_panel'))
    elif user_role == 'admin':
        return redirect(url_for('admin_panel'))
    elif user_role == 'van':
        return redirect(url_for('van_panel'))

    # Get statistics
    orders = db.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,)).fetchall()
    total_orders = len(orders)
    total_spent = sum(order['total_price'] for order in orders)

    locations_count = db.execute('SELECT COUNT(*) as count FROM locations WHERE user_id = ?', (user_id,)).fetchone()['count']

    # Get recent 5 orders
    recent_orders = db.execute(
        'SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC LIMIT 5',
        (user_id,)
    ).fetchall()

    return render_template('dashboard.html',
                         total_orders=total_orders,
                         total_spent=total_spent,
                         locations_count=locations_count,
                         recent_orders=recent_orders)

@app.route('/locations', methods=['GET', 'POST'])
@login_required
def locations():
    db = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        label = request.form.get('label', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        is_default = 1 if request.form.get('is_default') else 0

        if not label or not address or not city:
            flash('All fields are required', 'error')
            return redirect(url_for('locations'))

        # If setting as default, unset other defaults
        if is_default:
            db.execute('UPDATE locations SET is_default = 0 WHERE user_id = ?', (user_id,))

        db.execute(
            'INSERT INTO locations (user_id, label, address, city, is_default) VALUES (?, ?, ?, ?, ?)',
            (user_id, label, address, city, is_default)
        )
        db.commit()

        flash('Location added successfully', 'success')
        return redirect(url_for('locations'))

    user_locations = db.execute('SELECT * FROM locations WHERE user_id = ?', (user_id,)).fetchall()
    return render_template('locations.html', locations=user_locations)

@app.route('/location/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    db = get_db()
    user_id = session['user_id']

    location = db.execute('SELECT * FROM locations WHERE id = ? AND user_id = ?', (location_id, user_id)).fetchone()
    if not location:
        flash('Location not found', 'error')
        return redirect(url_for('locations'))

    if request.method == 'POST':
        label = request.form.get('label', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        is_default = 1 if request.form.get('is_default') else 0

        if not label or not address or not city:
            flash('All fields are required', 'error')
            return redirect(url_for('edit_location', location_id=location_id))

        # If setting as default, unset other defaults
        if is_default:
            db.execute('UPDATE locations SET is_default = 0 WHERE user_id = ?', (user_id,))

        db.execute(
            'UPDATE locations SET label = ?, address = ?, city = ?, is_default = ? WHERE id = ?',
            (label, address, city, is_default, location_id)
        )
        db.commit()

        flash('Location updated successfully', 'success')
        return redirect(url_for('locations'))

    return render_template('edit_location.html', location=location)

@app.route('/location/<int:location_id>/delete', methods=['POST'])
@login_required
def delete_location(location_id):
    db = get_db()
    user_id = session['user_id']

    location = db.execute('SELECT * FROM locations WHERE id = ? AND user_id = ?', (location_id, user_id)).fetchone()
    if not location:
        flash('Location not found', 'error')
        return redirect(url_for('locations'))

    db.execute('DELETE FROM locations WHERE id = ?', (location_id,))
    db.commit()

    flash('Location deleted successfully', 'success')
    return redirect(url_for('locations'))

@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    db = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        bottle_type = request.form.get('bottle_type', '')
        quantity = request.form.get('quantity', '0')
        location_id = request.form.get('location_id', '')

        if not bottle_type or not quantity or not location_id:
            flash('Please fill all fields', 'error')
            return redirect(url_for('order'))

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash('Invalid quantity', 'error')
            return redirect(url_for('order'))

        price_per_unit = 50 if bottle_type == '2 Liter' else 200
        total_price = price_per_unit * quantity
        
        # Fetch location details to save with order
        loc = db.execute('SELECT * FROM locations WHERE id = ?', (location_id,)).fetchone()
        address = loc['address'] if loc else "Unknown"
        city = loc['city'] if loc else "Unknown"

        db.execute(
            'INSERT INTO orders (user_id, bottle_type, quantity, total_price, order_type, status, address, city) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, bottle_type, quantity, total_price, 'single', 'pending', address, city)
        )
        db.commit()

        flash('Order placed successfully! Waiting for delivery acceptance.', 'success')
        return redirect(url_for('order_history'))

    user_locations = db.execute('SELECT * FROM locations WHERE user_id = ?', (user_id,)).fetchall()
    return render_template('order.html', locations=user_locations)

@app.route('/order_history')
@login_required
def order_history():
    db = get_db()
    user_id = session['user_id']

    orders = db.execute(
        'SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC',
        (user_id,)
    ).fetchall()

    return render_template('order_history.html', orders=orders)

@app.route('/subscription', methods=['GET', 'POST'])
@login_required
def subscription():
    db = get_db()
    user_id = session['user_id']

    if request.method == 'POST':
        bottle_type = request.form.get('bottle_type', '')
        quantity = request.form.get('quantity', '0')
        location_id = request.form.get('location_id', '')

        if not bottle_type or not quantity or not location_id:
            flash('Please fill all fields', 'error')
            return redirect(url_for('subscription'))

        try:
            quantity = int(quantity)
            location_id = int(location_id)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash('Invalid input', 'error')
            return redirect(url_for('subscription'))

        price_per_unit = 50 if bottle_type == '2 Liter' else 200
        total_price = price_per_unit * quantity

        existing = db.execute('SELECT * FROM subscriptions WHERE user_id = ?', (user_id,)).fetchone()

        if existing:
            db.execute(
                'UPDATE subscriptions SET bottle_type = ?, quantity = ?, total_price = ?, location_id = ? WHERE user_id = ?',
                (bottle_type, quantity, total_price, location_id, user_id)
            )
            flash('Subscription updated successfully!', 'success')
        else:
            db.execute(
                'INSERT INTO subscriptions (user_id, bottle_type, quantity, total_price, location_id) VALUES (?, ?, ?, ?, ?)',
                (user_id, bottle_type, quantity, total_price, location_id)
            )
            flash('Subscription created successfully!', 'success')

        # SYNC: Update today's pending order if it exists
        # Fetch new location details
        new_loc = db.execute('SELECT * FROM locations WHERE id = ?', (location_id,)).fetchone()
        new_addr = new_loc['address'] if new_loc else "Unknown"
        new_city = new_loc['city'] if new_loc else "Unknown"

        db.execute('''
            UPDATE orders 
            SET bottle_type = ?, quantity = ?, total_price = ?, address = ?, city = ?
            WHERE user_id = ? 
            AND status = 'pending' 
            AND order_type = 'subscription'
            AND date(order_date) = date('now')
        ''', (bottle_type, quantity, total_price, new_addr, new_city, user_id))

        db.commit()
        return redirect(url_for('subscription'))

    user_locations = db.execute('SELECT * FROM locations WHERE user_id = ?', (user_id,)).fetchall()
    current_subscription = db.execute('SELECT * FROM subscriptions WHERE user_id = ?', (user_id,)).fetchone()

    return render_template('subscription.html', locations=user_locations, subscription=current_subscription)

@app.route('/admin')
@admin_required
def admin_panel():
    db = get_db()

    users = db.execute('SELECT * FROM users WHERE role = "user"').fetchall()

    all_orders = db.execute(
        'SELECT orders.*, users.name as user_name FROM orders JOIN users ON orders.user_id = users.id ORDER BY orders.order_date DESC'
    ).fetchall()

    total_revenue = db.execute('SELECT SUM(total_price) as total FROM orders').fetchone()['total'] or 0

    return render_template('admin.html', users=users, orders=all_orders, total_revenue=total_revenue)

@app.route('/admin/clear_db', methods=['POST'])
@admin_required
def clear_db():
    db = get_db()
    
    try:
        db.execute('DELETE FROM orders')
        db.execute('DELETE FROM subscriptions')
        db.execute('DELETE FROM locations')
        db.execute('DELETE FROM users WHERE role != "admin" AND role != "delivery" AND role != "van"')
        db.commit()
        flash('Database refreshed successfully!', 'success')
        
    except Exception as e:
        db.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
        
    return redirect(url_for('admin_panel'))

@app.route('/delivery')
@delivery_required
def delivery_panel():
    """DELIVERY BOY: Only sees single (on-demand) orders"""
    db = get_db()
    delivery_id = session['user_id']
    
    pending_orders = db.execute(
        '''SELECT orders.*, users.name as user_name, users.phone, users.email
           FROM orders 
           JOIN users ON orders.user_id = users.id 
           WHERE orders.status = "pending" AND orders.order_type = "single"
           ORDER BY orders.order_date ASC'''
    ).fetchall()
    
    my_deliveries = db.execute(
        '''SELECT orders.*, users.name as user_name, users.phone, users.email
           FROM orders 
           JOIN users ON orders.user_id = users.id 
           WHERE orders.status = "out_for_delivery" 
           AND orders.delivery_boy_id = ?
           ORDER BY orders.order_date ASC''',
        (delivery_id,)
    ).fetchall()
    
    my_history = db.execute(
        '''SELECT orders.*, users.name as user_name 
           FROM orders 
           JOIN users ON orders.user_id = users.id 
           WHERE orders.status = "delivered" AND orders.delivery_boy_id = ?
           ORDER BY orders.order_date DESC LIMIT 10''',
        (delivery_id,)
    ).fetchall()
    
    return render_template('deliveryboy.html', 
                         pending_orders=pending_orders, 
                         my_deliveries=my_deliveries,
                         my_history=my_history)

@app.route('/van')
@van_required
def van_panel():
    """DELIVERY VAN: Only sees subscription orders"""
    db = get_db()
    van_id = session['user_id']
    
    # Check automated orders (just in case they weren't generated yet for some reason)
    # But before_request handled it.
    
    pending_orders = db.execute(
        '''SELECT orders.*, users.name as user_name, users.phone, users.email
           FROM orders 
           JOIN users ON orders.user_id = users.id 
           WHERE orders.status = "pending" AND orders.order_type = "subscription"
           ORDER BY orders.order_date ASC'''
    ).fetchall()
    
    my_deliveries = db.execute(
        '''SELECT orders.*, users.name as user_name, users.phone, users.email
           FROM orders 
           JOIN users ON orders.user_id = users.id 
           WHERE orders.status = "out_for_delivery" 
           AND orders.delivery_boy_id = ?
           ORDER BY orders.order_date ASC''',
        (van_id,)
    ).fetchall()
    
    my_history = db.execute(
        '''SELECT orders.*, users.name as user_name 
           FROM orders 
           JOIN users ON orders.user_id = users.id 
           WHERE orders.status = "delivered" AND orders.delivery_boy_id = ?
           ORDER BY orders.order_date DESC LIMIT 10''',
        (van_id,)
    ).fetchall()
    
    return render_template('delivery_van.html', 
                         pending_orders=pending_orders, 
                         my_deliveries=my_deliveries,
                         my_history=my_history)

@app.route('/delivery/accept/<int:order_id>', methods=['POST'])
@login_required
def accept_order(order_id):
    # Works for both Delivery Boy and Van
    db = get_db()
    user_id = session['user_id']
    role = session['user_role']

    if role not in ['delivery', 'van']:
        flash('Permission denied', 'error')
        return redirect(url_for('dashboard'))
    
    order = db.execute('SELECT status FROM orders WHERE id = ?', (order_id,)).fetchone()
    if order and order['status'] == 'pending':
        db.execute(
            'UPDATE orders SET status = "out_for_delivery", delivery_boy_id = ? WHERE id = ?',
            (user_id, order_id)
        )
        db.commit()
        flash('Order accepted! Please deliver it.', 'success')
    else:
        flash('Order is no longer available.', 'error')
        
    if role == 'van':
        return redirect(url_for('van_panel'))
    return redirect(url_for('delivery_panel'))

@app.route('/delivery/complete/<int:order_id>', methods=['POST'])
@login_required
def complete_order(order_id):
    # Works for both Delivery Boy and Van
    db = get_db()
    user_id = session['user_id']
    role = session['user_role']
    
    if role not in ['delivery', 'van']:
        flash('Permission denied', 'error')
        return redirect(url_for('dashboard'))
    
    order = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    if order and order['delivery_boy_id'] == user_id and order['status'] == 'out_for_delivery':
        db.execute(
            'UPDATE orders SET status = "delivered" WHERE id = ?',
            (order_id,)
        )
        db.commit()
        flash('Order marked as delivered! Good job.', 'success')
    else:
        flash('Invalid order operation.', 'error')
        
    if role == 'van':
        return redirect(url_for('van_panel'))
    return redirect(url_for('delivery_panel'))

@app.route('/toggle_theme')
def toggle_theme():
    current_theme = session.get('theme', 'dark')
    session['theme'] = 'light' if current_theme == 'dark' else 'dark'
    referer = request.referrer
    if referer:
        return redirect(referer)
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    
    # MIGRATION logic (your existing code stays)
    with app.app_context():
        db = get_db()
        try:
            db.execute('SELECT delivery_boy_id FROM orders LIMIT 1')
        except sqlite3.OperationalError:
            print("Migrating: Adding delivery_boy_id to orders...")
            try:
                db.execute('ALTER TABLE orders ADD COLUMN delivery_boy_id INTEGER REFERENCES users(id)')
                db.commit()
            except Exception as e: print(f"Migrate Error: {e}")

        try:
            db.execute('SELECT address FROM orders LIMIT 1')
        except sqlite3.OperationalError:
            print("Migrating: Adding address and city to orders...")
            try:
                db.execute('ALTER TABLE orders ADD COLUMN address TEXT')
                db.execute('ALTER TABLE orders ADD COLUMN city TEXT')
                db.commit()
            except Exception as e: print(f"Migrate Error: {e}")

        try:
            db.execute('SELECT last_generated_date FROM subscriptions LIMIT 1')
        except sqlite3.OperationalError:
            print("Migrating: Adding last_generated_date to subscriptions...")
            try:
                db.execute('ALTER TABLE subscriptions ADD COLUMN last_generated_date TEXT')
                db.commit()
            except Exception as e: print(f"Migrate Error: {e}")

        init_db()

    # Use Render's PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)