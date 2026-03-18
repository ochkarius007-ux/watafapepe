# Helpdesk система МООНД

Система обработки технических заявок с поддержкой веб-интерфейса, Telegram и MAX ботов.

## Структура проекта

```
helpdesk_system/
├── app.py                 # Основное Flask приложение
├── requirements.txt       # Зависимости Python
├── README.md             # Этот файл
├── templates/            # HTML шаблоны
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── my_tickets.html
│   ├── new_ticket.html
│   └── ticket_detail.html
└── bots/                 # Боты
    ├── telegram_bot.py   # Telegram бот
    └── max_bot.py        # MAX бот
```

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите основное приложение:
```bash
python app.py
```

3. Запустите Telegram бота (предварительно настройте токен):
```bash
export TELEGRAM_BOT_TOKEN='your_token'
export HELPDESK_API_URL='http://localhost:5000'
python bots/telegram_bot.py
```

4. Запустите MAX бота:
```bash
export MAX_BOT_TOKEN='your_token'
export HELPDESK_API_URL='http://localhost:5000'
python bots/max_bot.py
```

## Пользователи по умолчанию

- **Admin**: admin / admin123
- **Specialist**: specialist / spec123

## Функционал

### Веб-интерфейс
- Регистрация и авторизация пользователей
- Создание и просмотр заявок
- Переписка в рамках заявки
- Назначение исполнителей
- Изменение статуса заявок
- Фильтрация по статусам

### Telegram бот
- Автоматические ответы
- Создание заявок через чат
- Добавление сообщений к заявкам
- Проверка статуса заявок
- Команды: /start, /help, /new, /status

### MAX бот
- Webhook для получения сообщений
- Автоматические ответы
- Создание заявок через чат
- Добавление сообщений к заявкам

## API Endpoints

### Создание заявки
```
POST /api/ticket/create
{
    "external_user_id": "user123",
    "external_chat_id": "chat456",
    "source": "telegram|max|web",
    "title": "Заголовок",
    "description": "Описание",
    "phone": "+79991234567"
}
```

### Добавление сообщения
```
POST /api/ticket/<id>/message
{
    "external_user_id": "user123",
    "external_chat_id": "chat456",
    "source": "telegram|max",
    "content": "Текст сообщения"
}
```

### Получение сообщений
```
GET /api/ticket/<id>/messages
```

## Важные уведомления

Все автоматические ответы содержат предупреждение:
> ⚠️ Важно: Заявки с персональными данными не будут обрабатываться. 
> Пожалуйста, укажите в общих чертах, что требуется сделать. 
> Специалист сразу свяжется с вами по указанному телефону.

## Конфигурация

Переменные окружения:
- `SECRET_KEY` - Секретный ключ Flask
- `TELEGRAM_BOT_TOKEN` - Токен Telegram бота
- `MAX_BOT_TOKEN` - Токен MAX бота
- `HELPDESK_API_URL` - URL основного приложения
