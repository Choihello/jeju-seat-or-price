"""사전등록 봉인 — 10월 예측·가설·채점 규칙을 하나의 JSON으로 고정하고 SHA-256을 남긴다.

    python scripts/seal.py 2026-09-28     # 최종 봉인(9/29 아침, 9/28 값까지 반영한 데이터로)
    python scripts/seal.py                # 초안(지금 데이터 끝까지) — sealed/draft_*.json 으로만 저장
    python scripts/seal.py --draft 2026-09-24   # 기준일을 정한 초안
산출: sealed/sealed_<cutoff>.json · .md · .sha256
10월 예측은 9/25 작성본(sealed/draft_2026-09-24.*, git 커밋)을 쓴다. 외부 공증은 하지 않는다(사용자 결정 9/25).
"""
import datetime as dt
import hashlib
import json
import sys

import pandas as pd

from forecast import TARGET, W, build
from model_d import ROOT

KST = dt.timezone(dt.timedelta(hours=9))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(cutoff=None, final=None, test=False):
    df, meta = build(cutoff)
    final = (cutoff is not None) if final is None else final
    bt = pd.read_csv(ROOT / "results/backtest_daily.csv")
    rec = pd.read_csv(ROOT / "results/disruption_recovery.csv") if (ROOT / "results/disruption_recovery.csv").exists() else None
    doc = {
        "title": "제주 내국인 입도객 10월 사전등록 — 좌석이 가린 수요(잘린 수요) 검증",
        "sealed_at_kst": dt.datetime.now(KST).isoformat(timespec="seconds"),
        "status": "final" if final else "draft",
        "data": {
            "target": "제주관광빅데이터플랫폼 데이터픽 「입도 관광객 추이(일별)」(regSn=18) 내국인방문객수, 출처 제주관광협회 잠정치",
            "train_file": "data/platform/daily_arrivals.csv", "train_sha256": sha(ROOT / "data/platform/daily_arrivals.csv"),
            "cutoff": meta["cutoff"],
            "scoring_value": "2026-10-31 이후 플랫폼 CSV로 내려받은 값(서면 제출본은 10/30까지 30일, 발표본은 31일)",
        },
        "code_sha256": {p.name: sha(p) for p in sorted((ROOT / "scripts").glob("*.py"))},
        "model": {"name": "Model D", "spec": "log y = 요일 + 연휴 블록 위치 + 설·추석 전후 + 연중 푸리에 3차 + 여름 요일 + 연월 수준, 1차 잔차 ±0.25 초과일 제외 후 재적합(릿지 0.01)",
                  "level": {"L1": meta["L1"], "L2": meta["L2"], "used": meta["level"]},
                  "interval": "백테스트(2024-03~2026-09, 롤링) 로그오차 분위수", "log_err_q": meta["log_err_q"],
                  "baseline_B1": "364일 전 같은 요일 x 최근 28일 전년 대비 비율"},
        "forecast": [{k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()} for r in
                     df.assign(date=df["date"].astype(str)).to_dict("records")],
        "sets": {"C_peak": list(df.index[df.C_peak].strftime("%Y-%m-%d")),
                 "W_sports": list(W.strftime("%Y-%m-%d")),
                 "N_normal": list(df.index[df.N_normal].strftime("%Y-%m-%d"))},
        "disruption_rule": {
            "primary": "airportal 일자별 실적에서 그날 제주 도착 국내선 운항편수가 직전 4주 같은 요일 중앙값의 80% 미만이면 결항일. 결항일과 다음 날은 M1·H1·H2 채점에서 빼고 따로 보고",
            "provisional": "airportal 확정 전(D+7)에는 실측이 수준 보정 예측의 75% 미만인 날과 다음 날로 임시 판정",
        },
        "metrics": {
            "M1": "결항일 제외 일별 MAPE: Model D < B1 이면 '예측 우위' (백테스트에서 D가 이긴 달 18/31 — 한 달 결과는 참고치)",
            "M2": "PI80 적중률(목표 80%, 30일 기준 65~95%면 보정 양호), PI95 적중률",
            "M3": "10월 합계 오차율 |Σ예측-Σ실측|/Σ실측",
        },
        "hypotheses": {
            "H1_holiday_ceiling": {
                "claim": "좌석 공급이 줄어든 2026년에는 연휴 첫날·전날 같은 피크일에 입도객이 예측보다 더 눌린다(천장)",
                "stat": "Δ1 = mean log(실측/예측)[C] - mean log(실측/예측)[N]  (같은 달 안의 상대 비교라 월 수준 오차가 상쇄됨)",
                "decision": "Δ1 ≤ -0.05 → 천장 지지 / Δ1 ≥ 0.00 → 기각 / 사이 → 보류",
                "placebo": "행사 없는 18개월(2025-03~2026-08) 같은 규칙: Δ1 평균 +0.027, 표준편차 0.067, ≤-0.05 오탐 11%, ≥0.00 61% — 한 달 판정의 검정력이 낮음을 밝힌다",
                "prior_retro": "2026년 1~9월 사후 점검에서는 예측 상위 10%일 잔차 차이 +0.009(표준오차 0.022) — 사전 근거는 약함을 밝힌다",
            },
            "H2_sports_crowdout": {
                "claim": "전국체전(10/16~22, 참가 약 2만9천 명) 기간 입도객 증가는 도외 참가자 수보다 훨씬 작다 — 좌석 천장 또는 일반 관광객 구축",
                "stat": "Δ2 = mean log(실측/예측)[W] - mean log(실측/예측)[N]; 보조로 초과 입도 E = Σ_W(실측 - 예측·exp(N 평균 잔차))",
                "expected_if_free": "도외 참가자 약 2.6만~2.8만 명의 80%가 W 안에 항공으로 입도하면 Δ2 ≈ +0.06~+0.07, E ≈ 2.1만~2.2만",
                "decision": "증거 강도로 판정: Δ2 ≥ +0.05 → '여유' 쪽 우도비 약 5.5 / Δ2 ≤ +0.02 → '구축·천장' 쪽 우도비 약 3.4 / 사이 → 보류. 결론은 보조 근거(편당 여객)와 함께 낸다",
                "placebo": "행사 없는 18개월 가짜 창(13~21일 중 연휴 아닌 날): Δ2 평균 -0.009, 표준편차 0.052, ≥+0.05 11%, ≤+0.02 67%. 우도비는 '여유' 가정 Δ2~N(+0.065, 0.052)과 '구축' 가정 = 위약 분포로 계산",
                "auxiliary": "airportal 노선별 일자 실적의 편당 여객이 W 입도 피크일(10/14~10/16)에 2025~2026년 10월 분포 상위 5% 이상이면 좌석 천장 쪽 근거로 본다",
            },
            "H3_disruption_loss": {
                "claim": "기상 결항으로 못 들어온 내국인 관광객은 이후 7일 안에 거의 돌아오지 않는다",
                "retro": ("2023-01~2026-09 결항 의심 18건: 7일 회복률 가중 3%, 위약(무작위 날) 7일 초과합 평균 +1.1천(표준편차 10.6천)" if rec is not None else ""),
                "prospective": "10/1~11/15에 결항일(airportal 기준)이 생기면 7일 회복률 < 30% 예측. 결항이 없으면 판정 없음",
            },
        },
        "retro_backtest": {
            "months": "2024-03~2026-09", "days": int(len(bt)),
            "MAPE_D": round(float(bt.ape_D.mean()), 2), "MAPE_B1": round(float(bt.ape_B1.mean()), 2),
            "MAPE_D_no_disrupt": round(float(bt.ape_D[~bt.disrupt].mean()), 2), "MAPE_B1_no_disrupt": round(float(bt.ape_B1[~bt.disrupt].mean()), 2),
        },
    }
    prefix = "test" if test else ("sealed" if final else "draft")
    name = f"{prefix}_{meta['cutoff']}"
    js = ROOT / f"sealed/{name}.json"
    if (js.parent / f"{js.name}.ots").exists():
        raise SystemExit(f"{js.name}은 이미 공증됨 — 덮어쓰면 증명이 깨지므로 중단")
    if final and dt.datetime.now(KST) >= dt.datetime(2026, 10, 1, tzinfo=KST):
        raise SystemExit("10/1 0시(KST)가 지나 10월 사전등록으로 인정되지 않으므로 최종 봉인하지 않음")
    # 봉인 파일은 운영체제와 무관하게 LF 바이트로 쓴다(해시 재현)
    js.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    h = sha(js)
    (ROOT / f"sealed/{name}.sha256").write_text(f"{h}  {js.name}\n", encoding="utf-8", newline="\n")
    lines = [f"# {doc['title']}", "", f"SHA-256(`{js.name}`): `{h}`", "",
             f"- 상태: {doc['status']} · 봉인 시각 {doc['sealed_at_kst']} · 데이터 기준일 {meta['cutoff']}",
             f"- 목표: {doc['data']['target']}", f"- 월 수준: L1 {meta['L1']:.3f} · L2 {meta['L2']:.3f} → {meta['level']:.3f}",
             f"- 10월 합계 예측 {df.D.sum():,.0f}명 (B1 {df.B1.sum():,.0f}명)",
             f"- C(피크 후보) {', '.join(doc['sets']['C_peak'])} · W(전국체전) 10/13~10/21 · N(평상일) {len(doc['sets']['N_normal'])}일", "",
             "| 날짜 | 요일 | 예측 | 80% 구간 | 95% 구간 | B1 | 묶음 |", "|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        tag = "C" if r.C_peak else ("W" if r.W_sports else ("N" if r.N_normal else ""))
        lines.append(f"| {r.date} | {r.dow} | {r.D:,.0f} | {r.PI80_lo:,.0f}~{r.PI80_hi:,.0f} | {r.PI95_lo:,.0f}~{r.PI95_hi:,.0f} | {r.B1:,.0f} | {tag} |")
    lines += ["", "## 가설과 판정 규칙(사전 등록)"]
    for k, v in doc["hypotheses"].items():
        lines.append(f"- **{k}**: {v['claim']}")
        for kk in ("stat", "decision", "placebo", "expected_if_free", "auxiliary", "prior_retro", "retro", "prospective"):
            if v.get(kk):
                lines.append(f"  - {kk}: {v[kk]}")
    lines += ["", "## 채점 지표", *[f"- {k}: {v}" for k, v in doc["metrics"].items()],
              "", "## 결항일 규칙", *[f"- {k}: {v}" for k, v in doc["disruption_rule"].items()]]
    (ROOT / f"sealed/{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{js.name} sha256 {h}")
    return js


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else None, final=False if ("--draft" in sys.argv or "--test" in sys.argv) else None,
         test="--test" in sys.argv)
