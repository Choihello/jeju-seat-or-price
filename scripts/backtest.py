"""롤링 백테스트 — 매달 1일 3일 전까지의 데이터로 그 달 전체를 예측하고 채점한다.

산출: results/backtest_daily.csv (일별 예측·오차), results/backtest_summary.md
    python scripts/backtest.py [종료일]   # 기본 2026-09-24(보고서 수치의 기준, 31개월)
'모양 오차'는 월 합계를 실측에 맞춘 뒤의 일별 MAPE — 달력 특징만의 성능이다.
"""
import sys

import numpy as np
import pandas as pd

from model_d import ROOT, baseline_b1, forecast, load

END = sys.argv[1] if len(sys.argv) > 1 else "2026-09-24"
y = load("kor").loc[:END]
months = pd.period_range("2024-03", y.index.max().strftime("%Y-%m"), freq="M").strftime("%Y-%m")
rows = []
for tm in months:
    fd, info, _ = forecast(y, tm)
    fn, _, _ = forecast(y, tm, use_calendar=False)
    fb = baseline_b1(y, tm)
    act = y.reindex(fd.index).dropna()
    scale_d = act.sum() / fd[act.index].sum()
    scale_n = act.sum() / fn[act.index].sum()
    for d in act.index:
        rows.append({"date": d.date(), "month": tm, "actual": act[d], "D": fd[d], "D_nocal": fn[d], "B1": fb[d],
                     "D_shape": fd[d] * scale_d, "nocal_shape": fn[d] * scale_n, "level_L1": info["L1"], "level_L2": info["L2"]})
bt = pd.DataFrame(rows)
for k in ("D", "D_nocal", "B1", "D_shape", "nocal_shape"):
    bt[f"ape_{k}"] = (bt[k] / bt.actual - 1).abs() * 100
    bt[f"le_{k}"] = np.log(bt.actual / bt[k])
# 결항 의심일(모양 기준 실측이 예측의 75% 미만)과 그 다음 날 — 채점 규칙 보조용(본 채점은 항공 운항 실적으로 판정)
dis = bt.le_D_shape < np.log(0.75)
bt["disrupt"] = dis | dis.shift(1, fill_value=False)
ok = ~bt.disrupt
print(f"결항 의심일+다음날 {bt.disrupt.sum()}일 제외 시: MAPE D {bt.ape_D[ok].mean():.1f}% · B1 {bt.ape_B1[ok].mean():.1f}% · 모양 {bt.ape_D_shape[ok].mean():.1f}% · 달력제외 모양 {bt.ape_nocal_shape[ok].mean():.1f}%")
out = ROOT / "results"
out.mkdir(exist_ok=True)
bt.to_csv(out / "backtest_daily.csv", index=False, encoding="utf-8")

g = bt.groupby("month")
by_m = pd.DataFrame({"MAPE_D": g.ape_D.mean(), "MAPE_nocal": g.ape_D_nocal.mean(), "MAPE_B1": g.ape_B1.mean(),
                     "shape_D": g.ape_D_shape.mean()})
tot = g[["actual", "D", "B1"]].sum()
by_m["month_err_D%"] = (tot.D / tot.actual - 1) * 100
by_m["month_err_B1%"] = (tot.B1 / tot.actual - 1) * 100
q = bt.le_D.quantile([0.025, 0.1, 0.5, 0.9, 0.975])
qs = bt.le_D_shape.quantile([0.1, 0.9])
lines = ["# 백테스트 요약 (내국인 일별 입도객)", "",
         f"- 기간: {months[0]} ~ {months[-1]} ({len(months)}개월, {len(bt)}일), 매달 1일 3일 전 데이터까지만 사용",
         f"- 일별 MAPE: Model D {bt.ape_D.mean():.1f}% · 달력특징 제외 {bt.ape_D_nocal.mean():.1f}% · B1(364일 전×최근비) {bt.ape_B1.mean():.1f}%",
         f"- 모양 오차(월 합계를 맞춘 뒤): Model D {bt.ape_D_shape.mean():.1f}% · 달력특징 제외 {bt.ape_nocal_shape.mean():.1f}%",
         f"- 월 합계 절대오차 평균: Model D {by_m['month_err_D%'].abs().mean():.1f}% · B1 {by_m['month_err_B1%'].abs().mean():.1f}%",
         f"- Model D 로그오차 분위수: 2.5% {q[0.025]:+.3f} · 10% {q[0.1]:+.3f} · 50% {q[0.5]:+.3f} · 90% {q[0.9]:+.3f} · 97.5% {q[0.975]:+.3f}",
         f"- 모양 로그오차 10~90%: {qs[0.1]:+.3f} ~ {qs[0.9]:+.3f}",
         "", "| 월 | MAPE D | 달력제외 | B1 | 모양 오차 D | 월합계 오차 D | 월합계 오차 B1 |", "|---|---|---|---|---|---|---|"]
for m, r in by_m.iterrows():
    lines.append(f"| {m} | {r.MAPE_D:.1f} | {r.MAPE_nocal:.1f} | {r.MAPE_B1:.1f} | {r.shape_D:.1f} | {r['month_err_D%']:+.1f}% | {r['month_err_B1%']:+.1f}% |")
(out / "backtest_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
