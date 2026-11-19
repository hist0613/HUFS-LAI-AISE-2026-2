from drone_rl.rule import rule


def scene(**changes):
    """아무것도 없는 열린 코스에 바꾸고 싶은 항목만 덮어쓴다."""
    obs = {
        "sector_range_m": dict.fromkeys(["far_left", "left", "center", "right", "far_right"], 25),
        "sectors_blocked": 0,
        "path_ahead_m": 25,
        "free_ahead_above_m": 25,
        "free_ahead_level_m": 25,
        "free_ahead_below_m": 25,
        "nearest_obstacle_m": 25,
        "target": {"visible": True, "bearing_deg": 0, "range_m": 5, "unseen_for_s": 0},
    }
    obs.update(changes)
    return obs


def test_open_course_holds_course():
    assert rule(scene()) == ("hold_course", 0.0, False)


def test_beam_ahead_climbs():
    mv, risk, _ = rule(scene(sectors_blocked=5, path_ahead_m=1.5, nearest_obstacle_m=1.5))
    assert mv == "climb"
    assert risk == 0.5


def test_no_way_through_brakes():
    mv, _, _ = rule(scene(sectors_blocked=5, path_ahead_m=1, free_ahead_above_m=1))
    assert mv == "brake"


def test_pillar_goes_to_open_side():
    pillar_left = {"far_left": 25, "left": 2, "center": 2, "right": 25, "far_right": 25}
    pillar_right = {"far_left": 25, "left": 25, "center": 2, "right": 2, "far_right": 25}
    assert rule(scene(sector_range_m=pillar_left, sectors_blocked=2, path_ahead_m=2))[0] == "gap_right"
    assert rule(scene(sector_range_m=pillar_right, sectors_blocked=2, path_ahead_m=2))[0] == "gap_left"


def test_target_lost_only_after_a_while():
    unseen = {"visible": False, "bearing_deg": None, "range_m": None, "unseen_for_s": 0.5}
    assert rule(scene(target=unseen)) == ("hold_course", 0.0, False)
    unseen["unseen_for_s"] = 3
    assert rule(scene(target=unseen)) == ("reacquire", 0.0, True)
