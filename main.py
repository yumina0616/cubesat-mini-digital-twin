"""
main.py - CubeSat Mini Digital Twin 진입점
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    print("=" * 50)
    print("  CubeSat Mini Digital Twin")
    print("=" * 50)

    # ── Step 2-3: 궤도 시뮬레이션 + 그래프 ──────────
    from src.orbit.orbit_simulator import OrbitSimulator
    from src.utils.plot_utils import plot_all_orbit

    sim = OrbitSimulator(altitude=400_000, sim_time=6000)
    orbit_data = sim.run()
    plot_all_orbit(orbit_data)

    # ── Step 3: 자세 제어 + PID ──────────────────────
    from src.attitude.attitude_model import AttitudeModel
    from src.attitude.pid_controller import PIDController
    from src.utils.plot_utils import plot_attitude_response

    model = AttitudeModel(initial_angle=30.0, disturbance_std=1e-5, dt=0.01)
    pid   = PIDController(Kp=0.4, Ki=0.005, Kd=0.05, dt=0.01,
                          output_limit=0.05, integral_limit=5.0)

    steps = int(30.0 / 0.01)
    for _ in range(steps):
        torque = pid.compute(setpoint=0.0, measurement=model.angle_deg)
        model.step(torque)

    plot_attitude_response(model.get_history(), pid.get_history())

    # ── Step 4: 텔레메트리 생성 ──────────────────────
    # from src.telemetry.telemetry_generator import TelemetryGenerator
    # ...

    # ── Step 5: 이상 감지 ────────────────────────────
    # from src.telemetry.anomaly_detector import AnomalyDetector
    # ...

    print("\n[INFO] 대시보드 실행: streamlit run src/dashboard/app.py")


if __name__ == "__main__":
    main()