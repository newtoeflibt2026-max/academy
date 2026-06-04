# -*- coding: utf-8 -*-
"""Hearts System - Yamen Academy
Handles: lose heart, regenerate, check, unlimited for premium
"""
import sqlite3, datetime, os

DB_PATH = os.environ.get('DB_PATH', r'C:\Users\nelt2\yamen_academy\academy.db')
MAX_HEARTS = 5
REGEN_MINUTES = 300  # 5 hours per heart (Duolingo style)

# Premium subscription types = unlimited hearts
PREMIUM_PLANS = ['monthly', 'quarterly', 'yearly', 'lifetime', 'pro', 'premium']

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def get_hearts_status(user_id):
    """Returns: {hearts, max, unlimited, next_regen_in_minutes, regen_at}"""
    conn = _conn(); cur = conn.cursor()
    row = cur.execute(
        "SELECT hearts, hearts_updated_at, hearts_unlimited, subscription_type FROM students WHERE user_id=?",
        (user_id,)
    ).fetchone()
    if not row:
        conn.close()
        return {'hearts': MAX_HEARTS, 'max': MAX_HEARTS, 'unlimited': False, 'next_regen_in_minutes': 0}
    
    hearts = row['hearts'] if row['hearts'] is not None else MAX_HEARTS
    sub = (row['subscription_type'] or '').lower()
    unlimited = bool(row['hearts_unlimited']) or sub in PREMIUM_PLANS
    
    # Regenerate hearts based on time elapsed
    if not unlimited and hearts < MAX_HEARTS and row['hearts_updated_at']:
        try:
            last = datetime.datetime.fromisoformat(row['hearts_updated_at'])
            elapsed_min = (datetime.datetime.now() - last).total_seconds() / 60
            regen_count = int(elapsed_min // REGEN_MINUTES)
            if regen_count > 0:
                hearts = min(MAX_HEARTS, hearts + regen_count)
                new_time = (last + datetime.timedelta(minutes=regen_count * REGEN_MINUTES)).isoformat()
                cur.execute("UPDATE students SET hearts=?, hearts_updated_at=? WHERE user_id=?", (hearts, new_time, user_id))
                conn.commit()
        except: pass
    
    # Time until next heart
    next_min = 0
    if not unlimited and hearts < MAX_HEARTS and row['hearts_updated_at']:
        try:
            last = datetime.datetime.fromisoformat(row['hearts_updated_at'])
            elapsed = (datetime.datetime.now() - last).total_seconds() / 60
            next_min = max(0, int(REGEN_MINUTES - (elapsed % REGEN_MINUTES)))
        except: pass
    
    conn.close()
    return {
        'hearts': MAX_HEARTS if unlimited else hearts,
        'max': MAX_HEARTS,
        'unlimited': unlimited,
        'next_regen_in_minutes': 0 if unlimited else next_min,
    }

def lose_heart(user_id, reason='wrong_answer', section=None, lesson_id=None):
    """Decrease 1 heart. Returns new status. Premium = no change."""
    status = get_hearts_status(user_id)
    if status['unlimited']:
        _log(user_id, 0, reason + '_unlimited', section, lesson_id, status['hearts'])
        return status
    
    conn = _conn(); cur = conn.cursor()
    new_hearts = max(0, status['hearts'] - 1)
    cur.execute("UPDATE students SET hearts=?, hearts_updated_at=? WHERE user_id=?",
                (new_hearts, datetime.datetime.now().isoformat(), user_id))
    conn.commit(); conn.close()
    _log(user_id, -1, reason, section, lesson_id, new_hearts)
    return get_hearts_status(user_id)

def can_practice(user_id):
    """Returns True if user has hearts > 0 or unlimited"""
    s = get_hearts_status(user_id)
    return s['unlimited'] or s['hearts'] > 0

def refill_hearts(user_id, reason='manual_refill'):
    """Reset hearts to MAX (e.g., after watching ad or premium purchase)"""
    conn = _conn(); cur = conn.cursor()
    cur.execute("UPDATE students SET hearts=?, hearts_updated_at=? WHERE user_id=?",
                (MAX_HEARTS, datetime.datetime.now().isoformat(), user_id))
    conn.commit(); conn.close()
    _log(user_id, MAX_HEARTS, reason, None, None, MAX_HEARTS)
    return get_hearts_status(user_id)

def _log(user_id, change, reason, section, lesson_id, hearts_after):
    try:
        conn = _conn(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO hearts_log (user_id, change, reason, section, lesson_id, hearts_after) VALUES (?,?,?,?,?,?)",
            (user_id, change, reason, section, lesson_id, hearts_after)
        )
        conn.commit(); conn.close()
    except Exception as e:
        print(f'[hearts_log] {e}')
