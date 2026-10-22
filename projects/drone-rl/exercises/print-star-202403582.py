import colorsys
import math
import os
import random
import shutil
import sys
import time

SPIN = 9.0  # 프로펠러 회전 속도 (rad/s)
STAR_CHARS = {0.6: ".", 1.5: "+", 3.0: "*"}  # 배경 별: 멀수록 느리고 흐리다


def rotors(n):
    """로터 4개의 중심 (x, y)와 회전 방향. 대각선끼리 같은 방향, 이웃끼리 반대 방향으로 돈다."""
    d = 5 * n // 2
    return [(-d, -d, 1), (d, -d, -1), (-d, d, -1), (d, d, 1)]


def near_line(dx, dy, angle):
    """점 (dx, dy)가 원점을 지나는 angle 방향 직선 위에 있는지."""
    return abs(dy * math.cos(angle) - dx * math.sin(angle)) < 0.55


def part_at(x, y, n, props, t):
    """좌표 (x, y)가 드론의 어느 부위인지 돌려준다. 빈 곳이면 None."""
    for rx, ry, spin in props:
        dx, dy = x - rx, y - ry
        dist = math.hypot(dx, dy)
        if abs(dist - n) < 0.5:
            outward = (dx * rx + dy * ry) / (dist * math.hypot(rx, ry))
            if outward > 0.9:
                return "nav_rear" if ry > 0 else ("nav_fl" if rx < 0 else "nav_fr")
            return "ring"
        if dist < n - 0.5:
            angle = spin * (SPIN * t + 0.5)
            if dist < 0.7 or near_line(dx, dy, angle):
                return "blade"
            if near_line(dx, dy, angle - spin * 0.35):
                return "trail"
            return "disc"

    body = 0.6 * n
    if abs(x) + abs(y) <= 0.25 * body + 0.5:
        return "led"
    if abs(x) <= body and abs(y) <= body and abs(x) + abs(y) <= 1.5 * body:
        return "body"
    if abs(abs(x) - abs(y)) < 0.6 and max(abs(x), abs(y)) < abs(props[0][0]):
        return "arm"
    return None


def draw_drone(n, t):
    """로터 반지름이 n 인 드론을 격자로 그린다. 칸마다 부위 이름이 들어간다."""
    props = rotors(n)
    half = abs(props[0][0]) + n
    grid = []
    for row in range(2 * half + 1):
        y = row - half
        # 글자는 세로로 길쭉해서 가로 좌표를 반으로 줄여야 원이 둥글게 보인다
        grid.append([part_at((col - 2 * half) / 2, y, n, props, t) for col in range(4 * half + 1)])
    return grid


def render_plain(grid):
    """색 없이 * 와 공백만으로 찍는다."""
    return ["".join(" " if kind in (None, "trail", "disc") else "*" for kind in line).rstrip() for line in grid]


def hsv(h, s, v):
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1, s, v))


def color_of(kind, row, col, h, w, t):
    """부위와 시간에 따라 색 (r, g, b)를 정한다."""
    if kind == "ring":
        return hsv((col / w + row / h) * 0.5 + t * 0.25, 0.75, 1)
    if kind == "blade":
        return (255, 250, 200)
    if kind == "trail":
        return (90, 90, 120)
    if kind == "arm":
        k = 0.55 + 0.45 * (0.5 + 0.5 * math.sin((col + row * 2) * 0.3 - t * 6))
        return (int(170 * k), int(175 * k), int(195 * k))
    if kind == "body":
        return hsv(0.8 + 0.08 * math.sin(t * 1.5 + (row + col * 0.5) * 0.4), 0.7, 1)
    if kind == "led":
        k = 0.5 + 0.5 * math.sin(t * 5)
        return (int(60 * k), int(140 + 115 * k), 255)
    if kind == "nav_fl":
        return (255, 50, 50)
    if kind == "nav_fr":
        return (50, 255, 90)
    return (255, 255, 255) if (t * 1.5) % 1 < 0.12 else (80, 80, 80)


def paint(rgb, ch):
    return "\x1b[38;2;%d;%d;%dm%s" % (*rgb, ch)


def render_color(grid, t, stars, cols, rows):
    """별이 흘러가는 밤하늘 위에 흔들리며 떠 있는 드론 한 프레임을 만든다."""
    h, w = len(grid), len(grid[0])
    top = (rows - h) // 2 - round(math.sin(t * 2))
    left = (cols - w) // 2 + round(math.sin(t * 0.7) * 3)
    sky = {}
    for x, y, speed, phase in stars:
        sky[(int(y + speed * t) % rows, x)] = (speed, phase)

    lines = []
    for r in range(rows):
        line = []
        for c in range(cols):
            gr, gc = r - top, c - left
            kind = grid[gr][gc] if 0 <= gr < h and 0 <= gc < w else None
            if kind == "disc":
                line.append(" ")  # 프로펠러가 도는 원 안쪽은 배경 별을 가린다
            elif kind:
                line.append(paint(color_of(kind, gr, gc, h, w, t), "*"))
            elif (r, c) in sky:
                speed, phase = sky[(r, c)]
                k = speed / 3 * (0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 3 + phase)))
                line.append(paint((int(210 * k), int(220 * k), int(255 * k)), STAR_CHARS[speed]))
            else:
                line.append(" ")
        lines.append("".join(line) + "\x1b[0m")
    return "\n".join(lines)


def hud(n, t):
    """맨 아래 계기판 한 줄."""
    battery = max(0, 100 - int(t / 3))
    bar = paint(hsv(battery / 300, 0.9, 1), "#" * (battery // 10)) + paint((70, 70, 70), "-" * (10 - battery // 10))
    alt = 12 + math.sin(t * 2) * 0.4
    rpm = 9600 + int(200 * math.sin(t * 7))
    info = paint((0, 220, 255), " DRONE-RL n=%d  ALT %4.1fm  RPM %d  BATT [" % (n, alt, rpm))
    return info + bar + paint((0, 220, 255), "] %3d%%" % battery) + paint((140, 140, 160), "  Ctrl+C 로 종료\x1b[0m\x1b[K")


def animate(n):
    """Ctrl+C 를 누를 때까지 드론을 띄운다."""
    cols, rows = shutil.get_terminal_size()
    rows -= 1
    grid = draw_drone(n, 0)
    h, w = len(grid), len(grid[0])
    if cols < max(w + 8, 80) or rows < h + 2:
        print("터미널이 작습니다. 최소 %dx%d 가 필요합니다. 창을 키우거나 n 을 줄여 주세요." % (max(w + 8, 80), h + 3))
        return
    if os.name == "nt":
        os.system("")  # Windows 콘솔에서 ANSI 색을 켠다

    stars = [(random.randrange(cols), random.uniform(0, rows), random.choice(list(STAR_CHARS)), random.uniform(0, 6.3))
             for _ in range(cols * rows // 30)]
    sys.stdout.write("\x1b[?1049h\x1b[?25l")
    start = time.perf_counter()
    try:
        while True:
            t = time.perf_counter() - start
            sys.stdout.write("\x1b[H" + render_color(draw_drone(n, t), t, stars, cols, rows) + "\n" + hud(n, t))
            sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
    print("\n".join(render_plain(grid)))
    print("착륙 완료!")


try:
    n = int(input("드론 크기 n (2~8): " if sys.stdin.isatty() else ""))
except (ValueError, EOFError):
    n = 0

if not 2 <= n <= 8:
    print("n 은 2 이상 8 이하의 정수여야 합니다.")
elif sys.stdout.isatty():
    animate(n)
else:
    print("\n".join(render_plain(draw_drone(n, 0))))
