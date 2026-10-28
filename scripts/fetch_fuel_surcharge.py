"""국내선 유류할증료 월별 시계열 — 항공여행(airtravelinfo.kr) 월간 글 「항공 유류할증료(YYYY년 M월)」에서 국내선 편도 값을 뽑는다.

    python scripts/fetch_fuel_surcharge.py
산출: data/external/fuel_surcharge_domestic.csv (month, krw, level, url, snippet) — 요청 간격 2초.
값은 발권월 기준(대한항공·아시아나 동일 적용). 뽑지 못한 달은 빈칸으로 남기고 snippet으로 확인한다.
"""
import csv
import re
import time
from pathlib import Path

from curl_cffi import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/external/fuel_surcharge_domestic.csv"
BASE = "https://airtravelinfo.kr"
LIST = BASE + "/index.php?mid=info_etc&search_target=title&search_keyword=%EC%9C%A0%EB%A5%98%ED%95%A0%EC%A6%9D%EB%A3%8C&page={}"


def main():
    s = requests.Session(impersonate="chrome")
    posts = {}
    for page in range(1, 8):
        html = s.get(LIST.format(page), timeout=30).text
        # 목록의 JSON-LD(ItemList)에서 제목과 주소를 읽는다
        for title, srl in re.findall(r'"headline":\s*"([^"]+)",\s*"url":\s*"/info_etc/(\d+)"', html):
            ym = re.search(r"유류할증료\s*\((20\d\d)년\s*(\d{1,2})월\)", title)
            if ym:
                posts.setdefault(f"{ym.group(1)}-{int(ym.group(2)):02d}", srl)
        time.sleep(2)
    rows = []
    for key in sorted(posts):
        if key < "2024-01":
            continue
        url = f"{BASE}/info_etc/{posts[key]}"
        html = s.get(url, timeout=30).text
        desc = re.search(r'<meta name="description" content="([^"]*)"', html)
        body = re.sub(r"<[^>]+>", " ", html)
        text = (desc.group(1) if desc else "") + " " + body
        m = re.search(r"국내선[^.。]{0,40}?(\d{1,2},\d{3})원\s*\((\d{1,2})단계\)", text) or re.search(r"국내선[^.。]{0,60}?(\d{1,2},\d{3})원", text)
        krw = int(m.group(1).replace(",", "")) if m else ""
        level = m.group(2) if (m and m.lastindex and m.lastindex >= 2) else ""
        snip = re.search(r"국내선[^.。]{0,80}", text)
        rows.append([key, krw, level, url, snip.group(0).strip() if snip else ""])
        print(key, krw, level, flush=True)
        time.sleep(2)
    with OUT.open("w", encoding="utf-8", newline="\n") as fp:
        w = csv.writer(fp, lineterminator="\n")
        w.writerow(["month", "krw", "level", "url", "snippet"])
        w.writerows(rows)
    print(f"{len(rows)}개월 → {OUT.name}")


if __name__ == "__main__":
    main()
