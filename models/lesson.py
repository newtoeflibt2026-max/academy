# -*- coding: utf-8 -*-

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class LessonExercise:
    exercise_id: str
    title: str
    prompt: str
    exercise_type: str = "short_answer"
    skill: str = "general"
    expected_answer: str = ""
    explanation: str = ""
    options: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LessonTestQuestion:
    question_id: int
    prompt: str
    options: Dict[str, str]
    correct_answer: str
    explanation: str = ""
    skill: str = "general"

    def to_dict(self, include_correct_answer: bool = False) -> Dict[str, Any]:
        payload = {
            "question_id": self.question_id,
            "prompt": self.prompt,
            "options": dict(self.options),
            "explanation": self.explanation,
            "skill": self.skill,
        }
        if include_correct_answer:
            payload["correct_answer"] = self.correct_answer
        return payload


@dataclass
class Lesson:
    lesson_id: str
    track: str
    order: int
    title: str
    objective: str
    content_summary: str
    exercises: List[LessonExercise] = field(default_factory=list)
    lesson_test: List[LessonTestQuestion] = field(default_factory=list)
    xp_reward: int = 100
    pass_threshold: int = 70
    unlocks_next_lesson_id: str = ""

    def max_test_score(self) -> int:
        if not self.lesson_test:
            return 0
        return len(self.lesson_test) * 100

    def evaluate_test(self, answers: Dict[Any, str]) -> Dict[str, Any]:
        normalized_answers: Dict[int, str] = {}
        for key, value in (answers or {}).items():
            try:
                question_id = int(key)
            except Exception:
                continue
            normalized_answers[question_id] = str(value).strip().upper()

        total_questions = len(self.lesson_test)
        if total_questions == 0:
            return {
                "score": 0,
                "correct_count": 0,
                "total_questions": 0,
                "passed": False,
                "breakdown": [],
            }

        correct_count = 0
        breakdown: List[Dict[str, Any]] = []

        for question in self.lesson_test:
            selected_answer = normalized_answers.get(question.question_id, "")
            correct_answer = str(question.correct_answer).strip().upper()
            is_correct = selected_answer == correct_answer

            if is_correct:
                correct_count += 1

            breakdown.append(
                {
                    "question_id": question.question_id,
                    "skill": question.skill,
                    "selected_answer": selected_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "prompt": question.prompt,
                    "explanation": question.explanation,
                }
            )

        score = round((correct_count / total_questions) * 100)
        passed = score >= int(self.pass_threshold)

        return {
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "passed": passed,
            "breakdown": breakdown,
        }

    def to_dict(self, include_test_answers: bool = False) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "track": self.track,
            "order": self.order,
            "title": self.title,
            "objective": self.objective,
            "content_summary": self.content_summary,
            "xp_reward": self.xp_reward,
            "pass_threshold": self.pass_threshold,
            "unlocks_next_lesson_id": self.unlocks_next_lesson_id,
            "exercises": [exercise.to_dict() for exercise in self.exercises],
            "lesson_test": [
                question.to_dict(include_correct_answer=include_test_answers)
                for question in self.lesson_test
            ],
        }
