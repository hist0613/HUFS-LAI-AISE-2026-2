#!/usr/bin/env python3
"""A tiny rainbow star theatre. Try --static --seed 7 for a still frame."""

import argparse
import colorsys
import math
import os
import random
import shutil
import sys
import time

ESC = "\x1b["
RESET = ESC + "0m"
FPS, DURATION = 20, 10.0


def paint(hue, brightness=1.0):
    red, green, blue = colorsys.hsv_to_rgb(hue % 1, 0.8, brightness)
    return f"{ESC}38;2;{int(red * 255)};{int(green * 255)};{int(blue * 255)}m"


def put(canvas, x, y, hue, brightness=1.0):
    if 0 <= y < len(canvas) and 0 <= x < len(canvas[0]):
        canvas[y][x] = (hue, brightness)


def twinkle(canvas, stars, tick):
    for x, y, phase, hue in stars:
        glow = (1 + math.sin(tick * 4 + phase)) / 2
        if glow > 0.25:
            put(canvas, x, y, hue + tick * 0.03, 0.15 + glow * 0.45)


def scene_diamond(canvas, size, tick):
    """A filled classic diamond with moving rainbow bands."""
    cx, cy = len(canvas[0]) // 2, len(canvas) // 2
    for dy in range(-size, size + 1):
        reach = size - abs(dy)
        for dx in range(-reach * 2, reach * 2 + 1, 2):
            hue = (dx + dy * 2) / (size * 6) + tick * 0.16
            put(canvas, cx + dx, cy + dy, hue)


def scene_pyramid(canvas, size, tick):
    """A rainbow pyramid above its rippling, dimmer reflection."""
    cx, cy = len(canvas[0]) // 2, len(canvas) // 2
    for row in range(size + 1):
        for dx in range(-row * 2, row * 2 + 1, 2):
            hue = row / (size + 1) + dx / (size * 8) + tick * 0.12
            put(canvas, cx + dx, cy - size + row, hue)
            if row < size:
                ripple = round(math.sin(tick * 3 + row * 0.7))
                put(canvas, cx + dx + ripple, cy + size - row, hue, 0.4)


def scene_heart(canvas, size, tick):
    """A beating heart cut out by (x^2 + y^2 - 1)^3 - x^2 y^3 <= 0."""
    cx, cy = len(canvas[0]) // 2, len(canvas) // 2
    beat = 1 + 0.12 * max(0.0, math.sin(tick * 7)) ** 8
    for y in range(len(canvas)):
        for x in range(cx % 2, len(canvas[0]), 2):
            u = (x - cx) / (2 * size) * 1.2 / beat
            v = (cy - y) / size * 1.2 / beat + 0.1
            if (u * u + v * v - 1) ** 3 - u * u * v ** 3 <= 0:
                depth = 1 - min(1.0, math.hypot(u, v - 0.2))
                put(canvas, x, y, 0.95 + 0.06 * depth + 0.02 * math.sin(tick * 3), 0.65 + 0.35 * depth)


def scene_fireworks(canvas, size, tick):
    """Three bursts at different stages, each ray dragging a fading tail."""
    cx, cy = len(canvas[0]) // 2, len(canvas) // 2
    bursts = [(cx, cy, 0.62, 0.0), (cx - size * 3 // 2, cy - size // 2, 0.38, 0.33),
              (cx + size * 3 // 2, cy + size // 3, 0.14, 0.66)]
    for bx, by, phase, hue in bursts:
        life = (tick / 1.6 + phase) % 1
        fade = 1 - life ** 3
        put(canvas, bx, by, hue, fade)
        for ray in range(12):
            angle = ray * math.tau / 12 + phase
            for tail in range(3):
                r = life * size * 0.8 - tail * 0.8
                if r > 0:
                    put(canvas, bx + round(math.cos(angle) * r * 2), by + round(math.sin(angle) * r),
                        hue + ray / 96, fade * (1 - tail * 0.3))


SCENES = [("RAINBOW DIAMOND", scene_diamond), ("MIRROR PYRAMID", scene_pyramid),
          ("BEATING HEART", scene_heart), ("FIREWORKS", scene_fireworks)]
SCENE_KEYS = [scene.__name__.removeprefix("scene_") for _, scene in SCENES]


def make_stars(width, height, rng):
    # Even columns only, so the background shares the scenes' two-column star grid.
    return [(rng.randrange(0, width, 2), rng.randrange(height),
             rng.random() * math.tau, rng.random())
            for _ in range(width * height // 12)]


def render(size, stars, tick, scene_index, color):
    width, height = 4 * size + 9, 2 * size + 3
    canvas = [[None] * width for _ in range(height)]
    title, scene = SCENES[scene_index]
    twinkle(canvas, stars, tick)
    scene(canvas, size, tick)
    lines = [f" {title} ".center(width, "=")]
    for row in canvas:
        line = ""
        for cell in row:
            if cell is None:
                line += " "
            else:
                line += (paint(*cell) + "*" + RESET) if color else "*"
        lines.append(line)
    lines.append(" * STAR THEATRE * ".center(width, "="))
    return "\n".join(lines)


def size_value(value):
    size = int(value)
    if not 2 <= size <= 30:
        raise argparse.ArgumentTypeError("size must be between 2 and 30")
    return size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true", help="print one still frame")
    parser.add_argument("--seed", type=int, help="reproducible background seed")
    parser.add_argument("--size", type=size_value, default=7, help="star size: 2..30")
    parser.add_argument("--scene", choices=SCENE_KEYS, help="show only this scene")
    args = parser.parse_args()
    order = [SCENE_KEYS.index(args.scene)] if args.scene else list(range(len(SCENES)))
    tty = sys.stdout.isatty()
    # FORCE_COLOR keeps colors when piping (e.g. into a screenshot tool).
    color = (tty or "FORCE_COLOR" in os.environ) and "NO_COLOR" not in os.environ
    animate = tty and not args.static
    size = args.size
    if animate:
        columns, rows = shutil.get_terminal_size((80, 24))
        # Leave a spare column and row to avoid terminal autowrap/scrolling.
        size = min(size, (columns - 10) // 4, (rows - 6) // 2)
        if size < 2:
            animate, size = False, args.size
    stars = make_stars(4 * size + 9, 2 * size + 3, random.Random(args.seed))
    try:
        if not animate:
            print(render(size, stars, 0.0, order[0], color))
            return
        sys.stdout.write(ESC + "?1049h" + ESC + "?25l" + ESC + "2J")
        start = time.monotonic()
        for frame in range(int(FPS * DURATION)):
            tick = time.monotonic() - start
            if tick >= DURATION:
                break
            index = order[min(int(tick / DURATION * len(order)), len(order) - 1)]
            sys.stdout.write(ESC + "H" + render(size, stars, tick, index, color))
            sys.stdout.flush()
            time.sleep(max(0, start + (frame + 1) / FPS - time.monotonic()))
    except KeyboardInterrupt:
        pass
    finally:
        if tty:
            sys.stdout.write(RESET + ESC + "?25h" + (ESC + "?1049l" if animate else ""))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
