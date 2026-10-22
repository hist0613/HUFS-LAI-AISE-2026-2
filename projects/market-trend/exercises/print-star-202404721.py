"""A colorful shooting-star show for the terminal (standard library only)."""

import math
import os
import random
import shutil
import sys
import time

# ANSI 256-color codes: silver, blue, purple, pink, gold, and orange.
SKY_COLORS = (250, 117, 141, 213)
STAR_COLORS = (226, 220, 214, 208)


def paint(symbol, color, enabled):
    """Add terminal color when ANSI output is supported."""
    return f"\033[38;5;{color}m{symbol}\033[0m" if enabled else symbol


def star_vertices(center_x, center_y, radius):
    """Return the 10 alternating outer/inner corners of a five-pointed star."""
    vertices = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.43
        vertices.append((center_x + 2 * r * math.cos(angle),
                         center_y + r * math.sin(angle)))
    return vertices


def inside_polygon(x, y, vertices):
    """Check whether a point is inside the star using ray casting."""
    inside = False
    for i, (x1, y1) in enumerate(vertices):
        x2, y2 = vertices[(i + 1) % len(vertices)]
        if (y1 > y) != (y2 > y):
            crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossing_x:
                inside = not inside
    return inside


def draw_frame(width, height, frame, background, colored):
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    colors = [[None for _ in range(width)] for _ in range(height)]

    # Small stars flicker at different speeds.
    for x, y, phase in background:
        if (frame + phase) % 7 in (0, 1, 2):
            canvas[y][x] = "+"
            colors[y][x] = SKY_COLORS[phase % len(SKY_COLORS)]
        else:
            canvas[y][x] = "."
            colors[y][x] = 250

    # Draw a shooting star and its fading trail.
    head_x = frame * 2 - 12
    head_y = 2 + frame // 5
    for tail in range(7, -1, -1):
        x = head_x - tail
        y = head_y - tail // 3
        if 0 <= x < width and 0 <= y < height:
            canvas[y][x] = "*" if tail == 0 else ("+" if tail < 4 else ".")
            colors[y][x] = 231 if tail == 0 else 123

    # Fill the five-pointed star with a warm color gradient.
    center_x, center_y = width // 2, height // 2
    vertices = star_vertices(center_x, center_y, min(height * 0.42, width / 4))
    for y in range(height):
        for x in range(width):
            if inside_polygon(x + 0.5, y + 0.5, vertices):
                canvas[y][x] = "*"
                colors[y][x] = STAR_COLORS[(y // 3 + frame // 5) % len(STAR_COLORS)]

    lines = []
    for y in range(height):
        lines.append("".join(
            paint(canvas[y][x], colors[y][x], colored)
            if colors[y][x] is not None else " "
            for x in range(width)
        ))
    return "\n".join(lines)


def main():
    terminal = shutil.get_terminal_size((80, 24))
    width = max(25, min(68, terminal.columns - 2))
    height = max(12, min(20, terminal.lines - 5))
    animated = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    colored = animated

    rng = random.Random(42)  # Same sky, different twinkles each frame.
    background = [
        (rng.randrange(width), rng.randrange(height), rng.randrange(100))
        for _ in range(width * height // 20)
    ]

    if animated:
        print("\033[?25l", end="")  # Hide the cursor while animating.

    try:
        total_frames = 40 if animated else 1
        for frame in range(total_frames):
            if animated:
                print("\033[H\033[J", end="")  # Refresh in place.
            print("*" * width)
            print("MAKE A WISH".center(width))
            print(draw_frame(width, height, frame if animated else 18,
                             background, colored))
            print("*" * width, flush=True)
            if animated:
                time.sleep(0.08)
    finally:
        if animated:
            print("\033[0m\033[?25h")  # Restore colors and cursor.


if __name__ == "__main__":
    main()
