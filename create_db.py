import sqlite3

# Подключаемся к базе данных (если файла нет, SQLite создаст его автоматически)
conn = sqlite3.connect('/home/zhenyawallet/mysite/wallet.db')

# Создаем курсор для выполнения SQL-запросов
cursor = conn.cursor()

# Создаем таблицу пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    balance INTEGER NOT NULL DEFAULT 100,
    address TEXT UNIQUE NOT NULL
)
''')

# Создаем таблицу транзакций
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(sender_id) REFERENCES users(id),
    FOREIGN KEY(receiver_id) REFERENCES users(id)
)
''')

# Сохраняем изменения
conn.commit()

# Закрываем соединение с базой данных
conn.close()

print("База данных и таблицы успешно созданы.")