from engine.recommendation_engine import generate

def main():
    print("\n🌱 Quantum Crop Yield Optimizer\n")

    data = {
        "rainfall": float(input("Rainfall (mm): ")),
        "temperature": float(input("Temperature (°C): ")),
        "soil_type": input("Soil type (sandy/loam/clay): "),
        "crop_type": input("Crop type (maize/rice/wheat): "),
        "area": float(input("Area (hectares): "))
    }

    result = generate(data)

    print("\n✅ FARM RECOMMENDATION")
    for k, v in result.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
