"""LLM을 사용하여 플레이어 입력을 선택지로 매핑

Upstage Solar API (https://console.upstage.ai/api/chat) 사용.
OpenAI 호환 인터페이스로 동작합니다.
"""

from typing import List, Optional, Dict
from ..game.encounter import Choice
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# Upstage Solar API 엔드포인트
UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"


class ChoiceMapper:
    """플레이어의 자연어 입력을 게임 선택지로 매핑하는 클래스
    
    Upstage Solar LLM을 사용합니다.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("UPSTAGE_API_KEY")
        self.model = model or os.getenv("UPSTAGE_MODEL", "solar-pro")
        self.base_url = UPSTAGE_BASE_URL
        
        # Upstage Solar API 클라이언트 초기화 (OpenAI 호환)
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def map_to_choice(
        self,
        player_input: str,
        available_choices: List[Choice],
        encounter_name: Optional[str] = None,
        encounter_description: Optional[str] = None,
    ) -> Optional[Choice]:
        """플레이어 입력을 가장 적합한 선택지로 매핑"""
        if not available_choices:
            return None
        
        if len(available_choices) == 1:
            return available_choices[0]
        
        return self._ask_llm_to_find_choice(
            player_input,
            available_choices,
            encounter_name=encounter_name,
            encounter_description=encounter_description,
        )
    
    def _ask_llm_to_find_choice(
        self,
        player_input: str,
        available_choices: List[Choice],
        encounter_name: Optional[str] = None,
        encounter_description: Optional[str] = None,
    ) -> Optional[Choice]:
        """LLM에게 선택지 찾아달라고 요청"""
        # 프롬프트 생성
        choices_text = self._make_choices_text(available_choices)
        id_list = ", ".join(c.id for c in available_choices)
        example_id = available_choices[0].id if available_choices else "choice_fight"
        scenario = self._make_scenario(
            encounter_name=encounter_name,
            encounter_description=encounter_description,
        )
        
        prompt = f"""당신은 텍스트 어드벤처 게임의 AI입니다. **현재 시나리오**를 바탕으로 플레이어의 입력과 가장 적합한 선택지를 판단해주세요.

## 현재 시나리오 (상황)
{scenario}

## 사용 가능한 선택지 (반드시 아래 ID 중 하나를 그대로 사용)
{choices_text}

## 플레이어 입력
"{player_input}"

위 플레이어 입력이 **이 시나리오 안에서** 어떤 선택지에 해당하는지 판단하고, 해당 선택지의 ID만 반환하세요.
가능한 ID: {id_list}
**반드시 위 목록에 있는 ID를 그대로** 사용해야 합니다. JSON 형식으로만 답하세요. 다른 설명 금지.
예시: {{"choice_id": "{example_id}"}}"""

        try:
            # LLM API 호출 (structured output 사용)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You map player input to game choice IDs. Reply only with JSON: {\"choice_id\": \"exact_id_from_list\"}. No other text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150,
                stream=False,
                response_format={"type": "json_object"},  # Structured output 적용
            )
            
            # 응답 파싱
            content = response.choices[0].message.content
            result = json.loads(content)
            choice_id = result.get("choice_id", "").strip()
            
            # 선택지 찾기
            for choice in available_choices:
                if choice.id == choice_id:
                    return choice
            
            # 매칭 실패 시 첫 번째 선택지 반환
            return available_choices[0]
            
        except json.JSONDecodeError as e:
            print(f"Solar API response parse error: {e}")
            return available_choices[0]
        except Exception as e:
            err = str(e).lower()
            if "401" in err or "insufficient credit" in err or "api_key_is_not_allowed" in err:
                print(
                    "Solar API 오류: API 크레딧 부족으로 키가 정지되었습니다. "
                    "https://console.upstage.ai/billing 에서 결제 수단을 등록해주세요."
                )
            else:
                print(f"Solar API mapping error: {e}")
            return available_choices[0]
    
    def _make_choices_text(self, choices: List[Choice]) -> str:
        """선택지 텍스트 만들기"""
        formatted = []
        for i, choice in enumerate(choices, 1):
            choice_info = f"{i}. ID: {choice.id}\n"
            choice_info += f"   설명: {choice.description or choice.text}\n"
            formatted.append(choice_info)
        return "\n".join(formatted)
    
    def _make_scenario(
        self,
        encounter_name: Optional[str] = None,
        encounter_description: Optional[str] = None,
    ) -> str:
        """시나리오 만들기"""
        base = "플레이어는 핵전쟁 이후의 폐허가 된 서울에서 생존하고 있습니다."
        if not encounter_name and not encounter_description:
            return base
        parts = [base]
        if encounter_name:
            parts.append(f"\n\n**지금 겪는 일**: {encounter_name}")
        if encounter_description:
            parts.append(f"\n{encounter_description}")
        return "\n".join(parts)
    
    def explain_choice(self, choice: Choice) -> str:
        """선택 결과 스토리 반환. story 있으면 사용, 없으면 기본 문장."""
        if getattr(choice, "story", "") and choice.story.strip():
            return choice.story.strip()
        return f"'{choice.description or choice.text}' 선택지를 선택했습니다."
