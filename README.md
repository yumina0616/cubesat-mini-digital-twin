# 🛰️CubeSat Mini Digital Twin

## Overview

**CubeSat Mini Digital Twin** is a personal aerospace software project that aims to simulate a simplified CubeSat system.

The project will integrate basic aerospace software components such as:

* 2D orbital simulation
* 1-axis attitude control
* Telemetry data generation
* Rule-based anomaly detection
* Streamlit-based digital twin dashboard

The main goal of this project is to explore how software can be used to model, control, monitor, and visualize a small satellite system.

---

## Motivation

I am interested in aerospace software development, especially in areas such as GNC, simulation, embedded systems, and digital twin technologies.

Before joining a university lab related to space mobility and digital twin research, I started this project to build a small but meaningful software system that connects programming with aerospace engineering concepts.

This project is designed as a learning-oriented portfolio project for understanding the basic workflow of aerospace software systems.

---

## Project Goals

The final goal of this project is to build a simplified CubeSat digital twin with the following features:

1. Simulate a 2D CubeSat orbit around Earth
2. Implement a 1-axis attitude control system using PID control
3. Generate telemetry data from the simulated satellite system
4. Model basic satellite states such as battery, temperature, and communication availability
5. Detect abnormal conditions using rule-based logic
6. Visualize satellite states through a Streamlit dashboard

---

## Current Progress

### Step 1: Project Initialization

Status: Completed

Completed tasks:

* Created the initial project folder structure
* Added empty Python modules for future implementation
* Added `requirements.txt`
* Added `main.py` as the project entry point
* Added initial documentation in `README.md`

---

### Step 2: 2D Orbit Simulation

Status: Completed

In this step, a simplified 2D Low Earth Orbit simulation was implemented for a CubeSat at an altitude of approximately 400 km.

Implemented files:

* `src/orbit/orbital_constants.py`

  * Defines physical constants such as Earth's gravitational parameter and Earth radius.

* `src/orbit/orbit_simulator.py`

  * Simulates the CubeSat's 2D orbital motion using Forward Euler numerical integration.

* `src/utils/plot_utils.py`

  * Generates plots for orbit trajectory, altitude over time, and speed over time.

Simulation conditions:

```text
Orbit altitude: 400 km
Orbit radius: 6,771 km
Orbital speed: 7.67 km/s
Orbital period: 92.4 minutes
Simulation duration: approximately 100 minutes
```

Generated result plots:

* `results/orbit_plot.png`
* `results/altitude_plot.png`
* `results/speed_plot.png`

---

## Orbit Simulation

The orbit simulation models a CubeSat moving around Earth in a simplified 2D inertial frame.

The satellite state is represented by position and velocity vectors:

```text
r = [x, y]
v = [vx, vy]
```

The gravitational acceleration is calculated using Newtonian gravity:

```text
a = -μr / |r|³
```

where:

* `μ` is Earth's gravitational parameter
* `r` is the satellite position vector from Earth's center
* `|r|` is the distance between the satellite and Earth's center

The simulator updates the satellite state over time using Forward Euler integration.

---

## Numerical Integration Method

This project currently uses the Forward Euler method for orbit propagation.

Forward Euler is simple and useful for understanding the basic idea of numerical simulation. However, it is not highly accurate for long-duration orbital simulations because numerical error accumulates over time.

In the current 400 km Low Earth Orbit simulation, the altitude graph shows an accumulated error of approximately 50 km over about 6,000 seconds.

This behavior is expected because Forward Euler does not conserve orbital energy well over long simulations.

In future versions, the simulator will be improved using more accurate integration methods such as:

* Runge-Kutta 4th order method
* `scipy.integrate.solve_ivp`
* More realistic perturbation models

This limitation is intentionally documented to show the difference between a simple educational simulator and a more realistic aerospace simulation tool.

---

## Results from Step 2

The initial 2D orbit simulation successfully produced the following results:

| Quantity           |         Value |
| ------------------ | ------------: |
| Orbit altitude     |        400 km |
| Orbit radius       |      6,771 km |
| Orbital speed      |     7.67 km/s |
| Orbital period     |      92.4 min |
| Integration method | Forward Euler |

The simulation confirms the basic behavior of a CubeSat in Low Earth Orbit. Although the orbit is not perfectly stable due to numerical integration error, the result is sufficient for the first version of the project.

---

## Updated Development Roadmap

### Step 1. Project Initialization

Status: Completed

### Step 2. 2D Orbit Simulation

Status: Completed

Implemented:

* Physical constants
* Initial orbit conditions
* Forward Euler integration
* Orbit trajectory plotting
* Altitude plotting
* Speed plotting

### Step 3. Attitude Control

Status: Planned

Next step:

* Implement a simplified 1-axis attitude dynamics model
* Implement a PID controller
* Simulate attitude stabilization
* Generate attitude response and control input plots

### Step 4. Telemetry Generation

Status: Planned

### Step 5. Anomaly Detection

Status: Planned

### Step 6. Streamlit Dashboard

Status: Planned

### Step 7. Documentation and Portfolio Refinement

Status: Planned

---

## Planned Features

### 1. Orbit Simulation

A 2D orbital simulator will be implemented to calculate the CubeSat's position, velocity, altitude, and trajectory over time.

Planned outputs:

* Orbit plot
* Altitude over time
* Speed over time

---

### 2. Attitude Control

A simplified 1-axis attitude control model will be implemented using a PID controller.

Planned outputs:

* Attitude angle response
* Attitude error
* Control input over time

---

### 3. Telemetry Generation

The simulation results will be converted into telemetry-like data.

Planned telemetry data includes:

* Time
* Position
* Altitude
* Speed
* Attitude angle
* Attitude error
* Battery level
* Temperature
* Sunlight condition
* Communication availability
* Warning status

---

### 4. Anomaly Detection

A simple rule-based anomaly detection module will be added.

Example warning conditions:

* Low battery
* Large attitude error
* Abnormal temperature
* Communication loss

---

### 5. Digital Twin Dashboard

A Streamlit dashboard will be developed to visualize the simulated CubeSat state.

The dashboard will include:

* Current satellite status
* Orbit visualization
* Altitude graph
* Attitude response graph
* Battery and temperature graphs
* Warning panel

---

## Tech Stack

* Python
* NumPy
* SciPy
* Pandas
* Matplotlib
* Streamlit
* Plotly
* python-dotenv

---

## Project Structure

```text
cubesat-mini-digital-twin/
│
├── README.md
├── requirements.txt
├── main.py
│
├── src/
│   ├── orbit/
│   │   ├── orbit_simulator.py
│   │   └── orbital_constants.py
│   │
│   ├── attitude/
│   │   ├── attitude_model.py
│   │   └── pid_controller.py
│   │
│   ├── telemetry/
│   │   ├── telemetry_generator.py
│   │   └── anomaly_detector.py
│   │
│   ├── dashboard/
│   │   └── app.py
│   │
│   └── utils/
│       └── plot_utils.py
│
├── data/
│   └── sample_telemetry.csv
│
├── results/
│   ├── orbit_plot.png
│   ├── altitude_plot.png
│   ├── attitude_response.png
│   └── dashboard_screenshot.png
│
└── docs/
    └── project_report.md
```

---

## Development Roadmap

### Step 1. Project Initialization

Set up the initial project structure and dependencies.

Status: Completed

### Step 2. Orbit Simulation

Implement a 2D orbital simulator for a simplified CubeSat.

Status: Planned

### Step 3. Attitude Control

Implement a 1-axis attitude model and PID controller.

Status: Planned

### Step 4. Telemetry Generation

Generate telemetry data from orbit and attitude simulation results.

Status: Planned

### Step 5. Anomaly Detection

Add rule-based warning detection for abnormal satellite states.

Status: Planned

### Step 6. Streamlit Dashboard

Build an interactive dashboard for visualizing CubeSat telemetry.

Status: Planned

### Step 7. Documentation and Portfolio Refinement

Organize results, screenshots, and explanations for GitHub portfolio use.

Status: Planned

---

## Future Improvements

Possible future extensions include:

* 3D orbit simulation
* Real TLE data integration
* Kalman Filter-based state estimation
* 3-axis attitude control
* Ground station visibility analysis
* ROS 2 integration
* More realistic thermal and power models

---

## Project Purpose

This project is not intended to be a fully accurate satellite simulator.

Instead, it is a learning project designed to connect software development with aerospace concepts such as GNC, simulation, telemetry, anomaly detection, and digital twin systems.
