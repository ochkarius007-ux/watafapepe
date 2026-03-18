from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///helpdesk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user', 'specialist', 'admin'
    phone = db.Column(db.String(20))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, closed
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    source = db.Column(db.String(20), default='web')  # web, telegram, max
    external_user_id = db.Column(db.String(100))  # For Telegram/MAX user IDs
    external_chat_id = db.Column(db.String(100))  # For Telegram/MAX chat IDs
    
    user = db.relationship('User', foreign_keys=[user_id], backref='created_tickets')
    specialist = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tickets')
    messages = db.relationship('Message', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_from_user = db.Column(db.Boolean, default=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    user = db.relationship('User', backref='messages')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role in ['specialist', 'admin']:
            return redirect(url_for('dashboard'))
        return redirect(url_for('my_tickets'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Неверное имя пользователя или пароль', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован', 'error')
            return render_template('register.html')
        
        user = User(username=username, email=email, phone=phone, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['specialist', 'admin']:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status', 'all')
    query = Ticket.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    tickets = query.order_by(Ticket.updated_at.desc()).all()
    return render_template('dashboard.html', tickets=tickets, status_filter=status_filter)

@app.route('/my_tickets')
@login_required
def my_tickets():
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.created_at.desc()).all()
    return render_template('my_tickets.html', tickets=tickets)

@app.route('/ticket/new', methods=['GET', 'POST'])
@login_required
def new_ticket():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority', 'medium')
        
        ticket = Ticket(
            title=title,
            description=description,
            priority=priority,
            user_id=current_user.id,
            source='web'
        )
        db.session.add(ticket)
        db.session.commit()
        
        # Add initial message
        message = Message(
            content=description,
            ticket_id=ticket.id,
            user_id=current_user.id,
            is_from_user=True
        )
        db.session.add(message)
        db.session.commit()
        
        flash('Заявка создана успешно!', 'success')
        return redirect(url_for('ticket_detail', ticket_id=ticket.id))
    return render_template('new_ticket.html')

@app.route('/ticket/<int:ticket_id>')
@login_required
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Check permissions
    if current_user.role not in ['specialist', 'admin']:
        if ticket.user_id != current_user.id:
            flash('Доступ запрещен', 'error')
            return redirect(url_for('index'))
    
    # Get all specialists for assignment
    specialists = User.query.filter(User.role.in_(['specialist', 'admin'])).all()
    
    return render_template('ticket_detail.html', ticket=ticket, specialists=specialists)

@app.route('/ticket/<int:ticket_id>/message', methods=['POST'])
@login_required
def add_message(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    content = request.form.get('content')
    
    if not content:
        flash('Сообщение не может быть пустым', 'error')
        return redirect(url_for('ticket_detail', ticket_id=ticket.id))
    
    message = Message(
        content=content,
        ticket_id=ticket.id,
        user_id=current_user.id,
        is_from_user=(current_user.role == 'user')
    )
    db.session.add(message)
    db.session.commit()
    
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash('Сообщение добавлено', 'success')
    return redirect(url_for('ticket_detail', ticket_id=ticket.id))

@app.route('/ticket/<int:ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    if current_user.role not in ['specialist', 'admin']:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    ticket = Ticket.query.get_or_404(ticket_id)
    specialist_id = request.form.get('specialist_id')
    
    if specialist_id:
        ticket.assigned_to = int(specialist_id)
        ticket.status = 'in_progress'
        db.session.commit()
        flash('Заявка назначена', 'success')
    
    return redirect(url_for('ticket_detail', ticket_id=ticket.id))

@app.route('/ticket/<int:ticket_id>/status', methods=['POST'])
@login_required
def update_status(ticket_id):
    if current_user.role not in ['specialist', 'admin']:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    ticket = Ticket.query.get_or_404(ticket_id)
    status = request.form.get('status')
    
    if status in ['open', 'in_progress', 'resolved', 'closed']:
        ticket.status = status
        db.session.commit()
        flash(f'Статус изменен на {status}', 'success')
    
    return redirect(url_for('ticket_detail', ticket_id=ticket.id))

@app.route('/ticket/<int:ticket_id>/close', methods=['POST'])
@login_required
def close_ticket(ticket_id):
    if current_user.role not in ['specialist', 'admin']:
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = 'closed'
    db.session.commit()
    flash('Заявка закрыта', 'success')
    return redirect(url_for('dashboard'))

# API for bots
@app.route('/api/ticket/create', methods=['POST'])
def api_create_ticket():
    data = request.json
    external_user_id = data.get('external_user_id')
    external_chat_id = data.get('external_chat_id')
    source = data.get('source', 'web')
    title = data.get('title', 'Заявка от пользователя')
    description = data.get('description')
    phone = data.get('phone')
    
    if not description:
        return jsonify({'error': 'Описание обязательно'}), 400
    
    # Find or create user
    user = User.query.filter_by(
        username=f"{source}_{external_user_id}"
    ).first()
    
    if not user:
        user = User(
            username=f"{source}_{external_user_id}",
            email=f"{source}_{external_user_id}@temp.local",
            role='user',
            phone=phone
        )
        user.set_password('temp_password')
        db.session.add(user)
        db.session.commit()
    
    ticket = Ticket(
        title=title,
        description=description,
        user_id=user.id,
        source=source,
        external_user_id=external_user_id,
        external_chat_id=external_chat_id
    )
    db.session.add(ticket)
    db.session.commit()
    
    message = Message(
        content=description,
        ticket_id=ticket.id,
        user_id=user.id,
        is_from_user=True
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'ticket_id': ticket.id,
        'status': 'created',
        'message': 'Заявка создана. Специалист свяжется с вами по указанному телефону.'
    })

@app.route('/api/ticket/<int:ticket_id>/message', methods=['POST'])
def api_add_message(ticket_id):
    data = request.json
    external_user_id = data.get('external_user_id')
    external_chat_id = data.get('external_chat_id')
    content = data.get('content')
    source = data.get('source', 'web')
    
    if not content:
        return jsonify({'error': 'Сообщение обязательно'}), 400
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verify user
    user = User.query.filter_by(
        username=f"{source}_{external_user_id}"
    ).first()
    
    if not user or user.id != ticket.user_id:
        return jsonify({'error': 'Пользователь не найден'}), 404
    
    message = Message(
        content=content,
        ticket_id=ticket.id,
        user_id=user.id,
        is_from_user=True
    )
    db.session.add(message)
    db.session.commit()
    
    ticket.updated_at = datetime.utcnow()
    if ticket.external_chat_id:
        ticket.external_chat_id = external_chat_id
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Сообщение добавлено'
    })

@app.route('/api/ticket/<int:ticket_id>/messages', methods=['GET'])
def api_get_messages(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    messages = ticket.messages.order_by(Message.created_at.asc()).all()
    
    return jsonify({
        'messages': [
            {
                'id': m.id,
                'content': m.content,
                'created_at': m.created_at.isoformat(),
                'is_from_user': m.is_from_user
            }
            for m in messages
        ]
    })

# Initialize database
with app.app_context():
    db.create_all()
    
    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@helpdesk.local', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created: admin / admin123")
    
    # Create specialist user if not exists
    specialist = User.query.filter_by(username='specialist').first()
    if not specialist:
        specialist = User(username='specialist', email='specialist@helpdesk.local', role='specialist')
        specialist.set_password('spec123')
        db.session.add(specialist)
        db.session.commit()
        print("Specialist user created: specialist / spec123")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
