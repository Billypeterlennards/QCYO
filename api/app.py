
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sys
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.recommendation_engine import RecommendationEngine

app = Flask(__name__)
CORS(app)

# BEFORE: no rate limiting existed anywhere in the API. Any client could
# call /recommend/batch (up to 50 items processed server-side per call)
# in an unbounded loop with zero throttling - a trivial DoS vector, and
# /clear-cache could be spammed by anyone to wipe the shared cache for
# every user. Defaults are generous for legitimate use but bound the worst
# case; tune per your actual traffic patterns and consider a shared
# backend (e.g. Redis) instead of in-memory storage once you run more than
# one worker process.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour", "30 per minute"],
    storage_uri="memory://",
)

# In-memory cache for performance
recommendation_cache = {}
MAX_CACHE_SIZE = 100

# Request counter for metrics
request_counter = {
    'total': 0,
    'advanced': 0,
    'simple': 0,
    'errors': 0
}

# Validator for input parameters
class InputValidator:
    @staticmethod
    def validate_rainfall(value):
        try:
            val = float(value)
            if val < 0 or val > 1000:
                return False, 'Rainfall must be between 0 and 1000 mm'
            return True, val
        except:
            return False, 'Rainfall must be a number'
    
    @staticmethod
    def validate_temperature(value):
        try:
            val = float(value)
            if val < -20 or val > 50:
                return False, 'Temperature must be between -20°C and 50°C'
            return True, val
        except:
            return False, 'Temperature must be a number'
    
    @staticmethod
    def validate_soil_type(value):
        valid_soils = ['sandy', 'loam', 'clay', 'silty', 'peaty', 'chalky']
        if value.lower() in valid_soils:
            return True, value.lower()
        return False, f'Soil type must be one of: {", ".join(valid_soils)}'
    
    @staticmethod
    def validate_crop_type(value):
        valid_crops = ['maize', 'wheat', 'rice', 'barley', 'soybean', 'sorghum']
        if value.lower() in valid_crops:
            return True, value.lower()
        return False, f'Crop type must be one of: {", ".join(valid_crops)}'
    
    @staticmethod
    def validate_area(value):
        try:
            val = float(value)
            if val <= 0 or val > 10000:
                return False, 'Area must be between 0.1 and 10,000 hectares'
            return True, val
        except:
            return False, 'Area must be a number'

    @staticmethod
    def validate_budget(value):
        try:
            val = float(value)
            if val <= 0:
                return False, 'Budget must be a positive number'
            return True, val
        except:
            return False, 'Budget must be a number'


def extract_optional_budget(data):
    """
    AUDIT FIX (critical, systemic gap): budget was accepted by NONE of
    /recommend, /recommend/advanced, or /recommend/simple - not because
    of a validation bug, but because the field was never extracted from
    the request or passed to engine.get_recommendation() at all, on any
    endpoint. The engine itself fully implements budget-constrained
    quantum optimization (see engine/recommendation_engine.py's
    quantum_fertilizer_optimization), and the Flutter client already
    sends a `budget` field from its "Advanced Options" form section - but
    every request silently had it dropped on the floor server-side.
    Verified live: submitting budget=100 (guaranteed to be exceeded) and
    budget=2000 (guaranteed to be respected) both produced a response
    with no budget_constraint_usd/within_budget/budget_utilization_percent
    fields whatsoever, for either case.

    This is the single, shared extraction point every endpoint below now
    calls, instead of four independent (and, until now, entirely missing)
    implementations - `budget` is optional, so a missing field is not an
    error, unlike the required fields validated by validate_input().
    """
    if 'budget' not in data or data['budget'] is None:
        return True, None, None
    is_valid, result = InputValidator.validate_budget(data['budget'])
    if not is_valid:
        return False, None, f'budget: {result}'
    return True, result, None

def validate_input(data, required_fields):
    errors = []
    validated = {}
    
    for field, validator in required_fields.items():
        if field not in data:
            errors.append(f'Missing field: {field}')
            continue
            
        is_valid, result = validator(data[field])
        if is_valid:
            validated[field] = result
        else:
            errors.append(f'{field}: {result}')
    
    return len(errors) == 0, validated, errors

def get_cache_key(params, budget=None):
    return f'{params.get("rainfall")}_{params.get("temperature")}_{params.get("soil_type")}_{params.get("crop_type")}_{params.get("area")}_{budget}'

# BEFORE: /recommend/advanced, /recommend/simple, and /recommend/batch each
# did their own raw `float(data.get(...))` extraction with ZERO range or
# whitelist validation - meaning rainfall=999999999, a garbage soil_type
# string, or a negative area could reach the recommendation engine directly,
# completely bypassing the InputValidator that /recommend uses. Any endpoint
# that accepts user input now goes through this same shared validator.
STANDARD_FIELDS = {
    'rainfall': InputValidator.validate_rainfall,
    'temperature': InputValidator.validate_temperature,
    'soil_type': InputValidator.validate_soil_type,
    'crop_type': InputValidator.validate_crop_type,
    'area': InputValidator.validate_area,
}

def validate_recommendation_input(data, defaults=None):
    """Validate the 5 standard recommendation fields, applying defaults for
    any that are missing (used by endpoints where fields are optional),
    then running every value - including defaults - through the same
    range/whitelist checks as /recommend.
    """
    defaults = defaults or {}
    merged = {**defaults, **(data or {})}
    return validate_input(merged, STANDARD_FIELDS)

def cleanup_cache():
    global recommendation_cache
    if len(recommendation_cache) > MAX_CACHE_SIZE:
        keys_to_remove = list(recommendation_cache.keys())[:MAX_CACHE_SIZE // 2]
        for key in keys_to_remove:
            del recommendation_cache[key]
        logger.info(f'Cleaned up {len(keys_to_remove)} cache entries')

@app.route('/recommend', methods=['POST'])
def recommend():
    request_counter['total'] += 1
    
    try:
        data = request.get_json()
        if not data:
            request_counter['errors'] += 1
            return jsonify({
                'error': 'No JSON data provided',
                'status': 'error'
            }), 400
        
        required_fields = {
            'rainfall': InputValidator.validate_rainfall,
            'temperature': InputValidator.validate_temperature,
            'soil_type': InputValidator.validate_soil_type,
            'crop_type': InputValidator.validate_crop_type,
            'area': InputValidator.validate_area
        }
        
        is_valid, validated_data, errors = validate_input(data, required_fields)
        if not is_valid:
            request_counter['errors'] += 1
            return jsonify({
                'error': 'Validation failed',
                'details': errors,
                'status': 'error'
            }), 400

        budget_valid, budget, budget_error = extract_optional_budget(data)
        if not budget_valid:
            request_counter['errors'] += 1
            return jsonify({
                'error': 'Validation failed',
                'details': [budget_error],
                'status': 'error'
            }), 400

        cache_key = get_cache_key(validated_data, budget)
        if cache_key in recommendation_cache:
            logger.info(f'Cache hit for key: {cache_key}')
            result = recommendation_cache[cache_key]
            result['cached'] = True
            result['timestamp'] = datetime.now().isoformat()
            return jsonify(result)

        engine = RecommendationEngine(use_advanced_fertilizer=True)
        result = engine.get_recommendation(
            validated_data['rainfall'],
            validated_data['temperature'],
            validated_data['soil_type'],
            validated_data['crop_type'],
            validated_data['area'],
            budget=budget
        )
        
        result['timestamp'] = datetime.now().isoformat()
        result['request_id'] = f'req_{request_counter["total"]}'
        result['cached'] = False
        
        recommendation_cache[cache_key] = result
        cleanup_cache()
        
        logger.info(f'Recommendation generated for {validated_data["crop_type"]} on {validated_data["area"]}ha')
        
        return jsonify(result)
        
    except Exception as e:
        request_counter['errors'] += 1
        logger.error(f'Error in /recommend: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500

@app.route('/recommend/advanced', methods=['POST'])
def recommend_advanced():
    request_counter['total'] += 1
    request_counter['advanced'] += 1

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided', 'status': 'error'}), 400

        is_valid, validated_data, errors = validate_recommendation_input(
            data,
            defaults={'rainfall': 120, 'temperature': 26, 'soil_type': 'sandy',
                      'crop_type': 'maize', 'area': 5},
        )
        if not is_valid:
            request_counter['errors'] += 1
            return jsonify({'error': 'Validation failed', 'details': errors, 'status': 'error'}), 400

        budget_valid, budget, budget_error = extract_optional_budget(data)
        if not budget_valid:
            request_counter['errors'] += 1
            return jsonify({'error': 'Validation failed', 'details': [budget_error], 'status': 'error'}), 400

        engine = RecommendationEngine(use_advanced_fertilizer=True)
        result = engine.get_recommendation(
            validated_data['rainfall'], validated_data['temperature'],
            validated_data['soil_type'], validated_data['crop_type'],
            validated_data['area'],
            budget=budget,
        )

        result['endpoint'] = 'advanced'
        result['fertilizer_algorithm'] = 'quantum-inspired'
        result['timestamp'] = datetime.now().isoformat()

        logger.info(
            f'Advanced recommendation for {validated_data["crop_type"]} '
            f'(Area: {validated_data["area"]}ha, Rainfall: {validated_data["rainfall"]}mm)'
        )

        return jsonify(result)

    except Exception as e:
        request_counter['errors'] += 1
        # BEFORE: `str(e)` was returned directly to the client, leaking
        # internal exception details (file paths, library internals) to
        # anyone calling the API. Full detail is logged server-side only;
        # the client gets a generic, safe message.
        logger.error(f'Error in /recommend/advanced: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'status': 'error'
        }), 500

@app.route('/recommend/simple', methods=['POST'])
def recommend_simple():
    request_counter['total'] += 1
    request_counter['simple'] += 1

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided', 'status': 'error'}), 400

        is_valid, validated_data, errors = validate_recommendation_input(
            data,
            defaults={'rainfall': 120, 'temperature': 26, 'soil_type': 'sandy',
                      'crop_type': 'maize', 'area': 5},
        )
        if not is_valid:
            request_counter['errors'] += 1
            return jsonify({'error': 'Validation failed', 'details': errors, 'status': 'error'}), 400

        budget_valid, budget, budget_error = extract_optional_budget(data)
        if not budget_valid:
            request_counter['errors'] += 1
            return jsonify({'error': 'Validation failed', 'details': [budget_error], 'status': 'error'}), 400

        engine = RecommendationEngine(use_advanced_fertilizer=False)
        result = engine.get_recommendation(
            validated_data['rainfall'], validated_data['temperature'],
            validated_data['soil_type'], validated_data['crop_type'],
            validated_data['area'],
            budget=budget,
        )

        result['endpoint'] = 'simple'
        result['fertilizer_algorithm'] = 'linear-formula'
        result['timestamp'] = datetime.now().isoformat()
        result['note'] = 'Using simple formula for backward compatibility'

        logger.info(f'Simple recommendation for {validated_data["crop_type"]}')

        return jsonify(result)

    except Exception as e:
        request_counter['errors'] += 1
        logger.error(f'Error in /recommend/simple: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'Invalid request',
            'status': 'error'
        }), 400

@app.route('/recommend/batch', methods=['POST'])
@limiter.limit("5 per minute")
def recommend_batch():
    request_counter['total'] += 1
    
    try:
        data = request.get_json()
        if not data or 'requests' not in data:
            return jsonify({'error': 'No batch requests provided', 'status': 'error'}), 400
        
        requests = data.get('requests', [])
        use_advanced = data.get('advanced', True)
        
        if not isinstance(requests, list) or len(requests) > 50:
            return jsonify({
                'error': 'Requests must be a list (max 50 items)',
                'status': 'error'
            }), 400
        
        results = []
        engine = RecommendationEngine(use_advanced_fertilizer=use_advanced)
        
        for i, req in enumerate(requests):
            try:
                is_valid, validated_data, errors = validate_recommendation_input(
                    req,
                    defaults={'rainfall': 120, 'temperature': 26, 'soil_type': 'sandy',
                              'crop_type': 'maize', 'area': 5},
                )
                if not is_valid:
                    results.append({
                        'batch_index': i,
                        'status': 'error',
                        'error': 'Validation failed',
                        'details': errors,
                        'input_parameters': req,
                    })
                    continue

                result = engine.get_recommendation(
                    validated_data['rainfall'], validated_data['temperature'],
                    validated_data['soil_type'], validated_data['crop_type'],
                    validated_data['area'],
                )
                result['batch_index'] = i
                result['input_parameters'] = req
                results.append(result)

            except Exception as e:
                logger.error(f'Error in batch item {i}: {str(e)}', exc_info=True)
                results.append({
                    'batch_index': i,
                    'status': 'error',
                    'error': 'Processing failed for this item',
                    'input_parameters': req
                })
        
        return jsonify({
            'status': 'success',
            'total_requests': len(requests),
            'successful': len([r for r in results if r.get('status') == 'success']),
            'failed': len([r for r in results if r.get('status') != 'success']),
            'results': results,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        request_counter['errors'] += 1
        logger.error(f'Error in /recommend/batch: {str(e)}')
        return jsonify({
            'error': 'Batch processing failed',
            'message': str(e),
            'status': 'error'
        }), 500

@app.route('/health', methods=['GET'])
def health():
    engine = RecommendationEngine()
    test_result = engine.get_recommendation(120, 26, 'sandy', 'maize', 1.0)
    
    health_status = {
        'status': 'healthy' if test_result.get('status') == 'success' else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'service': 'Q-CYO Backend',
        'version': '1.0.0',
        'engine_status': test_result.get('status', 'unknown'),
        'ml_model_available': test_result.get('ml_model_available', False),
        'requests_processed': request_counter['total'],
        'cache_size': len(recommendation_cache),
        'memory_usage': f'{len(recommendation_cache) * 0.5:.1f}KB (estimated)'
    }
    
    return jsonify(health_status)

@app.route('/metrics', methods=['GET'])
def metrics():
    total = request_counter['total']
    errors = request_counter['errors']
    success_rate = ((total - errors) / total * 100) if total > 0 else 0
    
    return jsonify({
        'status': 'success',
        'metrics': {
            'requests_total': total,
            'requests_advanced': request_counter['advanced'],
            'requests_simple': request_counter['simple'],
            'errors_total': errors,
            'success_rate': f'{success_rate:.1f}%',
            'cache_hits': len([v for v in recommendation_cache.values() if v.get('cached', False)]),
            'cache_size': len(recommendation_cache)
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/clear-cache', methods=['POST'])
@limiter.limit("5 per hour")
def clear_cache():
    global recommendation_cache
    cache_size = len(recommendation_cache)
    recommendation_cache = {}
    
    logger.info(f'Cache cleared (was {cache_size} entries)')
    
    return jsonify({
        'status': 'success',
        'message': f'Cache cleared ({cache_size} entries removed)',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/validate-input', methods=['POST'])
def validate_input_endpoint():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided', 'status': 'error'}), 400
        
        required_fields = {
            'rainfall': InputValidator.validate_rainfall,
            'temperature': InputValidator.validate_temperature,
            'soil_type': InputValidator.validate_soil_type,
            'crop_type': InputValidator.validate_crop_type,
            'area': InputValidator.validate_area
        }
        
        is_valid, validated_data, errors = validate_input(data, required_fields)
        
        return jsonify({
            'status': 'success' if is_valid else 'invalid',
            'valid': is_valid,
            'validated_data': validated_data if is_valid else None,
            'errors': errors if not is_valid else [],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 400

@app.route('/supported', methods=['GET'])
def supported():
    return jsonify({
        'status': 'success',
        'supported_parameters': {
            'soil_types': ['sandy', 'loam', 'clay', 'silty', 'peaty', 'chalky'],
            'crop_types': ['maize', 'wheat', 'rice', 'barley', 'soybean', 'sorghum'],
            'rainfall_range': {'min': 0, 'max': 1000, 'unit': 'mm'},
            'temperature_range': {'min': -20, 'max': 50, 'unit': '°C'},
            'area_range': {'min': 0.1, 'max': 10000, 'unit': 'hectares'}
        },
        'endpoints': {
            '/recommend': 'Main endpoint (advanced fertilizer)',
            '/recommend/advanced': 'Advanced quantum fertilizer',
            '/recommend/simple': 'Simple formula (backward compatible)',
            '/recommend/batch': 'Batch processing',
            '/validate-input': 'Validate input without processing',
            '/health': 'System health check',
            '/metrics': 'API metrics',
            '/supported': 'This endpoint'
        }
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'app': 'Quantum Crop Yield Optimizer (Q-CYO)',
        'version': '1.0.0',
        'status': 'running',
        'description': 'AI-powered crop yield prediction with quantum-inspired optimization',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'GET': {
                '/': 'This documentation',
                '/health': 'Health check',
                '/metrics': 'API metrics',
                '/supported': 'Supported parameters'
            },
            'POST': {
                '/recommend': 'Get recommendation (default)',
                '/recommend/advanced': 'Advanced quantum optimization',
                '/recommend/simple': 'Simple formula',
                '/recommend/batch': 'Batch processing',
                '/validate-input': 'Validate input',
                '/clear-cache': 'Clear cache'
            }
        },
        'example_request': {
            'method': 'POST',
            'url': '/recommend',
            'headers': {'Content-Type': 'application/json'},
            'body': {
                'rainfall': 150,
                'temperature': 28,
                'soil_type': 'loam',
                'crop_type': 'maize',
                'area': 10.5
            }
        },
        'quick_start': 'curl -X POST http://localhost:5000/recommend -H "Content-Type: application/json" -d \'{"rainfall":120,"temperature":26,"soil_type":"sandy","crop_type":"maize","area":5}\''
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'Check the / endpoint for available endpoints',
        'status': 'error'
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed',
        'status': 'error'
    }), 405

if __name__ == '__main__':
    # Debug mode must never be hardcoded True: Flask's debug mode exposes the
    # interactive Werkzeug debugger, which allows arbitrary code execution to
    # anyone who can reach an unhandled exception. Default to OFF; opt in
    # explicitly with FLASK_DEBUG=1 for local development.
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    port = int(os.environ.get('PORT', 5000))

    print('\n' + '='*60)
    print('🚀 QUANTUM CROP YIELD OPTIMIZER API')
    print('='*60)
    print(f'📡 Starting server on http://0.0.0.0:{port} (debug={debug_mode})')
    print(f'📚 API Documentation: http://localhost:{port}')
    print(f'🏥 Health check: http://localhost:{port}/health')
    print('='*60 + '\n')

    app.run(host='0.0.0.0', port=port, debug=debug_mode)
