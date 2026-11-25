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

const form = byId("order-form");
const quantity = byId("quantity");
const canvas = byId("price-chart");
const rangeButtons = [...document.querySelectorAll(".ranges button")];
let selected = sample.stocks[0];
let rangeSize = 0;
let scrub = null;

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
    scrub = null;
    form.reset();
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

  byId("order-stock").textContent = selected.name;
  byId("order-current").textContent = `현재가 ${won(current.close)}`;
  renderOrder();
  renderChart();
}

function orderState() {
  const selling = form.elements.side.value === "sell";
  const unitPrice = price(selected);
  const limit = selling ? selected.holding : Math.floor(sample.cash / unitPrice);
  return { selling, unitPrice, limit };
}

function renderOrder() {
  const { selling, unitPrice, limit } = orderState();
  form.dataset.side = selling ? "sell" : "buy";
  quantity.max = limit;
  quantity.disabled = limit === 0;
  form.querySelectorAll('[data-step="quantity"], [data-ratio]').forEach((button) => { button.disabled = limit === 0; });
  const valid = limit > 0 && quantity.validity.valid;
  byId("available-label").textContent = selling ? "매도 가능" : "매수 가능";
  byId("available").textContent = selling
    ? `${number.format(limit)}주`
    : `${number.format(limit)}주 · 현금 ${won(sample.cash)}`;
  byId("estimate").textContent = valid ? won(quantity.valueAsNumber * unitPrice) : "—";
  const button = byId("preview-order");
  button.disabled = !valid;
  button.textContent = selling ? "매도 확인" : "매수 확인";
  byId("order-status").textContent = limit === 0 ? (selling ? "보유한 주식이 없습니다." : "주문 가능 현금이 부족합니다.")
    : !quantity.validity.valid ? `1~${number.format(limit)}주를 입력하세요.` : "";
}

form.addEventListener("input", renderOrder);
form.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-step], button[data-ratio]");
  if (!button || button.disabled) return;
  const { limit } = orderState();
  if (button.dataset.ratio) {
    quantity.value = Math.max(1, Math.floor(limit * Number(button.dataset.ratio)));
  } else {
    const next = (Number.isInteger(quantity.valueAsNumber) ? quantity.valueAsNumber : 0) + Number(button.dataset.dir);
    quantity.value = Math.min(Math.max(next, 1), Math.max(limit, 1));
  }
  renderOrder();
});
form.addEventListener("submit", (event) => {
  event.preventDefault();
  if (byId("preview-order").disabled || !form.checkValidity()) return;
  const { selling, unitPrice } = orderState();
  const how = `현재가 ${won(unitPrice)}`;
  byId("order-status").textContent = `${selected.name} ${number.format(quantity.valueAsNumber)}주 ${how} ${selling ? "매도" : "매수"} 미리보기`;
});

rangeButtons.forEach((button) => button.addEventListener("click", () => {
  rangeSize = Number(button.dataset.size);
  scrub = null;
  renderChart();
}));

const visible = () => rangeSize ? selected.candles.slice(-rangeSize) : selected.candles;
const firstIndex = () => selected.candles.length - visible().length;

function renderChart() {
  rangeButtons.forEach((button) => button.setAttribute("aria-pressed", Number(button.dataset.size) === rangeSize));
  const start = firstIndex();
  canvas.setAttribute("aria-label", `${selected.name} 턴별 시세. ${visible().map((candle, index) =>
    `${start + index + 1}턴 시가 ${won(candle.open)}, 고가 ${won(candle.high)}, 저가 ${won(candle.low)}, 종가 ${won(candle.close)}, 거래량 ${number.format(candle.volume)}주`).join(". ")}`);
  renderLegend();
  drawChart();
}

function renderLegend() {
  const index = firstIndex() + (scrub ?? visible().length - 1);
  const candle = selected.candles[index];
  const base = index > 0 ? selected.candles[index - 1].close : candle.open;
  const item = (label, value) => el("span", "", `${label} `, el("b", direction(value - base), number.format(value)));
  byId("chart-legend").replaceChildren(
    el("strong", "", `${index + 1}턴`),
    item("시", candle.open), item("고", candle.high), item("저", candle.low), item("종", candle.close),
    el("span", "", "거래량 ", el("b", "", number.format(candle.volume))));
}

function niceStep(raw) {
  const power = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 2.5, 5, 10].map((factor) => factor * power).find((step) => step >= raw);
}

function chartGeometry() {
  const { width, height } = canvas.getBoundingClientRect();
  const candles = visible();
  const left = 4, right = width - 64, top = 20;
  const priceBottom = Math.round(height * 0.72), volumeTop = priceBottom + 16, volumeBottom = height - 24;
  let min = Math.min(...candles.map((candle) => candle.low));
  let max = Math.max(...candles.map((candle) => candle.high));
  const pad = (max - min) * 0.12 || max * 0.01;
  min -= pad;
  max += pad;
  const maxVolume = Math.max(...candles.map((candle) => candle.volume));
  const slot = (right - left) / candles.length;
  return {
    width, height, candles, left, right, top, priceBottom, volumeTop, volumeBottom, min, max, slot,
    x: (index) => left + slot * (index + 0.5),
    y: (value) => priceBottom - (priceBottom - top) * (value - min) / (max - min),
    v: (volume) => volumeBottom - (volumeBottom - volumeTop) * volume / maxVolume,
  };
}

function drawChart() {
  const { width, height, candles, left, right, top, priceBottom, volumeTop, volumeBottom, min, max, slot, x, y, v } = chartGeometry();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.scale(ratio, ratio);
  const theme = getComputedStyle(canvas);
  const color = (name) => theme.getPropertyValue(name).trim();
  const up = color("--up-solid"), down = color("--down-solid"), muted = color("--muted"), line = color("--line"), ink = color("--ink");
  ctx.textBaseline = "middle";
  ctx.lineWidth = 1;

  if (scrub !== null) {
    ctx.fillStyle = color("--surface");
    ctx.fillRect(x(scrub) - slot / 2, top - 12, slot, volumeBottom - top + 12);
  }

  ctx.font = "11px system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.strokeStyle = line;
  ctx.fillStyle = muted;
  const step = niceStep((max - min) / 6);
  for (let level = Math.ceil(min / step) * step; level <= max; level += step) {
    const ly = Math.round(y(level)) + 0.5;
    ctx.beginPath();
    ctx.moveTo(left, ly);
    ctx.lineTo(right, ly);
    ctx.stroke();
    ctx.fillText(number.format(level), right + 8, ly);
  }
  ctx.beginPath();
  ctx.moveTo(left, volumeTop - 7.5);
  ctx.lineTo(right, volumeTop - 7.5);
  ctx.stroke();
  ctx.fillText("거래량", right + 8, volumeTop + 4);

  const body = Math.max(3, Math.min(slot * 0.56, 26));
  candles.forEach((candle, index) => {
    const tone = candle.close >= candle.open ? up : down;
    const cx = Math.round(x(index)) + 0.5;
    ctx.strokeStyle = ctx.fillStyle = tone;
    ctx.beginPath();
    ctx.moveTo(cx, y(candle.high));
    ctx.lineTo(cx, y(candle.low));
    ctx.stroke();
    const bodyTop = y(Math.max(candle.open, candle.close));
    ctx.fillRect(x(index) - body / 2, bodyTop, body, Math.max(1, y(Math.min(candle.open, candle.close)) - bodyTop));
    ctx.globalAlpha = 0.45;
    ctx.fillRect(x(index) - body / 2, v(candle.volume), body, volumeBottom - v(candle.volume));
    ctx.globalAlpha = 1;
  });

  ctx.font = "600 11px system-ui, sans-serif";
  const highest = candles.reduce((best, candle, index) => candle.high > candles[best].high ? index : best, 0);
  const lowest = candles.reduce((best, candle, index) => candle.low < candles[best].low ? index : best, 0);
  const mark = (index, label, value, tone, offset) => {
    ctx.fillStyle = tone;
    ctx.textAlign = x(index) > (left + right) / 2 ? "right" : "left";
    ctx.fillText(`${label} ${number.format(value)}`, x(index), y(value) + offset);
  };
  mark(highest, "최고", candles[highest].high, up, -10);
  mark(lowest, "최저", candles[lowest].low, down, 10);

  const current = price(selected);
  const change = current - previousClose(selected);
  const tag = change > 0 ? up : change < 0 ? down : ink;
  const cy = Math.round(y(current)) + 0.5;
  ctx.strokeStyle = tag;
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(left, cy);
  ctx.lineTo(right, cy);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = tag;
  ctx.beginPath();
  ctx.roundRect(right + 2, cy - 10, width - right - 2, 20, 4);
  ctx.fill();
  ctx.fillStyle = change === 0 ? color("--panel") : "#fff";
  ctx.textAlign = "left";
  ctx.fillText(number.format(current), right + 7, cy);

  if (scrub !== null) {
    ctx.strokeStyle = muted;
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    ctx.moveTo(Math.round(x(scrub)) + 0.5, top - 12);
    ctx.lineTo(Math.round(x(scrub)) + 0.5, volumeBottom);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  ctx.font = "11px system-ui, sans-serif";
  ctx.fillStyle = muted;
  ctx.textAlign = "center";
  const start = firstIndex();
  candles.forEach((_, index) => {
    if (slot >= 34 || index % 2 === (candles.length - 1) % 2) {
      ctx.fillText(`${start + index + 1}턴`, x(index), height - 9);
    }
  });
}

function scrubTo(event) {
  const { candles, left, slot } = chartGeometry();
  const offset = event.clientX - canvas.getBoundingClientRect().left;
  const index = Math.min(Math.max(Math.floor((offset - left) / slot), 0), candles.length - 1);
  if (index === scrub) return;
  scrub = index;
  renderLegend();
  drawChart();
}

function endScrub() {
  if (scrub === null) return;
  scrub = null;
  renderLegend();
  drawChart();
}

canvas.addEventListener("pointermove", scrubTo);
canvas.addEventListener("pointerdown", scrubTo);
canvas.addEventListener("pointerleave", endScrub);
canvas.addEventListener("pointercancel", endScrub);
canvas.addEventListener("pointerup", (event) => { if (event.pointerType !== "mouse") endScrub(); });

renderSelection();
new ResizeObserver(drawChart).observe(canvas);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", drawChart);
