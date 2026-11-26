import assert from "node:assert/strict";
import test from "node:test";
import { createApp } from "./app.mjs";
import { Market } from "./market.mjs";
import { sampleEvent } from "../events/sample.mjs";

// 테스트마다 같은 시드의 새 서버를 빈 포트로 띄우고, 끝나면 닫는다.
async function withServer(fn) {
  const server = createApp({ market: new Market({ seed: 2026 }) }).listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  const base = `http://localhost:${server.address().port}`;
  try {
    await fn(base);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

const send = async (method, url, body) => {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
  return { status: res.status, body: await res.json() };
};
const getGame = async (base) => (await send("GET", `${base}/api/game`)).body;

test("GET /api/health 는 ok를 돌려준다", () =>
  withServer(async (base) => {
    assert.deepEqual(await send("GET", `${base}/api/health`), { status: 200, body: { ok: true } });
  }));

test("GET /api/game 은 화면에 필요한 상태를 모두 돌려준다", () =>
  withServer(async (base) => {
    const game = await getGame(base);
    for (const key of ["turn", "initialCash", "cash", "equity", "profit", "stocks", "news"]) {
      assert.ok(key in game, key);
    }
    const stock = game.stocks[0];
    for (const key of ["id", "name", "price", "previousClose", "holding", "averagePrice", "candles", "book"]) {
      assert.ok(key in stock, key);
    }
    assert.equal(stock.price, 50_000);
    assert.deepEqual(Object.keys(stock.candles[0]), ["turn", "open", "high", "low", "close", "volume"]);
  }));

test("POST /api/events 는 뉴스를 반영하고 상태가 이어진다", () =>
  withServer(async (base) => {
    const first = await send("POST", `${base}/api/events`, sampleEvent);
    assert.equal(first.status, 201);
    assert.equal(first.body.news.priceAfter, 51_000);
    assert.equal(first.body.game.stocks[0].price, 51_000);
    await send("POST", `${base}/api/events`, sampleEvent);
    const game = await getGame(base);
    assert.equal(game.stocks[0].price, 52_000);
    assert.equal(game.stocks[1].price, 20_000);
    assert.equal((await send("GET", `${base}/api/news`)).body.length, 2);
  }));

test("POST /api/turns 는 턴을 넘긴다", () =>
  withServer(async (base) => {
    assert.equal((await send("POST", `${base}/api/turns`)).body.game.turn, 9);
    assert.equal((await send("POST", `${base}/api/turns`, { count: 3 })).body.game.turn, 12);
    assert.equal((await send("POST", `${base}/api/turns`, { count: 0 })).status, 400);
    assert.equal((await getGame(base)).stocks[0].candles.length, 12);
  }));

test("POST /api/game/reset 은 같은 시드면 처음 상태로 돌아간다", () =>
  withServer(async (base) => {
    const initial = await getGame(base);
    await send("POST", `${base}/api/turns`, { count: 2 });
    await send("POST", `${base}/api/events`, sampleEvent);
    const reset = await send("POST", `${base}/api/game/reset`, { seed: 2026 });
    assert.equal(reset.status, 200);
    assert.deepEqual(reset.body.game, initial);
  }));

test("잘못된 요청은 400을 돌려주고 상태를 바꾸지 않는다", () =>
  withServer(async (base) => {
    const before = await getGame(base);
    for (const body of [{ ...sampleEvent, stockId: "unknown" }, { ...sampleEvent, changePercent: 1e15 }, "{ 깨진 json"]) {
      const res = await send("POST", `${base}/api/events`, body);
      assert.equal(res.status, 400);
      assert.ok(res.body.error);
    }
    assert.equal((await send("POST", `${base}/api/game/reset`, { seed: "abc" })).status, 400);
    assert.deepEqual(await getGame(base), before);
  }));

test("없는 주소는 404를 돌려준다", () =>
  withServer(async (base) => {
    assert.equal((await send("GET", `${base}/api/nothing`)).status, 404);
  }));
