# 좌석이냐 가격이냐

제주관광빅데이터플랫폼 데이터와 항공 통계로 2026년 제주 내국인 관광객 감소의 원인을 좌석과 가격으로 가른 연구의 코드와 데이터입니다. 2026 제주 관광 데이터 활용사례 공모전 응모작의 재현 자료입니다.

결과보고서: [docs/report.md](docs/report.md)

## 주요 결과

- **평시에는 좌석이 병목이 아니다.** 대한항공·아시아나 통합 과정의 아시아나 계열 감편을 도구변수로 쓰면 편수가 방문객에 주는 효과는 0이다(계수 -0.03, 표준오차 0.04).
- **2026년 5~8월 감소는 가격 쪽이다.** 유류할증료가 오른 5월부터 제주행 편당 여객이 줄었다. 할증료가 전년보다 1만 원 높으면 여객은 1.5% 줄었다(16개월, 참고치).
- **좌석이 막는 건 쌀 때와 결항 때다.** 2023~2026년 결항 15건에서 못 들어온 관광객은 7일 안에 11%만 돌아왔다. 순손실은 관광객 약 22.7만 명, 소비 425억~1,448억 원이다.
- **플랫폼 지표에 착시가 있다.** T맵 차량 도착 표본이 2026년 1월에 44% 커져 2026년 '전년 대비' 값이 부풀려졌다.
- **사전 예측 검증.** 9월 25일에 낸 10월 일별 입도객 예측(`sealed/`)을 실측으로 채점했다. 10/1~27 일별 오차 7.1%(백테스트 8.5%), 연휴 좌석 천장 없음, 전국체전 기간에는 관광객이 밀려나지 않고 예측보다 1.2만~2.2만 명 더 들어왔다.

## 폴더

| 경로 | 내용 |
|---|---|
| `scripts/` | 예측 모형(`model_d.py`, `calendar_kr.py`), 백테스트·위약 검사, 자연실험 3개, 채점, 그림, 데이터 수집 |
| `data/platform/` | 제주관광빅데이터플랫폼 데이터픽: 일별 입도객(2018~), 시도별 방문객(2025.1~), T맵 도착과 입도객(월) |
| `data/external/` | 항공정보포털 제주 일별·노선 월간 실적, 국내선 유류할증료(출처 포함) |
| `sealed/` | 2026-09-25에 작성한 10월 예측과 판정 규칙. 이후 수정하지 않음(SHA-256 함께) |
| `results/` | 백테스트, 위약 검사, 결항 판정, 노선 패널, 가격 대 좌석, 10월 채점 결과 |
| `figures/` | 보고서 그림 1~7 |
| `docs/report.md` | 결과보고서 |

## 재현

Python 3.12 이상, `pandas`, `numpy`, `statsmodels`, `matplotlib`.

```bash
python scripts/backtest.py          # 31개월 롤링 백테스트 → results/backtest_*
python scripts/placebo.py           # 판정 기준 위약 보정 → results/placebo.md
python scripts/disruption_airportal.py   # 결항 15건 판정·회복·손실 → results/disruption_airportal.*
python scripts/origin_supply.py     # 출발 권역 × 노선 패널·도구변수 → results/origin_supply.*
python scripts/price_vs_seats.py    # 편당 여객 판정·할증료 회귀 → results/price_vs_seats.md
python scripts/score.py sealed/draft_2026-09-24.json   # 10월 예측 채점 → results/score_*.md
python scripts/make_figures.py      # 그림 1~7 → figures/
```

데이터 갱신:
- `fetch_airportal.py <시작일> <종료일>`, `fetch_airportal_routes.py`: 항공정보포털 공개 통계(요청 간격 1.2초 이상).
- `refresh_data.py`, `fetch_platform_origin.py`: 데이터픽 공개 차트를 브라우저 세션으로 1회 조회한다(Aside 브라우저 CLI 사용). 플랫폼 실시간 API는 수집하지 않는다.

## 데이터 출처

- 제주관광공사 제주관광빅데이터플랫폼(data.ijto.or.kr) 데이터픽
- 항공정보포털(airportal.go.kr, 국토교통부·한국항공협회) 항공 통계
- 국내선 유류할증료: 항공사 공지를 정리한 월별 값(`data/external/fuel_surcharge_domestic.csv`의 source 열)

코드는 MIT 라이선스입니다. 데이터의 권리는 각 출처에 있습니다.
