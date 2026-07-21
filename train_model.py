"""
Trains the crop-yield RandomForestRegressor on the real project dataset
(data/crop_yield.csv), using the shared encoding logic in
utils/preprocess.py - the exact same encoding recommendation_engine.py
uses at inference time, so there is no possibility of the two silently
diverging (see utils/preprocess.py's module docstring for the real,
verified bug this fixes).

Run: python train_model.py
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

from utils.preprocess import build_training_features, feature_columns

DATA_PATH = "data/crop_yield.csv"
OUTPUT_DIR = "saved_models"

# The real dataset has 1,000,000 rows. Training a RandomForest on the
# full set is unnecessary for this model's accuracy needs and slow to
# iterate on; a fixed, seeded sample keeps training fast while still
# being a real fit against real data (not synthetic/fabricated), and the
# seed makes the sample itself reproducible.
SAMPLE_SIZE = 100_000
RANDOM_SEED = 42


def main():
    print(f"Loading {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    print(f"  Full dataset: {len(df):,} rows")

    if len(df) > SAMPLE_SIZE:
        df = df.sample(n=SAMPLE_SIZE, random_state=RANDOM_SEED)
        print(f"  Sampled down to {len(df):,} rows (seed={RANDOM_SEED}, reproducible)")

    X, y = build_training_features(df)
    print(f"  Features ({X.shape[1]}): {list(X.columns)}")

    expected_columns = feature_columns()
    assert list(X.columns) == expected_columns, (
        "Training features do not match utils.preprocess.feature_columns() - "
        "this must never happen, since both are derived from the same source."
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )

    print(f"\nTraining RandomForestRegressor on {len(X_train):,} samples...")
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"\nTest set performance ({len(X_test):,} samples):")
    print(f"  MAE: {mae:.3f} tons/hectare")
    print(f"  R^2: {r2:.3f}")

    print("\nFeature importances:")
    for name, importance in sorted(
        zip(X.columns, model.feature_importances_), key=lambda t: -t[1]
    ):
        print(f"  {name}: {importance:.3f}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    model_path = os.path.join(OUTPUT_DIR, "yield_model.pkl")
    joblib.dump(model, model_path)

    feature_path = os.path.join(OUTPUT_DIR, "feature_names.pkl")
    joblib.dump(expected_columns, feature_path)

    print(f"\nSaved model to {model_path}")
    print(f"Saved feature names to {feature_path}")

    # Sanity check: reload from disk and confirm a real prediction runs
    # end-to-end without error, using the actual saved artifacts - not
    # just the in-memory objects from this same process.
    from utils.preprocess import encode_features

    reloaded_model = joblib.load(model_path)
    reloaded_features = joblib.load(feature_path)
    sample_input = encode_features(150, 26, "Loam", "Maize")[reloaded_features]
    sample_prediction = reloaded_model.predict(sample_input)
    print(
        f"\nSanity check - reloaded model prediction for "
        f"(150mm rain, 26C, Loam soil, Maize): {sample_prediction[0]:.2f} tons/ha"
    )


if __name__ == "__main__":
    main()
