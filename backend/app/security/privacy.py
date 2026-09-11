import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.app.core.database import SessionLocal
from backend.app.models.user import User, UserSession
from backend.app.models.conversation import Conversation, Message
from backend.app.models.admin_system import AiProviderConfig
from backend.app.models.audit import AuditLog

class PrivacyManager:
    """Privacy controls, user data isolation, export, and AI provider gatekeeping."""

    @staticmethod
    def export_user_data(user_id: str) -> Dict[str, Any]:
        """Exports all conversation history, messages, and user profile data (GDPR compliant)."""
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()
            export_payload = {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                },
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_conversations": len(conversations),
                "conversations": []
            }

            for conv in conversations:
                messages = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at.asc()).all()
                export_payload["conversations"].append({
                    "conversation_id": conv.id,
                    "title": conv.title,
                    "created_at": conv.created_at.isoformat() if conv.created_at else None,
                    "messages": [
                        {
                            "sender": m.sender,
                            "content": m.content,
                            "created_at": m.created_at.isoformat() if m.created_at else None
                        }
                        for m in messages
                    ]
                })

            # Audit the export action
            audit = AuditLog(
                actor_id=user_id,
                action="USER_DATA_EXPORT",
                resource="users",
                resource_id=user_id,
                details={"conversations_count": len(conversations)}
            )
            db.add(audit)
            db.commit()

            return export_payload
        finally:
            db.close()

    @staticmethod
    def delete_user_account(user_id: str) -> Dict[str, Any]:
        """Permanently erases user account, active sessions, and personal conversations."""
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Cascade delete conversations and messages
            convs = db.query(Conversation).filter(Conversation.user_id == user_id).all()
            for c in convs:
                db.query(Message).filter(Message.conversation_id == c.id).delete()
                db.delete(c)

            # Delete sessions
            db.query(UserSession).filter(UserSession.user_id == user_id).delete()

            # Audit record before deleting user record
            audit = AuditLog(
                actor_id=user_id,
                action="ACCOUNT_DELETION",
                resource="users",
                resource_id=user_id,
                details={"deleted_user_email": user.email}
            )
            db.add(audit)

            # Delete user record
            db.delete(user)
            db.commit()

            return {"success": True, "message": "User account and all personal data permanently deleted."}
        finally:
            db.close()

    @staticmethod
    def verify_provider_privacy(provider_name: str, has_private_data: bool = False, has_documents: bool = False) -> bool:
        """Verifies if the specified AI provider is authorized to receive private or document data."""
        db: Session = SessionLocal()
        try:
            provider = db.query(AiProviderConfig).filter(AiProviderConfig.provider_name == provider_name).first()
            if not provider or not provider.is_enabled:
                return False

            if has_private_data and not provider.is_allowed_for_private_data:
                return False

            if has_documents and not provider.is_allowed_for_documents:
                return False

            return True
        finally:
            db.close()

privacy_manager = PrivacyManager()
