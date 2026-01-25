"""인카운터 시스템"""

from typing import Dict, List, Optional, Any, Set
import random
import json
import os


class Choice:
    """선택지 클래스"""
    
    def __init__(self, choice_data: Dict):
        self.id = choice_data.get("id", "")
        self.text = choice_data.get("text", "")
        self.requirements = choice_data.get("requirements", {})
        self.results = choice_data.get("results", {})
        self.description = choice_data.get("description", self.text)
        self.story = choice_data.get("story", "")
    
    def check_requirements(self, gadget_manager, resources) -> bool:
        """요구사항 확인"""
        # 가젯 요구사항 확인
        if "gadgets" in self.requirements:
            required_gadgets = self.requirements["gadgets"]
            if not gadget_manager.check_requirements(required_gadgets):
                return False
        
        # 자원 요구사항 확인
        if "resources" in self.requirements:
            resource_req = {}
            for key, value in self.requirements["resources"].items():
                from .resource import ResourceType
                if key == "health":
                    resource_req[ResourceType.HEALTH] = value
                elif key == "mental":
                    resource_req[ResourceType.MENTAL] = value
                elif key == "money":
                    resource_req[ResourceType.MONEY] = value
            
            if not resources.check_requirement(resource_req):
                return False
        
        return True
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        d: Dict = {
            "id": self.id,
            "text": self.text,
            "description": self.description,
            "requirements": self.requirements,
        }
        if self.story:
            d["story"] = self.story
        return d


def _normalize_message(item: Any) -> Dict:
    """메시지 항목 정규화: { type, content? } | { type, url?, alt? }"""
    if isinstance(item, str):
        return {"type": "text", "content": item}
    if isinstance(item, dict):
        t = item.get("type", "text")
        if t == "image":
            return {
                "type": "image",
                "url": item.get("url", ""),
                "alt": item.get("alt", ""),
            }
        return {"type": "text", "content": item.get("content", "")}
    return {"type": "text", "content": ""}


class Encounter:
    """인카운터 클래스"""
    
    def __init__(self, encounter_data: Dict):
        self.id = encounter_data.get("id", "")
        self.type = encounter_data.get("type", "basic")
        self.name = encounter_data.get("name", "")
        self.description = encounter_data.get("description", "")
        self.conditions = encounter_data.get("conditions", {})
        self.choices = [Choice(choice_data) for choice_data in encounter_data.get("choices", [])]
        self.weight = encounter_data.get("weight", 1)
        raw = encounter_data.get("messages", [])
        if raw:
            self.messages = [_normalize_message(m) for m in raw]
        else:
            self.messages = [{"type": "text", "content": self.description}]
    
    def get_available_choices(self, gadget_manager, resources) -> List[Choice]:
        """사용 가능한 선택지 반환"""
        available = []
        for choice in self.choices:
            if choice.check_requirements(gadget_manager, resources):
                available.append(choice)
        return available
    
    def get_messages(self) -> List[Dict]:
        """인카운터 메시지 목록 (말풍선·이미지). API/UI용."""
        return self.messages.copy()

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "messages": self.messages,
            "choices": [choice.to_dict() for choice in self.choices],
        }


class EncounterPool:
    """인카운터 풀 관리"""
    
    def __init__(self):
        self.encounters: Dict[str, Encounter] = {}
        self.encountered: Set[str] = set()
    
    def load_encounter(self, encounter_data: Dict):
        """인카운터 로드"""
        encounter = Encounter(encounter_data)
        self.encounters[encounter.id] = encounter
    
    def load_from_file(self, filepath: str):
        """파일에서 인카운터 로드"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for encounter_data in data:
                    self.load_encounter(encounter_data)
            elif isinstance(data, dict) and "encounters" in data:
                for encounter_data in data["encounters"]:
                    self.load_encounter(encounter_data)
    
    def get_encounter(self, encounter_id: str) -> Optional[Encounter]:
        """인카운터 가져오기"""
        return self.encounters.get(encounter_id)
    
    def get_random_encounter(self, encounter_type: str = "basic", 
                            gadget_manager=None, resources=None) -> Optional[Encounter]:
        """랜덤 인카운터 선택"""
        # 조건에 맞는 인카운터 필터링
        available = []
        for encounter in self.encounters.values():
            if encounter.type != encounter_type:
                continue
            
            # 조건 확인
            if self._check_encounter_conditions(encounter, gadget_manager, resources):
                available.append(encounter)
        
        if not available:
            return None
        
        # 가중치 적용 랜덤 선택
        weights = [encounter.weight for encounter in available]
        return random.choices(available, weights=weights, k=1)[0]
    
    def _check_encounter_conditions(self, encounter: Encounter, 
                                   gadget_manager, resources) -> bool:
        """인카운터 발생 조건 확인"""
        conditions = encounter.conditions
        
        # 가젯 조건 확인
        if "gadgets" in conditions:
            required_gadgets = conditions["gadgets"]
            if gadget_manager and not gadget_manager.has_any(required_gadgets):
                return False
        
        # 플래그 조건 확인 (나중에 구현)
        # if "flags" in conditions:
        #     ...
        
        return True
    
    def mark_encountered(self, encounter_id: str):
        """인카운터 발생 기록"""
        self.encountered.add(encounter_id)
