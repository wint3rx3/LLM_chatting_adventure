"""채팅 인터페이스"""

from typing import Optional, Callable, List
from ..game.encounter import Encounter, Choice
from ..llm.choice_mapper import ChoiceMapper


def get_encounter_messages(encounter: Encounter) -> List[dict]:
    """인카운터 메시지 목록 (말풍선·이미지). API/UI용."""
    return encounter.get_messages()


class ChatInterface:
    """채팅 기반 게임 인터페이스"""
    
    def __init__(self, choice_mapper: Optional[ChoiceMapper] = None):
        self.choice_mapper = choice_mapper or ChoiceMapper()
        self.message_history: list = []
    
    def display_encounter(self, encounter: Encounter) -> str:
        """인카운터 표시 (콘솔용 문자열). 메시지 여러 개 + 이미지 지원."""
        msgs = get_encounter_messages(encounter)
        parts = []
        for m in msgs:
            if m.get("type") == "image":
                url = m.get("url", "")
                parts.append(f"[이미지: {url}]" if url else "[이미지]")
            else:
                c = m.get("content", "")
                if c:
                    parts.append(c)
        text = "\n".join(parts) if parts else encounter.description
        prompt = "채팅창에 당신의 행동이나 선택을 입력하세요."
        full = f"{text}\n\n{prompt}"
        self.message_history.append({"type": "encounter", "messages": msgs})
        return full
    
    def process_player_input(
        self,
        player_input: str,
        available_choices: List[Choice],
        encounter: Optional[Encounter] = None,
        gadget_manager=None,
        resources=None,
    ) -> Optional[Choice]:
        """플레이어 입력 처리. 전체 선택지로 매핑 후 요구사항 확인, 미충족 시 실패 선택지로 대체."""
        if not player_input.strip():
            return None
        
        enc_name = encounter.name if encounter else None
        enc_desc = encounter.description if encounter else None
        
        # 전체 선택지로 매핑 (요구사항과 무관하게)
        all_choices = encounter.choices if encounter else available_choices
        mapped_choice = self.choice_mapper.map_to_choice(
            player_input,
            all_choices,
            encounter_name=enc_name,
            encounter_description=enc_desc,
        )
        
        if not mapped_choice:
            return None
        
        # 매핑된 선택지의 요구사항 확인
        if gadget_manager and resources:
            if not mapped_choice.check_requirements(gadget_manager, resources):
                # 요구사항 미충족: 실패 선택지 찾기 (id에 "_fail" 포함)
                fail_choice_id = mapped_choice.id + "_fail"
                for choice in all_choices:
                    if choice.id == fail_choice_id:
                        mapped_choice = choice
                        break
        
        if mapped_choice:
            explanation = self.choice_mapper.explain_choice(mapped_choice)
            self.message_history.append({
                "type": "player",
                "content": player_input
            })
            self.message_history.append({
                "type": "system",
                "content": explanation
            })
        
        return mapped_choice
    
    def display_result(self, result: dict) -> str:
        """결과 표시"""
        message = "\n"
        
        if "results" in result:
            results = result["results"]
            
            # 자원 변화 표시
            if "resources" in results:
                resource_changes = []
                for resource_name, change in results["resources"].items():
                    if change != 0:
                        sign = "+" if change > 0 else ""
                        resource_changes.append(f"{resource_name}: {sign}{change}")
                if resource_changes:
                    message += f"자원 변화: {', '.join(resource_changes)}\n"
            
            # 가젯 변화 표시
            if "gadgets" in results:
                gadget_changes = []
                for gadget_change in results["gadgets"]:
                    action = gadget_change.get("action", "acquire")
                    gadget_id = gadget_change.get("id", "")
                    amount = gadget_change.get("amount", 1)
                    
                    if action == "acquire":
                        gadget_changes.append(f"{gadget_id} 획득 (+{amount})")
                    elif action == "lose":
                        gadget_changes.append(f"{gadget_id} 손실 (-{amount})")
                
                if gadget_changes:
                    message += f"가젯 변화: {', '.join(gadget_changes)}\n"
        
        # 게임오버 확인
        if result.get("game_over"):
            message += f"\n게임 오버: {result.get('game_over_reason', '')}"
        
        self.message_history.append({
            "type": "result",
            "content": message
        })
        
        return message
    
    def display_state(self, state: dict) -> str:
        """게임 상태 표시"""
        resources = state.get("resources", {})
        message = f"\n현재 상태:\n"
        message += f"  체력: {resources.get('health', 0)}/3\n"
        message += f"  멘탈: {resources.get('mental', 0)}/3\n"
        message += f"  돈: {resources.get('money', 0)}/3\n"
        
        gadgets = state.get("gadgets", {})
        if gadgets:
            message += f"  보유 가젯: {', '.join(gadgets.keys())}\n"
        
        return message
    
    def get_message_history(self) -> list:
        """메시지 히스토리 가져오기"""
        return self.message_history.copy()
