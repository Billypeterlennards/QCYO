"""
Shared feature-encoding logic for the crop yield model.

AUDIT FIX (critical, real bug): before this fix, training and inference
each had their own INDEPENDENT encoding logic that silently diverged:

- train_model.py's load_data() called `pd.get_dummies(X, drop_first=True)`
  on whatever columns happened to be in the CSV it was pointed at.
- recommendation_engine.py's predict_yield_ml() built a feature dict via
  ad-hoc keyword matching on feature NAMES ('rain' in name.lower(), etc.)
  and fed raw strings like "sandy"/"maize" directly into the model.
- The .pkl actually committed to this repo (saved_models/yield_model.pkl)
  turned out to have been trained on an entirely different, unrelated
  dataset (a global per-country crop yield dataset with 114 one-hot
  columns like `Area_Ghana`, `Item_Maize`) - not this project's own
  Rainfall/Temperature/Soil_Type/Crop schema at all. Verified empirically:
  every real prediction attempt through the old code threw an exception
  (feature-count mismatch, plus a separate scikit-learn pickle version
  incompatibility), was silently caught, and fell back to the formula -
  meaning the "ML model" was 100% non-functional despite the API
  unconditionally reporting `ml_model_used: true`.

Fix: ONE shared, explicit encoding function, imported by both
train_model.py (fit time) and recommendation_engine.py (inference time).
There is no way for these two to silently diverge again, because there is
only one place the encoding is defined.
"""

import pandas as pd

# Exactly the 6 soil types and 6 crops present in data/crop_yield.csv,
# and already accepted by the Flask API validator and the Flutter UI's
# dropdown options - kept as an explicit, ordered list (not inferred from
# whatever happens to appear in a given training run) so the one-hot
# columns produced here are always complete and in a fixed, predictable
# order, regardless of which soil types/crops happen to appear in a
# particular batch of input data.
SOIL_TYPES = ["Chalky", "Clay", "Loam", "Peaty", "Sandy", "Silt"]
CROPS = ["Barley", "Cotton", "Maize", "Rice", "Soybean", "Wheat"]

# The only 4 inputs the live API (and Flutter app) can actually supply.
# Region, Fertilizer_Used, Irrigation_Used, Weather_Condition, and
# Days_to_Harvest all exist in the raw CSV but are deliberately EXCLUDED
# from the model - training on columns the live system can never provide
# a real value for would just reintroduce the same class of train/
# inference mismatch this fix targets, one level removed.
NUMERIC_FEATURES = ["Rainfall_mm", "Temperature_Celsius"]


# Aliases already accepted elsewhere in this system (the Flask API's
# InputValidator and the fertilizer engine's soil_factors dict both
# accept 'loamy' as a synonym for 'loam', and 'silty' as a synonym for
# 'silt') but not by the raw category names in crop_yield.csv itself.
# Normalizing here means a request that's already valid everywhere else
# in the app doesn't get rejected by the ML encoder specifically -
# verified this was a real, live bug: a request with soil_type="loamy"
# (accepted by the API validator) failed here before this fix.
SOIL_ALIASES = {
    "Loamy": "Loam",
    "Silty": "Silt",
}


def _normalize_soil(soil_type: str) -> str:
    normalized = soil_type.strip().capitalize()
    return SOIL_ALIASES.get(normalized, normalized)


def encode_features(rainfall: float, temperature: float, soil_type: str, crop: str) -> pd.DataFrame:
    """
    Encodes a single (rainfall, temperature, soil_type, crop) input into
    the exact one-hot feature row the model expects, using the same
    fixed category lists as `build_training_features` below - single
    source of truth for both directions (fit and predict).

    Raises ValueError for a crop/soil type the model was never trained
    on (e.g. "sorghum" - accepted by the Flask API's InputValidator, but
    absent from data/crop_yield.csv, so the model has literally never
    seen it). Before this fix, an unrecognized category silently produced
    an all-zero one-hot row - implicitly and incorrectly treated as the
    reference category (Barley) - rather than failing. Callers (see
    predict_yield_ml in recommendation_engine.py) catch this and fall
    back to the formula predictor, which does have explicit, real support
    for every crop/soil the API accepts.
    """
    soil_normalized = _normalize_soil(soil_type)
    crop_normalized = crop.strip().capitalize()

    if soil_normalized not in SOIL_TYPES:
        raise ValueError(
            f"Soil type '{soil_type}' has no trained encoding (model was trained "
            f"on {SOIL_TYPES}); falling back to the formula predictor is correct here."
        )
    if crop_normalized not in CROPS:
        raise ValueError(
            f"Crop '{crop}' has no trained encoding (model was trained on "
            f"{CROPS}); falling back to the formula predictor is correct here."
        )

    row = {
        "Rainfall_mm": float(rainfall),
        "Temperature_Celsius": float(temperature),
    }
    # One-hot encode with drop_first semantics matching pd.get_dummies:
    # the first category in each list is the implicit reference (all
    # zeros); every other category gets its own 0/1 column.
    for soil in SOIL_TYPES[1:]:
        row[f"Soil_Type_{soil}"] = 1.0 if soil_normalized == soil else 0.0
    for crop_name in CROPS[1:]:
        row[f"Crop_{crop_name}"] = 1.0 if crop_normalized == crop_name else 0.0

    return pd.DataFrame([row])


def build_training_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Builds the (X, y) training matrix from the raw crop_yield.csv,
    applying the exact same encoding scheme `encode_features` uses at
    inference time. Categorical dtypes are fixed to the full known
    category lists (via pd.Categorical) before one-hot encoding, so the
    resulting columns are identical regardless of which specific
    soil/crop values happen to appear in a given training split - this
    is what guarantees `encode_features` can never produce a column the
    trained model doesn't recognize, or vice versa.
    """
    df = df.reset_index(drop=True)
    X = df[NUMERIC_FEATURES].copy()

    soil_dummies = pd.get_dummies(
        pd.Categorical(df["Soil_Type"], categories=SOIL_TYPES),
        prefix="Soil_Type",
        drop_first=True,
        dtype=float,
    )
    crop_dummies = pd.get_dummies(
        pd.Categorical(df["Crop"], categories=CROPS),
        prefix="Crop",
        drop_first=True,
        dtype=float,
    )

    X = pd.concat([X, soil_dummies, crop_dummies], axis=1)
    y = df["Yield_tons_per_hectare"]
    return X, y


def feature_columns() -> list[str]:
    """The full, fixed list of column names the model is trained/queried on, in order."""
    cols = list(NUMERIC_FEATURES)
    cols += [f"Soil_Type_{s}" for s in SOIL_TYPES[1:]]
    cols += [f"Crop_{c}" for c in CROPS[1:]]
    return cols
