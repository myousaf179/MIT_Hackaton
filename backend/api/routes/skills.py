"""GET /skills/search — autocomplete used by the frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_skill_matcher
from api.schemas import SkillSearchResponse, SkillSearchResult
from matching.skill_matcher import SkillMatcher

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/search", response_model=SkillSearchResponse)
def search_skills(
    q: str = Query(..., min_length=1, description="Free-text query."),
    limit: int = Query(8, ge=1, le=25),
    matcher: SkillMatcher = Depends(get_skill_matcher),
) -> SkillSearchResponse:
    results = matcher.search(q, limit=limit)
    return SkillSearchResponse(
        query=q,
        results=[SkillSearchResult(**r) for r in results],
    )
