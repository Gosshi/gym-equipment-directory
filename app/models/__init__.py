# モジュール読み込み用（Alembicがモデルを見つけるために必要）
# app/models/__init__.py
from .base import Base
from .equipment import Equipment
from .favorite import Favorite
from .gym import Gym
from .gym_candidate import CandidateStatus, GymCandidate
from .gym_equipment import GymEquipment
from .gym_image import GymImage
from .report import Report
from .scraped_page import ScrapedPage
from .source import Source, SourceType

__all__ = [
    "Base",
    "Gym",
    "Equipment",
    "GymEquipment",
    "Source",
    "Report",
    "Favorite",
    "GymImage",
    "ScrapedPage",
    "GymCandidate",
    "CandidateStatus",
    "SourceType",
]
