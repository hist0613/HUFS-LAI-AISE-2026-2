"""X2 motor allocation and attitude stabilization; guidance follows later."""

import mujoco
import numpy as np


class MotorMixer:
    """Allocate body +Z thrust (N) and body torque about the COM (N m).

    Outputs follow model actuator order. Total thrust is clipped to capacity;
    torque is uniformly reduced when necessary to preserve that total thrust.
    Supports four direct, unit-gain X2 motors with equal 0..max thrust limits.
    """

    def __init__(self, model):
        if model.nu != 4 or sorted(model.actuator(i).name for i in range(4)) != [
            "thrust1", "thrust2", "thrust3", "thrust4",
        ]:
            raise ValueError("Expected exactly four X2 motors")
        if not np.all(model.actuator_trntype == mujoco.mjtTrn.mjTRN_SITE):
            raise ValueError("Expected site-based motors")
        if (np.any(model.actuator_dyntype != mujoco.mjtDyn.mjDYN_NONE)
                or np.any(model.actuator_gaintype != mujoco.mjtGain.mjGAIN_FIXED)
                or np.any(model.actuator_biastype != mujoco.mjtBias.mjBIAS_NONE)
                or not np.allclose(model.actuator_gainprm[:, 0], 1)):
            raise ValueError("Expected direct unit-gain motors without bias")
        limits = model.actuator_ctrlrange
        self.max_thrust = float(limits[0, 1])
        if (not model.actuator_ctrllimited.all() or not np.isfinite(limits).all()
                or self.max_thrust <= 0
                or not np.allclose(limits, [0, self.max_thrust])):
            raise ValueError("Expected equal finite 0..max motor limits")

        body = model.body("x2").id
        columns = []
        for motor in range(4):
            site = model.actuator_trnid[motor, 0]
            if model.site_bodyid[site] != body:
                raise ValueError("Motor sites must belong directly to the X2")
            rotation = np.empty(9)
            mujoco.mju_quat2Mat(rotation, model.site_quat[site])
            rotation = rotation.reshape(3, 3)
            force = rotation @ model.actuator_gear[motor, :3]
            if not np.allclose(force, [0, 0, 1]):
                raise ValueError("Expected unit body +Z motor force")
            arm = model.site_pos[site] - model.body_ipos[body]
            torque = np.cross(arm, force) + rotation @ model.actuator_gear[motor, 3:]
            columns.append(np.r_[force[2], torque])
        allocation = np.column_stack(columns)
        if not np.allclose(allocation[1:].sum(axis=1), 0, atol=1e-10):
            raise ValueError("Equal X2 motor thrust must produce zero COM torque")
        if np.linalg.matrix_rank(allocation) != 4:
            raise ValueError("Motor layout cannot control all three torque axes")
        self._inverse = np.linalg.inv(allocation)

    def mix(self, thrust_n, torque_nm):
        """Return four bounded thrusts; reject malformed/non-finite requests."""
        torque = np.asarray(torque_nm, dtype=float)
        if np.ndim(thrust_n) != 0 or torque.shape != (3,):
            raise ValueError("Expected scalar thrust and three torque components")
        thrust = float(thrust_n)
        if not np.isfinite(thrust) or not np.isfinite(torque).all():
            raise ValueError("Thrust and torque must be finite")
        collective = np.clip(thrust, 0, 4 * self.max_thrust) / 4
        with np.errstate(over="ignore", invalid="ignore"):
            delta = self._inverse @ np.r_[0, torque]
        if not np.isfinite(delta).all():
            raise ValueError("Torque request is too large to represent")
        room = np.where(delta > 0, self.max_thrust - collective, collective)
        ratios = np.divide(room, np.abs(delta), out=np.ones(4), where=delta != 0)
        scale = min(1.0, float(ratios.min()))
        return np.clip(collective + scale * delta, 0, self.max_thrust)


class AttitudeController:
    """Track a fixed body->world wxyz attitude with zero target angular rate.

    State uses the team's quat/angvel keys; angvel is body-frame rad/s.
    Natural frequency is in rad/s. This controller does not regulate altitude.
    Call act once per physics step; the caller supplies total thrust in N.
    """

    def __init__(self, model, natural_frequency=6.0, damping_ratio=1.0):
        gains = np.asarray([natural_frequency, damping_ratio], dtype=float)
        if gains.shape != (2,) or not np.isfinite(gains).all() or np.any(gains <= 0):
            raise ValueError("Expected positive finite frequency and damping")
        self.mixer = MotorMixer(model)
        body = model.body("x2").id
        rotation = np.empty(9)
        mujoco.mju_quat2Mat(rotation, model.body_iquat[body])
        rotation = rotation.reshape(3, 3)
        # Principal inertia is expressed in the inertial frame, not body axes.
        self._inertia = rotation @ np.diag(model.body_inertia[body]) @ rotation.T
        self._kp = natural_frequency**2
        self._kd = 2 * damping_ratio * natural_frequency

    @staticmethod
    def _quaternion(value):
        quat = np.asarray(value, dtype=float)
        if quat.shape != (4,) or not np.isfinite(quat).all():
            raise ValueError("Expected a finite wxyz quaternion")
        norm = np.linalg.norm(quat)
        if not np.isclose(norm, 1.0, rtol=0, atol=1e-6):
            raise ValueError("Expected a unit quaternion")
        return quat / norm

    def act(self, thrust_n, target_quat, drone_state):
        """Return four motor thrusts using shortest-rotation PD feedback."""
        target = self._quaternion(target_quat)
        current = self._quaternion(drone_state["quat"])
        omega = np.asarray(drone_state["angvel"], dtype=float)
        if omega.shape != (3,) or not np.isfinite(omega).all():
            raise ValueError("Expected three finite body angular velocities")
        error = np.empty(3)
        mujoco.mju_subQuat(error, target, current)
        with np.errstate(over="ignore", invalid="ignore"):
            torque = self._inertia @ (self._kp * error - self._kd * omega)
            torque += np.cross(omega, self._inertia @ omega)
        return self.mixer.mix(thrust_n, torque)
