"""Analytics & Telemetry Aggregation Service.

Computes actual database-backed metrics for Platform Super Admins and
College Administrators with strict date-range filtering and tenant isolation.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select, and_, func, desc, exists
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.college import College
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.feedback_support import Feedback, SupportTicket
from app.models.knowledge import KnowledgeChunk
from app.models.document import Document
from app.models.website import WebsitePage
from app.models.ai import AIProviderEvent
from app.models.registration import CollegeRegistration
from app.schemas.support_and_analytics import (
    PlatformAnalyticsResponse,
    CollegeAnalyticsDetailResponse,
    AIUsageMetrics,
    QuestionFrequencyItem,
    UnansweredQuestionItem,
)

logger = logging.getLogger(__name__)
ANALYTICS_TIMEZONE = ZoneInfo("Asia/Kolkata")


class AnalyticsService:
    """Computes real platform and tenant analytics across database models."""

    async def _get_query_trend(
        self,
        college_id: Optional[uuid.UUID],
        time_range: str,
        time_cutoff: datetime,
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """Return zero-filled query buckets for the selected range."""
        now = datetime.now(timezone.utc)
        local_now = now.astimezone(ANALYTICS_TIMEZONE).replace(tzinfo=None)
        tr = time_range.upper().strip()
        bucket_unit = "hour" if tr == "TODAY" else "day"
        if tr == "TODAY":
            bucket_count = local_now.hour + 1
        else:
            local_cutoff_date = time_cutoff.astimezone(ANALYTICS_TIMEZONE).date()
            bucket_count = max(1, (local_now.date() - local_cutoff_date).days + 1)
        local_created_at = func.timezone("Asia/Kolkata", ChatMessage.created_at)
        query = (
            select(
                func.date_trunc(bucket_unit, local_created_at).label("bucket"),
                func.count(ChatMessage.id).label("queries"),
            )
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                func.lower(ChatMessage.sender_role) == "user",
                ChatMessage.created_at >= time_cutoff,
            )
            .group_by("bucket")
            .order_by("bucket")
        )
        if college_id:
            query = query.where(ChatSession.college_id == college_id)
        rows = (await session.execute(query)).all()

        if bucket_unit == "hour":
            latest = local_now.replace(minute=0, second=0, microsecond=0)
            buckets = [latest - timedelta(hours=offset) for offset in range(bucket_count - 1, -1, -1)]
            date_format = "%H:00"
            counts = {
                (row.bucket.date(), row.bucket.hour): row.queries
                for row in rows
            }
            key_for = lambda value: (value.date(), value.hour)
        else:
            latest = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            buckets = [latest - timedelta(days=offset) for offset in range(bucket_count - 1, -1, -1)]
            date_format = "%b %d"
            counts = {row.bucket.date(): row.queries for row in rows}
            key_for = lambda value: value.date()

        return [
            {
                "date": bucket.strftime(date_format),
                "queries": counts.get(key_for(bucket), 0),
            }
            for bucket in buckets
        ]

    @staticmethod
    def _resolve_time_boundary(time_range: str = "30D") -> datetime:
        """Calculates UTC timestamp boundary for time filter."""
        now = datetime.now(timezone.utc)
        tr = time_range.upper().strip()
        if tr == "TODAY":
            local_now = now.astimezone(ANALYTICS_TIMEZONE)
            local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            return local_midnight.astimezone(timezone.utc)
        elif tr == "7D":
            return now - timedelta(days=7)
        elif tr == "90D":
            return now - timedelta(days=90)
        return now - timedelta(days=30)  # Default 30D

    async def get_platform_analytics(
        self,
        time_range: str,
        session: AsyncSession,
    ) -> PlatformAnalyticsResponse:
        """Aggregates platform-wide metrics for Global Super Admin."""
        time_cutoff = self._resolve_time_boundary(time_range)

        # 1. Colleges
        tot_colleges = (await session.execute(select(func.count(College.id)))).scalar() or 0
        appr_colleges = (await session.execute(select(func.count(College.id)).where(College.is_active == True))).scalar() or 0
        pend_regs = (await session.execute(
            select(func.count(CollegeRegistration.id)).where(CollegeRegistration.status == "PENDING")
        )).scalar() or 0

        # 2. Users
        tot_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
        act_users = (await session.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0

        # 3. Chat Metrics
        tot_sessions = (await session.execute(
            select(func.count(ChatSession.id)).where(ChatSession.created_at >= time_cutoff)
        )).scalar() or 0
        tot_questions = (await session.execute(
            select(func.count(ChatMessage.id)).where(
                and_(ChatMessage.sender_role == "user", ChatMessage.created_at >= time_cutoff)
            )
        )).scalar() or 0

        # 4. Knowledge & Documents
        tot_chunks = (await session.execute(select(func.count(KnowledgeChunk.id)))).scalar() or 0
        tot_docs = (await session.execute(select(func.count(Document.id)))).scalar() or 0
        tot_pages = (await session.execute(select(func.count(WebsitePage.id)))).scalar() or 0
        open_tickets = (await session.execute(
            select(func.count(SupportTicket.id)).where(SupportTicket.status.in_(["OPEN", "IN_PROGRESS", "WAITING_FOR_USER"]))
        )).scalar() or 0

        # 5. AI Telemetry
        ai_metrics = await self.get_ai_usage_analytics(session=session, time_cutoff=time_cutoff)

        # 6. Daily Trend & Top Colleges
        daily_trend = await self._get_query_trend(None, time_range, time_cutoff, session)

        top_colleges_stmt = (
            select(College.name, func.count(ChatMessage.id).label("queries"))
            .outerjoin(ChatSession, ChatSession.college_id == College.id)
            .outerjoin(
                ChatMessage,
                and_(
                    ChatMessage.session_id == ChatSession.id,
                    func.lower(ChatMessage.sender_role) == "user",
                    ChatMessage.created_at >= time_cutoff,
                ),
            )
            .group_by(College.name)
            .order_by(desc("queries"))
            .limit(5)
        )
        colleges_res = await session.execute(top_colleges_stmt)
        college_rows = colleges_res.all()
        total_top_queries = sum(row[1] or 0 for row in college_rows)
        top_colleges = [
            {"name": row[0], "queries": row[1] or 0,
             "percent": round(((row[1] or 0) / total_top_queries) * 100, 1) if total_top_queries else 0.0}
            for row in college_rows
        ]

        return PlatformAnalyticsResponse(
            time_range=time_range,
            total_colleges=tot_colleges,
            approved_colleges=appr_colleges,
            pending_registrations=pend_regs,
            total_users=tot_users,
            active_users=act_users,
            total_chat_sessions=tot_sessions,
            total_questions_asked=tot_questions,
            total_knowledge_chunks=tot_chunks,
            total_documents_processed=tot_docs,
            total_crawled_pages=tot_pages,
            open_support_tickets=open_tickets,
            ai_metrics=ai_metrics,
            top_active_colleges=top_colleges,
            daily_volume_trend=daily_trend,
        )

    async def get_college_analytics(
        self,
        college_id: uuid.UUID,
        time_range: str,
        session: AsyncSession,
    ) -> CollegeAnalyticsDetailResponse:
        """Aggregates institution-specific metrics for College Admin."""
        time_cutoff = self._resolve_time_boundary(time_range)

        # 1. Queries and sessions scoped to this college
        sessions_stmt = select(func.count(ChatSession.id)).where(
            and_(ChatSession.college_id == college_id, ChatSession.created_at >= time_cutoff)
        )
        total_sessions = (await session.execute(sessions_stmt)).scalar() or 0

        questions_stmt = (
            select(func.count(ChatMessage.id))
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                and_(
                    ChatSession.college_id == college_id,
                    ChatMessage.sender_role == "user",
                    ChatMessage.created_at >= time_cutoff,
                )
            )
        )
        total_queries = (await session.execute(questions_stmt)).scalar() or 0

        # Unique active students
        students_stmt = select(func.count(func.distinct(ChatSession.user_id))).where(
            and_(ChatSession.college_id == college_id, ChatSession.created_at >= time_cutoff)
        )
        active_students = (await session.execute(students_stmt)).scalar() or 0

        # 2. Feedback ratings
        pos_stmt = select(func.count(Feedback.id)).where(
            and_(Feedback.college_id == college_id, Feedback.rating > 0, Feedback.created_at >= time_cutoff)
        )
        neg_stmt = select(func.count(Feedback.id)).where(
            and_(Feedback.college_id == college_id, Feedback.rating < 0, Feedback.created_at >= time_cutoff)
        )
        pos_count = (await session.execute(pos_stmt)).scalar() or 0
        neg_count = (await session.execute(neg_stmt)).scalar() or 0
        tot_feedback = pos_count + neg_count
        satisfaction_score = round(
            3.0 + (2.0 * (pos_count - neg_count) / tot_feedback), 1
        ) if tot_feedback > 0 else 0.0

        # 3. Knowledge chunks
        tot_chunks_stmt = select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.college_id == college_id)
        pub_chunks_stmt = select(func.count(KnowledgeChunk.id)).where(
            and_(KnowledgeChunk.college_id == college_id, KnowledgeChunk.status == "PUBLISHED")
        )
        pending_stmt = select(func.count(KnowledgeChunk.id)).where(
            and_(KnowledgeChunk.college_id == college_id, KnowledgeChunk.status == "PENDING_REVIEW")
        )
        tot_chunks = (await session.execute(tot_chunks_stmt)).scalar() or 0
        pub_chunks = (await session.execute(pub_chunks_stmt)).scalar() or 0
        pending_chunks = (await session.execute(pending_stmt)).scalar() or 0

        # 4. Questions & Unanswered queries
        frequent_q = await self.get_frequently_asked_questions(
            college_id, limit=5, session=session, time_cutoff=time_cutoff
        )
        unanswered_q = await self.get_unanswered_questions(
            college_id, limit=5, session=session, time_cutoff=time_cutoff
        )

        # 5. Trend and distributions
        daily_trend = await self._get_query_trend(college_id, time_range, time_cutoff, session)
        source_rows = await session.execute(
            select(ChatMessage.answer_source_type, func.count(ChatMessage.id))
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                ChatSession.college_id == college_id,
                func.lower(ChatMessage.sender_role) == "assistant",
                ChatMessage.created_at >= time_cutoff,
            )
            .group_by(ChatMessage.answer_source_type)
        )
        source_distribution = {str(source): int(count) for source, count in source_rows.all()}
        category_distribution: Dict[str, int] = {}

        return CollegeAnalyticsDetailResponse(
            college_id=college_id,
            time_range=time_range,
            total_queries=total_queries,
            total_sessions=total_sessions,
            active_students_count=active_students,
            satisfaction_score=satisfaction_score,
            positive_feedback_count=pos_count,
            negative_feedback_count=neg_count,
            knowledge_records_count=tot_chunks,
            published_chunks_count=pub_chunks,
            pending_reviews_count=pending_chunks,
            daily_query_trend=daily_trend,
            category_distribution=category_distribution,
            source_distribution=source_distribution,
            frequent_questions=frequent_q,
            unanswered_questions=unanswered_q,
        )

    async def get_frequently_asked_questions(
        self,
        college_id: Optional[uuid.UUID],
        limit: int = 10,
        session: Optional[AsyncSession] = None,
        time_cutoff: Optional[datetime] = None,
    ) -> List[QuestionFrequencyItem]:
        """Calculates recurring inquiries based on user turns."""
        query = (
            select(
                ChatMessage.message_text,
                func.count(ChatMessage.id).label("freq"),
                func.max(ChatMessage.created_at).label("latest"),
            )
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(func.lower(ChatMessage.sender_role) == "user")
        )
        if time_cutoff:
            query = query.where(ChatMessage.created_at >= time_cutoff)
        if college_id:
            query = query.where(ChatSession.college_id == college_id)

        query = query.group_by(ChatMessage.message_text).order_by(desc("freq")).limit(limit)
        res = await session.execute(query)
        rows = res.all()

        items = []
        for text, count, latest in rows:
            items.append(
                QuestionFrequencyItem(
                    query=text,
                    count=count,
                    category="GENERAL",
                    latest_asked_at=latest,
                )
            )
        return items

    async def get_unanswered_questions(
        self,
        college_id: Optional[uuid.UUID],
        limit: int = 10,
        session: Optional[AsyncSession] = None,
        time_cutoff: Optional[datetime] = None,
    ) -> List[UnansweredQuestionItem]:
        """Identifies student inquiries where verified facts were missing."""
        # Pair a no-reliable-info response with the immediately preceding student
        # question in that chat session, so analytics report the question itself.
        user_message = aliased(ChatMessage)
        assistant_message = aliased(ChatMessage)
        later_user_message = aliased(ChatMessage)
        query = (
            select(
                user_message.message_text,
                func.count(assistant_message.id).label("freq"),
                func.max(assistant_message.created_at).label("latest"),
                func.max(ChatSession.id).label("sample_session"),
            )
            .join(ChatSession, user_message.session_id == ChatSession.id)
            .join(
                assistant_message,
                and_(
                    assistant_message.session_id == user_message.session_id,
                    assistant_message.created_at > user_message.created_at,
                    func.lower(assistant_message.sender_role) == "assistant",
                    assistant_message.answer_source_type == "NO_RELIABLE_INFORMATION",
                ),
            )
            .where(
                func.lower(user_message.sender_role) == "user",
                ~exists(
                    select(1).where(
                        later_user_message.session_id == user_message.session_id,
                        func.lower(later_user_message.sender_role) == "user",
                        later_user_message.created_at > user_message.created_at,
                        later_user_message.created_at < assistant_message.created_at,
                    )
                )
            )
        )
        if college_id:
            query = query.where(ChatSession.college_id == college_id)
        if time_cutoff:
            query = query.where(
                user_message.created_at >= time_cutoff,
                assistant_message.created_at >= time_cutoff,
            )

        query = query.group_by(user_message.message_text).order_by(desc("freq")).limit(limit)
        res = await session.execute(query)
        rows = res.all()

        items = []
        for text, count, latest, s_id in rows:
            items.append(
                UnansweredQuestionItem(
                    query=text,
                    category="OTHER",
                    occurrence_count=count,
                    last_occurred_at=latest or datetime.now(timezone.utc),
                    sample_session_id=s_id,
                )
            )
        return items

    async def get_ai_usage_analytics(
        self,
        session: AsyncSession,
        college_id: Optional[uuid.UUID] = None,
        time_cutoff: Optional[datetime] = None,
    ) -> AIUsageMetrics:
        """Aggregates LLM telemetry from ai_provider_events."""
        cutoff = time_cutoff or (datetime.now(timezone.utc) - timedelta(days=30))
        query = select(
            func.count(AIProviderEvent.id).label("total_reqs"),
            func.sum(AIProviderEvent.prompt_tokens).label("prompt_toks"),
            func.sum(AIProviderEvent.completion_tokens).label("comp_toks"),
            func.avg(AIProviderEvent.latency_ms).label("avg_lat"),
        ).where(AIProviderEvent.created_at >= cutoff)

        res = await session.execute(query)
        row = res.one_or_none()

        total_reqs = row.total_reqs or 0 if row else 0
        prompt_toks = row.prompt_toks or 0 if row else 0
        comp_toks = row.comp_toks or 0 if row else 0
        avg_lat = round(float(row.avg_lat), 1) if row and row.avg_lat else 0.0
        tot_toks = prompt_toks + comp_toks

        secondary_reqs = (await session.execute(
            select(func.count(AIProviderEvent.id)).where(
                AIProviderEvent.created_at >= cutoff,
                AIProviderEvent.event_type == "FALLBACK_FAILOVER",
            )
        )).scalar() or 0
        failed_reqs = (await session.execute(
            select(func.count(AIProviderEvent.id)).where(
                AIProviderEvent.created_at >= cutoff,
                AIProviderEvent.event_type == "ALL_PROVIDERS_FAILED",
            )
        )).scalar() or 0

        # Calculate estimated cost using standard Gemini Flash pricing ($0.075 per 1M input, $0.30 per 1M output)
        est_cost = (prompt_toks * 0.000000075) + (comp_toks * 0.0000003)

        return AIUsageMetrics(
            total_requests=total_reqs,
            primary_requests=max(0, total_reqs - secondary_reqs),
            secondary_requests=secondary_reqs,
            failed_requests=failed_reqs,
            total_tokens=tot_toks,
            prompt_tokens=prompt_toks,
            completion_tokens=comp_toks,
            average_latency_ms=avg_lat,
            fallback_rate_percent=round((secondary_reqs / total_reqs) * 100, 2) if total_reqs else 0.0,
            estimated_cost_usd=round(est_cost, 4),
        )


analytics_service = AnalyticsService()

