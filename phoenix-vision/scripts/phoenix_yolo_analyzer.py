"""
phoenix_yolo_analyzer.py
Simple wrapper around YOLOv8 (ultralytics) for terrain/obstacle scoring.
Provides:
 - YOLOAnalyzer.analyze_image_path(image_path)
 - YOLOAnalyzer.analyze_tile(coords)  # downloads OSM tile and runs detector (optional)
If YOLO isn't installed or fails, returns a simulated safe/unsafe profile.
"""

import os, math, requests, tempfile
try:
    from ultralytics import YOLO
    import cv2, numpy as np
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False

class YOLOAnalyzer:
    def __init__(self, model_name="yolov8n.pt"):
        self.model_name = model_name
        self.model = None
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(model_name)
                print("YOLO model loaded:", model_name)
            except Exception as e:
                print("YOLO load failed:", e)
                self.model = None

    def analyze_image_path(self, image_path):
        """Run YOLO on a local image path. Returns dict of counts and confidence."""
        if not (YOLO_AVAILABLE and self.model):
            return self._simulated_result()
        try:
            img = cv2.imread(image_path)
            res = self.model(img)[0]
            stats = {"buildings":0,"vehicles":0,"persons":0,"trees":0,"open_space":50,"confidence":0.0,"real_analysis":True}
            if hasattr(res, "boxes") and res.boxes is not None:
                for box in res.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    stats["confidence"] = max(stats["confidence"], conf)
                    # Map common COCO names
                    name = self.model.names.get(cls_id, "")
                    if name in ("car","truck","bus","motorcycle"):
                        stats["vehicles"] += 1
                    elif name in ("person",):
                        stats["persons"] += 1
                    elif name in ("tree",):  # may not exist in COCO small models
                        stats["trees"] += 1
                    elif name in ("building",):
                        stats["buildings"] += 1
            # derive open_space heuristically
            stats["open_space"] = max(10, 100 - (stats["buildings"]*5 + stats["vehicles"]*3 + stats["trees"]*2))
            return stats
        except Exception as e:
            print("YOLO analyze error:", e)
            return self._simulated_result()

    def analyze_tile(self, coords, zoom=16):
        """Download an OSM tile and analyze it. coords = (lat, lon).
        This is optional and may be blocked by tile server rate-limits.
        """
        lat, lon = coords
        # convert coords to tile x,y (sloppy but usable)
        try:
            x, y = self._deg2tile(lat, lon, zoom)
            tile_url = f"https://tile.openstreetmap.org/{zoom}/{x}/{y}.png"
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            r = requests.get(tile_url, timeout=10)
            tmp.write(r.content)
            tmp.flush()
            tmp.close()
            stats = self.analyze_image_path(tmp.name)
            os.unlink(tmp.name)
            return stats
        except Exception as e:
            print("Tile download/analyze failed:", e)
            return self._simulated_result()

    def _deg2tile(self, lat_deg, lon_deg, zoom):
        lat_rad = math.radians(lat_deg)
        n = 2.0 ** zoom
        x = int((lon_deg + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def _simulated_result(self):
        # lightweight deterministic fallback
        return {"buildings":5,"vehicles":7,"persons":2,"trees":12,"open_space":60,"confidence":0.0,"real_analysis":False}

# quick local test
if __name__ == "__main__":
    ya = YOLOAnalyzer()
    print("Sample analyze:", ya._simulated_result())
