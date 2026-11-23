"""MuJoCo Menagerie의 Skydio X2 드론 모델을 사용하는 장애물 코스."""

from itertools import combinations
import math
import os

import mujoco
import numpy as np

OBSTACLE_GEOM_GROUP = 1
TARGET_GEOM_GROUP = 2

ROVER_START_X = 1.25
ROVER_FINISH_X = 12.0
ROVER_SPEED = 1.0
_ROVER_WAYPOINTS = np.array([
    [ROVER_START_X, 0.0],
    [2.5, 0.0],
    [4.6, 0.55],
    [7.0, -0.40],
    [9.0, 0.40],
    [10.5, -0.35],
    [11.5, 0.0],
    [ROVER_FINISH_X, 0.0],
])
_PILLAR_NAMES = ("left_pillar", "right_pillar", "rear_pillar")
_PILLAR_XY = np.array([[7.0, 0.8], [9.0, -0.8], [10.5, 0.8]])
_PILLAR_RADIUS = 0.25
# 차량 중심에서 가장 먼 바퀴 외곽까지의 수평 거리를 올림한 값.
_ROVER_FOOTPRINT_RADIUS = 0.26
_ROVER_PILLAR_CLEARANCE = 0.10


def _model_path():
    # X2 모델 파일의 경로를 지정하면 인터넷 연결 없이 실행할 수 있다.
    if path := os.environ.get("DRONE_RL_X2_XML"):
        return path
    from robot_descriptions.skydio_x2_mj_description import MJCF_PATH
    return MJCF_PATH


def _rover_pose(time):
    x = min(ROVER_START_X + ROVER_SPEED * time, ROVER_FINISH_X)
    segment = np.searchsorted(_ROVER_WAYPOINTS[:, 0], x, side="left")
    segment = max(1, segment)
    (start_x, start_y), (end_x, end_y) = _ROVER_WAYPOINTS[segment - 1:segment + 1]
    fraction = (x - start_x) / (end_x - start_x)
    # 경유점에서 곡선이 꺾이지 않도록 양 끝의 기울기와 곡률이 0인 보간을 쓴다.
    blend = fraction**3 * (10 - 15 * fraction + 6 * fraction**2)
    slope = (end_y - start_y) / (end_x - start_x) * 30 * fraction**2 * (1 - fraction)**2
    return x, start_y + (end_y - start_y) * blend, math.atan(slope)


def _random_course(seed, rng):
    # 연속된 시드 10개(0~9, 10~19, ...)에 빔 구간 조합을 한 번씩 배정한다.
    orders = list(combinations(range(5), 2))
    if isinstance(seed, (int, np.integer)):
        block, index = divmod(int(seed), len(orders))
        order_rng = np.random.default_rng([block, 517])
        beam_slots = orders[order_rng.permutation(len(orders))[index]]
    else:
        beam_slots = orders[rng.integers(len(orders))]

    slots = np.linspace(2.5, 11.0, 5) + rng.uniform(-0.30, 0.30, 5)
    beam_x = slots[list(beam_slots)]
    pillar_x = np.delete(slots, beam_slots)
    pillars = []
    # 경로의 굽은 부분까지 포함해 차량 및 드론이 지날 통로를 확보한다.
    # 기둥의 x에서 이 반경보다 먼 경로점은 x 거리만으로도 충분히 떨어져 있다.
    corridor = max(0.80, _PILLAR_RADIUS + _ROVER_FOOTPRINT_RADIUS + _ROVER_PILLAR_CLEARANCE)
    for x, side in zip(pillar_x, rng.permutation([1, -1, rng.choice([-1, 1])])):
        lo = max(ROVER_START_X, x - corridor)
        hi = min(ROVER_FINISH_X, x + corridor)
        # 경유점 사이에서 y는 단조로 변하므로 양 끝과 내부 경유점에서 극값을 얻는다.
        ys = [_rover_pose((edge - ROVER_START_X) / ROVER_SPEED)[1] for edge in (lo, hi)]
        ys.extend(y for wx, y in _ROVER_WAYPOINTS if lo < wx < hi)
        edge_y = max(ys) if side > 0 else min(ys)
        pillars.append((x, edge_y + side * (corridor + rng.uniform(0, 0.45))))
    return beam_x, pillars


class Sim:
    """모터 4개의 추력을 한 번 입력할 때마다 시뮬레이션을 2밀리초 진행"""

    def __init__(self, seed, *, randomize_obstacles=False):
        self.seed = seed
        spawn_seed, obstacle_seed = np.random.SeedSequence(seed).spawn(2)
        spawn_rng = np.random.default_rng(spawn_seed)
        spawn_x, spawn_y = spawn_rng.uniform([-0.3, -0.5], [0.3, 0.5])
        beam_x = (2.0, 11.5)
        pillar_positions = _PILLAR_XY
        if randomize_obstacles:
            beam_x, pillar_positions = _random_course(seed, np.random.default_rng(obstacle_seed))
        spec = mujoco.MjSpec.from_file(str(_model_path()))
        spec.option.timestep = 0.002
        world = spec.worldbody
        geom = mujoco.mjtGeom

        # 밝은 하늘과 격자 바닥을 깔아 높이와 이동 거리를 눈으로 구별하기 쉽게 한다.
        spec.add_texture(type=mujoco.mjtTexture.mjTEXTURE_SKYBOX,
                         builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
                         rgb1=[0.54, 0.70, 0.91], rgb2=[0.18, 0.26, 0.40],
                         width=256, height=256)
        spec.add_texture(name="course_grid", type=mujoco.mjtTexture.mjTEXTURE_2D,
                         builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
                         rgb1=[0.30, 0.34, 0.40], rgb2=[0.42, 0.47, 0.54],
                         width=128, height=128)
        spec.add_material(name="course_floor", texrepeat=[20, 50]).textures[
            mujoco.mjtTextureRole.mjTEXROLE_RGB] = "course_grid"
        spec.visual.headlight.ambient[:] = [0.40, 0.40, 0.40]
        spec.visual.headlight.diffuse[:] = [0.55, 0.55, 0.55]
        spec.visual.global_.azimuth = 125
        spec.visual.global_.elevation = -22
        spec.stat.center[:] = [6, 0, 1]
        spec.stat.extent = 9
        world.add_light(name="course_sun", pos=[6, -4, 8], dir=[0, 0.45, -1],
                        type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
                        diffuse=[0.65, 0.65, 0.65], castshadow=True)
        world.add_geom(name="floor", type=geom.mjGEOM_PLANE, size=[20, 50, 0.1],
                       material="course_floor")

        # 코스 양쪽 바깥까지 빔을 뻗어 코스 안에서 옆으로 돌아갈 틈을 없앤다.
        for name, x in zip(("beam", "finish_beam"), beam_x):
            world.add_geom(name=name, type=geom.mjGEOM_CYLINDER,
                           fromto=[x, -45, 1.6, x, 45, 1.6], size=[0.15],
                           group=OBSTACLE_GEOM_GROUP,
                           rgba=[1, 0.72, 0.05, 1])
        for name, (x, y) in zip(_PILLAR_NAMES, pillar_positions):
            world.add_geom(name=name, type=geom.mjGEOM_CYLINDER, pos=[x, y, 1.25],
                           size=[_PILLAR_RADIUS, 1.25], group=OBSTACLE_GEOM_GROUP, rgba=[0.76, 0.77, 0.80, 1])

        # 차량은 드론 앞에서 출발해 두 빔 아래와 세 기둥 사이를 지나간다.
        target = world.add_body(name="target", mocap=True, pos=[ROVER_START_X, 0, 0.1])
        target.add_geom(name="rover_chassis", type=geom.mjGEOM_BOX,
                        size=[0.21, 0.12, 0.05], rgba=[0.89, 0.17, 0.07, 1],
                        contype=0, conaffinity=0, group=TARGET_GEOM_GROUP)
        target.add_geom(name="rover_cab", type=geom.mjGEOM_BOX,
                        size=[0.085, 0.10, 0.05], pos=[0.06, 0, 0.08],
                        rgba=[0.14, 0.21, 0.29, 1], contype=0, conaffinity=0, group=TARGET_GEOM_GROUP)
        for x, y in [(-0.14, -0.125), (-0.14, 0.125), (0.14, -0.125), (0.14, 0.125)]:
            target.add_geom(type=geom.mjGEOM_CYLINDER, size=[0.065, 0.0275],
                            pos=[x, y, -0.035], axisangle=[1, 0, 0, 90],
                            rgba=[0.10, 0.12, 0.15, 1], contype=0, conaffinity=0, group=TARGET_GEOM_GROUP)

        self.model = spec.compile()
        self._drone = self.model.body("x2").id
        joint = self.model.body_jntadr[self._drone]
        self._q = self.model.jnt_qposadr[joint]
        self._v = self.model.jnt_dofadr[joint]
        self._target = self.model.body_mocapid[self.model.body("target").id]
        # jev-drone 기본 코스와 같은 높이에서 시작한다.
        self.model.qpos0[self._q:self._q + 3] = [spawn_x, spawn_y, 1.6]
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
        self._target_unseen_since_s = None
        self._last_observation_s = 0.0
        self.collisions = 0
        self._touching = set()

    @property
    def t(self):
        return self.data.time

    @property
    def drone_state(self):
        """드론의 현재 상태를 복사해 반환한다.

        위치와 속도는 월드 좌표계 기준이다. 자세는 드론 좌표를 월드 좌표로
        회전시키는 쿼터니언(w, x, y, z)이고, 각속도는 드론 좌표계 기준이다.
        """
        q, v = self._q, self._v
        return {
            "pos": self.data.qpos[q:q + 3].copy(),
            "quat": self.data.qpos[q + 3:q + 7].copy(),
            "vel": self.data.qvel[v:v + 3].copy(),
            "angvel": self.data.qvel[v + 3:v + 6].copy(),
        }

    def step(self, ctrl):
        """모터 1~4의 추력을 뉴턴 단위로 적용하고 새로 발생한 접촉을 센다."""
        thrust = np.asarray(ctrl, dtype=float)
        if (thrust.shape != (4,) or not np.isfinite(thrust).all()
                or np.any(thrust < 0) or np.any(thrust > 13)):
            raise ValueError("Expected four finite motor thrusts between 0 and 13 N.")
        self.data.ctrl[:] = thrust
        mujoco.mj_step(self.model, self.data)
        x, y, yaw = _rover_pose(self.t)
        self.data.mocap_pos[self._target, :2] = [x, y]
        self.data.mocap_quat[self._target] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        # 한 스텝 진행한 뒤의 자세를 기준으로 접촉 정보와 물체 위치를 갱신한다.
        mujoco.mj_forward(self.model, self.data)
        touching = set()
        for contact in self.data.contact:
            a, b = contact.geom
            bodies = self.model.geom_bodyid
            if bodies[a] == self._drone and bodies[b] == 0:
                touching.add(b)
            elif bodies[b] == self._drone and bodies[a] == 0:
                touching.add(a)
        self.collisions += len(touching - self._touching)
        self._touching = touching
