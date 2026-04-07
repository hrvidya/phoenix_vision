"""
phoenix_fusion_controller.py
Unified Phoenix Vision Controller:
 - failure detection (model)
 - terrain analysis (advanced_emergency_system)
 - autopilot control (FlightGear via Telnet)
 - logging & safety

Usage:
    python phoenix_fusion_controller.py

Make sure FlightGear is running with telnet enabled (port 5400).
Place phoenix_failure_model.pkl in scripts/ (or adjust MODEL_PATH).
Place data/airports.csv with icao,lat,lon,len_ft
"""

import os, time, datetime, telnetlib, joblib, math, csv, traceback
import pandas as pd

# CONFIG
HOST, PORT = "localhost", 5400
SCRIPT_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(SCRIPT_DIR, "phoenix_failure_model.pkl")
LOG_DIR = os.path.join(SCRIPT_DIR, "..", "data", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
AIRPORTS_CSV = os.path.join(SCRIPT_DIR, "..", "data", "airports.csv")

# TUNABLES
LOOP_INTERVAL = 1.0            # seconds between cycles
FAILURE_PROB_THRESH = 0.5      # minimum probability to treat as detected
GLIDE_RATIO = 9.0              # aircraft glide ratio
RESERVE_FT = 500.0             # reserve altitude for safety
MIN_RUNWAY_FT = 2500           # minimum runway length to consider
VISION_TIMEOUT = 15            # seconds allowed for vision analysis (per zone)
VISION_ENABLED = True          # set False to skip calling vision module

# ---------- UTIL / TELNET ----------
def start_telnet(host=HOST, port=PORT, timeout=10):
    tn = telnetlib.Telnet(host, port, timeout=timeout)
    return tn

def send_cmd(tn, cmd):
    tn.write((cmd + "\r\n").encode())
    time.sleep(0.04)

def read_prop(tn, prop, timeout=1.5):
    tn.write((f"get {prop}\r\n").encode())
    raw = tn.read_until(b"/>", timeout=timeout).decode(errors="ignore")
    import re
    m = re.search(r"[-+]?\d*\.\d+|\d+", raw)
    return float(m.group()) if m else 0.0

# ---------- PLANNER (local version) ----------
def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R_km * c * 0.539957

def estimate_glide_loss_ft(distance_nm, glide_ratio=GLIDE_RATIO):
    return (distance_nm * 6076.0) / glide_ratio

def bearing_to(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(phi2)
    x = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dl)
    brng = (math.degrees(math.atan2(y, x)) + 360) % 360
    return brng

def load_airports(csv_path=AIRPORTS_CSV):
    aps = []
    if not os.path.exists(csv_path):
        return aps
    with open(csv_path, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip().lower() in ("icao","id"): continue
            icao, lat, lon, length_ft = row[:4]
            aps.append({"icao":icao.strip(),"lat":float(lat),"lon":float(lon),"len_ft":float(length_ft)})
    return aps

def reachable_airports(lat, lon, alt_ft, airports, min_len_ft=MIN_RUNWAY_FT):
    reachable=[]
    for ap in airports:
        if ap["len_ft"] < min_len_ft: continue
        dist_nm = haversine_nm(lat, lon, ap["lat"], ap["lon"])
        need_ft = estimate_glide_loss_ft(dist_nm) + RESERVE_FT
        if alt_ft >= need_ft:
            reachable.append((dist_nm, ap))
    reachable.sort(key=lambda x: x[0])
    return reachable

# ---------- VISION WRAPPER (calls your advanced_emergency_system) ----------
def analyze_zones_with_vision(lat, lon, landing_candidates):
    """
    landing_candidates: list of dicts { 'name', 'coords', 'base_safety', 'distance' }
    returns: list of dicts with 'ai_score' (0-100) and obstacle dict
    """
    results = []
    try:
        if not VISION_ENABLED:
            raise ImportError("Vision disabled by config")
        from phoenix_advanced_emergency_system import EnhancedYOLOEmergencySystem
        vsys = EnhancedYOLOEmergencySystem()
        # Use the built-in analyzer for each candidate
        for cand in landing_candidates:
            coords = tuple(cand["coords"])
            # Weather & urban intelligence fetched inside system (fast)
            # We call the specialized analyzer functions directly
            weather = vsys.get_real_weather(coords)
            analysis = vsys.analyze_landing_zone(cand["name"], {"coords": coords, "type": cand.get("type","open_area"), "base_safety": cand.get("base_safety", 60)}, weather)
            # The returned structure includes ai_score and obstacles
            results.append(analysis)
        return results
    except Exception as e:
        # Vision not available or failed; do a fast simulated scoring
        # produce fallback scores based on open space and distance
        for cand in landing_candidates:
            score = cand.get("base_safety", 60) - cand.get("distance", 0) * 2.0
            results.append({
                "name": cand["name"],
                "coords": cand["coords"],
                "distance": cand.get("distance", 0),
                "ai_score": max(0, min(100, score)),
                "obstacles": {},
                "real_analysis": False
            })
        return results

# ---------- RANKING: fuse planner + vision ----------
def fuse_and_rank(airport_pick, vision_candidates):
    """
    airport_pick: dict for runway (ican, distance, heading, len_ft) or None
    vision_candidates: list of analyses (include airports too)
    We return best choice (dict) combining reachability and safety
    """
    choices = []
    # If runway pick exists, add it (vision may also analyze runway)
    if airport_pick:
        choices.append({
            "kind": "airport",
            "id": airport_pick["icao"],
            "coords": (airport_pick.get("lat", None), airport_pick.get("lon", None)),
            "distance_nm": airport_pick["distance_nm"],
            "heading_deg": airport_pick["heading_deg"],
            "ai_score": 80.0,    # give runway a base
            "len_ft": airport_pick.get("len_ft", 4000)
        })
    # add vision candidates (fields etc.)
    for v in vision_candidates:
        choices.append({
            "kind": "vision",
            "id": v["name"],
            "coords": tuple(v["coords"]),
            "distance_km": v.get("distance", 0.0),
            "ai_score": v.get("ai_score", 50.0)
        })
    # normalize & rank
    # choose by highest ai_score then smallest distance
    choices_sorted = sorted(choices, key=lambda c: (-c["ai_score"], c.get("distance_nm", c.get("distance_km", 9999))))
    return choices_sorted

# ---------- FUSION CONTROLLER MAIN ----------
def main():
    print("Phoenix Fusion Controller starting...")
    # model
    if not os.path.exists(MODEL_PATH):
        print("ERROR: model not found at", MODEL_PATH)
        return
    model = joblib.load(MODEL_PATH)
    # airports
    airports = load_airports()
    # telnet
    try:
        tn = start_telnet()
        print("Connected to FlightGear telnet.")
    except Exception as e:
        print("Cannot connect to FlightGear telnet:", e)
        return

    # logfile
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = os.path.join(LOG_DIR, f"fusion_log_{ts}.csv")
    with open(logfile, "w", newline="") as logf:
        logf.write("time,lat,lon,alt_ft,airspeed_kt,heading_deg,pitch_deg,roll_deg,vsi_fps,pred,p_prob,choice_kind,choice_id,choice_heading,choice_alt,choice_score,cmds\n")
        print("Logging to", logfile)

        try:
            while True:
                tstamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # READ telemetry
                lat = read_prop(tn, "/position/latitude-deg")
                lon = read_prop(tn, "/position/longitude-deg")
                alt = read_prop(tn, "/position/altitude-ft")
                airspeed = read_prop(tn, "/velocities/airspeed-kt")
                heading = read_prop(tn, "/orientation/heading-deg")
                pitch = read_prop(tn, "/orientation/pitch-deg")
                roll = read_prop(tn, "/orientation/roll-deg")
                vsi = read_prop(tn, "/velocities/vertical-speed-fps")

                # CLASSIFY
                feat_df = pd.DataFrame([[alt, airspeed, heading, pitch, roll, vsi]],
                                       columns=["alt_ft","airspeed_kt","heading_deg","pitch_deg","roll_deg","vsi_fps"])
                pred = model.predict(feat_df)[0]
                try:
                    prob = max(model.predict_proba(feat_df)[0])
                except:
                    prob = 1.0

                chosen = None
                cmds_sent = ""

                # If failure detected, run planner+vision fusion
                if pred != "Normal" and prob >= FAILURE_PROB_THRESH:
                    # 1) find reachable airports
                    reach = reachable_airports(lat, lon, alt, airports, min_len_ft=MIN_RUNWAY_FT)
                    airport_pick = None
                    if reach:
                        dist_nm, ap = reach[0]
                        airport_pick = {"icao": ap["icao"], "lat": ap["lat"], "lon": ap["lon"], "distance_nm": dist_nm, "heading_deg": bearing_to(lat, lon, ap["lat"], ap["lon"]), "len_ft": ap["len_ft"]}

                    # 2) generate simple vision landing candidates around current pos (nearby fields)
                    # We'll create a few ring candidates (N/E/S/W) with base safety
                    landing_candidates = []
                    rad_km = max(5, min(30, alt / 100.0))  # generate candidate distance proportional to altitude
                    offsets = [(0.008*rad_km,0),( -0.008*rad_km,0),(0,0.008*rad_km),(0,-0.008*rad_km),(0.005*rad_km,0.005*rad_km)]
                    names = ["north_field","south_field","east_field","west_field","nearby_field"]
                    for i,off in enumerate(offsets):
                        lat_c = lat + off[0]
                        lon_c = lon + off[1]
                        landing_candidates.append({"name": names[i], "coords": (lat_c, lon_c), "base_safety": 60, "distance": math.hypot(off[0], off[1])*111})

                    # 3) run vision analysis (may fallback quickly)
                    vision_results = analyze_zones_with_vision(lat, lon, landing_candidates)

                    # 4) fuse runway pick and vision
                    fused = fuse_and_rank(airport_pick, vision_results)

                    if fused:
                        best = fused[0]
                        chosen = best
                        # build commands depending on type
                        if best["kind"] == "airport":
                            target_heading = best["heading_deg"]
                            # choose target altitude: simple descent target (for demo): alt - 200*distance_nm but > 500
                            desired_alt = max(alt - (best["distance_nm"] * 200), 500)
                            throttle = 0.0
                            # send autopilot updates
                            send_cmd(tn, f"set /autopilot/heading-bug/bug-deg {target_heading}")
                            send_cmd(tn, "set /autopilot/heading-hold 1")
                            send_cmd(tn, f"set /autopilot/altitude/altitude-ft {desired_alt}")
                            send_cmd(tn, "set /autopilot/altitude-hold 1")
                            send_cmd(tn, f"set /controls/engines/engine[0]/throttle {throttle}")
                            cmds_sent = f"hdg={target_heading:.1f};alt={desired_alt:.1f};thr={throttle}"
                        else:
                            # vision-chosen open field: point to its coords, set heading + controlled descent
                            cx, cy = best["coords"]
                            target_heading = bearing_to(lat, lon, cx, cy)
                            distance_nm = haversine_nm(lat, lon, cx, cy)
                            desired_alt = max(alt - (distance_nm * 200), 200)
                            throttle = 0.0
                            # put autopilot into heading hold toward field
                            send_cmd(tn, f"set /autopilot/heading-bug/bug-deg {target_heading}")
                            send_cmd(tn, "set /autopilot/heading-hold 1")
                            send_cmd(tn, f"set /autopilot/altitude/altitude-ft {desired_alt}")
                            send_cmd(tn, "set /autopilot/altitude-hold 1")
                            send_cmd(tn, f"set /controls/engines/engine[0]/throttle {throttle}")
                            cmds_sent = f"hdg={target_heading:.1f};alt={desired_alt:.1f};thr={throttle}"

                # If no failure detected or after actions, maintain normal (no override)
                # LOG
                choice_kind = chosen["kind"] if chosen else ""
                choice_id = chosen.get("id","") if chosen else ""
                choice_heading = chosen.get("heading_deg","") if chosen else ""
                choice_alt = ""  # we write alt used in cmds_sent
                choice_score = chosen.get("ai_score","") if chosen else ""
                logf.write(f"{tstamp},{lat:.6f},{lon:.6f},{alt:.1f},{airspeed:.1f},{heading:.1f},{pitch:.2f},{roll:.2f},{vsi:.2f},{pred},{prob:.2f},{choice_kind},{choice_id},{choice_heading},{choice_alt},{choice_score},{cmds_sent}\n")
                logf.flush()

                print(f"[{tstamp}] pred={pred} p={prob:.2f} alt={alt:.0f}ft ias={airspeed:.1f}kt choice={choice_kind}/{choice_id} score={choice_score} cmds={cmds_sent}")

                time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            print("Stopped by user.")
        except Exception as e:
            print("Fusion controller error:", e)
            traceback.print_exc()
        finally:
            tn.close()

if __name__ == "__main__":
    main()
