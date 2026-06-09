"""
app.py - CubeSat Mini Digital Twin Streamlit Dashboard

Run:
    streamlit run src/dashboard/app.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="CubeSat Mini Digital Twin",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .anomaly-alert {
        background: #3d1f1f;
        border-left: 4px solid #f78166;
        border-radius: 4px;
        padding: 10px 16px;
        margin: 6px 0;
    }
    .ok-badge {
        background: #1a3d2b;
        border-left: 4px solid #3fb950;
        border-radius: 4px;
        padding: 10px 16px;
        margin: 6px 0;
    }
</style>
""", unsafe_allow_html=True)

C_BLUE   = "#58a6ff"
C_GREEN  = "#3fb950"
C_RED    = "#f78166"
C_YELLOW = "#e3b341"
C_ORANGE = "#f0883e"
C_BG     = "#0d1117"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=C_BG,
    plot_bgcolor="#161b22",
    font_color="#c9d1d9",
    xaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
    margin=dict(l=50, r=20, t=40, b=40),
)


# ── Simulation runners (cached) ───────────────────────────────────
@st.cache_data(show_spinner=False)
def run_orbit(altitude_km, sim_time_min, method, tle_preset, tle_line1, tle_line2):
    from src.orbit.orbit_simulator import OrbitSimulator
    from src.orbit.tle_loader import TLELoader, PRESET_TLES

    if tle_preset == "None (manual altitude)":
        sim  = OrbitSimulator(altitude=altitude_km * 1000,
                              sim_time=sim_time_min * 60,
                              method=method)
        data = sim.run()
        tle_info = None
    else:
        # Use live-fetched lines if available, otherwise fall back to preset
        if tle_line1 and tle_line2:
            loader = TLELoader.from_string(tle_preset, tle_line1, tle_line2)
        else:
            loader = TLELoader.from_preset(tle_preset)
        ic   = loader.get_initial_conditions()
        sim  = OrbitSimulator(
            altitude=ic['altitude_2d'],
            sim_time=ic['period_min'] * 60,
            method=method,
            x0=ic['x0'], y0=ic['y0'],
            vx0=ic['vx0'], vy0=ic['vy0'],
        )
        data     = sim.run()
        tle_info = ic
    return data, sim, tle_info


@st.cache_data(show_spinner=False)
def run_attitude(initial_angle, kp, ki, kd, att_method='rk4'):
    from src.attitude.attitude_model import AttitudeModel
    from src.attitude.pid_controller import PIDController
    model = AttitudeModel(initial_angle=initial_angle,
                          disturbance_std=1e-5, dt=0.01,
                          method=att_method)
    pid   = PIDController(Kp=kp, Ki=ki, Kd=kd, dt=0.01,
                          output_limit=0.05, integral_limit=5.0)
    for _ in range(int(30.0 / 0.01)):
        model.step(pid.compute(0.0, model.angle_deg))
    return model.get_history(), pid.get_history()


@st.cache_data(show_spinner=False)
def run_telemetry(altitude_km, sim_time_min, method, tle_preset, tle_line1, tle_line2,
                  initial_angle, kp, ki, kd, att_method):
    from src.telemetry.telemetry_generator import TelemetryGenerator
    from src.telemetry.anomaly_detector import AnomalyDetector
    orbit_data, _, _ = run_orbit(altitude_km, sim_time_min, method, tle_preset, tle_line1, tle_line2)
    attitude_data, _ = run_attitude(initial_angle, kp, ki, kd, att_method)
    gen     = TelemetryGenerator(orbit_data, attitude_data, sample_interval=10)
    df      = gen.generate()
    anomaly = AnomalyDetector(df).detect_all()
    return df, anomaly


# ════════════════════════════════════════════════════════════════════
# Sidebar
# ════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("CubeSat Digital Twin")
    st.divider()

    st.subheader("Orbit Parameters")
    tle_options = ["None (manual altitude)", "ISS", "DOVE-1", "LEMUR-2", "CUSTOM"]
    tle_preset  = st.selectbox("Satellite Preset (TLE)", tle_options, index=0)

    tle_line1, tle_line2 = "", ""
    if tle_preset == "None (manual altitude)":
        altitude_km  = st.slider("Altitude (km)",      200, 800, 400, 10)
        sim_time_min = st.slider("Sim Duration (min)",  30, 200, 100, 10)
    elif tle_preset == "CUSTOM":
        st.caption("Enter TLE lines manually or fetch by NORAD ID:")
        norad_input = st.text_input("NORAD ID (optional)", placeholder="e.g. 25544 for ISS")
        if norad_input and st.button("Fetch from Celestrak", type="secondary"):
            try:
                from src.orbit.tle_fetcher import TLEFetcher
                fetched = TLEFetcher.fetch_by_norad_id(int(norad_input))
                st.session_state['fetched_tle'] = fetched
                st.success(f"Fetched: {fetched['name']} ({fetched['source']})")
            except Exception as e:
                st.error(f"Fetch failed: {e}")

        if 'fetched_tle' in st.session_state:
            f = st.session_state['fetched_tle']
            tle_line1 = st.text_input("TLE Line 1", value=f['line1'])
            tle_line2 = st.text_input("TLE Line 2", value=f['line2'])
        else:
            tle_line1 = st.text_input("TLE Line 1")
            tle_line2 = st.text_input("TLE Line 2")
        altitude_km  = 400
        sim_time_min = 100
    else:
        # Preset — attempt live fetch from Celestrak
        fetch_live = st.toggle("Fetch live TLE from Celestrak", value=True)
        if fetch_live:
            from src.orbit.tle_fetcher import TLEFetcher
            NORAD_MAP = {"ISS": 25544, "DOVE-1": 39418, "LEMUR-2": 41789}
            try:
                fetched  = TLEFetcher.fetch_by_norad_id(NORAD_MAP[tle_preset])
                tle_line1 = fetched['line1']
                tle_line2 = fetched['line2']
                src_label = fetched['source']
            except Exception:
                from src.orbit.tle_loader import PRESET_TLES
                tle_line1 = PRESET_TLES[tle_preset]['line1']
                tle_line2 = PRESET_TLES[tle_preset]['line2']
                src_label = "offline cache"
            st.caption(f"TLE source: **{src_label}**")
        else:
            from src.orbit.tle_loader import PRESET_TLES
            tle_line1 = PRESET_TLES[tle_preset]['line1']
            tle_line2 = PRESET_TLES[tle_preset]['line2']
            st.caption(PRESET_TLES[tle_preset]["description"])
        altitude_km  = 400
        sim_time_min = 100

    st.divider()
    st.subheader("Integration Method")
    method = st.radio(
        "Numerical integrator",
        options=["rk4", "euler"],
        format_func=lambda x: "RK4 (Runge-Kutta 4th order)" if x == "rk4" else "Euler (Forward Euler)",
        index=0,
    )
    if method == "euler":
        st.warning("Forward Euler accumulates significant error over time. Use RK4 for accurate results.")

    st.divider()
    st.subheader("Attitude Control")
    initial_angle = st.slider("Initial Angle (deg)", -90, 90, 30, 5)
    att_method = st.radio(
        "Attitude integrator",
        options=["rk4", "euler"],
        format_func=lambda x: "RK4 (recommended)" if x == "rk4" else "Euler (may diverge at large dt)",
        index=0,
    )
    st.caption("PID Gains")
    kp = st.number_input("Kp", 0.0, 2.0, 0.4, 0.05)
    ki = st.number_input("Ki", 0.0, 0.1, 0.005, 0.001, format="%.3f")
    kd = st.number_input("Kd", 0.0, 0.5, 0.05,  0.005, format="%.3f")

    st.divider()
    st.divider()
    run_btn = st.button("Run Simulation", use_container_width=True, type="primary")

# ── Session state ─────────────────────────────────────────────────
if "sim_done" not in st.session_state:
    st.session_state.sim_done = False

if run_btn:
    st.session_state.sim_done = True
    st.session_state.params = (
        altitude_km, sim_time_min, method,
        tle_preset, tle_line1, tle_line2,
        initial_angle, kp, ki, kd, att_method
    )

# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════
st.title("CubeSat Mini Digital Twin")

if not st.session_state.sim_done:
    st.info("Set parameters in the sidebar and click Run Simulation.")
    st.stop()

p = st.session_state.params
altitude_km, sim_time_min, method, tle_preset, tle_line1, tle_line2, \
    initial_angle, kp, ki, kd, att_method = p

with st.spinner("Running simulation..."):
    orbit_data, sim, tle_info = run_orbit(altitude_km, sim_time_min, method,
                                          tle_preset, tle_line1, tle_line2)
    attitude_data, pid_data   = run_attitude(initial_angle, kp, ki, kd, att_method)
    df, anomaly               = run_telemetry(*p)

# ── KPI cards ─────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
display_alt = f"{tle_info['altitude_2d']/1000:.0f} km" if tle_info else f"{altitude_km} km"
c1.metric("Altitude",         display_alt)
c2.metric("Satellite",        tle_preset if tle_preset != "None (manual altitude)" else "Manual")
c3.metric("Orbit Integrator", method.upper())
c4.metric("Att. Integrator",  att_method.upper())
c5.metric("GS Contact",       f"{df['ground_contact'].sum()} pts")
c6.metric("Anomalies",        f"{anomaly['summary']['anomaly_rows']} pts",
          delta=f"{anomaly['summary']['anomaly_rate']:.1f}%",
          delta_color="inverse")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Orbit", "Integrator Comparison", "Attitude", "Telemetry", "Anomaly"]
)


# ════════ TAB 1: ORBIT ═══════════════════════════════════════════
with tab1:
    col_l, col_r = st.columns(2)

    with col_l:
        fig = go.Figure()
        theta = np.linspace(0, 2 * np.pi, 200)
        fig.add_trace(go.Scatter(
            x=6371 * np.cos(theta), y=6371 * np.sin(theta),
            fill='toself', fillcolor='#1f6feb',
            line=dict(color='#388bfd', width=1),
            name='Earth', hoverinfo='skip',
        ))
        fig.add_trace(go.Scatter(
            x=orbit_data['x'] / 1000, y=orbit_data['y'] / 1000,
            mode='lines',
            line=dict(color=C_BLUE if method == 'rk4' else C_ORANGE, width=1.5),
            name=f'Orbit path ({method.upper()})',
        ))
        fig.update_layout(**PLOTLY_LAYOUT,
            title=f"Orbital Path (2D) — {method.upper()}", height=380,
            xaxis_title="X (km)", yaxis_title="Y (km)",
            yaxis_scaleanchor="x",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                             subplot_titles=("Altitude (km)", "Speed (km/s)"))
        t_min = orbit_data['time'] / 60
        line_color = C_BLUE if method == 'rk4' else C_ORANGE
        fig2.add_trace(go.Scatter(x=t_min, y=orbit_data['altitude'] / 1000,
                                  line=dict(color=line_color), name="Altitude"), row=1, col=1)
        fig2.add_trace(go.Scatter(x=t_min, y=orbit_data['speed'] / 1000,
                                  line=dict(color=C_GREEN), name="Speed"), row=2, col=1)
        fig2.update_layout(**PLOTLY_LAYOUT, height=380, showlegend=False)
        fig2.update_xaxes(title_text="Time (min)", row=2, col=1)
        st.plotly_chart(fig2, use_container_width=True)

    st.caption(
        f"Orbital period: **{sim.period/60:.1f} min** | "
        f"Orbital speed: **{sim.v_orbit/1000:.2f} km/s** | "
        f"Orbital radius: **{sim.r_orbit/1000:.0f} km** | "
        f"Integrator: **{method.upper()}**"
    )
    if tle_info:
        st.info(
            f"TLE source: **{tle_info['name']}** | "
            f"Inclination: **{tle_info['inclination']:.1f}°** | "
            f"Orbital period: **{tle_info['period_min']:.1f} min** | "
            f"Note: 3D orbit projected to 2D (XY plane)"
        )


# ════════ TAB 2: INTEGRATOR COMPARISON ═══════════════════════════
with tab2:
    st.subheader("Forward Euler vs Runge-Kutta 4 — Side-by-Side Comparison")
    st.caption("Both simulations use identical initial conditions. Only the integration method differs.")

    with st.spinner("Running both integrators..."):
        euler_data, _, _ = run_orbit(altitude_km, sim_time_min, 'euler', "None (manual altitude)", "", "")
        rk4_data,   _, _ = run_orbit(altitude_km, sim_time_min, 'rk4',   "None (manual altitude)", "", "")

    t_euler = euler_data['time'] / 60
    t_rk4   = rk4_data['time']  / 60

    # ── Altitude comparison ───────────────────────────────────────
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        subplot_titles=(
            "Altitude (km)",
            "Orbital Energy Drift (%)",
            "Altitude Error  |Euler - RK4|  (km)",
        ),
        row_heights=[0.4, 0.3, 0.3],
    )

    fig.add_trace(go.Scatter(x=t_euler, y=euler_data['altitude'] / 1000,
                             line=dict(color=C_ORANGE, width=1.8), name="Euler"), row=1, col=1)
    fig.add_trace(go.Scatter(x=t_rk4, y=rk4_data['altitude'] / 1000,
                             line=dict(color=C_BLUE, width=1.8), name="RK4"), row=1, col=1)

    e0_e = euler_data['energy'][0]
    e0_r = rk4_data['energy'][0]
    fig.add_trace(go.Scatter(
        x=t_euler,
        y=(euler_data['energy'] - e0_e) / abs(e0_e) * 100,
        line=dict(color=C_ORANGE, width=1.6), name="Euler energy"), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=t_rk4,
        y=(rk4_data['energy'] - e0_r) / abs(e0_r) * 100,
        line=dict(color=C_BLUE, width=1.6), name="RK4 energy"), row=2, col=1)

    alt_error = np.abs(euler_data['altitude'] / 1000 - rk4_data['altitude'] / 1000)
    fig.add_trace(go.Scatter(
        x=t_euler, y=alt_error,
        fill='tozeroy', fillcolor='rgba(88,166,255,0.08)',
        line=dict(color=C_BLUE, width=1.5), name="Error"), row=3, col=1)

    fig.update_layout(**PLOTLY_LAYOUT, height=580, showlegend=True,
                      legend=dict(orientation='h', y=1.02))
    fig.update_xaxes(title_text="Time (min)", row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # ── Stats table ───────────────────────────────────────────────
    euler_drift  = (euler_data['altitude'][-1] - euler_data['altitude'][0]) / 1000
    rk4_drift    = (rk4_data['altitude'][-1]   - rk4_data['altitude'][0])   / 1000
    euler_edrift = (euler_data['energy'][-1] - euler_data['energy'][0]) / abs(euler_data['energy'][0]) * 100
    rk4_edrift   = (rk4_data['energy'][-1]   - rk4_data['energy'][0])   / abs(rk4_data['energy'][0])   * 100

    col_e, col_r = st.columns(2)
    with col_e:
        st.markdown("**Forward Euler**")
        st.metric("Altitude drift",   f"{euler_drift:+.2f} km")
        st.metric("Energy drift",     f"{euler_edrift:+.4f}%")
        st.metric("Altitude std dev", f"{np.std(euler_data['altitude']/1000):.4f} km")
    with col_r:
        st.markdown("**RK4**")
        st.metric("Altitude drift",   f"{rk4_drift:+.6f} km")
        st.metric("Energy drift",     f"{rk4_edrift:+.6f}%")
        st.metric("Altitude std dev", f"{np.std(rk4_data['altitude']/1000):.6f} km")

    st.info(
        f"Over {sim_time_min} minutes, Euler accumulates **{abs(euler_drift):.1f} km** of altitude error "
        f"while RK4 stays within **{abs(rk4_drift)*1000:.2f} m**. "
        f"RK4 is ~{int(abs(euler_drift) / max(abs(rk4_drift), 1e-6))}x more accurate."
        if abs(rk4_drift) > 1e-6
        else f"Over {sim_time_min} minutes, Euler accumulates **{abs(euler_drift):.1f} km** of altitude error. RK4 shows no measurable drift."
    )


# ════════ TAB 3: ATTITUDE ════════════════════════════════════════
with tab3:
    att_time  = attitude_data['time'][1:]
    att_angle = attitude_data['angle'][1:]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=(
                            f"Attitude Angle (deg) — {att_method.upper()}",
                            "Control Torque (N·m)"
                        ))

    fig.add_trace(go.Scatter(x=att_time, y=att_angle,
                             line=dict(color=C_BLUE, width=2), name="Angle"), row=1, col=1)
    fig.add_hline(y=0,  line=dict(color=C_GREEN,  dash='dash', width=1.2), row=1, col=1)
    fig.add_hline(y=1,  line=dict(color=C_YELLOW, dash='dot',  width=1),   row=1, col=1)
    fig.add_hline(y=-1, line=dict(color=C_YELLOW, dash='dot',  width=1),   row=1, col=1)

    fig.add_trace(go.Scatter(x=att_time, y=pid_data['P'],
                             line=dict(color=C_BLUE,  width=1.2), name="P"), row=2, col=1)
    fig.add_trace(go.Scatter(x=att_time, y=pid_data['I'],
                             line=dict(color=C_GREEN, width=1.2), name="I"), row=2, col=1)
    fig.add_trace(go.Scatter(x=att_time, y=pid_data['D'],
                             line=dict(color=C_RED,   width=1.2), name="D"), row=2, col=1)
    fig.add_trace(go.Scatter(x=att_time, y=pid_data['output'],
                             line=dict(color='white', width=1.5, dash='dash'),
                             name="Total"), row=2, col=1)

    fig.update_layout(**PLOTLY_LAYOUT, height=480)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    converge = next((i for i, a in enumerate(att_angle) if abs(a) < 1.0), None)
    if converge:
        st.success(
            f"Converged to within 1 deg at {att_time[converge]:.2f}s | "
            f"Final angle: {att_angle[-1]:.3f} deg | "
            f"PID: Kp={kp}, Ki={ki}, Kd={kd}"
        )
    else:
        st.warning("Did not converge within 1 deg during simulation. Try adjusting PID gains.")


# ════════ TAB 4: TELEMETRY ═══════════════════════════════════════
with tab4:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        subplot_titles=("Battery (%)", "Temperature (C)", "Ground Contact"),
                        row_heights=[0.4, 0.4, 0.2])

    t = df['time_min']

    fig.add_trace(go.Scatter(x=t, y=df['battery_pct'],
                             fill='tozeroy', fillcolor='rgba(88,166,255,0.1)',
                             line=dict(color=C_BLUE), name="Battery"), row=1, col=1)
    fig.add_hline(y=20, line=dict(color=C_RED, dash='dash', width=1),
                  annotation_text="Low (20%)", row=1, col=1)

    fig.add_trace(go.Scatter(x=t, y=df['temperature_c'],
                             line=dict(color=C_YELLOW), name="Temp"), row=2, col=1)
    fig.add_hline(y=45,  line=dict(color=C_RED,  dash='dot', width=1), row=2, col=1)
    fig.add_hline(y=-25, line=dict(color=C_BLUE, dash='dot', width=1), row=2, col=1)

    fig.add_trace(go.Bar(x=t, y=df['ground_contact'],
                         marker_color=C_GREEN, name="GS Contact",
                         opacity=0.8), row=3, col=1)

    fig.update_layout(**PLOTLY_LAYOUT, height=560, showlegend=False)
    fig.update_xaxes(title_text="Time (min)", row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw Telemetry Data"):
        st.dataframe(
            df[['time_min', 'altitude_km', 'battery_pct',
                'temperature_c', 'attitude_deg', 'ground_contact']].round(3),
            use_container_width=True, height=300,
        )


# ════════ TAB 5: ANOMALY ═════════════════════════════════════════
with tab5:
    s = anomaly['summary']

    a1, a2, a3 = st.columns(3)
    a1.metric("Total Points",   s['total_rows'])
    a2.metric("Anomaly Points", s['anomaly_rows'])
    a3.metric("Anomaly Rate",   f"{s['anomaly_rate']:.1f}%")

    st.divider()

    st.subheader("Rule-based Threshold Detection")
    for col, res in anomaly['threshold'].items():
        if res['count'] > 0:
            st.markdown(
                f'<div class="anomaly-alert"><b>{res["name"]}</b> — '
                f'{res["count"]} anomalies (range: {res["rule"]})</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="ok-badge"><b>{res["name"]}</b> — Normal</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    st.subheader("Battery Discharge Trend")
    bt = anomaly['battery_trend']
    if bt['warning_count'] > 0:
        st.warning(
            f"{bt['warning_count']} consecutive drop warning(s) "
            f"(max {bt['max_consecutive']} steps in a row)"
        )
        for w in bt['warnings']:
            st.caption(
                f"  Started at {w['start_time']:.1f} min, "
                f"battery at {w['battery_at_start']:.1f}%"
            )
    else:
        st.success(f"Battery trend normal (max consecutive drop: {bt['max_consecutive']} steps)")

    st.divider()

    st.subheader("Anomaly Timeline")
    flag_cols = [c for c in df.columns if c.startswith('flag_')]
    if flag_cols:
        fig = go.Figure()
        colors = [C_RED, C_YELLOW, C_BLUE, C_GREEN]
        for i, col in enumerate(flag_cols):
            mask = df[col] == 1
            if mask.any():
                fig.add_trace(go.Scatter(
                    x=df.loc[mask, 'time_min'],
                    y=[col.replace('flag_', '')] * mask.sum(),
                    mode='markers',
                    marker=dict(color=colors[i % len(colors)], size=7, symbol='x'),
                    name=col.replace('flag_', ''),
                ))
        fig.update_layout(**PLOTLY_LAYOUT, height=250,
                          xaxis_title="Time (min)", yaxis_title="Flag")
        st.plotly_chart(fig, use_container_width=True)