import time,logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters
from handlers import start, register_players, generate_grid, play_match, handle_winner, view_stats, end_game, REGISTER_PLAYERS, GENERATE_GRID, PLAY_MATCH, VIEW_STATS,force_end_game, show_monthly_stats
from config import BOT_TOKEN
from database import initialize_database
from telegram.error import TelegramError

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_logs.txt"),  # Логи будут записываться в файл bot_logs.txt
    ]
)
logger = logging.getLogger(__name__)

def main():
    while True:  # Бесконечный цикл для автоподнятия бота
        try:
            # Инициализация базы данных
            initialize_database()

            # Создаем приложение бота
            application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(30).build()

            # Создаем ConversationHandler
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', start)],
                states={
                    REGISTER_PLAYERS: [MessageHandler(filters.TEXT, register_players)],
                    GENERATE_GRID: [MessageHandler(filters.TEXT & filters.Regex("^Начать игру$"), generate_grid)],
                    PLAY_MATCH: [
                        MessageHandler(
                            filters.TEXT & ~filters.Regex("^(Начать игру|Статистика|Завершить игру|Завершить игру сейчас)$"),
                            handle_winner
                        ),
                        MessageHandler(filters.TEXT & filters.Regex("^Начать игру$"), play_match),
                        MessageHandler(filters.TEXT & filters.Regex("^Завершить игру сейчас$"), force_end_game)
                    ],
                    VIEW_STATS: [
                        MessageHandler(filters.TEXT & filters.Regex("^Новый круг$"), generate_grid),
                        MessageHandler(filters.TEXT & filters.Regex("^Завершить игру$"), end_game),
                        MessageHandler(filters.TEXT & filters.Regex("^Статистика$"), show_monthly_stats)
                    ],
                },
                fallbacks=[
                    MessageHandler(filters.TEXT & filters.Regex("^Начать новую игру$"), start),
                ]
            )

            # Добавляем ConversationHandler в приложение
            application.add_handler(conv_handler)

            # Запускаем бота
            application.run_polling()

        except TelegramError as e:
            # Логируем ошибку
            logger.error(f"Бот упал с ошибкой: {e}. Перезапуск через 5 секунд...")
            time.sleep(5)  # Ждем 5 секунд перед перезапуском
        except Exception as e:
            # Логируем любые другие ошибки
            logger.error(f"Неизвестная ошибка: {e}. Перезапуск через 5 секунд...")
            time.sleep(5)  # Ждем 5 секунд перед перезапуском

if __name__ == '__main__':
    main()