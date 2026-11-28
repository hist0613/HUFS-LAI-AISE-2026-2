"""X2 flight control and basic maneuver guidance."""

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


class AltitudeController:
    """Hold a world-frame height using vertical PD feedback and gravity feedforward.

    Call once per physics step with pos/vel in world-frame m and m/s.
    Default attitude is level, yaw zero; target_quat uses body->world wxyz.
    Intended for near-level flight, not inverted recovery or horizontal hold.
    No integral state: a fresh episode needs no controller reset.
    """

    def __init__(self, model):
        self.attitude = AttitudeController(model)
        self._mass = float(model.body_subtreemass[model.body("x2").id])
        gravity = model.opt.gravity
        if (not np.isfinite(gravity).all() or not np.allclose(gravity[:2], 0)
                or gravity[2] >= 0):
            raise ValueError("Expected gravity along world -Z")
        self._gravity = float(-gravity[2])
        self._kp, self._kd = 9.0, 6.0  # 3 rad/s, critical damping.

    def act(self, target_height_m, drone_state, target_quat=(1, 0, 0, 0)):
        """Return four 0..13 N motor thrusts for a feasible target height."""
        pos = np.asarray(drone_state["pos"], dtype=float)
        vel = np.asarray(drone_state["vel"], dtype=float)
        if (np.ndim(target_height_m) != 0 or not np.isfinite(target_height_m)
                or pos.shape != (3,) or vel.shape != (3,)
                or not np.isfinite(pos).all() or not np.isfinite(vel).all()):
            raise ValueError("Expected finite scalar height and three-vector pos/vel")
        quat = self.attitude._quaternion(drone_state["quat"])
        with np.errstate(over="ignore", invalid="ignore"):
            accel = self._kp * (float(target_height_m) - pos[2]) - self._kd * vel[2]
        if not np.isfinite(accel):
            raise ValueError("Altitude request is too large to represent")
        # Bound ascent/descent acceleration while retaining positive lift.
        accel = np.clip(accel, -0.5 * self._gravity, 0.5 * self._gravity)
        vertical_axis = 1 - 2 * (quat[1]**2 + quat[2]**2)
        # Limit compensation beyond 60 degrees to avoid division by zero.
        thrust = self._mass * (self._gravity + accel) / max(vertical_axis, 0.5)
        return self.attitude.act(thrust, target_quat, drone_state)


class VelocityController:
    """Track world-frame XY velocity (m/s), height (m), and yaw (radians).

    Speed is capped at 3 m/s, desired tilt at 20 degrees and lateral acceleration
    at 3 m/s^2. Intended for near-level flight; no obstacle or position control.
    Call every physics step. No accumulated state needs resetting between runs.
    """

    def __init__(self, model):
        self.altitude = AltitudeController(model)
        self._gravity = float(-model.opt.gravity[2])
        self._max_accel = min(3.0, self._gravity * np.tan(np.deg2rad(20)))

    def act(self, target_velocity_xy, target_height_m, drone_state, target_yaw_rad=0.0):
        """Return four motor thrusts; yaw does not rotate the world-frame command."""
        target = np.asarray(target_velocity_xy, dtype=float)
        velocity = np.asarray(drone_state["vel"], dtype=float)
        if (target.shape != (2,) or velocity.shape != (3,)
                or not np.isfinite(target).all() or not np.isfinite(velocity).all()
                or np.ndim(target_yaw_rad) != 0 or not np.isfinite(target_yaw_rad)):
            raise ValueError("Expected finite XY target, XYZ velocity and scalar yaw")
        with np.errstate(over="ignore", invalid="ignore"):
            speed = np.linalg.norm(target)
        if not np.isfinite(speed):
            raise ValueError("Velocity request is too large to represent")
        target = target * (3.0 / speed) if speed > 3.0 else target
        with np.errstate(over="ignore", invalid="ignore"):
            accel = 1.5 * (target - velocity[:2])
            magnitude = np.linalg.norm(accel)
        if not np.isfinite(magnitude):
            raise ValueError("Velocity error is too large to represent")
        if magnitude > self._max_accel:
            accel = accel * (self._max_accel / magnitude)
        # Aim body +Z along the required acceleration including gravity.
        up = np.r_[accel, self._gravity]
        up /= np.linalg.norm(up)
        heading = np.array([np.cos(target_yaw_rad), np.sin(target_yaw_rad), 0])
        left = np.cross(up, heading)
        left /= np.linalg.norm(left)  # Positive up[2] prevents a parallel heading.
        forward = np.cross(left, up)
        target_quat = np.empty(4)
        mujoco.mju_mat2Quat(target_quat, np.column_stack((forward, left, up)).ravel())
        return self.altitude.act(target_height_m, drone_state, target_quat)


class PositionController:
    """Track world XYZ position or brake back to the brake-entry pose.

    Call each physics step. Braking is not instantaneous and can overshoot;
    this controller does not avoid obstacles or plan a stopping distance.
    Reset for a new episode or when leaving brake for an external controller.
    """

    def __init__(self, model):
        self.velocity = VelocityController(model)
        self.reset()

    def reset(self):
        """Forget the latched brake position and yaw."""
        self._brake_position = None
        self._brake_yaw = None

    @staticmethod
    def _position(value):
        pos = np.asarray(value, dtype=float)
        if pos.shape != (3,) or not np.isfinite(pos).all():
            raise ValueError("Expected a finite world XYZ position")
        return pos

    def _control(self, target, drone_state, yaw):
        pos = self._position(drone_state["pos"])
        with np.errstate(over="ignore", invalid="ignore"):
            speed = 0.6 * (target[:2] - pos[:2])
            magnitude = np.linalg.norm(speed)
        if not np.isfinite(magnitude):
            raise ValueError("Position error is too large to represent")
        if magnitude > 1.5:
            speed = speed * (1.5 / magnitude)
        return self.velocity.act(speed, target[2], drone_state, yaw)

    def act(self, target_position_m, drone_state, target_yaw_rad=0.0):
        """Track XYZ (m) and yaw (rad); a valid command exits latched braking."""
        ctrl = self._control(self._position(target_position_m), drone_state, target_yaw_rad)
        self.reset()
        return ctrl

    def brake(self, drone_state):
        """Latch current XYZ/yaw on the first valid call, then hold that pose."""
        target, yaw = self._brake_position, self._brake_yaw
        if target is None:
            target = self._position(drone_state["pos"]).copy()
            quat = AttitudeController._quaternion(drone_state["quat"])
            rotation = np.empty(9)
            mujoco.mju_quat2Mat(rotation, quat)
            yaw = float(np.arctan2(rotation[3], rotation[0]))
        ctrl = self._control(target, drone_state, yaw)
        # Invalid input must not latch or replace an episode's brake target.
        self._brake_position, self._brake_yaw = target, yaw
        return ctrl


class Pilot:
    """Execute hold_course, gap_left, gap_right and brake each physics step.

    Latch initial height/yaw until reset. Gap entry shifts the lateral path 1 m;
    repeating the same action keeps that path, rather than accumulating shifts.
    obs is reserved for climb/target guidance. No obstacle reflex is provided.
    """

    def __init__(self, model):
        self.position = PositionController(model)
        self.reset()

    def reset(self):
        """Clear all maneuver/episode targets before starting a new episode."""
        self.position.reset()
        self._maneuver = self._lane = self._height = self._yaw = None

    def act(self, mv, obs, drone_state):
        """Return four motor thrusts using the team's maneuver/state interface."""
        if mv in ("climb", "reacquire"):
            raise NotImplementedError(f"Maneuver {mv!r} is not implemented yet")
        if mv not in ("hold_course", "gap_left", "gap_right", "brake"):
            raise ValueError(f"Unknown maneuver: {mv!r}")
        if not isinstance(obs, dict):
            raise ValueError("Expected an observation dict")
        pos = PositionController._position(drone_state["pos"])
        height, yaw = self._height, self._yaw
        if height is None:
            height = float(pos[2])
            quat = AttitudeController._quaternion(drone_state["quat"])
            rotation = np.empty(9)
            mujoco.mju_quat2Mat(rotation, quat)
            yaw = float(np.arctan2(rotation[3], rotation[0]))
        lane = self._lane
        if mv == "brake":
            ctrl = self.position.brake(drone_state)
        else:
            forward = np.array([np.cos(yaw), np.sin(yaw)])
            left = np.array([-forward[1], forward[0]])
            if mv != self._maneuver:
                offset = {"hold_course": 0, "gap_left": 1, "gap_right": -1}[mv]
                lane = pos[:2].copy() + offset * left
            with np.errstate(over="ignore", invalid="ignore"):
                lateral_error = float((lane - pos[:2]) @ left)
            if not np.isfinite(lateral_error):
                raise ValueError("Lateral position error is too large to represent")
            lateral_speed = np.clip(0.6 * lateral_error, -0.6, 0.6)
            forward_speed = 1.0 if mv == "hold_course" else 0.6
            velocity = forward_speed * forward + lateral_speed * left
            ctrl = self.position.velocity.act(velocity, height, drone_state, yaw)
            self.position.reset()  # Leaving brake allows a new anchor next time.
        # Commit targets only after the complete request has been validated.
        self._maneuver, self._lane, self._height, self._yaw = mv, lane, height, yaw
        return ctrl
