export function createGame() {
  return {
    cash: 1_000_000,
    stocks: [
      { id: "samsong", name: "삼송전자", price: 50_000 },
      { id: "hanbit", name: "한빛물류", price: 20_000 },
    ],
  };
}

export function applyEvent(stocks, event) {
  if (!event || typeof event !== "object" || Array.isArray(event)) {
    throw new TypeError("뉴스 이벤트는 객체여야 합니다.");
  }
  if (typeof event.headline !== "string" || !event.headline.trim()) {
    throw new TypeError("뉴스 제목이 필요합니다.");
  }
  if (typeof event.stockId !== "string" || !stocks.some((stock) => stock.id === event.stockId)) {
    throw new TypeError("등록된 종목 ID가 필요합니다.");
  }
  if (!Number.isFinite(event.changePercent)) {
    throw new TypeError("변동률은 유한한 숫자여야 합니다.");
  }
  return stocks.map((stock) => {
    if (stock.id !== event.stockId) return stock;
    const calculatedPrice = stock.price * (1 + event.changePercent / 100);
    if (!Number.isFinite(calculatedPrice)) {
      throw new RangeError("계산된 가격이 유한한 숫자 범위를 벗어났습니다.");
    }
    const price = Math.max(1, Math.round(calculatedPrice));
    if (!Number.isSafeInteger(price)) {
      throw new RangeError("계산된 가격이 안전한 정수 범위를 벗어났습니다.");
    }
    return { ...stock, price };
  });
}

export function applyEventToGame(game, event) {
  return { ...game, stocks: applyEvent(game.stocks, event) };
}
