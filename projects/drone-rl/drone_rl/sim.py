"""MuJoCo Menagerie의 Skydio X2 드론 모델을 사용하는 고정 장애물 코스."""

import math
import os

import mujoco
import numpy as np

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


class Sim:
    """모터 4개의 추력을 한 번 입력할 때마다 시뮬레이션을 2밀리초 진행"""

    def __init__(self, seed):
        self.seed = seed  # 이후 장애물 배치를 재현할 때 쓰기 위해 저장해 둔다.
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
        for name, x in [("beam", 2), ("finish_beam", 11.5)]:
            world.add_geom(name=name, type=geom.mjGEOM_CYLINDER,
                           fromto=[x, -45, 1.6, x, 45, 1.6], size=[0.15],
                           rgba=[1, 0.72, 0.05, 1])
        for name, x, y in [("left_pillar", 7, 0.8), ("right_pillar", 9, -0.8),
                           ("rear_pillar", 10.5, 0.8)]:
            world.add_geom(name=name, type=geom.mjGEOM_CYLINDER, pos=[x, y, 1.25],
                           size=[0.25, 1.25], rgba=[0.76, 0.77, 0.80, 1])

        # 차량은 드론 앞에서 출발해 두 빔 아래와 세 기둥 사이를 지나간다.
        target = world.add_body(name="target", mocap=True, pos=[ROVER_START_X, 0, 0.1])
        target.add_geom(name="rover_chassis", type=geom.mjGEOM_BOX,
                        size=[0.21, 0.12, 0.05], rgba=[0.89, 0.17, 0.07, 1],
                        contype=0, conaffinity=0)
        target.add_geom(name="rover_cab", type=geom.mjGEOM_BOX,
                        size=[0.085, 0.10, 0.05], pos=[0.06, 0, 0.08],
                        rgba=[0.14, 0.21, 0.29, 1], contype=0, conaffinity=0)
        for x, y in [(-0.14, -0.125), (-0.14, 0.125), (0.14, -0.125), (0.14, 0.125)]:
            target.add_geom(type=geom.mjGEOM_CYLINDER, size=[0.065, 0.0275],
                            pos=[x, y, -0.035], axisangle=[1, 0, 0, 90],
                            rgba=[0.10, 0.12, 0.15, 1], contype=0, conaffinity=0)

        self.model = spec.compile()
        self._drone = self.model.body("x2").id
        joint = self.model.body_jntadr[self._drone]
        self._q = self.model.jnt_qposadr[joint]
        self._v = self.model.jnt_dofadr[joint]
        self._target = self.model.body_mocapid[self.model.body("target").id]
        # jev-drone 기본 코스와 같은 높이에서 시작한다.
        self.model.qpos0[self._q:self._q + 3] = [0, 0, 1.6]
        self.data = mujoco.MjData(self.model)
        mujoco.mj_forward(self.model, self.data)
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
