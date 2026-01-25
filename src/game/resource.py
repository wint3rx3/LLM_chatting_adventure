"""자원 관리 시스템"""

from typing import Dict, Optional
from enum import Enum


class ResourceType(Enum):
    HEALTH = "health"
    MENTAL = "mental"
    MONEY = "money"


class Resources:
    """플레이어의 자원을 관리하는 클래스"""
    
    MAX_RESOURCES = {
        ResourceType.HEALTH: 3,
        ResourceType.MENTAL: 3,
        ResourceType.MONEY: 3
    }
    
    def __init__(self, health: int = 3, mental: int = 3, money: int = 0):
        self.health = min(health, self.MAX_RESOURCES[ResourceType.HEALTH])
        self.mental = min(mental, self.MAX_RESOURCES[ResourceType.MENTAL])
        self.money = min(money, self.MAX_RESOURCES[ResourceType.MONEY])
    
    def change(self, resource_type: ResourceType, amount: int) -> bool:
        """자원을 변경하고, 변경 성공 여부를 반환"""
        current = self.get(resource_type)
        new_value = current + amount
        max_value = self.MAX_RESOURCES[resource_type]
        
        # 돈은 음수가 될 수 없음
        if resource_type == ResourceType.MONEY and new_value < 0:
            new_value = 0
        
        # 최대값 제한
        new_value = min(new_value, max_value)
        
        # 돈은 최대값 도달 시 더 이상 획득 불가
        if resource_type == ResourceType.MONEY and current >= max_value and amount > 0:
            return False
        
        self.set(resource_type, new_value)
        return True
    
    def get(self, resource_type: ResourceType) -> int:
        """자원 값을 가져옴"""
        if resource_type == ResourceType.HEALTH:
            return self.health
        elif resource_type == ResourceType.MENTAL:
            return self.mental
        elif resource_type == ResourceType.MONEY:
            return self.money
        return 0
    
    def set(self, resource_type: ResourceType, value: int):
        """자원 값을 설정"""
        max_value = self.MAX_RESOURCES[resource_type]
        value = max(0, min(value, max_value))
        
        if resource_type == ResourceType.HEALTH:
            self.health = value
        elif resource_type == ResourceType.MENTAL:
            self.mental = value
        elif resource_type == ResourceType.MONEY:
            self.money = value
    
    def check_requirement(self, requirement: Dict[ResourceType, int]) -> bool:
        """자원 요구사항을 확인"""
        for resource_type, required_amount in requirement.items():
            if self.get(resource_type) < required_amount:
                return False
        return True
    
    def is_dead(self) -> bool:
        """사망 상태인지 확인 (체력 또는 멘탈이 0)"""
        return self.health <= 0 or self.mental <= 0
    
    def to_dict(self) -> Dict[str, int]:
        """딕셔너리로 변환"""
        return {
            "health": self.health,
            "mental": self.mental,
            "money": self.money
        }
    
    def __str__(self) -> str:
        return f"체력: {self.health}/3, 멘탈: {self.mental}/3, 돈: {self.money}/3"
