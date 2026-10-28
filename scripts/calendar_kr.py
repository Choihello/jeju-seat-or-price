"""한국 공휴일 달력과 일별 달력 특징(제주 입도객 모형용).

연휴 블록 = 주말·공휴일이 3일 이상 이어진 구간. 입도객은 블록 첫날(또는 전날 저녁)에 몰리고
마지막 날에 빠지므로, 블록 안 위치(첫날·둘째 날·중간·마지막 날)와 앞뒤 평일을 따로 본다.
설·추석(major)은 귀성과 겹쳐 모양이 달라 별도 계수를 둔다.
"""
import datetime as dt

import pandas as pd

# (날짜, 이름, major 여부) — 대체공휴일·임시공휴일·선거일 포함. 근로자의 날(5/1)은 민간 다수가 쉬어 여행 수요상 휴일로 본다
HOLIDAYS = [
    ("2023-01-01", "신정", 0), ("2023-01-21", "설날", 1), ("2023-01-22", "설날", 1), ("2023-01-23", "설날", 1),
    ("2023-01-24", "설날 대체", 1), ("2023-03-01", "삼일절", 0), ("2023-05-01", "근로자의 날", 0), ("2023-05-05", "어린이날", 0),
    ("2023-05-27", "부처님오신날", 0), ("2023-05-29", "대체공휴일", 0), ("2023-06-06", "현충일", 0),
    ("2023-08-15", "광복절", 0), ("2023-09-28", "추석", 1), ("2023-09-29", "추석", 1), ("2023-09-30", "추석", 1),
    ("2023-10-02", "임시공휴일", 1), ("2023-10-03", "개천절", 1), ("2023-10-09", "한글날", 0),
    ("2023-12-25", "성탄절", 0),
    ("2024-01-01", "신정", 0), ("2024-02-09", "설날", 1), ("2024-02-10", "설날", 1), ("2024-02-11", "설날", 1),
    ("2024-02-12", "설날 대체", 1), ("2024-03-01", "삼일절", 0), ("2024-04-10", "총선", 0), ("2024-05-01", "근로자의 날", 0),
    ("2024-05-05", "어린이날", 0), ("2024-05-06", "대체공휴일", 0), ("2024-05-15", "부처님오신날", 0),
    ("2024-06-06", "현충일", 0), ("2024-08-15", "광복절", 0), ("2024-09-16", "추석", 1), ("2024-09-17", "추석", 1),
    ("2024-09-18", "추석", 1), ("2024-10-01", "국군의날 임시", 0), ("2024-10-03", "개천절", 0),
    ("2024-10-09", "한글날", 0), ("2024-12-25", "성탄절", 0),
    ("2025-01-01", "신정", 0), ("2025-01-27", "임시공휴일", 1), ("2025-01-28", "설날", 1), ("2025-01-29", "설날", 1),
    ("2025-01-30", "설날", 1), ("2025-03-01", "삼일절", 0), ("2025-03-03", "대체공휴일", 0), ("2025-05-01", "근로자의 날", 0),
    ("2025-05-05", "어린이날·부처님오신날", 0), ("2025-05-06", "대체공휴일", 0), ("2025-06-03", "대선", 0),
    ("2025-06-06", "현충일", 0), ("2025-08-15", "광복절", 0), ("2025-10-03", "개천절", 1),
    ("2025-10-05", "추석", 1), ("2025-10-06", "추석", 1), ("2025-10-07", "추석", 1), ("2025-10-08", "추석 대체", 1),
    ("2025-10-09", "한글날", 1), ("2025-12-25", "성탄절", 0),
    ("2026-01-01", "신정", 0), ("2026-02-16", "설날", 1), ("2026-02-17", "설날", 1), ("2026-02-18", "설날", 1),
    ("2026-03-01", "삼일절", 0), ("2026-03-02", "대체공휴일", 0), ("2026-05-01", "근로자의 날", 0), ("2026-05-05", "어린이날", 0),
    ("2026-05-24", "부처님오신날", 0), ("2026-05-25", "대체공휴일", 0), ("2026-06-03", "지방선거", 0),
    ("2026-06-06", "현충일", 0), ("2026-08-15", "광복절", 0), ("2026-08-17", "대체공휴일", 0),
    ("2026-09-24", "추석", 1), ("2026-09-25", "추석", 1), ("2026-09-26", "추석", 1),
    ("2026-10-03", "개천절", 0), ("2026-10-05", "대체공휴일", 0), ("2026-10-09", "한글날", 0),
    ("2026-12-25", "성탄절", 0),
]
HOL = {dt.date.fromisoformat(d): (n, m) for d, n, m in HOLIDAYS}

FEATURES = ["pre1", "b_first", "b_second", "b_mid", "b_last", "post1",
            "mj_first", "mj_mid", "mj_last", "hol_single", "pre_single",
            "pre_major_2_7", "pre_major_8_14", "post_major_2_7"]


def is_off(d):
    return d.weekday() >= 5 or d in HOL


def blocks(start, end):
    """[start-20, end+20] 범위에서 3일 이상 이어진 휴무 블록 목록: (first, last, major)."""
    d0, d1 = start - dt.timedelta(days=20), end + dt.timedelta(days=20)
    out, d = [], d0
    while d <= d1:
        if is_off(d):
            s = d
            while d + dt.timedelta(days=1) <= d1 and is_off(d + dt.timedelta(days=1)):
                d += dt.timedelta(days=1)
            if (d - s).days + 1 >= 3:
                major = any(HOL.get(s + dt.timedelta(days=k), ("", 0))[1] for k in range((d - s).days + 1))
                out.append((s, d, major))
        d += dt.timedelta(days=1)
    return out


def features(dates):
    """날짜 인덱스 → 달력 특징 DataFrame(요일 더미 제외)."""
    idx = pd.DatetimeIndex(dates)
    ds = [t.date() for t in idx]
    f = pd.DataFrame(0, index=idx, columns=FEATURES, dtype=float)
    bl = blocks(min(ds), max(ds))
    for s, e, major in bl:
        n = (e - s).days + 1
        for k in range(n):
            day = s + dt.timedelta(days=k)
            t = pd.Timestamp(day)
            if t not in f.index:
                continue
            if major:
                col = "mj_first" if k == 0 else ("mj_last" if k == n - 1 else "mj_mid")
                f.loc[t, col] = 1
            else:
                col = "b_first" if k == 0 else ("b_second" if k == 1 and n > 2 else ("b_last" if k == n - 1 else "b_mid"))
                f.loc[t, col] = 1
        for off, col in ((-1, "pre1"), (n, "post1")):
            t = pd.Timestamp(s + dt.timedelta(days=off))
            if t in f.index and not is_off(t.date()):
                f.loc[t, col] = 1
        if major:
            for k in range(2, 15):
                t = pd.Timestamp(s - dt.timedelta(days=k))
                if t in f.index and not is_off(t.date()):
                    f.loc[t, "pre_major_2_7" if k <= 7 else "pre_major_8_14"] = 1
            for k in range(2, 8):
                t = pd.Timestamp(e + dt.timedelta(days=k))
                if t in f.index and not is_off(t.date()):
                    f.loc[t, "post_major_2_7"] = 1
    in_block = f[["b_first", "b_second", "b_mid", "b_last", "mj_first", "mj_mid", "mj_last"]].sum(axis=1) > 0
    for t in f.index:
        d = t.date()
        if d in HOL and not in_block[t] and d.weekday() < 5:
            f.loc[t, "hol_single"] = 1
            p = pd.Timestamp(d - dt.timedelta(days=1))
            if p in f.index and not is_off(p.date()):
                f.loc[p, "pre_single"] = 1
    return f


if __name__ == "__main__":
    oct26 = pd.date_range("2026-09-20", "2026-10-31")
    f = features(oct26)
    f["dow"] = oct26.day_name().str[:3]
    print(f.loc[:, (f != 0).any()].to_string())
