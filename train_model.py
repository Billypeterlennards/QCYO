from utils.preprocess import load_international_data
from models.yield_model import train_yield_model
import joblib
import os

X, y = load_international_data("data/yield_df.csv")

model = train_yield_model(X, y)

os.makedirs("saved_models", exist_ok=True)
joblib.dump(model, "saved_models/yield_model.pkl")

print("✅ Yield model trained and saved")
