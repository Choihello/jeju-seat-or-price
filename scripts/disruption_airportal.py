"""결항 충격 실증 — 모형이 예측한 입도객보다 크게 모자란 날을 공항 여객으로 교차 확인하고, 이후 회복을 잰다.

    python scripts/disruption_airportal.py [종료일]
분석 기간: 2023-01-01 ~ 종료일(기본 2026-09-24, 보고서 수치의 기준). 종료일을 늘리면 모형을 다시 맞춰 경계선 사건이 바뀔 수 있다.
입력: data/external/airportal_cju_daily.csv(airportal 제주 국내선), data/platform/daily_arrivals.csv(플랫폼 입도객)
결항일 판정(둘 다 만족):
  ① 플랫폼 입도객이 Model D 예측(달력·연휴 반영)의 75% 미만
  ② airportal 제주 도착 국내선 여객이 직전 4주 같은 요일 중앙값의 80% 미만(통계 오류가 아닌 실제 승객 감소)
  단, 5일 이상 연휴가 끝난 뒤 3일 안은 제외(연휴 뒤 급감은 날씨가 아니라 수요).
편수는 기준으로 쓰지 않는다 — 결항일에도 체류객 수송용 빈 비행기가 들어와 도착 편수는 거의 정상이다(예: 2024-01-23 173편, 여객 1,799명).
여유 좌석 대리지표: 결항 전 28일 평균 탑승 지수(편당 도착 여객 ÷ ±45일 편당 여객 95분위수). 결항 뒤 탑승 지수는 회복분이 채운 결과라 쓰지 않는다.
결과: results/disruption_airportal.md, results/disruption_airportal.csv
"""
import datetime as dt
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

import model_d as M
from calendar_kr import blocks
from model_d import ROOT

END = sys.argv[1] if len(sys.argv) > 1 else "2026-09-24"
SPEND_CARD, SPEND_SURVEY = 187225, 637140  # 2025 내국인 관광객 1인 카드 포착 소비(플랫폼 카드/입도객), 실태조사 1인 여행경비

ap = pd.read_csv(ROOT / "data/external/airportal_cju_daily.csv", parse_dates=["date"]).set_index("date").sort_index().loc[:END]
ap["ppf"] = ap.dom_arr_person / ap.dom_arr_fp.replace(0, np.nan)
wk = lambda s, d: s.reindex([d - pd.Timedelta(days=7 * k) for k in range(1, 5)]).median()
ap["px_ratio"] = [ap.dom_arr_person[d] / wk(ap.dom_arr_person, d) for d in ap.index]
ap["fp_ratio"] = [ap.dom_arr_fp[d] / wk(ap.dom_arr_fp, d) for d in ap.index]
ap["dep_base"] = [wk(ap.dom_dep_person, d) for d in ap.index]
ap["load_idx"] = ap.ppf / ap.ppf.rolling(91, center=True, min_periods=30).quantile(0.95)

y = M.load("kor").loc[:END]
b, r = M.fit_train(y, y.index.max())
df = ap.join(y.rename("kor"), how="inner")
df["pred"] = (y / np.exp(r)).reindex(df.index)
df["lr"] = r.reindex(df.index)

long_after = set()
for s, e, _ in blocks(df.index.min().date(), df.index.max().date()):
    if (e - s).days + 1 >= 5:
        long_after |= {pd.Timestamp(e + dt.timedelta(days=k)) for k in range(1, 4)}
df["disrupt"] = (df.lr < np.log(0.75)) & (df.px_ratio < 0.8) & ~df.index.isin(long_after)

eps, cur = [], []
for d, flag in df.disrupt.items():
    if flag:
        cur.append(d)
    elif cur:
        eps.append(cur)
        cur = []
rows = []
for e in eps:
    after = [a for a in pd.date_range(e[-1] + pd.Timedelta(days=1), periods=7) if a in df.index and not df.disrupt.get(a, False)]
    before = [a for a in pd.date_range(e[0] - pd.Timedelta(days=2), periods=2) if a in df.index]
    pre28 = [a for a in pd.date_range(e[0] - pd.Timedelta(days=28), periods=28) if a in df.index and not df.disrupt.get(a, False)]
    lost = float((df.pred[e] - df.kor[e]).sum())
    rec = float((df.kor[after] - df.pred[after]).sum())
    rows.append({"start": e[0].date(), "days": len(e), "px_ratio": round(float(df.px_ratio[e].min()), 2), "fp_ratio": round(float(df.fp_ratio[e].min()), 2),
                 "ppf_on_day": round(float(df.dom_arr_person[e].sum() / max(df.dom_arr_fp[e].sum(), 1)), 1),
                 "lost_tourists": round(lost), "recovered_7d": round(rec), "recovery_pct": round(100 * rec / lost) if lost > 0 else np.nan,
                 "pre2d": round(float((df.kor[before] - df.pred[before]).sum())),
                 "dep_surge_2d": round(float(df.dom_dep_person[after[:2]].sum() - df.dep_base[after[:2]].sum())) if after else 0,
                 "load_before": round(float(df.load_idx[pre28].mean()), 3), "month": e[0].month})
t = pd.DataFrame(rows)
t.to_csv(ROOT / "results/disruption_airportal.csv", index=False, encoding="utf-8")

big = t[t.lost_tourists > 3000]
net_lost = float((big.lost_tourists - big.recovered_7d.clip(lower=0)).sum())
lines = ["# 결항 충격 실증 (모형 대비 급감 × airportal 도착 여객 교차 확인)", "",
         f"- 기간 {df.index.min().date()}~{df.index.max().date()}, 결항 사건 {len(t)}건 (입도객 < 예측의 75% 이면서 공항 도착 여객 < 평소의 80%, 5일 이상 연휴 직후 3일 제외)",
         f"- 결항일 도착 편수는 평소의 {t.fp_ratio.median():.0%}(중앙값)로 거의 정상인데 도착 여객은 {t.px_ratio.median():.0%} — 체류객 수송용 빈 비행기(결항일 편당 여객 중앙값 {t.ppf_on_day.median():.0f}명)",
         f"- 입도객 손실 3천 명 이상 {len(big)}건: 7일 회복률 가중 {100 * big.recovered_7d.sum() / big.lost_tourists.sum():.0f}%, 중앙값 {big.recovery_pct.median():.0f}% · 결항 전 2일도 평균 {big.pre2d.mean():+,.0f}명",
         f"- 결항 뒤 2일 제주 출발 여객 평소 대비 평균 {big.dep_surge_2d.mean():+,.0f}명(발 묶인 관광객 귀가)"]
if len(big) >= 6:
    fit = sm.OLS(big.recovery_pct, sm.add_constant(big.load_before)).fit()
    lines.append(f"- 여유 좌석과 회복: 결항 전 28일 탑승 지수 0.01 높을 때 회복률 {fit.params['load_before'] / 100:+.1f}%p (표준오차 {fit.bse['load_before'] / 100:.1f}, n={len(big)}) — 평소 비행기가 찰수록 회복이 적은지")
lines.append(f"- 회복분을 뺀 순손실 관광객 {net_lost:,.0f}명 → 소비 손실 약 {net_lost * SPEND_CARD / 1e8:,.0f}억 원(카드 포착 1인 {SPEND_CARD:,}원) ~ {net_lost * SPEND_SURVEY / 1e8:,.0f}억 원(실태조사 1인 {SPEND_SURVEY:,}원)")
lines += ["", "| 시작 | 일수 | 도착 여객비 | 도착 편수비 | 결항일 편당 여객 | 입도객 손실 | 7일 회복 | 회복률 | 결항 전 2일 | 이후 2일 출발 증가 | 결항 전 탑승지수 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
for x in t.itertuples():
    rc = "" if np.isnan(x.recovery_pct) else f"{x.recovery_pct:.0f}%"
    lines.append(f"| {x.start} | {x.days} | {x.px_ratio} | {x.fp_ratio} | {x.ppf_on_day} | {x.lost_tourists:,} | {x.recovered_7d:+,} | {rc} | {x.pre2d:+,} | {x.dep_surge_2d:+,} | {x.load_before} |")
(ROOT / "results/disruption_airportal.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print("\n".join(lines))
