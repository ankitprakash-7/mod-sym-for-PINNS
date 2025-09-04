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

"""Tools for optimization iteration tracking and management"""

import fitz  # PyMuPDF
import requests
from io import BytesIO
import random
from typing import Dict, Any

# Global variables to track optimization state
_optimization_iteration = 0
_best_parameters = None
_best_performance = None
_iteration_history = []

# Fixed URL for autoclave processing document
AUTOCLAVE_PROCESSING_DOC_URL = "https://drive.google.com/file/d/1T--rE4mDHEkx8dT2bzOepwP3omlE5nFY/view?usp=sharing"


def track_optimization_iteration(parameters: dict, performance_data: dict) -> dict:
    """
    Track optimization iterations and manage the 3-attempt limit.
    
    Args:
        parameters: Current parameter set
        performance_data: Performance results from simulation
        
    Returns:
        dict: Iteration status and recommendations
    """
    global _optimization_iteration, _best_parameters, _best_performance, _iteration_history
    
    _optimization_iteration += 1
    
    # Calculate performance score (lower is better - fewer violations)
    violations_count = performance_data.get('violations_count', 999)
    performance_score = violations_count
    
    # Store this iteration
    iteration_data = {
        "iteration": _optimization_iteration,
        "parameters": parameters.copy(),
        "performance": performance_data.copy(),
        "score": performance_score
    }
    _iteration_history.append(iteration_data)
    
    # Update best parameters if this is better
    if _best_parameters is None or performance_score < _best_performance.get('score', 999):
        _best_parameters = parameters.copy()
        _best_performance = performance_data.copy()
        _best_performance['score'] = performance_score
    
    # Check if max iterations reached
    max_iterations = 3
    iterations_remaining = max_iterations - _optimization_iteration
    
    return {
        "status": "success",
        "current_iteration": _optimization_iteration,
        "iterations_remaining": iterations_remaining,
        "max_iterations_reached": _optimization_iteration >= max_iterations,
        "best_parameters": _best_parameters,
        "best_performance": _best_performance,
        "iteration_history": _iteration_history
    }


def reset_optimization_tracking() -> dict:
    """Reset optimization tracking for new session."""
    global _optimization_iteration, _best_parameters, _best_performance, _iteration_history
    _optimization_iteration = 0
    _best_parameters = None
    _best_performance = None
    _iteration_history = []
    return {
        "status": "success",
        "message": "✅ Optimization tracking reset for new session."
    }


def give_context(url: str) -> dict:
    """
    Extracts and returns the main textual content from the specified PDF URL.
    This is used to extract autoclave specifications from technical documents.

    Args:
        url: URL of the PDF document containing autoclave specifications

    Returns:
        dict: Status and extracted text content from the PDF document
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        pdf_file = BytesIO(response.content)
        doc = fitz.open(stream=pdf_file, filetype="pdf")
        text = ""
        
        for page in doc:
            text += page.get_text()
        
        doc.close()
        
        return {
            "status": "success",
            "content": text,
            "message": f"Successfully extracted content from PDF document",
            "url": url,
            "text_length": len(text)
        }
        
    except requests.RequestException as e:
        return {
            "status": "error",
            "message": f"Error downloading PDF from {url}: {str(e)}",
            "url": url,
            "content": None
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error processing PDF document: {str(e)}",
            "url": url,
            "content": None
        }


def verifier(user_json: dict) -> dict:
    """
    Validates and corrects values in parameters against predefined valid ranges.

    Args:
        user_json: Dictionary containing user input parameters

    Returns:
        dict:
            - "all_valid" (bool): True if all values were valid initially; False if any were corrected.
            - "invalid_parameters" (list): List of keys that were invalid and got modified.
            - "corrected_user_json" (dict): The updated or original JSON with valid values.
    """
    valid_ranges = {
        "Heating rate r1 (°C/min)": [1.2, 3],
        "Heating rate r2 (°C/min)": [1.2, 3],
        "Hold duration hd1 (min)": [50, 70],
        "Hold duration hd2 (min)": [115, 125],
        "Hold Temperature ht1 (°C)": [100, 120],
        "Hold Temperature ht2 (°C)": [175, 185],
        "Heat transfer coefficient top htop p (W/m2K)": [70, 120],
        "Heat transfer coefficient bottom hbot p (W/m2K)": [40, 90],
        "Tool thickness Lt (cm)": [2, 4]
    }

    # Handle both direct parameters and nested user_requirements_json structure
    if "user_requirements_json" in user_json:
        user_req = user_json["user_requirements_json"].copy()
        base_json = user_json.copy()
    else:
        user_req = user_json.copy()
        base_json = {}

    invalid_params = []

    for param, (min_val, max_val) in valid_ranges.items():
        value = user_req.get(param, "")

        try:
            num_value = float(value)
            if not (min_val <= num_value <= max_val):
                raise ValueError
        except (ValueError, AttributeError):
            corrected_value = round(random.uniform(min_val, max_val), 1)
            user_req[param] = str(corrected_value)
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
        "corrected_user_json": corrected_json
    }