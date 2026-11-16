"""Repositories registry."""

from app.repositories.user_repository import UserRepository
from app.repositories.college_repository import CollegeRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.chat_repository import ChatRepository

__all__ = [
    "UserRepository",
    "CollegeRepository",
    "MembershipRepository",
    "ChatRepository",
]
