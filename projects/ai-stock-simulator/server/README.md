# 서버

`market/engine.mjs`의 게임 상태를 HTTP API로 제공하는 Express 서버다.
게임 상태는 메모리에만 보관하므로 서버를 다시 켜면 초기화된다.

## 실행

```sh
cd projects/ai-stock-simulator/server
npm install
npm start          # http://localhost:3000 (PORT 환경 변수로 변경 가능)
npm test
```

## API

| 요청 | 주소 | 설명 |
| --- | --- | --- |
| GET | `/api/health` | 서버 상태 확인. `{ "ok": true }` |
| GET | `/api/game` | 현재 현금과 종목 시세 |
| POST | `/api/events` | 뉴스 이벤트 반영 후 새 게임 상태 반환 |

`POST /api/events` 본문 예:

```json
{ "headline": "삼송전자 실적 호조", "stockId": "samsong", "changePercent": 5 }
```

잘못된 이벤트나 깨진 JSON은 `400`과 `{ "error": "..." }`, 없는 주소는 `404`를 돌려준다.
