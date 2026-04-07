"""
phoenix_path_planner.py
--------------------
Live AI-based Emergency Landing Map for FlightGear

Features:
 - Reads live aircraft position and altitude from FlightGear via Telnet
 - Displays all reachable airports ranked by AI safety score
 - Auto-refreshes same ai_live_map.html every few seconds
 - Automatically opens map in browser
"""

import os, time, math, telnetlib, re, random, requests, folium, webbrowser
import pandas as pd

# ================= Configuration =================
HOST = "localhost"
PORT = 5400
GLIDE_RATIO = 9.0
RESERVE_FT = 500.0
UPDATE_INTERVAL = 5  # seconds between updates
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
AIRPORT_CSV = os.path.join(DATA_DIR, "airports.csv")
OUTPUT_HTML = os.path.join(DATA_DIR, "ai_live_map.html")

# Default airports near Bengaluru
DEFAULT_AIRPORTS = [
    ["VOBL", 13.1986, 77.7066, 12000, "Kempegowda Intl Airport"],
    ["VOBG", 12.9499, 77.6682, 7400, "HAL Airport"],
    ["VOYK", 12.819, 77.682, 6000, "Electronic City Airstrip"],
    ["VOMY", 12.9580, 77.7010, 5500, "Yelahanka AFB"],
    ["VOJK", 13.05, 77.59, 4000, "Jakkur Aerodrome"],
]

# ================= Utility Functions =================
def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return (R_km * c) * 0.539957  # km→NM

def bearing_to(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def estimate_glide_loss_ft(distance_nm):
    return (distance_nm * 6076.0) / GLIDE_RATIO

def load_airports():
    if os.path.exists(AIRPORT_CSV):
        df = pd.read_csv(AIRPORT_CSV)
        cols = [c for c in ["icao", "lat", "lon", "length_ft", "name"] if c in df.columns]
        return df[cols].values.tolist()
    else:
        print("[WARN] Using default airport list.")
        return DEFAULT_AIRPORTS

def get_current_wind(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": True, "timezone": "auto"}
        r = requests.get(url, params=params, timeout=5)
        j = r.json()
        return float(j["current_weather"]["windspeed"])
    except:
        return 5.0

def safety_score(dist_nm, runway_ft, wind):
    runway_score = min(50, runway_ft / 200)
    dist_penalty = min(40, dist_nm * 1.5)
    wind_penalty = 10 if wind > 12 else 5 if wind > 8 else 2
    score = max(0, min(100, 100 - dist_penalty + runway_score - wind_penalty))
    return round(score, 1)

# ================= FlightGear Telnet Helpers =================
def start_telnet():
    try:
        tn = telnetlib.Telnet(HOST, PORT, timeout=5)
        print("[Connected] FlightGear Telnet active.")
        return tn
    except Exception as e:
        print(f"[WARN] Could not connect to FlightGear: {e}")
        print("[INFO] Running in demo mode (static coordinates).")
        return None

def read_prop(tn, prop, fallback=None):
    if tn is None:
        return fallback
    try:
        tn.write((f"get {prop}\r\n").encode())
        raw = tn.read_until(b"/>", timeout=1).decode(errors="ignore")
        m = re.search(r"[-+]?\d*\.\d+|\d+", raw)
        return float(m.group()) if m else fallback
    except:
        return fallback

# ================= Map Creation =================
def update_map(lat, lon, alt_ft, airports):
    wind = get_current_wind(lat, lon)
    reachable, unreachable = [], []

    for icao, alat, alon, length_ft, name in airports:
        dist_nm = haversine_nm(lat, lon, alat, alon)
        need_ft = estimate_glide_loss_ft(dist_nm) + RESERVE_FT
        score = safety_score(dist_nm, length_ft, wind)
        if alt_ft >= need_ft:
            reachable.append((icao, alat, alon, name, dist_nm, score))
        else:
            unreachable.append((icao, alat, alon, name, dist_nm, score))

    m = folium.Map(location=[lat, lon], zoom_start=9)
    folium.Marker([lat, lon],
                  popup=f"✈️ Aircraft<br>Alt: {alt_ft:.0f} ft<br>Wind: {wind:.1f} m/s",
                  icon=folium.Icon(color="red", icon="plane", prefix='fa')).add_to(m)

    for icao, alat, alon, name, dist_nm, score in reachable:
        popup = f"<b>{icao}</b> - {name}<br>Dist: {dist_nm:.1f} NM<br>Score: {score}"
        folium.Marker([alat, alon], popup=popup, icon=folium.Icon(color="green", icon="flag")).add_to(m)
        folium.PolyLine([[lat, lon], [alat, alon]], color="blue", weight=2, dash_array="5,5").add_to(m)

    for icao, alat, alon, name, dist_nm, score in unreachable:
        popup = f"<b>{icao}</b> - {name}<br>Too far ({dist_nm:.1f} NM)"
        folium.Marker([alat, alon], popup=popup, icon=folium.Icon(color="gray", icon="remove")).add_to(m)

    if reachable:
        best = sorted(reachable, key=lambda x: -x[5])[0]
        folium.Marker([best[1], best[2]],
                      popup=f"🏁 Best: {best[0]} ({best[5]} AI score)",
                      icon=folium.Icon(color="darkgreen", icon="check")).add_to(m)
        folium.PolyLine([[lat, lon], [best[1], best[2]]],
                        color="darkgreen", weight=3).add_to(m)

    m.save(OUTPUT_HTML)
    print(f"[Map Updated] Lat={lat:.4f} Lon={lon:.4f} Alt={alt_ft:.0f}ft | {time.strftime('%H:%M:%S')}")
    return m

# ================= MAIN LOOP =================
if __name__ == "__main__":
    tn = start_telnet()
    airports = load_airports()

    # Initial position
    lat, lon, alt_ft = 12.9716, 77.5946, 3000

    # Open map automatically
    if not os.path.exists(OUTPUT_HTML):
        open(OUTPUT_HTML, "w").close()
    webbrowser.open(OUTPUT_HTML, new=0)

    print("🛰️ Phoenix Vision Live Map started... Updating every 5 seconds.")
    while True:
        lat = read_prop(tn, "/position/latitude-deg", lat)
        lon = read_prop(tn, "/position/longitude-deg", lon)
        alt_ft = read_prop(tn, "/position/altitude-ft", alt_ft)
        update_map(lat, lon, alt_ft, airports)
        time.sleep(UPDATE_INTERVAL)
