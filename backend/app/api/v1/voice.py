from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Request
from pydantic import BaseModel
from backend.app.api.v1.auth import get_current_user
from backend.app.models.user import User
from backend.app.security.rate_limiter import rate_limiter

router = APIRouter(prefix="/voice", tags=["Voice"])

class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en"  # en, gu, hi
    voice: Optional[str] = "default"

@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Server-side audio speech-to-text endpoint (used when browser Web Speech API is not supported).
    """
    rate_limiter.enforce("voice", request, user_id=current_user.id)
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio recording")

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Server-side transcription is not configured; use browser speech recognition.",
    )

@router.post("/synthesize")
def synthesize_speech(
    req: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Speech synthesis configuration endpoint.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Server-side speech synthesis is not configured; use browser speech synthesis.",
    )
