"""
phoenix_demo_autopilot.py
-------------------------------------------------------
Phoenix Vision - Step 4 Demonstration Script
-------------------------------------------------------
✅ Connects to FlightGear via Telnet
✅ Simulates engine failure
✅ Runs AI failure detector (trained model)
✅ Activates autopilot glide control
✅ Logs all data + auto-generates graphs
-------------------------------------------------------
"""

import telnetlib, time, datetime, os, joblib, math, pandas as pd, matplotlib.pyplot as plt

# ------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------
HOST = "localhost"
PORT = 5400
MODEL_PATH = r"C:\Users\lenovo\Downloads\phoenix-vision\scripts\phoenix_failure_model.pkl"
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "demo_logs")
os.makedirs(LOG_DIR, exist_ok=True)

GLIDE_RATIO = 9.0
RESERVE_FT = 500.0

print("\n🚀 Phoenix Vision - AI Autopilot Demonstration Starting...\n")

# ------------------------------------------------------------------
# TELNET UTILITIES
# ------------------------------------------------------------------
def connect_telnet(host=HOST, port=PORT):
    tn = telnetlib.Telnet(host, port)
    print(f"✅ Connected to FlightGear at {host}:{port}")
    return tn

def send_cmd(tn, cmd):
    tn.write((cmd + "\r\n").encode())
    time.sleep(0.05)

def read_prop(tn, prop):
    tn.write((f"get {prop}\r\n").encode())
    raw = tn.read_until(b"/>", timeout=2).decode(errors="ignore")
    import re
    m = re.search(r"[-+]?\d*\.\d+|\d+", raw)
    return float(m.group()) if m else 0.0

# ------------------------------------------------------------------
# BASIC GEOMETRY UTILS
# ------------------------------------------------------------------
def haversine_nm(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return (R * c) * 0.539957  # km → NM

def bearing_to(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

# ------------------------------------------------------------------
# LOAD MODEL
# ------------------------------------------------------------------
print("🧠 Loading AI model...")
model = joblib.load(MODEL_PATH)
print("✅ Model loaded successfully!\n")

# ------------------------------------------------------------------
# CONNECT TO FLIGHTGEAR
# ------------------------------------------------------------------
tn = connect_telnet()

# ------------------------------------------------------------------
# LOG SETUP
# ------------------------------------------------------------------
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
logfile = os.path.join(LOG_DIR, f"demo_run_{timestamp}.csv")
print(f"🧾 Logging telemetry to: {logfile}\n")

# ------------------------------------------------------------------
# MAIN DEMO FLOW
# ------------------------------------------------------------------
print("📡 Gathering live telemetry...")
time.sleep(3)

lat = read_prop(tn, "/position/latitude-deg")
lon = read_prop(tn, "/position/longitude-deg")
alt = read_prop(tn, "/position/altitude-ft")
ias = read_prop(tn, "/velocities/airspeed-kt")
hdg = read_prop(tn, "/orientation/heading-deg")
pitch = read_prop(tn, "/orientation/pitch-deg")
roll = read_prop(tn, "/orientation/roll-deg")
vsi = read_prop(tn, "/velocities/vertical-speed-fps")

print(f"📍 Initial position: {lat:.4f}, {lon:.4f}, {alt:.0f} ft | IAS={ias:.1f} kt | HDG={hdg:.1f}\n")

# Simulate engine failure
print("⚠️ Triggering ENGINE FAILURE in FlightGear...\n")
send_cmd(tn, "set /engines/engine[0]/failed true")
time.sleep(2)

# Feature vector
feat_df = pd.DataFrame([[alt, ias, hdg, pitch, roll, vsi]],
                       columns=["alt_ft", "airspeed_kt", "heading_deg", "pitch_deg", "roll_deg", "vsi_fps"])
pred = model.predict(feat_df)[0]
prob = max(model.predict_proba(feat_df)[0])

print(f"🤖 AI MODEL → {pred} (confidence={prob:.2f})")

# ------------------------------------------------------------------
# AI-BASED CONTROL
# ------------------------------------------------------------------
if pred == "EngineFailure" and prob > 0.5:
    print("🧭 AI activating emergency glide autopilot...\n")

    target_heading = (hdg + 45) % 360
    target_alt = max(alt - 1000, 800)
    throttle = 0.0

    send_cmd(tn, f"set /autopilot/heading-bug/bug-deg {target_heading}")
    send_cmd(tn, "set /autopilot/heading-hold 1")
    send_cmd(tn, f"set /autopilot/altitude/altitude-ft {target_alt}")
    send_cmd(tn, "set /autopilot/altitude-hold 1")
    send_cmd(tn, f"set /controls/engines/engine[0]/throttle {throttle}")

    print(f"🛬 Autopilot set → HDG={target_heading:.1f}° | ALT={target_alt:.0f} ft | THR={throttle}")
else:
    print("✅ No failure detected. Maintaining normal flight.\n")

# ------------------------------------------------------------------
# LOG LIVE TELEMETRY FOR 30 SECONDS
# ------------------------------------------------------------------
data_log = []
print("\n📊 Capturing flight data for 30 seconds...\n")

for i in range(30):
    t = datetime.datetime.now().strftime("%H:%M:%S")
    alt = read_prop(tn, "/position/altitude-ft")
    ias = read_prop(tn, "/velocities/airspeed-kt")
    hdg = read_prop(tn, "/orientation/heading-deg")

    data_log.append({"time": t, "alt_ft": alt, "airspeed_kt": ias, "heading_deg": hdg})
    print(f"⏱️ {i:02d}s | Alt={alt:.0f} ft | IAS={ias:.1f} kt | HDG={hdg:.1f}")
    time.sleep(1)

pd.DataFrame(data_log).to_csv(logfile, index=False)
print("\n✅ Data logging complete.")

# ------------------------------------------------------------------
# GENERATE PERFORMANCE PLOTS
# ------------------------------------------------------------------
print("📈 Generating telemetry graphs...")

df = pd.DataFrame(data_log)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Convert time column to datetime if it's not already
df["time"] = pd.to_datetime(df["time"])

# Create figure and subplots
fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

# --- Altitude ---
axes[0].plot(df["time"], df["alt_ft"], color='blue', linewidth=1.8, label="Altitude (ft)")
axes[0].set_ylabel("Altitude (ft)")
axes[0].legend(loc="upper right")
axes[0].grid(True, linestyle="--", alpha=0.6)

# --- Airspeed ---
axes[1].plot(df["time"], df["airspeed_kt"], color='orange', linewidth=1.8, label="Airspeed (kt)")
axes[1].set_ylabel("Airspeed (kt)")
axes[1].legend(loc="upper right")
axes[1].grid(True, linestyle="--", alpha=0.6)

# --- Heading ---
axes[2].plot(df["time"], df["heading_deg"], color='green', linewidth=1.8, label="Heading (°)")
axes[2].set_ylabel("Heading (°)")
axes[2].legend(loc="upper right")
axes[2].grid(True, linestyle="--", alpha=0.6)

# Format X-axis (time)
axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
plt.xticks(rotation=30)
axes[2].set_xlabel("Time (HH:MM:SS)")

# Title and layout adjustments
fig.suptitle("Phoenix Vision AI Autopilot Demonstration", fontsize=15, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.96])

# Display
plt.show()


print("\n🛩️ DEMONSTRATION COMPLETE.")
print("➡️ Check FlightGear instruments for AI glide response.")
print("➡️ Graphs show how altitude and airspeed changed under AI control.")
