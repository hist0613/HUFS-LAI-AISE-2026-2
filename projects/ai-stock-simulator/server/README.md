# 서버

거래 화면(`ui/`)이 쓰는 데이터를 모두 HTTP API로 제공하는 Express 서버다.
뉴스 가격 계산과 검증은 `market/engine.mjs`를 그대로 쓰고, 턴·차트·주문·호가는 `server/market.mjs`가 처리한다.
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
| 시장가 | 현재가로 즉시 체결 | `placeOrder` |
| 지정가 | 현재가로 바로 살·팔 수 있으면 현재가로 즉시 체결. 아니면 대기하고 가격이 닿으면 주문 가격으로 체결 | `placeOrder`, `#matchOrders` |
| 대기 주문 | 매수는 현금, 매도는 수량을 묶어 둔다 | `availableCash`, `availableQuantity` |
| 거래량·호가 잔량 | 종목별 기준 거래량으로 무작위 생성 (실제 주문장 아님) | `BASE_VOLUME`, `#makeBook` |
| 수수료·세금·배당 | 없음 | — |

## API

| 요청 | 주소 | 본문 | 응답 |
| --- | --- | --- | --- |
| GET | `/api/health` | | `{ ok: true }` |
| GET | `/api/game` | | 게임 상태 |
| POST | `/api/game/reset` | `{ seed? }` | `{ game }` |
| POST | `/api/turns` | `{ count? }` (1~100, 기본 1) | `{ game }` |
| GET | `/api/news` | | 뉴스 목록 (최신이 앞) |
| POST | `/api/events` | `{ headline, stockId, changePercent }` | `201 { news, game }` |
| POST | `/api/orders` | `{ stockId, side, type, price?, quantity }` | `201 { order, trade, game }` |
| DELETE | `/api/orders/:id` | | `{ order, game }` |

- `side`: `"buy"` | `"sell"`, `type`: `"market"` | `"limit"`. `price`는 지정가일 때만 필요하다.
- 주문 결과의 `order.status`는 `"filled"`(즉시 체결) 또는 `"pending"`(대기)이다. 즉시 체결이면 `trade`에 체결 내역이 온다.
- 잘못된 요청은 `400`, 없는 주문·주소는 `404`, 응답 본문은 `{ "error": "..." }`이다. 실패한 요청은 상태를 바꾸지 않는다.

### 게임 상태 (`GET /api/game`)

```js
{
  seed, turn,                 // 현재 턴 번호 (화면 상단 "현재 n턴")
  initialCash,                // 1,000,000 (수익률 기준)
  cash,                       // 보유 현금
  availableCash,              // 대기 매수 주문에 묶인 돈을 뺀 주문 가능 현금
  equity, profit,             // 총자산, 총 손익
  stocks: [{
    id, name, price, previousClose,
    holding, availableQuantity, averagePrice,
    candles: [{ turn, open, high, low, close, volume }],  // 오래된 턴부터, 최대 200개
    book: { asks: [5개], bids: [5개] },                    // 현재가에서 가까운 호가부터의 잔량
  }],
  orders: [{ id, turn, stockId, side, type, price, quantity, status }], // 대기 주문
  trades: [{ id, orderId, turn, stockId, side, price, quantity, amount, realizedProfit }], // 최신이 앞, 최대 50개
  news:   [{ id, turn, headline, stockId, changePercent, priceBefore, priceAfter }],       // 최신이 앞, 최대 50개
}
```

화면 예제 데이터(`ui/app.mjs`의 `sample`)와 대응: `stocks[].candles`, `holding`, `averagePrice`, `book`, `initialCash`, `cash`는 같은 이름이다.
화면에서 매수 가능 금액은 `cash` 대신 `availableCash`를 쓰면 대기 주문까지 반영된다.
