# phoenix_path_planner.py
# Generic Emergency Landing Site Planner (Multi-City)

import math, folium, os, pandas as pd

# ================= Configuration =================
GLIDE_RATIO = 9.0
RESERVE_FT = 500.0

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_HTML = os.path.join(DATA_DIR, "ai_multiple_paths.html")

# ================= REGION AIRPORT DATABASE =================
REGION_AIRPORTS = {
    "bengaluru": [
        ["VOBL", 13.1986, 77.7066, 12000, "Kempegowda Intl Airport"],
        ["VOBG", 12.9499, 77.6682, 7400, "HAL Airport"],
        ["VOML", 12.9570, 77.7010, 5500, "Yelahanka AFB"],
        ["VOTV", 12.8600, 77.5700, 4000, "Jakkur Aerodrome"]
    ],

    "chennai": [
        ["VOMM", 12.9941, 80.1709, 11000, "Chennai Intl Airport"],
        ["VOHS", 13.0486, 80.2090, 6000, "Hosur Airport"],
        ["VOPC", 11.6410, 78.1790, 5300, "Salem Airport"]
    ],

    "hyderabad": [
        ["VOHS", 17.2403, 78.4294, 13900, "Rajiv Gandhi Intl Airport"],
        ["VOPN", 16.5426, 79.3187, 5000, "Nalgonda Airstrip"]
    ],

    "mumbai": [
        ["VABB", 19.0896, 72.8656, 11000, "Chhatrapati Shivaji Intl"],
        ["VAJJ", 18.5765, 73.9197, 6000, "Pune Airport"]
    ],

    "delhi": [
        ["VIDP", 28.5562, 77.1000, 14500, "Indira Gandhi Intl Airport"],
        ["VIJN", 25.4912, 78.5581, 6000, "Jhansi Airport"]
    ]
}

# ================= Utility Functions =================
def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return (R_km * c) * 0.539957  # km → NM

def bearing_to(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def estimate_glide_loss_ft(distance_nm):
    return (distance_nm * 6076) / GLIDE_RATIO

# ================= Core Logic =================
def find_reachable_airports(lat, lon, alt_ft, airports):
    reachable, unreachable = [], []

    for icao, alat, alon, length_ft, name in airports:
        dist_nm = haversine_nm(lat, lon, alat, alon)
        required_alt = estimate_glide_loss_ft(dist_nm) + RESERVE_FT

        if alt_ft >= required_alt:
            reachable.append((icao, alat, alon, length_ft, name, dist_nm,
                              bearing_to(lat, lon, alat, alon)))
        else:
            unreachable.append((icao, alat, alon, length_ft, name, dist_nm))

    return reachable, unreachable

def create_path_map(lat, lon, alt_ft, reachable, unreachable):
    m = folium.Map(location=[lat, lon], zoom_start=8)

    folium.Marker(
        [lat, lon],
        popup=f"Aircraft Position<br>Altitude: {alt_ft:.0f} ft",
        icon=folium.Icon(color="red", icon="plane", prefix="fa")
    ).add_to(m)

    for icao, alat, alon, length_ft, name, dist_nm, bearing in reachable:
        folium.Marker(
            [alat, alon],
            popup=f"<b>{icao}</b><br>{name}<br>{dist_nm:.1f} NM<br>Bearing {bearing:.1f}°",
            icon=folium.Icon(color="green", icon="flag")
        ).add_to(m)

        folium.PolyLine([[lat, lon], [alat, alon]],
                        color="blue", weight=2, dash_array="5,5").add_to(m)

    for icao, alat, alon, length_ft, name, dist_nm in unreachable:
        folium.Marker(
            [alat, alon],
            popup=f"{icao} (Unreachable)",
            icon=folium.Icon(color="gray", icon="remove")
        ).add_to(m)

    if reachable:
        best = min(reachable, key=lambda x: x[5])
        folium.PolyLine([[lat, lon], [best[1], best[2]]],
                        color="darkblue", weight=4).add_to(m)

        folium.Marker(
            [best[1], best[2]],
            popup=f"🏁 Best Landing Site<br>{best[0]}<br>{best[4]}",
            icon=folium.Icon(color="darkgreen", icon="check")
        ).add_to(m)

    m.save(OUTPUT_HTML)
    print(f"✅ Map generated → {OUTPUT_HTML}")

# ================= Main =================
if __name__ == "__main__":

    # 🔹 CHANGE ONLY THIS SECTION 🔹
    CITY = "chennai"     # bengaluru / chennai / hyderabad / mumbai / delhi
    lat, lon = 12.9, 80.2
    alt_ft = 6000
    # 🔹 ---------------------- 🔹

    airports = REGION_AIRPORTS[CITY]
    reachable, unreachable = find_reachable_airports(lat, lon, alt_ft, airports)
    create_path_map(lat, lon, alt_ft, reachable, unreachable)
