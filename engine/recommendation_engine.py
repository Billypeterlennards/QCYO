from models.yield_model import load_model, predict_yield
from models.weather_risk import assess_risk
from models.quantum_optimizer import optimize_fertilizer

model = load_model()

def generate(data: dict):
    predicted_yield = predict_yield(
        model,
        data["rainfall"],
        data["temperature"]
    )

    risk = assess_risk(
        data["rainfall"],
        data["temperature"]
    )

    fertilizer = optimize_fertilizer(
        predicted_yield,
        data["soil_type"],
        data["crop_type"]
    )

    total_yield = predicted_yield * data["area"]

    return {
        "yield_per_hectare": round(predicted_yield, 2),
        "total_yield": round(total_yield, 2),
        "fertilizer_kg_per_ha": fertilizer,
        "weather_risk": risk
    }
