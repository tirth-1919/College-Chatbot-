from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/voice", tags=["Voice"])

class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en"  # en, gu, hi
    voice: Optional[str] = "default"

@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """
    Server-side audio speech-to-text endpoint (used when browser Web Speech API is not supported).
    """
    content = await audio.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio recording")

    # In production, faster-whisper or Google Cloud Speech transcribes this audio
    return {
        "text": "Simulated audio transcription fallback",
        "language_detected": "en",
        "confidence": 0.95,
        "mode": "FALLBACK"
    }

@router.post("/synthesize")
def synthesize_speech(req: TTSRequest):
    """
    Speech synthesis configuration endpoint.
    """
    return {
        "text": req.text,
        "language": req.language,
        "speech_rate": 1.0,
        "pitch": 1.0,
        "provider": "WebSpeechAPI-native"
    }
