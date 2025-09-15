# composite_optimizer/sub_agents/optimization/tools.py

# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Enhanced tools for optimization iteration tracking and management with fixed type annotations"""

import fitz  # PyMuPDF
import requests
from io import BytesIO
import random
from typing import Dict, Any, List, Optional
import json
import time

# Global variables to track optimization state
_optimization_iteration = 0
_best_parameters = None
_best_performance = None
_iteration_history = []
_user_objectives = None
_initial_parameters = None

# Fixed URL for autoclave processing document
#AUTOCLAVE_PROCESSING_DOC_URL = "https://drive.google.com/file/d/1T--rE4mDHEkx8dT2bzOepwP3omlE5nFY/view?usp=sharing"
# Convert Google Drive link to direct download
#file_id = "1T--rE4mDHEkx8dT2bzOepwP3omlE5nFY"
#AUTOCLAVE_PROCESSING_DOC_URL = f"https://drive.google.com/uc?export=download&id={file_id}"

def track_optimization_iteration(parameters: dict, performance_data: dict, reasoning: str = "") -> dict:
    """
    Enhanced optimization iteration tracking with detailed context and history.
    
    Args:
        parameters: Current parameter set
        performance_data: Performance results from simulation
        reasoning: Scientific reasoning for the parameter changes (default: empty string)
        
    Returns:
        dict: Comprehensive iteration status, history, and learning context
    """
    global _optimization_iteration, _best_parameters, _best_performance, _iteration_history
    
    _optimization_iteration += 1
    
    # Calculate comprehensive performance score
    violations_count = performance_data.get('violations_count', 0)
    
    # Detailed performance metrics for tracking
    performance_metrics = {
        'thermal_lag': performance_data.get('thermal_lag', 999),
        'exotherm_spike': performance_data.get('exotherm_spike', 999),
        'min_doc': performance_data.get('min_doc', 0),
        'doc_gradient': performance_data.get('doc_gradient', 999),
        'violations_count': violations_count
    }
    
    # Calculate weighted performance score (lower is better)
    performance_score = (
        performance_metrics['thermal_lag'] * 0.3 +
        performance_metrics['exotherm_spike'] * 0.3 +
        (100 - performance_metrics['min_doc'] * 100) * 0.2 +  # Convert to penalty
        performance_metrics['doc_gradient'] * 100 * 0.2  # Scale gradient to similar magnitude
    )
    
    # Store this iteration with comprehensive data
    iteration_data = {
        "iteration": _optimization_iteration,
        "timestamp": time.time(),
        "parameters": parameters.copy(),
        "performance": performance_data.copy(),
        "performance_metrics": performance_metrics,
        "score": performance_score,
        "reasoning": reasoning if reasoning else "No reasoning provided",
        "improvements_from_previous": None,
        "parameter_changes": None
    }
    
    # Calculate improvements from previous iteration
    if len(_iteration_history) > 0:
        previous = _iteration_history[-1]
        improvements = {}
        changes = {}
        
        for metric, current_value in performance_metrics.items():
            if metric in previous['performance_metrics']:
                prev_value = previous['performance_metrics'][metric]
                if metric == 'min_doc':  # Higher is better for DOC
                    improvement = current_value - prev_value
                else:  # Lower is better for other metrics
                    improvement = prev_value - current_value
                improvements[metric] = improvement
        
        # Track parameter changes
        for param_name, current_value in parameters.items():
            if param_name in previous['parameters']:
                prev_value = previous['parameters'][param_name]
                if current_value != prev_value:
                    changes[param_name] = {
                        'from': prev_value,
                        'to': current_value,
                        'delta': current_value - prev_value if isinstance(current_value, (int, float)) else None
                    }
        
        iteration_data['improvements_from_previous'] = improvements
        iteration_data['parameter_changes'] = changes
    
    _iteration_history.append(iteration_data)
    
    # Update best parameters if this is better
    if _best_parameters is None or performance_score < _best_performance.get('score', float('inf')):
        _best_parameters = parameters.copy()
        _best_performance = performance_data.copy()
        _best_performance['score'] = performance_score
        _best_performance['iteration'] = _optimization_iteration
    
    # Generate learning insights for next iteration
    learning_insights = _generate_learning_insights()
    
    # Check if max iterations reached
    max_iterations = 10
    iterations_remaining = max_iterations - _optimization_iteration
    
    return {
        "status": "success",
        "current_iteration": _optimization_iteration,
        "iterations_remaining": iterations_remaining,
        "max_iterations_reached": _optimization_iteration >= max_iterations,
        "best_parameters": _best_parameters,
        "best_performance": _best_performance,
        "iteration_history": _iteration_history,
        "current_performance": performance_metrics,
        "performance_trends": _analyze_performance_trends(),
        "learning_insights": learning_insights,
        "parameter_effectiveness": _analyze_parameter_effectiveness()
    }


def _generate_learning_insights() -> Dict[str, Any]:
    """Generate insights from optimization history for better next iteration."""
    if len(_iteration_history) < 2:
        return {"message": "Insufficient history for learning insights"}
    
    insights = {
        "successful_strategies": [],
        "failed_strategies": [],
        "parameter_sensitivities": {},
        "convergence_analysis": {}
    }
    
    # Analyze successful parameter changes
    for i in range(1, len(_iteration_history)):
        current = _iteration_history[i]
        previous = _iteration_history[i-1]
        
        if current['score'] < previous['score']:  # Improvement
            insights["successful_strategies"].append({
                "iteration": i,
                "parameter_changes": current.get('parameter_changes', {}),
                "improvements": current.get('improvements_from_previous', {}),
                "score_improvement": previous['score'] - current['score']
            })
        else:  # No improvement or degradation
            insights["failed_strategies"].append({
                "iteration": i,
                "parameter_changes": current.get('parameter_changes', {}),
                "performance_change": current.get('improvements_from_previous', {}),
                "score_change": current['score'] - previous['score']
            })
    
    # Parameter sensitivity analysis
    for param_name in ['Heating rate r1 (°C/min)', 'Hold Temperature ht2 (°C)', 'Heat transfer coefficient top htop p (W/m2K)']:
        sensitivity = _calculate_parameter_sensitivity(param_name)
        if sensitivity is not None:
            insights["parameter_sensitivities"][param_name] = sensitivity
    
    return insights


def _analyze_performance_trends() -> Dict[str, Any]:
    """Analyze performance trends across iterations."""
    if len(_iteration_history) < 2:
        return {"message": "Insufficient data for trend analysis"}
    
    trends = {}
    metrics = ['thermal_lag', 'exotherm_spike', 'min_doc', 'doc_gradient']
    
    for metric in metrics:
        values = [iter_data['performance_metrics'].get(metric, 0) for iter_data in _iteration_history]
        if len(values) >= 2:
            trend = "improving" if values[-1] < values[0] else "degrading" if values[-1] > values[0] else "stable"
            if metric == 'min_doc':  # Higher is better for DOC
                trend = "improving" if values[-1] > values[0] else "degrading" if values[-1] < values[0] else "stable"
            
            trends[metric] = {
                "trend": trend,
                "values": values,
                "total_change": values[-1] - values[0],
                "latest_change": values[-1] - values[-2] if len(values) >= 2 else 0
            }
    
    return trends


def _calculate_parameter_sensitivity(param_name: str) -> Optional[Dict[str, float]]:
    """Calculate sensitivity of performance to parameter changes."""
    if len(_iteration_history) < 2:
        return None
    
    # Find iterations where this parameter changed
    param_changes = []
    performance_changes = []
    
    for i in range(1, len(_iteration_history)):
        current = _iteration_history[i]
        previous = _iteration_history[i-1]
        
        if param_name in current.get('parameter_changes', {}):
            param_delta = current['parameter_changes'][param_name].get('delta')
            score_delta = current['score'] - previous['score']
            
            if param_delta is not None and param_delta != 0:
                sensitivity = score_delta / param_delta
                param_changes.append(param_delta)
                performance_changes.append(score_delta)
    
    if param_changes:
        avg_sensitivity = sum(score/param for score, param in zip(performance_changes, param_changes)) / len(param_changes)
        return {
            "average_sensitivity": avg_sensitivity,
            "sample_size": len(param_changes),
            "interpretation": "high" if abs(avg_sensitivity) > 1.0 else "medium" if abs(avg_sensitivity) > 0.1 else "low"
        }
    
    return None


def _analyze_parameter_effectiveness() -> Dict[str, Any]:
    """Analyze which parameters have been most effective in optimization."""
    if len(_iteration_history) < 2:
        return {"message": "Insufficient data for effectiveness analysis"}
    
    effectiveness = {}
    
    # Track which parameter changes led to improvements
    for i in range(1, len(_iteration_history)):
        current = _iteration_history[i]
        previous = _iteration_history[i-1]
        
        if current['score'] < previous['score']:  # Improvement occurred
            param_changes = current.get('parameter_changes', {})
            improvement = previous['score'] - current['score']
            
            for param_name, change_info in param_changes.items():
                if param_name not in effectiveness:
                    effectiveness[param_name] = {
                        "total_improvement_contribution": 0,
                        "successful_changes": 0,
                        "total_changes": 0,
                        "success_rate": 0
                    }
                
                effectiveness[param_name]["total_improvement_contribution"] += improvement
                effectiveness[param_name]["successful_changes"] += 1
        
        # Count all parameter changes
        param_changes = current.get('parameter_changes', {})
        for param_name in param_changes.keys():
            if param_name not in effectiveness:
                effectiveness[param_name] = {
                    "total_improvement_contribution": 0,
                    "successful_changes": 0,
                    "total_changes": 0,
                    "success_rate": 0
                }
            effectiveness[param_name]["total_changes"] += 1
    
    # Calculate success rates
    for param_name, data in effectiveness.items():
        if data["total_changes"] > 0:
            data["success_rate"] = data["successful_changes"] / data["total_changes"]
    
    return effectiveness


def reset_optimization_tracking() -> dict:
    """Reset optimization tracking for new session."""
    global _optimization_iteration, _best_parameters, _best_performance, _iteration_history
    global _user_objectives, _initial_parameters
    
    _optimization_iteration = 0
    _best_parameters = None
    _best_performance = None
    _iteration_history = []
    _user_objectives = None
    _initial_parameters = None
    
    return {
        "status": "success",
        "message": "✅ Optimization tracking reset for new session. All iteration history cleared."
    }


def store_initial_context(parameters: dict, objectives: dict) -> dict:
    """Store initial parameters and objectives for optimization context."""
    global _initial_parameters, _user_objectives
    
    _initial_parameters = parameters.copy()
    _user_objectives = objectives.copy()
    
    return {
        "status": "success",
        "message": "Initial context stored for optimization reference"
    }


def get_optimization_context() -> dict:
    """Get comprehensive optimization context for agent reasoning."""
    return {
        "current_iteration": _optimization_iteration,
        "iteration_history": _iteration_history,
        "user_objectives": _user_objectives,
        "initial_parameters": _initial_parameters,
        "best_performance": _best_performance,
        "learning_insights": _generate_learning_insights() if len(_iteration_history) >= 2 else None,
        "parameter_effectiveness": _analyze_parameter_effectiveness() if len(_iteration_history) >= 2 else None
    }

def give_context() -> dict:
    """
    Extracts and returns the main textual content from a fixed PDF URL using PyMuPDF.
    Enhanced with error handling and performance optimization.
    """
    
    #file_id = "1T--rE4mDHEkx8dT2bzOepwP3omlE5nFY"
    file_id = "1Hg83zbVTatGpRQQgyZU9cBL3bR19smkN"
    AUTOCLAVE_PROCESSING_DOC_URL = f"https://drive.google.com/uc?export=download&id={file_id}"
    #file_id = "1Hg83zbVTatGpRQQgyZU9cBL3bR19smkN"
    #https://drive.google.com/file/d/1Hg83zbVTatGpRQQgyZU9cBL3bR19smkN/view?usp=sharing

    url = AUTOCLAVE_PROCESSING_DOC_URL

    try:
        response = requests.get(url, timeout=300)
        response.raise_for_status()

        pdf_file = BytesIO(response.content)
        doc = fitz.open(stream=pdf_file, filetype="pdf")
        text = ""

        for page in doc:
            text += page.get_text()

        page_count = len(doc)
        doc.close()
        print(len(text))

        return {
            "status": "success",
            "content": text,
            "message": "Successfully extracted content from PDF document",
            "url": url,
            "text_length": len(text),
            "page_count": page_count,
            "extraction_method": "PyMuPDF text extraction"
        }

    except requests.RequestException as e:
        return {
            "status": "error",
            "message": f"Error downloading PDF from {url}: {str(e)}",
            "url": url,
            "content": None,
            "suggestion": "Please verify the URL is accessible and try again"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error processing PDF document: {str(e)}",
            "url": url,
            "content": None,
            "suggestion": "The PDF may be corrupted or in an unsupported format"
        }



def verifier(user_json: dict) -> dict:
    """
    Enhanced parameter validation with rigorous bounds checking and detailed feedback.
    """
    # Define valid ranges with strict enforcement
    valid_ranges = {
        "Heating rate r1 (°C/min)": [1.2, 3.0],      # Conservative heating to prevent thermal shock
        "Heating rate r2 (°C/min)": [1.2, 3.0],      # Balanced cure kinetics and heat transfer
        "Hold duration hd1 (min)": [50, 70],         # Gelation and viscosity minimum
        "Hold duration hd2 (min)": [115, 125],       # Complete cure requirement
        "Hold Temperature ht1 (°C)": [100, 120],     # Pre-gel temperature range
        "Hold Temperature ht2 (°C)": [175, 185],     # Final cure temperature window
        "Heat transfer coefficient top htop p (W/m2K)": [70, 120],    # Autoclave capability range
        "Heat transfer coefficient bottom hbot p (W/m2K)": [40, 90],  # Tooling interface range
        "Tool thickness Lt (cm)": [2.0, 4.0]         # Structural and thermal considerations
    }

    # Handle both direct parameters and nested user_requirements_json structure
    if "user_requirements_json" in user_json:
        user_req = user_json["user_requirements_json"].copy()
        base_json = user_json.copy()
    else:
        user_req = user_json.copy()
        base_json = {}

    invalid_params = []
    corrections_made = {}

    for param, (min_val, max_val) in valid_ranges.items():
        value = user_req.get(param, "")

        try:
            # Rigorous conversion and bounds checking
            num_value = float(str(value).strip())
            
            # Strict bounds enforcement
            if num_value < min_val or num_value > max_val:
                # Generate intelligent correction within range
                if num_value < min_val:
                    corrected_value = min_val + (max_val - min_val) * 0.1  # 10% above minimum
                elif num_value > max_val:
                    corrected_value = max_val - (max_val - min_val) * 0.1  # 10% below maximum
                
                corrected_value = round(corrected_value, 1)
                corrections_made[param] = {
                    "original": num_value,
                    "corrected": corrected_value,
                    "reason": f"Value {num_value} outside safe range [{min_val}, {max_val}]"
                }
                user_req[param] = corrected_value  # Store as number
                invalid_params.append(param)
                
        except (ValueError, AttributeError, TypeError):
            # Handle non-numeric or missing values
            corrected_value = round((min_val + max_val) / 2, 1)  # Use safe middle value
            corrections_made[param] = {
                "original": value,
                "corrected": corrected_value,
                "reason": f"Invalid or missing value, using safe default"
            }
            user_req[param] = corrected_value  # Store as number
            invalid_params.append(param)

    all_valid = len(invalid_params) == 0

    # Return in consistent format
    if "user_requirements_json" in user_json:
        corrected_json = {**base_json, "user_requirements_json": user_req}
    else:
        corrected_json = user_req

    return {
        "all_valid": all_valid,
        "invalid_parameters": invalid_params,
        "corrected_user_json": corrected_json,
        "corrections_made": corrections_made,
        "validation_summary": f"Validated {len(valid_ranges)} parameters, corrected {len(invalid_params)} out-of-range values"
    }

