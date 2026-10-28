"""airportal 일자별 공항 통계 수집 — 하루 1건 요청으로 전국 공항의 국내선·국제선 운항·여객을 받는다.

    python scripts/fetch_airportal.py 2023-01-01 2026-09-24
출처: 항공정보포털(airportal.go.kr, 국토교통부·한국항공협회) 공개 통계. robots.txt 없음, 요청 간격 1.2초.
산출: data/external/airportal_daily_airports.jsonl(원자료, 이어받기 가능), data/external/airportal_cju_daily.csv(제주 요약)
"""
import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path

from curl_cffi import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/external/airportal_daily_airports.jsonl"
CJU = ROOT / "data/external/airportal_cju_daily.csv"
PAGE = "https://www.airportal.go.kr/stats/transport/dailyAirportRoute.do"
API = "https://www.airportal.go.kr/stats/transport/selectDailyStatisticsByAirportRoute.do"
HDR = {"Content-Type": "application/json;charset=UTF-8", "X-Requested-With": "XMLHttpRequest", "Referer": PAGE}
GAP = 1.2


def done_days():
    if not RAW.exists():
        return set()
    return {json.loads(l)["date"] for l in RAW.open(encoding="utf-8") if l.strip()}


def fetch(start, end):
    RAW.parent.mkdir(parents=True, exist_ok=True)
    have = done_days()
    s = requests.Session(impersonate="chrome")
    s.get(PAGE, timeout=30)
    d, n = start, 0
    with RAW.open("a", encoding="utf-8", newline="\n") as fp:
        while d <= end:
            key = d.strftime("%Y%m%d")
            if key not in have:
                for attempt in range(3):
                    try:
                        j = s.post(API, data=json.dumps({"startDt": key, "endDt": key}), headers=HDR, timeout=30).json()
                        fp.write(json.dumps({"date": key, "rows": j.get("content") or []}, ensure_ascii=False) + "\n")
                        fp.flush()
                        n += 1
                        break
                    except Exception as e:  # 일시 오류는 잠시 쉬고 재시도
                        print(key, "retry", attempt, e, flush=True)
                        time.sleep(10 * (attempt + 1))
                time.sleep(GAP)
                if n % 50 == 0:
                    print(key, "fetched", n, flush=True)
            d += dt.timedelta(days=1)
    return n


def summarize():
    rows = {}
    for l in RAW.open(encoding="utf-8"):
        rec = json.loads(l)
        out = {"date": f"{rec['date'][:4]}-{rec['date'][4:6]}-{rec['date'][6:]}"}
        for r in rec["rows"]:
            if r.get("ap_icao") != "제주":
                continue
            k = {"국내선": "dom", "국제선": "int"}.get(r.get("int_dom_cls"))
            if k:
                for f in ("arr_fp", "dep_fp", "arr_person", "dep_person"):
                    out[f"{k}_{f}"] = int(str(r.get(f) or 0).replace(",", ""))
        rows[out["date"]] = out
    cols = ["date", "dom_arr_fp", "dom_arr_person", "dom_dep_fp", "dom_dep_person", "int_arr_fp", "int_arr_person", "int_dep_fp", "int_dep_person"]
    with CJU.open("w", encoding="utf-8", newline="\n") as fp:
        w = csv.DictWriter(fp, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for k in sorted(rows):
            w.writerow({c: rows[k].get(c, "") for c in cols})
    return len(rows)


if __name__ == "__main__":
    a = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2023, 1, 1)
    b = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date.today() - dt.timedelta(days=1)
    print("new days", fetch(a, b), flush=True)
    print("cju rows", summarize(), flush=True)
