from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters
from handlers import start, register_players, generate_grid, play_match, handle_winner, view_stats, end_game, REGISTER_PLAYERS, GENERATE_GRID, PLAY_MATCH, VIEW_STATS,force_end_game
from config import BOT_TOKEN
from database import initialize_database

def main():
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
                MessageHandler(filters.TEXT & filters.Regex("^Завершить игру$"), end_game)
            ],
        },
        fallbacks=[
            MessageHandler(filters.TEXT & filters.Regex("^Статистика$"), lambda update, context: None),
            MessageHandler(filters.TEXT & filters.Regex("^Начать новую игру$"), start),
            # Обрабатываем кнопку "Начать новую игру"
        ]
    )

    # Добавляем ConversationHandler в приложение
    application.add_handler(conv_handler)

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()