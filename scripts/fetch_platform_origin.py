"""플랫폼 출발 지역(거주지 시도) 월별 방문객 — 데이터픽 regSn=23 공개 차트를 달마다 1회 조회(Aside).

    python scripts/fetch_platform_origin.py 2025-01 2026-07
출처: 제주관광빅데이터플랫폼 데이터픽 「제주 방문 관광객 거주지 분포(시도)」(이동통신). 요청 간격 1.5초.
산출: data/platform/origin_sido_monthly.csv (month, sido, visitors, visitors_ly, yoy)
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASIDE = Path.home() / "AppData/Local/Aside/CLI/current/aside.exe"
OUT = ROOT / "data/platform/origin_sido_monthly.csv"

JS = """
const pgO = await openTab('https://data.ijto.or.kr/prog/dataPick/bigdata/sub02/view.do?regSn=23');
const months = %MONTHS%;
const res = {};
for (const [b, e] of months) {
  res[b] = await pgO.evaluate(async (p) => {
    const r = await fetch('/api/dataPick/chart/renderChart.do', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(p)});
    const j = await r.json();
    return j.data.charts[0].data.map(x => [x.groupVal, x.sumVal, x.sumVal_yoy_sum, x.sumVal_yoy]);
  }, {regSn: '23', chartIndex: 0, searchDataBgnDt: b, searchDataEndDt: e});
  await sleep(1500);
}
await closeTab(pgO);
console.log('__DATA__' + JSON.stringify(res));
"""


def main(a, b):
    months = [[p.strftime("%Y%m01"), (p.to_timestamp(how="end")).strftime("%Y%m%d")] for p in pd.period_range(a, b, freq="M")]
    out = subprocess.run([str(ASIDE), "repl", JS.replace("%MONTHS%", json.dumps(months))], capture_output=True, timeout=170)
    text = out.stdout.decode("utf-8", "replace")
    m = re.search(r"__DATA__(\{.*\})", text)
    if not m:
        raise SystemExit("조회 실패:\n" + text[-800:] + out.stderr.decode("utf-8", "replace")[-400:])
    data = json.loads(m.group(1))
    with OUT.open("w", encoding="utf-8", newline="\n") as fp:
        w = csv.writer(fp, lineterminator="\n")
        w.writerow(["month", "sido", "visitors", "visitors_ly", "yoy"])
        for k in sorted(data):
            for sido, v, ly, yoy in data[k]:
                w.writerow([f"{k[:4]}-{k[4:6]}", sido, v, ly, yoy])
    print(f"{len(data)}개월 저장 → {OUT.name}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2025-01", sys.argv[2] if len(sys.argv) > 2 else "2026-07")
