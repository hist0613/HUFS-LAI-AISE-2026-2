import assert from "node:assert/strict";
import test from "node:test";
import { createApp } from "./app.mjs";
import { sampleEvent } from "../events/sample.mjs";

// 테스트마다 빈 포트로 새 서버를 띄우고, 끝나면 닫는다.
async function withServer(fn) {
  const server = createApp().listen(0);
  await new Promise((resolve) => server.once("listening", resolve));
  const base = `http://localhost:${server.address().port}`;
  try {
    await fn(base);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

const postJson = (url, body) =>
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });

test("GET /api/health 는 ok를 돌려준다", () =>
  withServer(async (base) => {
    const res = await fetch(`${base}/api/health`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ok: true });
  }));

test("GET /api/game 은 초기 게임 상태를 돌려준다", () =>
  withServer(async (base) => {
    const game = await (await fetch(`${base}/api/game`)).json();
    assert.equal(game.cash, 1_000_000);
    assert.equal(game.stocks[0].price, 50_000);
  }));

test("POST /api/events 는 뉴스를 반영하고 상태가 이어진다", () =>
  withServer(async (base) => {
    const first = await postJson(`${base}/api/events`, sampleEvent);
    assert.equal(first.status, 200);
    assert.equal((await first.json()).stocks[0].price, 51_000);
    await postJson(`${base}/api/events`, sampleEvent);
    const game = await (await fetch(`${base}/api/game`)).json();
    assert.equal(game.stocks[0].price, 52_020);
    assert.equal(game.stocks[1].price, 20_000);
  }));

test("잘못된 요청은 400을 돌려주고 상태를 바꾸지 않는다", () =>
  withServer(async (base) => {
    const bad = [
      { ...sampleEvent, stockId: "unknown" },
      { ...sampleEvent, changePercent: 1e15 },
      "{ 깨진 json",
    ];
    for (const body of bad) {
      const res = await postJson(`${base}/api/events`, body);
      assert.equal(res.status, 400);
      assert.ok((await res.json()).error);
    }
    const game = await (await fetch(`${base}/api/game`)).json();
    assert.equal(game.stocks[0].price, 50_000);
  }));

test("없는 주소는 404를 돌려준다", () =>
  withServer(async (base) => {
    const res = await fetch(`${base}/api/nothing`);
    assert.equal(res.status, 404);
  }));
