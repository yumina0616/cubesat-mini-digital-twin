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

    def __init__(self, altitude=DEFAULT_ALTITUDE, dt=DT, sim_time=DEFAULT_SIM_TIME):
        """
        Args:
            altitude  (float): 궤도 고도 (m). 기본값 400km
            dt        (float): 시간 스텝 (s). 기본값 1초
            sim_time  (float): 전체 시뮬레이션 시간 (s). 기본값 6000초
        """
        self.altitude = altitude
        self.dt = dt
        self.sim_time = sim_time

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

    def run(self):
        """
        시뮬레이션 실행 (Forward Euler 수치 적분)

        Forward Euler 방법:
            위치_다음 = 위치_현재 + 속도_현재 × dt
            속도_다음 = 속도_현재 + 가속도_현재 × dt

        마치 게임의 물리 엔진처럼, 매 프레임(dt=1초)마다
        위치와 속도를 조금씩 업데이트합니다.

        Returns:
            dict: 시뮬레이션 결과 딕셔너리
                - time       : 시간 배열 (s)
                - x, y       : 위치 배열 (m)
                - vx, vy     : 속도 배열 (m/s)
                - altitude   : 고도 배열 (m)
                - speed      : 속도 크기 배열 (m/s)
                - period_est : 추정 궤도 주기 (s)
        """
        n_steps = int(self.sim_time / self.dt)

        # 결과 저장 배열 미리 할당 (append보다 훨씬 빠름)
        time = np.zeros(n_steps)
        x    = np.zeros(n_steps)
        y    = np.zeros(n_steps)
        vx   = np.zeros(n_steps)
        vy   = np.zeros(n_steps)

        # ── 초기 조건 설정 ────────────────────────────────────────
        # 위성을 x축 위에서 시작 (오른쪽)
        # 속도는 y축 방향 (위) → 반시계 방향으로 공전
        x[0]  = self.r_orbit   # 초기 x 위치 (지구 중심에서 궤도 반지름만큼)
        y[0]  = 0.0             # 초기 y 위치
        vx[0] = 0.0             # 초기 x 속도
        vy[0] = self.v_orbit    # 초기 y 속도 (원형 궤도 속도)

        # ── 메인 시뮬레이션 루프 ─────────────────────────────────
        for i in range(1, n_steps):
            time[i] = i * self.dt

            # 현재 위치에서 가속도 계산
            ax, ay = self._compute_acceleration(x[i-1], y[i-1])

            # Forward Euler: 위치 업데이트
            x[i]  = x[i-1]  + vx[i-1] * self.dt
            y[i]  = y[i-1]  + vy[i-1] * self.dt

            # Forward Euler: 속도 업데이트
            vx[i] = vx[i-1] + ax * self.dt
            vy[i] = vy[i-1] + ay * self.dt

        # ── 파생 물리량 계산 ─────────────────────────────────────
        # 고도 = 지구 중심 거리 - 지구 반지름
        r_array  = np.sqrt(x**2 + y**2)
        altitude = r_array - EARTH_RADIUS

        # 속도 크기
        speed = np.sqrt(vx**2 + vy**2)

        print(f"[OrbitSimulator] 시뮬레이션 완료: {n_steps}스텝")
        print(f"  평균 고도: {np.mean(altitude)/1000:.2f} km")
        print(f"  평균 속도: {np.mean(speed):.2f} m/s")

        return {
            'time'      : time,
            'x'         : x,
            'y'         : y,
            'vx'        : vx,
            'vy'        : vy,
            'altitude'  : altitude,
            'speed'     : speed,
            'r'         : r_array,
            'period_est': self.period,
        }


if __name__ == "__main__":
    # 직접 실행 테스트: python src/orbit/orbit_simulator.py
    sim = OrbitSimulator(altitude=400_000, sim_time=6000)
    data = sim.run()
    print(f"\n첫 번째 위치: x={data['x'][0]/1000:.1f} km, y={data['y'][0]/1000:.1f} km")
    print(f"마지막 고도: {data['altitude'][-1]/1000:.2f} km")