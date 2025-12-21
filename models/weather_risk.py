def assess_risk(rainfall, temperature):
    if rainfall < 80 and temperature > 30:
        return "HIGH"
    elif rainfall < 100:
        return "MEDIUM"
    else:
        return "LOW"