import { sampleEvent } from "./events/sample.mjs";
import { createGame, applyEventToGame } from "./market/engine.mjs";

let game = createGame();
const won = (amount) => amount.toLocaleString("ko-KR") + "원";

console.log("초기 현금:", won(game.cash));
const events = [
  sampleEvent,
  { ...sampleEvent, headline: "삼송전자, 반도체 시제품 공급 계약 체결" },
];
for (const event of events) {
  const previousGame = game;
  game = applyEventToGame(game, event);
  console.log("예제 뉴스:", event.headline);
  for (const [index, stock] of game.stocks.entries()) {
    console.log(stock.name, won(previousGame.stocks[index].price), "→", won(stock.price));
  }
}
