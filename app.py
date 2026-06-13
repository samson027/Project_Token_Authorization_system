# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, Token
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = 'your-super-secret-key-change-in-production'

# PythonAnywhere MySQL Configuration
# REPLACE: yourusername, yourpassword with YOUR actual credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://lota:ramya%4066@lota.mysql.pythonanywhere-services.com/lota$gatepassdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 280}

db.init_app(app)

# Create tables on first run
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Homepage with navigation"""
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin panel: Generate tokens and view claimed tokens"""
    if request.method == 'POST':
        try:
            quantity = int(request.form['quantity'])
            duration_hours = int(request.form['duration'])
            
            if quantity < 1 or quantity > 100:
                flash('Quantity must be between 1 and 100.', 'error')
                return redirect(url_for('admin'))
            
            if duration_hours < 1 or duration_hours > 168:
                flash('Duration must be between 1 and 168 hours.', 'error')
                return redirect(url_for('admin'))
            
            # Generate batch ID for this group of tokens
            batch_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
            
            generated_codes = []
            for _ in range(quantity):
                token_code = Token.generate_token_code()
                new_token = Token(
                    code=token_code,
                    batch_id=batch_id,
                    expires_at=expires_at,
                    is_active=True
                )
                db.session.add(new_token)
                generated_codes.append(token_code)
            
            db.session.commit()
            flash(f'Successfully generated {quantity} tokens (Batch: {batch_id[:8]}) valid for {duration_hours} hours.', 'success')
            flash(f'Tokens: {", ".join(generated_codes)}', 'info')
            
        except ValueError:
            flash('Invalid input. Please enter valid numbers.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error generating tokens: {str(e)}', 'error')
    
    # Fetch claimed tokens (assigned_user is not NULL)
    claimed_tokens = Token.query.filter(Token.assigned_user.isnot(None)).order_by(Token.created_at.desc()).all()
    
    # Fetch all tokens for management view
    all_tokens = Token.query.order_by(Token.created_at.desc()).all()
    
    return render_template('admin.html', claimed_tokens=claimed_tokens, all_tokens=all_tokens)

@app.route('/admin/toggle/<int:token_id>')
def toggle_token(token_id):
    """Toggle is_active status for a token"""
    token = Token.query.get_or_404(token_id)
    token.is_active = not token.is_active
    db.session.commit()
    status = "activated" if token.is_active else "deactivated"
    flash(f'Token {token.code} has been {status}.', 'success')
    return redirect(url_for('admin'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login with token and username"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        token_code = request.form['token'].strip().upper()
        
        if not username or not token_code:
            flash('Username and token are required.', 'error')
            return render_template('login.html')
        
        # Find token in database
        token = Token.query.filter_by(code=token_code).first()
        
        if not token:
            flash('Invalid token code.', 'error')
            return render_template('login.html')
        
        # Check if token is valid
        if not token.is_valid():
            if not token.is_active:
                flash('Token has been deactivated by admin.', 'error')
            else:
                flash('Token has expired.', 'error')
            return render_template('login.html')
        
        # First Use Logic: Token is unassigned
        if not token.is_assigned():
            token.assigned_user = username
            db.session.commit()
            session['username'] = username
            session['token_code'] = token_code
            flash(f'Welcome {username}! Token {token_code} has been assigned to you.', 'success')
            return redirect(url_for('dashboard'))
        
        # Re-Login Logic: Token already assigned
        elif token.assigned_user == username:
            session['username'] = username
            session['token_code'] = token_code
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        
        # Token claimed by someone else
        else:
            flash(f'Token {token_code} is already assigned to another user.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """User dashboard after successful login"""
    if 'username' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('login'))
    
    # Fetch user's token details
    token = Token.query.filter_by(code=session.get('token_code')).first()
    
    return render_template('dashboard.html', user=session['username'], token=token)

@app.route('/logout')
def logout():
    """User logout - clears session"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye {username}! You have been logged out.', 'success')
    return redirect(url_for('index'))

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500

if __name__ == '__main__':
    app.run(debug=True)
