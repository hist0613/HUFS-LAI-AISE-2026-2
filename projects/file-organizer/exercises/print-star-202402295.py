import math
import time

W, H = 80, 30
symbols = ".,-~:;=!*#$@"

a = 0
b = 0

try:
    while True:
        screen = [" "] * (W * H)
        depth = [float("inf")] * (W * H)

        for i in range(0, 628, 10):
            for j in range(0, 628, 14):
                u = i / 100
                v = j / 100

                # 도넛의 3D 좌표
                x = (2 + math.cos(v)) * math.cos(u)
                y = (2 + math.cos(v)) * math.sin(u)
                z = math.sin(v)

                # X축 회전
                y, z = (
                    y * math.cos(a) - z * math.sin(a),
                    y * math.sin(a) + z * math.cos(a)
                )

                # Y축 회전
                x, z = (
                    x * math.cos(b) + z * math.sin(b),
                    -x * math.sin(b) + z * math.cos(b)
                )

                # 3D -> 2D 투영
                d = z + 6
                px = int(W / 2 + x * 30 / d)
                py = int(H / 2 - y * 16 / d)

                if 0 <= px < W and 0 <= py < H:
                    idx = py * W + px

                    if d < depth[idx]:
                        depth[idx] = d
                        shade = int((3 - z) / 6 * len(symbols))
                        shade = max(0, min(shade, len(symbols) - 1))
                        screen[idx] = symbols[shade]

        print("\033[H\033[J", end="")
        for row in range(H):
            print("".join(screen[row * W:(row + 1) * W]))

        a += 0.06
        b += 0.03
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\n애니메이션 종료!")
