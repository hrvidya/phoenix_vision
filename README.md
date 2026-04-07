# ✈️ Phoenix Vision: AI-Driven Emergency Flight Assistance System

## 📌 Overview
Phoenix Vision is an AI-powered aviation safety system designed to detect in-flight failures and assist in emergency landing decisions using real-time flight data. It integrates machine learning, glide physics, and autopilot control within the FlightGear simulator.

The system improves flight safety by:
- Detecting failures instantly  
- Recommending safe landing locations  
- Assisting with autonomous glide control  
- Providing real-time monitoring via a dashboard  

---

## 🚀 Key Features
- Real-time flight data acquisition via Telnet  
- AI-based failure detection (Random Forest)  
- Emergency glide path planning  
- Reachable airport selection using physics  
- Autopilot command generation  
- YOLO-based obstacle detection  
- Live dashboard (Streamlit)  
- Simulation-based safe testing  

---

## 🧠 Core Algorithm

Hybrid AI Approach:

Machine Learning (Random Forest)  
+ Glide Physics Model  
+ Rule-Based Safety Logic  
+ Autopilot Control  

### Workflow:
1. Read real-time flight data  
2. Predict failure using ML model  
3. If failure detected:
   - Compute reachable airports  
   - Apply glide constraints  
   - Select safest airport  
4. Generate autopilot commands  
5. Assist in emergency landing  

---

## 📂 Project Structure

Phoenix-Vision/
│
├── phoenix_failure_training.py     # Train ML model  
├── phoenix_inference.py            # Core AI + decision engine ⭐  
├── phoenix_path_planner.py         # Emergency landing map  
├── phoenix_yolo_analyzer.py        # Obstacle detection  
├── phoenix_demo_autopilot.py       # Full system demo  
├── phoenix_dashboard.py            # Streamlit dashboard  
│
├── dataset/                        # Flight data  
├── models/  
│   └── phoenix_failure_model.pkl   # Trained model  
│
├── airports.csv                   # Airport database  
└── README.md  

---

## ⚙️ Technologies Used
- Python  
- FlightGear Simulator  
- Telnet (telnetlib)  
- Scikit-learn (Random Forest)  
- YOLOv8 (Ultralytics)  
- Streamlit  
- Matplotlib / Plotly / Folium  

---

## 📊 Data Collection
- Data collected via Telnet from FlightGear  
- Logged every 1 second for 10 seconds per scenario  

### Features:
- Altitude  
- Airspeed  
- Heading  
- Pitch  
- Roll  
- Vertical Speed  

### Scenarios:
- Normal Flight  
- Engine Failure  
- Fuel Leak  

---

## 🤖 Machine Learning Model
- Model: Random Forest Classifier  
- Type: Supervised Learning  

### Input Features:
- alt_ft  
- airspeed_kt  
- heading_deg  
- pitch_deg  
- roll_deg  
- vsi_fps  

### Output:
- Normal  
- EngineFailure  
- FuelLeak  

### Why Random Forest?
- Handles non-linear data  
- Resistant to overfitting  
- Works well with noisy flight data  
- Provides feature importance  

---

## 🛫 Emergency Path Planning
- Glide Ratio: 9:1  
- Distance: Haversine Formula  

### Factors Considered:
- Altitude  
- Distance  
- Runway length  
- Wind conditions  

### Output:
- Best reachable airport  
- Safe glide path  
- Autopilot commands  

---

## 👁️ Vision Module (YOLO)
- Detects:
  - Buildings  
  - Vehicles  
  - People  
  - Trees  

- Outputs:
  - Obstacle density  
  - Open space estimation  
  - Safety score  

---

## 🖥️ Dashboard
Built using Streamlit

### Displays:
- Real-time telemetry  
- AI predictions + confidence  
- Selected airport  
- Altitude & airspeed graphs  
- Interactive emergency map  

---

## 🎮 Demo Workflow

1. Start FlightGear with Telnet enabled  

2. Run:
python phoenix_demo_autopilot.py

3. System will:
- Simulate engine failure  
- Detect failure using AI  
- Activate autopilot  
- Log telemetry  
- Generate graphs  

---

## 📈 Outputs
- CSV logs (telemetry + predictions)  

### Graphs:
- Altitude vs Time  
- Airspeed vs Time  
- Heading vs Time  

---

## 🛡️ Safety & Limitations

### Advantages:
- Reduces pilot workload  
- Fast failure detection  
- Intelligent emergency guidance  

### Limitations:
- Simulation only (not certified)  
- Approximate glide calculations  
- Vision depends on image quality  

---

## 🔮 Future Improvements
- LiDAR / RADAR integration  
- Real satellite imagery  
- Weather-aware planning  
- Dynamic glide ratio  
- Real aircraft integration  

---

## 🏆 Key File
👉 phoenix_inference.py  

This is the core module integrating:
- ML prediction  
- Path planning  
- Autopilot control  

---

## 📌 Conclusion
Phoenix Vision demonstrates how AI, simulation, and physics can be combined to improve aviation safety through intelligent, real-time emergency assistance.

---
