"""출발 지역 × 노선 공급 — 같은 달 안에서 제주 노선 편수가 더 줄어든 권역일수록 관광객이 더 줄었나.

    python scripts/origin_supply.py
입력: data/platform/origin_sido_monthly.csv(플랫폼 통신 거주지), data/external/airportal_cju_routes_monthly.csv
모형: Δlog 방문객(전년 동월) = 월 고정효과 + β·Δlog 제주행 편수(권역 공항, 전년 동월) + 오차 (권역 8개 × 19개월)
결과: results/origin_supply.md
"""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from model_d import ROOT

REGION = {  # 권역: (시도 목록, 공항 목록)
    "수도권": (["서울특별시", "경기도", "인천광역시"], ["김포", "인천"]),
    "부산·경남": (["부산광역시", "경상남도"], ["김해", "사천"]),
    "울산": (["울산광역시"], ["울산"]),
    "대구·경북": (["대구광역시", "경상북도"], ["대구", "포항경주"]),
    "광주·전남": (["광주광역시", "전라남도", "전남광주통합특별시"], ["광주", "무안", "여수"]),
    "충청": (["대전광역시", "세종특별자치시", "충청북도", "충청남도"], ["청주"]),
    "전북": (["전북특별자치도"], ["군산"]),
    "강원": (["강원특별자치도"], ["원주", "양양"]),
}

o = pd.read_csv(ROOT / "data/platform/origin_sido_monthly.csv")
r = pd.read_csv(ROOT / "data/external/airportal_cju_routes_monthly.csv")
r["ap"] = r.origin.str.extract(r"^(\S+)")[0]
rows = []
for reg, (sidos, aps) in REGION.items():
    ov = o[o.sido.isin(sidos)].groupby("month").visitors.sum()
    fp = r[r.ap.isin(aps)].groupby("month").arr_fp.sum()
    px = r[r.ap.isin(aps)].groupby("month").arr_person.sum()
    asg = r[r.ap.isin(aps) & r.airline.isin(["AAR", "ABL", "ASV"])].groupby("month").arr_fp.sum()  # 아시아나 계열
    for m in ov.index:
        ly = (pd.Period(m, "M") - 12).strftime("%Y-%m")
        vly = o[o.sido.isin(sidos) & (o.month == m)].visitors_ly.sum()
        if vly <= 0 or ly not in fp.index or m not in fp.index:
            continue
        rows.append({"region": reg, "month": m, "dv": np.log(ov[m] / vly), "df": np.log(fp[m] / fp[ly]),
                     "dp": np.log(px[m] / px[ly]), "d_asiana": (asg.get(m, 0) - asg.get(ly, 0)) / fp[ly],
                     "visitors": ov[m], "flights": fp[m]})
d = pd.DataFrame(rows)
m1 = smf.ols("dv ~ df + C(month)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.region})
m2 = smf.ols("dv ~ df + C(month) + C(region)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.region})
iv1 = smf.ols("df ~ d_asiana + C(month)", data=d).fit()
d["df_hat"] = iv1.fittedvalues
m3 = smf.ols("dv ~ df_hat + C(month)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.region})
lines = ["# 출발 권역 × 제주 노선 공급 (2025-01~2026-07, 권역 8개)", "",
         f"- 관측 {len(d)}개(권역×월). 종속변수 = 플랫폼 통신 방문객의 전년 동월 대비 로그 변화",
         f"- **월 고정효과**: β = {m1.params['df']:+.3f} (권역 군집 표준오차 {m1.bse['df']:.3f}, p={m1.pvalues['df']:.3f}) — 제주행 편수 1% 감소당 방문객 {m1.params['df']:.2f}% 감소",
         f"- 월 + 권역 고정효과: β = {m2.params['df']:+.3f} (표준오차 {m2.bse['df']:.3f}, p={m2.pvalues['df']:.3f})",
         f"- 아시아나 계열 편수 변화를 도구로 쓴 2단계: 1단계 계수 {iv1.params['d_asiana']:+.3f} (F≈{(iv1.tvalues['d_asiana'])**2:.1f}), 2단계 β = {m3.params['df_hat']:+.3f} (표준오차 {m3.bse['df_hat']:.3f}, 1단계 불확실성 미반영 — 참고치)",
         "", "## 2026-07 권역별", "", "| 권역 | 방문객 전년비 | 제주행 편수 전년비 | 제주행 여객 전년비 |", "|---|---|---|---|"]
for x in d[d.month == "2026-07"].itertuples():
    lines.append(f"| {x.region} | {np.expm1(x.dv) * 100:+.1f}% | {np.expm1(x.df) * 100:+.1f}% | {np.expm1(x.dp) * 100:+.1f}% |")
(ROOT / "results/origin_supply.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
d.to_csv(ROOT / "results/origin_supply_panel.csv", index=False, encoding="utf-8")
print("\n".join(lines))
