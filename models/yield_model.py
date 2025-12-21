import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor

MODEL_PATH = "saved_models/yield_model.pkl"

# ---------- TRAINING (OFFLINE ONLY) ----------
def train_yield_model(X, y):
    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42
    )
    model.fit(X, y)
    return model


# ---------- LOADING (APP RUNTIME) ----------
def load_model():
    return joblib.load(MODEL_PATH)


# ---------- PREDICTION (APP RUNTIME) ----------
def predict_yield(model, rainfall, temperature):
    X_new = pd.DataFrame(
        [[rainfall, temperature]],
        columns=["rainfall", "temperature"]
    )
    return model.predict(X_new)[0]
