# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import math
import traceback
import importlib
from copy import deepcopy
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, redirect, url_for


# ============================================================
# App Configuration
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
)

app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.url_map.strict_slashes = False

try:
    app.json.ensure_ascii = False
except Exception:
    pass


# ============================================================
# Optional Imports Loader
# ============================================================

def _load_optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


database_module = _load_optional_module("database")
student_module = _load_optional_module("models.student")
plan_generator_module = _load_optional_module("core.plan_generator")
diagnostic_module = _load_optional_module("data.diagnostic_questions")
lesson_module = _load_optional_module("models.lesson")
error_bank_module = _load_optional_module("models.error_bank")
spaced_repetition_module = _load_optional_module("core.spaced_repetition")


# ============================================================
# General Utilities
# ============================================================

def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        return int(float(str(value).strip()))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(str(value).strip())
    except Exception:
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value).strip()
    except Exception:
        return default


def _safe_parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _safe_parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).strip())
    except Exception:
        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


def _payload() -> Dict[str, Any]:
    try:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    try:
        if request.form:
            return request.form.to_dict()
    except Exception:
        pass

    return {}


def _api_ok(message: str = "OK", **extra):
    response = {"success": True, "message": message}
    response.update(extra)
    return jsonify(response), 200


def _api_error(message: str = "حدث خطأ", status_code: int = 400, **extra):
    response = {"success": False, "message": message}
    response.update(extra)
    return jsonify(response), status_code


def _normalize_track(track: Any) -> str:
    raw = _safe_str(track, "").lower()
    if raw in {"foundation", "beginner", "base", "starter"}:
        return "foundation"
    if raw in {"toefl", "intermediate", "standard"}:
        return "toefl"
    if raw in {"advanced", "expert", "pro"}:
        return "advanced"
    if raw in {"pending", "", "none", "null"}:
        return "pending"
    return "foundation"


def _normalize_package_days(package_type: Any) -> int:
    raw = _safe_str(package_type, "60")
    digits = "".join(ch for ch in raw if ch.isdigit())
    try:
        number = int(digits) if digits else 60
    except Exception:
        number = 60
    return max(number, 1)


def _normalize_stage(stage: Any) -> str:
    raw = _safe_str(stage, "pre-diagnostic").lower()
    if raw in {"pre", "pre-diagnostic", "pre_diagnostic"}:
        return "pre-diagnostic"
    if raw in {"post", "post-diagnostic", "post_diagnostic"}:
        return "post-diagnostic"
    if raw in {"active", "learning"}:
        return "active"
    return raw or "pre-diagnostic"


def _ensure_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            return obj.to_dict()
        except Exception:
            pass

    data = {}
    for attr in [
        "uid",
        "username",
        "target_score",
        "test_date",
        "package_type",
        "student_stage",
        "study_hours_per_day",
        "track",
        "points",
        "current_lesson",
        "diagnostic_score",
    ]:
        try:
            data[attr] = getattr(obj, attr, None)
        except Exception:
            data[attr] = None
    return data


# ============================================================
# Fallback Models
# ============================================================

@dataclass
class FallbackStudent:
    uid: int = 1
    username: str = "إمبراطورة دانيا"
    target_score: int = 105
    test_date: str = "2026-12-31"
    package_type: Any = 60
    student_stage: str = "pre-diagnostic"
    study_hours_per_day: float = 3.0
    track: str = "advanced"
    points: int = 1250
    current_lesson: Any = "advanced_lesson_1"
    diagnostic_score: int = 82

    def package_days(self) -> int:
        return _normalize_package_days(self.package_type)

    def calculate_daily_progress_needed(self) -> Dict[str, Any]:
        exam_date = _safe_parse_date(self.test_date)
        today = date.today()
        if exam_date is None:
            days_remaining = self.package_days()
        else:
            days_remaining = max((exam_date - today).days, 1)

        current_score = _safe_int(self.diagnostic_score, 0)
        target_score = _safe_int(self.target_score, 100)
        gap = max(target_score - current_score, 0)
        daily_needed = round(gap / max(days_remaining, 1), 2)

        return {
            "days_remaining": days_remaining,
            "score_gap": gap,
            "score_per_day": daily_needed,
            "study_hours_per_day": _safe_float(self.study_hours_per_day, 2.0),
            "weekly_focus_units": max(1, math.ceil(gap / 5)) if gap else 1,
            "status": "steady" if daily_needed <= 0.5 else "intensive",
            "label": f"{daily_needed} نقطة يومياً تقريباً",
        }

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FallbackLessonExercise:
    exercise_id: str
    prompt: str
    exercise_type: str = "short_text"
    expected_answer: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exercise_id": self.exercise_id,
            "prompt": self.prompt,
            "exercise_type": self.exercise_type,
            "expected_answer": self.expected_answer,
        }


@dataclass
class FallbackLessonTestQuestion:
    question_id: str
    question: str
    options: List[str]
    correct_answer: str
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "options": list(self.options),
            "correct_answer": self.correct_answer,
            "explanation": self.explanation,
        }


@dataclass
class FallbackLesson:
    lesson_id: str
    track: str
    order: int
    title: str
    objective: str
    content_summary: str
    content_blocks: List[str]
    xp_reward: int = 100
    pass_threshold: float = 70.0
    exercises: List[Any] = field(default_factory=list)
    lesson_test: List[Any] = field(default_factory=list)

    def max_test_score(self) -> int:
        return len(self.lesson_test)

    def evaluate_test(self, answers: List[str]) -> Dict[str, Any]:
        total = len(self.lesson_test)
        correct = 0
        details = []

        for index, question in enumerate(self.lesson_test):
            user_answer = answers[index] if index < len(answers) else ""
            user_answer = _safe_str(user_answer, "")
            correct_answer = _safe_str(getattr(question, "correct_answer", ""), "")
            is_correct = user_answer == correct_answer
            if is_correct:
                correct += 1

            details.append({
                "question_id": getattr(question, "question_id", f"q{index + 1}"),
                "question": getattr(question, "question", ""),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "explanation": getattr(question, "explanation", ""),
            })

        percentage = round((correct / total) * 100, 2) if total else 0.0
        passed = percentage >= float(self.pass_threshold)

        return {
            "correct_count": correct,
            "total_questions": total,
            "score_percentage": percentage,
            "passed": passed,
            "details": details,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "track": self.track,
            "order": self.order,
            "title": self.title,
            "objective": self.objective,
            "content_summary": self.content_summary,
            "content_blocks": list(self.content_blocks),
            "xp_reward": self.xp_reward,
            "pass_threshold": self.pass_threshold,
            "exercises": [
                item.to_dict() if hasattr(item, "to_dict") else item for item in self.exercises
            ],
            "lesson_test": [
                item.to_dict() if hasattr(item, "to_dict") else item for item in self.lesson_test
            ],
        }


@dataclass
class FallbackErrorRecord:
    error_id: str
    uid: int
    source_type: str
    source_ref: str
    question_text: str
    student_answer: str
    correct_answer: str
    explanation: str = ""
    status: str = "active"
    consecutive_correct: int = 0
    review_count: int = 0
    created_at: str = field(default_factory=_utc_now_iso)
    last_reviewed_at: Optional[str] = None
    next_review_at: str = field(default_factory=_utc_now_iso)

    def is_due(self) -> bool:
        scheduled = _safe_parse_datetime(self.next_review_at)
        if scheduled is None:
            return True
        return datetime.utcnow() >= scheduled

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FallbackSpacedRepetitionEngine:
    def process_review(self, record: Any, is_correct: bool) -> Dict[str, Any]:
        now = datetime.utcnow()
        record.review_count = _safe_int(getattr(record, "review_count", 0), 0) + 1
        record.last_reviewed_at = now.isoformat()

        if is_correct:
            record.consecutive_correct = _safe_int(getattr(record, "consecutive_correct", 0), 0) + 1
            if record.consecutive_correct >= 2:
                record.status = "resolved"
                record.next_review_at = now.isoformat()
                return {
                    "action": "delete",
                    "record": record,
                    "message": "تم حذف الخطأ بعد إجابتين صحيحتين متتاليتين.",
                }

            record.status = "reviewing"
            record.next_review_at = (now + timedelta(days=1)).isoformat()
            return {
                "action": "keep",
                "record": record,
                "message": "إجابة صحيحة. سيعاد عرض الخطأ لاحقاً للتثبيت.",
            }

        record.consecutive_correct = 0
        record.status = "active"
        record.next_review_at = (now + timedelta(hours=12)).isoformat()
        return {
            "action": "keep",
            "record": record,
            "message": "إجابة غير صحيحة. تمت إعادة جدولة الخطأ.",
        }


class FallbackPlanGenerator:
    def __init__(self, student: Any):
        self.student = student

    def generate_success_plan(self) -> Dict[str, Any]:
        student_dict = _student_to_dict(self.student)
        target_score = _safe_int(student_dict.get("target_score"), 100)
        diagnostic_score = _safe_int(student_dict.get("diagnostic_score"), 0)
        gap = max(target_score - diagnostic_score, 0)

        weakness_percentages = {
            "reading": min(100, max(25, 50 + gap // 3)),
            "listening": min(100, max(25, 48 + gap // 4)),
            "speaking": min(100, max(25, 58 + gap // 3)),
            "writing": min(100, max(25, 60 + gap // 3)),
        }

        focus_order = sorted(
            weakness_percentages.keys(),
            key=lambda k: weakness_percentages.get(k, 0),
            reverse=True,
        )

        expected_scores = {
            "day_1": diagnostic_score,
            "day_15": min(target_score, diagnostic_score + max(3, round(gap * 0.18))),
            "day_30": min(target_score, diagnostic_score + max(7, round(gap * 0.40))),
            "day_45": min(target_score, diagnostic_score + max(12, round(gap * 0.68))),
            "day_60": target_score,
        }

        milestones = [
            {
                "day": 1,
                "title": "إطلاق الخطة",
                "goal": "تثبيت مستوى البداية وتحديد أولويات العمل",
                "focus": focus_order[:2],
                "expected_score": expected_scores["day_1"],
            },
            {
                "day": 15,
                "title": "بناء القاعدة",
                "goal": "تحسين جودة الفهم والتنظيم",
                "focus": focus_order[:2],
                "expected_score": expected_scores["day_15"],
            },
            {
                "day": 30,
                "title": "منتصف الرحلة",
                "goal": "رفع الثبات في الأداء وتقليل التردد",
                "focus": focus_order[:3],
                "expected_score": expected_scores["day_30"],
            },
            {
                "day": 45,
                "title": "مرحلة الإتقان",
                "goal": "محاكاة عالية الكثافة ومعالجة الفجوات الدقيقة",
                "focus": focus_order[:3],
                "expected_score": expected_scores["day_45"],
            },
            {
                "day": 60,
                "title": "الجاهزية النهائية",
                "goal": "وصول منظم ومضبوط إلى الدرجة المستهدفة",
                "focus": focus_order,
                "expected_score": expected_scores["day_60"],
            },
        ]

        return {
            "weakness_percentages": weakness_percentages,
            "study_weights": {
                "reading": 0.24,
                "listening": 0.22,
                "speaking": 0.28,
                "writing": 0.26,
            },
            "focus_order": focus_order,
            "expected_scores": expected_scores,
            "milestones": milestones,
        }


# ============================================================
# Resolve Real Classes or Fallbacks
# ============================================================

StudentClass = (
    getattr(student_module, "StudentProfile", None)
    or getattr(student_module, "Student", None)
    or FallbackStudent
)

PlanGeneratorClass = (
    getattr(plan_generator_module, "PlanGenerator", None)
    or FallbackPlanGenerator
)

LessonClass = (
    getattr(lesson_module, "Lesson", None)
    or getattr(lesson_module, "LessonModel", None)
    or FallbackLesson
)

LessonExerciseClass = (
    getattr(lesson_module, "LessonExercise", None)
    or getattr(lesson_module, "Exercise", None)
    or FallbackLessonExercise
)

LessonTestQuestionClass = (
    getattr(lesson_module, "LessonTestQuestion", None)
    or getattr(lesson_module, "LessonQuizQuestion", None)
    or FallbackLessonTestQuestion
)

ErrorRecordClass = (
    getattr(error_bank_module, "ErrorRecord", None)
    or getattr(error_bank_module, "ErrorItem", None)
    or FallbackErrorRecord
)

SpacedRepetitionEngineClass = (
    getattr(spaced_repetition_module, "SpacedRepetitionEngine", None)
    or FallbackSpacedRepetitionEngine
)


# ============================================================
# Default Diagnostic Questions
# ============================================================

DEFAULT_DIAGNOSTIC_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "dq_1",
        "section": "reading",
        "skill": "main_idea",
        "difficulty": "medium",
        "question": "What is the main purpose of an introductory paragraph in an academic essay?",
        "options": [
            "To provide the final conclusion",
            "To introduce the topic and thesis",
            "To list all supporting examples",
            "To repeat the body paragraphs",
        ],
        "correct_answer": "To introduce the topic and thesis",
        "explanation": "An introduction presents the topic and thesis statement.",
    },
    {
        "id": "dq_2",
        "section": "reading",
        "skill": "vocabulary",
        "difficulty": "medium",
        "question": "Choose the closest meaning of the word 'significant'.",
        "options": ["Minor", "Important", "Temporary", "Silent"],
        "correct_answer": "Important",
        "explanation": "Significant means important or meaningful.",
    },
    {
        "id": "dq_3",
        "section": "reading",
        "skill": "inference",
        "difficulty": "medium",
        "question": "If a passage says 'the results were unexpected,' what can be inferred?",
        "options": [
            "The results were predicted exactly",
            "The results surprised the researchers",
            "The experiment never happened",
            "The data was missing",
        ],
        "correct_answer": "The results surprised the researchers",
        "explanation": "Unexpected results indicate surprise.",
    },
    {
        "id": "dq_4",
        "section": "reading",
        "skill": "detail",
        "difficulty": "easy",
        "question": "A supporting detail in a reading passage usually helps the reader:",
        "options": [
            "Ignore the author's point",
            "Understand the main idea better",
            "Skip the paragraph",
            "Memorize unrelated words",
        ],
        "correct_answer": "Understand the main idea better",
        "explanation": "Supporting details develop and clarify the main idea.",
    },
    {
        "id": "dq_5",
        "section": "listening",
        "skill": "gist",
        "difficulty": "medium",
        "question": "In TOEFL listening, identifying the gist means understanding:",
        "options": [
            "Every spelling rule",
            "The speaker's clothing",
            "The main point of the talk",
            "The building location only",
        ],
        "correct_answer": "The main point of the talk",
        "explanation": "Gist questions test understanding of the main point.",
    },
    {
        "id": "dq_6",
        "section": "listening",
        "skill": "function",
        "difficulty": "medium",
        "question": "When a professor says, 'Let's move on,' the function is usually to:",
        "options": [
            "Change to a new point",
            "End the course forever",
            "Ask for directions",
            "Correct grammar",
        ],
        "correct_answer": "Change to a new point",
        "explanation": "This phrase signals a transition.",
    },
    {
        "id": "dq_7",
        "section": "listening",
        "skill": "attitude",
        "difficulty": "medium",
        "question": "A rising excited tone often indicates the speaker is:",
        "options": ["Bored", "Enthusiastic", "Absent", "Confused by noise only"],
        "correct_answer": "Enthusiastic",
        "explanation": "Tone helps reveal speaker attitude.",
    },
    {
        "id": "dq_8",
        "section": "listening",
        "skill": "detail",
        "difficulty": "easy",
        "question": "Good note-taking during listening should focus on:",
        "options": [
            "Every single article and preposition",
            "Main points and key details",
            "Drawing unrelated pictures",
            "Translating each word immediately",
        ],
        "correct_answer": "Main points and key details",
        "explanation": "Efficient notes capture structure and important support.",
    },
    {
        "id": "dq_9",
        "section": "speaking",
        "skill": "organization",
        "difficulty": "medium",
        "question": "A strong TOEFL speaking response usually includes:",
        "options": [
            "A clear structure and relevant support",
            "Only repeated filler words",
            "No examples at all",
            "Random personal stories",
        ],
        "correct_answer": "A clear structure and relevant support",
        "explanation": "Organization and support improve speaking scores.",
    },
    {
        "id": "dq_10",
        "section": "speaking",
        "skill": "delivery",
        "difficulty": "medium",
        "question": "Which habit improves speaking delivery most effectively?",
        "options": [
            "Speaking with controlled pace and clarity",
            "Speaking as fast as possible",
            "Avoiding pauses completely",
            "Ignoring pronunciation",
        ],
        "correct_answer": "Speaking with controlled pace and clarity",
        "explanation": "Controlled delivery helps coherence and intelligibility.",
    },
    {
        "id": "dq_11",
        "section": "speaking",
        "skill": "support",
        "difficulty": "medium",
        "question": "Why are examples useful in speaking answers?",
        "options": [
            "They make the answer longer without meaning",
            "They support the main point",
            "They replace the need for organization",
            "They confuse the listener",
        ],
        "correct_answer": "They support the main point",
        "explanation": "Examples strengthen and clarify ideas.",
    },
    {
        "id": "dq_12",
        "section": "speaking",
        "skill": "coherence",
        "difficulty": "easy",
        "question": "Using linking words like 'first' and 'therefore' helps:",
        "options": [
            "Decrease coherence",
            "Organize ideas clearly",
            "Hide pronunciation problems",
            "Shorten the response too much",
        ],
        "correct_answer": "Organize ideas clearly",
        "explanation": "Transitions guide the listener through the response.",
    },
    {
        "id": "dq_13",
        "section": "writing",
        "skill": "thesis",
        "difficulty": "medium",
        "question": "The thesis statement in an essay should:",
        "options": [
            "Be unclear and broad",
            "Present the main argument",
            "Be written only in the conclusion",
            "Contain unrelated details",
        ],
        "correct_answer": "Present the main argument",
        "explanation": "The thesis communicates the essay's central claim.",
    },
    {
        "id": "dq_14",
        "section": "writing",
        "skill": "coherence",
        "difficulty": "medium",
        "question": "Paragraph unity means each paragraph should:",
        "options": [
            "Contain many unrelated ideas",
            "Focus on one central idea",
            "Avoid examples",
            "Repeat the title only",
        ],
        "correct_answer": "Focus on one central idea",
        "explanation": "Unified paragraphs stay centered on one point.",
    },
    {
        "id": "dq_15",
        "section": "writing",
        "skill": "development",
        "difficulty": "medium",
        "question": "What best improves essay development?",
        "options": [
            "Specific reasons and examples",
            "Very short unsupported claims",
            "Repeated topic sentences only",
            "Random quotations without explanation",
        ],
        "correct_answer": "Specific reasons and examples",
        "explanation": "Development comes from explanation and support.",
    },
    {
        "id": "dq_16",
        "section": "writing",
        "skill": "grammar",
        "difficulty": "easy",
        "question": "Which sentence is grammatically correct?",
        "options": [
            "She go to university every day.",
            "She goes to university every day.",
            "She going to university every day.",
            "She gone to university every day.",
        ],
        "correct_answer": "She goes to university every day.",
        "explanation": "Third person singular in present simple takes -s.",
    },
    {
        "id": "dq_17",
        "section": "grammar",
        "skill": "sentence_structure",
        "difficulty": "easy",
        "question": "Choose the correct sentence.",
        "options": [
            "Because the weather was cold.",
            "The weather was cold, we stayed inside.",
            "Because the weather was cold, we stayed inside.",
            "Was cold the weather, we stayed inside.",
        ],
        "correct_answer": "Because the weather was cold, we stayed inside.",
        "explanation": "This is a complete complex sentence.",
    },
    {
        "id": "dq_18",
        "section": "vocabulary",
        "skill": "academic_word",
        "difficulty": "medium",
        "question": "The word 'evaluate' most nearly means:",
        "options": ["Ignore", "Assess", "Translate", "Collect"],
        "correct_answer": "Assess",
        "explanation": "Evaluate means assess or judge.",
    },
    {
        "id": "dq_19",
        "section": "strategy",
        "skill": "time_management",
        "difficulty": "easy",
        "question": "The best TOEFL time-management strategy is to:",
        "options": [
            "Spend all time on one question",
            "Ignore the clock completely",
            "Monitor time and move efficiently",
            "Answer only easy sections",
        ],
        "correct_answer": "Monitor time and move efficiently",
        "explanation": "Balanced pacing is critical in TOEFL sections.",
    },
    {
        "id": "dq_20",
        "section": "strategy",
        "skill": "test_readiness",
        "difficulty": "easy",
        "question": "A full practice test is most useful for:",
        "options": [
            "Avoiding all study",
            "Building familiarity with timing and endurance",
            "Replacing all feedback",
            "Memorizing only one essay",
        ],
        "correct_answer": "Building familiarity with timing and endurance",
        "explanation": "Practice tests improve timing and readiness.",
    },
]

DIAGNOSTIC_QUESTIONS = getattr(
    diagnostic_module,
    "DIAGNOSTIC_QUESTIONS",
    deepcopy(DEFAULT_DIAGNOSTIC_QUESTIONS),
)
if not isinstance(DIAGNOSTIC_QUESTIONS, list) or not DIAGNOSTIC_QUESTIONS:
    DIAGNOSTIC_QUESTIONS = deepcopy(DEFAULT_DIAGNOSTIC_QUESTIONS)


# ============================================================
# Runtime Stores
# ============================================================

RUNTIME_STUDENTS: Dict[int, Dict[str, Any]] = {}
RUNTIME_LESSON_PROGRESS: Dict[int, Dict[str, Dict[str, Any]]] = {}
RUNTIME_ERROR_BANK: Dict[int, List[Any]] = {}
SPACED_REPETITION_ENGINE = SpacedRepetitionEngineClass()


# ============================================================
# UI Config
# ============================================================

DASHBOARD_CONFIG = {
    "theme": "academy-night",
    "refresh_interval_seconds": 20,
    "brand_name": "Yamen Academy 2026",
    "default_track_label": "PENDING",
}

PRODUCTION_CHECKLIST = [
    "جاهزية حساب الطالب",
    "التشخيص الأولي",
    "تفعيل الخطة الشخصية",
    "تفعيل بنك المفردات",
    "تفعيل نظام الدروس",
    "تفعيل مستودع الأخطاء",
    "جهوزية لوحة الإدارة",
]

TRACK_LABELS = {
    "foundation": "FOUNDATION",
    "toefl": "TOEFL",
    "advanced": "ADVANCED",
    "pending": "PENDING",
}

VOCAB_LIBRARY = {
    "foundation": [
        {"word": "analyze", "meaning": "يحلل", "example": "Students analyze the passage carefully."},
        {"word": "support", "meaning": "يدعم", "example": "Use examples to support your answer."},
        {"word": "evidence", "meaning": "دليل", "example": "Strong evidence improves writing quality."},
        {"word": "predict", "meaning": "يتوقع", "example": "Try to predict the lecture topic early."},
    ],
    "toefl": [
        {"word": "coherent", "meaning": "مترابط", "example": "A coherent essay is easier to follow."},
        {"word": "infer", "meaning": "يستنتج", "example": "You should infer the speaker's attitude from tone."},
        {"word": "distinct", "meaning": "متميز", "example": "Each paragraph needs a distinct purpose."},
        {"word": "evaluate", "meaning": "يقيّم", "example": "The professor asked students to evaluate the data."},
    ],
    "advanced": [
        {"word": "synthesize", "meaning": "يُركّب / يدمج", "example": "High scorers synthesize ideas across sources."},
        {"word": "articulate", "meaning": "يعبر بوضوح", "example": "She can articulate complex arguments fluently."},
        {"word": "nuanced", "meaning": "دقيق ومتعدد الطبقات", "example": "A nuanced response shows mature reasoning."},
        {"word": "rigorous", "meaning": "صارم / دقيق", "example": "The plan follows a rigorous weekly cycle."},
    ],
}


# ============================================================
# Default Student
# ============================================================

DEFAULT_STUDENT = {
    "uid": 1,
    "username": "إمبراطورة دانيا",
    "target_score": 105,
    "test_date": "2026-12-31",
    "package_type": 60,
    "student_stage": "pre-diagnostic",
    "study_hours_per_day": 3.0,
    "track": "advanced",
    "points": 1250,
    "current_lesson": "advanced_lesson_1",
    "diagnostic_score": 82,
}


# ============================================================
# Database Bridge
# ============================================================

def _db_get_student(uid: int):
    if database_module is None:
        return None

    fn = getattr(database_module, "get_student", None)
    if not callable(fn):
        return None

    try:
        return fn(uid=uid)
    except TypeError:
        try:
            return fn(uid)
        except Exception:
            return None
    except Exception:
        return None


def _db_list_students():
    if database_module is None:
        return []

    fn = getattr(database_module, "list_students", None)
    if not callable(fn):
        return []

    try:
        value = fn()
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _db_save_student(student_dict: Dict[str, Any]) -> bool:
    if database_module is None:
        return False

    uid = _safe_int(student_dict.get("uid"), 1)

    update_fn = getattr(database_module, "update_student", None)
    create_fn = getattr(database_module, "create_student", None)
    save_fn = getattr(database_module, "save_student", None)

    if callable(update_fn):
        try:
            update_fn(uid=uid, data=student_dict)
            return True
        except TypeError:
            try:
                update_fn(uid, student_dict)
                return True
            except Exception:
                pass
        except Exception:
            pass

        try:
            update_fn(student_dict)
            return True
        except Exception:
            pass

    if callable(save_fn):
        try:
            save_fn(student_dict)
            return True
        except Exception:
            pass

    if callable(create_fn):
        try:
            create_fn(student_dict)
            return True
        except Exception:
            pass

    return False


# ============================================================
# Student Helpers
# ============================================================

def _build_student_instance(data: Dict[str, Any]):
    payload = deepcopy(DEFAULT_STUDENT)
    if isinstance(data, dict):
        payload.update(data)

    payload["uid"] = _safe_int(payload.get("uid"), 1)
    payload["target_score"] = _safe_int(payload.get("target_score"), 100)
    payload["study_hours_per_day"] = _safe_float(payload.get("study_hours_per_day"), 2.0)
    payload["points"] = _safe_int(payload.get("points"), 0)
    payload["diagnostic_score"] = _safe_int(payload.get("diagnostic_score"), 0)
    payload["track"] = _normalize_track(payload.get("track"))
    if payload["track"] == "pending":
        payload["track"] = "foundation"
    payload["student_stage"] = _normalize_stage(payload.get("student_stage"))
    payload["package_type"] = payload.get("package_type", 60)

    try:
        return StudentClass(**payload)
    except Exception:
        return FallbackStudent(**payload)


def _student_to_dict(student: Any) -> Dict[str, Any]:
    payload = deepcopy(DEFAULT_STUDENT)
    payload.update(_ensure_dict(student))

    payload["uid"] = _safe_int(payload.get("uid"), 1)
    payload["username"] = _safe_str(payload.get("username"), "طالب أكاديمي")
    payload["target_score"] = _safe_int(payload.get("target_score"), 100)
    payload["study_hours_per_day"] = _safe_float(payload.get("study_hours_per_day"), 2.0)
    payload["points"] = _safe_int(payload.get("points"), 0)
    payload["diagnostic_score"] = _safe_int(payload.get("diagnostic_score"), 0)
    payload["track"] = _normalize_track(payload.get("track"))
    if payload["track"] == "pending":
        payload["track"] = "foundation"
    payload["student_stage"] = _normalize_stage(payload.get("student_stage"))
    payload["current_lesson"] = _safe_str(payload.get("current_lesson"), "")
    return payload


def _load_student(uid: int = 1):
    db_student = _db_get_student(uid)
    if db_student is not None:
        student_obj = _build_student_instance(_ensure_dict(db_student))
        RUNTIME_STUDENTS[uid] = _student_to_dict(student_obj)
        return student_obj

    runtime_student = RUNTIME_STUDENTS.get(uid)
    if runtime_student:
        return _build_student_instance(runtime_student)

    default_student = deepcopy(DEFAULT_STUDENT)
    default_student["uid"] = uid
    RUNTIME_STUDENTS[uid] = default_student
    _db_save_student(default_student)
    return _build_student_instance(default_student)


def _save_student(student_obj: Any):
    student_dict = _student_to_dict(student_obj)
    uid = _safe_int(student_dict.get("uid"), 1)
    RUNTIME_STUDENTS[uid] = student_dict
    _db_save_student(student_dict)
    return _build_student_instance(student_dict)


def _calculate_daily_progress(student_obj: Any) -> Dict[str, Any]:
    method = getattr(student_obj, "calculate_daily_progress_needed", None)
    if callable(method):
        try:
            value = method()
            if isinstance(value, dict):
                return value
        except Exception:
            pass

    student_dict = _student_to_dict(student_obj)
    exam_date = _safe_parse_date(student_dict.get("test_date"))
    today = date.today()
    days_remaining = max((exam_date - today).days, 1) if exam_date else _normalize_package_days(student_dict.get("package_type"))
    gap = max(_safe_int(student_dict.get("target_score"), 100) - _safe_int(student_dict.get("diagnostic_score"), 0), 0)
    daily_needed = round(gap / max(days_remaining, 1), 2)

    return {
        "days_remaining": days_remaining,
        "score_gap": gap,
        "score_per_day": daily_needed,
        "study_hours_per_day": _safe_float(student_dict.get("study_hours_per_day"), 2.0),
        "weekly_focus_units": max(1, math.ceil(gap / 5)) if gap else 1,
        "status": "steady" if daily_needed <= 0.5 else "intensive",
        "label": f"{daily_needed} نقطة يومياً تقريباً",
    }


# ============================================================
# Plan Helpers
# ============================================================

def _generate_success_plan(student_obj: Any) -> Dict[str, Any]:
    try:
        generator = PlanGeneratorClass(student_obj)
    except Exception:
        generator = FallbackPlanGenerator(student_obj)

    for method_name in ["generate_success_plan", "generate_plan", "create_plan", "build_success_plan"]:
        method = getattr(generator, method_name, None)
        if callable(method):
            try:
                result = method()
                if isinstance(result, dict):
                    return result
            except Exception:
                continue

    return FallbackPlanGenerator(student_obj).generate_success_plan()


def _normalize_success_plan(plan: Dict[str, Any], student_obj: Any) -> Dict[str, Any]:
    if not isinstance(plan, dict):
        plan = {}

    student_dict = _student_to_dict(student_obj)
    diagnostic_score = _safe_int(student_dict.get("diagnostic_score"), 0)
    target_score = _safe_int(student_dict.get("target_score"), 100)

    expected_scores = plan.get("expected_scores")
    if not isinstance(expected_scores, dict):
        expected_scores = {
            "day_1": diagnostic_score,
            "day_15": min(target_score, diagnostic_score + 4),
            "day_30": min(target_score, diagnostic_score + 10),
            "day_45": min(target_score, diagnostic_score + 16),
            "day_60": target_score,
        }

    milestones = plan.get("milestones")
    if not isinstance(milestones, list) or len(milestones) < 5:
        focus_order = plan.get("focus_order") if isinstance(plan.get("focus_order"), list) else ["speaking", "writing", "reading", "listening"]
        milestones = [
            {
                "day": 1,
                "title": "اليوم 1",
                "goal": "قراءة تقرير البداية وتحديد الأولويات",
                "focus": focus_order[:2],
                "expected_score": expected_scores.get("day_1", diagnostic_score),
            },
            {
                "day": 15,
                "title": "اليوم 15",
                "goal": "بناء القاعدة الأكاديمية وتنظيم الأداء",
                "focus": focus_order[:2],
                "expected_score": expected_scores.get("day_15", diagnostic_score + 4),
            },
            {
                "day": 30,
                "title": "اليوم 30",
                "goal": "تعزيز الثبات في القراءة والاستماع والتعبير",
                "focus": focus_order[:3],
                "expected_score": expected_scores.get("day_30", diagnostic_score + 10),
            },
            {
                "day": 45,
                "title": "اليوم 45",
                "goal": "معالجة الأخطاء عالية التكرار واختبارات محاكاة",
                "focus": focus_order[:3],
                "expected_score": expected_scores.get("day_45", diagnostic_score + 16),
            },
            {
                "day": 60,
                "title": "اليوم 60",
                "goal": "الجاهزية النهائية قبل الاختبار",
                "focus": focus_order,
                "expected_score": expected_scores.get("day_60", target_score),
            },
        ]

    weakness_percentages = plan.get("weakness_percentages")
    if not isinstance(weakness_percentages, dict):
        weakness_percentages = {
            "reading": 58,
            "listening": 52,
            "speaking": 66,
            "writing": 63,
        }

    study_weights = plan.get("study_weights")
    if not isinstance(study_weights, dict):
        study_weights = {
            "reading": 0.24,
            "listening": 0.22,
            "speaking": 0.28,
            "writing": 0.26,
        }

    focus_order = plan.get("focus_order")
    if not isinstance(focus_order, list):
        focus_order = sorted(weakness_percentages.keys(), key=lambda k: weakness_percentages.get(k, 0), reverse=True)

    return {
        "weakness_percentages": weakness_percentages,
        "study_weights": study_weights,
        "focus_order": focus_order,
        "expected_scores": expected_scores,
        "milestones": milestones,
    }


# ============================================================
# Lesson Factories
# ============================================================

def _lesson_question(question_id: str, question: str, options: List[str], correct_answer: str, explanation: str = ""):
    try:
        return LessonTestQuestionClass(
            question_id=question_id,
            question=question,
            options=options,
            correct_answer=correct_answer,
            explanation=explanation,
        )
    except Exception:
        return FallbackLessonTestQuestion(
            question_id=question_id,
            question=question,
            options=options,
            correct_answer=correct_answer,
            explanation=explanation,
        )


def _lesson_exercise(exercise_id: str, prompt: str, exercise_type: str = "short_text", expected_answer: str = ""):
    try:
        return LessonExerciseClass(
            exercise_id=exercise_id,
            prompt=prompt,
            exercise_type=exercise_type,
            expected_answer=expected_answer,
        )
    except Exception:
        return FallbackLessonExercise(
            exercise_id=exercise_id,
            prompt=prompt,
            exercise_type=exercise_type,
            expected_answer=expected_answer,
        )


def _lesson_item(
    lesson_id: str,
    track: str,
    order: int,
    title: str,
    objective: str,
    content_summary: str,
    content_blocks: List[str],
    xp_reward: int,
    pass_threshold: float,
    exercises: List[Any],
    lesson_test: List[Any],
):
    try:
        return LessonClass(
            lesson_id=lesson_id,
            track=track,
            order=order,
            title=title,
            objective=objective,
            content_summary=content_summary,
            content_blocks=content_blocks,
            xp_reward=xp_reward,
            pass_threshold=pass_threshold,
            exercises=exercises,
            lesson_test=lesson_test,
        )
    except Exception:
        return FallbackLesson(
            lesson_id=lesson_id,
            track=track,
            order=order,
            title=title,
            objective=objective,
            content_summary=content_summary,
            content_blocks=content_blocks,
            xp_reward=xp_reward,
            pass_threshold=pass_threshold,
            exercises=exercises,
            lesson_test=lesson_test,
        )


# ============================================================
# Lessons Catalog
# ============================================================

def _build_lesson_catalog() -> Dict[str, List[Any]]:
    foundation_lessons = [
        _lesson_item(
            lesson_id="foundation_lesson_1",
            track="foundation",
            order=1,
            title="Foundation Reading Basics",
            objective="فهم الفكرة الرئيسة والتفاصيل الأساسية في النصوص القصيرة.",
            content_summary="درس تأسيسي لبناء مهارة قراءة الفكرة الرئيسة والتمييز بين الفكرة والدعم.",
            content_blocks=[
                "ابدأ دائماً بعنوان النص والجملة الأولى من كل فقرة.",
                "ابحث عن الفكرة العامة قبل التفاصيل.",
                "استخدم الكلمات الانتقالية لاكتشاف اتجاه الفقرة.",
                "لا تضيّع الوقت على كلمة واحدة مجهولة.",
            ],
            xp_reward=90,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("foundation_l1_e1", "اكتب جملة تشرح الفرق بين main idea و detail."),
                _lesson_exercise("foundation_l1_e2", "اقرأ فقرة قصيرة وحدد الجملة الأكثر تمثيلاً للفكرة الرئيسة."),
            ],
            lesson_test=[
                _lesson_question("foundation_l1_q1", "What is the main idea?", ["A small detail", "The central message", "A grammar rule", "A date"], "The central message"),
                _lesson_question("foundation_l1_q2", "Supporting details help the reader:", ["Forget the point", "Understand the main idea", "Skip the text", "Memorize punctuation"], "Understand the main idea"),
                _lesson_question("foundation_l1_q3", "A good reader first looks for:", ["Every unknown word", "The overall topic", "All footnotes", "The author photo"], "The overall topic"),
                _lesson_question("foundation_l1_q4", "A topic sentence usually tells:", ["The paragraph's main point", "A random example", "The essay conclusion", "A spelling list"], "The paragraph's main point"),
                _lesson_question("foundation_l1_q5", "If a paragraph gives examples only, they usually:", ["Support a point", "Replace the title", "End the essay", "Remove coherence"], "Support a point"),
            ],
        ),
        _lesson_item(
            lesson_id="foundation_lesson_2",
            track="foundation",
            order=2,
            title="Foundation Listening Notes",
            objective="تدوين الملاحظات بشكل فعّال واستخراج الفكرة العامة.",
            content_summary="درس تأسيسي في التقاط النقاط الرئيسية في الاستماع الأكاديمي.",
            content_blocks=[
                "اكتب الكلمات المفتاحية فقط.",
                "فرّق بين main point و supporting detail.",
                "تابع نبرة المتحدث لمعرفة الهدف.",
                "رتّب الملاحظات حسب الانتقال بين الأفكار.",
            ],
            xp_reward=100,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("foundation_l2_e1", "اكتب 3 كلمات مفتاحية يمكن تدوينها أثناء محاضرة قصيرة."),
                _lesson_exercise("foundation_l2_e2", "اشرح متى يجب تدوين مثال ومتى تكتفي بعنوان الفكرة."),
            ],
            lesson_test=[
                _lesson_question("foundation_l2_q1", "Good note-taking focuses on:", ["Main points", "Every article", "Only numbers", "Spelling all words"], "Main points"),
                _lesson_question("foundation_l2_q2", "The phrase 'let's move on' signals:", ["A transition", "A conclusion forever", "An argument", "A joke only"], "A transition"),
                _lesson_question("foundation_l2_q3", "Why use abbreviations in notes?", ["To save time", "To hide meaning", "To forget content", "To avoid structure"], "To save time"),
                _lesson_question("foundation_l2_q4", "Listening for tone helps identify:", ["Speaker attitude", "Desk color", "Room size", "Keyboard model"], "Speaker attitude"),
                _lesson_question("foundation_l2_q5", "A lecture outline is useful because it:", ["Shows structure", "Replaces comprehension", "Removes details", "Ends note-taking"], "Shows structure"),
            ],
        ),
        _lesson_item(
            lesson_id="foundation_lesson_3",
            track="foundation",
            order=3,
            title="Foundation Speaking Response Shape",
            objective="بناء إجابة قصيرة واضحة مع سبب ومثال.",
            content_summary="درس تأسيسي في تنظيم إجابات التحدث لتكون واضحة ومدعومة.",
            content_blocks=[
                "ابدأ برأي مباشر.",
                "أعط سبباً واحداً واضحاً.",
                "أضف مثالاً صغيراً لكنه محدد.",
                "اختم بجملة تلخص موقفك.",
            ],
            xp_reward=110,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("foundation_l3_e1", "اكتب قالباً من 4 جمل لإجابة Speaking مستقلة."),
                _lesson_exercise("foundation_l3_e2", "اختر رأياً واحداً وادعمه بسبب ومثال."),
            ],
            lesson_test=[
                _lesson_question("foundation_l3_q1", "A good speaking answer starts with:", ["A clear opinion", "A long silence", "A dictionary quote", "An apology"], "A clear opinion"),
                _lesson_question("foundation_l3_q2", "Examples are important because they:", ["Support ideas", "Confuse listeners", "Replace structure", "Shorten answers"], "Support ideas"),
                _lesson_question("foundation_l3_q3", "Transitions like 'first' help:", ["Organization", "Pronunciation only", "Typing speed", "Grammar avoidance"], "Organization"),
                _lesson_question("foundation_l3_q4", "A controlled speaking pace improves:", ["Clarity", "Confusion", "Silence", "Background noise"], "Clarity"),
                _lesson_question("foundation_l3_q5", "The best response shape is usually:", ["Point + Reason + Example", "Example only", "Reason only", "Random ideas"], "Point + Reason + Example"),
            ],
        ),
    ]

    toefl_lessons = [
        _lesson_item(
            lesson_id="toefl_lesson_1",
            track="toefl",
            order=1,
            title="TOEFL Reading Strategy Stack",
            objective="تطوير الاستراتيجيات المتوسطة لفهم البنية والاستنتاج.",
            content_summary="درس متوسط في تحليل أسئلة القراءة الرسمية وتحديد نوع السؤال بسرعة.",
            content_blocks=[
                "حدّد نوع السؤال قبل القراءة العميقة.",
                "استخدم elimination عند الشك بين خيارين.",
                "الاستنتاج يجب أن يكون مدعوماً بالنص.",
                "عد إلى السطر المرجعي ثم وسّع القراءة سطراً أو سطرين.",
            ],
            xp_reward=120,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("toefl_l1_e1", "صنّف 4 أنواع من أسئلة القراءة الشائعة."),
                _lesson_exercise("toefl_l1_e2", "اشرح كيف تستخدم elimination في سؤال inference."),
            ],
            lesson_test=[
                _lesson_question("toefl_l1_q1", "Inference questions require:", ["Text-based reasoning", "Pure guessing", "Memorized essays", "No reading"], "Text-based reasoning"),
                _lesson_question("toefl_l1_q2", "A reference question asks you to:", ["Locate what a word refers to", "Write an essay", "Choose a lecture topic", "Predict a score"], "Locate what a word refers to"),
                _lesson_question("toefl_l1_q3", "Elimination helps because it:", ["Narrows choices", "Deletes the passage", "Skips logic", "Hides evidence"], "Narrows choices"),
                _lesson_question("toefl_l1_q4", "Best support for an answer comes from:", ["The passage", "A friend's opinion", "Memory alone", "A random website"], "The passage"),
                _lesson_question("toefl_l1_q5", "Question type awareness improves:", ["Speed and accuracy", "Only handwriting", "Only speaking", "Only attendance"], "Speed and accuracy"),
            ],
        ),
        _lesson_item(
            lesson_id="toefl_lesson_2",
            track="toefl",
            order=2,
            title="TOEFL Integrated Listening Map",
            objective="فهم أسئلة الغرض والاتجاه والعلاقة بين الأفكار في الاستماع.",
            content_summary="درس متوسط لتحسين قراءة خريطة المحاضرة والتمييز بين الفكرة والدعم.",
            content_blocks=[
                "لاحظ متى يقدّم المتحدث مثالاً ومتى يغيّر الفكرة.",
                "اسأل نفسك: لماذا قال هذه الجملة؟",
                "ركّز على التحول بين concepts.",
                "لا تكتب كل شيء، اكتب ما يُبنى عليه السؤال.",
            ],
            xp_reward=125,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("toefl_l2_e1", "اكتب مثالاً على phrase تدل على transition في المحاضرة."),
                _lesson_exercise("toefl_l2_e2", "اشرح الفرق بين purpose و detail question."),
            ],
            lesson_test=[
                _lesson_question("toefl_l2_q1", "A purpose question asks:", ["Why something was said", "How to spell it", "Where the student lives", "What the weather is"], "Why something was said"),
                _lesson_question("toefl_l2_q2", "A professor's example usually:", ["Supports a concept", "Ends the semester", "Replaces the lecture", "Changes the building"], "Supports a concept"),
                _lesson_question("toefl_l2_q3", "Transitions in lectures help identify:", ["Structure", "Accent only", "Microphone brand", "Attendance list"], "Structure"),
                _lesson_question("toefl_l2_q4", "Efficient notes capture:", ["Hierarchy of ideas", "Every article", "Only jokes", "Only names"], "Hierarchy of ideas"),
                _lesson_question("toefl_l2_q5", "Speaker attitude is often shown through:", ["Tone", "Desk color", "Lighting", "Slide font only"], "Tone"),
            ],
        ),
        _lesson_item(
            lesson_id="toefl_lesson_3",
            track="toefl",
            order=3,
            title="TOEFL Writing Structure Engine",
            objective="بناء مقال متماسك مع أطروحة وأمثلة وانتقالات قوية.",
            content_summary="درس متوسط في تنظيم كتابة TOEFL المستقلة أو الأكاديمية بشكل مرتّب.",
            content_blocks=[
                "ابدأ thesis واضحة وقابلة للدعم.",
                "كل فقرة جسم = فكرة واحدة + شرح + مثال.",
                "اربط الفقرات بانتقالات طبيعية.",
                "اختم بتلخيص لا يكرر النص حرفياً.",
            ],
            xp_reward=130,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("toefl_l3_e1", "اكتب thesis statement واضحة حول موضوع أكاديمي عام."),
                _lesson_exercise("toefl_l3_e2", "اكتب هيكل 4 فقرات لمقال TOEFL مستقل."),
            ],
            lesson_test=[
                _lesson_question("toefl_l3_q1", "A thesis statement should:", ["State the main argument", "Repeat the title only", "Be unrelated", "Contain all examples"], "State the main argument"),
                _lesson_question("toefl_l3_q2", "Paragraph unity means:", ["One central idea per paragraph", "Many random ideas", "No examples", "No transitions"], "One central idea per paragraph"),
                _lesson_question("toefl_l3_q3", "Specific examples improve:", ["Development", "Confusion", "Only punctuation", "Typing speed"], "Development"),
                _lesson_question("toefl_l3_q4", "A conclusion should:", ["Summarize and close the argument", "Introduce new major arguments", "Ignore the thesis", "Be one random word"], "Summarize and close the argument"),
                _lesson_question("toefl_l3_q5", "Transitions help the essay feel:", ["Coherent", "Disconnected", "Shorter only", "Noisier"], "Coherent"),
            ],
        ),
    ]

    advanced_lessons = [
        _lesson_item(
            lesson_id="advanced_lesson_1",
            track="advanced",
            order=1,
            title="Advanced Speaking Frameworks",
            objective="رفع جودة الإقناع والتنظيم والتدفق في Speaking المتقدم.",
            content_summary="درس متقدم لبناء إجابات ناضجة ذات منطق، دعم، وانتقال سلس.",
            content_blocks=[
                "ابدأ بموقف حاسم وعبارة افتتاحية دقيقة.",
                "نظّم الرد إلى claim و reasoning و illustration.",
                "استخدم لغة أكاديمية مرنة دون تعقيد مصطنع.",
                "خفف التكرار وركّز على precision.",
            ],
            xp_reward=145,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("advanced_l1_e1", "اكتب إطاراً متقدماً لإجابة Speaking من 45 ثانية."),
                _lesson_exercise("advanced_l1_e2", "أعد صياغة رأي بسيط إلى رأي أكاديمي أكثر نضجاً."),
            ],
            lesson_test=[
                _lesson_question("advanced_l1_q1", "A high-band speaking answer shows:", ["Clear logic and precise support", "Only speed", "Only long sentences", "No organization"], "Clear logic and precise support"),
                _lesson_question("advanced_l1_q2", "Precision in speaking means:", ["Choosing accurate language", "Speaking louder", "Speaking longer only", "Avoiding examples"], "Choosing accurate language"),
                _lesson_question("advanced_l1_q3", "Overusing filler words usually harms:", ["Delivery quality", "Keyboard speed", "Reading length", "Typing format"], "Delivery quality"),
                _lesson_question("advanced_l1_q4", "An effective speaking framework includes:", ["Claim + Reasoning + Illustration", "Illustration only", "Claim only", "Memorized script only"], "Claim + Reasoning + Illustration"),
                _lesson_question("advanced_l1_q5", "Advanced speaking should sound:", ["Natural and controlled", "Artificial and rushed", "Disconnected", "Monotone by force"], "Natural and controlled"),
            ],
        ),
        _lesson_item(
            lesson_id="advanced_lesson_2",
            track="advanced",
            order=2,
            title="Advanced Writing Precision",
            objective="ترقية جودة الكتابة من جيدة إلى مقنعة ومتقنة لغوياً.",
            content_summary="درس متقدم لتحسين الدقة اللغوية وتفادي التعميم والضعف الحجاجي.",
            content_blocks=[
                "اختر claim قابلة للدفاع وليست فضفاضة.",
                "كل example يجب أن يضيف معنى جديداً لا تكراراً.",
                "استخدم concession عند الحاجة لزيادة النضج.",
                "راجع الجمل من حيث clarity قبل التعقيد.",
            ],
            xp_reward=150,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("advanced_l2_e1", "حوّل claim عام إلى claim أكثر دقة وإقناعاً."),
                _lesson_exercise("advanced_l2_e2", "أضف concession sentence إلى فقرة حجاجية."),
            ],
            lesson_test=[
                _lesson_question("advanced_l2_q1", "Precision in writing improves:", ["Argument quality", "Only word count", "Only margins", "Only title size"], "Argument quality"),
                _lesson_question("advanced_l2_q2", "A concession sentence can:", ["Acknowledge another view strategically", "Delete the thesis", "End the essay suddenly", "Replace all evidence"], "Acknowledge another view strategically"),
                _lesson_question("advanced_l2_q3", "Strong development requires:", ["Distinct reasoning and support", "Repeated claims only", "No explanation", "Random vocabulary"], "Distinct reasoning and support"),
                _lesson_question("advanced_l2_q4", "Overly vague language often makes essays:", ["Less persuasive", "More precise", "More coherent automatically", "More grammatical automatically"], "Less persuasive"),
                _lesson_question("advanced_l2_q5", "Clarity should come:", ["Before forced complexity", "After random expansion", "Only in the conclusion", "Never"], "Before forced complexity"),
            ],
        ),
        _lesson_item(
            lesson_id="advanced_lesson_3",
            track="advanced",
            order=3,
            title="Advanced Full-Test Readiness",
            objective="دمج المهارات تحت ضغط الزمن للوصول إلى أداء مستقر عالي.",
            content_summary="درس متقدم لربط إدارة الوقت، التحليل، والثبات النفسي قبل الاختبار.",
            content_blocks=[
                "قسّم الاختبار ذهنياً إلى وحدات تحكم صغيرة.",
                "استخدم post-test review لتحديد الأخطاء عالية التكرار.",
                "ثبّت قوالب البدء والانتقال لاستخدامها تلقائياً.",
                "الاستقرار أهم من الاندفاع في المرحلة النهائية.",
            ],
            xp_reward=160,
            pass_threshold=70.0,
            exercises=[
                _lesson_exercise("advanced_l3_e1", "صمّم خطة زمنية شخصية ليوم محاكاة TOEFL كامل."),
                _lesson_exercise("advanced_l3_e2", "اكتب ثلاث قواعد تمنع الانهيار الذهني تحت الضغط."),
            ],
            lesson_test=[
                _lesson_question("advanced_l3_q1", "Full-test readiness depends heavily on:", ["Timing and stability", "Luck only", "Font size", "Desk color"], "Timing and stability"),
                _lesson_question("advanced_l3_q2", "Post-test review is useful because it:", ["Reveals recurring mistakes", "Replaces the test", "Deletes weak areas", "Changes official scores"], "Reveals recurring mistakes"),
                _lesson_question("advanced_l3_q3", "In the final stage, consistency is usually:", ["More valuable than emotional over-speed", "Less useful than panic", "Unrelated to performance", "Only for writing"], "More valuable than emotional over-speed"),
                _lesson_question("advanced_l3_q4", "A realistic mock test should:", ["Simulate timing and pressure", "Be paused every minute", "Skip weak sections", "Ignore endurance"], "Simulate timing and pressure"),
                _lesson_question("advanced_l3_q5", "The best final preparation is:", ["Structured repetition and review", "Random topic hopping", "No analysis", "Pure memorization without feedback"], "Structured repetition and review"),
            ],
        ),
    ]

    return {
        "foundation": foundation_lessons,
        "toefl": toefl_lessons,
        "advanced": advanced_lessons,
    }


LESSON_CATALOG = _build_lesson_catalog()
LESSON_TITLE_LOOKUP = {}

for track_key, lessons in LESSON_CATALOG.items():
    for lesson in lessons:
        LESSON_TITLE_LOOKUP[getattr(lesson, "lesson_id", "")] = getattr(lesson, "title", "")


# ============================================================
# Lesson Helpers
# ============================================================

def _serialize_lesson(lesson: Any) -> Dict[str, Any]:
    if lesson is None:
        return {}

    if hasattr(lesson, "to_dict") and callable(getattr(lesson, "to_dict")):
        try:
            return lesson.to_dict()
        except Exception:
            pass

    return {
        "lesson_id": getattr(lesson, "lesson_id", ""),
        "track": getattr(lesson, "track", ""),
        "order": getattr(lesson, "order", 0),
        "title": getattr(lesson, "title", ""),
        "objective": getattr(lesson, "objective", ""),
        "content_summary": getattr(lesson, "content_summary", ""),
        "content_blocks": list(getattr(lesson, "content_blocks", []) or []),
        "xp_reward": _safe_int(getattr(lesson, "xp_reward", 100), 100),
        "pass_threshold": _safe_float(getattr(lesson, "pass_threshold", 70.0), 70.0),
        "exercises": [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in (getattr(lesson, "exercises", []) or [])
        ],
        "lesson_test": [
            item.to_dict() if hasattr(item, "to_dict") else item
            for item in (getattr(lesson, "lesson_test", []) or [])
        ],
    }


def _get_lessons_for_track(track: str) -> List[Any]:
    return LESSON_CATALOG.get(_normalize_track(track), LESSON_CATALOG.get("foundation", []))


def _find_lesson_by_id(lesson_id: str) -> Optional[Any]:
    lesson_id = _safe_str(lesson_id, "")
    for lessons in LESSON_CATALOG.values():
        for lesson in lessons:
            if getattr(lesson, "lesson_id", "") == lesson_id:
                return lesson
    return None


def _get_next_lesson(track: str, lesson_id: str) -> Optional[Any]:
    lessons = _get_lessons_for_track(track)
    for index, lesson in enumerate(lessons):
        if getattr(lesson, "lesson_id", "") == lesson_id:
            if index + 1 < len(lessons):
                return lessons[index + 1]
            return None
    return None


def _ensure_lesson_progress_for_uid(uid: int, track: str) -> Dict[str, Dict[str, Any]]:
    normalized_track = _normalize_track(track)
    lessons = _get_lessons_for_track(normalized_track)

    if uid not in RUNTIME_LESSON_PROGRESS:
        RUNTIME_LESSON_PROGRESS[uid] = {}

    store = RUNTIME_LESSON_PROGRESS[uid]
    lesson_ids = [getattr(lesson, "lesson_id", "") for lesson in lessons]

    for index, lesson in enumerate(lessons):
        lesson_id = getattr(lesson, "lesson_id", "")
        if lesson_id not in store:
            store[lesson_id] = {
                "lesson_id": lesson_id,
                "track": normalized_track,
                "unlocked": True if index == 0 else False,
                "completed": False,
                "score": 0.0,
                "last_score": 0.0,
                "attempts": 0,
                "xp_awarded": 0,
                "unlocked_at": _utc_now_iso() if index == 0 else None,
                "completed_at": None,
            }
        else:
            store[lesson_id]["track"] = normalized_track
            store[lesson_id].setdefault("lesson_id", lesson_id)
            store[lesson_id].setdefault("unlocked", True if index == 0 else False)
            store[lesson_id].setdefault("completed", False)
            store[lesson_id].setdefault("score", 0.0)
            store[lesson_id].setdefault("last_score", 0.0)
            store[lesson_id].setdefault("attempts", 0)
            store[lesson_id].setdefault("xp_awarded", 0)
            store[lesson_id].setdefault("unlocked_at", _utc_now_iso() if index == 0 else None)
            store[lesson_id].setdefault("completed_at", None)

    unlocked_any = any(
        bool(store.get(lesson_id, {}).get("unlocked"))
        for lesson_id in lesson_ids
    )
    if not unlocked_any and lesson_ids:
        first_lesson_id = lesson_ids[0]
        store[first_lesson_id]["unlocked"] = True
        if not store[first_lesson_id].get("unlocked_at"):
            store[first_lesson_id]["unlocked_at"] = _utc_now_iso()

    return store


def _get_current_lesson_for_student(student_obj: Any) -> Optional[Any]:
    student_dict = _student_to_dict(student_obj)
    uid = _safe_int(student_dict.get("uid"), 1)
    track = _normalize_track(student_dict.get("track"))
    progress = _ensure_lesson_progress_for_uid(uid, track)

    current_lesson_id = _safe_str(student_dict.get("current_lesson"), "")
    current_lesson = _find_lesson_by_id(current_lesson_id)
    if current_lesson is not None:
        return current_lesson

    lessons = _get_lessons_for_track(track)
    for lesson in lessons:
        lesson_id = getattr(lesson, "lesson_id", "")
        if progress.get(lesson_id, {}).get("unlocked"):
            return lesson

    return lessons[0] if lessons else None


def _unlock_next_lesson(uid: int, track: str, current_lesson_id: str) -> Optional[Dict[str, Any]]:
    progress = _ensure_lesson_progress_for_uid(uid, track)
    next_lesson = _get_next_lesson(track, current_lesson_id)
    if next_lesson is None:
        return None

    next_lesson_id = getattr(next_lesson, "lesson_id", "")
    if next_lesson_id not in progress:
        progress[next_lesson_id] = {
            "lesson_id": next_lesson_id,
            "track": _normalize_track(track),
            "unlocked": True,
            "completed": False,
            "score": 0.0,
            "last_score": 0.0,
            "attempts": 0,
            "xp_awarded": 0,
            "unlocked_at": _utc_now_iso(),
            "completed_at": None,
        }
    else:
        progress[next_lesson_id]["unlocked"] = True
        if not progress[next_lesson_id].get("unlocked_at"):
            progress[next_lesson_id]["unlocked_at"] = _utc_now_iso()

    return {
        "lesson_id": next_lesson_id,
        "title": getattr(next_lesson, "title", ""),
        "track": getattr(next_lesson, "track", _normalize_track(track)),
    }


def _merge_lesson_with_progress(lesson: Any, progress_row: Dict[str, Any]) -> Dict[str, Any]:
    lesson_dict = _serialize_lesson(lesson)
    progress_row = progress_row or {}

    unlocked = bool(progress_row.get("unlocked"))
    completed = bool(progress_row.get("completed"))
    lesson_dict["progress"] = {
        "unlocked": unlocked,
        "completed": completed,
        "score": _safe_float(progress_row.get("score"), 0.0),
        "last_score": _safe_float(progress_row.get("last_score"), 0.0),
        "attempts": _safe_int(progress_row.get("attempts"), 0),
        "xp_awarded": _safe_int(progress_row.get("xp_awarded"), 0),
        "unlocked_at": progress_row.get("unlocked_at"),
        "completed_at": progress_row.get("completed_at"),
    }
    lesson_dict["locked"] = not unlocked
    lesson_dict["unlocked"] = unlocked
    lesson_dict["completed"] = completed
    return lesson_dict


def _normalize_choice_answer(raw_answer: Any, options: List[str]) -> str:
    answer_text = _safe_str(raw_answer, "")
    if not answer_text:
        return ""

    normalized_options = [str(option).strip() for option in options or []]

    if answer_text in normalized_options:
        return answer_text

    upper_answer = answer_text.upper()
    labels = [chr(65 + i) for i in range(len(normalized_options))]
    if upper_answer in labels:
        return normalized_options[labels.index(upper_answer)]

    return answer_text


def _extract_answer_sequence(raw_answers: Any, questions: List[Dict[str, Any]]) -> List[str]:
    if isinstance(raw_answers, list):
        extracted = []
        for index, question in enumerate(questions):
            answer = raw_answers[index] if index < len(raw_answers) else ""
            extracted.append(_normalize_choice_answer(answer, question.get("options", [])))
        return extracted

    if isinstance(raw_answers, dict):
        extracted = []
        for index, question in enumerate(questions):
            qid = _safe_str(question.get("id"), f"q_{index + 1}")
            answer = ""
            if qid in raw_answers:
                answer = raw_answers.get(qid)
            elif str(index) in raw_answers:
                answer = raw_answers.get(str(index))
            elif str(index + 1) in raw_answers:
                answer = raw_answers.get(str(index + 1))
            extracted.append(_normalize_choice_answer(answer, question.get("options", [])))
        return extracted

    return []


# ============================================================
# Error Bank Helpers
# ============================================================

def _serialize_error_record(record: Any) -> Dict[str, Any]:
    if record is None:
        return {}

    if hasattr(record, "to_dict") and callable(getattr(record, "to_dict")):
        try:
            return record.to_dict()
        except Exception:
            pass

    return {
        "error_id": getattr(record, "error_id", ""),
        "uid": _safe_int(getattr(record, "uid", 1), 1),
        "source_type": getattr(record, "source_type", ""),
        "source_ref": getattr(record, "source_ref", ""),
        "question_text": getattr(record, "question_text", ""),
        "student_answer": getattr(record, "student_answer", ""),
        "correct_answer": getattr(record, "correct_answer", ""),
        "explanation": getattr(record, "explanation", ""),
        "status": getattr(record, "status", "active"),
        "consecutive_correct": _safe_int(getattr(record, "consecutive_correct", 0), 0),
        "review_count": _safe_int(getattr(record, "review_count", 0), 0),
        "created_at": getattr(record, "created_at", _utc_now_iso()),
        "last_reviewed_at": getattr(record, "last_reviewed_at", None),
        "next_review_at": getattr(record, "next_review_at", _utc_now_iso()),
    }


def _get_error_bank_for_uid(uid: int) -> List[Any]:
    if uid not in RUNTIME_ERROR_BANK:
        RUNTIME_ERROR_BANK[uid] = []
    return RUNTIME_ERROR_BANK[uid]


def _record_is_due(record: Any) -> bool:
    due_method = getattr(record, "is_due", None)
    if callable(due_method):
        try:
            return bool(due_method())
        except Exception:
            pass

    next_review_at = _safe_parse_datetime(getattr(record, "next_review_at", None))
    if next_review_at is None:
        return True
    return datetime.utcnow() >= next_review_at


def _build_error_record(
    uid: int,
    source_type: str,
    source_ref: str,
    question_text: str,
    student_answer: str,
    correct_answer: str,
    explanation: str = "",
):
    error_id = f"err_{uid}_{int(datetime.utcnow().timestamp() * 1000)}"
    try:
        return ErrorRecordClass(
            error_id=error_id,
            uid=uid,
            source_type=source_type,
            source_ref=source_ref,
            question_text=question_text,
            student_answer=student_answer,
            correct_answer=correct_answer,
            explanation=explanation,
        )
    except Exception:
        return FallbackErrorRecord(
            error_id=error_id,
            uid=uid,
            source_type=source_type,
            source_ref=source_ref,
            question_text=question_text,
            student_answer=student_answer,
            correct_answer=correct_answer,
            explanation=explanation,
        )


def _add_error_to_bank(
    uid: int,
    source_type: str,
    source_ref: str,
    question_text: str,
    student_answer: str,
    correct_answer: str,
    explanation: str = "",
):
    bank = _get_error_bank_for_uid(uid)

    for existing in bank:
        if (
            _safe_str(getattr(existing, "source_type", ""), "") == _safe_str(source_type, "")
            and _safe_str(getattr(existing, "source_ref", ""), "") == _safe_str(source_ref, "")
            and _safe_str(getattr(existing, "question_text", ""), "") == _safe_str(question_text, "")
            and _safe_str(getattr(existing, "correct_answer", ""), "") == _safe_str(correct_answer, "")
            and _safe_str(getattr(existing, "status", "active"), "active") != "resolved"
        ):
            existing.student_answer = _safe_str(student_answer, "")
            existing.correct_answer = _safe_str(correct_answer, "")
            existing.explanation = _safe_str(explanation, "")
            if not getattr(existing, "next_review_at", None):
                existing.next_review_at = _utc_now_iso()
            return existing

    new_record = _build_error_record(
        uid=uid,
        source_type=source_type,
        source_ref=source_ref,
        question_text=question_text,
        student_answer=student_answer,
        correct_answer=correct_answer,
        explanation=explanation,
    )
    bank.append(new_record)
    return new_record


def _remove_error_record(uid: int, error_id: str) -> bool:
    bank = _get_error_bank_for_uid(uid)
    for index, record in enumerate(bank):
        if _safe_str(getattr(record, "error_id", ""), "") == _safe_str(error_id, ""):
            del bank[index]
            return True
    return False


def _find_error_record(uid: int, error_id: str):
    bank = _get_error_bank_for_uid(uid)
    for record in bank:
        if _safe_str(getattr(record, "error_id", ""), "") == _safe_str(error_id, ""):
            return record
    return None


def _error_bank_summary(uid: int) -> Dict[str, Any]:
    bank = _get_error_bank_for_uid(uid)
    total_errors = len(bank)
    due_errors = 0
    active_errors = 0
    reviewing_errors = 0
    resolved_errors = 0

    for record in bank:
        status = _safe_str(getattr(record, "status", "active"), "active")
        if status == "resolved":
            resolved_errors += 1
        elif status == "reviewing":
            reviewing_errors += 1
        else:
            active_errors += 1

        if status != "resolved" and _record_is_due(record):
            due_errors += 1

    return {
        "uid": uid,
        "total_errors": total_errors,
        "due_errors": due_errors,
        "active_errors": active_errors,
        "reviewing_errors": reviewing_errors,
        "resolved_errors": resolved_errors,
        "failed_count": total_errors,
        "due_count": due_errors,
        "resolved_count": resolved_errors,
    }


# ============================================================
# Placement Helpers
# ============================================================

def _placement_questions_public() -> List[Dict[str, Any]]:
    public_questions = []
    for index, item in enumerate(DIAGNOSTIC_QUESTIONS):
        if not isinstance(item, dict):
            continue
        public_questions.append({
            "id": _safe_str(item.get("id"), f"dq_{index + 1}"),
            "index": index + 1,
            "section": _safe_str(item.get("section"), "general"),
            "skill": _safe_str(item.get("skill"), "general"),
            "difficulty": _safe_str(item.get("difficulty"), "medium"),
            "question": _safe_str(item.get("question"), ""),
            "options": list(item.get("options", []) or []),
        })
    return public_questions


def _calculate_placement_result(raw_answers: Any) -> Dict[str, Any]:
    questions = [q for q in DIAGNOSTIC_QUESTIONS if isinstance(q, dict)]
    answers = _extract_answer_sequence(raw_answers, questions)

    details = []
    correct_count = 0

    for index, question in enumerate(questions):
        options = list(question.get("options", []) or [])
        user_answer = answers[index] if index < len(answers) else ""
        user_answer = _normalize_choice_answer(user_answer, options)
        correct_answer = _safe_str(question.get("correct_answer"), "")
        is_correct = user_answer == correct_answer

        if is_correct:
            correct_count += 1

        details.append({
            "id": _safe_str(question.get("id"), f"dq_{index + 1}"),
            "question": _safe_str(question.get("question"), ""),
            "section": _safe_str(question.get("section"), "general"),
            "skill": _safe_str(question.get("skill"), "general"),
            "options": options,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": _safe_str(question.get("explanation"), ""),
        })

    total_questions = len(questions)
    percentage = round((correct_count / total_questions) * 100, 2) if total_questions else 0.0
    estimated_toefl_score = round((correct_count / max(total_questions, 1)) * 120)

    if estimated_toefl_score < 60:
        track = "foundation"
    elif estimated_toefl_score < 90:
        track = "toefl"
    else:
        track = "advanced"

    return {
        "correct_count": correct_count,
        "total_questions": total_questions,
        "percentage": percentage,
        "estimated_toefl_score": estimated_toefl_score,
        "track": track,
        "details": details,
    }


def _update_student_after_placement(student_obj: Any, placement_result: Dict[str, Any]):
    student_dict = _student_to_dict(student_obj)
    student_dict["diagnostic_score"] = _safe_int(placement_result.get("estimated_toefl_score"), 0)
    student_dict["track"] = _normalize_track(placement_result.get("track"))
    student_dict["student_stage"] = "post-diagnostic"

    track_lessons = _get_lessons_for_track(student_dict["track"])
    if track_lessons:
        first_lesson_id = getattr(track_lessons[0], "lesson_id", "")
        student_dict["current_lesson"] = first_lesson_id

    updated_student = _build_student_instance(student_dict)
    updated_student = _save_student(updated_student)
    _ensure_lesson_progress_for_uid(_safe_int(student_dict["uid"], 1), student_dict["track"])
    return updated_student


# ============================================================
# Admin Helpers
# ============================================================

def _admin_safe_student_to_dict(student_obj):
    if student_obj is None:
        return {}

    if isinstance(student_obj, dict):
        return dict(student_obj)

    if hasattr(student_obj, "to_dict") and callable(getattr(student_obj, "to_dict")):
        try:
            return student_obj.to_dict()
        except Exception:
            pass

    data = {}
    for attr in [
        "uid",
        "username",
        "target_score",
        "test_date",
        "package_type",
        "student_stage",
        "study_hours_per_day",
        "track",
        "points",
        "current_lesson",
        "diagnostic_score",
    ]:
        try:
            data[attr] = getattr(student_obj, attr, None)
        except Exception:
            data[attr] = None
    return data


def _admin_collect_all_students():
    students = []

    try:
        db_students = _db_list_students()
        if isinstance(db_students, list) and db_students:
            students = db_students
    except Exception:
        students = []

    if not students and isinstance(RUNTIME_STUDENTS, dict) and RUNTIME_STUDENTS:
        students = list(RUNTIME_STUDENTS.values())

    if not students:
        students = [deepcopy(DEFAULT_STUDENT)]

    normalized_students = []
    for item in students:
        normalized_students.append(_admin_safe_student_to_dict(item))
    return normalized_students


def _admin_calculate_stats():
    students = _admin_collect_all_students()
    total_students = len(students)

    xp_values = []
    for student in students:
        points_value = student.get("points", 0)
        try:
            xp_values.append(float(points_value))
        except Exception:
            xp_values.append(0.0)

    average_xp = round(sum(xp_values) / len(xp_values), 2) if xp_values else 0.0

    return {
        "total_students": total_students,
        "average_xp": average_xp,
        "students": students,
    }


def _admin_questions_file_path():
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "diagnostic_questions.py")


def _admin_normalize_question_payload(question, index_number):
    if not isinstance(question, dict):
        raise ValueError(f"العنصر رقم {index_number} ليس كائناً صالحاً.")

    question_text = _safe_str(question.get("question"), "")
    if not question_text:
        raise ValueError(f"السؤال رقم {index_number} لا يحتوي على نص السؤال.")

    options = question.get("options", [])
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError(f"السؤال رقم {index_number} يجب أن يحتوي على خيارين على الأقل.")

    normalized_options = [str(opt).strip() for opt in options if str(opt).strip()]
    if len(normalized_options) < 2:
        raise ValueError(f"السؤال رقم {index_number} يحتوي على خيارات غير صالحة.")

    correct_answer = _safe_str(question.get("correct_answer"), "")
    if not correct_answer:
        raise ValueError(f"السؤال رقم {index_number} لا يحتوي على إجابة صحيحة.")

    if correct_answer not in normalized_options:
        labels = [chr(65 + i) for i in range(len(normalized_options))]
        if correct_answer.upper() in labels:
            correct_answer = normalized_options[labels.index(correct_answer.upper())]
        else:
            raise ValueError(f"الإجابة الصحيحة في السؤال رقم {index_number} يجب أن تطابق أحد الخيارات أو حرف الخيار.")

    return {
        "id": _safe_str(question.get("id"), f"diagnostic_{index_number}"),
        "section": _safe_str(question.get("section"), "general"),
        "skill": _safe_str(question.get("skill"), _safe_str(question.get("section"), "general")),
        "difficulty": _safe_str(question.get("difficulty"), "medium"),
        "question": question_text,
        "options": normalized_options,
        "correct_answer": correct_answer,
        "explanation": _safe_str(question.get("explanation"), ""),
    }


def _admin_write_diagnostic_questions_file(questions_list):
    serialized = json.dumps(questions_list, ensure_ascii=False, indent=4)
    file_content = (
        "# -*- coding: utf-8 -*-\n"
        "\"\"\"\n"
        "Yamen Academy 2026 - Diagnostic Questions\n"
        "هذا الملف يُدار ديناميكياً من لوحة الإدارة.\n"
        "\"\"\"\n\n"
        f"DIAGNOSTIC_QUESTIONS = {serialized}\n"
    )

    file_path = _admin_questions_file_path()
    with open(file_path, "w", encoding="utf-8") as file_obj:
        file_obj.write(file_content)
    return file_path


def _admin_reload_diagnostic_questions_runtime(questions_list):
    globals()["DIAGNOSTIC_QUESTIONS"] = questions_list


# ============================================================
# Base Routes
# ============================================================

@app.get("/")
def home_page():
    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)
    stage = _normalize_stage(student_dict.get("student_stage"))
    if stage == "pre-diagnostic":
        return redirect(url_for("placement_page"))
    return redirect(url_for("dashboard_page"))


@app.get("/placement")
def placement_page():
    return render_template(
        "placement.html",
        academy_name="Yamen Academy 2026",
        question_count=len(DIAGNOSTIC_QUESTIONS),
    )


@app.get("/dashboard")
def dashboard_page():
    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)

    try:
        db_student = _db_get_student(1)
        if db_student is not None:
            student = _build_student_instance(_ensure_dict(db_student))
            student_dict = _student_to_dict(student)
    except Exception:
        pass

    success_plan_raw = _generate_success_plan(student)
    success_plan = _normalize_success_plan(success_plan_raw, student)
    milestones = success_plan.get("milestones", [])
    daily_progress = _calculate_daily_progress(student)

    _ensure_lesson_progress_for_uid(_safe_int(student_dict.get("uid"), 1), student_dict.get("track"))
    current_lesson = _get_current_lesson_for_student(student)
    if current_lesson is not None and not student_dict.get("current_lesson"):
        student_dict["current_lesson"] = getattr(current_lesson, "lesson_id", "")
        student = _save_student(_build_student_instance(student_dict))

    return render_template(
        "dashboard.html",
        student=student,
        daily_progress=daily_progress,
        milestones=milestones,
        success_plan=success_plan,
        dashboard_config=DASHBOARD_CONFIG,
        production_checklist=PRODUCTION_CHECKLIST,
    )


@app.get("/lesson")
def lesson_page():
    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)
    track = _normalize_track(student_dict.get("track"))
    uid = _safe_int(student_dict.get("uid"), 1)
    progress = _ensure_lesson_progress_for_uid(uid, track)
    lessons = _get_lessons_for_track(track)

    lesson_payloads = []
    for lesson in lessons:
        lesson_id = getattr(lesson, "lesson_id", "")
        lesson_payloads.append(_merge_lesson_with_progress(lesson, progress.get(lesson_id, {})))

    current_lesson = _get_current_lesson_for_student(student)
    current_lesson_payload = _merge_lesson_with_progress(
        current_lesson,
        progress.get(getattr(current_lesson, "lesson_id", ""), {})
    ) if current_lesson else None

    return render_template(
        "lesson.html",
        student=student,
        lessons=lesson_payloads,
        current_lesson=current_lesson_payload,
    )


@app.get("/error-bank")
def error_bank_page():
    student = _load_student(uid=1)
    uid = _safe_int(_student_to_dict(student).get("uid"), 1)
    summary = _error_bank_summary(uid)
    all_items = [_serialize_error_record(record) for record in _get_error_bank_for_uid(uid)]
    due_items = [item for item in all_items if item.get("status") != "resolved"]

    return render_template(
        "error_bank.html",
        student=student,
        error_bank_items=due_items,
        error_bank_summary=summary,
        all_error_bank_items=all_items,
    )


# ============================================================
# Student Initialization API
# ============================================================

@app.post("/api/student/initialize")
def api_student_initialize():
    payload = _payload()

    username = _safe_str(payload.get("username"), "")
    target_score = _safe_int(payload.get("target_score"), 100)
    test_date = _safe_str(payload.get("test_date"), "")
    package_type = payload.get("package_type", 60)
    student_stage = _normalize_stage(payload.get("student_stage"))
    study_hours_per_day = _safe_float(payload.get("study_hours_per_day"), 2.0)

    if not username:
        return _api_error("حقل username مطلوب.", 400)

    if not test_date or _safe_parse_date(test_date) is None:
        return _api_error("حقل test_date مطلوب ويجب أن يكون بصيغة YYYY-MM-DD.", 400)

    if target_score <= 0:
        return _api_error("حقل target_score غير صالح.", 400)

    if study_hours_per_day <= 0:
        return _api_error("حقل study_hours_per_day يجب أن يكون أكبر من صفر.", 400)

    existing_student = _load_student(uid=1)
    existing_dict = _student_to_dict(existing_student)

    existing_dict.update({
        "uid": 1,
        "username": username,
        "target_score": target_score,
        "test_date": test_date,
        "package_type": package_type,
        "student_stage": student_stage,
        "study_hours_per_day": study_hours_per_day,
        "track": _normalize_track(existing_dict.get("track")) if existing_dict.get("track") else "foundation",
        "current_lesson": existing_dict.get("current_lesson") or "foundation_lesson_1",
    })

    student = _build_student_instance(existing_dict)
    saved_student = _save_student(student)

    return _api_ok(
        "تم تهيئة ملف الطالب بنجاح والاستعداد للاختبار التشخيصي.",
        student=_student_to_dict(saved_student),
        exam_ready=True,
        next_step="placement_exam",
    )


# ============================================================
# Placement APIs
# ============================================================

@app.get("/api/placement/questions")
def api_placement_questions():
    questions = _placement_questions_public()
    return _api_ok(
        "تم تحميل أسئلة الاختبار التشخيصي.",
        total_questions=len(questions),
        questions=questions,
    )


@app.post("/api/placement/submit")
def api_placement_submit():
    payload = _payload()
    raw_answers = payload.get("answers", payload)

    student = _load_student(uid=1)
    uid = _safe_int(_student_to_dict(student).get("uid"), 1)

    result = _calculate_placement_result(raw_answers)
    updated_student = _update_student_after_placement(student, result)

    for detail in result.get("details", []):
        if not detail.get("is_correct"):
            _add_error_to_bank(
                uid=uid,
                source_type="placement",
                source_ref=_safe_str(detail.get("id"), ""),
                question_text=_safe_str(detail.get("question"), ""),
                student_answer=_safe_str(detail.get("user_answer"), ""),
                correct_answer=_safe_str(detail.get("correct_answer"), ""),
                explanation=_safe_str(detail.get("explanation"), ""),
            )

    plan = _normalize_success_plan(_generate_success_plan(updated_student), updated_student)

    return _api_ok(
        "تم تصحيح الاختبار التشخيصي بنجاح.",
        result={
            "correct_count": result.get("correct_count", 0),
            "total_questions": result.get("total_questions", 0),
            "percentage": result.get("percentage", 0.0),
            "estimated_toefl_score": result.get("estimated_toefl_score", 0),
            "track": result.get("track", "foundation"),
        },
        personalized_track=result.get("track", "foundation"),
        student=_student_to_dict(updated_student),
        success_plan=plan,
        milestones=plan.get("milestones", []),
        dashboard_url=url_for("dashboard_page"),
        lesson_url=url_for("lesson_page"),
    )


# ============================================================
# Vocabulary + Review APIs
# ============================================================

@app.get("/api/vocabulary/session")
def api_vocabulary_session():
    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)
    requested_track = request.args.get("track")
    track = _normalize_track(requested_track or student_dict.get("track"))
    items = VOCAB_LIBRARY.get(track, VOCAB_LIBRARY.get("foundation", []))

    return _api_ok(
        "تم تحميل جلسة المفردات.",
        track=track,
        items=items,
        session_size=len(items),
    )


@app.get("/api/reviews/summary/<int:uid>")
def api_reviews_summary(uid: int):
    summary = _error_bank_summary(uid)
    return _api_ok("تم تحميل ملخص المراجعات.", summary=summary, **summary)


# ============================================================
# Lesson APIs
# ============================================================

@app.get("/api/lessons")
def api_lessons():
    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)
    uid = _safe_int(student_dict.get("uid"), 1)
    track = _normalize_track(student_dict.get("track"))

    progress = _ensure_lesson_progress_for_uid(uid, track)
    lessons = _get_lessons_for_track(track)

    lesson_payloads = []
    for lesson in lessons:
        lesson_id = getattr(lesson, "lesson_id", "")
        lesson_payloads.append(_merge_lesson_with_progress(lesson, progress.get(lesson_id, {})))

    return _api_ok(
        "تم تحميل دروس المسار الحالي.",
        track=track,
        current_track=track,
        lessons=lesson_payloads,
        current_lesson=student_dict.get("current_lesson"),
    )


@app.get("/api/lessons/current")
def api_lessons_current():
    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)
    uid = _safe_int(student_dict.get("uid"), 1)
    track = _normalize_track(student_dict.get("track"))
    progress = _ensure_lesson_progress_for_uid(uid, track)
    current_lesson = _get_current_lesson_for_student(student)

    if current_lesson is None:
        return _api_error("لا يوجد درس حالي متاح.", 404)

    lesson_id = getattr(current_lesson, "lesson_id", "")
    return _api_ok(
        "تم تحميل الدرس الحالي.",
        lesson=_merge_lesson_with_progress(current_lesson, progress.get(lesson_id, {})),
    )


@app.get("/api/lessons/<lesson_id>")
def api_lessons_detail(lesson_id: str):
    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)
    uid = _safe_int(student_dict.get("uid"), 1)
    track = _normalize_track(student_dict.get("track"))
    progress = _ensure_lesson_progress_for_uid(uid, track)

    lesson = _find_lesson_by_id(lesson_id)
    if lesson is None:
        return _api_error("الدرس غير موجود.", 404)

    lesson_track = _normalize_track(getattr(lesson, "track", "foundation"))
    if lesson_track != track:
        return _api_error("الدرس لا ينتمي إلى مسار الطالب الحالي.", 403)

    lesson_progress = progress.get(lesson_id, {})
    if not lesson_progress.get("unlocked"):
        return _api_error("الدرس ما زال مقفلاً.", 403)

    return _api_ok(
        "تم تحميل تفاصيل الدرس.",
        lesson=_merge_lesson_with_progress(lesson, lesson_progress),
    )


@app.post("/api/lessons/submit-quiz")
def api_lessons_submit_quiz():
    payload = _payload()
    lesson_id = _safe_str(payload.get("lesson_id"), "")
    raw_answers = payload.get("answers", [])

    if not lesson_id:
        return _api_error("حقل lesson_id مطلوب.", 400)

    student = _load_student(uid=1)
    student_dict = _student_to_dict(student)
    uid = _safe_int(student_dict.get("uid"), 1)
    track = _normalize_track(student_dict.get("track"))

    lesson = _find_lesson_by_id(lesson_id)
    if lesson is None:
        return _api_error("الدرس غير موجود.", 404)

    if _normalize_track(getattr(lesson, "track", "foundation")) != track:
        return _api_error("هذا الدرس لا ينتمي إلى مسار الطالب الحالي.", 403)

    progress = _ensure_lesson_progress_for_uid(uid, track)
    lesson_progress = progress.get(lesson_id, {})

    if not lesson_progress.get("unlocked"):
        return _api_error("الدرس الحالي مقفل ولا يمكن إرسال الاختبار.", 403)

    lesson_dict = _serialize_lesson(lesson)
    question_bank = lesson_dict.get("lesson_test", [])
    answers = _extract_answer_sequence(raw_answers, question_bank)

    evaluator = getattr(lesson, "evaluate_test", None)
    if callable(evaluator):
        try:
            result = evaluator(answers)
        except Exception:
            fallback_lesson = FallbackLesson(**lesson_dict)
            result = fallback_lesson.evaluate_test(answers)
    else:
        fallback_lesson = FallbackLesson(**lesson_dict)
        result = fallback_lesson.evaluate_test(answers)

    lesson_progress["attempts"] = _safe_int(lesson_progress.get("attempts"), 0) + 1
    lesson_progress["score"] = _safe_float(result.get("score_percentage"), 0.0)
    lesson_progress["last_score"] = _safe_float(result.get("score_percentage"), 0.0)

    for detail in result.get("details", []):
        if not detail.get("is_correct"):
            _add_error_to_bank(
                uid=uid,
                source_type="lesson_quiz",
                source_ref=lesson_id,
                question_text=_safe_str(detail.get("question"), ""),
                student_answer=_safe_str(detail.get("user_answer"), ""),
                correct_answer=_safe_str(detail.get("correct_answer"), ""),
                explanation=_safe_str(detail.get("explanation"), ""),
            )

    xp_awarded_now = 0
    unlocked_next = None

    if result.get("passed"):
        if not lesson_progress.get("completed"):
            lesson_progress["completed"] = True
            lesson_progress["completed_at"] = _utc_now_iso()
            xp_awarded_now = _safe_int(getattr(lesson, "xp_reward", 100), 100)
            lesson_progress["xp_awarded"] = _safe_int(lesson_progress.get("xp_awarded"), 0) + xp_awarded_now

            student_dict["points"] = _safe_int(student_dict.get("points"), 0) + xp_awarded_now
            unlocked_next = _unlock_next_lesson(uid, track, lesson_id)

            if unlocked_next is not None:
                student_dict["current_lesson"] = unlocked_next.get("lesson_id", lesson_id)
            else:
                student_dict["current_lesson"] = lesson_id

            student = _save_student(_build_student_instance(student_dict))
        else:
            unlocked_next = _get_next_lesson(track, lesson_id)
            if unlocked_next is not None:
                unlocked_next = {
                    "lesson_id": getattr(unlocked_next, "lesson_id", ""),
                    "title": getattr(unlocked_next, "title", ""),
                    "track": getattr(unlocked_next, "track", track),
                }
    else:
        student = _save_student(_build_student_instance(student_dict))

    refreshed_progress = _ensure_lesson_progress_for_uid(uid, track)
    lessons_payload = []
    for item in _get_lessons_for_track(track):
        item_id = getattr(item, "lesson_id", "")
        lessons_payload.append(_merge_lesson_with_progress(item, refreshed_progress.get(item_id, {})))

    return _api_ok(
        "تم استلام اختبار الدرس.",
        result=result,
        passed=bool(result.get("passed")),
        xp_awarded=xp_awarded_now,
        unlocked_next_lesson=unlocked_next,
        student=_student_to_dict(student),
        lessons=lessons_payload,
    )


# ============================================================
# Error Bank APIs
# ============================================================

@app.get("/api/error-bank")
def api_error_bank():
    student = _load_student(uid=1)
    uid = _safe_int(_student_to_dict(student).get("uid"), 1)

    bank = _get_error_bank_for_uid(uid)
    all_items = [_serialize_error_record(record) for record in bank]
    due_items = [
        item for item, original in zip(all_items, bank)
        if item.get("status") != "resolved" and _record_is_due(original)
    ]

    return _api_ok(
        "تم تحميل بنك الأخطاء.",
        uid=uid,
        due_items=due_items,
        all_items=all_items,
        summary=_error_bank_summary(uid),
    )


@app.post("/api/error-bank/review")
def api_error_bank_review():
    payload = _payload()
    error_id = _safe_str(payload.get("error_id"), "")
    if not error_id:
        return _api_error("حقل error_id مطلوب.", 400)

    student = _load_student(uid=1)
    uid = _safe_int(_student_to_dict(student).get("uid"), 1)
    record = _find_error_record(uid, error_id)

    if record is None:
        return _api_error("عنصر الخطأ غير موجود.", 404)

    is_correct = payload.get("is_correct", None)
    if is_correct is None:
        submitted_answer = _safe_str(payload.get("answer"), "")
        correct_answer = _safe_str(getattr(record, "correct_answer", ""), "")
        normalized_answer = _normalize_choice_answer(submitted_answer, [])
        is_correct = normalized_answer == correct_answer
    else:
        is_correct = bool(is_correct)

    processor = getattr(SPACED_REPETITION_ENGINE, "process_review", None)
    if not callable(processor):
        processor = FallbackSpacedRepetitionEngine().process_review

    result = processor(record, bool(is_correct))

    deleted = False
    if _safe_str(result.get("action"), "") == "delete":
        deleted = _remove_error_record(uid, error_id)

    bank = _get_error_bank_for_uid(uid)
    all_items = [_serialize_error_record(item) for item in bank]
    due_items = [
        item for item, original in zip(all_items, bank)
        if item.get("status") != "resolved" and _record_is_due(original)
    ]

    return _api_ok(
        result.get("message", "تم تحديث حالة عنصر الخطأ."),
        deleted=deleted,
        reviewed_error=None if deleted else _serialize_error_record(record),
        due_items=due_items,
        all_items=all_items,
        summary=_error_bank_summary(uid),
    )


# ============================================================
# Health API
# ============================================================

@app.get("/api/health")
def api_health():
    return _api_ok(
        "الخادم يعمل بشكل طبيعي.",
        service="Yamen Academy 2026",
        status="healthy",
        utc_time=_utc_now_iso(),
        diagnostic_questions=len(DIAGNOSTIC_QUESTIONS),
        lesson_tracks=list(LESSON_CATALOG.keys()),
    )


# ============================================================
# Error Handlers
# ============================================================

@app.errorhandler(404)
def not_found_handler(error):
    if request.path.startswith("/api/"):
        return _api_error("المسار المطلوب غير موجود.", 404)
    return "<h1>404</h1><p>الصفحة المطلوبة غير موجودة.</p>", 404


@app.errorhandler(405)
def method_not_allowed_handler(error):
    if request.path.startswith("/api/"):
        return _api_error("الطريقة غير مسموحة لهذا المسار.", 405)
    return "<h1>405</h1><p>الطريقة غير مسموحة.</p>", 405


@app.errorhandler(413)
def payload_too_large_handler(error):
    if request.path.startswith("/api/"):
        return _api_error("حجم الطلب أكبر من الحد المسموح.", 413)
    return "<h1>413</h1><p>حجم الطلب أكبر من الحد المسموح.</p>", 413


@app.errorhandler(500)
def internal_error_handler(error):
    traceback.print_exc()
    if request.path.startswith("/api/"):
        return _api_error("حدث خطأ داخلي في الخادم.", 500)
    return "<h1>500</h1><p>حدث خطأ داخلي في الخادم.</p>", 500


# ============================================================
# Main Entry
# ============================================================

if __name__ == "__main__":
    print("==============================================")
    print("Yamen Academy 2026 Backend Starting...")
    print(f"Templates directory: {TEMPLATES_DIR}")
    print(f"Static directory: {STATIC_DIR}")
    print(f"Diagnostic questions loaded: {len(DIAGNOSTIC_QUESTIONS)}")
    print(f"Lesson tracks loaded: {', '.join(LESSON_CATALOG.keys())}")
    print("Server ready on http://127.0.0.1:5000")
    print("==============================================")
    app.run(host="0.0.0.0", port=5000, debug=True)
# ============================================================
# Admin Dashboard + Dynamic Diagnostic Questions Update
# ============================================================

def _admin_questions_file_path():
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "diagnostic_questions.py")


def _admin_normalize_question_payload(question, index_number):
    if not isinstance(question, dict):
        raise ValueError(f"العنصر رقم {index_number} ليس كائناً صالحاً.")

    question_text = str(question.get("question", "")).strip()
    if not question_text:
        raise ValueError(f"السؤال رقم {index_number} لا يحتوي على نص السؤال.")

    options = question.get("options", [])
    if not isinstance(options, list):
        raise ValueError(f"خيارات السؤال رقم {index_number} يجب أن تكون مصفوفة.")

    normalized_options = [str(option).strip() for option in options if str(option).strip()]
    if len(normalized_options) != 4:
        raise ValueError(f"السؤال رقم {index_number} يجب أن يحتوي على 4 خيارات بالضبط.")

    correct_answer = str(question.get("correct_answer", "")).strip()
    if not correct_answer:
        raise ValueError(f"السؤال رقم {index_number} لا يحتوي على الإجابة الصحيحة.")

    if correct_answer not in normalized_options:
        labels = ["A", "B", "C", "D"]
        if correct_answer.upper() in labels:
            correct_answer = normalized_options[labels.index(correct_answer.upper())]
        else:
            raise ValueError(
                f"الإجابة الصحيحة في السؤال رقم {index_number} يجب أن تطابق أحد الخيارات أو تكون A/B/C/D."
            )

    return {
        "id": str(question.get("id", f"dq_{index_number}")).strip() or f"dq_{index_number}",
        "section": str(question.get("section", "general")).strip() or "general",
        "skill": str(question.get("skill", "general")).strip() or "general",
        "difficulty": str(question.get("difficulty", "medium")).strip() or "medium",
        "question": question_text,
        "options": normalized_options,
        "correct_answer": correct_answer,
        "explanation": str(question.get("explanation", "")).strip(),
    }


def _admin_write_diagnostic_questions_file(questions_list):
    serialized = json.dumps(questions_list, ensure_ascii=False, indent=4)

    file_content = (
        "# -*- coding: utf-8 -*-\n"
        "\"\"\"\n"
        "Yamen Academy 2026 - Diagnostic Questions\n"
        "هذا الملف يُدار ديناميكياً من لوحة الإدارة.\n"
        "\"\"\"\n\n"
        f"DIAGNOSTIC_QUESTIONS = {serialized}\n"
    )

    file_path = _admin_questions_file_path()
    with open(file_path, "w", encoding="utf-8") as file_obj:
        file_obj.write(file_content)

    return file_path


def _admin_reload_questions_runtime(questions_list):
    globals()["DIAGNOSTIC_QUESTIONS"] = questions_list


@app.get("/admin")
def admin_dashboard_page():
    questions = globals().get("DIAGNOSTIC_QUESTIONS", [])
    if not isinstance(questions, list):
        questions = []

    students = []
    try:
        students = _db_list_students()
    except Exception:
        students = []

    if not students and isinstance(RUNTIME_STUDENTS, dict):
        students = list(RUNTIME_STUDENTS.values())

    if not students:
        students = [deepcopy(DEFAULT_STUDENT)]

    normalized_students = []
    for student in students:
        if isinstance(student, dict):
            normalized_students.append(student)
        else:
            normalized_students.append(_ensure_dict(student))

    total_students = len(normalized_students)

    xp_values = []
    for student in normalized_students:
        try:
            xp_values.append(float(student.get("points", 0)))
        except Exception:
            xp_values.append(0.0)

    average_xp = round(sum(xp_values) / len(xp_values), 2) if xp_values else 0.0

    return render_template(
        "admin.html",
        total_students=total_students,
        average_xp=average_xp,
        current_questions=questions,
    )


@app.post("/api/admin/questions/update")
def admin_questions_update_handler():
    try:
        payload = request.get_json(silent=True)

        if payload is None:
            return jsonify({
                "success": False,
                "message": "لم يتم إرسال JSON صالح."
            }), 400

        incoming_questions = None
        if isinstance(payload, list):
            incoming_questions = payload
        elif isinstance(payload, dict):
            incoming_questions = payload.get("questions")

        if not isinstance(incoming_questions, list):
            return jsonify({
                "success": False,
                "message": "يجب إرسال مصفوفة الأسئلة داخل الحقل questions أو كمصفوفة مباشرة."
            }), 400

        normalized_questions = []
        for index, question in enumerate(incoming_questions, start=1):
            normalized_questions.append(_admin_normalize_question_payload(question, index))

        file_path = _admin_write_diagnostic_questions_file(normalized_questions)
        _admin_reload_questions_runtime(normalized_questions)

        return jsonify({
            "success": True,
            "message": "تم تحديث بنك الأسئلة التشخيصية بنجاح.",
            "questions_count": len(normalized_questions),
            "file_path": file_path.replace("\\", "/"),
        }), 200

    except ValueError as exc:
        return jsonify({
            "success": False,
            "message": str(exc)
        }), 400

    except Exception as exc:
        return jsonify({
            "success": False,
            "message": f"تعذر تحديث الأسئلة: {str(exc)}"
        }), 500
