import sqlite3
import logging
from config import DATABASE_NAME

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_connection():
    """Создает соединение с базой данных."""
    return sqlite3.connect(DATABASE_NAME, check_same_thread=False)

def initialize_database():
    """Инициализирует таблицы в базе данных."""
    conn = create_connection()
    cursor = conn.cursor()

    # Создаем таблицу sessions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL
    )
    ''')

    # Создаем таблицу players
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
    )
    ''')

    # Создаем таблицу matches с новой колонкой is_skipped
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        match_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        round_number INTEGER NOT NULL,
        player1_id INTEGER NOT NULL,
        player2_id INTEGER NOT NULL,
        winner_id INTEGER,
        is_skipped INTEGER DEFAULT 0,  -- Новая колонка для отслеживания пропущенных матчей
        FOREIGN KEY (session_id) REFERENCES sessions (session_id),
        FOREIGN KEY (player1_id) REFERENCES players (player_id),
        FOREIGN KEY (player2_id) REFERENCES players (player_id),
        FOREIGN KEY (winner_id) REFERENCES players (player_id)
    )
    ''')

    conn.commit()
    conn.close()
    logger.info("База данных инициализирована с новой колонкой is_skipped.")
