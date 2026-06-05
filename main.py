"""
main.py - CubeSat Mini Digital Twin 진입점

각 단계를 순서대로 실행하는 메인 스크립트.
각 모듈이 완성되면 주석을 해제하면서 사용한다.
"""

import os
import sys

# 프로젝트 루트를 파이썬 경로에 추가 (모듈 import를 위해 필요)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=" * 50)
    print("  CubeSat Mini Digital Twin")
    print("=" * 50)

    # ── Step 3: 궤도 시뮬레이션 ──────────────────────
    # from src.orbit.orbit_simulator import OrbitSimulator
    # sim = OrbitSimulator()
    # orbit_data = sim.run()
    # sim.plot_results(orbit_data)

    # ── Step 5-6: 자세 제어 ──────────────────────────
    # from src.attitude.attitude_model import AttitudeModel
    # from src.attitude.pid_controller import PIDController
    # ...

    # ── Step 8: 텔레메트리 생성 ──────────────────────
    # from src.telemetry.telemetry_generator import TelemetryGenerator
    # ...

    # ── Step 9: 이상 감지 ────────────────────────────
    # from src.telemetry.anomaly_detector import AnomalyDetector
    # ...

    print("\n[INFO] 각 단계를 구현한 후 주석을 해제하세요.")
    print("[INFO] 대시보드 실행: streamlit run src/dashboard/app.py")


if __name__ == "__main__":
    main()
