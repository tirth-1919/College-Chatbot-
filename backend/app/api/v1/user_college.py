"""
User-side College Context API (Part A / Part I §66).

No separate college-selection page, no mandatory dropdown: the college
question appears as a normal assistant message inside the existing chat and
the user types the college name naturally. Resolution is database-backed via
CollegeContextManager; the frontend NEVER supplies an authoritative
college_id (§67).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.v1.auth import get_current_user
from backend.app.models.user import User
from backend.app.models.conversation import Conversation
from backend.app.chat.college_context import (
    college_context_manager, ONBOARDING_QUESTION, AMBIGUOUS_THRESHOLD
)
from backend.app.core.permissions import log_admin_audit

router = APIRouter(prefix="/college-context", tags=["College Context"])

# Re-export: single source of truth for the onboarding text lives in the
# CollegeContextManager module.


def _college_dict(college) -> Optional[dict]:
    if not college:
        return None
    return {
        "id": college.id,
        "name": college.name,
        "code": college.code,
        "slug": college.slug,
        "official_website": college.official_website,
        "city": college.city,
        "state": college.state,
        "status": college.status,
    }


def _state(db: Session, user: User, conversation_id: Optional[str]) -> dict:
    """Load user default + conversation college; server-derived only (§67)."""
    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        ).first()
    default_college = college_context_manager.get_user_default(db, user)
    conv_college = college_context_manager.get_conversation_college(db, conv) if conv else None
    # §5/§12: onboarding is needed for every conversation without a college
    # (and for a brand-new chat). Neither the user's default preference nor
    # any legacy tenant linkage auto-assigns a new conversation (§67).
    needs_onboarding = conv_college is None if conv else True
    return {
        "default_college": _college_dict(default_college),
        "conversation_college": _college_dict(conv_college),
        "needs_onboarding": needs_onboarding,
        "onboarding_message": ONBOARDING_QUESTION if needs_onboarding else None,
    }


class ResolveRequest(BaseModel):
    college_name: str
    conversation_id: Optional[str] = None
    set_default: bool = True


class SwitchRequest(BaseModel):
    conversation_id: Optional[str] = None
    college_name: Optional[str] = None
    college_id: Optional[str] = None  # optional direct id from ambiguity UI


class ConfirmSwitchRequest(BaseModel):
    conversation_id: str
    college_id: str


@router.get("/me")
def get_my_college_context(
    conversation_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Current college context for the logged-in user.
    `needs_onboarding=True` means the existing chat should show the
    first college question as an assistant message (§2) — not a separate page.
    """
    return _state(db, current_user, conversation_id)


@router.post("/resolve")
def resolve_college(
    req: ResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Resolve a user-typed college name (§3, §12, §57).
    On a confident database match: persist users.default_college_id (only when
    set_default — the deliberate onboarding/first-resolution flow) and the
    current conversation's college (§5). Ambiguous/unknown matches never
    silently guess (§12).
    """
    if not (req.college_name or "").strip():
        raise HTTPException(status_code=400, detail="College name cannot be empty")

    conv = None
    if req.conversation_id:
        conv = db.query(Conversation).filter(
            Conversation.id == req.conversation_id, Conversation.user_id == current_user.id
        ).first()

    res = college_context_manager.resolve_and_persist(
        db, current_user, conv, req.college_name,
        set_default=req.set_default and conv is None
    )

    if res["status"] == "AMBIGUOUS":
        top = res["candidates"][0] if res["candidates"] else None
        return {
            "status": "AMBIGUOUS",
            "message": (
                f"🤖 I found a possible match: {top['name']}\n\nDid you mean this college? Please enter the full name to confirm."
                if top else
                "🤖 I couldn't identify that college. Please enter the full college name."
            ),
            "candidates": res["candidates"],
        }
    if res["status"] == "NOT_FOUND":
        return {
            "status": "NOT_FOUND",
            "message": (
                "🤖 I couldn't find that college in my database. "
                "Please check the spelling or enter the full college name "
                "(Example: RC Technical)."
            ),
            "candidates": [],
        }

    college = res["college"]
    log_admin_audit(db, user=current_user, action="COLLEGE_CONTEXT_RESOLVED",
              resource="college_context", status_str="SUCCESS", college_id=res["college_id"])
    return {
        "status": "RESOLVED",
        "college": _college_dict(college),
        "default_college_id": current_user.default_college_id,
        "conversation_college_id": conv.college_id if conv else res["college_id"],
        "message": (
            f"🤖 Got it. I'll use {college.name} for your future chats."
        ),
    }


@router.post("/switch")
def switch_conversation_college(
    req: SwitchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safe conversation-college switch (§23, §24, §61): changes ONLY the current
    conversation's college. users.default_college_id is NEVER touched here.
    """
    conv = db.query(Conversation).filter(
        Conversation.id == req.conversation_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if req.college_id:
        from backend.app.models.college import College
        college = db.query(College).filter(College.id == req.college_id, College.status == "ACTIVE").first()
        if not college:
            raise HTTPException(status_code=400, detail="Unknown college")
    elif req.college_name:
        res = college_context_manager.resolve(db, req.college_name)
        if res["status"] != "RESOLVED":
            return {"status": res["status"], "candidates": res["candidates"],
                    "message": "Please confirm the college name to switch."}
        college = res["college"]
    else:
        raise HTTPException(status_code=400, detail="college_name or college_id required")

    college_context_manager.set_conversation_college(db, conv, college.id)
    # §10: 'college exists' is not 'college connected' — verify the target
    # college actually has connectable content (official website or verified
    # knowledge) before claiming the switch succeeded.
    from sqlalchemy import func as _func
    from backend.app.models.knowledge import WebsiteSnapshot, AitEntity
    has_snapshots = db.query(_func.count()).select_from(WebsiteSnapshot).filter(
        WebsiteSnapshot.college_id == college.id
    ).scalar() or 0
    has_entities = db.query(_func.count()).select_from(AitEntity).filter(
        AitEntity.college_id == college.id,
        AitEntity.is_verified == True,
    ).scalar() or 0
    connected = bool(has_snapshots) or bool(has_entities) or bool(college.official_website)
    log_admin_audit(db, user=current_user, action="COLLEGE_CONTEXT_SWITCHED",
              resource="college_context", status_str="SUCCESS", college_id=college.id)
    return {
        "status": "RESOLVED",
        "college": _college_dict(college),
        "connected": connected,
        "message": (
            f"🤖 This conversation now uses {college.name}."
            if connected else
            f"🤖 Switched to {college.name}, but I couldn't verify connected "
            "information for it — answers will be clearly labeled as "
            "unverified until the college's official data is connected."
        ),
    }


@router.post("/default/change")
def change_default_college(
    req: SwitchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deliberate default-college change (§25): only via this explicit action."""
    if req.college_name:
        res = college_context_manager.resolve(db, req.college_name)
        if res["status"] != "RESOLVED":
            return {"status": res["status"], "candidates": res["candidates"],
                    "message": "Please confirm the college name."}
        college_id = res["college_id"]
    elif req.college_id:
        college_id = req.college_id
    else:
        raise HTTPException(status_code=400, detail="college_name or college_id required")

    from backend.app.models.college import College
    college = db.query(College).filter(College.id == college_id, College.status == "ACTIVE").first()
    if not college:
        raise HTTPException(status_code=400, detail="Unknown college")

    college_context_manager.set_user_default(db, current_user, college.id)
    log_admin_audit(db, user=current_user, action="COLLEGE_DEFAULT_CHANGED",
              resource="college_context", status_str="SUCCESS", college_id=college.id)
    return {"status": "RESOLVED", "college": _college_dict(college),
            "message": f"🤖 Your default college is now {college.name}."}


@router.post("/default/forget")
def forget_default_college(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Forget college (§26): next new chat asks the college question again."""
    college_context_manager.forget_user_default(db, current_user)
    log_admin_audit(db, user=current_user, action="COLLEGE_DEFAULT_FORGOTTEN",
              resource="college_context", status_str="SUCCESS", college_id=None)
    return {"status": "FORGOTTEN", "message": ONBOARDING_QUESTION}
