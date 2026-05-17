# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional


class SpacedRepetitionEngine:
    """
    قاعدة العمل:
    - إذا أجاب الطالب إجابة صحيحة مرة واحدة: يبقى الخطأ في المستودع ويُجدول للمراجعة القادمة.
    - إذا أجاب إجابتين صحيحتين متتاليتين: يُحذف الخطأ من المستودع.
    - إذا أخطأ مرة أخرى: يُصفّر العداد ويُعاد جدولة الخطأ.
    """

    first_success_interval_days = 1
    retry_interval_hours = 12
    required_consecutive_correct_to_remove = 2

    def utc_now_iso(self) -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def parse_iso(self, value: str) -> Optional[datetime]:
        if not value:
            return None

        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = raw[:-1]

        try:
            return datetime.fromisoformat(raw)
        except Exception:
            return None

    def format_iso(self, value: datetime) -> str:
        return value.replace(microsecond=0).isoformat() + "Z"

    def is_due(self, error_record: Any, current_time: Optional[datetime] = None) -> bool:
        now = current_time or datetime.utcnow()
        next_review_at = getattr(error_record, "next_review_at", "") or ""
        status = str(getattr(error_record, "status", "active") or "active").strip().lower()

        if status == "mastered":
            return False

        if not next_review_at:
            return True

        parsed = self.parse_iso(next_review_at)
        if parsed is None:
            return True

        return parsed <= now

    def due_errors(self, errors: Iterable[Any], current_time: Optional[datetime] = None) -> List[Any]:
        now = current_time or datetime.utcnow()
        return [error for error in errors if self.is_due(error, now)]

    def review(self, error_record: Any, is_correct: bool, reviewed_at: Optional[datetime] = None) -> Dict[str, Any]:
        now = reviewed_at or datetime.utcnow()
        reviewed_at_iso = self.format_iso(now)

        if hasattr(error_record, "mark_reviewed"):
            error_record.mark_reviewed(reviewed_at_iso)
        else:
            error_record.last_reviewed_at = reviewed_at_iso
            error_record.total_reviews = int(getattr(error_record, "total_reviews", 0)) + 1

        if is_correct:
            current_streak = int(getattr(error_record, "consecutive_correct", 0)) + 1
            error_record.consecutive_correct = current_streak

            if current_streak >= self.required_consecutive_correct_to_remove:
                if hasattr(error_record, "mark_mastered"):
                    error_record.mark_mastered()
                else:
                    error_record.status = "mastered"
                    error_record.archived = True
                    error_record.next_review_at = ""

                return {
                    "remove_from_bank": True,
                    "action": "removed_after_two_consecutive_correct",
                    "error": error_record,
                    "next_review_at": "",
                    "consecutive_correct": current_streak,
                }

            next_review = now + timedelta(days=self.first_success_interval_days)
            next_review_iso = self.format_iso(next_review)

            if hasattr(error_record, "mark_due"):
                error_record.mark_due(next_review_iso)
            else:
                error_record.status = "review_due"
                error_record.next_review_at = next_review_iso

            return {
                "remove_from_bank": False,
                "action": "scheduled_after_first_correct",
                "error": error_record,
                "next_review_at": next_review_iso,
                "consecutive_correct": current_streak,
            }

        error_record.consecutive_correct = 0
        retry_at = now + timedelta(hours=self.retry_interval_hours)
        retry_at_iso = self.format_iso(retry_at)

        if hasattr(error_record, "mark_due"):
            error_record.mark_due(retry_at_iso)
        else:
            error_record.status = "review_due"
            error_record.next_review_at = retry_at_iso

        return {
            "remove_from_bank": False,
            "action": "scheduled_retry_after_incorrect_review",
            "error": error_record,
            "next_review_at": retry_at_iso,
            "consecutive_correct": 0,
        }
