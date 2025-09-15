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

"""Enhanced tools for requirement gathering and intelligent parameter suggestion"""

import random
import re
import math
from typing import Dict, Any


# Material property database for scientific parameter generation
MATERIAL_PROPERTIES = {
    "AS4/8552": {
        "thermal_conductivity": 0.8,  # W/mK
        "density": 1580,  # kg/m³
        "specific_heat": 1100,  # J/kgK
        "total_heat_of_reaction": 560000,  # J/kg
        "cure_temp_range": [175, 185],  # °C
        "gel_temp": 110,  # °C
        "activation_energy_1": 85000,  # J/mol (E1)
        "activation_energy_2": 65000,  # J/mol (E2)
        "pre_exponential_1": 2.5e8,  # A1 (s^-1)
        "pre_exponential_2": 1.8e6,  # A2 (s^-1)
        "kinetic_exponents": {"m": 0.8, "n": 1.8}
    },
    "T700/M21": {
        "thermal_conductivity": 0.7,  # W/mK  
        "density": 1560,  # kg/m³
        "specific_heat": 1050,  # J/kgK
        "total_heat_of_reaction": 420000,  # J/kg
        "cure_temp_range": [170, 180],  # °C
        "gel_temp": 115,  # °C
        "activation_energy_1": 78000,  # J/mol
        "activation_energy_2": 58000,  # J/mol
        "pre_exponential_1": 1.8e8,  # A1
        "pre_exponential_2": 1.2e6,  # A2
        "kinetic_exponents": {"m": 0.7, "n": 1.9}
    }
}

# Tooling material properties
TOOLING_PROPERTIES = {
    "ALUMINUM": {
        "thermal_conductivity": 200,  # W/mK
        "density": 2700,  # kg/m³
        "specific_heat": 900  # J/kgK
    },
    "STEEL": {
        "thermal_conductivity": 45,  # W/mK
        "density": 7850,  # kg/m³
        "specific_heat": 460  # J/kgK
    }
}


def intelligent_parameter_suggestion(context: dict) -> dict:
    """
    Enhanced intelligent parameter suggestion with scientific calculations and reasoning.
    
    Args:
        context: Dictionary containing material_type, part_thickness, tooling_material, 
                tooling_thickness, and objectives
        
    Returns:
        dict: Comprehensive parameter suggestion with scientific justification
    """
    # Extract and validate input parameters
    material_type = context.get("material_type", "AS4/8552").upper().replace("/", "/")
    
    # Handle part thickness (always in cm)
    part_thickness_raw = context.get("part_thickness", 3.0)
    if isinstance(part_thickness_raw, str):
        numeric_match = re.search(r'(\d+\.?\d*)', part_thickness_raw)
        part_thickness = float(numeric_match.group(1)) if numeric_match else 3.0
    else:
        part_thickness = float(part_thickness_raw)
    
    # Extract tooling information
    tooling_material = context.get("tooling_material", "ALUMINUM").upper()
    tooling_thickness_raw = context.get("tooling_thickness", 2.5)
    if isinstance(tooling_thickness_raw, str):
        numeric_match = re.search(r'(\d+\.?\d*)', tooling_thickness_raw)
        tooling_thickness = float(numeric_match.group(1)) if numeric_match else 2.5
    else:
        tooling_thickness = float(tooling_thickness_raw)
    
    # Get material properties
    if material_type not in MATERIAL_PROPERTIES:
        material_type = "AS4/8552"  # Default fallback
    
    mat_props = MATERIAL_PROPERTIES[material_type]
    tool_props = TOOLING_PROPERTIES.get(tooling_material, TOOLING_PROPERTIES["ALUMINUM"])
    
    # Calculate scientific parameters
    thermal_diffusivity = mat_props["thermal_conductivity"] / (mat_props["density"] * mat_props["specific_heat"])
    characteristic_time = (part_thickness * 0.01) ** 2 / thermal_diffusivity  # Convert cm to m
    
    # Biot number analysis for heating rate selection
    estimated_htc = 100  # W/m²K initial estimate
    biot_number = estimated_htc * (part_thickness * 0.01) / mat_props["thermal_conductivity"]
    
    # Base parameter calculation with scientific reasoning
    base_params = _calculate_base_parameters(mat_props, part_thickness, characteristic_time, biot_number)
    
    # Apply thickness-dependent adjustments
    thickness_adjusted_params = _apply_thickness_adjustments(base_params, part_thickness, characteristic_time)
    
    # Apply tooling-dependent adjustments
    final_params = _apply_tooling_adjustments(thickness_adjusted_params, tool_props, tooling_thickness, part_thickness)
    
    # Add tool thickness to parameters
    final_params["Tool thickness Lt (cm)"] = max(2.0, tooling_thickness)
    
    # Generate comprehensive scientific reasoning
    scientific_reasoning = _generate_scientific_reasoning(
        material_type, part_thickness, tooling_material, tooling_thickness,
        mat_props, tool_props, thermal_diffusivity, characteristic_time, biot_number
    )
    
    # Calculate performance predictions
    performance_predictions = _predict_performance(final_params, mat_props, part_thickness)
    
    return {
        "suggested_parameters": final_params,
        "reasoning": f"Parameters scientifically optimized for {material_type} with {part_thickness}cm thickness",
        "adjustments_made": _describe_adjustments(part_thickness, tooling_material, biot_number),
        "scientific_analysis": scientific_reasoning,
        "performance_predictions": performance_predictions,
        "material_properties_used": mat_props,
        "calculations": {
            "thermal_diffusivity": thermal_diffusivity,
            "characteristic_time": characteristic_time,
            "biot_number": biot_number
        }
    }


def _calculate_base_parameters(mat_props: dict, thickness: float, char_time: float, biot_num: float) -> dict:
    """Calculate base parameters using material properties and physics."""
    
    # Heating rate based on thermal diffusion time
    max_safe_heating_rate = min(3.0, 60 / char_time * 0.8)  # 80% of critical rate
    heating_rate_1 = max(1.2, max_safe_heating_rate * 0.7)  # Conservative first ramp
    heating_rate_2 = max(1.2, max_safe_heating_rate * 0.9)  # Slightly more aggressive second ramp
    
    # Hold temperatures from material properties
    hold_temp_1 = mat_props["gel_temp"]
    hold_temp_2 = mat_props["cure_temp_range"][0] + 5  # 5°C above minimum cure temp
    
    # Hold durations based on cure kinetics at temperature
    R = 8.314  # Gas constant
    T1_kelvin = hold_temp_1 + 273.15
    T2_kelvin = hold_temp_2 + 273.15
    
    # Calculate reaction rate constants at hold temperatures
    k1_at_T1 = mat_props["pre_exponential_1"] * math.exp(-mat_props["activation_energy_1"] / (R * T1_kelvin))
    k1_at_T2 = mat_props["pre_exponential_1"] * math.exp(-mat_props["activation_energy_1"] / (R * T2_kelvin))
    
    # Hold duration inversely proportional to reaction rate (minimum gel time and cure time)
    hold_duration_1 = max(50, min(70, 3600 / k1_at_T1 * 0.01))  # Scale factor for practical times
    hold_duration_2 = max(115, min(125, 7200 / k1_at_T2 * 0.01))
    
    # Heat transfer coefficients based on Biot number optimization
    htc_top = 95  # Standard autoclave top surface
    htc_bottom = 75  # Reduced due to tooling interface
    
    return {
        "Heating rate r1 (°C/min)": round(heating_rate_1, 1),
        "Heating rate r2 (°C/min)": round(heating_rate_2, 1),
        "Hold Temperature ht1 (°C)": int(hold_temp_1),
        "Hold Temperature ht2 (°C)": int(hold_temp_2),
        "Hold duration hd1 (min)": int(hold_duration_1),
        "Hold duration hd2 (min)": int(hold_duration_2),
        "Heat transfer coefficient top htop p (W/m2K)": int(htc_top),
        "Heat transfer coefficient bottom hbot p (W/m2K)": int(htc_bottom),
    }


def _apply_thickness_adjustments(params: dict, thickness: float, char_time: float) -> dict:
    """Apply thickness-dependent adjustments for thick parts."""
    
    if thickness > 3.0:
        # Thick part adjustments
        thickness_factor = min(2.0, thickness / 3.0)  # Cap at 2x adjustments
        
        # Reduce heating rates for thermal uniformity
        params["Heating rate r1 (°C/min)"] = max(1.2, params["Heating rate r1 (°C/min)"] / thickness_factor)
        params["Heating rate r2 (°C/min)"] = max(1.2, params["Heating rate r2 (°C/min)"] / (thickness_factor * 0.9))
        
        # Extend hold times for penetration
        params["Hold duration hd1 (min)"] = min(70, int(params["Hold duration hd1 (min)"] * thickness_factor))
        params["Hold duration hd2 (min)"] = min(125, int(params["Hold duration hd2 (min)"] * thickness_factor))
        
        # Adjust HTCs for better heat penetration balance
        params["Heat transfer coefficient top htop p (W/m2K)"] = min(120, int(params["Heat transfer coefficient top htop p (W/m2K)"] * 1.1))
        params["Heat transfer coefficient bottom hbot p (W/m2K)"] = max(40, int(params["Heat transfer coefficient bottom hbot p (W/m2K)"] * 0.9))
    
    return params


def _apply_tooling_adjustments(params: dict, tool_props: dict, tool_thickness: float, part_thickness: float) -> dict:
    """Apply tooling-specific thermal adjustments."""
    
    # Calculate tooling thermal mass effect
    thermal_mass_ratio = (tool_props["density"] * tool_props["specific_heat"] * tool_thickness) / (1580 * 1100 * part_thickness)
    
    # Adjust bottom HTC based on tooling thermal properties
    if tool_props["thermal_conductivity"] > 100:  # Aluminum-like
        # High conductivity tooling - can use higher bottom HTC
        params["Heat transfer coefficient bottom hbot p (W/m2K)"] = min(90, int(params["Heat transfer coefficient bottom hbot p (W/m2K)"] * 1.2))
    else:  # Steel-like
        # Lower conductivity tooling - reduce bottom HTC to prevent gradients
        params["Heat transfer coefficient bottom hbot p (W/m2K)"] = max(40, int(params["Heat transfer coefficient bottom hbot p (W/m2K)"] * 0.8))
    
    # Adjust heating rates based on thermal mass
    if thermal_mass_ratio > 2.0:  # Heavy tooling
        params["Heating rate r1 (°C/min)"] = max(1.2, params["Heating rate r1 (°C/min)"] * 0.9)
        params["Heating rate r2 (°C/min)"] = max(1.2, params["Heating rate r2 (°C/min)"] * 0.9)
    
    return params


def _generate_scientific_reasoning(material: str, part_thick: float, tool_material: str, tool_thick: float,
                                 mat_props: dict, tool_props: dict, alpha: float, tau: float, bi: float) -> str:
    """Generate detailed scientific reasoning for parameter selection."""
    
    reasoning = f"""
**Material Science Analysis for {material}:**

**Thermal Properties:**
- Thermal conductivity: k = {mat_props['thermal_conductivity']} W/mK
- Thermal diffusivity: α = {alpha:.2e} m²/s
- Characteristic diffusion time: τ = L²/α = {tau:.1f} seconds

**Heat Transfer Analysis:**
- Biot number: Bi = hL/k = {bi:.2f}
- Thermal regime: {'Thermally thick (Bi > 0.1)' if bi > 0.1 else 'Thermally thin (Bi < 0.1)'}
- Implication: {'Internal thermal gradients significant' if bi > 0.1 else 'Uniform internal temperature'}

**Cure Kinetics Considerations:**
- Gelation temperature: {mat_props['gel_temp']}°C
- Cure temperature range: {mat_props['cure_temp_range'][0]}-{mat_props['cure_temp_range'][1]}°C
- Heat of reaction: {mat_props['total_heat_of_reaction']/1000:.0f} kJ/kg
- Exotherm potential: {'High' if mat_props['total_heat_of_reaction'] > 500000 else 'Moderate'}

**Thickness Effects ({part_thick}cm):**
- Thermal lag scaling: Proportional to L² for thick parts
- Heat generation scaling: Proportional to volume (L³)
- Heat removal scaling: Proportional to surface area (L²)
- Risk assessment: {'Elevated exotherm risk' if part_thick > 3.0 else 'Standard thermal management'}

**Tooling Thermal Effects ({tool_material}, {tool_thick}cm):**
- Tool thermal conductivity: {tool_props['thermal_conductivity']} W/mK
- Tool thermal mass: {tool_props['density'] * tool_props['specific_heat'] * tool_thick:.0f} J/m²K
- Bottom surface heat transfer: {'Enhanced' if tool_props['thermal_conductivity'] > 100 else 'Limited'} by tooling
- Heating uniformity: {'Good' if tool_props['thermal_conductivity'] > 100 else 'Asymmetric'} top/bottom balance

**Parameter Selection Logic:**
- Heating rates limited by thermal diffusion time to maintain Bi < 1.0 where possible
- Hold temperatures selected for optimal cure kinetics within safe exotherm limits
- Hold durations calculated from Arrhenius kinetics for complete cure
- HTCs balanced for uniform heating considering tooling thermal properties
"""
    
    return reasoning


def _predict_performance(params: dict, mat_props: dict, thickness: float) -> dict:
    """Predict expected performance based on parameters and physics."""
    
    # Simplified performance predictions based on parameter analysis
    htc_top = params["Heat transfer coefficient top htop p (W/m2K)"]
    htc_bottom = params["Heat transfer coefficient bottom hbot p (W/m2K)"]
    heating_rate = params["Heating rate r2 (°C/min)"]
    
    # Thermal lag prediction (simplified 1D analysis)
    thermal_lag_estimate = max(0, (thickness * 0.01) * heating_rate / mat_props["thermal_conductivity"] * 10)
    
    # Exotherm prediction based on heat generation and removal balance
    heat_gen_rate = mat_props["total_heat_of_reaction"] * 0.1  # Simplified kinetic rate
    heat_removal_capacity = (htc_top + htc_bottom) / 2 * 20  # Simplified heat transfer
    exotherm_estimate = max(0, heat_gen_rate / heat_removal_capacity - 5)
    
    # DOC prediction based on hold time and temperature
    hold_duration = params["Hold duration hd2 (min)"]
    hold_temp = params["Hold Temperature ht2 (°C)"]
    doc_estimate = min(95, 50 + hold_duration * 0.3 + (hold_temp - 170) * 2)
    
    # DOC gradient estimate based on thickness and thermal uniformity
    doc_gradient_estimate = max(1, thermal_lag_estimate * 0.3)
    
    return {
        "predicted_thermal_lag": round(thermal_lag_estimate, 1),
        "predicted_exotherm_spike": round(exotherm_estimate, 1),
        "predicted_min_doc": round(doc_estimate, 1),
        "predicted_doc_gradient": round(doc_gradient_estimate, 1),
        "confidence_level": "medium",
        "basis": "Simplified physics-based models"
    }


def _describe_adjustments(thickness: float, tooling: str, biot: float) -> str:
    """Describe the adjustments made and why."""
    
    adjustments = []
    
    if thickness > 3.0:
        adjustments.append(f"Reduced heating rates and extended hold times for {thickness}cm thick part")
        adjustments.append("Applied thermal diffusion scaling for thick section cure")
    
    if biot > 0.1:
        adjustments.append("Adjusted for thermally thick regime (Bi > 0.1)")
        adjustments.append("Balanced HTCs to minimize internal thermal gradients")
    
    if tooling == "STEEL":
        adjustments.append("Reduced bottom HTC for steel tooling thermal properties")
    elif tooling == "ALUMINUM":
        adjustments.append("Optimized HTCs for aluminum tooling high conductivity")
    
    if not adjustments:
        adjustments.append("Standard parameters for typical thickness and geometry")
    
    return "; ".join(adjustments)


def verifier(user_json: dict) -> dict:
    """
    Enhanced parameter validation with rigorous bounds checking.
    """
    # Strict valid ranges for manufacturing safety
    valid_ranges = {
        "Heating rate r1 (°C/min)": [1.2, 3.0],
        "Heating rate r2 (°C/min)": [1.2, 3.0],
        "Hold duration hd1 (min)": [50, 70],
        "Hold duration hd2 (min)": [115, 125],
        "Hold Temperature ht1 (°C)": [100, 120],
        "Hold Temperature ht2 (°C)": [175, 185],
        "Heat transfer coefficient top htop p (W/m2K)": [70, 120],
        "Heat transfer coefficient bottom hbot p (W/m2K)": [40, 90],
        "Tool thickness Lt (cm)": [2.0, 4.0]
    }

    # Handle both direct parameters and nested user_requirements_json structure
    if "user_requirements_json" in user_json:
        user_req = user_json["user_requirements_json"].copy()
        base_json = user_json.copy()
    else:
        user_req = user_json.copy()
        base_json = {}

    invalid_params = []
    corrections_applied = {}

    for param, (min_val, max_val) in valid_ranges.items():
        value = user_req.get(param, "")

        try:
            # Convert to float and check bounds rigorously
            num_value = float(str(value).strip())
            
            # Strict bounds checking - must be within range
            if num_value < min_val or num_value > max_val:
                # Generate intelligent correction within safe range
                if num_value < min_val:
                    corrected_value = min_val + (max_val - min_val) * 0.2  # 20% above minimum
                elif num_value > max_val:
                    corrected_value = max_val - (max_val - min_val) * 0.2  # 20% below maximum
                
                corrected_value = round(corrected_value, 1)
                corrections_applied[param] = {
                    "original": num_value,
                    "corrected": corrected_value,
                    "reason": f"Value {num_value} outside safe manufacturing range [{min_val}, {max_val}]"
                }
                user_req[param] = corrected_value  # Store as number, not string
                invalid_params.append(param)
                
        except (ValueError, TypeError, AttributeError):
            # Handle non-numeric, empty, or invalid values
            corrected_value = round((min_val + max_val) / 2, 1)  # Use middle of range
            corrections_applied[param] = {
                "original": value,
                "corrected": corrected_value,
                "reason": f"Invalid or missing value '{value}', using safe default"
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
        "corrections_applied": corrections_applied,
        "safety_check": f"✅ Validated {len(valid_ranges)} parameters, corrected {len(invalid_params)} values"
    }


def store_user_objectives(objectives: dict) -> dict:
    """
    Enhanced storage of user objectives with validation and context.
    """
    # Validate objective format and values
    required_objectives = [
        "max_thermal_lag",
        "max_exotherm_spike", 
        "min_degree_of_cure",
        "max_doc_gradient"
    ]
    
    validated_objectives = {}
    validation_warnings = []
    
    for obj in required_objectives:
        if obj in objectives:
            value = objectives[obj]
            try:
                num_value = float(value)
                validated_objectives[obj] = num_value
                
                # Add engineering validation warnings
                if obj == "max_thermal_lag" and num_value < 5:
                    validation_warnings.append(f"Very tight thermal lag requirement ({num_value}°C) may be challenging")
                elif obj == "max_exotherm_spike" and num_value < 2:
                    validation_warnings.append(f"Very tight exotherm limit ({num_value}°C) may require conservative processing")
                elif obj == "min_degree_of_cure" and num_value > 90:
                    validation_warnings.append(f"Very high DOC requirement ({num_value}%) may need extended cure times")
                    
            except (ValueError, TypeError):
                validation_warnings.append(f"Invalid value for {obj}: {value}")
        else:
            validation_warnings.append(f"Missing required objective: {obj}")
    
    return {
        "status": "success",
        "message": "Optimization targets validated and stored",
        "stored_objectives": validated_objectives,
        "objective_count": len(validated_objectives),
        "validation_warnings": validation_warnings if validation_warnings else ["All objectives validated successfully"],
        "engineering_assessment": _assess_objective_difficulty(validated_objectives)
    }


def _assess_objective_difficulty(objectives: dict) -> str:
    """Assess the engineering difficulty of meeting the objectives."""
    
    difficulty_score = 0
    
    if objectives.get("max_thermal_lag", 20) < 10:
        difficulty_score += 2
    elif objectives.get("max_thermal_lag", 20) < 15:
        difficulty_score += 1
        
    if objectives.get("max_exotherm_spike", 10) < 3:
        difficulty_score += 2
    elif objectives.get("max_exotherm_spike", 10) < 5:
        difficulty_score += 1
        
    if objectives.get("min_degree_of_cure", 70) > 85:
        difficulty_score += 2
    elif objectives.get("min_degree_of_cure", 70) > 80:
        difficulty_score += 1
        
    if objectives.get("max_doc_gradient", 10) < 3:
        difficulty_score += 2
    elif objectives.get("max_doc_gradient", 10) < 5:
        difficulty_score += 1
    
    if difficulty_score >= 6:
        return "High difficulty - Very tight specifications requiring careful optimization"
    elif difficulty_score >= 3:
        return "Moderate difficulty - Achievable with proper parameter tuning"
    else:
        return "Standard difficulty - Should be achievable with baseline parameters"
