"""웹 서버 실행 스크립트"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    # PORT 미설정 시 8001 사용 (8000 충돌 회피). PORT=8000 으로 8000 지정 가능
    port = int(os.getenv("PORT", "8001"))
    print(f"웹 서버 시작: http://localhost:{port}")
    uvicorn.run(
        "src.web.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Windows에서 reload 시 PermissionError 가능
    )
