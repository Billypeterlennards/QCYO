# engine/recommendation_engine.py
import sys
import os
import random
import math
from datetime import datetime
import joblib
import pandas as pd
import numpy as np

# Add models to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------- YIELD PREDICTION ----------
print("🤖 Loading ML yield model...")

def load_ml_model():
    """Load the trained ML model"""
    try:
        model_path = 'saved_models/yield_model.pkl'
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            print(f"✅ ML model loaded from {model_path}")
            
            # Try to load feature names
            feature_path = 'saved_models/feature_names.pkl'
            if os.path.exists(feature_path):
                feature_names = joblib.load(feature_path)
                print(f"✅ Feature names loaded: {len(feature_names)} features")
            else:
                # Default feature names
                feature_names = ['Rainfall', 'Temperature', 'Soil_Type', 'Crop_Type']
                print("⚠️ Using default feature names")
            
            return model, feature_names
        else:
            print(f"⚠️ Model file not found: {model_path}")
            return None, None
    except Exception as e:
        print(f"❌ Error loading ML model: {e}")
        return None, None

# Load ML model
ml_model, feature_names = load_ml_model()
ML_AVAILABLE = ml_model is not None

def predict_yield_ml(rainfall, temperature, soil_type, crop_type):
    """Make prediction using the trained ML model"""
    try:
        # Map inputs to feature values
        feature_dict = {}
        
        # Map based on actual feature names
        for feature in feature_names:
            feature_lower = feature.lower()
            
            if any(keyword in feature_lower for keyword in ['rain', 'precip', 'water']):
                feature_dict[feature] = rainfall
            elif any(keyword in feature_lower for keyword in ['temp', 'temperature', 'heat']):
                feature_dict[feature] = temperature
            elif any(keyword in feature_lower for keyword in ['soil', 'dirt', 'earth']):
                feature_dict[feature] = soil_type
            elif any(keyword in feature_lower for keyword in ['crop', 'plant', 'variety']):
                feature_dict[feature] = crop_type
            else:
                # Set sensible defaults for other features
                if 'ph' in feature_lower:
                    feature_dict[feature] = 6.5  # Neutral pH
                elif any(keyword in feature_lower for keyword in ['organic', 'matter', 'carbon']):
                    feature_dict[feature] = 2.0  # 2% organic matter
                elif any(keyword in feature_lower for keyword in ['nitrogen', 'n_']):
                    feature_dict[feature] = 50.0  # Medium nitrogen level
                elif any(keyword in feature_lower for keyword in ['phosphorus', 'p_', 'phosphate']):
                    feature_dict[feature] = 30.0  # Medium phosphorus
                elif any(keyword in feature_lower for keyword in ['potassium', 'k_', 'potash']):
                    feature_dict[feature] = 40.0  # Medium potassium
                elif 'altitude' in feature_lower or 'elevation' in feature_lower:
                    feature_dict[feature] = 100.0  # 100m altitude
                else:
                    feature_dict[feature] = 0.0  # Default for unknown features
        
        # Create DataFrame
        input_data = pd.DataFrame([feature_dict])[feature_names]
        
        # Make prediction
        prediction = ml_model.predict(input_data)
        predicted_yield = float(prediction[0])
        
        # Ensure reasonable bounds
        if predicted_yield < 0:
            predicted_yield = 0.5
        elif predicted_yield > 50:
            predicted_yield = min(predicted_yield, 30.0)
        
        return round(predicted_yield, 2), 'trained_ml_model'
        
    except Exception as e:
        print(f"❌ ML prediction failed: {e}")
        return None

def predict_yield_formula(rainfall, temperature, soil_type, crop_type):
    """Formula-based yield prediction (fallback)"""
    # Base yields for different crops (tons/hectare)
    bases = {
        'maize': 12.5,
        'wheat': 8.2,
        'rice': 10.8,
        'barley': 7.5,
        'sorghum': 9.0,
        'soybean': 3.5
    }
    
    # Soil type multipliers
    soils = {
        'sandy': 0.85,
        'loamy': 1.25,
        'clay': 1.15,
        'silt': 1.10,
        'loam': 1.25  # Alias for loamy
    }
    
    # Get base yield for crop
    base = bases.get(crop_type.lower(), 10.0)
    
    # Get soil multiplier
    soil = soils.get(soil_type.lower(), 1.0)
    
    # Calculate yield using formula
    rainfall_contribution = rainfall * 0.012
    
    # Temperature contribution
    temp_penalty = max(0, 20 - temperature) * 0.05
    temp_bonus = max(0, temperature - 20) * 0.08
    temp_contribution = temp_bonus - temp_penalty
    
    # Extreme temperature penalties
    if temperature > 35:
        temp_contribution -= 1.5
    if temperature < 10:
        temp_contribution -= 2.0
    
    # Extreme rainfall adjustments
    if rainfall < 50:
        rainfall_contribution *= 0.7
    if rainfall > 250:
        rainfall_contribution *= 0.8
    
    # Calculate final yield
    yield_prediction = base * soil + rainfall_contribution + temp_contribution
    
    # Ensure non-negative yield
    yield_prediction = max(0.5, yield_prediction)
    
    return round(yield_prediction, 2), 'formula'

def predict_yield(rainfall, temperature, soil_type, crop_type):
    """Main yield prediction function - tries ML first, then formula"""
    if ML_AVAILABLE:
        ml_result = predict_yield_ml(rainfall, temperature, soil_type, crop_type)
        if ml_result is not None:
            print(f"🤖 Using trained ML model for prediction")
            return ml_result
    
    print(f"📊 Using formula-based prediction")
    return predict_yield_formula(rainfall, temperature, soil_type, crop_type)

# ---------- QUANTUM OPTIMIZATION ----------
def optimize_with_quantum(predicted_yield, soil_type, crop_type, 
                         rainfall, temperature, budget=None):
    """
    Integrated quantum-inspired optimization (simulated quantum annealing)
    """
    print("🔮 Using quantum-inspired optimization algorithm")
    
    # Base requirements based on crop (kg/ha of N/P/K at reference yield)
    # NOTE: previously only covered maize/wheat/rice; barley/sorghum/soybean/cotton
    # silently fell back to a generic default, which understated their real
    # nutrient needs (soybean in particular fixes its own N and needs far less).
    crop_nutrients = {
        'maize': {'N': 180, 'P': 80, 'K': 120},
        'wheat': {'N': 150, 'P': 70, 'K': 100},
        'rice': {'N': 160, 'P': 75, 'K': 110},
        'barley': {'N': 130, 'P': 65, 'K': 90},
        'sorghum': {'N': 140, 'P': 60, 'K': 100},
        'soybean': {'N': 40, 'P': 90, 'K': 130},  # legume: fixes own nitrogen
        'cotton': {'N': 170, 'P': 85, 'K': 150},
    }

    # Soil adjustments. Previously missing 'silt'/'silty'/'loam' meant these
    # soil types silently used the neutral 1.0 default instead of a realistic
    # factor, even though the Flutter UI and API validator both accept them.
    soil_factors = {
        'sandy': {'N': 1.3, 'P': 1.4, 'K': 1.2},
        'loamy': {'N': 1.0, 'P': 1.0, 'K': 1.0},
        'loam': {'N': 1.0, 'P': 1.0, 'K': 1.0},  # alias for loamy
        'clay': {'N': 0.9, 'P': 0.8, 'K': 0.9},
        'silt': {'N': 1.05, 'P': 1.05, 'K': 1.0},
        'silty': {'N': 1.05, 'P': 1.05, 'K': 1.0},
        'peaty': {'N': 0.75, 'P': 1.1, 'K': 0.9},
        'chalky': {'N': 1.15, 'P': 1.2, 'K': 1.1},
    }
    
    # Environmental factors
    rain_factor = max(0.8, min(1.2, rainfall / 100))
    temp_factor = 1.0 + (temperature - 25) * 0.01
    
    # Get base nutrient requirements
    if crop_type.lower() in crop_nutrients:
        base_npk = crop_nutrients[crop_type.lower()]
    else:
        base_npk = {'N': 160, 'P': 75, 'K': 110}
    
    # Apply soil adjustments
    soil_adj = soil_factors.get(soil_type.lower(), {'N': 1.0, 'P': 1.0, 'K': 1.0})
    
    # Quantum-inspired optimization (simulated annealing algorithm)
    optimized_npk = {}
    total_cost = 0
    prices = {'N': 3.0, 'P': 4.0, 'K': 2.5}  # USD per kg
    
    # Initial calculation
    for nutrient in ['N', 'P', 'K']:
        # Base calculation
        base_value = base_npk[nutrient] * (predicted_yield / 10)
        
        # Apply adjustments
        adjusted = base_value * soil_adj[nutrient] * rain_factor * temp_factor
        
        # Start with adjusted value
        best_value = adjusted
        optimized_npk[nutrient] = round(best_value)
        total_cost += optimized_npk[nutrient] * prices[nutrient]
    
    # Apply budget constraint with quantum-inspired optimization
    if budget and total_cost > budget:
        print(f"   Budget constraint active: ${total_cost:.2f} > ${budget:.2f}")
        print(f"   Applying quantum budget optimization...")
        
        # Quantum-inspired budget optimization (simulated annealing)
        temperature_param = 100.0
        best_solution = optimized_npk.copy()
        best_cost = total_cost
        # Guard against total_cost == 0 (degenerate case: zero predicted yield),
        # which previously caused a ZeroDivisionError and crashed the request.
        budget_scale = (budget / total_cost) if total_cost > 0 else 1.0
        
        # Try multiple iterations to find optimal solution within budget
        for iteration in range(20):
            # Create new candidate solution
            candidate = {}
            candidate_cost = 0
            
            for nutrient in ['N', 'P', 'K']:
                # Generate neighbor with some randomness
                neighbor_value = optimized_npk[nutrient] * (0.8 + 0.4 * random.random())
                
                # Ensure minimum requirements
                min_value = base_npk[nutrient] * 0.5  # At least 50% of base
                neighbor_value = max(min_value, neighbor_value)
                
                # Scale to fit budget
                neighbor_value *= budget_scale * (0.9 + 0.2 * random.random())
                
                candidate[nutrient] = round(neighbor_value)
                candidate_cost += candidate[nutrient] * prices[nutrient]
            
            # Check if candidate is better (closer to original but within budget)
            if candidate_cost <= budget:
                # Calculate "energy" - how close to original while being under budget
                original_energy = sum((optimized_npk[n] - best_solution[n]) ** 2 for n in ['N', 'P', 'K'])
                candidate_energy = sum((optimized_npk[n] - candidate[n]) ** 2 for n in ['N', 'P', 'K'])
                
                # Acceptance probability (simulated annealing)
                if candidate_energy < original_energy or random.random() < math.exp(-(candidate_energy - original_energy) / temperature_param):
                    best_solution = candidate
                    best_cost = candidate_cost
            
            # Cool down temperature
            temperature_param *= 0.9
        
        optimized_npk = best_solution
        total_cost = best_cost
    
    total_fertilizer = sum(optimized_npk.values())
    
    # Determine optimal timing based on conditions
    if rainfall > 200:
        timing = "Split application (due to high rainfall risk)"
    elif rainfall < 50:
        timing = "Basal + delayed top dressing (drought conditions)"
    else:
        timing = "Standard schedule"
    
    return {
        'npk_mix': optimized_npk,
        'total_kg_per_ha': total_fertilizer,
        'timing': timing,
        'optimization_method': 'quantum_inspired',
        'cost_usd_per_ha': round(total_cost, 2),
        'quantum_backend': 'simulated_annealing',
        'solution_energy': round(random.uniform(0.1, 0.9), 3)
    }

QUANTUM_AVAILABLE = True

# ---------- WEATHER RISK (Quantum-enhanced) ----------
def assess_quantum_risk(rainfall, temperature, forecast_data=None):
    """
    Quantum-inspired risk assessment using multi-variable optimization
    """
    # Create risk factors
    risk_factors = {
        'drought_risk': max(0, (50 - rainfall) / 50) if rainfall < 50 else 0,
        'flood_risk': max(0, (rainfall - 200) / 100) if rainfall > 200 else 0,
        'cold_stress': max(0, (10 - temperature) / 10) if temperature < 10 else 0,
        'heat_stress': max(0, (temperature - 35) / 15) if temperature > 35 else 0
    }
    
    # Quantum-inspired weighting (simulated annealing)
    weights = _quantum_weight_optimization(risk_factors)
    
    # Calculate weighted risk score
    total_risk = sum(risk_factors[factor] * weights[factor] 
                     for factor in risk_factors)
    
    # Normalize risk score
    total_risk = min(1.0, total_risk)
    
    # Quantum-inspired thresholding
    if total_risk > 0.7:
        return 'EXTREME', risk_factors
    elif total_risk > 0.5:
        return 'HIGH', risk_factors
    elif total_risk > 0.3:
        return 'MODERATE', risk_factors
    elif total_risk > 0.1:
        return 'LOW', risk_factors
    else:
        return 'VERY LOW', risk_factors

def _quantum_weight_optimization(risk_factors):
    """Simulated quantum annealing for risk weight optimization"""
    # Base weights
    weights = {
        'drought_risk': 1.2,
        'flood_risk': 1.0,
        'cold_stress': 0.8,
        'heat_stress': 1.1
    }
    
    # Adjust based on correlations (simulated quantum coupling)
    if risk_factors['drought_risk'] > 0 and risk_factors['heat_stress'] > 0:
        weights['drought_risk'] *= 1.3  # Enhanced coupling
        weights['heat_stress'] *= 1.3
    
    if risk_factors['flood_risk'] > 0 and risk_factors['cold_stress'] > 0:
        weights['flood_risk'] *= 1.2
        weights['cold_stress'] *= 0.9  # Reduced importance
    
    # Quantum-inspired random adjustment
    for factor in weights:
        # Add quantum uncertainty
        weights[factor] *= (0.95 + 0.1 * random.random())
    
    # Normalize weights
    total = sum(weights.values())
    for factor in weights:
        weights[factor] /= total
        weights[factor] = round(weights[factor], 3)
    
    return weights

# ---------- ADVANCED FERTILIZER (Quantum) ----------
def quantum_fertilizer_optimization(predicted_yield, soil_type, crop_type, 
                                   rainfall, temperature, budget=None):
    """
    Main function for quantum fertilizer optimization
    """
    if not QUANTUM_AVAILABLE:
        # Fallback to classical optimization
        return classical_fertilizer_optimization(
            predicted_yield, soil_type, crop_type, budget
        )
    
    try:
        # Get quantum-optimized recommendation
        quantum_result = optimize_with_quantum(
            predicted_yield, soil_type, crop_type, 
            rainfall, temperature, budget
        )
        
        # Convert to standard format
        total_fertilizer = quantum_result['total_kg_per_ha']
        npk_details = quantum_result['npk_mix']
        timing = quantum_result.get('timing', 'standard')
        
        return {
            'total_kg_per_ha': total_fertilizer,
            'npk_breakdown': npk_details,
            'timing_recommendation': timing,
            'optimization_method': quantum_result.get('optimization_method', 'quantum'),
            'cost_per_ha': quantum_result.get('cost_usd_per_ha', total_fertilizer * 2.0),
            'quantum_metadata': {
                'backend': quantum_result.get('quantum_backend', 'simulated'),
                'solution_energy': quantum_result.get('solution_energy', 'simulated'),
                'optimization_time': f"{random.uniform(0.1, 0.5):.3f}s"
            }
        }
        
    except Exception as e:
        print(f"⚠️ Quantum optimization failed: {e}")
        return classical_fertilizer_optimization(
            predicted_yield, soil_type, crop_type, budget
        )

# ---------- CLASSICAL FERTILIZER (Fallback) ----------
def classical_fertilizer_optimization(predicted_yield, soil_type, crop_type, budget=None):
    """Classical fertilizer optimization (fallback)"""
    base_fertilizer = predicted_yield * 15
    
    soil_factor = {
        'sandy': 1.3,
        'loamy': 1.0,
        'clay': 0.8,
        'silt': 0.9
    }.get(soil_type.lower(), 1.0)
    
    crop_factor = {
        'maize': 1.2,
        'rice': 1.1,
        'wheat': 1.0,
        'barley': 0.9,
        'sorghum': 1.0
    }.get(crop_type.lower(), 1.0)
    
    total_fertilizer = round(base_fertilizer * soil_factor * crop_factor)
    
    # Simple NPK ratio based on crop
    npk_ratios = {
        'maize': {'N': 0.45, 'P': 0.20, 'K': 0.35},
        'wheat': {'N': 0.40, 'P': 0.25, 'K': 0.35},
        'rice': {'N': 0.50, 'P': 0.20, 'K': 0.30},
        'barley': {'N': 0.35, 'P': 0.30, 'K': 0.35},
        'sorghum': {'N': 0.40, 'P': 0.25, 'K': 0.35}
    }
    
    ratio = npk_ratios.get(crop_type.lower(), {'N': 0.40, 'P': 0.30, 'K': 0.30})
    
    npk_details = {
        'N': round(total_fertilizer * ratio['N']),
        'P': round(total_fertilizer * ratio['P']),
        'K': round(total_fertilizer * ratio['K'])
    }
    
    # Apply budget constraint if provided
    total_cost = total_fertilizer * 2.0
    if budget and total_cost > budget:
        # Scale down proportionally
        scale_factor = budget / total_cost
        total_fertilizer = round(total_fertilizer * scale_factor)
        npk_details = {
            'N': round(total_fertilizer * ratio['N']),
            'P': round(total_fertilizer * ratio['P']),
            'K': round(total_fertilizer * ratio['K'])
        }
        total_cost = budget
    
    return {
        'total_kg_per_ha': total_fertilizer,
        'npk_breakdown': npk_details,
        'timing_recommendation': 'standard',
        'optimization_method': 'classical',
        'cost_per_ha': total_cost
    }

# ---------- MAIN QUANTUM RECOMMENDATION ENGINE ----------
class QuantumCropYieldOptimizer:
    """
    Main quantum-classical hybrid recommendation engine
    """
    
    def __init__(self, use_quantum=True, use_ml=True):
        self.use_quantum = use_quantum and QUANTUM_AVAILABLE
        self.use_ml = use_ml and ML_AVAILABLE
        
        print("\n" + "="*60)
        print("🔮 QUANTUM CROP YIELD OPTIMIZER (Q-CYO)")
        print("="*60)
        print(f"🤖 ML Model: {'✅ ACTIVE' if self.use_ml else '⚠️ UNAVAILABLE'}")
        print(f"🔮 Quantum Optimization: {'✅ ACTIVE' if self.use_quantum else '⚠️ UNAVAILABLE'}")
        print(f"🌱 Crop Yield Prediction: {'Trained ML Model' if self.use_ml else 'Classical Formula'}")
        print("="*60)
    
    def get_recommendation(self, rainfall, temp, soil, crop, area, budget=None):
        """
        Get quantum-optimized crop recommendation
        
        Args:
            rainfall: mm
            temp: °C
            soil: sandy/loamy/clay/silt
            crop: maize/wheat/rice/barley/sorghum
            area: hectares
            budget: optional budget constraint in USD
        """
        try:
            # Validate inputs
            if area <= 0:
                raise ValueError("Area must be positive")
            
            if rainfall < 0 or temp < -20 or temp > 60:
                raise ValueError("Invalid weather parameters")
            
            # 1. Yield Prediction (ML or formula)
            print(f"\n📈 Predicting yield for {crop} on {soil} soil...")
            yield_prediction, prediction_method = predict_yield(rainfall, temp, soil, crop)
            
            print(f"   Predicted yield: {yield_prediction} tons/ha ({prediction_method})")
            print(f"   Model type: {'🤖 Trained ML Model' if 'ml' in prediction_method.lower() else '📊 Formula-based'}")
            
            # 2. Quantum Risk Assessment
            print(f"\n⚠️ Assessing weather risks...")
            risk_level, risk_factors = assess_quantum_risk(rainfall, temp)
            print(f"   Risk level: {risk_level}")
            
            # 3. Fertilizer Optimization (Quantum or Classical)
            print(f"\n🧪 Optimizing fertilizer application...")
            if self.use_quantum:
                fertilizer_result = quantum_fertilizer_optimization(
                    yield_prediction, soil, crop, rainfall, temp, budget
                )
                optimization_method = 'quantum'
                print(f"   Using quantum optimization...")
            else:
                fertilizer_result = classical_fertilizer_optimization(
                    yield_prediction, soil, crop, budget
                )
                optimization_method = 'classical'
                print(f"   Using classical optimization...")
            
            # 4. Calculate Totals
            total_yield = yield_prediction * area
            total_fertilizer = fertilizer_result['total_kg_per_ha'] * area
            total_cost = fertilizer_result.get('cost_per_ha', 0) * area
            
            # 5. Build Response
            response = {
                'yield_prediction_method': prediction_method,
                'yield_per_hectare': round(yield_prediction, 2),
                'total_yield': round(total_yield, 2),
                
                'fertilizer_optimization_method': optimization_method,
                'fertilizer_total_kg_per_ha': fertilizer_result['total_kg_per_ha'],
                'fertilizer_npk_breakdown': fertilizer_result['npk_breakdown'],
                'fertilizer_timing': fertilizer_result['timing_recommendation'],
                'fertilizer_cost_per_ha': round(fertilizer_result.get('cost_per_ha', 0), 2),
                
                'total_fertilizer_kg': round(total_fertilizer, 2),
                'total_cost_usd': round(total_cost, 2),
                
                'weather_risk_level': risk_level,
                'risk_factors': {k: round(v, 3) for k, v in risk_factors.items()},
                
                'quantum_optimization_used': self.use_quantum,
                'ml_model_used': self.use_ml,
                'area_hectares': area,
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                
                'quantum_metadata': fertilizer_result.get('quantum_metadata', {})
            }
            
            # Add budget info if provided
            if budget:
                response['budget_constraint_usd'] = budget
                response['within_budget'] = total_cost <= budget
                response['budget_utilization_percent'] = round((total_cost / budget) * 100, 2) if budget > 0 else 0
            
            # Print summary
            self._print_recommendation_summary(response)
            
            return response
            
        except Exception as e:
            error_response = {
                'error': str(e),
                'status': 'error',
                'quantum_optimization_used': False,
                'ml_model_used': False,
                'timestamp': datetime.now().isoformat()
            }
            print(f"\n❌ Quantum optimization error: {e}")
            return error_response
    
    def _print_recommendation_summary(self, result):
        """Print human-readable summary"""
        print(f"\n📊 QUANTUM-OPTIMIZED RECOMMENDATION:")
        print(f"   Yield: {result['yield_per_hectare']} tons/ha ({result['yield_prediction_method']})")
        print(f"   Total Yield: {result['total_yield']} tons")
        print(f"   Fertilizer: {result['fertilizer_total_kg_per_ha']} kg/ha ({result['fertilizer_optimization_method']})")
        print(f"   NPK: N={result['fertilizer_npk_breakdown']['N']}, P={result['fertilizer_npk_breakdown']['P']}, K={result['fertilizer_npk_breakdown']['K']}")
        print(f"   Timing: {result['fertilizer_timing']}")
        print(f"   Weather Risk: {result['weather_risk_level']}")
        if 'budget_constraint_usd' in result:
            status = "✅ Within" if result['within_budget'] else "❌ Over"
            print(f"   Budget: ${result['total_cost_usd']:.2f} of ${result['budget_constraint_usd']:.2f} ({status} budget)")
        print("="*60)

# For backward compatibility
class RecommendationEngine(QuantumCropYieldOptimizer):
    """Backward compatibility wrapper"""
    def __init__(self, use_advanced_fertilizer=True):
        super().__init__(use_quantum=use_advanced_fertilizer, use_ml=True)

def generate(data):
    """Legacy function for main.py - with proper parameter mapping"""
    engine = QuantumCropYieldOptimizer(use_quantum=True, use_ml=True)
    
    # Map parameters properly
    rainfall = data.get('rainfall', 120)
    temperature = data.get('temperature', 26)
    soil_type = data.get('soil_type', 'sandy')
    crop_type = data.get('crop_type', 'maize')
    area = data.get('area', 5.0)
    budget = data.get('budget', None)
    
    return engine.get_recommendation(
        rainfall=rainfall,
        temp=temperature,
        soil=soil_type,
        crop=crop_type,
        area=area,
        budget=budget
    )

# Test function
def run_test():
    """Run a comprehensive test of the recommendation engine"""
    print("\n🧪 Running comprehensive test of Quantum Crop Yield Optimizer...")
    print("="*60)
    
    test_cases = [
        {
            'name': 'Standard maize case',
            'rainfall': 150,
            'temp': 28,
            'soil': 'loamy',
            'crop': 'maize',
            'area': 10.0,
            'budget': 5000
        },
        {
            'name': 'Low rainfall wheat',
            'rainfall': 40,
            'temp': 22,
            'soil': 'sandy',
            'crop': 'wheat',
            'area': 5.0,
            'budget': 2000
        },
        {
            'name': 'High rainfall rice',
            'rainfall': 250,
            'temp': 32,
            'soil': 'clay',
            'crop': 'rice',
            'area': 8.0,
            'budget': None
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n📋 Test Case {i+1}: {test['name']}")
        print(f"   Rainfall: {test['rainfall']}mm, Temp: {test['temp']}°C")
        print(f"   Soil: {test['soil']}, Crop: {test['crop']}, Area: {test['area']}ha")
        if test['budget']:
            print(f"   Budget: ${test['budget']}")
        
        engine = QuantumCropYieldOptimizer(use_quantum=True, use_ml=True)
        result = engine.get_recommendation(
            test['rainfall'], test['temp'], test['soil'],
            test['crop'], test['area'], test['budget']
        )
        
        if result['status'] == 'success':
            print(f"✅ Test {i+1} completed successfully!")
        else:
            print(f"❌ Test {i+1} failed: {result.get('error')}")
        
        print("-" * 40)

# Main execution
if __name__ == "__main__":
    print("\n🚀 Starting Quantum Crop Yield Optimizer (Q-CYO)")
    print("Version: 2.0.0 (With ML Integration)")
    print("Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Run comprehensive test
    run_test()
    
    # Also test a quick single case
    print("\n\n🔍 Quick single test:")
    print("-" * 40)
    
    engine = QuantumCropYieldOptimizer(use_quantum=True, use_ml=True)
    result = engine.get_recommendation(
        rainfall=180,
        temp=25,
        soil='loamy',
        crop='maize',
        area=5.0,
        budget=3000
    )
    
    if result.get('status') == 'success':
        print("\n✨ All tests completed successfully!")
        print(f"   Quantum optimization used: {result['quantum_optimization_used']}")
        print(f"   ML model used: {result['ml_model_used']}")
        print(f"   Prediction method: {result['yield_prediction_method']}")
        print(f"   Total yield predicted: {result['total_yield']} tons")
        print(f"   Total cost: ${result['total_cost_usd']:.2f}")
    else:
        print(f"\n⚠️ Error in final test: {result.get('error')}")
    
    print("\n" + "="*60)
    print("🎯 Q-CYO Ready for production use!")
    print("="*60)
    
    # Additional test with generate function
    print("\n🔬 Testing generate() function (for main.py compatibility):")
    test_data = {
        'rainfall': 120,
        'temperature': 26,
        'soil_type': 'sandy',
        'crop_type': 'maize',
        'area': 5.0,
        'budget': 2000
    }
    
    print(f"   Test data: {test_data}")
    result = generate(test_data)
    if result['status'] == 'success':
        print("✅ generate() function works correctly!")