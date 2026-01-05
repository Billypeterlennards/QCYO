🌱 Quantum Crop Yield Optimizer (Q-CYO)

Quantum Crop Yield Optimizer (Q-CYO) is an AI-powered agricultural decision support system that predicts crop yield, recommends fertilizer usage, and assesses weather risk using machine learning, agronomic logic, and quantum-inspired optimization.

The system consists of:

A Python Flask backend (ML + optimization)

A Flutter frontend application (Windows, Android, Web, iOS)

🧠 System Architecture
Flutter App (UI)
      ↓ HTTP (JSON)
Python Flask API (ML + Optimization)
      ↓
Predictions & Recommendations

🐍 Q-CYO – Python Backend

The backend handles all intelligence, including:

Crop yield prediction

Fertilizer optimization

Weather risk assessment

Input validation

API metrics and monitoring

It exposes a REST API consumed by the Flutter application.

📁 Backend Project Structure
Q-CYO_PYTHON_PROJECT/
│
├── api/
│   └── app.py                    # Flask API entry point
│
├── data/                         # Crop yield datasets
│
├── engine/
│   └── recommendation_engine.py  # Core recommendation logic
│
├── models/
│   ├── yield_model.py            # ML yield prediction model
│   ├── weather_risk.py           # Weather risk assessment
│   └── quantum_optimizer.py      # Fertilizer optimization logic
│
├── saved_models/
│   └── yield_model.pkl           # Trained ML model
│
├── utils/
│   └── preprocess.py             # Data preprocessing utilities
│
├── train_model.py                # Train and save ML model
├── main.py                       # CLI testing and debugging
├── requirements.txt              # Python dependencies
└── README.md                     # Backend documentation

📄 Backend Structure Explanation

api/ – REST API exposed to Flutter

data/ – Raw and processed datasets

engine/ – ML + optimization orchestration

models/ – Prediction, risk, and optimization logic

saved_models/ – Stored trained models

utils/ – Preprocessing utilities

train_model.py – Model training script

main.py – Local testing

requirements.txt – Dependencies

⚙️ Backend Setup
Install Dependencies
pip install -r requirements.txt

Train the Model (Run Once)
python train_model.py


This generates:

saved_models/yield_model.pkl

Run the API (Local)
python -m api.app


API base URL:

http://127.0.0.1:5000

🔗 Backend API Endpoints
Core Recommendation
POST /recommend

Example Request
{
  "rainfall": 120,
  "temperature": 26,
  "soil_type": "sandy",
  "crop_type": "maize",
  "area": 5
}

Example Response
{
  "yield_per_hectare": 12.46,
  "total_yield": 62.3,
  "fertilizer_kg_per_ha": 292,
  "weather_risk": "LOW"
}

Additional API Endpoints

GET

/ – API documentation

/health – Health check

/metrics – API metrics

/supported – Supported crops and soils

POST

/recommend – Default recommendation

/recommend/advanced – Quantum-inspired optimization

/recommend/simple – Lightweight formula

/recommend/batch – Batch processing

/validate-input – Input validation

🚀 Backend Deployment

Supported platforms:

Render (recommended)

Fly.io

Railway

Production start command:

gunicorn api.app:app

📱 Q-CYO – Flutter Application

The Q-CYO Flutter App is the user-facing interface designed for farmers and agricultural stakeholders.
It collects farm data and displays AI-powered recommendations from the Python backend.

🚀 Flutter App Features

Farmer-friendly UI

Crop yield prediction

Fertilizer recommendations

Weather risk alerts

Real-time API communication

Cross-platform support (Windows, Android, Web, iOS)

📁 Flutter Project Structure
Q_CYO_FLUTTER_APP/
│
├── lib/
│   ├── main.dart                 # Application entry point
│   │
│   ├── screens/
│   │   └── home_screen.dart      # Farmer input form & results display
│   │
│   └── services/
│       └── api_service.dart      # HTTP API communication
│
├── pubspec.yaml                  # Flutter dependencies
└── README.md                     # Flutter documentation

🔌 Connecting Flutter (Windows) to Python Backend
1️⃣ Add HTTP Dependency

pubspec.yaml

dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0


Run:

flutter pub get

2️⃣ Configure API Service

lib/services/api_service.dart

import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = "http://127.0.0.1:5000";

  static Future<Map<String, dynamic>> getRecommendation({
    required double rainfall,
    required double temperature,
    required String soilType,
    required String cropType,
    required double area,
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/recommend"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "rainfall": rainfall,
        "temperature": temperature,
        "soil_type": soilType,
        "crop_type": cropType,
        "area": area,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception("Failed to fetch recommendation");
    }
  }
}

3️⃣ Run Flutter App (Windows)
flutter run -d windows


⚠️ Important:
For Flutter Windows, always use:

http://127.0.0.1:5000


instead of localhost.

🌍 Production Configuration

After deploying backend:

static const String baseUrl = "https://your-backend-url";


Use HTTPS in production.

✅ Project Summary

Clean separation of frontend and backend

Real machine learning model

Quantum-inspired optimization logic

REST API architecture

Cross-platform Flutter application

Production-ready prototype

🌾 Project Name

Quantum Crop Yield Optimizer (Q-CYO)
AI-Driven Agriculture for Smarter Farming
