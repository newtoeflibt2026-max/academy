# -*- coding: utf-8 -*-

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


@dataclass
class ErrorRecord:
    error_id: str
    uid: int
    lesson_id: str
    skill: str
    prompt: str
    user_answer: str
    correct_answer: str
    explanation: str
    source_type: str = "lesson_test"
    status: str = "active"
    consecutive_correct: int = 0
    total_reviews: int = 0
    created_at: str = ""
    last_reviewed_at: str = ""
    next_review_at: str = ""
    track: str = ""
    archived: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = utc_now_iso()

    def mark_reviewed(self, reviewed_at: str):
        self.last_reviewed_at = reviewed_at
        self.total_reviews += 1

    def mark_due(self, next_review_at: str):
        self.status = "review_due"
        self.next_review_at = next_review_at

    def mark_active(self):
        self.status = "active"
        self.next_review_at = ""

    def mark_mastered(self):
        self.status = "mastered"
        self.archived = True
        self.next_review_at = ""

    def reset_streak(self):
        self.consecutive_correct = 0

    def increment_streak(self):
        self.consecutive_correct += 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
