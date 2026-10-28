"""사전등록 채점 — 봉인 JSON과 최신 플랫폼 일별 입도객으로 M1~M3, H1, H2를 계산한다.

    python scripts/score.py sealed/sealed_2026-09-28.json [data/platform/daily_arrivals.csv]
airportal 결항 판정 파일(data/external/airportal_cju_daily.csv: date,dom_arr_fp)이 있으면 그 규칙을,
없으면 임시 규칙(실측 < 수준 보정 예측의 75%)을 쓴다. 결과: results/score_<봉인이름>.md
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def disruption_flags(dates, act, pred_adj):
    ext = ROOT / "data/external/airportal_cju_daily.csv"
    if ext.exists():
        a = pd.read_csv(ext, parse_dates=["date"]).set_index("date").dom_arr_fp.sort_index()
        flag = pd.Series(False, index=dates)
        for d in dates:
            prev = [d - pd.Timedelta(days=7 * k) for k in range(1, 5)]
            base = a.reindex(prev).median()
            if d in a.index and base and a[d] < 0.8 * base:
                flag[d] = True
        rule = "airportal"
    else:
        flag = pd.Series(act.values < 0.75 * pred_adj.values, index=dates)
        rule = "provisional"
    return flag | flag.shift(1, fill_value=False), rule


def main(sealed_path, data_path=None):
    doc = json.loads(Path(sealed_path).read_text(encoding="utf-8"))
    fc = pd.DataFrame(doc["forecast"])
    fc.index = pd.to_datetime(fc["date"])
    d = pd.read_csv(data_path or ROOT / "data/platform/daily_arrivals.csv", dtype={"date": str})
    d.index = pd.to_datetime(d["date"])
    act = d["kor"].astype(float).reindex(fc.index).dropna()
    act = act[act.index <= pd.Timestamp("2026-10-30")] if len(act) and act.index.max() < pd.Timestamp("2026-11-01") else act
    fc = fc.loc[act.index]
    lr = np.log(act / fc.D)
    S = {k: pd.to_datetime(v) for k, v in doc["sets"].items()}
    N = [t for t in S["N_normal"] if t in act.index]
    level_adj = float(lr[N].mean()) if N else 0.0
    dis, rule = disruption_flags(act.index, act, fc.D * np.exp(level_adj))
    ok = ~dis

    def mean_lr(ix):
        ix = [t for t in ix if t in act.index and ok[t]]
        return (float(lr[ix].mean()), float(lr[ix].std(ddof=1) / np.sqrt(len(ix))) if len(ix) > 1 else np.nan, len(ix)) if ix else (np.nan, np.nan, 0)

    mN, sN, nN = mean_lr(S["N_normal"])
    mC, sC, nC = mean_lr(S["C_peak"])
    mW, sW, nW = mean_lr(S["W_sports"])
    d1, d2 = mC - mN, mW - mN
    se1, se2 = np.sqrt(sC ** 2 + sN ** 2), np.sqrt(sW ** 2 + sN ** 2)
    h1 = "천장 지지" if d1 <= -0.05 else ("기각" if d1 >= 0.0 else "보류")
    h2 = "여유 쪽(우도비 약 5.5)" if d2 >= 0.05 else ("구축·천장 쪽(우도비 약 3.4)" if d2 <= 0.02 else "보류")
    Wd = [t for t in S["W_sports"] if t in act.index and ok[t]]
    E = float((act[Wd] - fc.D[Wd] * np.exp(mN)).sum()) if Wd else np.nan
    ape_d = (fc.D[ok] / act[ok] - 1).abs() * 100
    ape_b = (fc.B1[ok] / act[ok] - 1).abs() * 100
    cov80 = ((act >= fc.PI80_lo) & (act <= fc.PI80_hi)).mean()
    cov95 = ((act >= fc.PI95_lo) & (act <= fc.PI95_hi)).mean()
    m3 = (fc.D.sum() / act.sum() - 1) * 100
    lines = [f"# 채점 — {Path(sealed_path).name}", "",
             f"- 채점일 수 {len(act)}일({act.index.min().date()}~{act.index.max().date()}), 결항 판정 규칙 {rule}, 제외 {int(dis.sum())}일",
             f"- M1 일별 MAPE(결항 제외): Model D {ape_d.mean():.1f}% · B1 {ape_b.mean():.1f}% → {'예측 우위' if ape_d.mean() < ape_b.mean() else '우위 없음'}",
             f"- M2 구간 적중률: 80% 구간 {cov80:.0%} · 95% 구간 {cov95:.0%}",
             f"- M3 합계 오차율: {m3:+.1f}% (예측 {fc.D.sum():,.0f} / 실측 {act.sum():,.0f})",
             f"- 평상일 N 평균 잔차 {mN:+.3f} (n={nN}) — 월 수준 오차",
             f"- **H1** Δ1 = {d1:+.3f} (표준오차 {se1:.3f}, C n={nC}) → {h1}",
             f"- **H2** Δ2 = {d2:+.3f} (표준오차 {se2:.3f}, W n={nW}) → {h2} · 초과 입도 E = {E:+,.0f}명",
             "", "| 날짜 | 실측 | 예측 | log(실측/예측) | 묶음 | 결항 |", "|---|---|---|---|---|---|"]
    for t in act.index:
        tag = "C" if t in S["C_peak"] else ("W" if t in S["W_sports"] else ("N" if t in S["N_normal"] else ""))
        lines.append(f"| {t.date()} | {act[t]:,.0f} | {fc.D[t]:,.0f} | {lr[t]:+.3f} | {tag} | {'x' if dis[t] else ''} |")
    out = ROOT / f"results/score_{Path(sealed_path).stem}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))


if __name__ == "__main__":
    main(*sys.argv[1:])
