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

# 프로젝트 루트의 .env 로드 (웹 서버 cwd와 무관하게)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# Upstage Solar API 엔드포인트
UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
DEBUG_CHOICE_MAPPER = os.getenv("DEBUG_CHOICE_MAPPER", "").lower() in ("1", "true", "yes")


class ChoiceMapper:
    """플레이어의 자연어 입력을 게임 선택지로 매핑하는 클래스
    
    Upstage Solar LLM을 사용합니다.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("UPSTAGE_API_KEY")
        self.model = model or os.getenv("UPSTAGE_MODEL", "solar-pro")
        self.base_url = UPSTAGE_BASE_URL
        
        # Upstage Solar API 클라이언트 초기화 (OpenAI 호환)
        try:
            from openai import OpenAI
            self.client = (
                OpenAI(api_key=self.api_key, base_url=self.base_url)
                if self.api_key
                else None
            )
        except ImportError:
            self.client = None
            print("Warning: openai library not installed. Using fallback mapper.")
    
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
        
        if not self.client:
            return self._fallback_mapping(player_input, available_choices)
        
        return self._llm_mapping(
            player_input,
            available_choices,
            encounter_name=encounter_name,
            encounter_description=encounter_description,
        )
    
    def _llm_mapping(
        self,
        player_input: str,
        available_choices: List[Choice],
        encounter_name: Optional[str] = None,
        encounter_description: Optional[str] = None,
    ) -> Optional[Choice]:
        """LLM을 사용하여 선택지 매핑"""
        try:
            choices_text = self._format_choices_for_llm(available_choices)
            id_list = ", ".join(c.id for c in available_choices)
            example_id = available_choices[0].id if available_choices else "choice_fight"
            scenario = self._get_context(
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

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You map player input to game choice IDs. Reply only with JSON: {\"choice_id\": \"exact_id_from_list\"}. No other text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=150,
                stream=False,
            )
            
            content = response.choices[0].message.content
            if not content or not content.strip():
                return self._fallback_mapping(player_input, available_choices)
            
            result = self._parse_json_response(content)
            if not result:
                return self._fallback_mapping(player_input, available_choices)
            
            raw = result.get("choice_id", "")
            choice_id = (raw.strip() if isinstance(raw, str) else str(raw)).strip('"\'')
            if DEBUG_CHOICE_MAPPER:
                print(f"[ChoiceMapper] LLM raw={raw!r} -> choice_id={choice_id!r}")
            
            # 1) 정확히 일치하는 선택지
            for choice in available_choices:
                if choice.id == choice_id:
                    if DEBUG_CHOICE_MAPPER:
                        print(f"[ChoiceMapper] 매칭: exact id -> {choice.id}")
                    return choice
            
            # 2) choice_1, choice_2 또는 1, 2 형태 → 1-based 인덱스로 해석
            idx = None
            if choice_id.isdigit():
                idx = int(choice_id) - 1
            elif choice_id.lower().startswith("choice_"):
                suffix = choice_id[7:].strip()
                if suffix.isdigit():
                    idx = int(suffix) - 1
            if idx is not None and 0 <= idx < len(available_choices):
                c = available_choices[idx]
                if DEBUG_CHOICE_MAPPER:
                    print(f"[ChoiceMapper] 매칭: index {idx+1} -> {c.id}")
                return c
            
            # 3) 부분 일치 (id에 choice_id가 포함되거나 반대)
            for choice in available_choices:
                if choice_id in choice.id or choice.id in choice_id:
                    if DEBUG_CHOICE_MAPPER:
                        print(f"[ChoiceMapper] 매칭: partial -> {choice.id}")
                    return choice
            
            # 4) 실패 시 키워드 폴백 (첫 번째 고정 대신)
            if DEBUG_CHOICE_MAPPER:
                print(f"[ChoiceMapper] ID 미매칭, 키워드 폴백 사용")
            return self._fallback_mapping(player_input, available_choices)
            
        except json.JSONDecodeError as e:
            print(f"Solar API response parse error: {e}")
            return self._fallback_mapping(player_input, available_choices)
        except Exception as e:
            err = str(e).lower()
            if "401" in err or "insufficient credit" in err or "api_key_is_not_allowed" in err:
                print(
                    "Solar API 오류: API 크레딧 부족으로 키가 정지되었습니다. "
                    "https://console.upstage.ai/billing 에서 결제 수단을 등록해주세요. "
                    "(키워드 매핑으로 계속 진행합니다.)"
                )
            else:
                print(f"Solar API mapping error: {e}")
            return self._fallback_mapping(player_input, available_choices)
    
    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """LLM 응답에서 JSON 추출 (```json ... ``` 래핑 처리)"""
        content = content.strip()
        if content.startswith("```"):
            # ```json ... ``` 또는 ``` ... ``` 제거
            lines = content.split("\n")
            start = 1 if lines[0].startswith("```") else 0
            end = len(lines)
            for i, line in enumerate(lines):
                if i > start and line.strip() == "```":
                    end = i
                    break
            content = "\n".join(lines[start:end])
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    def _has_gadget_change(self, choice: Choice) -> bool:
        """선택지 결과에 가젯 획득/손실이 있는지 확인"""
        gadgets = choice.results.get("gadgets", [])
        if not gadgets:
            return False
        for gadget_change in gadgets:
            action = gadget_change.get("action", "")
            if action in ("acquire", "lose"):
                return True
        return False
    
    def _format_choices_for_llm(self, choices: List[Choice]) -> str:
        """선택지를 LLM이 이해할 수 있는 형식으로 변환"""
        formatted = []
        for i, choice in enumerate(choices, 1):
            choice_info = f"{i}. ID: {choice.id}\n"
            choice_info += f"   설명: {choice.description or choice.text}\n"
            if choice.requirements:
                reqs = []
                # 가젯 요구사항: 가젯 획득/손실이 있을 때만 표시
                if "gadgets" in choice.requirements and self._has_gadget_change(choice):
                    reqs.append(f"필요 가젯: {', '.join(choice.requirements['gadgets'])}")
                if "resources" in choice.requirements:
                    reqs.append(f"필요 자원: {choice.requirements['resources']}")
                if reqs:
                    choice_info += f"   ({', '.join(reqs)})\n"
            formatted.append(choice_info)
        return "\n".join(formatted)
    
    def _get_context(
        self,
        encounter_name: Optional[str] = None,
        encounter_description: Optional[str] = None,
    ) -> str:
        """현재 게임·시나리오 컨텍스트"""
        base = "플레이어는 핵전쟁 이후의 폐허가 된 서울에서 생존하고 있습니다."
        if not encounter_name and not encounter_description:
            return base
        parts = [base]
        if encounter_name:
            parts.append(f"\n\n**지금 겪는 일**: {encounter_name}")
        if encounter_description:
            parts.append(f"\n{encounter_description}")
        return "\n".join(parts)
    
    def _fallback_mapping(self, player_input: str, available_choices: List[Choice]) -> Optional[Choice]:
        """키워드·부분문자열 기반 폴백 매핑 (LLM 미사용 시)"""
        player_lower = player_input.strip().lower()
        best_match = None
        best_score = 0
        
        for choice in available_choices:
            score = 0
            choice_text = (choice.description or choice.text).lower()
            
            # 1) 단어 단위 매칭
            for word in player_lower.split():
                if len(word) >= 2 and word in choice_text:
                    score += 2
                elif word in choice_text:
                    score += 1
            
            # 2) 2글자 이상 부분 문자열 매칭 (예: "도망갈게" → "도망" in "도망간다")
            for i in range(len(player_lower) - 1):
                for n in (2, 3):  # 2글자, 3글자
                    if i + n > len(player_lower):
                        break
                    sub = player_lower[i : i + n]
                    if sub in choice_text:
                        score += 1
                        break  # 같은 시작 위치에서 중복 방지
            
            if score > best_score:
                best_score = score
                best_match = choice
        
        return best_match or available_choices[0]
    
    def explain_choice(self, choice: Choice) -> str:
        """선택 결과 스토리 반환. story 있으면 사용, 없으면 기본 문장."""
        if getattr(choice, "story", "") and choice.story.strip():
            return choice.story.strip()
        return f"'{choice.description or choice.text}' 선택지를 선택했습니다."
