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

test("다시 시작하면 처음 상태로 돌아간다", () => {
  const market = new Market({ seed: SEED });
  const initial = market.snapshot();
  market.advanceTurn();
  market.applyNews(sampleEvent);
  market.reset({ seed: SEED });
  assert.deepEqual(market.snapshot(), initial);
  assert.throws(() => market.reset({ seed: -1 }), GameError);
});
