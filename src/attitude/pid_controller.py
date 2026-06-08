"""
pid_controller.py - PID 제어기

[PID란?]
    목표값(setpoint)과 현재값(measurement)의 차이(오차)를 줄이기 위해
    세 가지 항의 합으로 제어 출력을 계산합니다.

    output = Kp × e(t)                    ← P: 현재 오차에 비례
           + Ki × ∫e(t)dt                 ← I: 누적 오차를 적분
           + Kd × de(t)/dt               ← D: 오차 변화율에 비례

    [P 항] 오차가 크면 세게 밀고, 작으면 약하게 밂
           → 너무 크면 오버슈트(목표를 지나쳐버림)
    [I 항] 오차가 오래 지속되면 누적해서 더 강하게 밂
           → 정상상태 오차(steady-state error) 제거
    [D 항] 오차가 빠르게 변할 때 브레이크 역할
           → 진동 감소, 안정화

[위성 자세 제어에서의 의미]
    목표각(예: 0°)과 현재 자세각의 차이를 계산해서
    반응 휠(Reaction Wheel)이나 추력기에 보낼 토크를 결정합니다.
"""

import numpy as np


class PIDController:
    """
    이산시간 PID 제어기

    사용 예시:
        pid = PIDController(Kp=0.5, Ki=0.01, Kd=0.1, dt=0.1)
        torque = pid.compute(setpoint=0.0, measurement=30.0)
    """

    def __init__(
        self,
        Kp=0.5,           # 비례 이득
        Ki=0.01,          # 적분 이득
        Kd=0.1,           # 미분 이득
        dt=0.1,           # 시간 스텝 (AttitudeModel과 동일해야 함)
        output_limit=0.05, # 토크 출력 제한 (N·m) - 반응 휠 포화 방지
        integral_limit=10.0, # 적분 와인드업 방지 상한
    ):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.dt = dt
        self.output_limit   = output_limit
        self.integral_limit = integral_limit

        # 내부 상태
        self._integral    = 0.0   # 누적 오차 (I 항 계산용)
        self._prev_error  = None  # 이전 오차 (D 항 계산용)

        # 히스토리
        self.error_history  = []
        self.output_history = []
        self.p_history      = []
        self.i_history      = []
        self.d_history      = []

        print(f"[PIDController] 초기화 완료")
        print(f"  Kp={Kp}, Ki={Ki}, Kd={Kd}")
        print(f"  출력 제한: ±{output_limit} N·m")

    def compute(self, setpoint, measurement):
        """
        PID 출력 계산

        Args:
            setpoint    (float): 목표값 (도)
            measurement (float): 현재 측정값 (도)

        Returns:
            output (float): 제어 토크 (N·m)
        """
        # 오차 계산
        error = setpoint - measurement

        # 각도 오차는 -180 ~ 180 범위로 정규화
        # 예: 목표 0°, 현재 350° → 오차는 -10° (10° 돌아가면 됨)
        error = (error + 180) % 360 - 180

        # ── P 항 ─────────────────────────────────────────────────
        P = self.Kp * error

        # ── I 항 (적분 와인드업 방지 포함) ───────────────────────
        self._integral += error * self.dt
        # 와인드업: 적분값이 너무 커지면 제어기가 한쪽으로 계속 밀어붙임
        # → 상한을 두어 방지
        self._integral = np.clip(self._integral, -self.integral_limit, self.integral_limit)
        I = self.Ki * self._integral

        # ── D 항 ─────────────────────────────────────────────────
        if self._prev_error is None:
            D = 0.0  # 첫 스텝은 이전 오차가 없으므로 0
        else:
            D = self.Kd * (error - self._prev_error) / self.dt

        self._prev_error = error

        # 출력 합산 + 제한
        output = P + I + D
        output = np.clip(output, -self.output_limit, self.output_limit)

        # 히스토리 저장
        self.error_history.append(error)
        self.output_history.append(output)
        self.p_history.append(P)
        self.i_history.append(I)
        self.d_history.append(D)

        return output

    def reset(self):
        """제어기 상태 초기화"""
        self._integral   = 0.0
        self._prev_error = None
        self.error_history  = []
        self.output_history = []
        self.p_history = []
        self.i_history = []
        self.d_history = []

    def get_history(self):
        return {
            'error' : np.array(self.error_history),
            'output': np.array(self.output_history),
            'P'     : np.array(self.p_history),
            'I'     : np.array(self.i_history),
            'D'     : np.array(self.d_history),
        }


if __name__ == "__main__":
    # 단독 테스트: AttitudeModel + PIDController 연동
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.attitude.attitude_model import AttitudeModel

    model = AttitudeModel(initial_angle=30.0, disturbance_std=0)
    pid   = PIDController(Kp=0.5, Ki=0.01, Kd=0.05, dt=0.1)

    print("\n[테스트] 30° → 0° 수렴 시뮬레이션 (처음 10스텝)")
    for i in range(10):
        torque = pid.compute(setpoint=0.0, measurement=model.angle_deg)
        angle  = model.step(torque)
        err    = pid.error_history[-1]
        print(f"  step {i+1:02d} | angle={angle:7.3f}° | torque={torque:.5f} N·m | error={err:.3f}°")