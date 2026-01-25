"""게임 엔진 핵심"""

from typing import Dict, Optional, List
from .resource import Resources, ResourceType
from .gadget import GadgetManager
from .encounter import Encounter, EncounterPool, Choice
from .flag import FlagManager


class GameState:
    """게임 상태"""
    
    def __init__(self):
        self.resources = Resources()
        self.gadgets = GadgetManager()
        self.flags = FlagManager()
        self.turn = 0
        self.level = 1
        self.current_encounter: Optional[Encounter] = None
        self.encounter_history: List[str] = []
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "resources": self.resources.to_dict(),
            "gadgets": self.gadgets.get_all(),
            "flags": list(self.flags.get_all_flags()),
            "turn": self.turn,
            "level": self.level
        }


class GameEngine:
    """게임 엔진"""
    
    def __init__(self):
        self.state = GameState()
        self.encounter_pool = EncounterPool()
        self.is_game_over = False
        self.game_over_reason = ""
    
    def load_encounters(self, filepath: str):
        """인카운터 로드"""
        self.encounter_pool.load_from_file(filepath)
    
    def trigger_encounter(self, encounter_id: Optional[str] = None) -> Optional[Encounter]:
        """인카운터 발생"""
        if encounter_id:
            encounter = self.encounter_pool.get_encounter(encounter_id)
        else:
            encounter = self.encounter_pool.get_random_encounter(
                "basic", self.state.gadgets, self.state.resources
            )
        
        if encounter:
            self.state.current_encounter = encounter
            self.encounter_pool.mark_encountered(encounter.id)
            self.state.encounter_history.append(encounter.id)
        
        return encounter
    
    def get_current_encounter(self) -> Optional[Encounter]:
        """현재 인카운터 가져오기"""
        return self.state.current_encounter
    
    def get_available_choices(self) -> List[Choice]:
        """사용 가능한 선택지 가져오기"""
        if not self.state.current_encounter:
            return []
        
        return self.state.current_encounter.get_available_choices(
            self.state.gadgets, self.state.resources
        )
    
    def process_choice(self, choice: Choice) -> Dict:
        """선택지 처리"""
        results = choice.results
        
        # 자원 변경
        if "resources" in results:
            for resource_name, change in results["resources"].items():
                resource_type = None
                if resource_name == "health":
                    resource_type = ResourceType.HEALTH
                elif resource_name == "mental":
                    resource_type = ResourceType.MENTAL
                elif resource_name == "money":
                    resource_type = ResourceType.MONEY
                
                if resource_type:
                    self.state.resources.change(resource_type, change)
        
        # 가젯 변경
        if "gadgets" in results:
            for gadget_change in results["gadgets"]:
                action = gadget_change.get("action", "acquire")
                gadget_id = gadget_change.get("id", "")
                amount = gadget_change.get("amount", 1)
                
                if action == "acquire":
                    self.state.gadgets.acquire(gadget_id, amount)
                elif action == "lose":
                    self.state.gadgets.lose(gadget_id, amount)
        
        # 플래그 변경
        if "flags" in results:
            self.state.flags.apply_flag_changes(results["flags"])
        
        # 턴 증가
        self.state.turn += 1
        
        # 사망 확인
        if self.state.resources.is_dead():
            self.is_game_over = True
            if self.state.resources.health <= 0:
                self.game_over_reason = "체력이 0이 되어 사망했습니다."
            elif self.state.resources.mental <= 0:
                self.game_over_reason = "멘탈이 0이 되어 스트레스로 사망했습니다."
        
        return {
            "success": True,
            "results": results,
            "game_over": self.is_game_over,
            "game_over_reason": self.game_over_reason
        }
    
    def get_state(self) -> Dict:
        """게임 상태 가져오기"""
        return self.state.to_dict()
    
    def reset(self):
        """게임 리셋"""
        self.state = GameState()
        self.is_game_over = False
        self.game_over_reason = ""
