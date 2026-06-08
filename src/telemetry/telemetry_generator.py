"""
telemetry_generator.py - CubeSat 텔레메트리 데이터 생성기

[텔레메트리(Telemetry)란?]
    위성이 지상국으로 전송하는 상태 데이터 패킷입니다.
    "지금 나 이런 상태야"를 주기적으로 보내는 것.

    실제 CubeSat이 보내는 데이터 예시:
        - 배터리 전압/전류
        - 온도 (태양 면 / 음영 면)
        - 자세각
        - 고도, 속도
        - 통신 가능 여부 (지상국 가시 범위 내인지)

[이 파일이 하는 것]
    궤도 시뮬레이터 + 자세 모델의 출력을 받아서
    현실적인 텔레메트리 데이터프레임(CSV)을 생성합니다.

    배터리, 온도, 통신 가능 여부는 물리 기반 단순 모델로 계산합니다.
"""

import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.orbit.orbital_constants import EARTH_RADIUS


class TelemetryGenerator:
    """
    궤도 + 자세 데이터를 받아 텔레메트리 CSV를 생성합니다.

    사용 예시:
        gen = TelemetryGenerator(orbit_data, attitude_data)
        df  = gen.generate()
        gen.save(df, 'data/sample_telemetry.csv')
    """

    # ── 위성 하드웨어 파라미터 (1U CubeSat 기준) ──────────────────
    BATTERY_CAPACITY   = 10.0    # Wh - 배터리 총 용량
    SOLAR_POWER        = 2.0     # W  - 태양 조사 시 발전량
    IDLE_POWER         = 0.8     # W  - 대기 소비 전력
    ACTIVE_POWER       = 1.5     # W  - 통신 중 소비 전력

    TEMP_SUNLIT        = 40.0    # °C - 태양 면 온도
    TEMP_ECLIPSE       = -20.0   # °C - 음영 면 온도
    TEMP_NOISE_STD     = 2.0     # °C - 온도 센서 노이즈

    # 지상국 위치 (위도/경도) - 서울 기준
    GS_LAT = 37.5665
    GS_LON = 126.9780
    GS_ELEVATION_MIN = 5.0  # 도 - 통신 가능 최소 앙각

    def __init__(self, orbit_data, attitude_data, sample_interval=10):
        """
        Args:
            orbit_data      (dict): OrbitSimulator.run() 반환값
            attitude_data   (dict): AttitudeModel.get_history() 반환값
            sample_interval (int) : 텔레메트리 샘플링 간격 (초)
                                    실제 위성은 1~10초에 한 번 전송
        """
        self.orbit    = orbit_data
        self.attitude = attitude_data
        self.dt_sample = sample_interval

        print(f"[TelemetryGenerator] 초기화 완료")
        print(f"  궤도 데이터  : {len(orbit_data['time'])} 포인트")
        print(f"  샘플 간격    : {sample_interval}초")

    # ──────────────────────────────────────────────────────────────
    # 내부 모델 함수들
    # ──────────────────────────────────────────────────────────────

    def _is_sunlit(self, x, y):
        """
        위성이 태양을 받는지 (음영 여부) 판단하는 단순 모델

        실제로는 태양 벡터와 궤도면 계산이 필요하지만,
        여기서는 x > 0 (지구 오른쪽 반구) = 태양 조사로 단순화합니다.

        Args:
            x, y (array): 위성 위치 (m)
        Returns:
            bool array: True = 태양 조사
        """
        # 지구 그림자 모델: x < 0이고 y가 작으면 음영
        # (태양이 +x 방향에서 온다고 가정)
        in_shadow = (x < 0) & (np.abs(y) < EARTH_RADIUS * 1.2)
        return ~in_shadow

    def _compute_battery(self, sunlit_array, active_array):
        """
        배터리 충방전 모델

        단순 에너지 균형:
            충전 중: 배터리 += (발전량 - 소비) × dt
            방전 중: 배터리 -= 소비 × dt

        Args:
            sunlit_array (bool array): 태양 조사 여부
            active_array (bool array): 통신 활성 여부
        Returns:
            battery_pct (array): 배터리 잔량 (0~100%)
        """
        n = len(sunlit_array)
        battery_wh  = np.zeros(n)
        battery_wh[0] = self.BATTERY_CAPACITY * 0.8  # 초기 충전량 80%

        for i in range(1, n):
            power_in  = self.SOLAR_POWER if sunlit_array[i] else 0.0
            power_out = self.ACTIVE_POWER if active_array[i] else self.IDLE_POWER
            net_power = power_in - power_out  # W

            # Wh로 변환 (샘플 간격이 dt_sample 초)
            delta_wh = net_power * (self.dt_sample / 3600.0)
            battery_wh[i] = np.clip(
                battery_wh[i-1] + delta_wh,
                0.0,
                self.BATTERY_CAPACITY
            )

        return (battery_wh / self.BATTERY_CAPACITY) * 100.0  # %

    def _compute_temperature(self, sunlit_array):
        """
        온보드 온도 모델

        태양 조사 → 따뜻함, 음영 → 차가움
        현실적인 열 시상수(열이 천천히 변하는 특성)를 단순 지수 이동평균으로 모사

        Args:
            sunlit_array (bool array): 태양 조사 여부
        Returns:
            temp (array): 온도 (°C)
        """
        n    = len(sunlit_array)
        temp = np.zeros(n)
        temp[0] = 20.0  # 초기 온도

        alpha = 0.05  # 열 시상수 (0에 가까울수록 온도 변화 느림)

        for i in range(1, n):
            target = self.TEMP_SUNLIT if sunlit_array[i] else self.TEMP_ECLIPSE
            # 지수 이동평균: 목표 온도로 천천히 수렴
            temp[i] = temp[i-1] + alpha * (target - temp[i-1])
            # 센서 노이즈 추가
            temp[i] += np.random.normal(0, self.TEMP_NOISE_STD)

        return temp

    def _compute_ground_contact(self, x, y, time_array):
        """
        지상국 통신 가능 여부 판단 단순 모델

        실제로는 지상국 위치와 위성 위치를 3D로 계산해야 하지만,
        여기서는 위성이 지구 "앞쪽" (x > 0)에 있을 때 주기적으로 통신 가능으로 단순화

        궤도 주기의 일부 구간에서만 통신 가능 (실제 LEO 패스: 약 10분/회)

        Args:
            x, y         (array): 위성 위치 (m)
            time_array   (array): 시간 배열 (s)
        Returns:
            contact (bool array): 통신 가능 여부
        """
        # 궤도 각도 계산 (0~360도)
        angle = np.degrees(np.arctan2(y, x)) % 360

        # 통신 가능 구간: 특정 각도 범위 (지상국 상공 통과 시뮬레이션)
        # 궤도 1바퀴(약 92분)에서 약 10분 통신 가능 → 360° 중 약 39° 구간
        contact_window = 39.0  # 도
        contact_center = 45.0  # 도 (지상국 상공 통과 각도)

        contact = (
            (angle > contact_center - contact_window / 2) &
            (angle < contact_center + contact_window / 2)
        )
        return contact

    # ──────────────────────────────────────────────────────────────
    # 메인 생성 함수
    # ──────────────────────────────────────────────────────────────

    def generate(self):
        """
        텔레메트리 데이터프레임 생성

        궤도 데이터를 sample_interval 간격으로 다운샘플링하고
        각종 하위 시스템 데이터를 계산해서 하나의 DataFrame으로 합칩니다.

        Returns:
            pd.DataFrame: 텔레메트리 데이터
        """
        # ── 궤도 데이터 다운샘플링 ────────────────────────────────
        orbit_dt = self.orbit['time'][1] - self.orbit['time'][0]  # 궤도 시뮬 dt
        step = max(1, int(self.dt_sample / orbit_dt))
        idx  = np.arange(0, len(self.orbit['time']), step)

        time    = self.orbit['time'][idx]
        x       = self.orbit['x'][idx]
        y       = self.orbit['y'][idx]
        alt     = self.orbit['altitude'][idx]
        speed   = self.orbit['speed'][idx]
        n       = len(time)

        # ── 하위 시스템 계산 ──────────────────────────────────────
        sunlit  = self._is_sunlit(x, y)
        contact = self._compute_ground_contact(x, y, time)
        temp    = self._compute_temperature(sunlit)
        battery = self._compute_battery(sunlit, contact)

        # ── 자세각 (궤도 시간 축에 맞게 보간) ────────────────────
        if len(self.attitude['time']) > 1:
            att_time  = self.attitude['time']
            att_angle = self.attitude['angle']
            # 궤도 시간 범위에 맞게 자세각을 주기적으로 반복
            # (자세 시뮬 시간이 더 짧으면 마지막 값으로 패딩)
            angle_interp = np.interp(
                time % att_time[-1],   # 자세 시뮬 시간 범위 내로 wrap
                att_time,
                att_angle
            )
        else:
            angle_interp = np.zeros(n)

        # ── 이상 플래그 (정상 범위 이탈 여부) ────────────────────
        # 나중에 anomaly_detector.py가 이 컬럼을 활용
        battery_low  = battery < 20.0          # 배터리 20% 이하
        temp_high    = temp > 35.0             # 온도 35°C 초과
        temp_low     = temp < -15.0            # 온도 -15°C 미만
        alt_anomaly  = np.abs(alt - np.mean(alt)) > 50_000  # 고도 ±50km 이탈

        # ── DataFrame 조립 ────────────────────────────────────────
        df = pd.DataFrame({
            # 시간
            'timestamp'       : time,
            'time_min'        : time / 60.0,

            # 궤도
            'altitude_km'     : alt / 1000.0,
            'speed_kms'       : speed / 1000.0,
            'pos_x_km'        : x / 1000.0,
            'pos_y_km'        : y / 1000.0,

            # 자세
            'attitude_deg'    : angle_interp,

            # 전력
            'battery_pct'     : battery,
            'is_sunlit'       : sunlit.astype(int),

            # 열
            'temperature_c'   : temp,

            # 통신
            'ground_contact'  : contact.astype(int),

            # 이상 플래그
            'flag_battery_low': battery_low.astype(int),
            'flag_temp_high'  : temp_high.astype(int),
            'flag_temp_low'   : temp_low.astype(int),
            'flag_alt_anomaly': alt_anomaly.astype(int),
        })

        print(f"[TelemetryGenerator] 생성 완료: {len(df)} 행 × {len(df.columns)} 열")
        print(f"  시간 범위  : 0 ~ {time[-1]/60:.1f} 분")
        print(f"  평균 배터리: {df['battery_pct'].mean():.1f}%")
        print(f"  평균 온도  : {df['temperature_c'].mean():.1f}°C")
        print(f"  통신 가능  : {df['ground_contact'].sum()} / {len(df)} 포인트")

        return df

    def save(self, df, path=None):
        """DataFrame을 CSV로 저장"""
        if path is None:
            path = os.path.join(
                os.path.dirname(__file__), '..', '..', 'data', 'sample_telemetry.csv'
            )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        print(f"[TelemetryGenerator] CSV 저장: {path}")
        return path


if __name__ == "__main__":
    # 단독 테스트
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.orbit.orbit_simulator import OrbitSimulator
    from src.attitude.attitude_model import AttitudeModel
    from src.attitude.pid_controller import PIDController

    # 궤도 시뮬
    sim  = OrbitSimulator(altitude=400_000, sim_time=6000)
    orbit_data = sim.run()

    # 자세 시뮬
    model = AttitudeModel(initial_angle=30.0, dt=0.01)
    pid   = PIDController(Kp=0.4, Ki=0.005, Kd=0.05, dt=0.01)
    for _ in range(int(30.0 / 0.01)):
        model.step(pid.compute(0.0, model.angle_deg))

    # 텔레메트리 생성
    gen = TelemetryGenerator(orbit_data, model.get_history(), sample_interval=10)
    df  = gen.generate()
    gen.save(df)
    print(df.head())