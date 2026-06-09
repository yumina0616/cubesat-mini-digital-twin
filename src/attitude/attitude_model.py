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

[수치 적분 방법 선택]
    orbit_simulator.py와 동일하게 두 가지 방법을 지원합니다.

    1. Forward Euler (method='euler')
       - 상태: [θ, ω]  (자세각, 각속도)
       - 도함수: [ω, τ/I]
       - 1차 정확도 → dt가 크면 불안정 (이 프로젝트에서 dt=0.1s 시 발산 경험)

    2. Runge-Kutta 4 (method='rk4')  ← 권장
       - 동일한 dt에서 훨씬 안정적
       - 에너지(각운동량) 보존이 더 잘 됨
       - dt=0.1s에서도 안정적으로 수렴
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class AttitudeModel:
    """
    CubeSat 1축 자세 동역학 모델 (단순 강체 회전)

    사용 예시:
        model = AttitudeModel(initial_angle=30.0, method='rk4')
        model.step(torque=0.001)
        print(model.angle_deg)
    """

    def __init__(
        self,
        inertia=0.002,
        initial_angle=30.0,
        initial_rate=0.0,
        dt=0.01,
        disturbance_std=1e-5,
        method='rk4',
    ):
        """
        Args:
            inertia        (float): 관성 모멘트 (kg·m²)
            initial_angle  (float): 초기 자세각 (도)
            initial_rate   (float): 초기 각속도 (도/s)
            dt             (float): 시간 스텝 (s)
            disturbance_std(float): 외란 노이즈 크기. 0이면 외란 없음
            method         (str)  : 'euler' 또는 'rk4'. 기본값 'rk4'
        """
        self.I               = inertia
        self.dt              = dt
        self.disturbance_std = disturbance_std
        self.method          = method

        self._angle = np.deg2rad(initial_angle)
        self._rate  = np.deg2rad(initial_rate)

        self.time_history   = [0.0]
        self.angle_history  = [initial_angle]
        self.rate_history   = [initial_rate]
        self.torque_history = [0.0]

        self._t = 0.0

        print(f"[AttitudeModel] 초기화 완료")
        print(f"  관성 모멘트  : {inertia:.4f} kg·m²")
        print(f"  초기 자세각  : {initial_angle:.1f}°")
        print(f"  시간 스텝    : {dt} s")
        print(f"  적분 방법    : {method.upper()}")

    # ── Properties ───────────────────────────────────────────────

    @property
    def angle_deg(self):
        """현재 자세각 (도)"""
        return np.rad2deg(self._angle)

    @property
    def rate_deg(self):
        """현재 각속도 (도/s)"""
        return np.rad2deg(self._rate)

    # ── 적분 내부 메서드 ─────────────────────────────────────────

    def _derivatives(self, angle, rate, torque):
        """
        상태 [angle, rate]의 시간 도함수 계산

        dangle/dt = rate
        drate/dt  = torque / I  (α = τ / I)

        RK4에서 k1~k4 계산 시 반복 호출됩니다.
        """
        d_angle = rate
        d_rate  = torque / self.I
        return d_angle, d_rate

    def _step_euler(self, angle, rate, torque):
        """Forward Euler 1스텝"""
        d_angle, d_rate = self._derivatives(angle, rate, torque)
        new_angle = angle + d_angle * self.dt
        new_rate  = rate  + d_rate  * self.dt
        return new_angle, new_rate

    def _step_rk4(self, angle, rate, torque):
        """
        Runge-Kutta 4차 1스텝

        자세 제어에서 토크는 매 스텝마다 PID가 결정하는 외부 입력이므로
        한 스텝 안에서 토크가 일정하다고 가정하고 RK4를 적용합니다.
        """
        dt = self.dt

        da1, dr1 = self._derivatives(angle,                rate,                torque)
        da2, dr2 = self._derivatives(angle + 0.5*dt*da1,  rate + 0.5*dt*dr1,  torque)
        da3, dr3 = self._derivatives(angle + 0.5*dt*da2,  rate + 0.5*dt*dr2,  torque)
        da4, dr4 = self._derivatives(angle +    dt*da3,   rate +    dt*dr3,   torque)

        new_angle = angle + (dt / 6) * (da1 + 2*da2 + 2*da3 + da4)
        new_rate  = rate  + (dt / 6) * (dr1 + 2*dr2 + 2*dr3 + dr4)
        return new_angle, new_rate

    # ── 메인 스텝 ─────────────────────────────────────────────────

    def step(self, torque):
        """
        1 타임스텝 진행

        Args:
            torque (float): 제어 토크 (N·m)

        Returns:
            angle_deg (float): 업데이트된 자세각 (도)
        """
        disturbance  = np.random.normal(0, self.disturbance_std)
        total_torque = torque + disturbance

        step_fn = self._step_rk4 if self.method == 'rk4' else self._step_euler
        new_angle, new_rate = step_fn(self._angle, self._rate, total_torque)

        # 각도를 -π ~ π 범위로 정규화
        self._angle = np.arctan2(np.sin(new_angle), np.cos(new_angle))
        self._rate  = new_rate
        self._t    += self.dt

        self.time_history.append(self._t)
        self.angle_history.append(self.angle_deg)
        self.rate_history.append(self.rate_deg)
        self.torque_history.append(torque)

        return self.angle_deg

    def reset(self, initial_angle=0.0, initial_rate=0.0):
        """상태 초기화"""
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
            'method': self.method,
        }


if __name__ == "__main__":
    # Euler vs RK4 비교 테스트 (dt=0.1s — Euler가 불안정했던 조건)
    from src.attitude.pid_controller import PIDController

    print("=== dt=0.1s 에서 Euler vs RK4 안정성 비교 ===\n")
    for method in ['euler', 'rk4']:
        model = AttitudeModel(initial_angle=30.0, disturbance_std=0, dt=0.1, method=method)
        pid   = PIDController(Kp=0.4, Ki=0.005, Kd=0.05, dt=0.1,
                              output_limit=0.05, integral_limit=5.0)
        for _ in range(int(20.0 / 0.1)):
            model.step(pid.compute(0.0, model.angle_deg))
        final = model.get_history()['angle'][-1]
        print(f"  {method.upper():5s} | 최종 자세각: {final:.4f}°")