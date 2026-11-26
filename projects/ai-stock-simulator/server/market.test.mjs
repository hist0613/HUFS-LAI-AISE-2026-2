import assert from "node:assert/strict";
import test from "node:test";
import { Market, GameError } from "./market.mjs";
import { isOnTick, roundToTick, tickSize } from "./ticks.mjs";
import { sampleEvent } from "../events/sample.mjs";

const SEED = 2026;
const stockOf = (game, id = "samsong") => game.stocks.find((stock) => stock.id === id);

function assertValidCandles(candles) {
  for (const candle of candles) {
    for (const key of ["open", "high", "low", "close"]) assert.ok(isOnTick(candle[key]), `${key} ${candle[key]}`);
    assert.ok(candle.low <= Math.min(candle.open, candle.close));
    assert.ok(candle.high >= Math.max(candle.open, candle.close));
    assert.ok(Number.isSafeInteger(candle.volume) && candle.volume > 0);
  }
}

test("호가 단위 반올림은 구간 경계에서도 호가에 맞는다", () => {
  assert.equal(tickSize(19_990), 10);
  assert.equal(tickSize(20_000), 50);
  assert.equal(roundToTick(52_020), 52_000);
  assert.equal(roundToTick(49_990), 50_000);
  assert.equal(roundToTick(0.2), 1);
  for (let price = 1; price < 600_000; price += 137) assert.ok(isOnTick(roundToTick(price)));
});

test("시작 상태는 화면이 쓰는 값을 모두 갖고, 같은 시드면 같다", () => {
  const game = new Market({ seed: SEED }).snapshot();
  assert.equal(game.turn, 8);
  assert.equal(game.initialCash, 1_000_000);
  assert.equal(game.cash, 1_000_000);
  assert.equal(game.availableCash, 1_000_000);
  assert.equal(game.equity, 1_000_000);
  const samsong = stockOf(game);
  assert.equal(samsong.name, "삼송전자");
  assert.equal(samsong.price, 50_000);
  assert.equal(stockOf(game, "hanbit").price, 20_000);
  assert.equal(samsong.candles.length, 8);
  assert.deepEqual(samsong.candles.map((candle) => candle.turn), [1, 2, 3, 4, 5, 6, 7, 8]);
  assert.equal(samsong.previousClose, samsong.candles[6].close);
  assert.equal(samsong.book.asks.length, 5);
  assert.equal(samsong.book.bids.length, 5);
  for (const stock of game.stocks) assertValidCandles(stock.candles);
  assert.deepEqual(new Market({ seed: SEED }).snapshot(), game);
});

test("턴을 넘기면 모든 종목에 새 캔들이 생긴다", () => {
  const market = new Market({ seed: SEED });
  for (let i = 0; i < 30; i += 1) market.advanceTurn();
  const game = market.snapshot();
  assert.equal(game.turn, 38);
  for (const stock of game.stocks) {
    assert.equal(stock.candles.length, 38);
    assert.equal(stock.candles.at(-1).turn, 38);
    assert.equal(stock.price, stock.candles.at(-1).close);
    assertValidCandles(stock.candles);
  }
});

test("뉴스는 엔진으로 계산하고 호가 단위로 맞춰 현재 턴에 반영한다", () => {
  const market = new Market({ seed: SEED });
  const first = market.applyNews(sampleEvent);
  assert.equal(first.priceBefore, 50_000);
  assert.equal(first.priceAfter, 51_000);
  market.applyNews(sampleEvent); // 51,000 × 1.02 = 52,020 → 52,000
  const game = market.snapshot();
  const samsong = stockOf(game);
  assert.equal(samsong.price, 52_000);
  assert.ok(samsong.candles.at(-1).high >= 52_000);
  assert.equal(game.turn, 8);
  assert.equal(game.news.length, 2);
  assert.equal(game.news[0].headline, sampleEvent.headline);
  assert.equal(stockOf(game, "hanbit").price, 20_000);
});

test("잘못된 뉴스는 엔진 오류로 거부하고 상태를 바꾸지 않는다", () => {
  const market = new Market({ seed: SEED });
  const before = market.snapshot();
  assert.throws(() => market.applyNews({ ...sampleEvent, stockId: "unknown" }), TypeError);
  assert.throws(() => market.applyNews({ ...sampleEvent, changePercent: 1e15 }), RangeError);
  assert.deepEqual(market.snapshot(), before);
});

test("시장가 매수·매도는 현재가로 바로 체결하고 평균 단가를 계산한다", () => {
  const market = new Market({ seed: SEED });
  market.placeOrder({ stockId: "samsong", side: "buy", type: "market", quantity: 2 });
  market.applyNews({ ...sampleEvent, changePercent: 10 }); // 55,000
  const { order, trade } = market.placeOrder({ stockId: "samsong", side: "buy", type: "market", quantity: 2 });
  assert.equal(order.status, "filled");
  assert.equal(trade.price, 55_000);
  let game = market.snapshot();
  assert.equal(stockOf(game).holding, 4);
  assert.equal(stockOf(game).averagePrice, 52_500);
  assert.equal(game.cash, 1_000_000 - 100_000 - 110_000);

  const sold = market.placeOrder({ stockId: "samsong", side: "sell", type: "market", quantity: 4 });
  assert.equal(sold.trade.realizedProfit, (55_000 - 52_500) * 4);
  game = market.snapshot();
  assert.equal(stockOf(game).holding, 0);
  assert.equal(stockOf(game).averagePrice, 0);
  assert.equal(game.cash, 1_010_000);
  assert.equal(game.trades.length, 3);
});

test("현재가로 살 수 있는 지정가는 현재가로 바로 체결한다", () => {
  const market = new Market({ seed: SEED });
  const { order, trade } = market.placeOrder({ stockId: "samsong", side: "buy", type: "limit", price: 50_800, quantity: 1 });
  assert.equal(order.status, "filled");
  assert.equal(trade.price, 50_000);
});

test("지정가 대기 주문은 돈을 묶어 두고, 가격이 닿으면 주문 가격으로 체결한다", () => {
  const market = new Market({ seed: SEED });
  const { order } = market.placeOrder({ stockId: "samsong", side: "buy", type: "limit", price: 47_000, quantity: 10 });
  assert.equal(order.status, "pending");
  let game = market.snapshot();
  assert.equal(game.orders.length, 1);
  assert.equal(game.cash, 1_000_000);
  assert.equal(game.availableCash, 530_000);
  assert.throws(
    () => market.placeOrder({ stockId: "samsong", side: "buy", type: "market", quantity: 11 }),
    { name: "GameError", message: "주문 가능 현금이 부족합니다." },
  );

  market.applyNews({ ...sampleEvent, changePercent: -10 }); // 45,000
  game = market.snapshot();
  assert.equal(game.orders.length, 0);
  assert.equal(stockOf(game).holding, 10);
  assert.equal(stockOf(game).averagePrice, 47_000);
  assert.equal(game.cash, 530_000);
  assert.equal(game.availableCash, 530_000);
});

test("지정가 매도 대기는 수량을 묶고, 취소하면 풀린다", () => {
  const market = new Market({ seed: SEED });
  market.placeOrder({ stockId: "samsong", side: "buy", type: "market", quantity: 3 });
  const { order } = market.placeOrder({ stockId: "samsong", side: "sell", type: "limit", price: 60_000, quantity: 2 });
  assert.equal(stockOf(market.snapshot()).availableQuantity, 1);
  assert.throws(() => market.placeOrder({ stockId: "samsong", side: "sell", type: "market", quantity: 2 }), GameError);
  assert.equal(market.cancelOrder(order.id).status, "cancelled");
  assert.equal(stockOf(market.snapshot()).availableQuantity, 3);
  assert.throws(() => market.cancelOrder(order.id), { status: 404 });
});

test("잘못된 주문은 거부하고 상태를 바꾸지 않는다", () => {
  const market = new Market({ seed: SEED });
  const before = market.snapshot();
  const base = { stockId: "samsong", side: "buy", type: "limit", price: 50_000, quantity: 1 };
  const invalid = [
    null, [], "주문",
    { ...base, stockId: "unknown" },
    { ...base, side: "hold" },
    { ...base, type: "stop" },
    { ...base, quantity: 0 },
    { ...base, quantity: 1.5 },
    { ...base, quantity: "1" },
    { ...base, price: 50_050 }, // 50,000원 이상은 100원 단위
    { ...base, price: undefined },
    { ...base, quantity: 21 }, // 1,050,000원 > 현금
    { ...base, side: "sell" }, // 보유 0주
  ];
  for (const input of invalid) {
    assert.throws(() => market.placeOrder(input), GameError, JSON.stringify(input));
  }
  assert.deepEqual(market.snapshot(), before);
});

test("다시 시작하면 처음 상태로 돌아간다", () => {
  const market = new Market({ seed: SEED });
  const initial = market.snapshot();
  market.placeOrder({ stockId: "samsong", side: "buy", type: "market", quantity: 3 });
  market.advanceTurn();
  market.applyNews(sampleEvent);
  market.reset({ seed: SEED });
  assert.deepEqual(market.snapshot(), initial);
  assert.throws(() => market.reset({ seed: -1 }), GameError);
});
