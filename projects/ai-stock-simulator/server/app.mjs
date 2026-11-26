import express from "express";
import { createGame, applyEventToGame } from "../market/engine.mjs";

// 서버 앱을 만든다. 실행(index.mjs)과 분리해 두어 테스트에서 따로 띄울 수 있다.
export function createApp() {
  const app = express();
  app.use(express.json());

  // 게임 상태는 우선 메모리에만 보관한다. 서버를 다시 켜면 초기화된다.
  let game = createGame();

  // 서버가 살아 있는지 확인
  app.get("/api/health", (req, res) => {
    res.json({ ok: true });
  });

  // 현재 게임 상태(현금, 종목 시세) 조회
  app.get("/api/game", (req, res) => {
    res.json(game);
  });

  // 뉴스 이벤트를 시장에 반영
  // 본문 예: { "headline": "...", "stockId": "samsong", "changePercent": 2 }
  app.post("/api/events", (req, res) => {
    game = applyEventToGame(game, req.body);
    res.json(game);
  });

  // 없는 주소
  app.use((req, res) => {
    res.status(404).json({ error: "없는 API 주소입니다." });
  });

  // 오류 처리: 잘못된 요청은 400, 그 밖의 서버 오류는 500
  app.use((err, req, res, next) => {
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
