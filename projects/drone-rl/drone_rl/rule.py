"""장면 요약을 보고 행동을 고르는 규칙 기반 판단."""

CLEAR_M = 3.0  # 앞길이 이보다 짧으면 피한다
LOST_AFTER_S = 2.0  # 타깃이 이보다 오래 안 보이면 놓쳤다고 본다


def rule(obs):
    """행동 이름, 위험도(0~1), 타깃을 놓쳤는지를 돌려준다."""
    target = obs["target"]
    lost = not target["visible"] and target["unseen_for_s"] >= LOST_AFTER_S
    risk = round(max(0.0, 1 - obs["nearest_obstacle_m"] / CLEAR_M), 2)

    if obs["path_ahead_m"] < CLEAR_M:
        sides = obs["sector_range_m"]
        if obs["sectors_blocked"] >= 4:
            # 좌우 끝까지 막힌 가로 빔은 옆으로 돌아갈 수 없으니 위로 넘는다.
            mv = "climb" if obs["free_ahead_above_m"] >= CLEAR_M else "brake"
        elif sides["left"] >= sides["right"]:
            mv = "gap_left"
        else:
            mv = "gap_right"
    elif lost:
        mv = "reacquire"
    else:
        mv = "hold_course"
    return mv, risk, lost
