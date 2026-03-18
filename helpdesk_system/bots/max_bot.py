import os
import logging
import configparser
from flask import Flask, request, jsonify
import requests

# Load configuration from config.ini
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini'))

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration from config.ini
MAX_BOT_TOKEN = config.get('MAX', 'bot_token', fallback='YOUR_MAX_BOT_TOKEN')
MAX_API_URL = config.get('MAX', 'api_url', fallback='https://api.max-platform.ru')
HELPDESK_API_URL = os.getenv('HELPDESK_API_URL', 'http://localhost:5000')

# Auto-reply messages
AUTO_REPLY_MESSAGES = {
    'greeting': """👋 Здравствуйте! Я бот технической поддержки МООНД.

⚠️ Важно: Заявки с персональными данными не будут обрабатываться. 
Пожалуйста, укажите в общих чертах, что требуется сделать. 
Специалист сразу свяжется с вами по указанному телефону.

Для создания заявки отправьте описание проблемы.""",
    
    'ticket_created': """✅ Ваша заявка #{} создана!

Специалист свяжется с вами по указанному телефону в ближайшее время.

Для добавления сообщения к заявке просто отправьте его в чат.""",
    
    'message_added': """✅ Ваше сообщение добавлено к заявке #{}.

Специалист ответит вам в ближайшее время.""",
    
    'help': """📖 Помощь:

Приветствие - Начать работу с ботом
Новая заявка - Создать новую заявку
Статус - Проверить статус последней заявки
Помощь - Показать это сообщение

Просто отправьте текст, чтобы создать новую заявку или добавить сообщение к последней."""
}

# User sessions storage (in production, use Redis or database)
user_sessions = {}


@app.route('/max/webhook', methods=['POST'])
def max_webhook():
    """Handle incoming messages from MAX bot"""
    try:
        data = request.json
        logger.info(f"Received from MAX: {data}")
        
        user_id = data.get('user_id')
        chat_id = data.get('chat_id')
        message_text = data.get('message', '')
        command = data.get('command')
        
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        
        response_message = ""
        
        # Handle commands
        if command == 'start' or message_text.lower() in ['приветствие', 'привет', 'старт']:
            response_message = AUTO_REPLY_MESSAGES['greeting']
        
        elif command == 'help' or message_text.lower() in ['помощь', 'help']:
            response_message = AUTO_REPLY_MESSAGES['help']
        
        elif command == 'new' or message_text.lower() in ['новая заявка', 'создать заявку']:
            response_message = "📝 Пожалуйста, опишите вашу проблему.\n\n⚠️ Не указывайте персональные данные!"
            user_sessions[user_id] = {'state': 'creating_ticket'}
        
        elif command == 'status' or message_text.lower() in ['статус', 'status']:
            response_message = handle_status_command(user_id)
        
        else:
            # Handle regular messages
            response_message = handle_message(user_id, chat_id, message_text)
        
        return jsonify({
            'response': response_message,
            'user_id': user_id
        })
    
    except Exception as e:
        logger.error(f"Error processing MAX webhook: {e}")
        return jsonify({'error': str(e)}), 500


def handle_status_command(user_id):
    """Handle status command"""
    try:
        response = requests.get(f"{HELPDESK_API_URL}/api/user/tickets/{user_id}")
        if response.status_code == 200:
            tickets = response.json().get('tickets', [])
            if tickets:
                last_ticket = tickets[-1]
                message = f"Последняя заявка #{last_ticket['id']}\n"
                message += f"Статус: {last_ticket['status']}\n"
                message += f"Заголовок: {last_ticket['title']}\n"
                message += f"Создана: {last_ticket['created_at']}"
                return message
            else:
                return "У вас нет заявок."
        else:
            return "Не удалось получить статус заявок."
    except Exception as e:
        logger.error(f"Error getting ticket status: {e}")
        return "Произошла ошибка при получении статуса."


def handle_message(user_id, chat_id, message_text):
    """Handle incoming message"""
    session = user_sessions.get(user_id, {})
    
    if session.get('state') == 'creating_ticket':
        return create_ticket(user_id, chat_id, message_text)
    else:
        return handle_existing_or_new_ticket(user_id, chat_id, message_text)


def create_ticket(user_id, chat_id, description):
    """Create a new ticket"""
    try:
        payload = {
            'external_user_id': user_id,
            'external_chat_id': chat_id,
            'source': 'max',
            'title': f'Заявка от MAX пользователя {user_id}',
            'description': description,
            'phone': user_id  # Use user_id as phone placeholder
        }
        
        response = requests.post(f"{HELPDESK_API_URL}/api/ticket/create", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            ticket_id = data.get('ticket_id')
            
            # Store ticket info in session
            user_sessions[user_id] = {
                'state': 'active',
                'current_ticket_id': ticket_id
            }
            
            return AUTO_REPLY_MESSAGES['ticket_created'].format(ticket_id) + "\n\n" + AUTO_REPLY_MESSAGES['greeting']
        else:
            logger.error(f"Failed to create ticket: {response.text}")
            return "❌ Ошибка при создании заявки. Попробуйте позже."
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        return "❌ Произошла ошибка. Попробуйте позже."


def handle_existing_or_new_ticket(user_id, chat_id, message_text):
    """Handle message for existing ticket or create new one"""
    session = user_sessions.get(user_id, {})
    ticket_id = session.get('current_ticket_id')
    
    if ticket_id:
        try:
            payload = {
                'external_user_id': user_id,
                'external_chat_id': chat_id,
                'source': 'max',
                'content': message_text
            }
            
            response = requests.post(f"{HELPDESK_API_URL}/api/ticket/{ticket_id}/message", json=payload)
            
            if response.status_code == 200:
                return AUTO_REPLY_MESSAGES['message_added'].format(ticket_id)
            else:
                # Ticket might be closed, create new one
                return create_ticket(user_id, chat_id, message_text)
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return create_ticket(user_id, chat_id, message_text)
    else:
        # No active ticket, create new one
        return create_ticket(user_id, chat_id, message_text)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
