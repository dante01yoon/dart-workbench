#!/bin/zsh
# 19편 00: 어댑터를 실습 환경(mcp 2.3)에 같이 넣으면 어떻게 되나 — 설치만 해 보고 지운다(실습 .venv는 건드리지 않는다)
echo "■ ① langchain-mcp-adapters 0.3.2 + mcp 2.3.0"
uv run -q --no-project --with mcp==2.3.0 --with langchain-mcp-adapters==0.3.2 python -c "" 2>&1 | head -4
echo "\n■ ② 버전을 안 정하면 → uv가 상한이 없는 0.3.1을 고른다"
uv run -q --no-project --with mcp==2.3.0 --with langchain-mcp-adapters python -u -c "
import importlib.metadata as m; print('  설치됨: adapters', m.version('langchain-mcp-adapters'), '· mcp', m.version('mcp'))
import langchain_mcp_adapters.client" 2>&1 | grep -E "설치됨|Error" | sed -E "s/ \(\/.*\)//"
echo "\n■ ③ 어댑터 전용 환경(sec19/requirements.txt)"
uv run -q --no-project --with-requirements sec19/requirements.txt python -c "
import importlib.metadata as m; print('  adapters', m.version('langchain-mcp-adapters'), '· mcp', m.version('mcp'), '· langgraph', m.version('langgraph'))"
echo "  서버(16편 SDK)는 실습 .venv:" $(uv run -q python -c "import importlib.metadata as m; print('mcp', m.version('mcp'))")
