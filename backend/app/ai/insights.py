"""Insight generation.

An LLM is used when ``OPENAI_API_KEY`` is configured; otherwise a deterministic
rule-based generator produces the same shape of output so the product works
offline and in CI. Only aggregated metrics are sent to the model - never raw
personal data such as email addresses or dates of birth.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.config import get_settings
from app.schemas import StudentMetrics

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT = (
    "You are an academic advisor assistant for a school management system. "
    "You receive aggregated, anonymised performance metrics for one student and "
    "must reply with strict JSON of the form "
    '{"summary": string, "recommendations": [string, ...]}. '
    "The summary is at most three sentences describing performance trends. "
    "Provide three to five concrete, actionable, encouraging study recommendations "
    "grounded only in the supplied metrics. Never invent data."
)


def _metrics_payload(metrics: StudentMetrics) -> dict[str, object]:
    return {
        "attendance_rate": metrics.attendance_rate,
        "sessions_recorded": metrics.sessions_recorded,
        "overall_average": metrics.overall_average,
        "marks_trend": metrics.marks_trend,
        "trend_delta": metrics.trend_delta,
        "assignment_completion_rate": metrics.assignment_completion_rate,
        "missing_assignments": metrics.missing_assignments,
        "risk_level": metrics.risk_level,
        "risk_reasons": metrics.risk_reasons,
        "subjects": [
            {
                "name": subject.subject_name,
                "average_percentage": subject.average_percentage,
                "trend": subject.trend,
            }
            for subject in metrics.subject_performance
        ],
    }


def generate_rule_based(metrics: StudentMetrics) -> tuple[str, list[str]]:
    parts: list[str] = []
    if metrics.sessions_recorded:
        parts.append(
            f"{metrics.student_name} attended {metrics.attendance_rate:.1f}% of "
            f"{metrics.sessions_recorded} recorded sessions"
        )
    else:
        parts.append(f"No attendance has been recorded yet for {metrics.student_name}")

    if metrics.subject_performance:
        parts.append(
            f"and is averaging {metrics.overall_average:.1f}% across "
            f"{len(metrics.subject_performance)} subject(s) with a {metrics.marks_trend} trend"
        )
    else:
        parts.append("and has no graded assessments yet")

    summary = " ".join(parts) + f". Overall academic risk is {metrics.risk_level}."

    recommendations: list[str] = []
    if metrics.weakest_subjects:
        recommendations.append(
            "Prioritise focused revision in "
            + ", ".join(metrics.weakest_subjects)
            + " with weekly practice sets and a follow-up quiz."
        )
    declining = [s.subject_name for s in metrics.subject_performance if s.trend == "declining"]
    if declining:
        recommendations.append(
            "Schedule a teacher check-in for "
            + ", ".join(declining)
            + " where scores are slipping."
        )
    if metrics.sessions_recorded and metrics.attendance_rate < settings.attendance_risk_threshold:
        recommendations.append(
            "Improve class attendance: notify the parent and agree on a weekly attendance target."
        )
    if metrics.missing_assignments:
        recommendations.append(
            f"Clear the {metrics.missing_assignments} outstanding assignment(s) before the next "
            "assessment cycle."
        )
    if metrics.strongest_subjects:
        recommendations.append(
            "Build confidence by using strengths in "
            + ", ".join(metrics.strongest_subjects)
            + " as a model for study habits in weaker subjects."
        )
    if not recommendations:
        recommendations.append("Maintain the current study routine and keep attendance consistent.")
    return summary, recommendations[:5]


def _generate_with_llm(metrics: StudentMetrics) -> tuple[str, list[str]] | None:
    if not settings.openai_api_key:
        return None
    try:
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(_metrics_payload(metrics))},
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        summary = str(parsed["summary"])
        recommendations = [str(item) for item in parsed["recommendations"]]
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("LLM insight generation failed, falling back to rules: %s", exc)
        return None
    if not summary or not recommendations:
        return None
    return summary, recommendations


def generate_insight(metrics: StudentMetrics) -> tuple[str, list[str], str]:
    """Return ``(summary, recommendations, source)``."""
    llm_result = _generate_with_llm(metrics)
    if llm_result is not None:
        return llm_result[0], llm_result[1], "llm"
    summary, recommendations = generate_rule_based(metrics)
    return summary, recommendations, "rules"
