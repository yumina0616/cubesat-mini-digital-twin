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

Completed:

* Created the initial project folder structure
* Added empty Python files for future implementation
* Added `requirements.txt`
* Added `main.py` as the future entry point
* Prepared the project for step-by-step development

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
