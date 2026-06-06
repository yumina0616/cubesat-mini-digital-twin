"""
plot_utils.py - 시뮬레이션 결과 시각화 유틸리티

그래프를 생성하고 results/ 폴더에 PNG로 저장합니다.
README.md에서 이 이미지들을 참조해서 포트폴리오로 활용합니다.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

# 결과 저장 경로
RESULTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'results')

# ── 전역 플롯 스타일 ──────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor' : '#0d1117',   # GitHub 다크 배경
    'axes.facecolor'   : '#161b22',
    'axes.edgecolor'   : '#30363d',
    'axes.labelcolor'  : '#c9d1d9',
    'text.color'       : '#c9d1d9',
    'xtick.color'      : '#8b949e',
    'ytick.color'      : '#8b949e',
    'grid.color'       : '#21262d',
    'grid.linewidth'   : 0.8,
    'axes.titlecolor'  : '#f0f6fc',
    'axes.titlesize'   : 13,
    'axes.labelsize'   : 11,
    'lines.linewidth'  : 1.8,
    'font.family'      : 'monospace',
})

ACCENT   = '#58a6ff'   # 파란 강조색
ACCENT2  = '#3fb950'   # 초록 강조색
ACCENT3  = '#f78166'   # 빨간 강조색
EARTH_C  = '#1f6feb'   # 지구 색


def _ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def plot_orbit(data, save=True, filename='orbit_plot.png'):
    """
    2D 궤도 경로 그래프 (XY 평면)

    지구를 중심에 그리고, 위성이 그린 궤적을 표시합니다.
    """
    _ensure_results_dir()

    fig, ax = plt.subplots(figsize=(7, 7))

    # 지구 그리기 (원)
    from src.orbit.orbital_constants import EARTH_RADIUS
    earth = plt.Circle((0, 0), EARTH_RADIUS / 1000, color=EARTH_C, alpha=0.8, zorder=3)
    ax.add_patch(earth)
    ax.text(0, 0, 'Earth', ha='center', va='center',
            fontsize=9, color='white', zorder=4)

    # 궤도 경로
    x_km = data['x'] / 1000
    y_km = data['y'] / 1000
    sc = ax.scatter(x_km, y_km, c=data['time'] / 60,
                    cmap='plasma', s=1.5, zorder=2, alpha=0.85)

    # 시작점 마커
    ax.plot(x_km[0], y_km[0], 'o', color=ACCENT2, markersize=8,
            label=f'Start  ({x_km[0]:.0f}, {y_km[0]:.0f}) km', zorder=5)

    cbar = fig.colorbar(sc, ax=ax, pad=0.02)
    cbar.set_label('Time (min)', color='#c9d1d9')
    cbar.ax.yaxis.set_tick_params(color='#8b949e')

    ax.set_aspect('equal')
    ax.set_xlabel('X (km)')
    ax.set_ylabel('Y (km)')
    ax.set_title('CubeSat Orbital Path (2D)')
    ax.legend(loc='upper right', fontsize=9, framealpha=0.3)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save:
        path = os.path.join(RESULTS_DIR, filename)
        fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f"[plot] 저장 완료: {path}")
    plt.close(fig)


def plot_altitude(data, save=True, filename='altitude_plot.png'):
    """
    고도-시간 그래프

    이상적인 원형 궤도라면 고도가 일정해야 합니다.
    Forward Euler의 수치 오차로 인해 미세하게 변동하는 것도 확인할 수 있습니다.
    """
    _ensure_results_dir()

    time_min = data['time'] / 60
    alt_km   = data['altitude'] / 1000

    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(time_min, alt_km, color=ACCENT, alpha=0.9, label='Altitude')
    ax.axhline(y=np.mean(alt_km), color=ACCENT2, linestyle='--',
               linewidth=1.2, alpha=0.7, label=f'Mean: {np.mean(alt_km):.2f} km')

    # 고도 변동 범위 표시
    alt_min, alt_max = np.min(alt_km), np.max(alt_km)
    ax.fill_between(time_min, alt_min, alt_max,
                    color=ACCENT, alpha=0.08)
    ax.text(time_min[-1] * 0.98, alt_max + 0.01,
            f'Δ{(alt_max - alt_min):.3f} km', ha='right',
            fontsize=9, color=ACCENT3)

    ax.set_xlabel('Time (min)')
    ax.set_ylabel('Altitude (km)')
    ax.set_title('CubeSat Altitude Over Time')
    ax.legend(fontsize=9, framealpha=0.3)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    if save:
        path = os.path.join(RESULTS_DIR, filename)
        fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f"[plot] 저장 완료: {path}")
    plt.close(fig)


def plot_speed(data, save=True, filename='speed_plot.png'):
    """
    속도-시간 그래프 (vx, vy 성분 + 합성 속력)

    원형 궤도에서 속력(크기)은 일정하지만,
    vx와 vy는 사인/코사인 형태로 주기적으로 변합니다.
    """
    _ensure_results_dir()

    time_min = data['time'] / 60

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    # 위쪽: 속도 성분
    axes[0].plot(time_min, data['vx'] / 1000, color=ACCENT,
                 alpha=0.85, label='Vx (km/s)', linewidth=1.5)
    axes[0].plot(time_min, data['vy'] / 1000, color=ACCENT2,
                 alpha=0.85, label='Vy (km/s)', linewidth=1.5)
    axes[0].axhline(0, color='#30363d', linewidth=0.8)
    axes[0].set_ylabel('Velocity Component (km/s)')
    axes[0].set_title('CubeSat Velocity Components & Speed')
    axes[0].legend(fontsize=9, framealpha=0.3)
    axes[0].grid(True, alpha=0.3)

    # 아래쪽: 속력(크기)
    speed_km = data['speed'] / 1000
    axes[1].plot(time_min, speed_km, color=ACCENT3,
                 alpha=0.9, label='Speed |V| (km/s)')
    axes[1].axhline(y=np.mean(speed_km), color='#8b949e',
                    linestyle='--', linewidth=1.0,
                    label=f'Mean: {np.mean(speed_km):.3f} km/s')
    axes[1].set_xlabel('Time (min)')
    axes[1].set_ylabel('Speed (km/s)')
    axes[1].legend(fontsize=9, framealpha=0.3)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    if save:
        path = os.path.join(RESULTS_DIR, filename)
        fig.savefig(path, dpi=150, bbox_inches='tight')
        print(f"[plot] 저장 완료: {path}")
    plt.close(fig)


def plot_all_orbit(data):
    """3개 그래프 한 번에 생성"""
    print("[plot] 궤도 그래프 생성 중...")
    plot_orbit(data)
    plot_altitude(data)
    plot_speed(data)
    print("[plot] 전체 완료 ✓")