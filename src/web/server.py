"""FastAPI 웹 서버"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Optional
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.game.engine import GameEngine
from src.llm.choice_mapper import ChoiceMapper
from src.ui.chat import ChatInterface, get_encounter_messages


def _encounter_messages_for_api(encounter):
    """인카운터 메시지 + 입력 안내 말풍선. API 응답용."""
    msgs = list(get_encounter_messages(encounter))
    msgs.append({"type": "text", "content": "채팅창에 당신의 행동이나 선택을 입력하세요."})
    return msgs

app = FastAPI(title="서울 2033 파쿠리 게임")

# 정적 파일 및 템플릿 설정
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 게임 세션 관리 (실제로는 Redis나 DB 사용 권장)
game_sessions: Dict[str, Dict] = {}


def create_game_session(session_id: str) -> Dict:
    """새 게임 세션 생성"""
    engine = GameEngine()
    choice_mapper = ChoiceMapper()
    chat = ChatInterface(choice_mapper)
    
    # 가젯 메타데이터 로드
    gadget_path = project_root / "src" / "data" / "gadgets" / "basic.json"
    if gadget_path.exists():
        with open(gadget_path, 'r', encoding='utf-8') as f:
            gadget_data = json.load(f)
            engine.state.gadgets.load_metadata(gadget_data.get("gadgets", {}))
    
    # 인카운터 로드
    encounter_path = project_root / "src" / "data" / "encounters" / "sample.json"
    if not encounter_path.exists():
        raise FileNotFoundError(f"인카운터 파일을 찾을 수 없습니다: {encounter_path}")
    engine.load_encounters(str(encounter_path))
    
    # 초기 가젯 부여
    engine.state.gadgets.acquire("근력")
    engine.state.gadgets.acquire("날렵함")
    
    # 첫 인카운터 발생
    encounter = engine.trigger_encounter()
    
    return {
        "session_id": session_id,
        "engine": engine,
        "chat": chat,
        "encounter": encounter,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/game/start")
async def start_game():
    """새 게임 시작"""
    try:
        session_id = str(uuid.uuid4())
        session = create_game_session(session_id)
    except FileNotFoundError as e:
        return {"error": str(e)}
    
    game_sessions[session_id] = session
    engine = session["engine"]
    encounter = session["encounter"]
    
    messages = _encounter_messages_for_api(encounter) if encounter else []
    return {
        "session_id": session_id,
        "encounter": {
            "id": encounter.id if encounter else None,
            "name": encounter.name if encounter else "",
            "description": encounter.description if encounter else "",
            "messages": messages,
            "choices": [
                {"id": c.id, "text": c.text, "description": c.description or c.text, "story": getattr(c, "story", "") or ""}
                for c in (encounter.choices if encounter else [])
            ],
        },
        "state": engine.get_state(),
        "messages": messages,
    }


@app.post("/api/game/{session_id}/choice")
async def process_choice(session_id: str, choice_input: Dict):
    """플레이어 선택 처리"""
    if session_id not in game_sessions:
        return {"error": "세션이 존재하지 않습니다."}
    
    session = game_sessions[session_id]
    engine = session["engine"]
    chat = session["chat"]
    
    if engine.is_game_over:
        return {"error": "게임이 종료되었습니다."}
    
    player_input = choice_input.get("input", "").strip()
    if not player_input:
        return {"error": "입력을 입력해주세요."}
    
    available_choices = engine.get_available_choices()
    if not available_choices:
        return {"error": "사용 가능한 선택지가 없습니다."}
    
    encounter = engine.get_current_encounter()
    mapped_choice = chat.process_player_input(
        player_input,
        available_choices,
        encounter=encounter,
        gadget_manager=engine.state.gadgets,
        resources=engine.state.resources,
    )
    if not mapped_choice:
        return {"error": "선택지를 찾을 수 없습니다. 다시 입력해주세요."}
    
    # 선택지 처리
    result = engine.process_choice(mapped_choice)
    
    # 다음 인카운터 발생
    next_encounter = None
    if not result.get("game_over"):
        next_encounter = engine.trigger_encounter()
        session["encounter"] = next_encounter
    
    story = chat.choice_mapper.explain_choice(mapped_choice)
    response_data = {
        "choice_mapped": {
            "id": mapped_choice.id,
            "text": mapped_choice.text,
            "description": mapped_choice.description or mapped_choice.text,
            "story": story,
            "explanation": story,
        },
        "result": {
            "resources": result.get("results", {}).get("resources", {}),
            "gadgets": result.get("results", {}).get("gadgets", []),
            "flags": result.get("results", {}).get("flags", []),
        },
        "state": engine.get_state(),
        "game_over": result.get("game_over", False),
        "game_over_reason": result.get("game_over_reason", ""),
    }

    if next_encounter:
        response_data["next_encounter"] = {
            "id": next_encounter.id,
            "name": next_encounter.name,
            "description": next_encounter.description,
            "messages": _encounter_messages_for_api(next_encounter),
            "choices": [
                {"id": c.id, "text": c.text, "description": c.description or c.text, "story": getattr(c, "story", "") or ""}
                for c in next_encounter.choices
            ],
        }
        response_data["messages"] = _encounter_messages_for_api(next_encounter)
    elif result.get("game_over"):
        response_data["game_over_message"] = chat.display_result(result)

    return response_data


@app.get("/api/game/{session_id}/state")
async def get_game_state(session_id: str):
    """게임 상태 조회"""
    if session_id not in game_sessions:
        return {"error": "세션이 존재하지 않습니다."}
    
    session = game_sessions[session_id]
    engine = session["engine"]
    encounter = session.get("encounter")
    
    return {
        "state": engine.get_state(),
        "encounter": {
            "id": encounter.id,
            "name": encounter.name,
            "description": encounter.description,
            "messages": _encounter_messages_for_api(encounter),
            "choices": [
                {"id": c.id, "text": c.text, "description": c.description or c.text, "story": getattr(c, "story", "") or ""}
                for c in encounter.choices
            ],
        } if encounter else None,
        "game_over": engine.is_game_over,
        "game_over_reason": engine.game_over_reason if engine.is_game_over else "",
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 엔드포인트 (실시간 채팅용)"""
    await websocket.accept()
    
    if session_id not in game_sessions:
        await websocket.send_json({"error": "세션이 존재하지 않습니다."})
        await websocket.close()
        return
    
    session = game_sessions[session_id]
    engine = session["engine"]
    chat = session["chat"]
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "choice":
                player_input = data.get("input", "").strip()
                if not player_input:
                    await websocket.send_json({"error": "입력을 입력해주세요."})
                    continue
                
                available_choices = engine.get_available_choices()
                if not available_choices:
                    await websocket.send_json({"error": "사용 가능한 선택지가 없습니다."})
                    continue
                
                encounter = engine.get_current_encounter()
                mapped_choice = chat.process_player_input(
                    player_input,
                    available_choices,
                    encounter=encounter,
                    gadget_manager=engine.state.gadgets,
                    resources=engine.state.resources,
                )
                if not mapped_choice:
                    await websocket.send_json({"error": "선택지를 찾을 수 없습니다."})
                    continue
                
                result = engine.process_choice(mapped_choice)
                
                # 응답 전송
                response = {
                    "type": "choice_result",
                    "choice": {
                        "id": mapped_choice.id,
                        "text": mapped_choice.text,
                        "explanation": chat.choice_mapper.explain_choice(mapped_choice)
                    },
                    "result": result,
                    "state": engine.get_state()
                }
                
                if not result.get("game_over"):
                    next_encounter = engine.trigger_encounter()
                    session["encounter"] = next_encounter
                    if next_encounter:
                        response["next_encounter"] = {
                            "id": next_encounter.id,
                            "name": next_encounter.name,
                            "description": next_encounter.description
                        }
                
                await websocket.send_json(response)
                
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
