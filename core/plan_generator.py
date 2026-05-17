# -*- coding: utf-8 -*-

from typing import Any, Dict, List


class PlanGenerator:
    def __init__(self, student: Any, diagnostic_scores: Dict[str, float]):
        self.student = student
        self.diagnostic_scores = self._normalize_scores(diagnostic_scores)

    def _package_days(self) -> int:
        package_value = str(getattr(self.student, "package_type", 30)).strip().lower()
        if "90" in package_value:
            return 90
        if "60" in package_value:
            return 60
        return 30

    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        normalized = {
            "reading": 0.0,
            "listening": 0.0,
            "speaking": 0.0,
            "writing": 0.0,
        }

        for skill in normalized:
            value = scores.get(skill, 0.0)
            try:
                value = float(value)
            except Exception:
                value = 0.0

            if value < 0:
                value = 0.0
            if value > 100:
                value = 100.0

            normalized[skill] = round(value, 2)

        return normalized

    def _weakness_percentages(self) -> Dict[str, float]:
        weakness = {}
        for skill, score in self.diagnostic_scores.items():
            weakness[skill] = round(100.0 - score, 2)
        return weakness

    def _study_weights(self, weakness: Dict[str, float]) -> Dict[str, int]:
        total_weakness = sum(weakness.values())
        if total_weakness <= 0:
            return {
                "reading": 25,
                "listening": 25,
                "speaking": 25,
                "writing": 25,
            }

        raw = {}
        for skill, value in weakness.items():
            raw[skill] = (value / total_weakness) * 100.0

        rounded = {skill: int(round(weight)) for skill, weight in raw.items()}
        diff = 100 - sum(rounded.values())

        if diff != 0:
            focus_skill = max(raw, key=raw.get)
            rounded[focus_skill] += diff

        return rounded

    def _focus_order(self, weakness: Dict[str, float]) -> List[str]:
        ordered = sorted(weakness.items(), key=lambda item: item[1], reverse=True)
        return [skill for skill, _ in ordered]

    def _expected_score_for_day(self, day: int) -> int:
        baseline = float(getattr(self.student, "diagnostic_score", 0))
        target = float(getattr(self.student, "target_score", 100))
        package_days = self._package_days()

        if package_days <= 0:
            return int(round(baseline))

        progress_ratio = min(day, package_days) / package_days
        expected = baseline + (target - baseline) * progress_ratio

        if day == 1 and target > baseline:
            expected = max(expected, baseline + 1)

        if expected < 0:
            expected = 0
        if expected > 120:
            expected = 120

        return int(round(expected))

    def _milestone_payload(self, day: int, focus_skill: str, study_weights: Dict[str, int]) -> Dict[str, Any]:
        focus_messages = {
            "reading": "تعزيز فهم المقاطع الأكاديمية، الاستنتاج، وإدارة الزمن في القراءة.",
            "listening": "رفع دقة التقاط الفكرة الرئيسية والتفاصيل والموقف الضمني.",
            "speaking": "بناء قوالب إجابة قوية ورفع الترابط والطلاقة تحت ضغط الوقت.",
            "writing": "تحسين البناء الأكاديمي، الترابط، والدعم بالأمثلة المقنعة.",
        }

        return {
            "day": day,
            "expected_mock_score": self._expected_score_for_day(day),
            "focus_skill": focus_skill,
            "focus_summary": focus_messages.get(focus_skill, "تحسين الأداء العام."),
            "study_weight": study_weights.get(focus_skill, 25),
        }

    def generate_plan(self) -> Dict[str, Any]:
        weakness = self._weakness_percentages()
        study_weights = self._study_weights(weakness)
        focus_order = self._focus_order(weakness)
        package_days = self._package_days()

        day_skill_map = {
            1: focus_order[0],
            15: focus_order[0],
            30: focus_order[1] if len(focus_order) > 1 else focus_order[0],
            45: focus_order[2] if len(focus_order) > 2 else focus_order[0],
            60: focus_order[3] if len(focus_order) > 3 else focus_order[0],
        }

        milestones = {
            "day_1": self._milestone_payload(1, day_skill_map[1], study_weights),
            "day_15": self._milestone_payload(15, day_skill_map[15], study_weights),
            "day_30": self._milestone_payload(30, day_skill_map[30], study_weights),
            "day_45": self._milestone_payload(45, day_skill_map[45], study_weights),
            "day_60": self._milestone_payload(60, day_skill_map[60], study_weights),
        }

        weakness_analysis = []
        for skill in ("reading", "listening", "speaking", "writing"):
            weakness_analysis.append(
                {
                    "skill": skill,
                    "diagnostic_score": self.diagnostic_scores[skill],
                    "weakness_percentage": weakness[skill],
                    "allocated_weight": study_weights[skill],
                }
            )

        return {
            "student_uid": getattr(self.student, "uid", None),
            "package_days": package_days,
            "daily_progress_needed": float(getattr(self.student, "calculate_daily_progress_needed")()),
            "focus_order": focus_order,
            "study_weights": study_weights,
            "weakness_analysis": weakness_analysis,
            "milestones": milestones,
        }
