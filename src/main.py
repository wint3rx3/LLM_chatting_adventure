"""게임 메인 진입점"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.game.engine import GameEngine
from src.llm.choice_mapper import ChoiceMapper
from src.ui.chat import ChatInterface


def main():
    """메인 게임 루프"""
    print("="*50)
    print("서울 2033 파쿠리 게임 - LLM 기반 채팅 어드벤처")
    print("="*50)
    print("\n게임을 시작합니다...\n")
    
    # 게임 엔진 초기화
    engine = GameEngine()
    
    # 가젯 메타데이터 로드
    gadget_path = Path(__file__).parent.parent / "src" / "data" / "gadgets" / "basic.json"
    if gadget_path.exists():
        import json
        with open(gadget_path, 'r', encoding='utf-8') as f:
            gadget_data = json.load(f)
            engine.state.gadgets.load_metadata(gadget_data.get("gadgets", {}))
    
    # 샘플 인카운터 로드
    sample_encounter_path = Path(__file__).parent.parent / "src" / "data" / "encounters" / "sample.json"
    if sample_encounter_path.exists():
        engine.load_encounters(str(sample_encounter_path))
    else:
        print("Warning: 샘플 인카운터 파일을 찾을 수 없습니다.")
        print("기본 인카운터를 생성합니다...\n")
        create_sample_encounter(sample_encounter_path)
        engine.load_encounters(str(sample_encounter_path))
    
    # LLM 및 채팅 인터페이스 초기화
    choice_mapper = ChoiceMapper()
    chat = ChatInterface(choice_mapper)
    
    # 초기 가젯 부여 (테스트용)
    engine.state.gadgets.acquire("근력")
    engine.state.gadgets.acquire("날렵함")
    
    # 첫 인카운터 발생
    encounter = engine.trigger_encounter()
    if not encounter:
        print("인카운터를 로드할 수 없습니다.")
        return
    
    # 게임 루프
    turn_count = 0
    max_turns = 10  # 테스트용 최대 턴 수
    
    while not engine.is_game_over and turn_count < max_turns:
        turn_count += 1
        
        # 인카운터 표시
        print(chat.display_encounter(encounter))
        
        # 게임 상태 표시
        state = engine.get_state()
        print(chat.display_state(state))
        
        # 사용 가능한 선택지 가져오기
        available_choices = engine.get_available_choices()
        if not available_choices:
            print("사용 가능한 선택지가 없습니다. 게임을 종료합니다.")
            break
        
        # 플레이어 입력 받기
        while True:
            player_input = input("\n당신의 선택: ").strip()
            if not player_input:
                print("입력을 입력해주세요.")
                continue
            
            encounter = engine.get_current_encounter()
            mapped_choice = chat.process_player_input(
                player_input,
                available_choices,
                encounter=encounter,
                gadget_manager=engine.state.gadgets,
                resources=engine.state.resources,
            )
            if mapped_choice:
                print(f"\n{chat.choice_mapper.explain_choice(mapped_choice)}")
                break
            else:
                print("선택지를 찾을 수 없습니다. 다시 입력해주세요.")
        
        # 선택지 처리
        result = engine.process_choice(mapped_choice)
        print(chat.display_result(result))
        
        if result.get("game_over"):
            break
        
        # 다음 인카운터 발생
        print("\n" + "-"*50 + "\n")
        encounter = engine.trigger_encounter()
        if not encounter:
            print("더 이상 인카운터가 없습니다. 게임을 종료합니다.")
            break
    
    if turn_count >= max_turns:
        print("\n최대 턴 수에 도달했습니다. 게임을 종료합니다.")
    
    print("\n게임이 종료되었습니다.")


def create_sample_encounter(filepath: Path):
    """샘플 인카운터 생성"""
    import json
    
    sample_data = {
        "encounters": [
            {
                "id": "encounter_001",
                "type": "basic",
                "name": "강도 만남",
                "description": "어둡고 좁은 골목에서 강도를 만났습니다. 그는 칼을 들고 당신을 위협하고 있습니다.",
                "conditions": {},
                "weight": 1,
                "choices": [
                    {
                        "id": "choice_fight",
                        "text": "싸운다",
                        "description": "강도와 싸운다",
                        "requirements": {
                            "gadgets": ["권총", "근력"]
                        },
                        "results": {
                            "resources": {
                                "health": -1
                            },
                            "gadgets": [
                                {"action": "acquire", "id": "돈", "amount": 1}
                            ]
                        }
                    },
                    {
                        "id": "choice_run",
                        "text": "도망간다",
                        "description": "도망간다",
                        "requirements": {
                            "gadgets": ["날렵함"]
                        },
                        "results": {
                            "resources": {
                                "mental": -1
                            }
                        }
                    },
                    {
                        "id": "choice_pay",
                        "text": "돈을 준다",
                        "description": "돈을 주고 협력한다",
                        "requirements": {
                            "resources": {"money": 1}
                        },
                        "results": {
                            "resources": {
                                "money": -1
                            }
                        }
                    },
                    {
                        "id": "choice_talk",
                        "text": "설득한다",
                        "description": "강도를 설득한다",
                        "requirements": {
                            "gadgets": ["웅변", "교섭"]
                        },
                        "results": {
                            "resources": {
                                "mental": -1
                            },
                            "gadgets": [
                                {"action": "acquire", "id": "좋은 평판", "amount": 1}
                            ]
                        }
                    }
                ]
            },
            {
                "id": "encounter_002",
                "type": "basic",
                "name": "쓰레기 더미 발견",
                "description": "쓰레기 더미에서 뭔가 반짝이는 것을 발견했습니다.",
                "conditions": {},
                "weight": 1,
                "choices": [
                    {
                        "id": "choice_search",
                        "text": "찾아본다",
                        "description": "쓰레기 더미를 뒤진다",
                        "requirements": {},
                        "results": {
                            "gadgets": [
                                {"action": "acquire", "id": "권총", "amount": 1}
                            ]
                        }
                    },
                    {
                        "id": "choice_ignore",
                        "text": "무시한다",
                        "description": "무시하고 지나간다",
                        "requirements": {},
                        "results": {}
                    }
                ]
            }
        ]
    }
    
    # 디렉토리 생성
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # 파일 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    print(f"샘플 인카운터 파일을 생성했습니다: {filepath}")


if __name__ == "__main__":
    main()
