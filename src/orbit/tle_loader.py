"""
tle_loader.py - TLE 데이터로 궤도 초기 조건 설정

[TLE란?]
    Two-Line Element의 약자로, 위성의 궤도 정보를 두 줄로 표현한
    국제 표준 형식입니다. NASA, NORAD, Space-Track.org 등에서
    모든 추적 위성의 TLE를 공개합니다.

    형식:
        Line 1: 위성 번호, 분류, 발사 연도, 궤도 감쇠율 등
        Line 2: 궤도 경사각, 승교점 적경, 이심률, 근지점 편각,
                평균 근점 이각, 평균 운동(하루 공전 횟수)

[이 파일이 하는 것]
    1. TLE 문자열을 파싱
    2. sgp4 라이브러리로 특정 시각의 위치/속도 계산
    3. OrbitSimulator에 주입할 초기 조건으로 변환

[좌표 변환]
    sgp4는 ECI(지구 중심 관성 좌표계) 기준 3D 위치를 반환합니다.
    이 프로젝트는 2D 시뮬레이터이므로 XY 평면(적도면)으로 투영합니다.
"""

import numpy as np
from datetime import datetime, timezone
from sgp4.api import Satrec, jday

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.orbit.orbital_constants import EARTH_RADIUS, MU_EARTH


# ── 내장 TLE 데이터 (오프라인 테스트용) ──────────────────────────
# Space-Track.org 또는 Celestrak에서 최신 TLE를 가져올 수 있음

PRESET_TLES = {
    "ISS": {
        "description": "International Space Station (~400 km, 51.6°)",
        "line1": "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9993",
        "line2": "2 25544  51.6400 208.9163 0006317  86.9959 273.1588 15.49815849421234",
    },
    "DOVE-1": {
        "description": "Planet Labs Dove CubeSat (~500 km, 97.4° SSO)",
        "line1": "1 39418U 13066L   24001.50000000  .00001234  00000-0  12345-3 0  9991",
        "line2": "2 39418  97.4000 100.0000 0010000  90.0000 270.0000 15.19000000123456",
    },
    "LEMUR-2": {
        "description": "Spire Global LEMUR-2 CubeSat (~500 km, 97.0° SSO)",
        "line1": "1 41789U 16059K   24001.50000000  .00000800  00000-0  98765-4 0  9998",
        "line2": "2 41789  97.0000 120.0000 0008000  45.0000 315.0000 15.15000000234567",
    },
    "CUSTOM": {
        "description": "Custom TLE (enter manually)",
        "line1": "",
        "line2": "",
    },
}


class TLELoader:
    """
    TLE 데이터를 파싱하고 궤도 초기 조건을 계산합니다.

    사용 예시:
        loader = TLELoader.from_preset("ISS")
        init   = loader.get_initial_conditions()
        sim    = OrbitSimulator(**init)
    """

    def __init__(self, name, line1, line2):
        """
        Args:
            name  (str): 위성 이름
            line1 (str): TLE 첫 번째 줄
            line2 (str): TLE 두 번째 줄
        """
        self.name  = name
        self.line1 = line1.strip()
        self.line2 = line2.strip()
        self.sat   = Satrec.twoline2rv(self.line1, self.line2)

        # TLE에서 직접 읽을 수 있는 궤도 요소
        self.inclination  = np.degrees(self.sat.inclo)   # 궤도 경사각 (도)
        self.eccentricity = self.sat.ecco                 # 이심률
        self.mean_motion  = self.sat.no_kozai             # 평균 운동 (rad/min)

        # 궤도 주기 (분)
        self.period_min = 2 * np.pi / self.mean_motion

        # 반장축 계산: a = (μ / n²)^(1/3)
        n_rad_s = self.mean_motion / 60.0  # rad/s
        self.semi_major_axis = (MU_EARTH / n_rad_s**2) ** (1/3)

        # 평균 고도 (근사)
        self.mean_altitude = self.semi_major_axis - EARTH_RADIUS

        print(f"[TLELoader] '{name}' 로드 완료")
        print(f"  궤도 경사각 : {self.inclination:.2f}°")
        print(f"  이심률      : {self.eccentricity:.6f}")
        print(f"  궤도 주기   : {self.period_min:.1f} 분")
        print(f"  평균 고도   : {self.mean_altitude/1000:.1f} km")

    @classmethod
    def from_preset(cls, preset_name):
        """내장 TLE 프리셋으로 초기화"""
        if preset_name not in PRESET_TLES:
            raise ValueError(f"알 수 없는 프리셋: {preset_name}. 선택 가능: {list(PRESET_TLES.keys())}")
        data = PRESET_TLES[preset_name]
        return cls(preset_name, data["line1"], data["line2"])

    @classmethod
    def from_string(cls, name, line1, line2):
        """직접 TLE 문자열로 초기화"""
        return cls(name, line1, line2)

    def get_state_at(self, dt=None):
        """
        특정 시각에서 위성의 ECI 위치와 속도를 계산합니다.

        Args:
            dt (datetime, optional): 계산할 시각. None이면 현재 시각 사용.

        Returns:
            dict: {
                'position_eci': [x, y, z] in km,
                'velocity_eci': [vx, vy, vz] in km/s,
                'datetime': 계산 시각
            }
        """
        if dt is None:
            dt = datetime.now(timezone.utc)

        # Julian Date 계산
        jd, fr = jday(dt.year, dt.month, dt.day,
                      dt.hour, dt.minute, dt.second + dt.microsecond/1e6)

        e, r, v = self.sat.sgp4(jd, fr)

        if e != 0:
            raise RuntimeError(f"SGP4 오류 코드 {e}: TLE가 유효하지 않거나 epoch에서 너무 멀리 벗어났습니다.")

        return {
            'position_eci': np.array(r),   # km
            'velocity_eci': np.array(v),   # km/s
            'datetime'    : dt,
        }

    def get_initial_conditions(self, dt=None):
        """
        OrbitSimulator에 주입할 2D 초기 조건을 계산합니다.

        [3D → 2D 투영]
            sgp4는 3D ECI 좌표를 반환합니다.
            이 프로젝트의 2D 시뮬레이터는 XY 평면을 사용하므로,
            3D 위치벡터를 XY 평면에 투영합니다.

            투영 방법:
                r_2d = sqrt(x² + y²)  (Z축 성분 무시)
                속도도 같은 방법으로 XY 성분만 사용

            이 투영은 적도 궤도(경사각 0°)에서 정확하고,
            경사각이 클수록 오차가 커지지만, 2D 시뮬레이터의
            교육적 목적에는 충분합니다.

        Returns:
            dict: OrbitSimulator 초기화에 필요한 파라미터
        """
        state = self.get_state_at(dt)

        r_eci = state['position_eci'] * 1000   # km → m
        v_eci = state['velocity_eci'] * 1000   # km/s → m/s

        # 3D 궤도 반지름 크기 보존
        r_mag      = np.linalg.norm(r_eci)
        altitude_2d = r_mag - EARTH_RADIUS

        # XY 평면에서의 위치 방향 단위벡터
        r_xy = np.array([r_eci[0], r_eci[1]])
        r_xy_norm = np.linalg.norm(r_xy)
        if r_xy_norm < 1.0:
            r_xy_dir = np.array([1.0, 0.0])
        else:
            r_xy_dir = r_xy / r_xy_norm

        # 2D 위치: 방향은 XY 투영, 크기는 3D 반지름 보존
        x0 = r_xy_dir[0] * r_mag
        y0 = r_xy_dir[1] * r_mag

        # 2D 속도: r에 수직(원형 궤도 조건 유지)
        # 3D 각운동량 Z성분 부호로 공전 방향 결정
        v_circ = np.sqrt(MU_EARTH / r_mag)
        L_z    = r_eci[0] * v_eci[1] - r_eci[1] * v_eci[0]
        sign   = 1.0 if L_z >= 0 else -1.0

        vx0 = -sign * r_xy_dir[1] * v_circ
        vy0 =  sign * r_xy_dir[0] * v_circ

        print(f"\n[TLELoader] 2D 초기 조건 계산 완료")
        print(f"  시각        : {state['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"  고도        : {altitude_2d/1000:.1f} km")
        print(f"  위치 (x, y) : ({x0/1000:.1f}, {y0/1000:.1f}) km")
        print(f"  속력        : {v_circ/1000:.3f} km/s")

        return {
            'x0'         : x0,
            'y0'         : y0,
            'vx0'        : vx0,
            'vy0'        : vy0,
            'altitude_2d': altitude_2d,
            'v_2d'       : v_circ,
            'name'       : self.name,
            'inclination': self.inclination,
            'period_min' : self.period_min,
        }


if __name__ == "__main__":
    print("=== ISS TLE 테스트 ===")
    loader = TLELoader.from_preset("ISS")
    ic     = loader.get_initial_conditions()

    print("\n=== OrbitSimulator에 연동 ===")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.orbit.orbit_simulator import OrbitSimulator

    sim  = OrbitSimulator(
        altitude=ic['altitude_2d'],
        sim_time=ic['period_min'] * 60,
        method='rk4',
        x0=ic['x0'], y0=ic['y0'],
        vx0=ic['vx0'], vy0=ic['vy0'],
    )
    data = sim.run()
    print(f"시뮬레이션 완료: 평균 고도 {data['altitude'].mean()/1000:.1f} km")