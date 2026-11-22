import assert from "node:assert/strict";
import test from "node:test";
import { createGame, applyEvent, applyEventToGame } from "./engine.mjs";
import { sampleEvent } from "../events/sample.mjs";

test("연속 뉴스는 갱신된 가격에 적용하고 원본과 다른 상태를 유지한다", () => {
  const game = createGame();
  game.trades = [];
  const original = structuredClone(game);
  game.stocks.forEach(Object.freeze);
  Object.freeze(game.stocks);
  Object.freeze(game);
  const first = applyEventToGame(game, sampleEvent);
  const second = applyEventToGame(first, sampleEvent);
  assert.equal(first.stocks[0].price, 51_000);
  assert.equal(second.stocks[0].price, 52_020);
  assert.equal(second.cash, 1_000_000);
  assert.deepEqual(second.stocks[1], original.stocks[1]);
  assert.deepEqual(second.trades, []);
  assert.deepEqual(game, original);
  assert.notEqual(first, game);
  assert.notEqual(first.stocks, game.stocks);
});

test("기존 배열 API는 원 단위 반올림과 최저가 1원을 유지한다", () => {
  const stocks = [{ id: "samsong", name: "삼송전자", price: 101 }];
  assert.equal(applyEvent(stocks, { ...sampleEvent, changePercent: 0.5 })[0].price, 102);
  assert.equal(applyEvent(stocks, { ...sampleEvent, changePercent: 0 })[0].price, 101);
  assert.equal(applyEvent(stocks, { ...sampleEvent, changePercent: -50 })[0].price, 51);
  assert.equal(applyEvent(stocks, { ...sampleEvent, changePercent: -100 })[0].price, 1);
  assert.equal(applyEvent(stocks, { ...sampleEvent, changePercent: -200 })[0].price, 1);
  assert.equal(stocks[0].price, 101);
});

test("잘못된 이벤트는 두 진입점에서 거부하고 상태를 보존한다", () => {
  const invalidEvents = [
    null, undefined, [], "뉴스", {},
    { ...sampleEvent, headline: "" },
    { ...sampleEvent, headline: "   " },
    { ...sampleEvent, headline: 123 },
    { ...sampleEvent, stockId: "unknown" },
    { ...sampleEvent, stockId: null },
    ...[undefined, null, "2", NaN, Infinity, -Infinity].map(
      (changePercent) => ({ ...sampleEvent, changePercent }),
    ),
  ];
  for (const event of invalidEvents) {
    const game = createGame();
    const original = structuredClone(game);
    assert.throws(() => applyEventToGame(game, event), TypeError);
    assert.throws(() => applyEvent(game.stocks, event), TypeError);
    assert.deepEqual(game, original);
  }
});

test("계산 범위 초과는 부분 반영 없이 거부한다", () => {
  const game = createGame();
  const original = structuredClone(game);
  for (const changePercent of [Number.MAX_VALUE, 1e15, -Number.MAX_VALUE]) {
    const event = { ...sampleEvent, changePercent };
    assert.throws(() => applyEventToGame(game, event), RangeError);
    assert.deepEqual(game, original);
  }
});
