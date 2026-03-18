# Инструкция по настройке токенов ботов

## Файл .env

Все токены и настройки хранятся в файле `.env` в корне проекта.

### Отредактируйте файл .env:

```bash
cd /workspace/helpdesk_system
nano .env
```

### Замените значения на свои:

```ini
# Токен Telegram бота (получить у @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz...

# Токен MAX бота (получить в админ-панели MAX)
MAX_BOT_TOKEN=ваш_токен_max_бота

# URL приложения helpdesk
HELPDESK_API_URL=http://localhost:5000

# Секретный ключ Flask (замените на случайную строку)
SECRET_KEY=случайная_строка_для_безопасности

# База данных
DATABASE_URI=sqlite:///instance/helpdesk.db
```

## Как получить токены

### Telegram Bot Token:
1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Придумайте имя и username для бота
4. BotFather выдаст токен вида: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz...`
5. Скопируйте токен в файл `.env`

### MAX Bot Token:
1. Войдите в административную панель MAX
2. Перейдите в раздел "Bots" или "API"
3. Создайте нового бота
4. Скопируйте выданный токен в файл `.env`

## Установка зависимостей

После редактирования `.env` установите зависимости:

```bash
cd /workspace/helpdesk_system
source venv/bin/activate
pip install -r requirements.txt
```

## Запуск приложения

### 1. Запуск основного Flask приложения:
```bash
python app.py
```

### 2. Запуск Telegram бота (в отдельном терминале):
```bash
source venv/bin/activate
python bots/telegram_bot.py
```

### 3. Запуск MAX бота (в отдельном терминале):
```bash
source venv/bin/activate
python bots/max_bot.py
```

Или используйте скрипт для запуска всего сразу:
```bash
./run_all.sh
```

## Проверка работы

1. Откройте браузер: http://localhost:5000
2. Войдите как admin/admin123
3. В Telegram найдите своего бота и отправьте /start
4. Для MAX настройте webhook на: http://ваш-ip:5001/max/webhook
