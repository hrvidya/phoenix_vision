#streamlit run phoenix_dashboard.py 
"""
Phoenix Vision Dashboard — Integrated with Path Planner
Displays:
  🛩️ Live telemetry
  🤖 Model predictions
  🗺️ Path planner map (reachable/unreachable airports + best path)
  📈 Trend charts
"""

import os, glob, math
import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_folium import st_folium
import folium
from streamlit_autorefresh import st_autorefresh

# --------------------------------------------------------------------------
# CONFIG
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "logs")
AIRPORT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "airports.csv")

GLIDE_RATIO = 9.0
RESERVE_FT = 500.0

st.set_page_config(page_title="Phoenix Vision Dashboard", layout="wide")
st.title("🛩️ Phoenix Vision — Obstacle Avoidance & Emergency Landing in Flights using Machine Learning")
st.caption("Live telemetry, AI inference, and emergency glide planning")
st_autorefresh(interval=2000, limit=None, key="phoenix_refresh")

# --------------------------------------------------------------------------
# Helper Functions
def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return (R_km * c) * 0.539957

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
        return [
            ["VOBL", 13.1986, 77.7066, 12000, "Kempegowda Intl Airport"],
            ["VOBG", 12.9499, 77.6682, 7400, "HAL Airport"],
            ["VOYK", 12.819, 77.682, 6000, "Electronic City Airstrip"],
            ["VOMY", 12.9580, 77.7010, 5500, "Yelahanka AFB"],
            ["VOJK", 13.05, 77.59, 4000, "Jakkur Aerodrome"],
        ]

def find_reachable_airports(lat, lon, alt_ft, airports):
    reachable, unreachable = [], []
    for icao, alat, alon, length_ft, name in airports:
        dist_nm = haversine_nm(lat, lon, alat, alon)
        need_ft = estimate_glide_loss_ft(dist_nm) + RESERVE_FT
        if alt_ft >= need_ft:
            reachable.append((icao, alat, alon, name, dist_nm, bearing_to(lat, lon, alat, alon)))
        else:
            unreachable.append((icao, alat, alon, name, dist_nm))
    return reachable, unreachable

# --------------------------------------------------------------------------
def get_latest_log():
    files = glob.glob(os.path.join(LOG_DIR, "fusion_log_*.csv"))
    return max(files, key=os.path.getctime) if files else None

def load_data(file):
    if file and os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame()

# --------------------------------------------------------------------------
latest_file = get_latest_log()
if not latest_file:
    st.error("⚠️ No fusion_log_*.csv found in data/logs/. Run phoenix_inference.py first.")
    st.stop()

st.sidebar.success(f"📁 Using log → {os.path.basename(latest_file)}")

df = load_data(latest_file)
if df.empty:
    st.warning("Log is empty — waiting for data …")
    st.stop()

latest = df.iloc[-1]
lat, lon, alt_ft = float(latest.lat), float(latest.lon), float(latest.alt_ft)
airspeed = getattr(latest, "airspeed_kt", 0)
pred = getattr(latest, "pred", "Unknown")
prob = getattr(latest, "f_prob", 1.0)

# --------------------------------------------------------------------------
# LIVE TELEMETRY
st.subheader("📡 Current Telemetry")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Altitude (ft)", f"{alt_ft:.0f}")
c2.metric("Airspeed (kt)", f"{airspeed:.1f}")
c3.metric("VSI (fps)", f"{getattr(latest, 'vsi_fps', 0):.1f}")
c4.metric("Heading (°)", f"{getattr(latest, 'heading_deg', 0):.1f}")

# --------------------------------------------------------------------------
# MODEL PREDICTION
st.subheader("🤖 Model Prediction")
c5, c6, c7 = st.columns(3)
c5.metric("Status", pred)
c6.metric("Confidence", f"{prob*100:.1f}%")
c7.metric("Target", getattr(latest, "target_icao", "—"))

# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# FLIGHT TRENDS
st.subheader("📈 Flight Trends")
tab1, tab2 = st.tabs(["Altitude", "Airspeed"])

with tab1:
    fig = px.line(df, x="time", y="alt_ft", title="Altitude vs Time")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig2 = px.line(df, x="time", y="airspeed_kt", title="Airspeed vs Time")
    st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------------------------------
st.caption("Phoenix Vision © 2025 | AI-powered Autonomous Emergency Landing System")
