"""10월 사전등록 예측 — Model D 일별 예측과 예측구간, 채점용 날짜 묶음(C·W·N)을 만든다.

    python scripts/forecast.py            # 지금 있는 데이터 끝까지로 초안
    python scripts/forecast.py 2026-09-28 # 최종(9/29 아침, 9/28 값까지 반영)
산출: results/forecast_2026-10_<cutoff>.csv, 화면 요약
"""
import sys

import numpy as np
import pandas as pd

from calendar_kr import features
from model_d import ROOT, baseline_b1, forecast, load

TARGET = "2026-10"
W = pd.date_range("2026-10-13", "2026-10-21")        # 전국체전(10/16~22) 도외 참가자 입도 창
N_PEAK = 4                                            # C = 전국체전 창 밖에서 예측이 가장 높은 4일


def build(cutoff=None, target=TARGET, win=W):
    y = load("kor")
    cutoff = pd.Timestamp(cutoff) if cutoff else y.index.max()
    y = y[y.index <= cutoff]
    fd, info, b = forecast(y, target, cutoff=cutoff)
    b1 = baseline_b1(y, target, cutoff=cutoff)
    bt = pd.read_csv(ROOT / "results/backtest_daily.csv")
    q = bt.le_D.quantile([0.025, 0.1, 0.9, 0.975])
    F = features(fd.index)
    df = pd.DataFrame({"date": fd.index.date, "dow": fd.index.day_name().str[:3], "D": fd.round(0),
                       "PI80_lo": (fd * np.exp(q[0.1])).round(0), "PI80_hi": (fd * np.exp(q[0.9])).round(0),
                       "PI95_lo": (fd * np.exp(q[0.025])).round(0), "PI95_hi": (fd * np.exp(q[0.975])).round(0),
                       "B1": b1.round(0)}, index=fd.index)
    df["W_sports"] = df.index.isin(win)
    top = df[~df.W_sports].D.nlargest(N_PEAK).index
    df["C_peak"] = df.index.isin(top)
    holiday_ctx = F[["pre1", "b_first", "b_second", "b_mid", "b_last", "post1", "mj_first", "mj_mid", "mj_last"]].sum(axis=1) > 0
    df["N_normal"] = ~(df.C_peak | df.W_sports | holiday_ctx)    # N = 연휴 블록·앞뒤 평일·C·W가 아닌 평상일
    meta = {"cutoff": str(cutoff.date()), "level": info["level"], "L1": info["L1"], "L2": info["L2"],
            "log_err_q": {str(k): float(v) for k, v in q.items()}, "n_backtest_days": int(len(bt)),
            "calendar_coefs": {k: float(v) for k, v in b.items() if not k.startswith("ym_")}}
    return df, meta


if __name__ == "__main__":
    df, meta = build(sys.argv[1] if len(sys.argv) > 1 else None)
    out = ROOT / f"results/forecast_{TARGET}_{meta['cutoff']}.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"cutoff {meta['cutoff']} · level L1 {meta['L1']:.3f} L2 {meta['L2']:.3f} → {meta['level']:.3f}")
    print(df.drop(columns=["PI95_lo", "PI95_hi"]).to_string(index=False))
    print(f"\n10월 합계 예측 {df.D.sum():,.0f} (B1 {df.B1.sum():,.0f}) · C={list(df.index[df.C_peak].strftime('%m-%d'))} · N {df.N_normal.sum()}일")
