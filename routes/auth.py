import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor
from database import get_db_connection

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = username
                logger.info(f"User {username} logged in successfully")
                return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Database login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
        finally:
            if conn:
                conn.close()
        
        flash('Invalid username or password')
        logger.warning(f"Failed login attempt for user: {username}")
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already exists', 'error')
                return render_template('register.html')
            
            # Insert new user
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                (username, password_hash)
            )
            user_id = cursor.fetchone()['id']
            conn.commit()
            
            # Log the user in
            session['user_id'] = user_id
            session['username'] = username
            
            flash('Registration successful! You are now logged in.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Database registration error: {e}")
            flash('Registration failed due to a database error. Please try again.', 'error')
            return render_template('register.html')
        finally:
            if conn:
                conn.close()

    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login')) 