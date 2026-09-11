from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.app.core.database import get_db
from backend.app.api.v1.admin.auth import get_current_admin
from backend.app.models.automation import KnowledgeEvaluation
from backend.app.knowledge.evaluation import run_golden_evaluation_suite
from backend.app.knowledge.rollback import rollback_engine

router = APIRouter(prefix="/evaluation", tags=["Admin Knowledge Evaluation & Rollback"])

class RollbackKnowledgeRequest(BaseModel):
    entity_id: str
    target_version: int

class RollbackPromptRequest(BaseModel):
    prompt_slug: str
    target_version: int

class RollbackFlagRequest(BaseModel):
    flag_key: str

@router.get("/results")
def get_evaluation_history(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Retrieves history of golden knowledge evaluations and domain scores."""
    evals = db.query(KnowledgeEvaluation).order_by(KnowledgeEvaluation.created_at.desc()).limit(20).all()
    return {
        "count": len(evals),
        "evaluations": [
            {
                "id": e.id,
                "version_tag": e.version_tag,
                "accuracy_score": e.accuracy_score,
                "passed_queries": e.passed_queries,
                "total_queries": e.total_queries,
                "regression_detected": e.regression_detected,
                "domain_scores": e.domain_scores,
                "evaluated_by": e.evaluated_by,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "detailed_results": e.detailed_results
            }
            for e in evals
        ]
    }

@router.post("/run")
def trigger_golden_evaluation(current_admin = Depends(get_current_admin)):
    """Triggers an instant golden evaluation run across all 16 academic domains."""
    result = run_golden_evaluation_suite()
    return result

@router.post("/rollback/knowledge")
def rollback_knowledge(req: RollbackKnowledgeRequest, current_admin = Depends(get_current_admin)):
    """Rolls back a verified knowledge entity to a previous version."""
    result = rollback_engine.rollback_knowledge_entity(
        entity_id=req.entity_id,
        target_version_number=req.target_version,
        actor_id=current_admin.email
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/rollback/prompt")
def rollback_prompt(req: RollbackPromptRequest, current_admin = Depends(get_current_admin)):
    """Rolls back a system prompt to a historical version."""
    result = rollback_engine.rollback_system_prompt(
        prompt_slug=req.prompt_slug,
        target_version=req.target_version,
        actor_id=current_admin.email
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/rollback/feature-flag")
def rollback_flag(req: RollbackFlagRequest, current_admin = Depends(get_current_admin)):
    """Toggles or rolls back a feature flag."""
    result = rollback_engine.rollback_feature_flag(
        key=req.flag_key,
        actor_id=current_admin.email
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
