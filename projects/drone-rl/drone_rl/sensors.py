"""MuJoCo의 거리 탐색으로 판단 모듈에 전달할 장면을 요약한다."""

import math

import mujoco
import numpy as np

from .sim import OBSTACLE_GEOM_GROUP, TARGET_GEOM_GROUP

MAX_RANGE_M = 25.0
BLOCKED_RANGE_M = 3.0
_SECTOR_NAMES = ("far_left", "left", "center", "right", "far_right")
# 원본 jev-drone의 카메라 해상도, 시야와 장애물 탐색 범위.
_CAMERA_WIDTH, _CAMERA_HEIGHT = 96, 72
_CAMERA_TILT_RAD = math.radians(-12)
_CAMERA_TAN_VERTICAL = math.tan(math.radians(110 / 2))
_CAMERA_TAN_HORIZONTAL = _CAMERA_TAN_VERTICAL * _CAMERA_WIDTH / _CAMERA_HEIGHT
_THREAT_HALF_FOV_DEG = 40
_AHEAD_HALF_FOV_DEG = 12
_IGNORE_BELOW_M = 0.5
_LEVEL_BAND_M = 0.75
_NEAR_BAND_M, _FAR_BAND_M = 0.8, 2.2

# 화면 왼쪽은 양수다. 정면은 장애물 탐색 범위 안의 더 좁은 영역이다.
_columns = np.linspace(1, -1, _CAMERA_WIDTH) * _CAMERA_TAN_HORIZONTAL
_columns = _columns[np.abs(_columns) <= math.tan(math.radians(_THREAT_HALF_FOV_DEG))]
_rows = np.linspace(1, -1, _CAMERA_HEIGHT) * _CAMERA_TAN_VERTICAL
_horizontal, _vertical = np.meshgrid(_columns, _rows)
_CAMERA_RAYS = np.stack((np.ones_like(_horizontal), _horizontal, _vertical), axis=-1)
_CAMERA_RAYS /= np.linalg.norm(_CAMERA_RAYS, axis=-1, keepdims=True)
_AHEAD_COLUMNS = np.abs(_columns) <= math.tan(math.radians(_AHEAD_HALF_FOV_DEG))

_OBSTACLE_MASK = np.zeros(mujoco.mjNGROUP, dtype=np.uint8)
_OBSTACLE_MASK[OBSTACLE_GEOM_GROUP] = 1
_LINE_OF_SIGHT_MASK = _OBSTACLE_MASK.copy()
_LINE_OF_SIGHT_MASK[TARGET_GEOM_GROUP] = 1


def _obstacle_summary(sim, origin, axes):
    rays = _CAMERA_RAYS @ axes
    distances = np.empty(rays.shape[:2])
    geom_ids = np.empty(distances.size, dtype=np.int32)
    mujoco.mj_multiRay(
        sim.model, sim.data, origin, rays.ravel(), _OBSTACLE_MASK, True, -1,
        geom_ids, distances.ravel(), None, distances.size, MAX_RANGE_M,
    )
    hits = (distances >= 0) & (distances <= MAX_RANGE_M)
    heights = distances * rays[:, :, 2]
    lateral = np.where(hits & (heights > -_IGNORE_BELOW_M), distances, MAX_RANGE_M)
    sectors = {
        name: float(samples.min())
        for name, samples in zip(_SECTOR_NAMES, np.array_split(lateral, len(_SECTOR_NAMES), axis=1))
    }

    ahead = distances[:, _AHEAD_COLUMNS]
    height = heights[:, _AHEAD_COLUMNS]
    seen = hits[:, _AHEAD_COLUMNS]

    def nearest_in_band(mask):
        return float(ahead[seen & mask].min(initial=MAX_RANGE_M))

    return {
        "sector_range_m": sectors,
        "sectors_blocked": sum(distance < BLOCKED_RANGE_M for distance in sectors.values()),
        "path_ahead_m": min(sectors["left"], sectors["center"], sectors["right"]),
        "free_ahead_above_m": nearest_in_band((height >= _NEAR_BAND_M) & (height <= _FAR_BAND_M)),
        "free_ahead_level_m": nearest_in_band(np.abs(height) <= _LEVEL_BAND_M),
        "free_ahead_below_m": (
            nearest_in_band((height <= -_NEAR_BAND_M) & (height >= -_FAR_BAND_M))
            if origin[2] > _NEAR_BAND_M else 0.0
        ),
        "nearest_obstacle_m": min(sectors.values()),
    }


def _observe_target(sim, drone, yaw, axes):
    now = float(sim.t)
    if now < sim._last_observation_s:
        sim._target_unseen_since_s = None
    sim._last_observation_s = now

    target_body = sim.data.body("target").id
    hit = np.empty(1, dtype=np.int32)
    for name in ("rover_chassis", "rover_cab"):
        target = sim.data.geom(name)
        offset = target.xpos - drone.xpos
        distance = float(np.linalg.norm(offset))
        depth, left, up = axes @ offset
        if (not 0 < distance <= MAX_RANGE_M
                or depth <= 0
                or abs(left) > depth * _CAMERA_TAN_HORIZONTAL
                or abs(up) > depth * _CAMERA_TAN_VERTICAL):
            continue

        heading = math.atan2(offset[1], offset[0]) - yaw
        bearing = (math.degrees(heading) + 180) % 360 - 180

        intersection = mujoco.mj_ray(
            sim.model, sim.data, drone.xpos, offset / distance, _LINE_OF_SIGHT_MASK, True, drone.id, hit,
        )
        if 0 <= intersection <= distance and sim.model.geom_bodyid[hit[0]] == target_body:
            sim._target_unseen_since_s = None
            return {"visible": True, "bearing_deg": bearing, "range_m": distance, "unseen_for_s": 0.0}

    if sim._target_unseen_since_s is None:
        sim._target_unseen_since_s = now
    return {
        "visible": False,
        "bearing_deg": None,
        "range_m": None,
        "unseen_for_s": now - sim._target_unseen_since_s,
    }


def observe(sim):
    """거리(m), 방향(왼쪽이 +인 도 단위), 타깃 비가시 시간(초)을 반환한다.

    드론 헤딩과 카메라 각도를 기준으로 격자 방향에 거리선을 쏜다.
    위·아래 여유는 전방 장애물의 상대 높이 구간별로 계산한다.
    비가시 시간은 첫 미검출 관측부터 센다.
    """
    drone = sim.data.body("x2")
    origin = drone.xpos
    rotation = drone.xmat.reshape(3, 3)
    forward = rotation[:2, 0]
    if np.linalg.norm(forward) < 1e-8:
        forward = np.array([rotation[1, 1], -rotation[0, 1]])
    yaw = math.atan2(forward[1], forward[0])

    heading = np.array([math.cos(yaw), math.sin(yaw), 0.0])
    left = np.array([-heading[1], heading[0], 0.0])
    vertical = np.array([0.0, 0.0, 1.0])
    tilt_cos, tilt_sin = math.cos(_CAMERA_TILT_RAD), math.sin(_CAMERA_TILT_RAD)
    axes = np.array((tilt_cos * heading + tilt_sin * vertical, left, -tilt_sin * heading + tilt_cos * vertical))
    scene = _obstacle_summary(sim, origin, axes)
    scene["target"] = _observe_target(sim, drone, yaw, axes)
    return scene
