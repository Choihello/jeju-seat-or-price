"""위약 검사 — 특별 행사가 없던 과거 달에 H1·H2 규칙을 그대로 적용해 우연히 기준을 넘는 비율을 본다.

    python scripts/placebo.py
각 달을 그 달 1일 3일 전 데이터로 예측하고, C = 예측 상위 4일, W = 13~21일 중 연휴 관련이 아닌 날(가짜 행사 창), N = 평상일.
결과: results/placebo.md
"""
import numpy as np
import pandas as pd

from calendar_kr import features
from forecast import build
from model_d import ROOT, load

y = load("kor")
rows = []
for tm in pd.period_range("2025-03", "2026-08", freq="M").strftime("%Y-%m"):
    first = pd.Timestamp(tm + "-01")
    win = pd.date_range(first + pd.Timedelta(days=12), first + pd.Timedelta(days=20))
    df, meta = build((first - pd.Timedelta(days=3)).strftime("%Y-%m-%d"), target=tm, win=win)
    act = y.reindex(df.index)
    lr = np.log(act / df.D)
    N = df.index[df.N_normal]
    lev = lr[N].mean()
    dis = act < 0.75 * df.D * np.exp(lev)
    dis = dis | dis.shift(1, fill_value=False)
    ok = ~dis
    ctx = features(df.index)[["pre1", "b_first", "b_second", "b_mid", "b_last", "post1", "mj_first", "mj_mid", "mj_last"]].sum(axis=1) > 0
    Wc = [t for t in df.index[df.W_sports] if not ctx[t]]   # 10월 창처럼 연휴 관련 날은 뺀다
    m = lambda ix: lr[[t for t in ix if ok[t]]].mean()
    rows.append({"month": tm, "d1": m(df.index[df.C_peak]) - m(N), "d2": m(Wc) - m(N), "nW": len(Wc),
                 "nN": int(sum(ok[t] for t in N))})
t = pd.DataFrame(rows)
lines = ["# 위약 검사 (2025-03~2026-08, 행사 없는 가짜 창)", "",
         f"- Δ1(피크 상위 4일 - 평상일): 평균 {t.d1.mean():+.3f}, 표준편차 {t.d1.std():.3f}, ≤-0.05 비율 {(t.d1 <= -0.05).mean():.0%}, ≥-0.02 비율 {(t.d1 >= -0.02).mean():.0%}",
         f"- Δ2(13~21일 - 평상일): 평균 {t.d2.mean():+.3f}, 표준편차 {t.d2.std():.3f}, ≥+0.05 비율 {(t.d2 >= 0.05).mean():.0%}, ≤+0.02 비율 {(t.d2 <= 0.02).mean():.0%}",
         "", "| 월 | Δ1 | Δ2 | N일수 | W일수 |", "|---|---|---|---|---|"]
lines += [f"| {r.month} | {r.d1:+.3f} | {r.d2:+.3f} | {r.nN} | {r.nW} |" for r in t.itertuples()]
bt = pd.read_csv(ROOT / "results/backtest_daily.csv")
win = bt.groupby("month").apply(lambda g: g.ape_D.mean() < g.ape_B1.mean())
lines.insert(4, f"- 백테스트에서 Model D가 B1보다 일별 MAPE가 낮은 달: {int(win.sum())}/{len(win)}개월")
(ROOT / "results/placebo.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
