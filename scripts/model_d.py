"""Model D — 제주 내국인 일별 입도객의 달력 기반 '비제약 수요' 예측.

log(입도객) = 요일 + 연휴 블록 위치(calendar_kr.FEATURES) + 연월 수준(FE) + 오차
목표 달의 수준은 두 추정의 평균:
  L1 = 직전 달 수준 + 과거 연도들의 (목표 달 - 직전 달) 수준 차 평균
  L2 = 작년 같은 달 수준 + 최근 두 달의 전년 대비 수준 차 평균
기준선 B1 = 364일 전 같은 요일 x 최근 28일 전년 대비 비율.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from calendar_kr import FEATURES, features

ROOT = Path(__file__).resolve().parents[1]
TRAIN_FROM = pd.Timestamp("2023-01-01")
# 훈련 기간에 없던 특징이 예측 기간에 나오면 가장 비슷한 특징으로 대신한다
FALLBACK = {"b_mid": "b_second", "b_second": "b_first", "mj_mid": "mj_first", "pre_major_8_14": "pre_major_2_7",
            "post_major_2_7": "post1", "pre_single": "pre1", "hol_single": "b_second"}
RIDGE = 1e-2


def load(col="kor"):
    d = pd.read_csv(ROOT / "data/platform/daily_arrivals.csv", dtype={"date": str})
    d.index = pd.to_datetime(d["date"])
    return d[col].astype(float)


def design(idx, use_calendar=True):
    idx = pd.DatetimeIndex(idx)
    parts = []
    if use_calendar:
        parts.append(features(idx))
    dow = pd.get_dummies(idx.dayofweek, prefix="dow", drop_first=True, dtype=float)
    dow.index = idx
    # 월 안의 계절 기울기(연중 푸리에 3차)와 여름 성수기(7/20~8/20)의 요일 모양
    doy = idx.dayofyear.values / 365.25
    season = pd.DataFrame(index=idx)
    for k in (1, 2, 3):
        season[f"sin{k}"] = np.sin(2 * np.pi * k * doy)
        season[f"cos{k}"] = np.cos(2 * np.pi * k * doy)
    md = idx.month * 100 + idx.day
    summer = ((md >= 720) & (md <= 820)).astype(float)
    season["summer"] = summer
    for d in range(1, 7):
        season[f"dow{d}_summer"] = ((idx.dayofweek == d) & (summer == 1)).astype(float)
    ym = pd.get_dummies(idx.strftime("%Y-%m"), prefix="ym", dtype=float)
    ym.index = idx
    return pd.concat(parts + [dow, season, ym], axis=1)


def solve(X, z):
    """작은 릿지(연월 FE는 벌점 없음)로 안정화한 최소제곱."""
    pen = np.array([0.0 if c.startswith("ym_") else RIDGE for c in X.columns])
    A = X.values.T @ X.values + np.diag(pen) * len(z)
    return np.linalg.solve(A + 1e-9 * np.eye(len(pen)), X.values.T @ z)


TRIM = 0.25  # 1차 잔차가 ±0.25(약 ±25%)를 넘는 날(기상 결항·그 반동)은 2차 적합에서 뺀다


def fit_train(y, cutoff, use_calendar=True):
    tr = y[(y.index >= TRAIN_FROM) & (y.index <= cutoff)]
    X = design(tr.index, use_calendar)
    X = X.loc[:, (X != 0).any()]
    z = np.log(tr.values)
    b = pd.Series(solve(X, z), index=X.columns)
    resid = z - X.values @ b.values
    keep = np.abs(resid) <= TRIM
    Xk = X[keep]
    Xk = Xk.loc[:, (Xk != 0).any()]
    b = pd.Series(solve(Xk, z[keep]), index=Xk.columns)
    resid = z - X[Xk.columns].values @ b.values
    return b, pd.Series(resid, index=tr.index)


def month_levels(b):
    return {c[3:]: v for c, v in b.items() if c.startswith("ym_")}


def target_level(lv, last, target):
    t_y, t_m = int(target[:4]), int(target[5:])
    l_y, l_m = int(last[:4]), int(last[5:])
    gap = (t_y - l_y) * 12 + (t_m - l_m)
    L1s = []
    for k in range(1, 4):
        a = f"{t_y - k}-{t_m:02d}"
        pl = pd.Period(a, "M") - gap
        b = pl.strftime("%Y-%m")
        if a in lv and b in lv:
            L1s.append(lv[a] - lv[b])
    L1 = lv[last] + np.mean(L1s) if L1s else None
    prev = pd.Period(last, "M") - 1
    yoy = [lv[p] - lv[(pd.Period(p, "M") - 12).strftime("%Y-%m")]
           for p in (last, prev.strftime("%Y-%m"))
           if p in lv and (pd.Period(p, "M") - 12).strftime("%Y-%m") in lv]
    ly = f"{t_y - 1}-{t_m:02d}"
    L2 = lv[ly] + np.mean(yoy) if (ly in lv and yoy) else None
    parts = [v for v in (L1, L2) if v is not None]
    return float(np.mean(parts)), {"L1": L1, "L2": L2}


def forecast(y, target_month, cutoff=None, use_calendar=True, days=None):
    """target_month 'YYYY-MM' 한 달치 예측. cutoff 이후 데이터는 쓰지 않는다."""
    first = pd.Timestamp(target_month + "-01")
    cutoff = cutoff or first - pd.Timedelta(days=3)
    b, resid = fit_train(y, cutoff, use_calendar)
    lv = month_levels(b)
    level, parts = target_level(lv, cutoff.strftime("%Y-%m"), target_month)
    days = days if days is not None else pd.date_range(first, first + pd.offsets.MonthEnd(0))
    Xf = design(days, use_calendar)
    for c in list(Xf.columns):
        if c in FEATURES and c not in b.index and Xf[c].any():
            fb = FALLBACK.get(c)
            if fb in Xf.columns:
                Xf[fb] = Xf[fb] + Xf[c]
    cols = [c for c in b.index if not c.startswith("ym_")]
    Xf = Xf.reindex(columns=cols, fill_value=0.0)
    base = Xf.values @ b[cols].values
    info = {"level": level, **parts, "resid_sd": float(resid.std()), "cutoff": str(cutoff.date())}
    return pd.Series(np.exp(base + level), index=days), info, b


def baseline_b1(y, target_month, cutoff=None):
    first = pd.Timestamp(target_month + "-01")
    cutoff = cutoff or first - pd.Timedelta(days=3)
    days = pd.date_range(first, first + pd.offsets.MonthEnd(0))
    rec = y[(y.index > cutoff - pd.Timedelta(days=28)) & (y.index <= cutoff)]
    ly = y.reindex(rec.index - pd.Timedelta(days=364))
    r = rec.sum() / ly.sum()
    return pd.Series(y.reindex(days - pd.Timedelta(days=364)).values * r, index=days)
