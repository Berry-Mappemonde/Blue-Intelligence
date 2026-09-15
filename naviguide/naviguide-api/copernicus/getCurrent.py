"""
Fetch sea-current data from Copernicus Marine for a given geographic position.

Dataset: cmems_mod_glo_phy_anfc_0.083deg_PT1H-m
Variables: uo (eastward_sea_water_velocity), vo (northward_sea_water_velocity)
"""
import math
import pandas as pd
import numpy as np
import copernicusmarine
from datetime import datetime, timedelta


def get_current_data_at_position(latitude, longitude, username=None, password=None):
    """
    Fetch surface sea-current data at a given position.

    Args:
        latitude  (float) : latitude  (-90 to 90)
        longitude (float) : longitude (-180 to 180)
        username  (str)   : Copernicus Marine username
        password  (str)   : Copernicus Marine password

    Returns:
        dict | None : current data (speed m/s, knots, direction °)
                      or None on error.
    """
    try:
        # Global Ocean Physics Analysis and Forecast — currents at surface
        dataset_id = "cmems_mod_glo_phy_anfc_0.083deg_PT1H-m"

        # Time window: yesterday (1-day processing lag)
        end_date   = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=1)

        margin = 0.2   # ±0.2° box around the point

        print(f"🌊 Récupération des courants marins pour:")
        print(f"   Latitude  : {latitude}°")
        print(f"   Longitude : {longitude}°")
        print(f"   Date      : {end_date.strftime('%Y-%m-%d')}")

        dataset = copernicusmarine.open_dataset(
            dataset_id=dataset_id,
            username=username,
            password=password,
            variables=["uo", "vo"],          # eastward / northward current
            minimum_longitude=longitude - margin,
            maximum_longitude=longitude + margin,
            minimum_latitude=latitude  - margin,
            maximum_latitude=latitude  + margin,
            start_datetime=start_date.strftime("%Y-%m-%d"),
            end_datetime=end_date.strftime("%Y-%m-%d"),
            coordinates_selection_method="nearest",
        )

        # Select the nearest point
        point_data = dataset.sel(
            latitude=latitude,
            longitude=longitude,
            method="nearest"
        )

        # Surface (depth=0 or first level)
        def _extract_surface(var_name):
            da = point_data[var_name].isel(time=-1)
            # If depth dimension exists, take surface (index 0)
            if "depth" in da.dims:
                da = da.isel(depth=0)
            return float(da.values)

        u_current = _extract_surface("uo")   # m/s — east component
        v_current = _extract_surface("vo")   # m/s — north component

        # Guard: NaN means point is on land or outside dataset coverage
        if math.isnan(u_current) or math.isnan(v_current):
            print("⚠️  u/v current is NaN — point may be on land or outside dataset coverage")
            return None

        # Scalar speed (m/s → knots)
        speed_ms     = math.sqrt(u_current**2 + v_current**2)
        speed_knots  = speed_ms * 1.94384
        speed_kmh    = speed_ms * 3.6

        # Direction the current is going (oceanographic)
        # 0° = North, 90° = East, 180° = South, 270° = West
        direction_deg = (math.atan2(u_current, v_current) * 180.0 / math.pi) % 360

        result = {
            "latitude":        latitude,
            "longitude":       longitude,
            "u_component":     round(u_current,  4),  # m/s (east)
            "v_component":     round(v_current,  4),  # m/s (north)
            "speed_ms":        round(speed_ms,   3),
            "speed_knots":     round(speed_knots, 2),
            "speed_kmh":       round(speed_kmh,  2),
            "direction_deg":   round(direction_deg, 1),
        }

        # Timestamp
        try:
            ts = point_data.time.isel(time=-1).values
            if isinstance(ts, np.datetime64):
                result["timestamp"] = pd.Timestamp(ts).isoformat()
        except Exception:
            pass

        print(f"✅ Courant de surface : {result['speed_knots']} nœuds → {result['direction_deg']}°")
        return result

    except Exception as e:
        print(f"❌ Erreur récupération courants : {e}")
        import traceback
        traceback.print_exc()
        return None


def overCurrent(latitude, longitude, threshold_knots=2.0, username=None, password=None):
    """
    Return True if current speed exceeds the given threshold (default 2 kn).
    Used to mark alert points on the route.
    """
    data = get_current_data_at_position(latitude, longitude, username, password)
    if data is None:
        return False
    return data["speed_knots"] > threshold_knots
