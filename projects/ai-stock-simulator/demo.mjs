import { sampleEvent } from "./events/sample.mjs";
import { createGame, applyEvent } from "./market/engine.mjs";

const game = createGame();
const updatedStocks = applyEvent(game.stocks, sampleEvent);
const won = (amount) => amount.toLocaleString("ko-KR") + "원";

console.log("초기 현금:", won(game.cash));
console.log("예제 뉴스:", sampleEvent.headline);
for (const [index, stock] of updatedStocks.entries()) {
  console.log(stock.name, won(game.stocks[index].price), "→", won(stock.price));
}
