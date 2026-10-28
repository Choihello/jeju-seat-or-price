"""airportal 제주 노선별 월간 실적 — 한 달 1건 요청으로 제주↔국내 공항 노선×항공사의 운항·여객을 받는다.

    python scripts/fetch_airportal_routes.py 2023-01 2026-08
출처: 항공정보포털 일자별 통계(노선), 기간 합계. 요청 간격 2초.
산출: data/external/airportal_cju_routes_monthly.csv (month, origin, airline, arr_fp, arr_person, dep_fp, dep_person)
arr = 제주 도착(출발지 → 제주), dep = 제주 출발.
"""
import calendar
import csv
import json
import sys
import time
from pathlib import Path

import pandas as pd
from curl_cffi import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/airportal_cju_routes_monthly.csv"
PAGE = "https://www.airportal.go.kr/stats/transport/dailyRoute.do"
API = "https://www.airportal.go.kr/stats/transport/selectDailyStatisticsByRoute.do"
HDR = {"Content-Type": "application/json;charset=UTF-8", "X-Requested-With": "XMLHttpRequest", "Referer": PAGE}


def num(v):
    return int(str(v or 0).replace(",", ""))


def main(a, b):
    have = set(pd.read_csv(OUT).month.astype(str)) if OUT.exists() else set()
    s = requests.Session(impersonate="chrome")
    s.get(PAGE, timeout=30)
    new = not OUT.exists()
    with OUT.open("a", encoding="utf-8", newline="\n") as fp:
        w = csv.writer(fp, lineterminator="\n")
        if new:
            w.writerow(["month", "origin", "airline", "arr_fp", "arr_person", "dep_fp", "dep_person"])
        for p in pd.period_range(a, b, freq="M"):
            m = p.strftime("%Y-%m")
            if m in have:
                continue
            last = calendar.monthrange(p.year, p.month)[1]
            body = {"startDt": f"{p.year}{p.month:02d}01", "endDt": f"{p.year}{p.month:02d}{last}", "koreaAirport": "RKPC", "airlineType": "D"}
            j = s.post(API, data=json.dumps(body), headers=HDR, timeout=60).json()
            for x in j.get("content") or []:
                w.writerow([m, x.get("ap2"), x.get("al_ICAO"), num(x.get("arr_FP")), num(x.get("arr_PERSON")), num(x.get("dep_FP")), num(x.get("dep_PERSON"))])
            fp.flush()
            print(m, len(j.get("content") or []), flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2023-01", sys.argv[2] if len(sys.argv) > 2 else "2026-08")
