"""보고서 그림 — 분석 결과를 인쇄용 PNG로 만든다.

    python scripts/make_figures.py
산출: figures/fig1~fig7_*.png (1600×900px, 200dpi)
색: dataviz 기준 팔레트(1번 파랑 #2a78d6, 2번 주황 #eb6834 — 검증 통과), 중립 회색, 이중 축 없음.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from model_d import ROOT

OUT = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, GRAY, GRAY_L = "#2a78d6", "#eb6834", "#8a8984", "#d9d8d4"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
BAND = "#cde2fb"
plt.rcParams.update({
    "font.family": "Malgun Gothic", "axes.unicode_minus": False, "font.size": 10,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "savefig.facecolor": SURF,
})


def finish(fig, ax, title, sub, src, name):
    fig.subplots_adjust(top=0.79, bottom=0.18)  # 제목·부제와 축 제목·출처가 겹치지 않게
    fig.suptitle(title, x=0.06, y=0.965, ha="left", fontsize=14, fontweight="bold", color=INK)
    fig.text(0.06, 0.875, sub, ha="left", fontsize=10, color=INK2)
    fig.text(0.06, 0.025, "출처: " + src, ha="left", fontsize=8, color=INK2)
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("saved", name)


def fig1_tmap():
    # 데이터픽 「제주 전역 내비게이션 운행 건 수 추이」(regSn 46) 월별 도착 수와 「월별 입도 관광객」(regSn 17) 내·외국인 합
    m = pd.read_csv(ROOT / "data/platform/tmap_vs_visitors_monthly.csv", dtype={"month": str}).set_index("month")
    r = (m.tmap_arrivals / m.visitors * 1000).dropna()
    r.index = pd.to_datetime(r.index, format="%Y%m")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.subplots_adjust(left=0.08, right=0.97, top=0.82, bottom=0.12)
    ax.plot(r.index, r.values, color=BLUE, lw=2)
    a, b = r[pd.Timestamp("2025-12-01")], r[pd.Timestamp("2026-01-01")]
    ax.scatter([pd.Timestamp("2025-12-01"), pd.Timestamp("2026-01-01")], [a, b], s=36, color=BLUE, zorder=3, edgecolor=SURF, linewidth=1.5)
    ax.annotate(f"2025.12  {a:,.0f}건", (pd.Timestamp("2025-12-01"), a), xytext=(-95, -22), textcoords="offset points", color=INK, fontsize=9)
    ax.annotate(f"2026.1  {b:,.0f}건 (+{b / a - 1:.0%})", (pd.Timestamp("2026-01-01"), b), xytext=(-150, 10), textcoords="offset points", color=INK, fontsize=9, fontweight="bold")
    ax.set_ylabel("입도객 1천 명당 T맵 도착 건수")
    ax.set_ylim(0, r.max() * 1.15)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    finish(fig, ax, "T맵 차량 도착은 2026년 1월 한 번에 44% 뛰었다",
           "관광객이 아니라 표본이 늘었다 — 2026년의 T맵 '전년 대비'는 수요 지표로 쓸 수 없다",
           "제주관광빅데이터플랫폼 데이터픽 「제주 전역 내비게이션 운행 건 수 추이」·「월별 입도 관광객」", "fig1_tmap_break.png")


def fig2_headlines():
    items = [("오름별 차량 도착\n(1~7월 누적)", 40.2, 5.8), ("곶자왈 도착\n(1~7월 누적)", 33.7, 0.9), ("애월 차량 도착\n(7월)", 33.3, -2.7)]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.subplots_adjust(left=0.2, right=0.95, top=0.8, bottom=0.14)
    y = np.arange(len(items))[::-1]
    h = 0.34
    ax.barh(y + h / 2 + 0.01, [i[1] for i in items], height=h, color=GRAY, label="데이터픽 표기(전년 대비)")
    ax.barh(y - h / 2 - 0.01, [i[2] for i in items], height=h, color=BLUE, label="T맵 표본 확대분을 뺀 값")
    for yi, (_, raw, adj) in zip(y, items):
        ax.text(raw + 0.8, yi + h / 2 + 0.01, f"+{raw:.1f}%", va="center", fontsize=9, color=INK)
        ax.text(max(adj, 0) + 0.8, yi - h / 2 - 0.01, f"{adj:+.1f}%", va="center", fontsize=9, color=INK, fontweight="bold")
    ax.set_yticks(y, [i[0] for i in items])
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlim(-6, 48)
    ax.set_xlabel("전년 대비 변화(%)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    finish(fig, ax, "데이터픽의 '급증'은 표본을 빼면 입도객 증감 수준이다",
           "같은 기간 섬 전체 T맵 +38.9%, 입도객 +4.8% → T맵 커버리지 +32.5%를 나눠 보정",
           "제주관광빅데이터플랫폼 데이터픽(오름별·곶자왈별·지역별 차량 도착, 내비게이션 운행 건수, 월별 입도 관광객), 자체 계산", "fig2_headline_correction.png")


def fig3_empty_planes():
    t = pd.read_csv(ROOT / "results/disruption_airportal.csv").sort_values("start")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.subplots_adjust(left=0.14, right=0.95, top=0.8, bottom=0.14)
    y = np.arange(len(t))[::-1]
    for yi, f, p in zip(y, t.fp_ratio * 100, t.px_ratio * 100):
        ax.plot([p, f], [yi, yi], color=GRAY_L, lw=2, zorder=1)
    ax.scatter(t.fp_ratio * 100, y, s=40, color=ORANGE, zorder=3, edgecolor=SURF, linewidth=1.5, label="도착 편수(평소 대비)")
    ax.scatter(t.px_ratio * 100, y, s=40, color=BLUE, zorder=3, edgecolor=SURF, linewidth=1.5, label="도착 여객(평소 대비)")
    ax.set_yticks(y, [str(s)[:10] for s in t.start], fontsize=8)
    ax.axvline(100, color=INK2, lw=0.8)
    ax.set_xlim(-5, 125)
    ax.set_xlabel("직전 4주 같은 요일 중앙값 대비(%)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=9, ncol=2)
    med_f, med_p = t.fp_ratio.median() * 100, t.px_ratio.median() * 100
    finish(fig, ax, f"결항일에도 비행기는 들어온다 — 편수 {med_f:.0f}%, 여객 {med_p:.0f}%",
           "발 묶인 관광객을 태워 나가려는 빈 비행기(2024.1.23: 173편, 1,799명) → 결항은 편수가 아니라 여객으로 판정",
           "항공정보포털 일자별 공항 통계(제주 국내선 도착), 제주관광빅데이터플랫폼 「입도 관광객 추이(일별)」, 자체 판정 15건", "fig3_empty_planes.png")


def fig4_recovery():
    t = pd.read_csv(ROOT / "results/disruption_airportal.csv")
    t = t[t.lost_tourists > 3000]
    med = t.load_before.median()
    lo = t.load_before <= med
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.subplots_adjust(left=0.1, right=0.95, top=0.8, bottom=0.14)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.axvline(med, color=GRID, lw=1.2)
    ax.scatter(t.load_before[lo], t.recovery_pct[lo], s=48, color=BLUE, edgecolor=SURF, linewidth=1.5, zorder=3,
               label=f"결항 전 여유 있음 (가중 회복 {100 * t[lo].recovered_7d.sum() / t[lo].lost_tourists.sum():.0f}%)")
    ax.scatter(t.load_before[~lo], t.recovery_pct[~lo], s=48, color=ORANGE, edgecolor=SURF, linewidth=1.5, zorder=3, marker="s",
               label=f"결항 전 꽉 참 (가중 회복 {100 * t[~lo].recovered_7d.sum() / t[~lo].lost_tourists.sum():.0f}%)")
    for _, x in t.iterrows():
        if x.start in ("2023-12-21", "2024-01-23", "2026-02-08", "2024-05-05", "2024-11-27"):
            ax.annotate(x.start[:7].replace("-", "."), (x.load_before, x.recovery_pct), xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK2)
    ax.set_xlabel("결항 전 28일 평균 탑승 지수(편당 여객 ÷ 계절 최대치)")
    ax.set_ylabel("7일 안에 돌아온 관광객(%)")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    finish(fig, ax, "비행기에 여유가 있을 때만 결항 수요가 돌아온다",
           "결항 15건, 순위상관 -0.89 · 성수기엔 좌석과 일정 여유가 함께 부족해 두 요인을 분리하지 못함",
           "항공정보포털 일자별 공항 통계, 제주관광빅데이터플랫폼 「입도 관광객 추이(일별)」, 자체 예측 모형", "fig4_recovery_vs_load.png")


def fig5_price_vs_seats():
    r = pd.read_csv(ROOT / "data/external/airportal_cju_routes_monthly.csv")
    g = r.groupby("month")[["arr_fp", "arr_person"]].sum()
    g.index = pd.PeriodIndex(g.index, freq="M")
    fs = pd.read_csv(ROOT / "data/external/fuel_surcharge_domestic.csv")
    fs.index = pd.PeriodIndex(fs.month, freq="M")
    d = pd.DataFrame({"fp": g.arr_fp, "px": g.arr_person, "fuel": fs.krw.reindex(g.index)})
    d["ppf"] = d.px / d.fp
    d["ppf_yoy"] = (d.ppf / d.ppf.shift(12) - 1) * 100
    d["fp_yoy"] = (d.fp / d.fp.shift(12) - 1) * 100
    d = d.loc["2025-01":"2026-08"]
    cls = np.where((d.ppf_yoy > 1) & (d.fp_yoy < 0), "seat", np.where(d.ppf_yoy < -1, "demand", "mixed"))
    x = np.arange(len(d))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 4.5), sharex=True, gridspec_kw={"height_ratios": [1, 1.6], "hspace": 0.12})
    fig.subplots_adjust(left=0.1, right=0.97, top=0.8, bottom=0.14)
    a1.step(x, d.fuel / 1000, where="mid", color=INK2, lw=2)
    a1.set_ylabel("할증료(천 원)")
    a1.set_ylim(0, 40)
    a1.text(x[list(d.index.astype(str)).index("2026-06")], 36.5, "35,200원", ha="center", fontsize=8, color=INK)
    colors = {"seat": BLUE, "demand": ORANGE, "mixed": GRAY_L}
    a2.bar(x, d.ppf_yoy, color=[colors[c] for c in cls], width=0.72)
    a2.axhline(0, color=INK2, lw=0.8)
    a2.set_ylabel("편당 여객 전년 대비(%)")
    a2.set_xticks(x, [f"{p.year % 100}.{p.month}" for p in d.index], fontsize=8)
    from matplotlib.patches import Patch
    a2.legend(handles=[Patch(color=BLUE, label="좌석 제약(더 꽉 참, 편수 감소)"), Patch(color=ORANGE, label="수요 감소(비어감)"), Patch(color=GRAY_L, label="혼합")],
              loc="upper left", frameon=False, fontsize=8, ncol=3)
    a2.set_ylim(-9, 14)
    finish(fig, a2, "싸면 좌석이, 비싸면 가격이 막는다",
           "위: 국내선 유류할증료(발권월, 편도) · 아래: 제주행 국내선 편당 여객 전년 대비와 월별 판정",
           "항공정보포털 제주 노선×항공사 월간 실적, 항공여행(airtravelinfo.kr) 월간 유류할증료 글", "fig6_price_vs_seats.png")


def fig6_route_iv():
    d = pd.read_csv(ROOT / "results/origin_supply_panel.csv")
    m1 = smf.ols("dv ~ df + C(month)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.region})
    m2 = smf.ols("dv ~ df + C(month) + C(region)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.region})
    iv1 = smf.ols("df ~ d_asiana + C(month)", data=d).fit()
    d["df_hat"] = iv1.fittedvalues
    m3 = smf.ols("dv ~ df_hat + C(month)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.region})
    rows = [("단순 비교\n(월 고정효과)", m1.params["df"], m1.bse["df"], GRAY), ("권역 고정효과 추가", m2.params["df"], m2.bse["df"], GRAY),
            ("수요와 무관한 감편만\n(아시아나 계열, 도구변수)", m3.params["df_hat"], m3.bse["df_hat"], BLUE)]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.subplots_adjust(left=0.27, right=0.95, top=0.8, bottom=0.14)
    y = np.arange(len(rows))[::-1]
    for yi, (lab, b, se, c) in zip(y, rows):
        ax.plot([b - 1.96 * se, b + 1.96 * se], [yi, yi], color=c, lw=2)
        ax.scatter([b], [yi], s=48, color=c, zorder=3, edgecolor=SURF, linewidth=1.5)
        ax.text(b + 1.96 * se + 0.02, yi, f"{b:+.2f}", va="center", fontsize=9, color=INK, fontweight="bold" if c == BLUE else "normal")
    ax.set_yticks(y, [r[0] for r in rows])
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlabel("제주행 편수 1% 변화당 방문객 변화(%) · 막대는 95% 신뢰구간")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(-0.3, 0.55)
    finish(fig, ax, "평시엔 좌석이 병목이 아니다 — 수요와 무관한 감편의 효과는 0",
           "출발 권역 8곳 × 19개월 패널: 편수와 방문객이 같이 움직인 건 '수요가 줄어 편수를 줄인' 역방향이 주였다",
           "제주관광빅데이터플랫폼 「제주 방문 관광객 거주지 분포(시도)」, 항공정보포털 제주 노선×항공사 월간 실적", "fig5_route_iv.png")


def fig7_forecast():
    doc = json.load(open(ROOT / "sealed/draft_2026-09-24.json", encoding="utf-8"))
    f = pd.DataFrame(doc["forecast"])
    f["date"] = pd.to_datetime(f["date"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.subplots_adjust(left=0.1, right=0.97, top=0.8, bottom=0.14)
    w = pd.to_datetime(doc["sets"]["W_sports"])
    ax.axvspan(w.min() - pd.Timedelta(hours=12), w.max() + pd.Timedelta(hours=12), color=GRID, alpha=0.6, lw=0)
    ax.text(w.min(), 44500, "전국체전 입도 창(10/13~21)", fontsize=8, color=INK2)
    ax.fill_between(f.date, f.PI80_lo, f.PI80_hi, color=BAND, lw=0, label="80% 예측구간")
    ax.plot(f.date, f.D, color=BLUE, lw=2, label="사전 예측(9/25 작성)")
    act = pd.read_csv(ROOT / "data/platform/daily_arrivals.csv", dtype={"date": str})
    act.index = pd.to_datetime(act.date)
    a = act.kor.reindex(f.date).dropna()
    if len(a):
        ax.scatter(a.index, a.values, s=22, color=ORANGE, zorder=3, label="실측")
    ax.set_ylim(20000, 46000)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1e4:.1f}만"))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{mdates.num2date(v).month}/{mdates.num2date(v).day}"))
    ax.set_ylabel("내국인 입도객(일)")
    ax.legend(loc="lower left", frameon=False, fontsize=9, ncol=3)
    fi = f.set_index("date")
    mape = (abs(a - fi.D.reindex(a.index)) / a).mean() * 100 if len(a) else 0
    cov = ((a >= fi.PI80_lo.reindex(a.index)) & (a <= fi.PI80_hi.reindex(a.index))).mean() * 100 if len(a) else 0
    end = a.index.max() if len(a) else None
    finish(fig, ax, "9월 25일에 미리 낸 10월 예측은 실측과 일별 7% 안팎으로 맞았다" if len(a) else "10월 일별 입도객을 미리 예측해 두고 실측으로 채점한다",
           f"10/1~{end.month}/{end.day} 일별 오차 {mape:.1f}%(백테스트 8.5%) · 80% 구간 적중 {cov:.0f}% · 전국체전 기간엔 예측보다 더 왔다"
           if len(a) else f"월 합계 예측 {f.D.sum():,.0f}명 · 백테스트(31개월) 일별 오차 8.5%",
           "제주관광빅데이터플랫폼 「입도 관광객 추이(일별)」 2018~2026, 자체 예측 모형", "fig7_october_forecast.png")


if __name__ == "__main__":
    for fn in (fig1_tmap, fig2_headlines, fig3_empty_planes, fig4_recovery, fig6_route_iv, fig5_price_vs_seats, fig7_forecast):
        fn()
