n = 6
width = 4 * n + 1
center = width // 2

for i in range(2 * n + 1):
    line = ""

    for j in range(width):
        star = False

        # 위쪽 삼각형
        if i < n - 1:
            if abs(j - center) <= 2 * (i // 2):
                if (j - center) % 2 == 0:
                    star = True

        # 가운데 가로 부분
        elif i == n - 1:
            if j % 2 == 0:
                star = True

        # 아래쪽 몸통
        elif i < n + 3:
            k = i - n + 1
            if 2 * k <= j <= width - 1 - 2 * k:
                if j % 2 == 0:
                    star = True

        # 아래쪽 두 다리
        else:
            k = i - (n + 3)
            left = 6 - 2 * k
            right = width - 1 - left

            if left <= j <= left + 4:
                if j % 2 == 0:
                    star = True

            if right - 4 <= j <= right:
                if j % 2 == 0:
                    star = True

        line += "*" if star else " "

    print(line.rstrip())