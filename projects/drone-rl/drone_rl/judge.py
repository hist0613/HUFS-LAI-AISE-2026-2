"""Laya에게 장면 요약을 보여 주고 행동, 위험도, 타깃을 놓쳤는지 묻는다."""

QUESTIONS = {
    "maneuver": {
        "type": "choice",
        "instructions": "A quadrotor is chasing a ground rover past beams and pillars. "
                        "Which maneuver should it take now?",
        "criteria": {
            "hold_course": "Keep flying toward the rover; the way ahead is open.",
            "gap_left": "Steer left around an obstacle that blocks the front.",
            "gap_right": "Steer right around an obstacle that blocks the front.",
            "climb": "Fly up over an obstacle that blocks the whole width.",
            "brake": "Slow down and stop; there is no way through.",
            "reacquire": "Search for the rover after losing sight of it.",
        },
    },
    "risk": {
        "type": "score",
        "instructions": "How close is the quadrotor to hitting something?",
        "criteria": ["open space", "tight but passable", "about to collide"],
    },
    "target_truly_lost": {
        "type": "noul",
        "instructions": "Has the rover been out of sight long enough to count as lost?",
        "criteria": {"true": "Lost; start searching.", "false": "Only hidden for a moment."},
    },
}


def judge(obs, model):
    """rule()과 같은 세 가지를 Laya에게 묻고, 행동별 확률도 함께 돌려준다."""
    answers = model.predict(obs, QUESTIONS)["answers"]
    maneuver = answers["maneuver"]
    top_level = len(QUESTIONS["risk"]["criteria"]) - 1
    return {
        "maneuver": maneuver["choice"],
        "risk": round(answers["risk"]["score"] / top_level, 2),  # 0~2 단계를 rule()처럼 0~1로 맞춘다
        "target_truly_lost": answers["target_truly_lost"]["noul"] >= 0.5,
        "probabilities": maneuver["probabilities"],
    }
