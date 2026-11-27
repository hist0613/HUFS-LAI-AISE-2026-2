import { createGame, applyEvent } from "../market/engine.mjs";
import { createRandom } from "./random.mjs";
import { roundToTick, isOnTick } from "./ticks.mjs";

// ── 시뮬레이션 설정 (회의에서 정하면 이 값만 바꾼다) ──
const HISTORY_TURNS = 8; // 게임 시작 시 미리 만들어 두는 턴 수 (차트가 비지 않게)
const MAX_CANDLES = 200; // 종목별로 보관할 최대 턴 수
const MAX_LOG = 50; // 뉴스·체결 내역 보관 개수
const VOLATILITY = 0.012; // 턴마다 가격이 움직이는 정도 (표준편차 1.2%)
const MAX_DRIFT = 0.08; // 뉴스 없는 한 턴의 최대 변동 ±8%
const BOOK_DEPTH = 5; // 호가 단계 수
const BASE_VOLUME = { samsong: 1_500_000, hanbit: 500_000 };
const DEFAULT_BASE_VOLUME = 300_000;
// 팀 리뷰용 배당 규칙. 시작 이후 10턴마다 삼송전자 주당 500원.
const DIVIDEND_INTERVAL = 10;
const DIVIDEND_PER_SHARE = { samsong: 500 };

// 게임 규칙 위반(현금 부족 등). status는 HTTP 응답 코드로 쓴다.
export class GameError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.name = "GameError";
    this.status = status;
  }
}

const baseVolume = (stockId) => BASE_VOLUME[stockId] ?? DEFAULT_BASE_VOLUME;
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const isPlainObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

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
    this.orders = []; // 체결을 기다리는 지정가 주문
    this.trades = []; // 체결 내역 (최신이 앞)
    this.news = []; // 반영된 뉴스 (최신이 앞)
    this.dividends = [];
    this.totalDividends = 0;
    this.lastDividendTurn = HISTORY_TURNS;
    this.nextId = { order: 1, trade: 1, news: 1 };
  }

  // ── 조회 ──

  price(stock) {
    return stock.candles.at(-1).close;
  }

  // 대기 중인 매수 주문에 묶인 돈을 뺀 주문 가능 현금
  availableCash() {
    return this.cash - this.orders
      .filter((order) => order.side === "buy")
      .reduce((sum, order) => sum + order.price * order.quantity, 0);
  }

  // 대기 중인 매도 주문에 묶인 수량을 뺀 매도 가능 수량
  availableQuantity(stock) {
    return stock.holding - this.orders
      .filter((order) => order.side === "sell" && order.stockId === stock.id)
      .reduce((sum, order) => sum + order.quantity, 0);
  }

  snapshot() {
    const stocks = this.stocks.map((stock) => ({
      id: stock.id,
      name: stock.name,
      price: this.price(stock),
      previousClose: stock.candles.at(-2).close,
      holding: stock.holding,
      availableQuantity: this.availableQuantity(stock),
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
      availableCash: this.availableCash(),
      equity,
      profit: equity - this.initialCash,
      stocks,
      orders: this.orders,
      trades: this.trades,
      news: this.news,
      dividends: this.dividends,
      totalDividends: this.totalDividends,
      nextDividendTurn: HISTORY_TURNS
        + (Math.floor((this.turn - HISTORY_TURNS) / DIVIDEND_INTERVAL) + 1) * DIVIDEND_INTERVAL,
    });
  }

  // ── 시장 진행 ──

  // 턴을 하나 넘긴다. 모든 종목에 새 캔들이 생기고 지정가 주문 체결을 확인한다.
  advanceTurn() {
    this.#payDividends(this.turn + 1);
    this.turn += 1;
    for (const stock of this.stocks) {
      const previous = this.price(stock);
      const close = roundToTick(previous * (1 + this.#drift()));
      const candle = this.#makeCandle(stock.id, previous, close, this.turn);
      stock.candles.push(candle);
      if (stock.candles.length > MAX_CANDLES) stock.candles.shift();
      stock.book = this.#makeBook(stock.id);
      this.#matchOrders(stock, candle.low, candle.high);
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
    this.#matchOrders(stock, after, after);
    return news;
  }

  // ── 주문 ──

  // 입력: { stockId, side: "buy"|"sell", type: "market"|"limit", price, quantity }
  // 시장가, 또는 현재가로 바로 살 수 있는 지정가는 즉시 현재가로 체결한다.
  // 나머지 지정가는 대기 주문이 되고, 이후 가격이 닿으면 주문 가격으로 체결한다.
  placeOrder(input) {
    if (!isPlainObject(input)) throw new GameError("주문은 객체여야 합니다.");
    const stock = this.stocks.find((item) => item.id === input.stockId);
    if (!stock) throw new GameError("등록된 종목 ID가 필요합니다.");
    if (input.side !== "buy" && input.side !== "sell") throw new GameError("side는 buy 또는 sell이어야 합니다.");
    if (input.type !== "market" && input.type !== "limit") throw new GameError("type은 market 또는 limit이어야 합니다.");
    if (!Number.isSafeInteger(input.quantity) || input.quantity < 1) throw new GameError("수량은 1 이상의 정수여야 합니다.");
    if (input.type === "limit" && !isOnTick(input.price)) throw new GameError("지정가는 호가 단위에 맞는 가격이어야 합니다.");

    const { side, type, quantity } = input;
    const current = this.price(stock);
    const immediate = type === "market" || (side === "buy" ? input.price >= current : input.price <= current);
    const fillPrice = immediate ? current : input.price;

    if (side === "buy" && fillPrice * quantity > this.availableCash()) {
      throw new GameError("주문 가능 현금이 부족합니다.");
    }
    if (side === "sell" && quantity > this.availableQuantity(stock)) {
      throw new GameError("매도 가능 수량이 부족합니다.");
    }

    const order = {
      id: this.nextId.order++,
      turn: this.turn,
      stockId: stock.id,
      side,
      type,
      price: type === "limit" ? input.price : null,
      quantity,
      status: "pending",
    };
    if (immediate) {
      const trade = this.#execute(stock, order, current);
      return { order: { ...order, status: "filled" }, trade };
    }
    this.orders.push(order);
    return { order: { ...order }, trade: null };
  }

  cancelOrder(orderId) {
    const index = this.orders.findIndex((order) => order.id === orderId);
    if (index === -1) throw new GameError("대기 중인 주문을 찾을 수 없습니다.", 404);
    const [order] = this.orders.splice(index, 1);
    return { ...order, status: "cancelled" };
  }

  // ── 내부 계산 ──

  // 지급 턴 시작 시 실제 보유량 기준. 해당 턴의 지정가 체결보다 먼저 확정한다.
  #payDividends(turn) {
    if (turn <= this.lastDividendTurn || (turn - HISTORY_TURNS) % DIVIDEND_INTERVAL !== 0) return;
    const payments = [];
    for (const stock of this.stocks) {
      const perShare = DIVIDEND_PER_SHARE[stock.id] ?? 0;
      if (perShare === 0 || stock.holding === 0) continue;
      const amount = stock.holding * perShare;
      if (!Number.isSafeInteger(amount)) throw new GameError("배당금이 안전한 정수 범위를 벗어났습니다.");
      payments.push({ turn, stockId: stock.id, quantity: stock.holding, perShare, amount });
    }
    const total = payments.reduce((sum, payment) => sum + payment.amount, 0);
    if (!Number.isSafeInteger(this.cash + total) || !Number.isSafeInteger(this.totalDividends + total)) {
      throw new GameError("누적 배당금 또는 현금이 안전한 정수 범위를 벗어났습니다.");
    }
    this.cash += total;
    this.totalDividends += total;
    this.dividends.unshift(...payments);
    this.dividends.length = Math.min(this.dividends.length, MAX_LOG);
    this.lastDividendTurn = turn;
  }

  #execute(stock, order, price) {
    const amount = price * order.quantity;
    let realizedProfit = 0;
    if (order.side === "buy") {
      const cost = stock.averagePrice * stock.holding + amount;
      stock.holding += order.quantity;
      stock.averagePrice = Math.round(cost / stock.holding);
      this.cash -= amount;
    } else {
      realizedProfit = (price - stock.averagePrice) * order.quantity;
      stock.holding -= order.quantity;
      if (stock.holding === 0) stock.averagePrice = 0;
      this.cash += amount;
    }
    const trade = {
      id: this.nextId.trade++,
      orderId: order.id,
      turn: this.turn,
      stockId: stock.id,
      side: order.side,
      price,
      quantity: order.quantity,
      amount,
      realizedProfit,
    };
    this.trades.unshift(trade);
    this.trades.length = Math.min(this.trades.length, MAX_LOG);
    return trade;
  }

  // 가격이 [low, high] 범위를 지나갔을 때 닿은 지정가 주문을 체결한다.
  #matchOrders(stock, low, high) {
    const filled = this.orders.filter((order) => order.stockId === stock.id
      && (order.side === "buy" ? low <= order.price : high >= order.price));
    for (const order of filled) {
      this.orders.splice(this.orders.indexOf(order), 1);
      this.#execute(stock, order, order.price);
    }
  }

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
