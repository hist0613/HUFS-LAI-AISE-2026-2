// 한국거래소 호가 단위. ui/app.mjs의 tick()과 같은 규칙이다.
export function tickSize(price) {
  if (price < 2_000) return 1;
  if (price < 5_000) return 5;
  if (price < 20_000) return 10;
  if (price < 50_000) return 50;
  if (price < 200_000) return 100;
  if (price < 500_000) return 500;
  return 1_000;
}

// 가장 가까운 호가 단위 가격으로 맞춘다. 최저 1원.
// 구간 경계(2,000·5,000·20,000…)는 위 구간 단위의 배수라서 경계를 넘어도 호가에 맞는다.
export function roundToTick(price) {
  const tick = tickSize(price);
  return Math.max(1, Math.round(price / tick) * tick);
}

// 화면의 지정가 검사와 같은 조건
export function isOnTick(price) {
  return Number.isSafeInteger(price) && price > 0 && price % tickSize(price) === 0;
}
