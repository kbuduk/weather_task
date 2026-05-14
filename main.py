"""Weather Aggregator Service.

This module provides a FastAPI-based web server that fetches current weather
averages and hourly forecasts from multiple public APIs. It leverages
asynchronous execution for performance and Pandas for HTML reporting.
"""

import asyncio
import logging
from typing import Any

import httpx
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Weather Aggregator Pro",
    description="Aggregate current weather and view hourly forecast reports.",
    version="2.0.0"
)

# API Endpoints
API_CONFIG = {
    "open_meteo": "https://api.open-meteo.com/v1/forecast",
    "wttr_in": "https://wttr.in/{}?format=j1",
    "seven_timer": "http://www.7timer.info/bin/api.pl"
}


# --- Current Weather Helpers ---

async def fetch_open_meteo(client: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
    """Fetches current temperature from the Open-Meteo API.

    Args:
        client: An asynchronous HTTP client (httpx.AsyncClient).
        lat: Latitude of the target location.
        lon: Longitude of the target location.

    Returns:
        A dictionary containing the provider name and temperature (float) or
        an error message string if the request fails.
    """
    try:
        params = {"latitude": lat, "longitude": lon, "current_weather": True}
        r = await client.get(API_CONFIG["open_meteo"], params=params)
        r.raise_for_status()
        temp = r.json()["current_weather"]["temperature"]
        return {"provider": "Open-Meteo", "temp": temp}
    except Exception as e:
        logger.error("Open-Meteo current failed: %s", e)
        return {"provider": "Open-Meteo", "error": str(e)}


async def fetch_wttr_in(client: httpx.AsyncClient, city: str) -> dict[str, Any]:
    """Fetches current temperature from the wttr.in API.

    Args:
        client: An asynchronous HTTP client (httpx.AsyncClient).
        city: The name of the city (string) to query.

    Returns:
        A dictionary containing the provider name and temperature (float) or
        an error message string if the request fails.
    """
    try:
        r = await client.get(API_CONFIG["wttr_in"].format(city))
        r.raise_for_status()
        temp = float(r.json()["current_condition"][0]["temp_C"])
        return {"provider": "wttr.in", "temp": temp}
    except Exception as e:
        logger.error("wttr.in current failed: %s", e)
        return {"provider": "wttr.in", "error": str(e)}


async def fetch_seven_timer(client: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
    """Fetches current temperature from the 7Timer! API.

    Args:
        client: An asynchronous HTTP client (httpx.AsyncClient).
        lat: Latitude of the target location.
        lon: Longitude of the target location.

    Returns:
        A dictionary containing the provider name and temperature (float) or
        an error message string if the request fails.
    """
    try:
        params = {"lon": lon, "lat": lat, "product": "civil", "output": "json"}
        r = await client.get(API_CONFIG["seven_timer"], params=params)
        r.raise_for_status()
        temp = r.json()["dataseries"][0]["temp2m"]
        return {"provider": "7Timer!", "temp": temp}
    except Exception as e:
        logger.error("7Timer! current failed: %s", e)
        return {"provider": "7Timer!", "error": str(e)}


# --- Endpoints ---

@app.get("/weather")
async def get_weather(
        city: str = Query(..., description="The name of the city", example="Berlin"),
        lat: float = Query(..., description="Latitude coordinate", example=52.52),
        lon: float = Query(..., description="Longitude coordinate", example=13.40)
) -> dict[str, Any]:
    """Aggregates current weather data from three different providers.

    This endpoint initiates parallel async requests. It calculates a simple
    average of all successfully retrieved temperatures.

    Args:
        city: The city name for the wttr.in service.
        lat: Latitude for coordinate-based services.
        lon: Longitude for coordinate-based services.

    Returns:
        A dictionary containing the city name, the calculated average
        Celsius temperature, and a list of individual provider responses.

    Raises:
        HTTPException: 503 error if no temperatures could be retrieved from
            any of the providers.
    """
    logger.info("Requesting current weather for %s", city)
    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await asyncio.gather(
            fetch_open_meteo(client, lat, lon),
            fetch_wttr_in(client, city),
            fetch_seven_timer(client, lat, lon)
        )

    valid_temps = [res["temp"] for res in results if "temp" in res]
    if not valid_temps:
        raise HTTPException(status_code=503, detail="All services unavailable.")

    avg_temp = round(sum(valid_temps) / len(valid_temps), 1)
    return {"city": city, "average_c": avg_temp, "responses": results}


@app.get("/weather/hourly", response_class=HTMLResponse)
async def get_hourly_weather(
        lat: float = Query(..., description="Latitude coordinate", example=52.52),
        lon: float = Query(..., description="Longitude coordinate", example=13.40)
) -> str:
    """Generates an hourly weather forecast report as an HTML table.

    Fetches forecast data from Open-Meteo and 7Timer!, processes the results
    using Pandas, and renders an HTML page styled with Bootstrap.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        A string containing a complete HTML document with forecast tables.

    Raises:
        HTTPException: 500 error if data processing fails.
        HTTPException: 503 error if primary hourly data sources are unreachable.
    """
    logger.info("Generating hourly report for %s, %s", lat, lon)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Launching hourly calls
        om_params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m"}
        st_params = {"lon": lon, "lat": lat, "product": "civil", "output": "json"}

        try:
            om_res, st_res = await asyncio.gather(
                client.get(API_CONFIG["open_meteo"], params=om_params),
                client.get(API_CONFIG["seven_timer"], params=st_params)
            )
            om_res.raise_for_status()
            st_res.raise_for_status()
        except Exception as e:
            logger.error("Hourly fetch failed: %s", e)
            raise HTTPException(status_code=503, detail="Hourly services unreachable.")

    try:
        # Pandas processing
        om_json = om_res.json()["hourly"]
        df_om = pd.DataFrame({
            "Time": om_json["time"],
            "OpenMeteo (°C)": om_json["temperature_2m"]
        }).head(24)

        st_json = st_res.json()["dataseries"]
        df_st = pd.DataFrame([
            {"Hour_Offset": d["timepoint"], "7Timer (°C)": d["temp2m"]}
            for d in st_json
        ]).head(8)

        html_om = df_om.to_html(classes='table table-sm table-hover', index=False)
        html_st = df_st.to_html(classes='table table-sm table-dark', index=False)

    except Exception as e:
        logger.error("Pandas processing failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal data processing error.")

    return f"""
    <html>
        <head>
            <title>Hourly Report</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
            <style>body {{ padding: 30px; background-color: #f8f9fa; }}</style>
        </head>
        <body>
            <div class="container">
                <h1 class="mb-4">Hourly Weather: {lat}, {lon}</h1>
                <div class="row">
                    <div class="col-md-7">
                        <h3>Open-Meteo (Next 24h)</h3>
                        {html_om}
                    </div>
                    <div class="col-md-5">
                        <h3>7Timer! (3h Steps)</h3>
                        {html_st}
                    </div>
                </div>
                <hr>
                <a href="/docs" class="btn btn-secondary">API Documentation</a>
            </div>
        </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
