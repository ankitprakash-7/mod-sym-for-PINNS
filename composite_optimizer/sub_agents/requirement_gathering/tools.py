# composite_optimizer/sub_agents/requirement_gathering/tools.py

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

"""Tools for requirement gathering and parameter suggestion"""

import random
import re
from typing import Dict, Any


def intelligent_parameter_suggestion(context: dict) -> dict:
    """
    MANDATORY FIRST STEP: Provides intelligent parameter suggestions based on material type and part geometry.
    
    Use this function immediately after collecting user requirements to generate initial cure cycle parameters.
    
    Args:
        context: Dictionary containing:
            - "material_type": Material system (e.g., "AS4/8552", "T700/M21")
            - "part_thickness": Part thickness as number or string (e.g., 4.0, "4cm")
            - "objectives": Optional user performance objectives
        
    Returns:
        dict: Contains "suggested_parameters" dict with all cure cycle parameters,
              "reasoning" string explaining the choices, and "adjustments_made" string
              
    Example:
        context = {"material_type": "AS4/8552", "part_thickness": 4.0}
        Returns: {"suggested_parameters": {...}, "reasoning": "...", "adjustments_made": "..."}
    """
    material_type = context.get("material_type", "AS4/8552").upper()
    
    # Handle part_thickness (always in cm as per system design)
    part_thickness_raw = context.get("part_thickness", 3.0)
    if isinstance(part_thickness_raw, str):
        # Extract numeric value - thickness is always in cm
        numeric_match = re.search(r'(\d+\.?\d*)', part_thickness_raw)
        if numeric_match:
            part_thickness = float(numeric_match.group(1))
        else:
            part_thickness = 3.0  # Default fallback
    else:
        part_thickness = float(part_thickness_raw)
    
    # All thickness values are in cm as per system design
    
    # Material-specific base parameters
    base_params = {
        "AS4/8552": {
            "Heating rate r1 (°C/min)": 1.5,
            "Heating rate r2 (°C/min)": 2.0,
            "Hold Temperature ht1 (°C)": 110,
            "Hold Temperature ht2 (°C)": 180,
            "Hold duration hd1 (min)": 60,
            "Hold duration hd2 (min)": 120,
            "Heat transfer coefficient top htop p (W/m2K)": 95,
            "Heat transfer coefficient bottom hbot p (W/m2K)": 85,
        },
        "T700/M21": {
            "Heating rate r1 (°C/min)": 1.8,
            "Heating rate r2 (°C/min)": 2.2,
            "Hold Temperature ht1 (°C)": 115,
            "Hold Temperature ht2 (°C)": 175,
            "Hold duration hd1 (min)": 55,
            "Hold duration hd2 (min)": 115,
            "Heat transfer coefficient top htop p (W/m2K)": 90,
            "Heat transfer coefficient bottom hbot p (W/m2K)": 80,
        }
    }
    
    # Get base parameters for material (fallback to AS4/8552)
    params = base_params.get(material_type, base_params["AS4/8552"]).copy()
    
    # Adjust for thick parts (>3cm)
    if part_thickness > 3.0:
        thickness_factor = part_thickness / 3.0
        params["Heating rate r1 (°C/min)"] *= 0.8  # Slower heating
        params["Heating rate r2 (°C/min)"] *= 0.9
        params["Hold duration hd1 (min)"] = int(params["Hold duration hd1 (min)"] * thickness_factor)
        params["Hold duration hd2 (min)"] = int(params["Hold duration hd2 (min)"] * thickness_factor)
    
    # Add tool thickness suggestion
    params["Tool thickness Lt (cm)"] = max(2.0, part_thickness * 0.7)
    
    return {
        "suggested_parameters": params,
        "reasoning": f"Parameters optimized for {material_type} with {part_thickness}cm thickness",
        "adjustments_made": f"{'Reduced heating rates and extended hold times for thick part' if part_thickness > 3.0 else 'Standard parameters for typical thickness'}"
    }


def verifier(user_json: dict) -> dict:
    """
    MANDATORY VALIDATION STEP: Validates and corrects cure cycle parameters against safe operating ranges.
    
    ALWAYS call this function before presenting parameters to the user. This ensures all suggested 
    parameters are within acceptable manufacturing limits and prevents dangerous cure cycles.

    Args:
        user_json: Dictionary containing cure cycle parameters to validate.
                  Can be direct parameters or nested under "user_requirements_json" key.

    Returns:
        dict: Validation results containing:
            - "all_valid" (bool): True if all values were initially valid
            - "invalid_parameters" (list): List of parameter names that were corrected  
            - "corrected_user_json" (dict): Parameters with any corrections applied
            
    Example:
        input_params = {"Heating rate r1 (°C/min)": 5.0}  # Too high!
        result = verifier(input_params)
        # Returns corrected parameters within safe range [1.2, 3.0]
        
    CRITICAL: Never present parameters to user without calling this function first!
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


def store_user_objectives(objectives: dict) -> dict:
    """
    REQUIRED STEP: Store user-defined performance objectives for later optimization use.
    
    Call this function after collecting all user performance targets to save them 
    for the optimization agent to reference during parameter improvement iterations.
    
    Args:
        objectives: Dictionary of user performance targets, e.g.:
                   {
                       "max_thermal_lag": 15.0,
                       "max_exotherm_spike": 3.0, 
                       "min_degree_of_cure": 70.0,
                       "max_doc_gradient": 5.0
                   }
        
    Returns:
        dict: Confirmation containing:
            - "status": "success"
            - "message": Confirmation text
            - "stored_objectives": Copy of stored objectives
            - "objective_count": Number of objectives stored
            
    Use this after collecting user requirements but before presenting parameters.
    """
    return {
        "status": "success",
        "message": "Your optimization targets have been saved:",
        "stored_objectives": objectives,
        "objective_count": len(objectives)
    }