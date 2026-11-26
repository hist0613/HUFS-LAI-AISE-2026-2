// 시드(seed)를 주면 항상 같은 순서의 난수를 만드는 생성기(mulberry32).
// 테스트와 시연을 똑같이 재현할 수 있게 Math.random 대신 쓴다.
export function createRandom(seed) {
  let state = seed >>> 0;
  const next = () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
  return {
    next,
    between: (min, max) => min + (max - min) * next(),
    // 평균 0, 표준편차 1인 정규분포 (Box-Muller)
    normal: () => Math.sqrt(-2 * Math.log(1 - next())) * Math.cos(2 * Math.PI * next()),
  };
}
