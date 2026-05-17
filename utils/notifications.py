"""
Yamen Academy v40 - Telegram Notification Layer
=================================================
Isolated fire-and-forget notification dispatcher.
- init_notifications(token)     → stores BOT_TOKEN globally
- send_telegram_notification(sid, text) → HTTP POST via requests
  Runs synchronously; MUST be called inside a daemon thread by the caller
  if non-blocking behaviour is required (e.g. from Flask routes).
"""

import sys
import traceback
from typing import Optional

import requests

# ── Global token placeholder ──────────────────────────
_BOT_TOKEN: Optional[str] = None


def init_notifications(token: str) -> None:
    """
    Store the Telegram Bot API token for subsequent notification calls.
    Called once during application bootstrap (e.g. in routes/admin_api.py).
    """
    global _BOT_TOKEN
    _BOT_TOKEN = token
    print(f"[NOTIFY] Bot token initialised (length={len(token)})", file=sys.stderr)


def send_telegram_notification(student_id: int, message_text: str) -> bool:
    """
    Send a Telegram message to *student_id* via the Bot API.

    Parameters
    ----------
    student_id : int
        Telegram chat ID of the recipient.
    message_text : str
        Text to send (supports HTML tags when parse_mode='HTML').

    Returns
    -------
    bool
        True if the message was sent successfully, False otherwise.

    Notes
    -----
    - This function performs a synchronous HTTP POST and **may block**
      for up to *timeout* seconds.  If you are calling this from a Flask
      request handler, wrap it in a daemon thread to avoid delaying the
      HTTP response.
    - All exceptions are caught internally; the caller will never receive
      a raised exception.
    """
    # ── Resolve token ─────────────────────────────────
    token: Optional[str] = _BOT_TOKEN
    if not token:
        # Fallback to environment variable (useful when init_notifications wasn't called)
        import os as _os
        token = _os.environ.get("YAMEN_BOT_TOKEN")
    if not token or token == "YOUR_ACTUAL_BOT_TOKEN_HERE":
        print(
            "[NOTIFY] ERROR: BOT_TOKEN is not set. "
            "Call init_notifications() or set YAMEN_BOT_TOKEN env var.",
            file=sys.stderr,
        )
        return False

    # ── Build request ─────────────────────────────────
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": student_id,
        "text": message_text,
        "parse_mode": "HTML",
    }

    # ── Execute (fully wrapped) ────────────────────────
    try:
        response = requests.post(url, json=payload, timeout=10)
    except requests.exceptions.Timeout:
        print(
            f"[NOTIFY] Timeout sending notification to student_id={student_id}",
            file=sys.stderr,
        )
        return False
    except requests.exceptions.ConnectionError:
        print(
            "[NOTIFY] ConnectionError: could not reach api.telegram.org",
            file=sys.stderr,
        )
        return False
    except requests.exceptions.RequestException as exc:
        print(f"[NOTIFY] RequestException: {exc}", file=sys.stderr)
        return False
    except Exception:
        traceback.print_exc()
        return False

    # ── Check response ────────────────────────────────
    if response.status_code == 200:
        print(
            f"[NOTIFY] Message sent successfully to student_id={student_id}",
            file=sys.stderr,
        )
        return True

    print(
        f"[NOTIFY] Telegram API returned HTTP {response.status_code}: "
        f"{response.text[:200]}",
        file=sys.stderr,
    )
    return False
