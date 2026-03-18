import os
import logging
from dotenv import load_dotenv
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
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
    
    'status_update': """📋 Статус вашей заявки #{} изменен на: {}""",
    
    'help': """📖 Помощь:

/start - Начать работу с ботом
/new - Создать новую заявку
/status - Проверить статус последней заявки
/help - Показать это сообщение

Просто отправьте текст, чтобы создать новую заявку или добавить сообщение к последней."""
}


class TelegramBot:
    def __init__(self):
        self.application = None
        self.user_sessions = {}  # Store user session data
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(AUTO_REPLY_MESSAGES['greeting'])
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(AUTO_REPLY_MESSAGES['help'])
    
    async def new_ticket_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new command"""
        await update.message.reply_text(
            "📝 Пожалуйста, опишите вашу проблему.\n\n"
            "⚠️ Не указывайте персональные данные!"
        )
        self.user_sessions[update.effective_user.id] = {'state': 'creating_ticket'}
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = str(update.effective_user.id)
        
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
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text("У вас нет заявок.")
            else:
                await update.message.reply_text("Не удалось получить статус заявок.")
        except Exception as e:
            logger.error(f"Error getting ticket status: {e}")
            await update.message.reply_text("Произошла ошибка при получении статуса.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        message_text = update.message.text
        
        if not message_text:
            return
        
        # Check if user is creating a ticket
        session = self.user_sessions.get(user_id, {})
        
        if session.get('state') == 'creating_ticket':
            # Create new ticket
            await self.create_ticket(update, message_text, user_id, chat_id)
        else:
            # Try to add message to last open ticket or create new one
            await self.handle_existing_or_new_ticket(update, message_text, user_id, chat_id)
    
    async def create_ticket(self, update: Update, description: str, user_id: str, chat_id: str):
        """Create a new ticket"""
        try:
            phone = update.effective_user.username or "не указан"
            
            payload = {
                'external_user_id': user_id,
                'external_chat_id': chat_id,
                'source': 'telegram',
                'title': f'Заявка от Telegram пользователя {user_id}',
                'description': description,
                'phone': phone
            }
            
            response = requests.post(f"{HELPDESK_API_URL}/api/ticket/create", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                ticket_id = data.get('ticket_id')
                
                # Store ticket info in session
                self.user_sessions[user_id] = {
                    'state': 'active',
                    'current_ticket_id': ticket_id
                }
                
                await update.message.reply_text(
                    AUTO_REPLY_MESSAGES['ticket_created'].format(ticket_id) + "\n\n" +
                    AUTO_REPLY_MESSAGES['greeting']
                )
            else:
                await update.message.reply_text("❌ Ошибка при создании заявки. Попробуйте позже.")
                logger.error(f"Failed to create ticket: {response.text}")
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_existing_or_new_ticket(self, update: Update, message_text: str, user_id: str, chat_id: str):
        """Handle message for existing ticket or create new one"""
        session = self.user_sessions.get(user_id, {})
        ticket_id = session.get('current_ticket_id')
        
        if ticket_id:
            # Add message to existing ticket
            try:
                payload = {
                    'external_user_id': user_id,
                    'external_chat_id': chat_id,
                    'source': 'telegram',
                    'content': message_text
                }
                
                response = requests.post(f"{HELPDESK_API_URL}/api/ticket/{ticket_id}/message", json=payload)
                
                if response.status_code == 200:
                    await update.message.reply_text(
                        AUTO_REPLY_MESSAGES['message_added'].format(ticket_id)
                    )
                else:
                    # Ticket might be closed, create new one
                    await self.create_ticket(update, message_text, user_id, chat_id)
            except Exception as e:
                logger.error(f"Error adding message: {e}")
                await self.create_ticket(update, message_text, user_id, chat_id)
        else:
            # No active ticket, create new one
            await self.create_ticket(update, message_text, user_id, chat_id)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        if update and update.message:
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    def run(self):
        """Run the bot"""
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("new", self.new_ticket_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("Starting Telegram bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()
