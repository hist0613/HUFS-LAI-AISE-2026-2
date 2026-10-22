# 소용돌이(나선 은하) 별찍기: 극좌표로 나선 팔 위의 점에만 별을 찍기
import math

SIZE = 25
for row in range(-SIZE, SIZE + 1):
    line = ""
    for col in range(-SIZE * 2, SIZE * 2 + 1):
        x = col / 2               # 글자는 세로로 길쭉해서 가로를 절반으로
        y = row
        r = math.hypot(x, y)      # 중심에서의 거리
        angle = math.atan2(y, x)  # 중심 기준 각도
        # 거리와 각도를 섞어서 2개의 나선 팔을 만든다
        arm = math.sin(2 * angle - r * 0.35)
        if r < 3:
            line += "@"           # 은하 중심
        elif r <= SIZE and arm > 0.6:
            line += "*"
        else:
            line += " "
    print(line)
