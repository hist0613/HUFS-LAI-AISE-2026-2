import { createApp } from "./app.mjs";
import { Market } from "./market.mjs";

const port = Number(process.env.PORT) || 3000;
// 예: TURN_INTERVAL_MS=5000 이면 5초마다 자동으로 턴이 넘어간다. 없으면 POST /api/turns로 넘긴다.
const turnInterval = Number(process.env.TURN_INTERVAL_MS) || 0;
// 예: SEED=2026 이면 매번 같은 시장으로 시작한다 (시연용).
const seed = process.env.SEED === undefined ? undefined : Number(process.env.SEED);

const market = new Market({ seed });
createApp({ market }).listen(port, () => {
  console.log(`AI Stock Simulator 서버 실행 중: http://localhost:${port}`);
  if (turnInterval > 0) console.log(`${turnInterval}ms마다 턴이 자동으로 넘어갑니다.`);
});

if (turnInterval > 0) {
  setInterval(() => market.advanceTurn(), turnInterval);
}
