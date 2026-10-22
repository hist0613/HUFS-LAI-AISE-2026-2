"""STAR THEATER - animated star printing for student 202002112.

Requires Python 3.10+; no external dependencies.
Run: python print-star-202002112.py
Still frame: python print-star-202002112.py --mode heart --snapshot
Scenes: galaxy, heart, fireworks, tree. Ctrl+C exits animation.
"""
from __future__ import annotations

import argparse
import colorsys
import ctypes
import math
import os
import random
import shutil
import sys
import time

TAU = math.tau
MODES = ("galaxy", "heart", "fireworks", "tree")
LABELS = {"galaxy": "SPIRAL GALAXY", "heart": "COSMIC HEART",
          "fireworks": "STARDUST FIREWORKS", "tree": "THE WISHING TREE"}
RESET = "\033[0m"


class Canvas:
    def __init__(self, width: int, height: int):
        self.width, self.height = width, height
        self.cells: dict[tuple[int, int], tuple[str, float, float]] = {}

    def point(self, x: float, y: float, char="*", hue=0.55, light=1.0):
        # Terminal characters are roughly twice as tall as they are wide.
        col = round(self.width / 2 + x * self.height * 2)
        row = round(self.height / 2 - y * self.height)
        if 0 <= col < self.width and 0 <= row < self.height:
            old = self.cells.get((col, row))
            if old is None or old[2] <= light:
                self.cells[col, row] = (char, hue % 1, light)

    def render(self, color: bool) -> str:
        lines = []
        for row in range(self.height):
            line = []
            for col in range(self.width):
                cell = self.cells.get((col, row))
                if cell is None:
                    line.append(" ")
                    continue
                char, hue, light = cell
                if color:
                    rgb = colorsys.hsv_to_rgb(hue, 0.55, min(1, max(0, light)))
                    r, g, b = (round(c * 255) for c in rgb)
                    line.append(f"\033[38;2;{r};{g};{b}m{char}")
                else:
                    line.append(char)
            lines.append("".join(line) + (RESET if color else ""))
        return "\n".join(lines)


def scene(mode: str, t: float, width: int, height: int) -> Canvas:
    canvas = Canvas(width, height)
    rng = random.Random(2026)
    # Fixed seed keeps stars anchored while brightness changes over time.
    for _ in range(width * height // 38):
        x, y = rng.uniform(-1.8, 1.8), rng.uniform(-0.49, 0.49)
        phase = rng.random() * TAU
        glow = 0.25 + 0.35 * (0.5 + 0.5 * math.sin(t * 2 + phase))
        canvas.point(x, y, "." if glow < 0.48 else "+", 0.62, glow)

    if mode == "galaxy":
        for _ in range(1600):
            radius = rng.random() ** 0.7 * 0.48
            arm = rng.randrange(4)
            angle = arm * TAU / 4 + radius * 12 + t * 0.32
            angle += rng.gauss(0, 0.15)
            x, y = math.cos(angle) * radius, math.sin(angle) * radius
            canvas.point(x * 1.42, y * 0.75, rng.choice(".*+*"),
                         0.48 + radius * 0.65 + t * 0.015,
                         0.5 + (1 - radius / 0.48) * 0.5)
        canvas.point(0, 0, "@", 0.12, 1)
    elif mode == "heart":
        beat = 1 + 0.055 * math.sin(t * 3) ** 7
        for _ in range(1700):
            a = rng.random() * TAU
            fill = rng.random() ** 0.3
            x = 16 * math.sin(a) ** 3
            y = 13 * math.cos(a) - 5 * math.cos(2*a) - 2 * math.cos(3*a) - math.cos(4*a)
            canvas.point(x / 42 * fill * beat, (y / 42 * fill + 0.04) * beat,
                         "*" if fill > 0.9 else rng.choice(".+*"),
                         0.88 + fill * 0.12 + 0.02 * math.sin(t), 0.45 + fill * 0.55)
    elif mode == "fireworks":
        for burst in range(6):
            local = t * 0.65 + burst * 0.53
            cycle, age = int(local / 2.8), local % 2.8
            burst_rng = random.Random(burst * 7919 + cycle * 101)
            cx, cy = burst_rng.uniform(-0.65, 0.65), burst_rng.uniform(-0.02, 0.28)
            hue = burst_rng.random()
            if age < 0.65:
                y = -0.5 + (cy + 0.5) * age / 0.65
                for trail in range(5):
                    canvas.point(cx, y - trail * 0.025, "*", 0.12, 1 - trail * 0.14)
            else:
                elapsed = age - 0.65
                for particle in range(85):
                    angle = particle * TAU / 85
                    speed = burst_rng.uniform(0.12, 0.32)
                    for trail in range(3):
                        dt = max(0, elapsed - trail * 0.045)
                        x = cx + math.cos(angle) * speed * dt
                        y = cy + math.sin(angle) * speed * dt - 0.12 * dt * dt
                        canvas.point(x, y, "*" if elapsed < 1 else ".", hue,
                                     max(0.1, 1 - elapsed / 2.3 - trail * 0.12))
    elif mode == "tree":
        for row in range(24):
            y = 0.37 - row * 0.03
            half = 0.025 + row * 0.017
            for col in range(-row, row + 1):
                x = col / max(1, row) * half
                ornament = (row * 13 + col * 7) % 11 == 0
                hue = (t * 0.12 + row * 0.05) % 1 if ornament else 0.38
                canvas.point(x, y, "*", hue, 0.95 if ornament else 0.55)
        for i in range(5):
            canvas.point(0, -0.35 - i * 0.02, "|", 0.08, 0.8)
        canvas.point(0, 0.43, "*", 0.13, 1)
        for i in range(45):
            x = rng.uniform(-0.9, 0.9)
            y = 0.5 - ((rng.random() + t * 0.07) % 1)
            canvas.point(x, y, ".", 0.55, 0.8)
    else:
        raise ValueError(f"Unknown scene: {mode}")
    return canvas


def enable_ansi() -> bool:
    if os.name != "nt":
        return True
    kernel = ctypes.windll.kernel32
    handle = kernel.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    return bool(kernel.GetConsoleMode(handle, ctypes.byref(mode)) and
                kernel.SetConsoleMode(handle, mode.value | 0x0004))


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description="STAR THEATER | Animated ASCII constellations")
    parser.add_argument("--mode", choices=(*MODES, "show"), default="show")
    parser.add_argument("--snapshot", action="store_true", help="print one still frame")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--fps", type=positive_int, default=24)
    parser.add_argument("--frames", type=positive_int, help="stop after N frames")
    parser.add_argument("--width", type=positive_int, help="canvas width (max 160)")
    parser.add_argument("--height", type=positive_int, help="canvas height (max 55)")
    args = parser.parse_args()
    terminal = sys.stdout.isatty()
    ansi = terminal and enable_ansi()
    still = args.snapshot or not ansi
    color = ansi and not args.no_color and "NO_COLOR" not in os.environ
    started = time.monotonic()
    frame = 0
    try:
        if not still:
            sys.stdout.write("\033[?1049h\033[?25l")
        while True:
            tick = time.monotonic()
            t = 1.8 if still else tick - started
            mode = MODES[int(t / 12) % len(MODES)] if args.mode == "show" else args.mode
            columns, rows = shutil.get_terminal_size((100, 36))
            width = max(1, min(args.width or 100, 160, columns - 1 if terminal else 160))
            height = max(1, min(args.height or 30, 55, rows - 5 if terminal else 55))
            title = f"*  STAR THEATER  /  {LABELS[mode]}  *"[:width].center(width)
            footer = ("Ctrl+C : exit  |  " + ("New scene every 12s" if args.mode == "show" else mode))[:width]
            body = scene(mode, t, width, height).render(color)
            prefix = "\033[H\033[J" if not still else ""
            sys.stdout.write(f"{prefix}{title}\n{'-' * width}\n{body}\n{footer}\n")
            sys.stdout.flush()
            frame += 1
            if still or (args.frames and frame >= args.frames):
                break
            time.sleep(max(0, 1 / min(args.fps, 60) - (time.monotonic() - tick)))
    except KeyboardInterrupt:
        pass
    finally:
        if not still:
            sys.stdout.write(RESET + "\033[?25h\033[?1049l")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
