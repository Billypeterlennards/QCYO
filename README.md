# 🌱 Q-CYO – Python Backend

Quantum Crop Yield Optimizer (Q-CYO) is a Python backend that uses machine learning and agronomic logic to predict crop yield, recommend fertilizer amounts, and assess weather risk.  
It exposes a REST API used by a Flutter application (Web, Android, Windows, iOS).

---
## 📁 Project Structure

```text
Q-CYO_PYTHON_PROJECT/
│
├── api/
│   └── app.py                  # Flask API entry point
│
├── data/                       # Crop yield datasets
│
├── engine/
│   └── recommendation_engine.py  # Core recommendation logic
│
├── models/
│   ├── yield_model.py          # ML yield prediction model
│   ├── weather_risk.py         # Weather risk assessment
│   └── quantum_optimizer.py    # Fertilizer optimization logic
│
├── saved_models/
│   └── yield_model.pkl         # Trained ML model
│
├── utils/
│   └── preprocess.py           # Data preprocessing utilities
│
├── train_model.py              # Train and save ML model
├── main.py                     # CLI testing and debugging
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

## Setup

Install dependencies:

pip install -r requirements.txt

---

## Train the Model (Run Once)

python train_model.py

This trains the yield prediction model and saves it to:
saved_models/yield_model.pkl

---

## Run the API (Local)

python -m api.app

The API runs at:
http://127.0.0.1:5000

---

## API Endpoint

POST /recommend

Request (JSON):

{
  "rainfall": 120,
  "temperature": 26,
  "soil_type": "sandy",
  "crop_type": "maize",
  "area": 5
}

Response (JSON):

{
  "yield_per_hectare": 12.46,
  "total_yield": 62.3,
  "fertilizer_kg_per_ha": 292,
  "weather_risk": "LOW"
}

---

## Flutter Integration

The Flutter app communicates with this backend via HTTP requests.
Python code is not placed inside the Flutter project.

---

## Deployment

The backend can be deployed on free platforms such as:
- Render (recommended)
- Railway
- Fly.io

Production start command:

gunicorn api.app:app

---

## Summary

- Real machine learning model
- Real training and predictions
- REST API backend
- Production-ready prototype
