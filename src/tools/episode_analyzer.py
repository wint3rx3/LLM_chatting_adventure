"""에피소드 원고를 분석해서 게임 요소(인카운터, 가젯)를 추출하는 에이전트"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv
import requests

# 프로젝트 루트의 .env 로드
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# Upstage API 엔드포인트
UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
UPSTAGE_DOCUMENT_PARSE_URL = f"{UPSTAGE_BASE_URL}/document-digitization/document-parsing"


class EpisodeAnalyzer:
    """에피소드 원고를 분석해서 인카운터와 가젯을 추출하는 클래스"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("UPSTAGE_API_KEY")
        self.model = model or os.getenv("UPSTAGE_MODEL", "solar-pro")
        self.base_url = UPSTAGE_BASE_URL
        
        # Upstage Solar API 클라이언트 초기화 (OpenAI 호환)
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def extract_text_from_pdf(self, file_path: Path) -> str:
        """PDF 파일에서 텍스트 추출 (Document Parsing API 사용)"""
        if not self.api_key:
            raise ValueError("UPSTAGE_API_KEY가 설정되지 않았습니다.")
        
        with open(file_path, 'rb') as f:
            files = {'document': (file_path.name, f, 'application/pdf')}
            headers = {'Authorization': f'Bearer {self.api_key}'}
            data = {
                'mode': 'standard',  # standard, enhanced, auto
                'output_type': 'markdown'  # markdown 또는 html
            }
            
            response = requests.post(
                UPSTAGE_DOCUMENT_PARSE_URL,
                headers=headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            
            result = response.json()
            # Document Parsing API 응답 구조에 따라 텍스트 추출
            # 실제 응답 구조는 API 문서 참조 필요
            if 'text' in result:
                return result['text']
            elif 'markdown' in result:
                return result['markdown']
            elif 'html' in result:
                # HTML에서 텍스트만 추출 (간단한 버전)
                import re
                from html import unescape
                text = result['html']
                text = re.sub(r'<[^>]+>', '', text)
                return unescape(text)
            else:
                # 응답 전체를 문자열로 변환
                return json.dumps(result, ensure_ascii=False, indent=2)
    
    def read_manuscript(self, file_path: Path) -> str:
        """원고 파일 읽기 (PDF/TXT 자동 감지)"""
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
        
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif suffix in ['.txt', '.md', '.text']:
            return file_path.read_text(encoding='utf-8')
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {suffix}. PDF 또는 TXT 파일을 사용해주세요.")
    
    def analyze_episode(self, manuscript_text: str) -> Dict[str, Any]:
        """원고 텍스트를 분석해서 인카운터와 가젯을 추출"""
        
        # 기존 데이터 구조 참조를 위한 예시 제공
        example_encounter = {
            "id": "encounter_001",
            "type": "basic",
            "name": "강도 만남",
            "description": "어둡고 좁은 골목에서 강도를 만났습니다.",
            "messages": [
                {"type": "text", "content": "어둡고 좁은 골목 끝에서 누군가 다가온다."}
            ],
            "conditions": {},
            "weight": 1,
            "choices": [
                {
                    "id": "choice_fight",
                    "text": "싸운다",
                    "description": "강도와 싸운다",
                    "story": "당신은 싸우기로 했다...",
                    "requirements": {"gadgets": ["권총", "근력"]},
                    "results": {"resources": {"health": -1}}
                }
            ]
        }
        
        example_gadget = {
            "id": "권총",
            "type": "item",
            "category": "weapon",
            "name": "권총",
            "description": "기본적인 권총입니다.",
            "stackable": False
        }
        
        prompt = f"""당신은 텍스트 어드벤처 게임의 콘텐츠 제작 AI입니다. 주어진 에피소드 원고를 분석하여 게임 요소를 추출해주세요.

## 에피소드 원고
{manuscript_text}

## 작업 지시사항
1. 원고에서 **인카운터(사건/상황)**를 찾아서 추출하세요.
2. 각 인카운터에 대해 **플레이어가 선택할 수 있는 선택지**를 설계하세요.
3. 선택지에 필요한 **가젯(아이템/능력)**과 **결과(자원 변화, 가젯 획득/손실)**를 정의하세요.
4. 원고에서 언급된 새로운 **가젯**이 있다면 추출하세요.

## 출력 형식
다음 JSON 형식으로 답변하세요:
{{
  "encounters": [
    {{
      "id": "encounter_XXX",
      "type": "basic",
      "name": "인카운터 이름",
      "description": "인카운터 설명",
      "messages": [
        {{"type": "text", "content": "메시지 내용"}}
      ],
      "conditions": {{}},
      "weight": 1,
      "choices": [
        {{
          "id": "choice_XXX",
          "text": "선택지 텍스트",
          "description": "선택지 설명",
          "story": "선택 결과 스토리",
          "requirements": {{"gadgets": ["가젯명"]}},
          "results": {{"resources": {{"health": 0}}, "gadgets": [{{"action": "acquire", "id": "가젯명", "amount": 1}}]}}
        }}
      ]
    }}
  ],
  "gadgets": {{
    "가젯명": {{
      "id": "가젯명",
      "type": "item|ability|state",
      "category": "weapon|physical|social|...",
      "name": "가젯명",
      "description": "가젯 설명",
      "stackable": true|false
    }}
  }}
}}

## 참고 예시
인카운터 예시:
{json.dumps(example_encounter, ensure_ascii=False, indent=2)}

가젯 예시:
{json.dumps(example_gadget, ensure_ascii=False, indent=2)}

## 중요 사항
- 인카운터 ID는 "encounter_XXX" 형식 (XXX는 숫자)
- 선택지 ID는 "choice_XXX" 형식
- 가젯 ID는 한글 또는 영문 (기존 가젯과 중복되지 않도록)
- 선택지는 최소 2개 이상
- 각 선택지마다 story(결과 스토리)를 작성
- requirements와 results를 적절히 설계
"""
        
        try:
            # LLM API 호출 (structured output 사용)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a game content designer AI. Analyze episode manuscripts and extract game elements (encounters, choices, gadgets) in JSON format."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
                stream=False,
                response_format={"type": "json_object"},
            )
            
            # 응답 파싱
            content = response.choices[0].message.content
            result = json.loads(content)
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            print(f"응답 내용: {content[:500]}")
            raise
        except Exception as e:
            print(f"분석 오류: {e}")
            raise
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """파일 경로를 받아서 분석 수행"""
        manuscript_text = self.read_manuscript(file_path)
        return self.analyze_episode(manuscript_text)
