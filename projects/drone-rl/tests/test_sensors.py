import json
import math

import mujoco
import numpy as np
import pytest

from drone_rl.sensors import MAX_RANGE_M, observe
from drone_rl.sim import Sim


@pytest.fixture
def sim():
    return Sim(seed=7)


def place(sim, drone, rover, yaw_deg=0, time_s=0):
    half_yaw = math.radians(yaw_deg) / 2
    joint = sim.model.body_jntadr[sim.model.body("x2").id]
    qpos = sim.model.jnt_qposadr[joint]
    sim.data.qpos[qpos:qpos + 7] = [
        *drone, math.cos(half_yaw), 0, 0, math.sin(half_yaw),
    ]
    sim.data.mocap_pos[sim.model.body("target").mocapid[0]] = rover
    sim.data.time = time_s
    mujoco.mj_forward(sim.model, sim.data)


def test_beam_blocks_all_sectors_at_flight_height(sim):
    place(sim, [1, 0, 1.6], [3, 0, 0.1])
    scene = observe(sim)
    assert list(scene["sector_range_m"]) == ["far_left", "left", "center", "right", "far_right"]
    assert scene["sectors_blocked"] == 5
    assert scene["path_ahead_m"] == pytest.approx(0.85, abs=0.01)
    assert scene["free_ahead_level_m"] == scene["nearest_obstacle_m"] == scene["path_ahead_m"]
    assert scene["free_ahead_above_m"] > scene["path_ahead_m"]
    assert scene["free_ahead_below_m"] > scene["path_ahead_m"]

    place(sim, [1, 0, 1.6], [3, 0, 0.1], yaw_deg=180)
    scene = observe(sim)
    assert scene["sectors_blocked"] == 0
    assert scene["path_ahead_m"] == MAX_RANGE_M


def test_path_ahead_includes_the_sectors_next_to_center(sim):
    place(sim, [5, 0, 1.6], [6, 0, 0.1])
    scene = observe(sim)
    assert scene["sector_range_m"]["center"] > 3.0
    assert scene["path_ahead_m"] == scene["sector_range_m"]["left"] < 3.0


def test_upper_band_detects_a_tall_pillar(sim):
    place(sim, [5, 0.8, 1.6], [6, 0, 0.1])
    scene = observe(sim)
    assert scene["free_ahead_level_m"] < 3.0
    assert scene["free_ahead_above_m"] < 3.0


def test_target_visibility_uses_downward_camera_tilt(sim):
    place(sim, [0, 0, 1.6], [0.65, 0, 0.1])
    assert observe(sim)["target"]["visible"] is True
    place(sim, [0, 0, 1.6], [0.7, 0, 2.5])
    assert observe(sim)["target"]["visible"] is False


def test_target_does_not_count_as_obstacle_and_bearing_is_positive_on_left(sim):
    place(sim, [-2, 0, 1.6], [-0.5, 0.6, 1.6])
    scene = observe(sim)
    assert scene["sectors_blocked"] == 0
    assert scene["path_ahead_m"] == pytest.approx(3.85, abs=0.01)
    assert scene["target"]["visible"] is True
    assert scene["target"]["bearing_deg"] == pytest.approx(math.degrees(math.atan2(0.6, 1.5)))
    assert scene["target"]["range_m"] == pytest.approx(math.hypot(1.5, 0.6))

    place(sim, [-2, 0, 1.6], [-0.5, 0.6, 1.6], yaw_deg=45)
    assert observe(sim)["target"]["bearing_deg"] == pytest.approx(scene["target"]["bearing_deg"] - 45)


def test_target_occlusion_duration_reacquisition_and_time_reset(sim):
    place(sim, [1, 0, 1.6], [3, 0, 1.6])
    hidden = {"visible": False, "bearing_deg": None, "range_m": None, "unseen_for_s": 0.0}
    assert observe(sim)["target"] == hidden
    place(sim, [1, 0, 1.6], [3, 0, 1.6], time_s=2)
    assert observe(sim)["target"] == {**hidden, "unseen_for_s": 2.0}

    place(sim, [1, 0, 1.6], [1.5, 0, 1.6], time_s=3)
    assert observe(sim)["target"]["visible"] is True
    assert observe(sim)["target"]["unseen_for_s"] == 0.0

    for time_s, unseen_s in [(4, 0), (5, 1), (0, 0)]:
        place(sim, [1, 0, 1.6], [3, 0, 1.6], time_s=time_s)
        assert observe(sim)["target"] == {**hidden, "unseen_for_s": unseen_s}


def test_target_outside_range_or_behind_is_not_visible(sim):
    for rover in ([-1, 0, 3], [30, 0, 3]):
        place(sim, [0, 0, 3], rover)
        target = observe(sim)["target"]
        assert target["visible"] is False
        assert target["bearing_deg"] is None
        assert target["range_m"] is None


def test_instances_do_not_share_target_history(sim):
    place(sim, [1, 0, 1.6], [3, 0, 1.6])
    observe(sim)
    sim.data.time = 3
    assert observe(sim)["target"]["unseen_for_s"] == 3
    second = Sim(seed=7)
    place(second, [1, 0, 1.6], [3, 0, 1.6], time_s=3)
    assert observe(second)["target"]["unseen_for_s"] == 0


def test_observation_does_not_advance_physics(sim):
    positions = sim.data.qpos.copy()
    velocities = sim.data.qvel.copy()
    scene = observe(sim)
    assert scene == observe(sim)
    assert json.loads(json.dumps(scene, allow_nan=False)) == scene
    np.testing.assert_array_equal(sim.data.qpos, positions)
    np.testing.assert_array_equal(sim.data.qvel, velocities)
    assert sim.t == sim.collisions == 0
