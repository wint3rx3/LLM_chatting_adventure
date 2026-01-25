"""게임 엔진 모듈"""

from .engine import GameEngine, GameState
from .resource import Resources, ResourceType
from .gadget import GadgetManager
from .encounter import Encounter, EncounterPool, Choice
from .flag import FlagManager

__all__ = [
    "GameEngine",
    "GameState",
    "Resources",
    "ResourceType",
    "GadgetManager",
    "Encounter",
    "EncounterPool",
    "Choice",
    "FlagManager"
]
