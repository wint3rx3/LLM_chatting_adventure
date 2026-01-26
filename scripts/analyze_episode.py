"""에피소드 원고 분석 CLI 실행 파일"""

import sys
import argparse
import json
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools.episode_analyzer import EpisodeAnalyzer


def load_json_file(file_path: Path) -> dict:
    """JSON 파일 로드"""
    if not file_path.exists():
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(file_path: Path, data: dict):
    """JSON 파일 저장"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_encounters(existing_data: dict, new_encounters: List[dict]) -> dict:
    """기존 인카운터 데이터에 새 인카운터 추가"""
    if "encounters" not in existing_data:
        existing_data["encounters"] = []
    
    # 기존 인카운터 ID 목록
    existing_ids = {enc.get("id") for enc in existing_data["encounters"]}
    
    # 새 인카운터 추가 (중복 ID 체크)
    added_count = 0
    for encounter in new_encounters:
        if encounter.get("id") not in existing_ids:
            existing_data["encounters"].append(encounter)
            existing_ids.add(encounter.get("id"))
            added_count += 1
        else:
            print(f"경고: 인카운터 ID '{encounter.get('id')}'가 이미 존재합니다. 건너뜁니다.")
    
    return existing_data, added_count


def merge_gadgets(existing_data: dict, new_gadgets: dict) -> dict:
    """기존 가젯 데이터에 새 가젯 추가"""
    if "gadgets" not in existing_data:
        existing_data["gadgets"] = {}
    
    # 기존 가젯 ID 목록
    existing_ids = set(existing_data["gadgets"].keys())
    
    # 새 가젯 추가 (중복 ID 체크)
    added_count = 0
    for gadget_id, gadget_data in new_gadgets.items():
        if gadget_id not in existing_ids:
            existing_data["gadgets"][gadget_id] = gadget_data
            added_count += 1
        else:
            print(f"경고: 가젯 ID '{gadget_id}'가 이미 존재합니다. 건너뜁니다.")
    
    return existing_data, added_count


def main():
    parser = argparse.ArgumentParser(
        description='에피소드 원고를 분석해서 게임 요소(인카운터, 가젯)를 추출합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python scripts/analyze_episode.py manuscript.txt
  python scripts/analyze_episode.py episode.pdf --output encounters/new.json
  python scripts/analyze_episode.py manuscript.txt --dry-run
        """
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='원고 파일 경로 (TXT 또는 PDF)'
    )
    
    parser.add_argument(
        '--output-encounters',
        '-e',
        type=str,
        default=None,
        help='인카운터 출력 파일 경로 (기본: src/data/encounters/sample.json)'
    )
    
    parser.add_argument(
        '--output-gadgets',
        '-g',
        type=str,
        default=None,
        help='가젯 출력 파일 경로 (기본: src/data/gadgets/basic.json)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 파일에 저장하지 않고 결과만 출력'
    )
    
    args = parser.parse_args()
    
    # 입력 파일 확인
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)
    
    # 출력 파일 경로 설정
    project_root = Path(__file__).parent.parent
    if args.output_encounters:
        encounters_path = Path(args.output_encounters)
    else:
        encounters_path = project_root / "src" / "data" / "encounters" / "sample.json"
    
    if args.output_gadgets:
        gadgets_path = Path(args.output_gadgets)
    else:
        gadgets_path = project_root / "src" / "data" / "gadgets" / "basic.json"
    
    print("=" * 60)
    print("에피소드 원고 분석 시작")
    print("=" * 60)
    print(f"입력 파일: {input_path}")
    print(f"인카운터 출력: {encounters_path}")
    print(f"가젯 출력: {gadgets_path}")
    print()
    
    try:
        # 원고 분석
        print("원고 파일 읽는 중...")
        analyzer = EpisodeAnalyzer()
        result = analyzer.analyze_file(input_path)
        
        print("분석 완료!")
        print()
        
        # 결과 확인
        encounters = result.get("encounters", [])
        gadgets = result.get("gadgets", {})
        
        print(f"추출된 인카운터: {len(encounters)}개")
        for enc in encounters:
            print(f"  - {enc.get('name', enc.get('id', 'Unknown'))} ({enc.get('id')})")
        
        print(f"추출된 가젯: {len(gadgets)}개")
        for gadget_id in gadgets.keys():
            print(f"  - {gadget_id}")
        
        print()
        
        if args.dry_run:
            print("=" * 60)
            print("DRY RUN 모드 - 결과 미리보기")
            print("=" * 60)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        
        # 기존 파일에 병합
        print("기존 데이터에 병합 중...")
        
        # 인카운터 병합
        existing_encounters = load_json_file(encounters_path)
        merged_encounters, enc_added = merge_encounters(existing_encounters, encounters)
        
        # 가젯 병합
        existing_gadgets = load_json_file(gadgets_path)
        merged_gadgets, gad_added = merge_gadgets(existing_gadgets, gadgets)
        
        # 파일 저장
        print("파일 저장 중...")
        save_json_file(encounters_path, merged_encounters)
        save_json_file(gadgets_path, merged_gadgets)
        
        print()
        print("=" * 60)
        print("완료!")
        print("=" * 60)
        print(f"인카운터: {enc_added}개 추가됨 (총 {len(merged_encounters.get('encounters', []))}개)")
        print(f"가젯: {gad_added}개 추가됨 (총 {len(merged_gadgets.get('gadgets', {}))}개)")
        print()
        print(f"인카운터 파일: {encounters_path}")
        print(f"가젯 파일: {gadgets_path}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
