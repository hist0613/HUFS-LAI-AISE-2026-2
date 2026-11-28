"""Independent X2 fixture and motor allocation tests; no course required.

Model: MuJoCo Menagerie / Skydio X2 (Apache-2.0), via robot_descriptions.
Run with Python 3.12: python -m pytest tests/test_pilot.py -v
The first model import downloads Menagerie and requires git and network access.
"""

import mujoco
import numpy as np
import pytest

from drone_rl.pilot import AltitudeController, AttitudeController, MotorMixer
from drone_rl.pilot import Pilot, PositionController, VelocityController


def reset_drone(model, data):
    """Reset the X2 free joint to a stationary pose 1.5 m above the floor."""
    mujoco.mj_resetData(model, data)
    joint = model.body_jntadr[model.body("x2").id]
    q = model.jnt_qposadr[joint]
    data.qpos[q:q + 3] = [0, 0, 1.5]
    data.qpos[q + 3:q + 7] = [1, 0, 0, 0]  # wxyz, body -> world
    mujoco.mj_forward(model, data)


@pytest.fixture(scope="module")
def pilot_model():
    from robot_descriptions.skydio_x2_mj_description import MJCF_PATH

    spec = mujoco.MjSpec.from_file(MJCF_PATH)
    spec.option.timestep = 0.002
    spec.worldbody.add_geom(
        name="pilot_test_floor", type=mujoco.mjtGeom.mjGEOM_PLANE,
        size=[20, 20, 0.1], rgba=[0.4, 0.4, 0.4, 1],
    )
    return spec.compile()


@pytest.fixture
def pilot_data(pilot_model):
    data = mujoco.MjData(pilot_model)
    reset_drone(pilot_model, data)
    return data


def test_x2_model_and_floor(pilot_model):
    m = pilot_model
    body = m.body("x2").id
    joint = m.body_jntadr[body]
    assert (m.nq, m.nv) == (7, 6)
    assert joint >= 0
    assert m.jnt_type[joint] == mujoco.mjtJoint.mjJNT_FREE
    assert m.body_subtreemass[body] > 0
    assert np.all(m.body_inertia[body] > 0)
    assert m.geom("pilot_test_floor").type == mujoco.mjtGeom.mjGEOM_PLANE
    np.testing.assert_allclose(m.opt.timestep, 0.002)


def test_motor_order_and_limits(pilot_model):
    m = pilot_model
    assert m.nu == 4
    assert [m.actuator(i).name for i in range(4)] == [
        "thrust1", "thrust2", "thrust3", "thrust4",
    ]
    assert m.actuator_ctrllimited.all()
    np.testing.assert_array_equal(m.actuator_ctrlrange, [[0, 13]] * 4)


def test_initial_drone_state(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    joint = m.body_jntadr[m.body("x2").id]
    q, v = m.jnt_qposadr[joint], m.jnt_dofadr[joint]
    np.testing.assert_array_equal(d.qpos[q:q + 3], [0, 0, 1.5])  # pos
    np.testing.assert_array_equal(d.qpos[q + 3:q + 7], [1, 0, 0, 0])  # quat
    np.testing.assert_array_equal(d.qvel[v:v + 3], [0, 0, 0])  # vel
    np.testing.assert_array_equal(d.qvel[v + 3:v + 6], [0, 0, 0])  # angvel
    np.testing.assert_array_equal(d.ctrl, np.zeros(4))
    assert d.time == 0
    assert d.ncon == 0


def test_unpowered_drone_falls(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    start_height = d.qpos[2]
    for _ in range(20):
        mujoco.mj_step(m, d)
    np.testing.assert_allclose(d.time, 0.04)
    assert start_height - 0.02 < d.qpos[2] < start_height
    assert d.qvel[2] < 0
    assert np.isfinite(d.qpos).all()
    assert np.isfinite(d.qvel).all()
    np.testing.assert_allclose(d.qpos[:2], [0, 0], atol=1e-4)


def test_reset_reproduces_trajectory(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    runs = []
    for _ in range(2):
        reset_drone(m, d)
        test_initial_drone_state(m, d)
        d.ctrl[:] = [1, 2, 3, 4]
        for _ in range(20):
            mujoco.mj_step(m, d)
        runs.append(np.concatenate((d.qpos, d.qvel)))
    np.testing.assert_allclose(runs[0], runs[1], rtol=0, atol=1e-12)


@pytest.fixture
def mixer(pilot_model):
    return MotorMixer(pilot_model)


def applied_wrench(model, data, ctrl):
    """Measure MuJoCo actuator force and COM torque in the body frame."""
    data.ctrl[:] = ctrl
    mujoco.mj_forward(model, data)
    body = model.body("x2").id
    v = model.jnt_dofadr[model.body_jntadr[body]]
    rotation = data.xmat[body].reshape(3, 3)
    force = rotation.T @ data.qfrc_actuator[v:v + 3]
    torque = data.qfrc_actuator[v + 3:v + 6] - np.cross(model.body_ipos[body], force)
    return force, torque


@pytest.mark.parametrize("thrust", [0, 13, 26, 52])
def test_equal_motor_thrust(mixer, pilot_model, pilot_data, thrust):
    ctrl = mixer.mix(thrust, [0, 0, 0])
    np.testing.assert_allclose(ctrl, np.full(4, thrust / 4))
    force, torque = applied_wrench(pilot_model, pilot_data, ctrl)
    np.testing.assert_allclose(force, [0, 0, thrust], atol=1e-10)
    np.testing.assert_allclose(torque, 0, atol=1e-10)


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("sign", [-1, 1])
def test_axis_torque_matches_mujoco(mixer, pilot_model, pilot_data, axis, sign):
    requested = np.zeros(3)
    requested[axis] = sign * 0.1
    ctrl = mixer.mix(20, requested)
    force, torque = applied_wrench(pilot_model, pilot_data, ctrl)
    np.testing.assert_allclose(force, [0, 0, 20], atol=1e-10)
    np.testing.assert_allclose(torque, requested, atol=1e-10)


def test_body_frame_torque_when_rotated(mixer, pilot_model, pilot_data):
    pilot_data.qpos[3:7] = [np.cos(0.3), 0, np.sin(0.3), 0]
    requested = np.array([0.1, -0.1, 0.05])
    force, torque = applied_wrench(pilot_model, pilot_data, mixer.mix(20, requested))
    np.testing.assert_allclose(force, [0, 0, 20], atol=1e-10)
    np.testing.assert_allclose(torque, requested, atol=1e-10)


@pytest.mark.parametrize("thrust", [-10, 0, 1, 26, 51, 52, 100])
def test_saturation_preserves_thrust(mixer, pilot_model, pilot_data, thrust):
    requested = np.array([10, -20, 5])
    ctrl = mixer.mix(thrust, requested)
    assert np.isfinite(ctrl).all()
    assert np.all((0 <= ctrl) & (ctrl <= 13))
    force, torque = applied_wrench(pilot_model, pilot_data, ctrl)
    np.testing.assert_allclose(force, [0, 0, np.clip(thrust, 0, 52)], atol=1e-10)
    scale = torque[0] / requested[0]
    assert -1e-10 <= scale < 1
    np.testing.assert_allclose(torque, requested * scale, atol=1e-10)
    assert np.any(np.isclose(ctrl, 0) | np.isclose(ctrl, 13))


@pytest.mark.parametrize("thrust,torque", [
    (np.nan, [0, 0, 0]), (np.inf, [0, 0, 0]),
    (13, [0, np.nan, 0]), (13, [0, 0, np.inf]),
    (13, [0, 0]), ([13], [0, 0, 0]),
    (13, [np.finfo(float).max] * 3),
])
def test_invalid_mixer_requests(mixer, thrust, torque):
    with pytest.raises(ValueError):
        mixer.mix(thrust, torque)


def test_mixer_uses_model_motor_geometry(pilot_model):
    # Change arm lengths and yaw gear to catch hard-coded X2 constants.
    import copy

    model = copy.copy(pilot_model)
    sites = model.actuator_trnid[:, 0]
    model.site_pos[sites, :2] *= 1.2
    model.actuator_gear[:, 5] *= 1.5
    ctrl = MotorMixer(model).mix(20, [0.1, 0, 0.1])
    data = mujoco.MjData(model)
    reset_drone(model, data)
    force, torque = applied_wrench(model, data, ctrl)
    np.testing.assert_allclose(force, [0, 0, 20], atol=1e-10)
    np.testing.assert_allclose(torque, [0.1, 0, 0.1], atol=1e-10)


def axis_quaternion(axis, degrees):
    half = np.deg2rad(degrees) / 2
    quat = np.zeros(4)
    quat[0], quat[axis + 1] = np.cos(half), np.sin(half)
    return quat


def attitude_state(data):
    return {"quat": data.qpos[3:7].copy(), "angvel": data.qvel[3:6].copy()}


@pytest.mark.parametrize("axis", [0, 1, 2])
@pytest.mark.parametrize("degrees", [-10, 10])
def test_attitude_recovers_within_three_seconds(pilot_model, pilot_data, axis, degrees):
    m, d = pilot_model, pilot_data
    controller = AttitudeController(m)
    d.qpos[3:7] = axis_quaternion(axis, degrees)
    thrust = m.body_subtreemass[m.body("x2").id] * np.linalg.norm(m.opt.gravity)
    # Constant weight compensation isolates attitude control from altitude control.
    for step in range(round(3 / m.opt.timestep)):
        d.ctrl[:] = controller.act(thrust, [1, 0, 0, 0], attitude_state(d))
        assert np.isfinite(d.ctrl).all() and np.all((0 <= d.ctrl) & (d.ctrl <= 13))
        mujoco.mj_step(m, d)
        assert d.ncon == 0  # Recovery must not be caused by ground contact.
        if step * m.opt.timestep >= 2.5:
            angle = 2 * np.arccos(np.clip(abs(d.qpos[3]), 0, 1))
            assert angle < np.deg2rad(3)
    assert np.linalg.norm(d.qvel[3:6]) < 0.05


def test_attitude_tracks_nonzero_target(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    controller = AttitudeController(m)
    target = axis_quaternion(2, 90)
    mujoco.mju_mulQuat(d.qpos[3:7], target, axis_quaternion(0, 10))
    thrust = m.body_subtreemass[m.body("x2").id] * np.linalg.norm(m.opt.gravity)
    for _ in range(round(3 / m.opt.timestep)):
        d.ctrl[:] = controller.act(thrust, target, attitude_state(d))
        mujoco.mj_step(m, d)
        assert d.ncon == 0
    angle = 2 * np.arccos(np.clip(abs(target @ d.qpos[3:7]), 0, 1))
    assert angle < np.deg2rad(3)


def test_attitude_damps_rotation(pilot_model, pilot_data):
    controller = AttitudeController(pilot_model)
    omega = np.array([0.1, -0.2, 0.05])
    state = {"quat": [1, 0, 0, 0], "angvel": omega}
    ctrl = controller.act(13, [1, 0, 0, 0], state)
    _, torque = applied_wrench(pilot_model, pilot_data, ctrl)
    assert omega @ torque < 0  # Damping removes rotational kinetic energy.


@pytest.mark.parametrize("current_sign,target_sign", [(1, 1), (-1, 1), (1, -1), (-1, -1)])
def test_attitude_quaternion_sign_equivalence(pilot_model, current_sign, target_sign):
    controller = AttitudeController(pilot_model)
    current, target = axis_quaternion(0, 10), axis_quaternion(2, 5)
    omega = np.array([0.1, 0, 0])
    expected = controller.act(13, target, {"quat": current, "angvel": omega})
    actual = controller.act(13, target_sign * target,
                            {"quat": current_sign * current, "angvel": omega})
    np.testing.assert_allclose(actual, expected, atol=1e-12)


def test_attitude_aligned_and_does_not_mutate_state(pilot_model):
    controller = AttitudeController(pilot_model)
    target = axis_quaternion(2, 30)
    state = {"quat": target.copy(), "angvel": np.zeros(3)}
    np.testing.assert_allclose(controller.act(13, target, state), np.full(4, 3.25))
    np.testing.assert_array_equal(state["quat"], target)
    np.testing.assert_array_equal(state["angvel"], np.zeros(3))


@pytest.mark.parametrize("field,value", [
    ("target", [0, 0, 0, 0]), ("target", [1, 0, 0]),
    ("quat", [np.nan, 0, 0, 0]), ("quat", [2, 0, 0, 0]),
    ("angvel", [0, 0]), ("angvel", [0, np.inf, 0]),
])
def test_attitude_rejects_bad_state(pilot_model, field, value):
    controller = AttitudeController(pilot_model)
    target = [1, 0, 0, 0]
    state = {"quat": target, "angvel": [0, 0, 0]}
    if field == "target":
        target = value
    else:
        state[field] = value
    with pytest.raises(ValueError):
        controller.act(13, target, state)


@pytest.mark.parametrize("frequency,damping", [(0, 1), (6, -1), (np.nan, 1), (6, np.inf)])
def test_attitude_rejects_bad_gains(pilot_model, frequency, damping):
    with pytest.raises(ValueError):
        AttitudeController(pilot_model, frequency, damping)


def flight_state(data):
    return {**attitude_state(data), "pos": data.qpos[:3].copy(),
            "vel": data.qvel[:3].copy()}


@pytest.mark.parametrize("initial_height", [1.0, 1.5, 2.0])
def test_altitude_holds_for_ten_seconds(pilot_model, pilot_data, initial_height):
    m, d = pilot_model, pilot_data
    controller = AltitudeController(m)
    d.qpos[2] = initial_height
    for _ in range(round(10 / m.opt.timestep)):
        d.ctrl[:] = controller.act(1.5, flight_state(d))
        assert np.isfinite(d.ctrl).all() and np.all((0 <= d.ctrl) & (d.ctrl <= 13))
        mujoco.mj_step(m, d)
        assert d.ncon == 0
        assert np.linalg.norm(d.qpos[:2]) < 0.3
        if d.time >= 2:
            assert abs(d.qpos[2] - 1.5) < 0.15
    assert abs(d.qvel[2]) < 0.05


@pytest.mark.parametrize("vertical_speed", [-1.0, 1.0])
def test_altitude_recovers_from_vertical_impulse(pilot_model, pilot_data, vertical_speed):
    m, d = pilot_model, pilot_data
    controller = AltitudeController(m)
    for step in range(round(6 / m.opt.timestep)):
        if step == round(3 / m.opt.timestep):
            d.qvel[2] = vertical_speed
        d.ctrl[:] = controller.act(1.5, flight_state(d))
        mujoco.mj_step(m, d)
        assert d.ncon == 0 and abs(d.qpos[2] - 1.5) < 0.3
        if d.time >= 5:
            assert abs(d.qpos[2] - 1.5) < 0.05
    assert abs(d.qvel[2]) < 0.05


@pytest.mark.parametrize("axis", [0, 1])
@pytest.mark.parametrize("degrees", [-10, 10])
def test_altitude_during_attitude_recovery(pilot_model, pilot_data, axis, degrees):
    m, d = pilot_model, pilot_data
    controller = AltitudeController(m)
    d.qpos[3:7] = axis_quaternion(axis, degrees)
    for _ in range(round(3 / m.opt.timestep)):
        d.ctrl[:] = controller.act(1.5, flight_state(d))
        mujoco.mj_step(m, d)
        assert d.ncon == 0 and abs(d.qpos[2] - 1.5) < 0.15
    assert abs(d.qvel[2]) < 0.05
    assert 2 * np.arccos(np.clip(abs(d.qpos[3]), 0, 1)) < np.deg2rad(3)
    # Lateral drift after an initial tilt is not controlled in this stage.


@pytest.mark.parametrize("target_height", [1.0, 2.0])
def test_altitude_tracks_changed_setpoint(pilot_model, pilot_data, target_height):
    m, d = pilot_model, pilot_data
    controller = AltitudeController(m)
    target_quat = axis_quaternion(2, 90)
    d.qpos[3:7] = target_quat
    for step in range(round(6 / m.opt.timestep)):
        height = 1.5 if step < round(3 / m.opt.timestep) else target_height
        d.ctrl[:] = controller.act(height, flight_state(d), target_quat)
        mujoco.mj_step(m, d)
        assert d.ncon == 0
        if d.time >= 5:
            assert abs(d.qpos[2] - target_height) < 0.15
    assert abs(d.qvel[2]) < 0.05
    np.testing.assert_allclose(d.qpos[3:7], target_quat, atol=1e-5)


def test_altitude_uses_model_mass_and_gravity(pilot_model):
    import copy

    model = copy.copy(pilot_model)
    body = model.body("x2").id
    model.body_mass[body] *= 1.2
    model.opt.gravity[2] = -8
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)
    reset_drone(model, data)
    controller = AltitudeController(model)
    state = flight_state(data)
    before = {key: value.copy() for key, value in state.items()}
    data.ctrl[:] = controller.act(1.5, state)
    mujoco.mj_forward(model, data)
    np.testing.assert_allclose(data.qacc, 0, atol=1e-8)
    for key in state:
        np.testing.assert_array_equal(state[key], before[key])


@pytest.mark.parametrize("height,speed,angle", [(100, 0, 0), (-100, 0, 0),
                                                (1.5, -100, 90), (1.5, 100, 180)])
def test_altitude_limits_extreme_requests(pilot_model, pilot_data, height, speed, angle):
    state = flight_state(pilot_data)
    state["vel"][2] = speed
    state["quat"] = axis_quaternion(0, angle)
    ctrl = AltitudeController(pilot_model).act(height, state)
    assert np.isfinite(ctrl).all() and np.all((0 <= ctrl) & (ctrl <= 13))
    assert ctrl.sum() > 0  # Bounded output only; inverted recovery is not promised.


@pytest.mark.parametrize("field,value", [
    ("height", np.nan), ("height", np.inf), ("height", [1.5]),
    ("height", np.finfo(float).max), ("pos", [0, 0]), ("pos", [0, 0, np.nan]),
    ("vel", [0, 0]), ("vel", [0, 0, np.inf]),
])
def test_altitude_rejects_bad_state(pilot_model, pilot_data, field, value):
    state, height = flight_state(pilot_data), 1.5
    if field == "height":
        height = value
    else:
        state[field] = value
    with pytest.raises(ValueError):
        AltitudeController(pilot_model).act(height, state)


@pytest.mark.parametrize("gravity", [[0, 0, 0], [1, 0, -9.81], [0, 0, np.nan]])
def test_altitude_rejects_unsupported_gravity(pilot_model, gravity):
    import copy

    model = copy.copy(pilot_model)
    model.opt.gravity[:] = gravity
    with pytest.raises(ValueError):
        AltitudeController(model)


def velocity_step(model, data, controller, target, height=1.5, yaw=0.0):
    data.ctrl[:] = controller.act(target, height, flight_state(data), yaw)
    assert np.isfinite(data.ctrl).all() and np.all((0 <= data.ctrl) & (data.ctrl <= 13))
    mujoco.mj_step(model, data)
    assert data.ncon == 0
    assert abs(data.qpos[2] - height) < 0.15
    vertical_axis = 1 - 2 * np.sum(data.qpos[4:6]**2)
    assert vertical_axis > np.cos(np.deg2rad(30))  # Actual transient tilt bound.


@pytest.mark.parametrize("yaw", [0.0, np.pi / 2])
@pytest.mark.parametrize("target", [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1]])
def test_velocity_tracks_world_xy(pilot_model, pilot_data, yaw, target):
    m, d = pilot_model, pilot_data
    controller = VelocityController(m)
    d.qpos[3:7] = axis_quaternion(2, np.rad2deg(yaw))
    for _ in range(round(6 / m.opt.timestep)):
        velocity_step(m, d, controller, target, yaw=yaw)
        if d.time >= 3:
            assert np.linalg.norm(d.qvel[:2] - target) < 0.15
    assert np.dot(d.qpos[:2], target) > 3
    forward = np.empty(9)
    mujoco.mju_quat2Mat(forward, d.qpos[3:7])
    heading = np.arctan2(forward[3], forward[0])
    assert abs(np.arctan2(np.sin(heading - yaw), np.cos(heading - yaw))) < np.deg2rad(3)


def test_velocity_changes_direction_and_rejects_disturbance(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    controller = VelocityController(m)
    for step in range(round(10 / m.opt.timestep)):
        target = [1, 0] if step < round(4 / m.opt.timestep) else [-1, 0]
        if step == round(7 / m.opt.timestep):
            d.qvel[1] += 1.0
        velocity_step(m, d, controller, target)
        if d.time >= 9:
            assert np.linalg.norm(d.qvel[:2] - target) < 0.15


def test_velocity_zero_request_holds_hover(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    controller = VelocityController(m)
    for _ in range(round(10 / m.opt.timestep)):
        velocity_step(m, d, controller, [0, 0])
        assert np.linalg.norm(d.qvel[:2]) < 0.05
        assert np.linalg.norm(d.qpos[:2]) < 0.3


@pytest.mark.parametrize("target", [[100, 0], [100, 100]])
def test_velocity_caps_speed_without_changing_direction(pilot_model, pilot_data, target):
    m, d = pilot_model, pilot_data
    controller = VelocityController(m)
    expected = np.asarray(target) * (3 / np.linalg.norm(target))
    for _ in range(round(8 / m.opt.timestep)):
        velocity_step(m, d, controller, target)
        if d.time >= 5:
            assert np.linalg.norm(d.qvel[:2] - expected) < 0.15


def test_velocity_preserves_inputs_and_has_no_episode_memory(pilot_model, pilot_data):
    controller = VelocityController(pilot_model)
    state, target = flight_state(pilot_data), np.array([100., 100.])
    before = {key: value.copy() for key, value in state.items()}
    expected = controller.act(target, 1.5, state)
    controller.act([-2, 1], 2.0, state, 1.0)
    np.testing.assert_allclose(controller.act(target, 1.5, state), expected)
    np.testing.assert_array_equal(target, [100, 100])
    for key in state:
        np.testing.assert_array_equal(state[key], before[key])


@pytest.mark.parametrize("field,value", [
    ("target", [1]), ("target", [1, 0, 0]), ("target", [np.nan, 0]),
    ("target", [np.inf, 0]), ("target", [np.finfo(float).max, 0]),
    ("vel", [0, 0]), ("vel", [0, np.nan, 0]),
    ("vel", [np.finfo(float).max, 0, 0]),
    ("yaw", np.inf), ("yaw", [0]), ("height", np.nan),
    ("quat", [0, 0, 0, 0]),
])
def test_velocity_rejects_bad_inputs(pilot_model, pilot_data, field, value):
    target, height, yaw = [1, 0], 1.5, 0.0
    state = flight_state(pilot_data)
    if field == "target":
        target = value
    elif field == "height":
        height = value
    elif field == "yaw":
        yaw = value
    else:
        state[field] = value
    with pytest.raises(ValueError):
        VelocityController(pilot_model).act(target, height, state, yaw)


def position_step(model, data, ctrl):
    assert np.isfinite(ctrl).all() and np.all((0 <= ctrl) & (ctrl <= 13))
    data.ctrl[:] = ctrl
    mujoco.mj_step(model, data)
    assert data.ncon == 0
    assert 1 - 2 * np.sum(data.qpos[4:6]**2) > np.cos(np.deg2rad(30))


@pytest.mark.parametrize("target", [[1, 0, 1.5], [0, -1, 1.5], [-1, 1, 1.5], [.5, -.5, 2]])
def test_position_reaches_and_holds_target(pilot_model, pilot_data, target):
    m, d = pilot_model, pilot_data
    controller = PositionController(m)
    for _ in range(round(10 / m.opt.timestep)):
        position_step(m, d, controller.act(target, flight_state(d)))
        if d.time >= 6:
            assert np.linalg.norm(d.qpos[:3] - target) < 0.15
            assert np.linalg.norm(d.qvel[:3]) < 0.1


@pytest.mark.parametrize("target,yaw", [([1, 0], 0), ([-1, 0], 0), ([0, 1], np.pi / 2),
                                       ([0, -1], 0), ([1, 1], np.pi / 2), ([3, 0], 0)])
def test_brake_after_flight_holds_entry_pose(pilot_model, pilot_data, target, yaw):
    m, d = pilot_model, pilot_data
    controller = PositionController(m)
    d.qpos[3:7] = axis_quaternion(2, np.rad2deg(yaw))
    for _ in range(round(3 / m.opt.timestep)):
        velocity_step(m, d, controller.velocity, target, yaw=yaw)
    anchor = d.qpos[:3].copy()
    assert np.linalg.norm(d.qvel[:2]) > 0.8
    for step in range(round(8 / m.opt.timestep)):
        position_step(m, d, controller.brake(flight_state(d)))
        assert abs(d.qpos[2] - anchor[2]) < 0.15
        if step * m.opt.timestep >= 6:
            assert np.linalg.norm(d.qpos[:3] - anchor) < 0.15
            assert np.linalg.norm(d.qvel[:3]) < 0.1
    rotation = np.empty(9)
    mujoco.mju_quat2Mat(rotation, d.qpos[3:7])
    error = np.arctan2(rotation[3], rotation[0]) - yaw
    assert abs(np.arctan2(np.sin(error), np.cos(error))) < np.deg2rad(3)


def test_brake_returns_after_position_and_velocity_disturbance(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    controller = PositionController(m)
    anchor = d.qpos[:3].copy()
    controller.brake(flight_state(d))
    d.qpos[:2] += [.5, -.5]
    d.qvel[:2] = [.4, -.3]
    for _ in range(round(10 / m.opt.timestep)):
        position_step(m, d, controller.brake(flight_state(d)))
        assert abs(d.qpos[2] - anchor[2]) < 0.15
        if d.time >= 6:
            assert np.linalg.norm(d.qpos[:3] - anchor) < 0.15
            assert np.linalg.norm(d.qvel[:3]) < 0.1


def test_position_limits_approach_speed(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    controller = PositionController(m)
    for _ in range(round(6 / m.opt.timestep)):
        position_step(m, d, controller.act([100, 100, 1.5], flight_state(d)))
        assert np.linalg.norm(d.qvel[:2]) < 1.65
    np.testing.assert_allclose(d.qvel[:2], np.full(2, 1.5 / np.sqrt(2)), atol=0.1)


@pytest.mark.parametrize("exit_mode", ["reset", "new_target"])
def test_brake_can_latch_a_new_pose(pilot_model, pilot_data, exit_mode):
    controller = PositionController(pilot_model)
    state = flight_state(pilot_data)
    controller.brake(state)
    state["pos"] = np.array([2., -1., 2.])
    state["quat"] = axis_quaternion(2, 90)
    if exit_mode == "reset":
        controller.reset()
    else:
        controller.act([3, -1, 2], state, np.pi / 2)
    np.testing.assert_allclose(controller.brake(state),
                               PositionController(pilot_model).brake(state), atol=1e-12)


def test_position_reset_reproduces_episode(pilot_model, pilot_data):
    m, d = pilot_model, pilot_data
    controller = PositionController(m)
    results = []
    for _ in range(2):
        reset_drone(m, d)
        controller.reset()
        d.qvel[0] = 1
        for step in range(1000):
            position_step(m, d, controller.brake(flight_state(d)))
        results.append(np.r_[d.qpos, d.qvel])
    np.testing.assert_allclose(*results, rtol=0, atol=1e-12)


def test_position_preserves_inputs_and_brake_target(pilot_model, pilot_data):
    controller = PositionController(pilot_model)
    state, target = flight_state(pilot_data), np.array([1., 1., 1.5])
    before = {key: value.copy() for key, value in state.items()}
    controller.act(target, state)
    controller.brake(state)
    np.testing.assert_array_equal(target, [1, 1, 1.5])
    for key in state:
        np.testing.assert_array_equal(state[key], before[key])
    # Mutating a caller-owned state array must not move the stored anchor.
    state["pos"][0] += 1
    expected = PositionController(pilot_model).act([0, 0, 1.5], state)
    np.testing.assert_allclose(controller.brake(state), expected)
    with pytest.raises(ValueError):
        controller.act([np.nan, 0, 1.5], state)
    np.testing.assert_allclose(controller.brake(state), expected)


@pytest.mark.parametrize("field,value", [("pos", [0, 0]), ("pos", [0, 0, np.nan]),
                                       ("vel", [np.inf, 0, 0]), ("quat", [0, 0, 0, 0])])
def test_invalid_brake_call_does_not_latch(pilot_model, pilot_data, field, value):
    controller = PositionController(pilot_model)
    bad = flight_state(pilot_data)
    bad[field] = value
    with pytest.raises(ValueError):
        controller.brake(bad)
    state = flight_state(pilot_data)
    state["pos"] += [2, -1, 0]
    np.testing.assert_allclose(controller.brake(state),
                               PositionController(pilot_model).brake(state))


@pytest.mark.parametrize("target", [[0, 0], [0, 0, np.nan], [np.inf, 0, 1.5],
                                    [np.finfo(float).max, 0, 1.5]])
def test_position_rejects_bad_target(pilot_model, pilot_data, target):
    with pytest.raises(ValueError):
        PositionController(pilot_model).act(target, flight_state(pilot_data))


@pytest.fixture
def maneuver_obs():
    return {"sector_range_m": dict.fromkeys(
        ["far_left", "left", "center", "right", "far_right"], 25.0),
        "sectors_blocked": 0, "path_ahead_m": 25.0, "nearest_obstacle_m": 25.0,
        "free_ahead_above_m": 25.0, "free_ahead_level_m": 25.0, "free_ahead_below_m": 25.0,
        "target": {"visible": True, "bearing_deg": 0.0, "range_m": 5.0, "unseen_for_s": 0.0}}


@pytest.mark.parametrize("yaw", [0, np.pi / 2])
@pytest.mark.parametrize("mv,offset", [("hold_course", 0), ("gap_left", 1), ("gap_right", -1)])
def test_maneuver_direction_and_repeated_command(pilot_model, pilot_data, maneuver_obs, yaw, mv, offset):
    m, d = pilot_model, pilot_data
    pilot = Pilot(m)
    d.qpos[2] = 1.8
    d.qpos[3:7] = axis_quaternion(2, np.rad2deg(yaw))
    forward, left = np.array([np.cos(yaw), np.sin(yaw)]), np.array([-np.sin(yaw), np.cos(yaw)])
    for _ in range(round(8 / m.opt.timestep)):
        position_step(m, d, pilot.act(mv, maneuver_obs, flight_state(d)))
        assert abs(d.qpos[2] - 1.8) < 0.15
        assert abs(d.qpos[:2] @ left) < 1.3
        if d.time >= 6:
            assert abs(d.qpos[:2] @ left - offset) < 0.15
            assert abs(d.qvel[:2] @ left) < 0.1
            expected_speed = 1.0 if mv == "hold_course" else 0.6
            assert abs(d.qvel[:2] @ forward - expected_speed) < 0.15
    assert d.qpos[:2] @ forward > 3


def test_hold_course_keeps_shifted_lane(pilot_model, pilot_data, maneuver_obs):
    m, d = pilot_model, pilot_data
    pilot = Pilot(m)
    for _ in range(round(6 / m.opt.timestep)):
        position_step(m, d, pilot.act("gap_left", maneuver_obs, flight_state(d)))
    lane_y = float(d.qpos[1])
    assert lane_y > 0.8
    for _ in range(round(6 / m.opt.timestep)):
        position_step(m, d, pilot.act("hold_course", maneuver_obs, flight_state(d)))
        assert abs(d.qpos[1] - lane_y) < 0.15


def test_maneuver_brake_move_brake_uses_new_anchor(pilot_model, pilot_data, maneuver_obs):
    m, d = pilot_model, pilot_data
    pilot = Pilot(m)
    anchors = []
    for _ in range(2):
        for _ in range(round(3 / m.opt.timestep)):
            position_step(m, d, pilot.act("hold_course", maneuver_obs, flight_state(d)))
        anchors.append(d.qpos[:3].copy())
        for step in range(round(8 / m.opt.timestep)):
            position_step(m, d, pilot.act("brake", maneuver_obs, flight_state(d)))
            if step * m.opt.timestep >= 6:
                assert np.linalg.norm(d.qpos[:3] - anchors[-1]) < 0.15
                assert np.linalg.norm(d.qvel[:3]) < 0.1
    assert anchors[1][0] - anchors[0][0] > 2


def test_pilot_reset_clears_height_heading_and_brake(pilot_model, pilot_data, maneuver_obs):
    pilot = Pilot(pilot_model)
    state = flight_state(pilot_data)
    pilot.act("gap_left", maneuver_obs, state)
    pilot.act("brake", maneuver_obs, state)
    pilot.reset()
    state["pos"] = np.array([2., -1., 2.])
    state["quat"] = axis_quaternion(2, 90)
    fresh = Pilot(pilot_model)
    for mv in ("brake", "gap_right", "hold_course", "brake"):
        np.testing.assert_allclose(pilot.act(mv, maneuver_obs, state),
                                   fresh.act(mv, maneuver_obs, state), atol=1e-12)


def test_pilot_preserves_observation_and_state(pilot_model, pilot_data, maneuver_obs):
    import copy

    pilot, state = Pilot(pilot_model), flight_state(pilot_data)
    obs_before, state_before = copy.deepcopy(maneuver_obs), copy.deepcopy(state)
    for mv in ("hold_course", "gap_left", "gap_right", "brake"):
        pilot.act(mv, maneuver_obs, state)
    assert maneuver_obs == obs_before
    for key in state:
        np.testing.assert_array_equal(state[key], state_before[key])


@pytest.mark.parametrize("mv,error", [("climb", NotImplementedError), ("reacquire", NotImplementedError),
                                     ("left", ValueError), (None, ValueError)])
def test_pilot_rejects_unsupported_actions(pilot_model, pilot_data, maneuver_obs, mv, error):
    with pytest.raises(error):
        Pilot(pilot_model).act(mv, maneuver_obs, flight_state(pilot_data))


@pytest.mark.parametrize("primed", [False, True])
@pytest.mark.parametrize("field,value", [("obs", None), ("pos", [0, 0]),
                                       ("quat", [0, 0, 0, 0]), ("angvel", [np.nan, 0, 0])])
def test_pilot_invalid_call_preserves_targets(pilot_model, pilot_data, maneuver_obs, primed, field, value):
    pilot, fresh = Pilot(pilot_model), Pilot(pilot_model)
    state, bad = flight_state(pilot_data), flight_state(pilot_data)
    if primed:
        pilot.act("brake", maneuver_obs, state)
        fresh.act("brake", maneuver_obs, state)
    bad["pos"] = np.array([2., -1., 2.])
    obs = value if field == "obs" else maneuver_obs
    if field != "obs":
        bad[field] = value
    with pytest.raises(ValueError):
        pilot.act("gap_left", obs, bad)
    for mv in ("brake", "hold_course", "gap_right"):
        np.testing.assert_allclose(pilot.act(mv, maneuver_obs, state),
                                   fresh.act(mv, maneuver_obs, state))
