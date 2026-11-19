"""Independent X2 fixture for later pilot tests; no course or controller yet.

Model: MuJoCo Menagerie / Skydio X2 (Apache-2.0), via robot_descriptions.
Run with Python 3.12: python -m pytest tests/test_pilot.py -v
The first model import downloads Menagerie and requires git and network access.
"""

import mujoco
import numpy as np
import pytest


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
