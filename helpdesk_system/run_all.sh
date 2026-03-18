#!/bin/bash

echo "Запуск Helpdesk системы МООНД..."

# Запуск основного Flask приложения
echo "Запуск основного приложения на порту 5000..."
python app.py &
MAIN_PID=$!

# Запуск MAX бота (если настроен)
if [ -n "$MAX_BOT_TOKEN" ] && [ "$MAX_BOT_TOKEN" != "YOUR_MAX_BOT_TOKEN" ]; then
    echo "Запуск MAX бота на порту 5001..."
    python bots/max_bot.py &
    MAX_PID=$!
fi

# Запуск Telegram бота (если настроен)
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ "$TELEGRAM_BOT_TOKEN" != "YOUR_TELEGRAM_BOT_TOKEN" ]; then
    echo "Запуск Telegram бота..."
    python bots/telegram_bot.py &
    TG_PID=$!
fi

echo ""
echo "=========================================="
echo "Helpdesk система запущена!"
echo "=========================================="
echo "Веб-интерфейс: http://localhost:5000"
echo "MAX Bot API: http://localhost:5001"
echo ""
echo "Пользователи по умолчанию:"
echo "  Admin: admin / admin123"
echo "  Specialist: specialist / spec123"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo "=========================================="

# Ожидание завершения
wait
