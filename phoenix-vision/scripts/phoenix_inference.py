# phoenix_inference.py
# Real-timecd  failure detection + rule-based glide planner + autopilot interface
import telnetlib, time, datetime, os, joblib, math, csv, pandas as pd

# ------------------ CONFIG ------------------
HOST, PORT = "localhost", 5400
MODEL_PATH = r"C:\Users\abhis\OneDrive\Desktop\mainnewpro\phoenix-vision\scripts\phoenix_failure_model.pkl"
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

GLIDE_RATIO = 9.0
RESERVE_FT = 500.0
AIRPORTS_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "airports.csv")

# ------------------ HELPERS ------------------
def load_model(path=MODEL_PATH):
    print("Loading model:", path)
    return joblib.load(path)

def start_telnet(host=HOST, port=PORT, timeout=10):
    tn = telnetlib.Telnet(host, port, timeout=timeout)
    print("Telnet connected to FlightGear on", host, port)
    return tn

def send_cmd(tn, cmd):
    tn.write((cmd + "\r\n").encode())
    time.sleep(0.05)

def read_prop(tn, prop, timeout=2.0):
    tn.write((f"get {prop}\r\n").encode())
    raw = tn.read_until(b"/>", timeout=timeout).decode(errors="ignore")
    import re
    m = re.search(r"[-+]?\d*\.\d+|\d+", raw)
    return float(m.group()) if m else 0.0

# ------------------ PLANNER UTILS ------------------
def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R_km * c * 0.539957  # km -> NM

def estimate_glide_loss_ft(distance_nm, glide_ratio=GLIDE_RATIO):
    return (distance_nm * 6076.0) / glide_ratio

def bearing_to(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def load_airports(csv_path=AIRPORTS_CSV):
    aps = []
    if not os.path.exists(csv_path): return aps
    with open(csv_path, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip().lower() in ("icao","id"): continue
            icao, lat, lon, length_ft = row[:4]
            aps.append({"icao":icao.strip(),"lat":float(lat),"lon":float(lon),"len_ft":float(length_ft)})
    return aps

def choose_best_airport(lat, lon, alt_ft, airports, min_len_ft=2500):
    candidates=[]
    for ap in airports:
        if ap["len_ft"] < min_len_ft: continue
        dist_nm = haversine_nm(lat, lon, ap["lat"], ap["lon"])
        need_ft = estimate_glide_loss_ft(dist_nm) + RESERVE_FT
        if alt_ft >= need_ft:
            candidates.append((dist_nm, ap))
    if not candidates: return None
    candidates.sort(key=lambda x: x[0])
    dist, best = candidates[0]
    return {"icao": best["icao"], "distance_nm": dist, "heading_deg": bearing_to(lat, lon, best["lat"], best["lon"])}

# ------------------ MAIN LOOP ------------------
def main(loop_interval=1.0):
    model = load_model()
    airports = load_airports()
    tn = start_telnet()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = os.path.join(LOG_DIR, f"inference_log_{ts}.csv")

    with open(logfile, "w", newline="") as f:
        f.write("time,lat,lon,alt_ft,airspeed_kt,heading_deg,pitch_deg,roll_deg,vsi_fps,pred,f_prob,target_icao,cmd_heading,cmd_alt,cmd_throttle\n")
        print("Started inference loop; logging to:", logfile)

        try:
            while True:
                t = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                lat = read_prop(tn, "/position/latitude-deg")
                lon = read_prop(tn, "/position/longitude-deg")
                alt = read_prop(tn, "/position/altitude-ft")
                airspeed = read_prop(tn, "/velocities/airspeed-kt")
                heading = read_prop(tn, "/orientation/heading-deg")
                pitch = read_prop(tn, "/orientation/pitch-deg")
                roll = read_prop(tn, "/orientation/roll-deg")
                vsi = read_prop(tn, "/velocities/vertical-speed-fps")

                feat_df = pd.DataFrame([[alt, airspeed, heading, pitch, roll, vsi]],
                                       columns=["alt_ft", "airspeed_kt", "heading_deg", "pitch_deg", "roll_deg", "vsi_fps"])
                pred = model.predict(feat_df)[0]
                try:
                    prob = max(model.predict_proba(feat_df)[0])
                except:
                    prob = 1.0

                target_icao = ""
                cmd_heading = ""
                cmd_alt = ""
                cmd_throttle = None

                if pred != "Normal" and prob > 0.5:
                    pick = choose_best_airport(lat, lon, alt, airports)
                    if pick:
                        target_icao = pick["icao"]
                        cmd_heading = pick["heading_deg"]
                        cmd_alt = max(alt - 200, 800)
                        cmd_throttle = 0.0
                        from phoenix_advanced_emergency_system import EnhancedYOLOEmergencySystem

                        # After predicting EngineFailure or FuelLeak:
                        if pred in ["EngineFailure", "FuelLeak"]:
                            vision_system = EnhancedYOLOEmergencySystem()
                            vision_system.trigger_emergency_at_location((lat, lon))


                        print(f"[AI] Emergency: {pred} → Diverting to {target_icao} | Hdg={cmd_heading:.1f}°, Alt={cmd_alt:.0f}ft")

                        send_cmd(tn, f"set /autopilot/heading-bug/bug-deg {cmd_heading}")
                        send_cmd(tn, "set /autopilot/heading-hold 1")
                        send_cmd(tn, f"set /autopilot/altitude/altitude-ft {cmd_alt}")
                        send_cmd(tn, "set /autopilot/altitude-hold 1")
                        send_cmd(tn, f"set /controls/engines/engine[0]/throttle {cmd_throttle}")
                    else:
                        print("[AI] No reachable airport! Throttle idle.")
                        send_cmd(tn, "set /controls/engines/engine[0]/throttle 0.0")

                f.write(f"{t},{lat},{lon},{alt},{airspeed},{heading},{pitch},{roll},{vsi},{pred},{prob},{target_icao},{cmd_heading},{cmd_alt},{cmd_throttle}\n")
                f.flush()

                print(f"[{t}] pred={pred} p={prob:.2f} alt={alt:.0f}ft ias={airspeed:.1f}kt target={target_icao}")
                time.sleep(loop_interval)

        except KeyboardInterrupt:
            print("Stopping inference loop.")
            tn.close()

if __name__ == "__main__":
    main()
