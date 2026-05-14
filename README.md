# 🌦️ Weather Aggregator Pro

A high-performance asynchronous Python server built with **FastAPI** and **Pandas**. This application aggregates weather data from multiple public APIs (Open-Meteo, wttr.in, and 7Timer!) in parallel to provide accurate real-time averages and detailed hourly forecast reports.

## 🚀 Features

*   **Asynchronous Parallelism:** Calls multiple APIs simultaneously using `httpx` and `asyncio`.
*   **Data Aggregation:** Provides a "consensus" temperature by averaging multiple sources.
*   **Visual Reporting:** Generates a professional HTML dashboard for hourly forecasts using Pandas.
*   **Production Ready:** Includes comprehensive logging, Google-standard docstrings, and Docker configuration.

---

## 🛠️ Installation & Local Setup

### 1. Requirements
*   Python 3.10+
*   Pip

### 2. Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd weather_aggregator

# Install dependencies
pip install -r requirements.txt
