"""게임 CLI 실행 파일 (콘솔 버전)"""

import sys
import json
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.game.engine import GameEngine
from src.llm.choice_mapper import ChoiceMapper
from src.ui.chat import ChatInterface


def main():
    """메인 게임 루프"""
    print("=" * 60)
    print("서울 2033 파쿠리 게임 - LLM 기반 채팅 어드벤처")
    print("=" * 60)
    print("\n게임을 시작합니다...\n")
    
    # 게임 엔진 초기화
    engine = GameEngine()
    
    # 가젯 메타데이터 로드
    gadget_path = project_root / "src" / "data" / "gadgets" / "basic.json"
    if gadget_path.exists():
        with open(gadget_path, 'r', encoding='utf-8') as f:
            gadget_data = json.load(f)
            engine.state.gadgets.load_metadata(gadget_data.get("gadgets", {}))
    else:
        print("경고: 가젯 메타데이터 파일을 찾을 수 없습니다.")
    
    # 인카운터 로드
    encounter_path = project_root / "src" / "data" / "encounters" / "sample.json"
    if not encounter_path.exists():
        print(f"오류: 인카운터 파일을 찾을 수 없습니다: {encounter_path}")
        return
    engine.load_encounters(str(encounter_path))
    
    # LLM 및 채팅 인터페이스 초기화
    choice_mapper = ChoiceMapper()
    chat = ChatInterface(choice_mapper)
    
    # 초기 가젯 부여
    engine.state.gadgets.acquire("근력")
    engine.state.gadgets.acquire("날렵함")
    
    # 첫 인카운터 발생
    encounter = engine.trigger_encounter()
    if not encounter:
        print("인카운터를 로드할 수 없습니다.")
        return
    
    # 게임 루프
    turn_count = 0
    max_turns = 50  # 최대 턴 수
    
    while not engine.is_game_over and turn_count < max_turns:
        turn_count += 1
        
        # 인카운터 표시
        print("\n" + "=" * 60)
        print(chat.display_encounter(encounter))
        print("=" * 60)
        
        # 게임 상태 표시
        state = engine.get_state()
        print(chat.display_state(state))
        
        # 사용 가능한 선택지 가져오기
        available_choices = engine.get_available_choices()
        if not available_choices:
            print("\n사용 가능한 선택지가 없습니다. 게임을 종료합니다.")
            break
        
        # 플레이어 입력 받기
        while True:
            try:
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
                    # 선택 결과 스토리 표시
                    story = chat.choice_mapper.explain_choice(mapped_choice)
                    print(f"\n{story}")
                    break
                else:
                    print("선택지를 찾을 수 없습니다. 다시 입력해주세요.")
            except KeyboardInterrupt:
                print("\n\n게임을 종료합니다.")
                return
            except EOFError:
                print("\n\n게임을 종료합니다.")
                return
        
        # 선택지 처리
        result = engine.process_choice(mapped_choice)
        
        # 결과 표시
        result_message = chat.display_result(result)
        if result_message.strip():
            print(result_message)
        
        if result.get("game_over"):
            print(f"\n게임 오버: {result.get('game_over_reason', '')}")
            break
        
        # 다음 인카운터 발생
        print("\n" + "-" * 60 + "\n")
        encounter = engine.trigger_encounter()
        if not encounter:
            print("더 이상 인카운터가 없습니다. 게임을 종료합니다.")
            break
    
    if turn_count >= max_turns:
        print(f"\n최대 턴 수({max_turns})에 도달했습니다. 게임을 종료합니다.")
    
    print("\n" + "=" * 60)
    print("게임이 종료되었습니다.")
    print("=" * 60)
    
    # 최종 상태 표시
    final_state = engine.get_state()
    print("\n최종 상태:")
    print(chat.display_state(final_state))


if __name__ == "__main__":
    main()
