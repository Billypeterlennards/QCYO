def optimize_fertilizer(predicted_yield, soil_type, crop_type):
    """
    Quantum-inspired fertilizer optimizer (rule + optimization based)
    Returns fertilizer amount in kg/ha
    """

    # Base fertilizer depends on yield target
    base_fertilizer = predicted_yield * 15  # kg/ha

    # Soil adjustment factors
    soil_factor = {
        "sandy": 1.3,   # nutrients leach faster
        "loam": 1.0,    # balanced soil
        "clay": 0.8     # retains nutrients
    }.get(soil_type.lower(), 1.0)

    # Crop nutrient demand
    crop_factor = {
        "maize": 1.2,
        "rice": 1.1,
        "wheat": 1.0
    }.get(crop_type.lower(), 1.0)

    optimized_fertilizer = base_fertilizer * soil_factor * crop_factor

    return round(optimized_fertilizer)
