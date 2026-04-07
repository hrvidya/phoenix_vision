import telnetlib, time, datetime, os

HOST, PORT = "localhost", 5400
tn = telnetlib.Telnet(HOST, PORT)

def send(cmd):
    tn.write(f"{cmd}\r\n".encode())
    time.sleep(0.05)

def get(prop):
    tn.write(f"get {prop}\r\n".encode())
    out = tn.read_until(b"/>", timeout=2).decode(errors="ignore").strip()
    if "'" in out:
        try:
            return float(out.split("'")[1])
        except:
            return 0.0
    try:
        return float(out.split()[-1])
    except:
        return 0.0

# Logs directory
logs_dir = os.path.join(os.path.dirname(__file__), "..", "data", "logs")
os.makedirs(logs_dir, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file_path = os.path.join(logs_dir, f"phoenix_dataset_{timestamp}.csv")

# Failures
scenarios = [
    ("Normal", []),
    ("EngineFailure", [
        "setd /controls/engines/engine[0]/throttle 0",
        "setb /engines/engine[0]/running false"
    ]),
    ("FuelLeak", [
        "setd /consumables/fuel/tank[0]/level-gal 0"
    ])
]

duration = 10     # seconds per scenario
interval = 1      # log every second

with open(log_file_path, "w") as f:
    header = "time,lat,lon,alt_ft,airspeed_kt,heading_deg,pitch_deg,roll_deg,vsi_fps,failure\n"
    f.write(header)

    for failure_name, commands in scenarios:
        print(f"=== Scenario: {failure_name} ===")
        for c in commands:
            send(c)

        start = time.time()
        while time.time() - start < duration:
            t = datetime.datetime.now().strftime("%H:%M:%S")

            # 🔑 Fetch everything before writing
            lat     = get("/position/latitude-deg")
            lon     = get("/position/longitude-deg")
            alt     = get("/position/altitude-ft")
            airspd  = get("/velocities/airspeed-kt")
            heading = get("/orientation/heading-deg")
            pitch   = get("/orientation/pitch-deg")
            roll    = get("/orientation/roll-deg")
            vsi     = get("/velocities/vertical-speed-fps")

            row = f"{t},{lat},{lon},{alt},{airspd},{heading},{pitch},{roll},{vsi},{failure_name}\n"
            f.write(row)
            print(row.strip())
            time.sleep(interval)

        # reset for next run
        send("setb /engines/engine[0]/running true")
        send("setd /controls/engines/engine[0]/throttle 0.5")
        send("setd /consumables/fuel/tank[0]/level-gal 20")

print(f"✅ Clean dataset saved: {log_file_path}")
