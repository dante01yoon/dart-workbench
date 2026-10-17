"""과제 2 풀이: clear에서 남기는 도구 결과를 1개로 줄이면? 메모 도구까지 빼면?
사용: uv run python sec05/solutions/a2_clear_keep.py"""

from _lab import lt, show

gold = lt.truth()
lt.KEEP = 1
show("KEEP=1 + 메모", lt.run("clear", gold))
lt.USE_NOTE = False
show("KEEP=1 · 메모 없음", lt.run("clear", gold))
