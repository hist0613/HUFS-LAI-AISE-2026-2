const sample = {
  initialCash: 1_000_000,
  cash: 900_000,
  stocks: [
    {
      name: "삼송전자",
      holding: 2,
      averagePrice: 50_000,
      // 턴별 [시가, 고가, 저가, 종가, 거래량]
      turns: [
        [47_200, 47_900, 47_000, 47_500, 1_284_000],
        [47_600, 49_100, 47_400, 48_900, 2_105_000],
        [48_800, 49_000, 48_300, 48_500, 1_532_000],
        [48_600, 49_900, 48_400, 49_700, 1_876_000],
        [49_600, 49_800, 49_100, 49_300, 1_201_000],
        [49_400, 50_400, 49_200, 50_200, 1_654_000],
        [50_100, 50_500, 49_800, 50_000, 1_112_000],
        [50_100, 51_200, 49_900, 51_000, 2_348_000],
      ],
    },
    {
      name: "한빛물류",
      holding: 0,
      averagePrice: 0,
      turns: [
        [21_000, 21_350, 20_950, 21_200, 412_000],
        [21_250, 21_300, 20_800, 20_900, 538_000],
        [20_900, 21_200, 20_850, 21_100, 367_000],
        [21_050, 21_100, 20_300, 20_400, 845_000],
        [20_450, 20_700, 20_350, 20_600, 402_000],
        [20_550, 20_600, 20_150, 20_200, 611_000],
        [20_250, 20_300, 19_950, 20_000, 726_000],
        [20_050, 20_150, 19_900, 20_000, 389_000],
      ],
    },
  ],
};

for (const stock of sample.stocks) {
  stock.candles = stock.turns.map(([open, high, low, close, volume]) => ({ open, high, low, close, volume }));
}

const byId = (id) => document.getElementById(id);
const number = new Intl.NumberFormat("ko-KR");
const signed = new Intl.NumberFormat("ko-KR", { signDisplay: "exceptZero" });
const percent = new Intl.NumberFormat("ko-KR", { style: "percent", signDisplay: "exceptZero", minimumFractionDigits: 2, maximumFractionDigits: 2 });
const won = (value) => `${number.format(value)}원`;
const price = (stock) => stock.candles.at(-1).close;
const previousClose = (stock) => stock.candles.at(-2).close;
const direction = (value) => value > 0 ? "up" : value < 0 ? "down" : "";
const arrow = (value) => value > 0 ? "▲" : value < 0 ? "▼" : "";
const movement = (value, base) => `${arrow(value - base)}${number.format(Math.abs(value - base))} (${percent.format(value / base - 1)})`;

function el(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.append(...children);
  return node;
}

let selected = sample.stocks[0];

const equity = sample.cash + sample.stocks.reduce((sum, stock) => sum + stock.holding * price(stock), 0);
byId("turn").textContent = `현재 ${selected.candles.length}턴`;
byId("equity").textContent = won(equity);
byId("cash").textContent = won(sample.cash);
byId("return").textContent = `${signed.format(equity - sample.initialCash)}원 (${percent.format(equity / sample.initialCash - 1)})`;
byId("return").className = direction(equity - sample.initialCash);

const stockButtons = sample.stocks.map((stock) => {
  const trend = direction(price(stock) - previousClose(stock));
  const button = el("button", "stock",
    el("span", "stock-name", stock.name, el("small", "", `보유 ${number.format(stock.holding)}주`)),
    el("span", "stock-quote",
      el("span", trend, number.format(price(stock))),
      el("small", trend, percent.format(price(stock) / previousClose(stock) - 1))));
  button.type = "button";
  button.addEventListener("click", () => {
    if (stock === selected) return;
    selected = stock;
    renderSelection();
  });
  byId("stocks").append(button);
  return button;
});

function renderSelection() {
  stockButtons.forEach((button, index) => button.setAttribute("aria-pressed", sample.stocks[index] === selected));
  const current = selected.candles.at(-1);
  const previous = previousClose(selected);
  byId("quote-name").textContent = selected.name;
  byId("price").textContent = won(current.close);
  byId("change").textContent = movement(current.close, previous);
  byId("price").className = byId("change").className = direction(current.close - previous);
  for (const key of ["open", "high", "low"]) {
    byId(`stat-${key}`).textContent = number.format(current[key]);
    byId(`stat-${key}`).className = direction(current[key] - previous);
  }
  byId("stat-prev").textContent = number.format(previous);
  byId("stat-volume").textContent = number.format(current.volume);

  const held = selected.holding > 0;
  const profit = (current.close - selected.averagePrice) * selected.holding;
  byId("market-value").textContent = won(selected.holding * current.close);
  byId("profit").textContent = held ? `${signed.format(profit)}원 (${percent.format(current.close / selected.averagePrice - 1)})` : "—";
  byId("profit").className = held ? direction(profit) : "";
  byId("holding").textContent = `${number.format(selected.holding)}주`;
  byId("average-price").textContent = held ? won(selected.averagePrice) : "—";
}

renderSelection();
