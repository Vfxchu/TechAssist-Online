"""
Solution memory service.

Stores successful fix solutions and matches them to new tickets
so the AI can suggest proven solutions before searching the web.
"""
import logging
from sqlalchemy.orm import Session
from models.solution import Solution

logger = logging.getLogger(__name__)


def find_matching_solution(
    db: Session,
    category: str,
    os_name: str,
    software: str,
    issue_keywords: list[str],
    threshold: float = 0.75,
) -> Solution | None:
    """
    Search past solutions for a close match.
    Returns the best match if its score exceeds the threshold, otherwise None.
    """
    candidates = (
        db.query(Solution)
        .filter(Solution.category == category)
        .order_by(Solution.success_count.desc())
        .all()
    )

    best_match: Solution | None = None
    best_score = 0.0

    for sol in candidates:
        score = _score(sol, os_name, software, issue_keywords)
        if score > best_score:
            best_score = score
            best_match = sol

    if best_match and best_score >= threshold:
        logger.info(
            "Solution memory hit — score=%.2f solution_id=%d", best_score, best_match.id
        )
        return best_match

    return None


def save_solution(
    db: Session,
    category: str,
    os_name: str,
    software: str,
    issue_summary: str,
    solution_steps: str,
    source_ticket_id: str,
) -> Solution:
    """
    Persist a resolved solution. If an identical entry already exists,
    increment its success_count instead of creating a duplicate.
    """
    existing = (
        db.query(Solution)
        .filter(
            Solution.category == category,
            Solution.os == os_name,
            Solution.software == software,
            Solution.issue_summary == issue_summary,
        )
        .first()
    )

    if existing:
        existing.success_count += 1
        db.commit()
        db.refresh(existing)
        return existing

    sol = Solution(
        category=category,
        os=os_name,
        software=software,
        issue_summary=issue_summary,
        solution_steps=solution_steps[:2000],
        source_ticket_id=source_ticket_id,
    )
    db.add(sol)
    db.commit()
    db.refresh(sol)
    return sol


def _score(
    sol: Solution,
    os_name: str,
    software: str,
    issue_keywords: list[str],
) -> float:
    """
    Compute a match score in [0.0, 1.0].
    Weights: OS match=0.3, software match=0.3, keyword overlap=0.4
    """
    score = 0.0
    sol_text = (sol.issue_summary + " " + sol.solution_steps).lower()

    if os_name and os_name.lower() in sol.os.lower():
        score += 0.3

    if software and software.lower() in sol.software.lower():
        score += 0.3

    if issue_keywords:
        hits = sum(1 for kw in issue_keywords if kw.lower() in sol_text)
        score += 0.4 * (hits / len(issue_keywords))

    return score
