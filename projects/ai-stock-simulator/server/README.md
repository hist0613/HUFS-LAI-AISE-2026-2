# 서버

거래 화면(`ui/`)이 쓰는 시세·차트·호가·계좌 데이터를 HTTP API로 제공하는 Express 서버다.
뉴스 가격 계산과 검증은 `market/engine.mjs`를 그대로 쓰고, 턴·차트·호가는 `server/market.mjs`가 처리한다.
게임 상태는 메모리에만 보관하므로 서버를 다시 켜면 초기화된다.

## 실행

```sh
cd projects/ai-stock-simulator/server
npm install
npm start                       # http://localhost:3000
SEED=2026 npm start             # 매번 같은 시장으로 시작 (시연용)
TURN_INTERVAL_MS=5000 npm start # 5초마다 자동으로 턴 진행
npm test
```

`ui/` 폴더가 있으면 같은 주소(`http://localhost:3000/`)에서 거래 화면도 열린다.

## 게임 규칙 (임시, 회의에서 조정)

| 항목 | 현재 규칙 | 바꿀 곳 |
| --- | --- | --- |
| 시간 | 턴 단위. 시작 시 8턴 기록을 만들어 둔다 | `HISTORY_TURNS` |
| 턴 변동 | 평균 0, 표준편차 1.2%, 최대 ±8% | `VOLATILITY`, `MAX_DRIFT` |
| 가격 | 모든 가격을 한국거래소 호가 단위로 맞춘다 | `ticks.mjs` |
| 뉴스 | 엔진으로 계산한 뒤 호가 단위로 맞춰 현재 턴 종가에 바로 반영 | `applyNews` |
| 거래량·호가 잔량 | 종목별 기준 거래량으로 무작위 생성 (실제 주문장 아님) | `BASE_VOLUME`, `#makeBook` |
| 매매·수수료·세금·배당 | 아직 없음 (보유 수량은 0) | — |

## API

| 요청 | 주소 | 본문 | 응답 |
| --- | --- | --- | --- |
| GET | `/api/health` | | `{ ok: true }` |
| GET | `/api/game` | | 게임 상태 |
| POST | `/api/game/reset` | `{ seed? }` | `{ game }` |
| POST | `/api/turns` | `{ count? }` (1~100, 기본 1) | `{ game }` |
| GET | `/api/news` | | 뉴스 목록 (최신이 앞) |
| POST | `/api/events` | `{ headline, stockId, changePercent }` | `201 { news, game }` |

- 잘못된 요청은 `400`, 없는 주소는 `404`, 응답 본문은 `{ "error": "..." }`이다. 실패한 요청은 상태를 바꾸지 않는다.

### 게임 상태 (`GET /api/game`)

```js
{
  seed, turn,                 // 현재 턴 번호 (화면 상단 "현재 n턴")
  initialCash,                // 1,000,000 (수익률 기준)
  cash,                       // 보유 현금
  equity, profit,             // 총자산, 총 손익
  stocks: [{
    id, name, price, previousClose,
    holding, averagePrice,
    candles: [{ turn, open, high, low, close, volume }],  // 오래된 턴부터, 최대 200개
    book: { asks: [5개], bids: [5개] },                    // 현재가에서 가까운 호가부터의 잔량
  }],
  news:   [{ id, turn, headline, stockId, changePercent, priceBefore, priceAfter }],       // 최신이 앞, 최대 50개
}
```

화면 예제 데이터(`ui/app.mjs`의 `sample`)와 대응: `stocks[].candles`, `holding`, `averagePrice`, `book`, `initialCash`, `cash`는 같은 이름이다.
