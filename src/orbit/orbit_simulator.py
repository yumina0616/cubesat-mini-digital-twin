"""
orbit_simulator.py - 2D CubeSat 원형 궤도 시뮬레이터

[물리 배경 - 소프트웨어 전공자를 위한 설명]

지구 주변을 도는 위성은 두 힘이 균형을 이룹니다:
  - 중력 (지구 중심 방향으로 잡아당김)
  - 원심력 (바깥으로 튕겨나가려는 관성)

[수치 적분 방법 선택]
    이 시뮬레이터는 두 가지 적분 방법을 지원합니다:

    1. Forward Euler (method='euler')
       - 가장 단순한 1차 방법
       - 매 스텝마다 현재 기울기 하나만 사용
       - 오차가 dt에 비례 → 장기 시뮬에서 고도 드리프트 발생

    2. Runge-Kutta 4 (method='rk4')  ← 권장
       - 4차 정확도
       - 한 스텝에 기울기를 4번 계산해서 가중 평균을 냄
       - 동일한 dt에서 Euler보다 오차가 수십 배 작음
       - 에너지 보존이 훨씬 잘 됨 → 고도가 안정적으로 유지됨

[좌표계]
    y
    ↑
    │   * ← 위성
    │  /
    │ /  r (지구 중심~위성 거리)
    │/
────┼────── x
지구 중심

위성 위치: (x, y) in meters
위성 속도: (vx, vy) in m/s
"""

import numpy as np
import sys
import os

# 프로젝트 루트를 경로에 추가 (상대 import 문제 방지)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.orbit.orbital_constants import (
    MU_EARTH, EARTH_RADIUS,
    DEFAULT_ALTITUDE, DEFAULT_SIM_TIME, DT
)


class OrbitSimulator:
    """
    2D 원형 궤도 시뮬레이터

    사용 예시:
        sim = OrbitSimulator(altitude=400_000)
        data = sim.run()
        print(data['altitude'])  # 고도 배열
    """

    def __init__(self, altitude=DEFAULT_ALTITUDE, dt=DT, sim_time=DEFAULT_SIM_TIME,
                 method='rk4'):
        """
        Args:
            altitude  (float): 궤도 고도 (m). 기본값 400km
            dt        (float): 시간 스텝 (s). 기본값 1초
            sim_time  (float): 전체 시뮬레이션 시간 (s). 기본값 6000초
            method    (str)  : 수치 적분 방법 'euler' 또는 'rk4'. 기본값 'rk4'
        """
        self.altitude = altitude
        self.dt = dt
        self.sim_time = sim_time
        self.method = method

        # 궤도 반지름 = 지구 반지름 + 고도
        self.r_orbit = EARTH_RADIUS + altitude

        # 원형 궤도 속도 계산: v = sqrt(μ / r)
        # 이 속도일 때 중력 = 원심력 → 완벽한 원형 궤도
        self.v_orbit = np.sqrt(MU_EARTH / self.r_orbit)

        # 궤도 주기 계산: T = 2π * r / v (초)
        self.period = 2 * np.pi * self.r_orbit / self.v_orbit

        print(f"[OrbitSimulator] 초기화 완료")
        print(f"  고도     : {altitude/1000:.1f} km")
        print(f"  궤도 반지름: {self.r_orbit/1000:.1f} km")
        print(f"  궤도 속도 : {self.v_orbit:.1f} m/s ({self.v_orbit/1000:.2f} km/s)")
        print(f"  궤도 주기 : {self.period/60:.1f} 분")
        print(f"  적분 방법 : {method.upper()}")

    def _compute_acceleration(self, x, y):
        """
        현재 위치 (x, y)에서 중력 가속도 계산

        뉴턴의 만유인력 법칙:
            F = μ * m / r²  (크기)
            방향: 지구 중심(원점)을 향함

        가속도 = F/m = μ / r²  (크기)
        x 성분: ax = -μ * x / r³
        y 성분: ay = -μ * y / r³

        Args:
            x, y (float): 위성 위치 (m)

        Returns:
            ax, ay (float): 가속도 (m/s²)
        """
        r = np.sqrt(x**2 + y**2)  # 지구 중심까지 거리
        ax = -MU_EARTH * x / r**3
        ay = -MU_EARTH * y / r**3
        return ax, ay

    def _derivatives(self, x, y, vx, vy):
        """
        상태 벡터의 시간 도함수 계산

        상태: [x, y, vx, vy]
        도함수: [vx, vy, ax, ay]

        RK4에서 k1~k4를 계산할 때 반복 호출됩니다.

        Args:
            x, y   (float): 위치 (m)
            vx, vy (float): 속도 (m/s)

        Returns:
            dx, dy, dvx, dvy (float): 각 상태 변수의 도함수
        """
        ax, ay = self._compute_acceleration(x, y)
        return vx, vy, ax, ay

    def _step_euler(self, x, y, vx, vy):
        """Forward Euler 1스텝"""
        ax, ay = self._compute_acceleration(x, y)
        x_new  = x  + vx * self.dt
        y_new  = y  + vy * self.dt
        vx_new = vx + ax * self.dt
        vy_new = vy + ay * self.dt
        return x_new, y_new, vx_new, vy_new

    def _step_rk4(self, x, y, vx, vy):
        """
        Runge-Kutta 4차 1스텝

        아이디어: 한 스텝을 나아갈 때 기울기를 4번 계산하고
        가중 평균(1/6, 2/6, 2/6, 1/6)을 내서 더 정확한 방향을 찾음

            k1: 현재 위치에서의 기울기
            k2: k1으로 반 스텝 나간 위치에서의 기울기
            k3: k2로 반 스텝 나간 위치에서의 기울기
            k4: k3로 한 스텝 나간 위치에서의 기울기

        오차가 dt⁴에 비례 → Euler(dt¹)보다 훨씬 정확
        """
        dt = self.dt

        # k1: 현재 상태에서의 도함수
        dx1, dy1, dvx1, dvy1 = self._derivatives(x, y, vx, vy)

        # k2: k1으로 dt/2 전진한 상태에서의 도함수
        dx2, dy2, dvx2, dvy2 = self._derivatives(
            x  + 0.5 * dt * dx1,
            y  + 0.5 * dt * dy1,
            vx + 0.5 * dt * dvx1,
            vy + 0.5 * dt * dvy1,
        )

        # k3: k2로 dt/2 전진한 상태에서의 도함수
        dx3, dy3, dvx3, dvy3 = self._derivatives(
            x  + 0.5 * dt * dx2,
            y  + 0.5 * dt * dy2,
            vx + 0.5 * dt * dvx2,
            vy + 0.5 * dt * dvy2,
        )

        # k4: k3로 dt 전진한 상태에서의 도함수
        dx4, dy4, dvx4, dvy4 = self._derivatives(
            x  + dt * dx3,
            y  + dt * dy3,
            vx + dt * dvx3,
            vy + dt * dvy3,
        )

        # 가중 평균으로 최종 업데이트
        x_new  = x  + (dt / 6) * (dx1  + 2*dx2  + 2*dx3  + dx4)
        y_new  = y  + (dt / 6) * (dy1  + 2*dy2  + 2*dy3  + dy4)
        vx_new = vx + (dt / 6) * (dvx1 + 2*dvx2 + 2*dvx3 + dvx4)
        vy_new = vy + (dt / 6) * (dvy1 + 2*dvy2 + 2*dvy3 + dvy4)

        return x_new, y_new, vx_new, vy_new

    def run(self):
        """
        시뮬레이션 실행

        self.method에 따라 Euler 또는 RK4로 적분합니다.

        Returns:
            dict: 시뮬레이션 결과 딕셔너리
                - time     : 시간 배열 (s)
                - x, y     : 위치 배열 (m)
                - vx, vy   : 속도 배열 (m/s)
                - altitude : 고도 배열 (m)
                - speed    : 속도 크기 배열 (m/s)
                - energy   : 비역학적 에너지 배열 (J/kg) ← 보존 여부 확인용
                - method   : 사용한 적분 방법
        """
        n_steps = int(self.sim_time / self.dt)

        time = np.zeros(n_steps)
        x    = np.zeros(n_steps)
        y    = np.zeros(n_steps)
        vx   = np.zeros(n_steps)
        vy   = np.zeros(n_steps)

        # 초기 조건
        x[0]  = self.r_orbit
        y[0]  = 0.0
        vx[0] = 0.0
        vy[0] = self.v_orbit

        # 적분 방법 선택
        step_fn = self._step_rk4 if self.method == 'rk4' else self._step_euler

        # 메인 루프
        for i in range(1, n_steps):
            time[i] = i * self.dt
            x[i], y[i], vx[i], vy[i] = step_fn(x[i-1], y[i-1], vx[i-1], vy[i-1])

        # 파생 물리량
        r_array  = np.sqrt(x**2 + y**2)
        altitude = r_array - EARTH_RADIUS
        speed    = np.sqrt(vx**2 + vy**2)

        # 비역학적 에너지: E = v²/2 - μ/r  (보존되어야 함)
        # Euler는 이 값이 드리프트, RK4는 거의 일정
        energy = 0.5 * speed**2 - MU_EARTH / r_array

        print(f"[OrbitSimulator] 시뮬레이션 완료 ({self.method.upper()}): {n_steps}스텝")
        print(f"  평균 고도      : {np.mean(altitude)/1000:.2f} km")
        print(f"  고도 편차 (std): {np.std(altitude)/1000:.4f} km")
        print(f"  에너지 드리프트: {(energy[-1] - energy[0]) / abs(energy[0]) * 100:.4f}%")

        return {
            'time'    : time,
            'x'       : x,
            'y'       : y,
            'vx'      : vx,
            'vy'      : vy,
            'altitude': altitude,
            'speed'   : speed,
            'r'       : r_array,
            'energy'  : energy,
            'method'  : self.method,
            'period_est': self.period,
        }


if __name__ == "__main__":
    # 직접 실행 테스트: python src/orbit/orbit_simulator.py
    sim = OrbitSimulator(altitude=400_000, sim_time=6000)
    data = sim.run()
    print(f"\n첫 번째 위치: x={data['x'][0]/1000:.1f} km, y={data['y'][0]/1000:.1f} km")
    print(f"마지막 고도: {data['altitude'][-1]/1000:.2f} km")