from flask import Flask, render_template, redirect, url_for, request, session, flash
import sqlite3
from hashlib import sha256
import random

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Функция для подключения к базе данных
def get_db():
    conn = sqlite3.connect('/home/zhenyawallet/mysite/wallet.db')
    conn.row_factory = sqlite3.Row
    return conn

# Генерация уникального адреса кошелька
def generate_address():
    return sha256(str(random.randint(100000, 999999)).encode()).hexdigest()

# Главная страница кошелька
@app.route('/')
def index():
    if 'user_id' in session:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT balance, address FROM users WHERE id = ?', (session['user_id'],))
            user_data = cursor.fetchone()

            if user_data:
                balance, address = user_data['balance'], user_data['address']

                # Получение истории транзакций
                cursor.execute('''
                    SELECT u.username as sender, v.username as receiver, t.amount, t.timestamp
                    FROM transactions t
                    JOIN users u ON u.id = t.sender_id
                    JOIN users v ON v.id = t.receiver_id
                    WHERE t.sender_id = ? OR t.receiver_id = ?
                    ORDER BY t.timestamp DESC
                ''', (session['user_id'], session['user_id']))
                transactions = cursor.fetchall()

                return render_template('wallet.html', balance=balance, address=address, transactions=transactions)
    return redirect(url_for('login'))

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        address = generate_address()

        if not username or not password:
            flash('Имя пользователя и пароль обязательны!', 'danger')
            return redirect(url_for('register'))

        with get_db() as conn:
            cursor = conn.cursor()

            # Проверяем, существует ли пользователь с таким же именем
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                flash('Пользователь с таким именем уже существует!', 'danger')
            else:
                # Добавляем нового пользователя
                cursor.execute('INSERT INTO users (username, password, balance, address) VALUES (?, ?, ?, ?)',
                               (username, sha256(password.encode()).hexdigest(), 0, address))
                flash('Регистрация прошла успешно!', 'success')
                return redirect(url_for('login'))

    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, password FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()

            if user and sha256(password.encode()).hexdigest() == user['password']:
                session['user_id'] = user['id']
                flash('Вы успешно вошли!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Неправильное имя пользователя или пароль', 'danger')

    return render_template('login.html')

# Выход
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# Пополнение баланса
@app.route('/deposit', methods=['POST'])
def deposit():
    if 'user_id' in session:
        try:
            amount = int(request.form['amount'])
            if amount <= 0:
                flash('Сумма должна быть положительной!', 'danger')
                return redirect(url_for('index'))

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, session['user_id']))
                flash('Баланс успешно пополнен!', 'success')
            return redirect(url_for('index'))
        except ValueError:
            flash('Некорректная сумма!', 'danger')
    return redirect(url_for('login'))

# Перевод другому пользователю
@app.route('/send', methods=['POST'])
def send():
    if 'user_id' in session:
        receiver_address = request.form['receiver']
        try:
            amount = int(request.form['amount'])
            if amount <= 0:
                flash('Сумма должна быть положительной!', 'danger')
                return redirect(url_for('index'))

            with get_db() as conn:
                cursor = conn.cursor()

                # Найти получателя по адресу
                cursor.execute('SELECT id FROM users WHERE address = ?', (receiver_address,))
                receiver = cursor.fetchone()

                if receiver:
                    receiver_id = receiver['id']

                    # Проверить баланс отправителя
                    cursor.execute('SELECT balance FROM users WHERE id = ?', (session['user_id'],))
                    sender_balance = cursor.fetchone()['balance']

                    if sender_balance >= amount:
                        # Обновить баланс отправителя и получателя
                        cursor.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, session['user_id']))
                        cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, receiver_id))

                        # Записать транзакцию
                        cursor.execute('INSERT INTO transactions (sender_id, receiver_id, amount) VALUES (?, ?, ?)',
                                       (session['user_id'], receiver_id, amount))
                        flash('Перевод успешно выполнен!', 'success')
                    else:
                        flash('Недостаточно средств на счету', 'danger')
                else:
                    flash('Пользователь с таким адресом не найден', 'danger')

            return redirect(url_for('index'))
        except ValueError:
            flash('Некорректная сумма!', 'danger')
    return redirect(url_for('login'))

@app.route('/clicker')
def clicker():
    return render_template('clicker.html')  # предположим, что код HTML находится в файле clicker.html

@app.route('/earn_coins', methods=['POST'])
def earn_coins():
    if 'user_id' in session:
        data = request.get_json()
        earned_coins = data.get('amount', 0)
        wallet_address = data.get('address', '')

        with get_db() as conn:
            cursor = conn.cursor()

            # Проверить, существует ли кошелек с таким адресом
            cursor.execute('SELECT id FROM users WHERE address = ?', (wallet_address,))
            receiver = cursor.fetchone()

            if receiver:
                receiver_id = receiver['id']

                # Обновить баланс получателя
                cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (earned_coins, receiver_id))

                # Записать транзакцию
                cursor.execute('INSERT INTO transactions (sender_id, receiver_id, amount) VALUES (?, ?, ?)',
                               (session['user_id'], receiver_id, earned_coins))
                conn.commit()

                return {'success': True}
            else:
                return {'success': False, 'message': 'Кошелек не найден'}

    return {'success': False}, 401

if __name__ == '__main__':
    app.run(debug=True)
