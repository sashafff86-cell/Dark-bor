import aiosqlite
import time

DB_NAME = "users.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 1000,
                referrer_id INTEGER DEFAULT NULL,
                last_bonus INTEGER DEFAULT 0
            )
        ''')
        await db.commit()

async def get_user(user_id: int, username: str, referrer_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user is None:
                await db.execute(
                    'INSERT INTO users (user_id, username, balance, referrer_id) VALUES (?, ?, ?, ?)',
                    (user_id, username, 1000, referrer_id)
                )
                if referrer_id and referrer_id != user_id:
                    await db.execute('UPDATE users SET balance = balance + 500 WHERE user_id = ?', (referrer_id,))
                await db.commit()
                return 1000
            return user[0]

async def update_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        await db.commit()

async def claim_daily_bonus(user_id: int) -> tuple[bool, int]:
    current_time = int(time.time())
    cd = 86400

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT last_bonus FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            last_bonus = row[0] if row else 0

        if current_time - last_bonus >= cd:
            bonus_amount = 500
            await db.execute(
                'UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id = ?',
                (bonus_amount, current_time, user_id)
            )
            await db.commit()
            return True, bonus_amount
        else:
            time_left = cd - (current_time - last_bonus)
            return False, time_left
