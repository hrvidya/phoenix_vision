# Phoenix Vision: Emergency Landing AI System

## Quick Start
1. Launch FlightGear with telnet enabled:
   ```
   fgfs --telnet=5400
   ```
   (Edit path if needed or use scripts/fg_start.bat)

2. Open project in VS Code.

3. Run the autopilot controller:
   ```
   cd scripts
   python run_controller.py
   ```

4. (Optional) Run the failure logger in another terminal:
   ```
   python fg_adaptive_failure_logger.py
   ```

Logs will appear in `data/logs/`.

## Structure
- scripts/: Core Python scripts
- data/logs/: Flight logs (CSV)
- configs/: Configurations
- ui/: Streamlit dashboard (optional)
