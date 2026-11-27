import assert from "node:assert/strict";
import test from "node:test";
import { Market } from "./market.mjs";

const buy = (market, stockId = "samsong") =>
  market.placeOrder({ stockId, side: "buy", type: "market", quantity: 2 });
const advance = (market, count) => {
  for (let i = 0; i < count; i += 1) market.advanceTurn();
};

test("시작 후 10턴에 배당을 지급하고 자산에는 현금으로 한 번 반영한다", () => {
  const market = new Market({ seed: 2026 });
  buy(market);
  assert.equal(market.snapshot().nextDividendTurn, 18);
  advance(market, 9);
  assert.equal(market.cash, 900_000);
  market.advanceTurn();
  const game = market.snapshot();
  assert.equal(game.cash, 901_000);
  assert.equal(game.availableCash, 901_000);
  assert.equal(game.totalDividends, 1_000);
  assert.equal(game.nextDividendTurn, 28);
  assert.deepEqual(game.dividends, [
    { turn: 18, stockId: "samsong", quantity: 2, perShare: 500, amount: 1_000 },
  ]);
  assert.equal(game.equity, game.cash + game.stocks[0].price * 2);
  assert.equal(game.profit, game.equity - game.initialCash);
  market.applyNews({ headline: "후속 뉴스", stockId: "samsong", changePercent: 0 });
  market.snapshot();
  assert.equal(market.cash, 901_000);
  advance(market, 10);
  assert.equal(market.cash, 902_000);
  assert.deepEqual(market.snapshot().dividends.map((item) => item.turn), [28, 18]);
});

test("미보유·무배당 종목·지급 전 전량 매도에는 배당이 없다", () => {
  for (const mode of ["empty", "hanbit", "sold"]) {
    const market = new Market({ seed: 2026 });
    if (mode === "hanbit") buy(market, "hanbit");
    if (mode === "sold") {
      buy(market);
      market.placeOrder({ stockId: "samsong", side: "sell", type: "market", quantity: 2 });
    }
    const cash = market.cash;
    advance(market, 10);
    assert.equal(market.cash, cash);
    assert.deepEqual(market.snapshot().dividends, []);
    assert.equal(market.snapshot().totalDividends, 0);
  }
});

test("미체결 매수에는 지급하지 않고 매도 대기 주식에는 지급한다", () => {
  const market = new Market({ seed: 2026 });
  buy(market);
  market.placeOrder({ stockId: "samsong", side: "sell", type: "limit", price: 1_000_000, quantity: 2 });
  market.placeOrder({ stockId: "samsong", side: "buy", type: "limit", price: 1, quantity: 3 });
  advance(market, 10);
  assert.equal(market.snapshot().totalDividends, 1_000);
  assert.equal(market.snapshot().availableCash, 900_997);
});

test("지급 턴의 지정가 체결은 배당 기준 수량을 바꾸지 않는다", () => {
  for (const side of ["buy", "sell"]) {
    const market = new Market({ seed: 2026 });
    if (side === "sell") buy(market);
    advance(market, 9);
    const current = market.snapshot().stocks[0].price;
    const price = side === "buy" ? current - 1_000 : current + 1_000;
    market.placeOrder({ stockId: "samsong", side, type: "limit", price, quantity: 2 });
    market.random.normal = () => side === "buy" ? -10 : 10;
    market.advanceTurn();
    assert.equal(market.snapshot().orders.length, 0);
    assert.equal(market.snapshot().dividends.length, side === "buy" ? 0 : 1);
    assert.equal(market.snapshot().totalDividends, side === "buy" ? 0 : 1_000);
  }
});

test("내역 보관 한도와 별개로 누적액을 유지하고 새 게임에서 초기화한다", () => {
  const market = new Market({ seed: 2026 });
  const initial = market.snapshot();
  buy(market);
  advance(market, 510);
  assert.equal(market.snapshot().dividends.length, 50);
  assert.equal(market.snapshot().totalDividends, 51_000);
  market.reset({ seed: 2026 });
  assert.deepEqual(market.snapshot(), initial);
  buy(market);
  advance(market, 10);
  assert.equal(market.snapshot().totalDividends, 1_000);
});
