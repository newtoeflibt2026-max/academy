# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect(r'C:\Users\nelt2\yamen_academy\academy.db')

cols = [r[1] for r in conn.execute('PRAGMA table_info(subscriptions)').fetchall()]
print('subscriptions cols:', cols)

if 'telegram_id' not in cols:
    conn.execute('ALTER TABLE subscriptions ADD COLUMN telegram_id TEXT')
    print('Added telegram_id')

conn.execute('UPDATE subscriptions SET telegram_id = CAST(user_id AS TEXT) WHERE telegram_id IS NULL')
conn.commit()

rows = conn.execute('SELECT id, user_id, telegram_id, is_active, end_date FROM subscriptions LIMIT 3').fetchall()
for r in rows:
    print(r)

conn.close()
print('DB DONE')
