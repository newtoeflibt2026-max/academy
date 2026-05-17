# -*- coding: utf-8 -*-

from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class StudentProfile:
    uid: int
    username: str
    target_score: int
    test_date: str
    package_type: Any
    student_stage: str
    study_hours_per_day: float
    track: str = "foundation"
    points: int = 0
    current_lesson: str = "Diagnostic Readiness"
    diagnostic_score: int = 0

    @property
    def package_days(self) -> int:
        package_value = str(self.package_type).strip().lower()
        if "90" in package_value:
            return 90
        if "60" in package_value:
            return 60
        return 30

    def calculate_daily_progress_needed(self) -> float:
        return round((self.target_score - self.diagnostic_score) / self.package_days, 4)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


Student = StudentProfile
