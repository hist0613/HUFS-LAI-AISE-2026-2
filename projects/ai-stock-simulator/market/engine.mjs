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
  return stocks.map((stock) => {
    if (stock.id !== event.stockId) return stock;
    const price = Math.max(1, Math.round(stock.price * (1 + event.changePercent / 100)));
    return { ...stock, price };
  });
}
