import mujoco
import numpy as np
import pytest

from drone_rl.sim import ROVER_SPEED, ROVER_START_X, Sim, _rover_pose


@pytest.fixture
def sim():
    return Sim(seed=7)


def advance(sim, steps, ctrl=(0, 0, 0, 0)):
    for _ in range(steps):
        sim.step(ctrl)


def test_course_and_initial_state(sim):
    m, state = sim.model, sim.drone_state
    course_geoms = ("beam", "finish_beam", "left_pillar", "right_pillar", "rear_pillar", "floor")
    assert all(m.geom(name).id >= 0 for name in course_geoms)
    assert [m.actuator(i).name for i in range(m.nu)] == [f"thrust{i}" for i in range(1, 5)]
    x, y, z = state["pos"]
    assert -0.3 <= x <= 0.3
    assert -0.5 <= y <= 0.5
    assert z == 1.6
    np.testing.assert_array_equal(state["quat"], [1, 0, 0, 0])
    np.testing.assert_array_equal(state["vel"], [0, 0, 0])
    np.testing.assert_array_equal(state["angvel"], [0, 0, 0])
    assert sim.t == sim.collisions == sim.data.ncon == 0


def test_seed_reproduces_spawn_and_optional_pillars(sim):
    same_seed = Sim(seed=7, randomize_obstacles=True)
    repeated = Sim(seed=7, randomize_obstacles=True)
    other_seed = Sim(seed=8, randomize_obstacles=True)
    fixed_course = Sim(seed=8)
    np.testing.assert_array_equal(sim.drone_state["pos"], same_seed.drone_state["pos"])
    np.testing.assert_array_equal(same_seed.drone_state["pos"], repeated.drone_state["pos"])
    np.testing.assert_array_equal(fixed_course.drone_state["pos"], other_seed.drone_state["pos"])
    assert not np.array_equal(sim.drone_state["pos"], other_seed.drone_state["pos"])

    for name in ("beam", "finish_beam", "left_pillar", "right_pillar", "rear_pillar"):
        base = sim.model.geom(name).pos
        randomized = same_seed.model.geom(name).pos
        np.testing.assert_array_equal(base, fixed_course.model.geom(name).pos)
        np.testing.assert_array_equal(randomized, repeated.model.geom(name).pos)
        assert not np.array_equal(base, randomized)
        assert not np.array_equal(randomized, other_seed.model.geom(name).pos)
        assert randomized[2] == base[2]


def test_shuffled_courses_leave_a_drone_passage():
    names = ("beam", "finish_beam", "left_pillar", "right_pillar", "rear_pillar")
    orders = []
    for seed in range(30):
        sim = Sim(seed, randomize_obstacles=True)
        obstacles = [sim.model.geom(name) for name in names]
        by_x = sorted(obstacles, key=lambda geom: geom.pos[0])
        orders.append(tuple(geom.name in names[:2] for geom in by_x))
        assert np.min(np.diff([geom.pos[0] for geom in by_x])) >= 1.52
        drone_geoms = np.flatnonzero(sim.model.geom_bodyid == sim.model.body("x2").id)
        start = sim.drone_state["pos"]
        # 실제 X2 형상을 차량 경로 위로 이동시키며 빔 앞에서 상승하고 뒤에서 내려온다.
        for x in np.arange(start[0], 12.01, 0.04):
            fraction = np.clip((x - start[0]) / (ROVER_START_X - start[0]), 0, 1)
            _, y, yaw = _rover_pose(max(0, (x - ROVER_START_X) / ROVER_SPEED))
            beam_distance = min(abs(x - beam.pos[0]) for beam in obstacles[:2])
            ramp = np.clip((1.7 - beam_distance) / 1.2, 0, 1)
            height = 1.6 + 0.8 * ramp**2 * (3 - 2 * ramp)
            sim.data.qpos[sim._q:sim._q + 7] = [
                x, y + (1 - fraction) * start[1], height, np.cos(yaw / 2), 0, 0, np.sin(yaw / 2),
            ]
            mujoco.mj_forward(sim.model, sim.data)
            for obstacle in obstacles:
                for part in drone_geoms:
                    gap = mujoco.mj_geomDistance(sim.model, sim.data, part, obstacle.id, 1.0, None)
                    assert gap > 0.1, (seed, x, obstacle.name, gap)
    for first in range(0, 30, 10):
        assert len(set(orders[first:first + 10])) == 10


def test_free_fall_and_target_motion(sim):
    start_altitude = sim.drone_state["pos"][2]
    target = sim.data.body("target").xpos.copy()
    advance(sim, 100)
    assert sim.t == pytest.approx(0.2)
    assert sim.drone_state["pos"][2] < start_altitude
    assert sim.drone_state["vel"][2] < 0
    rover = sim.data.body("target")
    np.testing.assert_allclose(target, [1.25, 0, 0.1])
    np.testing.assert_allclose(rover.xpos, [1.45, 0, 0.1])
    assert sim.collisions == 0


@pytest.mark.parametrize("seed, randomize_obstacles", [(7, False)] + [(seed, True) for seed in range(30)])
def test_rover_weaves_past_obstacles_without_overlap(seed, randomize_obstacles):
    sim = Sim(seed, randomize_obstacles=randomize_obstacles)
    model, data = sim.model, sim.data
    rover = data.body("target")
    rover_geoms = np.flatnonzero(model.geom_bodyid == rover.id)
    obstacles = [model.geom(name).id for name in
                 ("beam", "left_pillar", "right_pillar", "rear_pillar", "finish_beam")]
    pillar_passes = {7.0: -0.40, 9.0: 0.40, 10.5: -0.35}
    np.testing.assert_allclose(model.geom("rover_chassis").size, [0.21, 0.12, 0.05])

    for _ in range(round(11 / model.opt.timestep)):
        # 차량은 충돌 반응을 끄므로, 차체·바퀴와 장애물 사이의 거리를 직접 검사한다.
        for obstacle in obstacles:
            for part in rover_geoms:
                distance = mujoco.mj_geomDistance(model, data, part, obstacle, 2.0, None)
                assert distance > 0.1, (sim.t, int(part), obstacle, distance)
        x, y, _ = rover.xpos
        if round(x, 3) in pillar_passes:
            assert y == pytest.approx(pillar_passes.pop(round(x, 3)), abs=1e-5)
        sim.step((0, 0, 0, 0))

    assert not pillar_passes
    np.testing.assert_allclose(rover.xpos, [12, 0, 0.1])


def test_motor_commands_drive_physics(sim):
    start_altitude = sim.drone_state["pos"][2]
    advance(sim, 50, (5, 5, 5, 5))
    assert sim.drone_state["pos"][2] > start_altitude


def test_beam_counts_once_until_separation(sim):
    beam = sim.model.geom("beam")
    joint = sim.model.body_jntadr[sim.model.body("x2").id]
    q = sim.model.jnt_qposadr[joint]
    for previous_hits in (0, 1):
        # 드론을 빔 위에서 떨어뜨린다. 다시 빔에서 떼어 놓고 같은 과정을 반복한다.
        x, y, z = beam.pos
        sim.data.qpos[q:q + 7] = [x, y, z + beam.size[0] + 0.3, 1, 0, 0, 0]
        sim.data.qvel[:] = 0
        sim.step([0] * 4)
        assert sim.data.ncon == 0
        assert sim.collisions == previous_hits
        advance(sim, 200)
        assert any(beam.id in contact.geom for contact in sim.data.contact)
        assert sim.collisions == previous_hits + 1
        advance(sim, 50)
        assert sim.collisions == previous_hits + 1


@pytest.mark.parametrize("beam_name", ("beam", "finish_beam"))
@pytest.mark.parametrize("lateral, altitude, hits_beam", [
    (0, 1.6, True), (-5, 1.6, True), (5, 1.6, True),
    (0, 1.2, False), (0, 2.0, False),
])
def test_straight_path_through_beam(sim, beam_name, lateral, altitude, hits_beam):
    beam = sim.model.geom(beam_name)
    joint = sim.model.body_jntadr[sim.model.body("x2").id]
    q = sim.model.jnt_qposadr[joint]
    contacts = set()
    # 코스 중앙과 양쪽 가장자리에서 수평으로 직진할 때 빔에 닿는지 확인한다.
    for x in np.linspace(beam.pos[0] - 1, beam.pos[0] + 1, 41):
        sim.data.qpos[q:q + 3] = [x, lateral, altitude]
        mujoco.mj_forward(sim.model, sim.data)
        contacts.update(geom for contact in sim.data.contact for geom in contact.geom)
    assert (beam.id in contacts) == hits_beam


@pytest.mark.parametrize("ctrl", ([1, 2, 3], [-1, 0, 0, 0], [14] * 4, [np.nan] * 4))
def test_invalid_motor_commands_leave_sim_unchanged(sim, ctrl):
    with pytest.raises(ValueError):
        sim.step(ctrl)
    assert sim.t == 0
    np.testing.assert_array_equal(sim.data.ctrl, np.zeros(4))


@pytest.mark.parametrize("surface", ("floor", "left_pillar", "right_pillar", "rear_pillar"))
def test_landing_on_other_course_surfaces(sim, surface):
    geom = sim.model.geom(surface)
    joint = sim.model.body_jntadr[sim.model.body("x2").id]
    q = sim.model.jnt_qposadr[joint]
    sim.data.qpos[q:q + 3] = [*geom.pos[:2], 3.0]
    advance(sim, 450)
    assert any(geom.id in contact.geom for contact in sim.data.contact)
    assert sim.collisions == 1
