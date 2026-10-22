import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 1

star = [
    "       *",
    "      ***",
    "*   *******   *",
    " ************",
    "   ********",
    "    **   ***",
    "   **      **",
    "  *          *"
]

for line in star:
    scaled = "".join(c * n for c in line)
    for _ in range(n):
        print(scaled)
