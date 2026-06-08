"""
attitude_model.py - CubeSat 1축 자세 동역학 모델

[물리 배경 - 소프트웨어 전공자를 위한 설명]

"자세(Attitude)"란 위성이 우주 공간에서 어느 방향을 향하고 있는지를 말합니다.
이 파일은 위성이 회전할 때 어떻게 움직이는지를 시뮬레이션합니다.

[1축 회전 역학]
    뉴턴 제2법칙의 회전 버전:
        τ = I × α

    τ (tau)  : 토크 (N·m)  ← 외부에서 가해지는 회전력 (제어 입력)
    I        : 관성 모멘트 (kg·m²) ← 얼마나 회전하기 어려운지
    α (alpha): 각가속도 (rad/s²) ← 각속도의 변화율

    풀어쓰면:
        각가속도 = 토크 / 관성모멘트
        각속도   = 각속도 + 각가속도 × dt
        자세각   = 자세각 + 각속도   × dt

[목표]
    PID 제어기가 토크를 출력하면,
    이 모델이 그 토크를 받아서 위성의 각도가 어떻게 변하는지 계산합니다.
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class AttitudeModel:
    """
    CubeSat 1축 자세 동역학 모델 (단순 강체 회전)

    사용 예시:
        model = AttitudeModel(initial_angle=30.0)   # 초기 자세각 30도
        model.step(torque=0.001)                     # 토크 적용 → 1스텝 진행
        print(model.angle_deg)                       # 현재 각도 출력
    """

    def __init__(
        self,
        inertia=0.002,        # 관성 모멘트 (kg·m²) - 1U CubeSat 기준
        initial_angle=30.0,   # 초기 자세각 (도)
        initial_rate=0.0,     # 초기 각속도 (도/s)
        dt=0.1,               # 시간 스텝 (s) - 자세제어는 궤도보다 빠른 주기 필요
        disturbance_std=1e-5, # 외란 토크 표준편차 (N·m) - 우주 환경 노이즈
    ):
        """
        Args:
            inertia        (float): 관성 모멘트 (kg·m²)
            initial_angle  (float): 초기 자세각 (도)
            initial_rate   (float): 초기 각속도 (도/s)
            dt             (float): 시간 스텝 (s)
            disturbance_std(float): 외란 노이즈 크기. 0이면 외란 없음
        """
        self.I   = inertia
        self.dt  = dt
        self.disturbance_std = disturbance_std

        # 상태 변수 (내부적으로 라디안 사용, 외부에는 도 단위로 노출)
        self._angle = np.deg2rad(initial_angle)   # 자세각 (rad)
        self._rate  = np.deg2rad(initial_rate)    # 각속도 (rad/s)

        # 히스토리 기록용
        self.time_history  = [0.0]
        self.angle_history = [initial_angle]
        self.rate_history  = [initial_rate]
        self.torque_history = [0.0]

        self._t = 0.0  # 현재 시각

        print(f"[AttitudeModel] 초기화 완료")
        print(f"  관성 모멘트  : {inertia:.4f} kg·m²")
        print(f"  초기 자세각  : {initial_angle:.1f}°")
        print(f"  시간 스텝    : {dt} s")

    @property
    def angle_deg(self):
        """현재 자세각 (도)"""
        return np.rad2deg(self._angle)

    @property
    def rate_deg(self):
        """현재 각속도 (도/s)"""
        return np.rad2deg(self._rate)

    def step(self, torque):
        """
        1 타임스텝 진행

        외부 토크를 받아 Forward Euler로 상태를 업데이트합니다.

        Args:
            torque (float): 제어 토크 (N·m). 양수 = 반시계 방향

        Returns:
            angle_deg (float): 업데이트된 자세각 (도)
        """
        # 외란 토크 (우주 환경의 미세한 노이즈: 태양풍, 중력 기울기 등)
        disturbance = np.random.normal(0, self.disturbance_std)
        total_torque = torque + disturbance

        # τ = I × α  →  α = τ / I
        angular_accel = total_torque / self.I

        # Forward Euler 적분
        self._rate  += angular_accel * self.dt
        self._angle += self._rate    * self.dt

        # 각도를 -π ~ π 범위로 정규화 (360도 넘어가지 않게)
        self._angle = np.arctan2(np.sin(self._angle), np.cos(self._angle))

        self._t += self.dt

        # 히스토리 저장
        self.time_history.append(self._t)
        self.angle_history.append(self.angle_deg)
        self.rate_history.append(self.rate_deg)
        self.torque_history.append(torque)

        return self.angle_deg

    def reset(self, initial_angle=0.0, initial_rate=0.0):
        """상태 초기화 (새 시뮬레이션 시작할 때)"""
        self._angle = np.deg2rad(initial_angle)
        self._rate  = np.deg2rad(initial_rate)
        self._t     = 0.0
        self.time_history   = [0.0]
        self.angle_history  = [initial_angle]
        self.rate_history   = [initial_rate]
        self.torque_history = [0.0]

    def get_history(self):
        """전체 히스토리를 딕셔너리로 반환"""
        return {
            'time'  : np.array(self.time_history),
            'angle' : np.array(self.angle_history),
            'rate'  : np.array(self.rate_history),
            'torque': np.array(self.torque_history),
        }


if __name__ == "__main__":
    # 빠른 동작 확인: 토크 없이 관성으로만 회전하는지 테스트
    model = AttitudeModel(initial_angle=10.0, initial_rate=5.0, disturbance_std=0)
    for _ in range(5):
        angle = model.step(torque=0.0)
        print(f"  t={model._t:.1f}s  angle={angle:.4f}°  rate={model.rate_deg:.4f}°/s")