"""Chat & Feedback Database Repository.

Encapsulates data access logic for ChatSession, ChatMessage, and Feedback entities.
"""

import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ChatSession, ChatMessage
from app.models.feedback_support import Feedback


class ChatRepository:
    """Data access repository for chat conversations and ratings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(self, chat_session: ChatSession) -> ChatSession:
        """Persists a new conversational session."""
        self.session.add(chat_session)
        await self.session.flush()
        return chat_session

    async def get_session(self, session_id: uuid.UUID) -> Optional[ChatSession]:
        """Fetches a chat session with eager-loaded messages."""
        result = await self.session.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id, ChatSession.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_user_sessions(
        self, user_id: uuid.UUID, college_id: Optional[uuid.UUID] = None, limit: int = 50
    ) -> List[ChatSession]:
        """Lists chat sessions belonging to a specific user."""
        query = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.is_active.is_(True))
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        if college_id:
            query = query.where(ChatSession.college_id == college_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_session(self, chat_session: ChatSession) -> ChatSession:
        """Flushes session title or metadata updates."""
        await self.session.flush()
        return chat_session

    async def create_message(self, message: ChatMessage) -> ChatMessage:
        """Persists a user or assistant message turn."""
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_message(self, message_id: uuid.UUID) -> Optional[ChatMessage]:
        """Fetches a specific message by UUID."""
        result = await self.session.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        return result.scalar_one_or_none()

    async def create_feedback(self, feedback: Feedback) -> Feedback:
        """Persists a user feedback rating."""
        self.session.add(feedback)
        await self.session.flush()
        return feedback

