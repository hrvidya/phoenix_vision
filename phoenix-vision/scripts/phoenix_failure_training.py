# phoenix_failure_training.py

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import matplotlib.pyplot as plt

# ===============================
# 1. Load Dataset
# ===============================
df = pd.read_csv(r"C:\Users\abhis\OneDrive\Desktop\mainnewpro\phoenix-vision\data\logs\phoenix_dataset_20260107_144355.csv")  # <-- replace with your dataset file
print("Dataset Shape:", df.shape)
print(df.head())

# ===============================
# 2. Data Cleaning
# ===============================
# Drop rows where everything is zero (invalid samples)
df = df[(df[['lat','lon','alt_ft','airspeed_kt','heading_deg',
             'pitch_deg','roll_deg','vsi_fps']] != 0).any(axis=1)]

print("After cleaning:", df.shape)

# ===============================
# 3. Features & Labels
# ===============================
X = df[['alt_ft','airspeed_kt','heading_deg','pitch_deg','roll_deg','vsi_fps']]
y = df['failure']

# Encode labels if needed
y = y.astype("category")

# ===============================
# 4. Train-Test Split
# ===============================
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# ===============================
# 5. Train Model
# ===============================
model = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

# ===============================
# 6. Evaluation
# ===============================
y_pred = model.predict(X_test)

print("\nClassification Report:\n", classification_report(y_test, y_pred))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))

# ===============================
# 7. Feature Importance Plot
# ===============================
importances = model.feature_importances_
features = X.columns
plt.barh(features, importances)
plt.xlabel("Importance")
plt.ylabel("Feature")
plt.title("Feature Importance in Failure Prediction")
plt.show()

# ===============================
# 8. Save Model
# ===============================
joblib.dump(model, "phoenix_failure_model.pkl")
print("✅ Model saved as phoenix_failure_model.pkl")
