from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.solution import Solution
from schemas import SolutionOut

router = APIRouter(prefix="/solutions", tags=["solutions"])


@router.get("/search", response_model=list[SolutionOut])
def search_solutions(q: str = "", limit: int = 10, db: Session = Depends(get_db)):
    query = db.query(Solution)
    if q.strip():
        term = f"%{q.lower()}%"
        query = query.filter(
            Solution.issue_summary.ilike(term)
            | Solution.solution_steps.ilike(term)
            | Solution.category.ilike(term)
            | Solution.software.ilike(term)
        )
    return query.order_by(Solution.success_count.desc()).limit(limit).all()
