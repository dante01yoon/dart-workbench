"""22편 ② 1편 성적표 화면에 "출처 단 문장 · 심판 지지" 칸을 더해 띄운다(1편 코드는 그대로 가져다 쓴다).
사용: uv run python sec22/02_scoreboard.py → http://127.0.0.1:8800"""

import importlib.util
from http.server import HTTPServer
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "board1", Path(__file__).resolve().parent.parent / "sec01" / "scoreboard.py"
)
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)
board.COLS[2:2] = [("cited", "출처 단 문장"), ("supported", "심판 지지")]  # 통과율 · 문항 사이에

if __name__ == "__main__":
    print("성적표: http://127.0.0.1:8800")
    HTTPServer(("127.0.0.1", 8800), board.H).serve_forever()
