import pandas as pd

def load_international_data(path):
    df = pd.read_csv(path)
    df = df.dropna()

    # Rename columns
    df = df.rename(columns={
        "hg/ha_yield": "yield_hg",
        "average_rain_fall_mm_per_year": "rainfall",
        "avg_temp": "temperature"
    })

    # Convert hectograms/ha → tons/ha
    df["yield"] = df["yield_hg"] / 10000

    X = df[["rainfall", "temperature"]]
    y = df["yield"]

    return X, y
