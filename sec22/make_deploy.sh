#!/bin/zsh
# 22편: 배포 묶음(../deploy-workbench)을 만든다 — 실습 코드 + 빌드한 화면 + 회사 목록용 보고서 정보. 비밀 값(.env)과 검색 색인은 넣지 않는다.
set -e
P=${0:A:h:h}
D=${1:-$P/../deploy-workbench}
rm -rf "${D:?}"/sec*(N) "${D:?}/data"  # .git은 남긴다
mkdir -p "$D"
npm --prefix $P/sec21/web run build
rsync -a --exclude .venv --exclude node_modules --exclude __pycache__ --exclude .ruff_cache --exclude data --exclude .env $P/ $D/
mkdir -p $D/data/reports
for f in $P/data/reports/*_2025.json; do  # /api/companies는 회사 · 연도 · 접수번호만 쓴다 — 공시 본문은 넣지 않는다
  python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); json.dump({k: r[k] for k in ("corp","year","rcept_no")}, open(sys.argv[2],"w"), ensure_ascii=False)' $f $D/data/reports/${f:t}
done
cp $P/sec22/render.yaml $D/render.yaml            # Blueprint는 저장소 맨 위의 render.yaml을 읽는다
printf '.venv\nnode_modules\n__pycache__\n.env\n' > $D/.gitignore
printf 'node_modules\n' > $D/sec21/web/.gitignore      # 빌드한 화면(dist)은 저장소에 넣는다
echo "묶음 → $D ($(du -sh $D | cut -f1))"
