def sierpinski(n):
    """높이 n 짜리 시에르핀스키 삼각형을 줄 단위 문자열 리스트로 만든다. n = 3 * 2^k."""
    if n == 3:
        return [
            "  *  ",
            " * * ",
            "*****",
        ]

    half = sierpinski(n // 2)
    pad = " " * (n // 2)
    top = [pad + line + pad for line in half]
    bottom = [line + " " + line for line in half]
    return top + bottom


def is_valid_size(n):
    if n < 3 or n % 3 != 0:
        return False
    k = n // 3
    return k & (k - 1) == 0


n = int(input("n (3, 6, 12, 24, ...): "))

if not is_valid_size(n):
    print("n 은 3 * 2^k 꼴이어야 합니다. (3, 6, 12, 24, 48, ...)")
else:
    for line in sierpinski(n):
        print(line)
