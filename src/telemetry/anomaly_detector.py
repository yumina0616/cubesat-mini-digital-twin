"""
anomaly_detector.py - CubeSat 텔레메트리 이상 감지기

[이상 감지(Anomaly Detection)란?]
    정상 범위를 벗어난 데이터를 자동으로 찾아내는 기능입니다.
    위성 운용에서는 이상을 빨리 발견해야 고장을 예방할 수 있습니다.

[이 파일에서 구현하는 방법 2가지]
    1. 임계값 기반 (Rule-based): "배터리가 20% 이하면 이상"
       → 간단하고 해석이 쉬움. 실제 위성 운용에서도 많이 씀.

    2. 통계 기반 (Z-score): "평균에서 표준편차 N배 이상 벗어나면 이상"
       → 예상치 못한 이상도 잡을 수 있음.
"""

import numpy as np
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class AnomalyDetector:
    """
    텔레메트리 DataFrame을 분석해서 이상 항목을 탐지합니다.

    사용 예시:
        detector = AnomalyDetector(df)
        result   = detector.detect_all()
        detector.print_report(result)
    """

    # ── 임계값 규칙 정의 ──────────────────────────────────────────
    RULES = {
        'battery_pct'  : {'min': 15.0,  'max': 100.0, 'unit': '%',   'name': '배터리 잔량'},
        'temperature_c': {'min': -25.0, 'max':  45.0, 'unit': '°C',  'name': '온보드 온도'},
        'altitude_km'  : {'min': 390.0, 'max': 510.0, 'unit': 'km',  'name': '궤도 고도'},
        'speed_kms'    : {'min':   7.5, 'max':   8.0, 'unit': 'km/s','name': '궤도 속도'},
        'attitude_deg' : {'min': -10.0, 'max':  10.0, 'unit': '°',   'name': '자세각'},
    }

    Z_SCORE_THRESHOLD = 3.0  # Z-score 이상 기준 (3σ = 99.7% 범위 밖)

    def __init__(self, df):
        """
        Args:
            df (pd.DataFrame): TelemetryGenerator.generate() 반환 데이터프레임
        """
        self.df = df.copy()
        print(f"[AnomalyDetector] 초기화: {len(df)} 행 분석 준비")

    # ──────────────────────────────────────────────────────────────
    # 탐지 메서드들
    # ──────────────────────────────────────────────────────────────

    def detect_threshold(self):
        """
        임계값 기반 이상 탐지

        각 컬럼의 값이 정해진 min/max 범위를 벗어나면 이상으로 표시합니다.

        Returns:
            dict: {컬럼명: 이상 발생 행 인덱스 리스트}
        """
        results = {}
        for col, rule in self.RULES.items():
            if col not in self.df.columns:
                continue
            mask = (self.df[col] < rule['min']) | (self.df[col] > rule['max'])
            anomaly_idx = self.df.index[mask].tolist()
            results[col] = {
                'indices'  : anomaly_idx,
                'count'    : len(anomaly_idx),
                'rule'     : f"{rule['min']} ~ {rule['max']} {rule['unit']}",
                'name'     : rule['name'],
                'values'   : self.df.loc[mask, col].values if len(anomaly_idx) > 0 else [],
            }
        return results

    def detect_zscore(self):
        """
        Z-score 기반 통계적 이상 탐지

        Z-score = (값 - 평균) / 표준편차
        |Z| > threshold 이면 통계적으로 이상한 값으로 판단합니다.

        임계값 기반으로 잡기 어려운 "갑작스러운 변화"를 탐지할 때 유용합니다.

        Returns:
            dict: {컬럼명: 이상 발생 행 인덱스 리스트}
        """
        numeric_cols = ['battery_pct', 'temperature_c', 'altitude_km', 'attitude_deg']
        results = {}

        for col in numeric_cols:
            if col not in self.df.columns:
                continue
            series = self.df[col]
            mean   = series.mean()
            std    = series.std()

            if std < 1e-9:  # 표준편차가 0에 가까우면 스킵
                continue

            z_scores = np.abs((series - mean) / std)
            mask     = z_scores > self.Z_SCORE_THRESHOLD
            anomaly_idx = self.df.index[mask].tolist()

            results[col] = {
                'indices'  : anomaly_idx,
                'count'    : len(anomaly_idx),
                'mean'     : mean,
                'std'      : std,
                'threshold': self.Z_SCORE_THRESHOLD,
                'max_z'    : z_scores.max(),
            }
        return results

    def detect_battery_trend(self):
        """
        배터리 연속 하락 추세 감지

        N 스텝 연속으로 배터리가 감소하면 경고합니다.
        충전이 안 되는 상황(태양전지 고장 등)을 조기 감지하는 데 유용합니다.

        Returns:
            dict: 연속 하락 구간 정보
        """
        battery = self.df['battery_pct'].values
        consecutive_drop = 0
        max_consecutive  = 0
        drop_start_idx   = 0
        warnings = []

        WARN_THRESHOLD = 10  # N 스텝 연속 하락 시 경고

        for i in range(1, len(battery)):
            if battery[i] < battery[i-1]:
                if consecutive_drop == 0:
                    drop_start_idx = i - 1
                consecutive_drop += 1
                max_consecutive = max(max_consecutive, consecutive_drop)

                if consecutive_drop == WARN_THRESHOLD:
                    warnings.append({
                        'start_idx'  : drop_start_idx,
                        'start_time' : self.df['time_min'].iloc[drop_start_idx],
                        'battery_at_start': battery[drop_start_idx],
                    })
            else:
                consecutive_drop = 0

        return {
            'warnings'       : warnings,
            'max_consecutive': max_consecutive,
            'warning_count'  : len(warnings),
        }

    def detect_all(self):
        """모든 탐지기 실행 후 결과 통합"""
        return {
            'threshold'     : self.detect_threshold(),
            'zscore'        : self.detect_zscore(),
            'battery_trend' : self.detect_battery_trend(),
            'summary'       : self._make_summary(),
        }

    def _make_summary(self):
        """전체 이상 요약 통계"""
        total_rows  = len(self.df)
        flag_cols   = [c for c in self.df.columns if c.startswith('flag_')]
        any_anomaly = self.df[flag_cols].any(axis=1)

        return {
            'total_rows'    : total_rows,
            'anomaly_rows'  : int(any_anomaly.sum()),
            'anomaly_rate'  : float(any_anomaly.mean() * 100),
            'flag_counts'   : {col: int(self.df[col].sum()) for col in flag_cols},
        }

    # ──────────────────────────────────────────────────────────────
    # 리포트 출력
    # ──────────────────────────────────────────────────────────────

    def print_report(self, results=None):
        """터미널에 이상 감지 결과 출력"""
        if results is None:
            results = self.detect_all()

        print("\n" + "=" * 55)
        print("  ANOMALY DETECTION REPORT")
        print("=" * 55)

        # 요약
        s = results['summary']
        print(f"\n[요약]")
        print(f"  전체 데이터  : {s['total_rows']} 포인트")
        print(f"  이상 포인트  : {s['anomaly_rows']} ({s['anomaly_rate']:.1f}%)")
        for flag, cnt in s['flag_counts'].items():
            if cnt > 0:
                print(f"    {flag:<25}: {cnt} 건")

        # 임계값 기반
        print(f"\n[임계값 기반 탐지]")
        for col, res in results['threshold'].items():
            status = "⚠ ANOMALY" if res['count'] > 0 else "✓ OK"
            print(f"  {res['name']:<12} ({res['rule']:<20}) → {status} {res['count']}건")

        # 배터리 추세
        bt = results['battery_trend']
        print(f"\n[배터리 하락 추세]")
        if bt['warning_count'] > 0:
            print(f"  ⚠ 연속 하락 경고 {bt['warning_count']}회 (최대 {bt['max_consecutive']}스텝 연속)")
        else:
            print(f"  ✓ 이상 없음 (최대 연속 하락: {bt['max_consecutive']}스텝)")

        print("=" * 55)


if __name__ == "__main__":
    # 단독 테스트
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.orbit.orbit_simulator import OrbitSimulator
    from src.attitude.attitude_model import AttitudeModel
    from src.attitude.pid_controller import PIDController
    from src.telemetry.telemetry_generator import TelemetryGenerator

    sim  = OrbitSimulator(altitude=400_000, sim_time=6000)
    orbit_data = sim.run()

    model = AttitudeModel(initial_angle=30.0, dt=0.01)
    pid   = PIDController(Kp=0.4, Ki=0.005, Kd=0.05, dt=0.01)
    for _ in range(int(30.0 / 0.01)):
        model.step(pid.compute(0.0, model.angle_deg))

    gen = TelemetryGenerator(orbit_data, model.get_history())
    df  = gen.generate()

    detector = AnomalyDetector(df)
    results  = detector.detect_all()
    detector.print_report(results)