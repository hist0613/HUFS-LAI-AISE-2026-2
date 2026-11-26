import { fileURLToPath } from "node:url";
import express from "express";
import { Market, GameError } from "./market.mjs";

const uiDir = fileURLToPath(new URL("../ui/", import.meta.url));

// 서버 앱을 만든다. 실행(index.mjs)과 분리해 두어 테스트에서 따로 띄울 수 있다.
// 게임 상태는 우선 메모리에만 보관한다. 서버를 다시 켜면 초기화된다.
export function createApp({ market = new Market() } = {}) {
  const app = express();
  app.locals.market = market;
  app.use(express.json());

  // 서버가 살아 있는지 확인
  app.get("/api/health", (req, res) => {
    res.json({ ok: true });
  });

  // 화면에 필요한 전체 게임 상태
  app.get("/api/game", (req, res) => {
    res.json(market.snapshot());
  });

  // 100만 원으로 다시 시작. 본문 { "seed": 123 }을 주면 같은 시장을 재현한다.
  app.post("/api/game/reset", (req, res) => {
    market.reset({ seed: req.body?.seed ?? Date.now() });
    res.json({ game: market.snapshot() });
  });

  // 턴 넘기기. 본문 { "count": 3 }으로 여러 턴을 한 번에 넘길 수 있다 (최대 100).
  app.post("/api/turns", (req, res) => {
    const count = req.body?.count ?? 1;
    if (!Number.isSafeInteger(count) || count < 1 || count > 100) {
      throw new GameError("count는 1~100 사이의 정수여야 합니다.");
    }
    for (let i = 0; i < count; i += 1) market.advanceTurn();
    res.json({ game: market.snapshot() });
  });

  // 반영된 뉴스 목록 (최신이 앞)
  app.get("/api/news", (req, res) => {
    res.json(market.snapshot().news);
  });

  // 뉴스 이벤트를 시장에 반영
  // 본문 예: { "headline": "...", "stockId": "samsong", "changePercent": 2 }
  app.post("/api/events", (req, res) => {
    const news = market.applyNews(req.body);
    res.status(201).json({ news, game: market.snapshot() });
  });

  // 주문. 본문 예: { "stockId": "samsong", "side": "buy", "type": "limit", "price": 50800, "quantity": 3 }
  app.post("/api/orders", (req, res) => {
    const { order, trade } = market.placeOrder(req.body);
    res.status(201).json({ order, trade, game: market.snapshot() });
  });

  // 대기 중인 지정가 주문 취소
  app.delete("/api/orders/:id", (req, res) => {
    const order = market.cancelOrder(Number(req.params.id));
    res.json({ order, game: market.snapshot() });
  });

  // 거래 화면(ui/ 폴더)이 있으면 같은 주소에서 보여준다. http://localhost:3000/
  app.use(express.static(uiDir));

  // 없는 주소
  app.use((req, res) => {
    res.status(404).json({ error: "없는 주소입니다." });
  });

  // 오류 처리: 잘못된 요청은 400(또는 GameError가 정한 코드), 그 밖의 서버 오류는 500
  app.use((err, req, res, next) => {
    if (err instanceof GameError) {
      return res.status(err.status).json({ error: err.message });
    }
    if (err instanceof TypeError || err instanceof RangeError) {
      return res.status(400).json({ error: err.message });
    }
    if (err.type === "entity.parse.failed") {
      return res.status(400).json({ error: "JSON 형식이 올바르지 않습니다." });
    }
    console.error(err);
    res.status(500).json({ error: "서버 내부 오류입니다." });
  });

  return app;
}
