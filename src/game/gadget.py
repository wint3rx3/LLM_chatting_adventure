"""가젯 시스템 - 아이템, 능력, 상태 통합 관리"""

from typing import Dict, Set, List, Optional
from enum import Enum


class GadgetType(Enum):
    ITEM = "item"
    ABILITY = "ability"
    STATE = "state"


class GadgetManager:
    """가젯을 관리하는 클래스"""
    
    def __init__(self):
        # 가젯 ID -> 개수/레벨
        self.gadgets: Dict[str, int] = {}
        # 가젯 메타데이터 (ID -> 가젯 정보)
        self.gadget_metadata: Dict[str, Dict] = {}
    
    def acquire(self, gadget_id: str, amount: int = 1) -> None:
        """가젯 획득"""
        if gadget_id in self.gadgets:
            self.gadgets[gadget_id] += amount
        else:
            self.gadgets[gadget_id] = amount
    
    def lose(self, gadget_id: str, amount: int = 1) -> bool:
        """가젯 손실 (성공 여부 반환)"""
        if gadget_id not in self.gadgets:
            return False
        
        self.gadgets[gadget_id] -= amount
        if self.gadgets[gadget_id] <= 0:
            del self.gadgets[gadget_id]
        return True
    
    def has(self, gadget_id: str, level: Optional[int] = None) -> bool:
        """가젯 보유 여부 확인"""
        if gadget_id not in self.gadgets:
            return False
        
        if level is not None:
            return self.gadgets[gadget_id] >= level
        return True
    
    def has_all(self, gadget_ids: List[str]) -> bool:
        """모든 가젯 보유 여부 확인"""
        return all(self.has(gadget_id) for gadget_id in gadget_ids)
    
    def has_any(self, gadget_ids: List[str]) -> bool:
        """하나라도 가젯 보유 여부 확인"""
        return any(self.has(gadget_id) for gadget_id in gadget_ids)
    
    def get_level(self, gadget_id: str) -> int:
        """가젯 레벨/개수 가져오기"""
        return self.gadgets.get(gadget_id, 0)
    
    def check_requirements(self, requirements: List[str]) -> bool:
        """요구사항 확인 (OR 조건 - 하나라도 있으면 됨)"""
        if not requirements:
            return True
        return self.has_any(requirements)
    
    def get_all(self) -> Dict[str, int]:
        """모든 가젯 반환"""
        return self.gadgets.copy()
    
    def load_metadata(self, metadata: Dict[str, Dict]):
        """가젯 메타데이터 로드"""
        self.gadget_metadata.update(metadata)
    
    def get_gadget_name(self, gadget_id: str) -> str:
        """가젯 이름 가져오기"""
        if gadget_id in self.gadget_metadata:
            return self.gadget_metadata[gadget_id].get("name", gadget_id)
        return gadget_id
