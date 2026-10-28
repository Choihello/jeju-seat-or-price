"""플랫폼 일별 입도객 갱신 — Aside 브라우저로 데이터픽 공개 차트(regSn=18)를 한 번 조회해 CSV를 새로 쓴다.

    python scripts/refresh_data.py
실시간 API가 아니라 데이터픽 화면이 쓰는 공개 차트 1회 조회다(요청 1건). Aside 앱이 켜져 있어야 한다.
잠정치 수정은 data/platform/revisions.csv에, 갱신 이력은 data/platform/refresh_log.csv에 남긴다.
"""
import csv
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASIDE = Path.home() / "AppData/Local/Aside/CLI/current/aside.exe"
CSV = ROOT / "data/platform/daily_arrivals.csv"
KST = dt.timezone(dt.timedelta(hours=9))

JS = """
const pgR = await openTab('https://data.ijto.or.kr/prog/dataPick/bigdata/sub02/view.do?regSn=18');
const txR = await pgR.evaluate(async (end) => {
  const r = await fetch('/api/dataPick/chart/renderChart.do', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({regSn: '18', chartIndex: 0, searchDataBgnDt: '20180101', searchDataEndDt: end})});
  const j = await r.json();
  return JSON.stringify(j.data.charts[0].data.map(x => [x.dateVal, x.visitorKor, x.visitorFor, x.Total]));
}, '%END%');
await closeTab(pgR);
console.log('__DATA__' + txR);
"""


def fetch():
    end = dt.datetime.now(KST).strftime("%Y%m%d")
    out = subprocess.run([str(ASIDE), "repl", JS.replace("%END%", end)], capture_output=True, timeout=170)
    text = out.stdout.decode("utf-8", "replace")
    m = re.search(r"__DATA__(\[.*\])", text)
    if not m:
        raise SystemExit(f"조회 실패 (Aside 앱이 켜져 있는지 확인):\n{text[-800:]}\n{out.stderr.decode('utf-8', 'replace')[-400:]}")
    return json.loads(m.group(1))


def main():
    rows = fetch()
    old = {r["date"]: r for r in csv.DictReader(open(CSV, encoding="utf-8"))} if CSV.exists() else {}
    now = dt.datetime.now(KST).isoformat(timespec="seconds")
    revised = []
    for d, k, f, t in rows:
        o = old.get(d)
        if o and (int(o["kor"]), int(o["for"])) != (int(k), int(f)):
            revised.append([now, d, o["kor"], k, o["for"], f])
    dates = [r[0] for r in rows]
    gaps = [b for a, b in zip(dates, dates[1:])
            if (dt.date.fromisoformat(f"{b[:4]}-{b[4:6]}-{b[6:]}") - dt.date.fromisoformat(f"{a[:4]}-{a[4:6]}-{a[6:]}")).days != 1]
    with open(CSV, "w", newline="\n", encoding="utf-8") as fp:
        w = csv.writer(fp, lineterminator="\n")
        w.writerow(["date", "kor", "for", "total"])
        w.writerows(rows)
    if revised:
        rv = ROOT / "data/platform/revisions.csv"
        new = not rv.exists()
        with open(rv, "a", newline="\n", encoding="utf-8") as fp:
            w = csv.writer(fp, lineterminator="\n")
            if new:
                w.writerow(["fetched_at", "date", "kor_old", "kor_new", "for_old", "for_new"])
            w.writerows(revised)
    lg = ROOT / "data/platform/refresh_log.csv"
    new = not lg.exists()
    with open(lg, "a", newline="\n", encoding="utf-8") as fp:
        w = csv.writer(fp, lineterminator="\n")
        if new:
            w.writerow(["fetched_at", "first", "last", "rows", "revised", "gaps"])
        w.writerow([now, dates[0], dates[-1], len(rows), len(revised), len(gaps)])
    print(f"{len(rows)}행 {dates[0]}~{dates[-1]} · 이전 값과 달라진 날 {len(revised)} · 날짜 빈틈 {len(gaps)}")
    for r in revised[-10:]:
        print("  수정:", r[1], f"내국인 {r[2]}→{r[3]}", f"외국인 {r[4]}→{r[5]}")
    return dates[-1]


if __name__ == "__main__":
    main()
