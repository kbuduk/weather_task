"""Weather Aggregator Service.

This module provides a FastAPI-based web server that fetches weather data from
multiple public APIs (Open-Meteo, wttr.in, and 7Timer!) in parallel and
aggregates the results into a single JSON response.
"""

import asyncio
import logging
from typing import Any

import httpx
from fastapi import FastAPI, Query, HTTPException

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Weather Aggregator",
    description="Consolidates weather data from Open-Meteo, wttr.in, and 7Timer!",
    version="1.0.0"
)

# API Endpoints
API_CONFIG = {
    "open_meteo": "https://api.open-meteo.com/v1/forecast",
    "wttr_in": "https://wttr.in/{}?format=j1",
    "seven_timer": "http://www.7timer.info/bin/api.pl"
}


async def fetch_open_meteo(client: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
    """Fetches current temperature from the Open-Meteo API.

    Args:
        client: An asynchronous HTTP client instance.
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        A dictionary containing the provider name and temperature, or an error
        message if the request fails.
    """
    logger.info("Fetching data from Open-Meteo for lat: %s, lon: %s", lat, lon)
    try:
        params = {"latitude": lat, "longitude": lon, "current_weather": True}
        r = await client.get(API_CONFIG["open_meteo"], params=params)
        r.raise_for_status()
        data = r.json()
        temp = data["current_weather"]["temperature"]
        logger.info("Open-Meteo returned %s°C", temp)
        return {"provider": "Open-Meteo", "temp": temp}
    except Exception as e:
        logger.error("Open-Meteo request failed: %s", e)
        return {"provider": "Open-Meteo", "error": str(e)}


async def fetch_wttr_in(client: httpx.AsyncClient, city: str) -> dict[str, Any]:
    """Fetches current temperature from the wttr.in API.

    Args:
        client: An asynchronous HTTP client instance.
        city: The name of the city to query.

    Returns:
        A dictionary containing the provider name and temperature, or an error
        message if the request fails.
    """
    logger.info("Fetching data from wttr.in for city: %s", city)
    try:
        r = await client.get(API_CONFIG["wttr_in"].format(city))
        r.raise_for_status()
        data = r.json()
        temp = float(data["current_condition"][0]["temp_C"])
        logger.info("wttr.in returned %s°C", temp)
        return {"provider": "wttr.in", "temp": temp}
    except Exception as e:
        logger.error("wttr.in request failed: %s", e)
        return {"provider": "wttr.in", "error": str(e)}


async def fetch_seven_timer(client: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
    """Fetches current temperature from the 7Timer! API.

    Args:
        client: An asynchronous HTTP client instance.
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        A dictionary containing the provider name and temperature, or an error
        message if the request fails.
    """
    logger.info("Fetching data from 7Timer! for lat: %s, lon: %s", lat, lon)
    try:
        params = {"lon": lon, "lat": lat, "product": "civil", "output": "json"}
        r = await client.get(API_CONFIG["seven_timer"], params=params)
        r.raise_for_status()
        data = r.json()
        temp = data["dataseries"][0]["temp2m"]
        logger.info("7Timer! returned %s°C", temp)
        return {"provider": "7Timer!", "temp": temp}
    except Exception as e:
        logger.error("7Timer! request failed: %s", e)
        return {"provider": "7Timer!", "error": str(e)}


@app.get("/weather")
async def get_weather(
        city: str = Query(..., example="Berlin"),
        lat: float = Query(52.52, example=52.52),
        lon: float = Query(13.40, example=13.40)
) -> dict[str, Any]:
    """Aggregates weather data from multiple providers in parallel.

    Args:
        city: The name of the city for the wttr.in provider.
        lat: Latitude for coordinate-based providers.
        lon: Longitude for coordinate-based providers.

    Returns:
        A dictionary containing the location, average temperature, and individual
        responses from each provider.

    Raises:
        HTTPException: 503 error if all underlying weather services fail.
    """
    logger.info("Weather request received for %s (%s, %s)", city, lat, lon)

    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await asyncio.gather(
            fetch_open_meteo(client, lat, lon),
            fetch_wttr_in(client, city),
            fetch_seven_timer(client, lat, lon)
        )

    valid_temps = [res["temp"] for res in results if "temp" in res]

    if not valid_temps:
        logger.critical("All weather providers failed for city: %s", city)
        raise HTTPException(
            status_code=503,
            detail="All weather services are currently unavailable."
        )

    avg_temp = round(sum(valid_temps) / len(valid_temps), 1)
    logger.info("Aggregation complete for %s. Average: %s°C", city, avg_temp)

    return {
        "city": city,
        "average_c": avg_temp,
        "responses": results
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Weather Aggregator Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
