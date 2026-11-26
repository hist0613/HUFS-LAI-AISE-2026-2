import { createGame, applyEvent } from "../market/engine.mjs";
import { createRandom } from "./random.mjs";
import { roundToTick } from "./ticks.mjs";

// ── 시뮬레이션 설정 (회의에서 정하면 이 값만 바꾼다) ──
const HISTORY_TURNS = 8; // 게임 시작 시 미리 만들어 두는 턴 수 (차트가 비지 않게)
const MAX_CANDLES = 200; // 종목별로 보관할 최대 턴 수
const MAX_LOG = 50; // 뉴스·체결 내역 보관 개수
const VOLATILITY = 0.012; // 턴마다 가격이 움직이는 정도 (표준편차 1.2%)
const MAX_DRIFT = 0.08; // 뉴스 없는 한 턴의 최대 변동 ±8%
const BOOK_DEPTH = 5; // 호가 단계 수
const BASE_VOLUME = { samsong: 1_500_000, hanbit: 500_000 };
const DEFAULT_BASE_VOLUME = 300_000;

// 게임 규칙 위반(잘못된 seed 등). status는 HTTP 응답 코드로 쓴다.
export class GameError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = "GameError";
    this.status = status;
  }
}

const baseVolume = (stockId) => BASE_VOLUME[stockId] ?? DEFAULT_BASE_VOLUME;
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

// 한 사람이 하는 게임 하나의 전체 상태를 들고 있는 시장.
// 모든 변경 메서드는 검사를 먼저 끝낸 뒤 상태를 바꾼다. 실패하면 상태는 그대로다.
export class Market {
  constructor({ seed } = {}) {
    this.reset({ seed });
  }

  reset({ seed = Date.now() } = {}) {
    if (!Number.isSafeInteger(seed) || seed < 0) {
      throw new GameError("seed는 0 이상의 정수여야 합니다.");
    }
    const base = createGame();
    this.seed = seed;
    this.random = createRandom(seed);
    this.turn = HISTORY_TURNS;
    this.initialCash = base.cash;
    this.cash = base.cash;
    this.stocks = base.stocks.map((stock) => this.#createStock(stock));
    this.news = []; // 반영된 뉴스 (최신이 앞)
    this.nextId = { news: 1 };
  }

  // ── 조회 ──

  price(stock) {
    return stock.candles.at(-1).close;
  }

  snapshot() {
    const stocks = this.stocks.map((stock) => ({
      id: stock.id,
      name: stock.name,
      price: this.price(stock),
      previousClose: stock.candles.at(-2).close,
      holding: stock.holding,
      averagePrice: stock.averagePrice,
      candles: stock.candles,
      book: stock.book,
    }));
    const equity = this.cash + stocks.reduce((sum, stock) => sum + stock.holding * stock.price, 0);
    return structuredClone({
      seed: this.seed,
      turn: this.turn,
      initialCash: this.initialCash,
      cash: this.cash,
      equity,
      profit: equity - this.initialCash,
      stocks,
      news: this.news,
    });
  }

  // ── 시장 진행 ──

  // 턴을 하나 넘긴다. 모든 종목에 새 캔들이 생긴다.
  advanceTurn() {
    this.turn += 1;
    for (const stock of this.stocks) {
      const previous = this.price(stock);
      const close = roundToTick(previous * (1 + this.#drift()));
      const candle = this.#makeCandle(stock.id, previous, close, this.turn);
      stock.candles.push(candle);
      if (stock.candles.length > MAX_CANDLES) stock.candles.shift();
      stock.book = this.#makeBook(stock.id);
    }
  }

  // 뉴스를 지금 턴에 바로 반영한다. 가격 계산과 검사는 market/engine.mjs를 그대로 쓴다.
  applyNews(event) {
    const updated = applyEvent(this.stocks.map((stock) => ({ id: stock.id, price: this.price(stock) })), event);
    const stock = this.stocks.find((item) => item.id === event.stockId);
    const before = this.price(stock);
    const after = roundToTick(updated.find((item) => item.id === stock.id).price);
    const candle = stock.candles.at(-1);
    candle.close = after;
    candle.high = Math.max(candle.high, after);
    candle.low = Math.min(candle.low, after);
    candle.volume += this.#volume(stock.id, Math.abs(after / before - 1));
    stock.book = this.#makeBook(stock.id);
    const news = {
      id: this.nextId.news++,
      turn: this.turn,
      headline: event.headline.trim(),
      stockId: stock.id,
      changePercent: event.changePercent,
      priceBefore: before,
      priceAfter: after,
    };
    this.news.unshift(news);
    this.news.length = Math.min(this.news.length, MAX_LOG);
    return news;
  }

  // ── 내부 계산 ──

  #drift() {
    return clamp(this.random.normal() * VOLATILITY, -MAX_DRIFT, MAX_DRIFT);
  }

  #volume(stockId, move) {
    const raw = baseVolume(stockId) * (1 + move * 20) * this.random.between(0.6, 1.4);
    return Math.max(1_000, Math.round(raw / 1_000) * 1_000);
  }

  // 이전 종가에서 이번 종가까지 움직인 한 턴의 시가·고가·저가·종가·거래량
  #makeCandle(stockId, previousClose, close, turn) {
    const r = this.random;
    const open = roundToTick(previousClose * (1 + r.normal() * VOLATILITY * 0.25));
    const top = Math.max(open, close);
    const bottom = Math.min(open, close);
    const high = Math.max(top, roundToTick(top * (1 + Math.abs(r.normal()) * VOLATILITY * 0.4)));
    const low = Math.min(bottom, roundToTick(bottom * (1 - Math.abs(r.normal()) * VOLATILITY * 0.4)));
    const volume = this.#volume(stockId, Math.abs(close / previousClose - 1));
    return { turn, open, high, low, close, volume };
  }

  // 화면 호가창용 잔량(주). 현재가에서 가까운 호가부터 5단계.
  #makeBook(stockId) {
    const size = () => Math.max(1, Math.round(baseVolume(stockId) / 1_000 * this.random.between(0.8, 3)));
    return {
      asks: Array.from({ length: BOOK_DEPTH }, size),
      bids: Array.from({ length: BOOK_DEPTH }, size),
    };
  }

  // 현재가에서 거꾸로 거슬러 올라가며 지난 턴 기록을 만든다. 마지막 종가 = 엔진 초기 가격.
  #createStock({ id, name, price }) {
    const closes = [roundToTick(price)];
    for (let i = 1; i < HISTORY_TURNS; i += 1) {
      closes.unshift(roundToTick(closes[0] / (1 + this.#drift())));
    }
    let previous = roundToTick(closes[0] / (1 + this.#drift()));
    const candles = closes.map((close, index) => {
      const candle = this.#makeCandle(id, previous, close, index + 1);
      previous = close;
      return candle;
    });
    return { id, name, holding: 0, averagePrice: 0, candles, book: this.#makeBook(id) };
  }
}
