"""좌석이냐 가격이냐 — 제주행 국내선 편수(공급)·여객(수요)·편당 여객(탑승)의 전년 대비 변화를 유류할증료 변화와 맞댄다.

    python scripts/price_vs_seats.py
입력: data/external/airportal_cju_routes_monthly.csv, data/external/fuel_surcharge_domestic.csv, data/platform/daily_arrivals.csv
판정 규칙(월별): 편당 여객 전년비 > +1% 이고 편수 전년비 < 0 → '좌석 제약', 편당 여객 전년비 < -1% → '수요 감소', 그 밖 → '혼합'
결과: results/price_vs_seats.md
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from model_d import ROOT

r = pd.read_csv(ROOT / "data/external/airportal_cju_routes_monthly.csv")
g = r.groupby("month")[["arr_fp", "arr_person"]].sum()
g.index = pd.PeriodIndex(g.index, freq="M")
fs = pd.read_csv(ROOT / "data/external/fuel_surcharge_domestic.csv")
fs.index = pd.PeriodIndex(fs.month, freq="M")
da = pd.read_csv(ROOT / "data/platform/daily_arrivals.csv", dtype={"date": str})
da.index = pd.to_datetime(da.date)
kor = da.kor.resample("MS").sum()
kor.index = kor.index.to_period("M")

d = pd.DataFrame({"flights": g.arr_fp, "pax": g.arr_person, "kor": kor.reindex(g.index), "fuel": fs.krw.reindex(g.index)})
d["ppf"] = d.pax / d.flights
for c in ("flights", "pax", "ppf", "kor"):
    d[f"{c}_yoy"] = (d[c] / d[c].shift(12) - 1) * 100
d["fuel_dyoy"] = d.fuel - d.fuel.shift(12)
d["crash_base"] = [1 if str(p) in ("2026-01", "2026-02", "2026-03") else 0 for p in d.index]  # 2025년 1~3월 참사·계엄 기저
d["verdict"] = np.where((d.ppf_yoy > 1) & (d.flights_yoy < 0), "좌석 제약", np.where(d.ppf_yoy < -1, "수요 감소", "혼합"))
s = d.loc["2025-05":].dropna(subset=["fuel_dyoy", "pax_yoy"]).copy()
m = smf.ols("pax_yoy ~ fuel_dyoy + flights_yoy + crash_base", data=s.assign(fuel_dyoy=s.fuel_dyoy / 10000)).fit()
m2 = smf.ols("ppf_yoy ~ fuel_dyoy + crash_base", data=s.assign(fuel_dyoy=s.fuel_dyoy / 10000)).fit()
lines = ["# 좌석이냐 가격이냐 (제주행 국내선, 전년 동월 대비)", "",
         f"- 기간 {s.index.min()}~{s.index.max()} ({len(s)}개월). 유류할증료는 발권월 기준 국내선 편도(대한항공·아시아나 공통).",
         f"- 여객 전년비 = {m.params['Intercept']:+.1f} {m.params['fuel_dyoy']:+.2f}×(할증료 전년차, 만원) {m.params['flights_yoy']:+.2f}×(편수 전년비) · "
         f"할증료 계수 p={m.pvalues['fuel_dyoy']:.3f}, 편수 계수 p={m.pvalues['flights_yoy']:.3f}, R²={m.rsquared:.2f} (2026년 1~3월 기저효과 더미 포함)",
         f"- 편당 여객 전년비 = {m2.params['Intercept']:+.1f} {m2.params['fuel_dyoy']:+.2f}×(할증료 전년차, 만원) · p={m2.pvalues['fuel_dyoy']:.3f}, R²={m2.rsquared:.2f}",
         "- 표본이 작다(월 단위). 방향과 크기를 보는 근거이며, 일별·노선별 자료로 보강한다.",
         "", "| 월 | 편수 | 여객 | 편당 여객 | 입도객(내국인) | 할증료(편도) | 할증료 전년차 | 판정 |", "|---|---|---|---|---|---|---|---|"]
for p, x in d.loc["2025-01":].iterrows():
    f = "" if np.isnan(x.fuel) else f"{x.fuel:,.0f}원"
    fd = "" if np.isnan(x.fuel_dyoy) else f"{x.fuel_dyoy:+,.0f}원"
    kv = "" if np.isnan(x.kor_yoy) else f"{x.kor_yoy:+.1f}%"
    lines.append(f"| {p} | {x.flights_yoy:+.1f}% | {x.pax_yoy:+.1f}% | {x.ppf_yoy:+.1f}% | {kv} | {f} | {fd} | {x.verdict} |")
(ROOT / "results/price_vs_seats.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("\n".join(lines))
