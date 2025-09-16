# composite_optimizer/sub_agents/neural_pde/tools.py

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

"""Tools for neural PDE simulation using physics-informed neural operators with enhanced unit conversion"""

import os
import requests
import re
from typing import Dict, Any
from io import BytesIO

# Global variables to store latest results and parameters
_latest_pino_results = None
_latest_input_parameters = None


def run_pino_simulation(parameters: Dict[str, Any]) -> dict:
    """
    Execute physics-informed neural operator simulation with proper unit handling.
    
    Args:
        parameters: Dictionary containing cure cycle parameters
        
    Returns:
        dict: Detailed simulation results in user-friendly format
    """
    global _latest_pino_results, _latest_input_parameters
    
    try:
        # Store the input parameters for later retrieval
        _latest_input_parameters = parameters.copy()
        
        # Convert to PINO format with proper unit conversion
        pino_params = _ensure_pino_format(parameters)
        
        # Get PINO URL from environment or use default
        pino_url = os.getenv("PINO_API_URL", "http://localhost:8000")
        
        # Call PINO API
        response = requests.post(
            f"{pino_url}/inference",
            json=pino_params,
            timeout=120,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            pino_data = response.json()
            
            if pino_data.get("success", False):
                # Store raw results for optimization agent
                _latest_pino_results = pino_data
                
                # Generate comprehensive user-friendly report
                report = _generate_simulation_report(pino_data)
                return {
                    "status": "success",
                    "report": report,
                    "raw_data": pino_data
                }
            else:
                return {
                    "status": "error",
                    "message": f"Simulation failed: {pino_data.get('error', 'Unknown error')}"
                }
        else:
            return {
                "status": "error",
                "message": f"PINO API error: HTTP {response.status_code} - {response.text}"
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Cannot connect to PINO API. Please ensure the service is running on http://localhost:8000"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Simulation failed with error: {str(e)}"
        }


def get_performance_data_for_analysis() -> dict:
    """
    Extract raw performance data from latest simulation for optimization analysis.
    
    Returns:
        dict: Raw performance metrics for optimization agent to analyze
    """
    global _latest_pino_results
    
    if _latest_pino_results is None:
        return {"status": "error", "message": "No simulation results available"}
    
    try:
        data = _latest_pino_results['data']['composite']
        
        # Extract temperature data
        bottom_temp = data['bottom_layer']['temperature_c']
        middle_temp = data['middle_layer']['temperature_c']
        top_temp = data['top_layer']['temperature_c']
        overall = data['overall']
        
        # Calculate thermal metrics
        temp_values = [bottom_temp['max_reached'], middle_temp['max_reached'], top_temp['max_reached']]
        thermal_lag = max(temp_values) - min(temp_values)
        max_part_temp = overall['max_temperature_reached']
        exotherm_spike = max_part_temp - 180.0  # Exotherm above 180°C hold temp
        
        # Extract DOC data
        bottom_doc = data['bottom_layer']['cure_degree']['final']
        middle_doc = data['middle_layer']['cure_degree']['final']
        top_doc = data['top_layer']['cure_degree']['final']
        doc_values = [bottom_doc, middle_doc, top_doc]
        
        return {
            "status": "success",
            "thermal_lag": thermal_lag,
            "exotherm_spike": exotherm_spike,
            "max_part_temperature": max_part_temp,
            "min_doc": min(doc_values),
            "max_doc": max(doc_values),
            "avg_doc": overall['final_average_cure'],
            "doc_gradient": max(doc_values) - min(doc_values),
            "violations_count": _count_violations(thermal_lag, exotherm_spike, min(doc_values), max(doc_values) - min(doc_values)),
            "layer_temps": {
                "bottom": bottom_temp['max_reached'],
                "middle": middle_temp['max_reached'],
                "top": top_temp['max_reached']
            },
            "layer_docs": {
                "bottom": bottom_doc,
                "middle": middle_doc,
                "top": top_doc
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to extract performance data: {str(e)}"
        }

def get_current_parameters() -> dict:
    """Extract current parameters from the latest simulation input with proper format.
    Keep tool thickness in METERS throughout to match simulation expectations."""
    global _latest_input_parameters
    
    if _latest_input_parameters is None:
        return {"status": "error", "message": "No simulation has been run yet"}
    
    try:
        # Extract parameters from the input that was used for simulation
        if "user_requirements_json" in _latest_input_parameters:
            # From requirement gathering format
            user_req = _latest_input_parameters["user_requirements_json"]
            
            # Handle both cm and m thickness formats, but always return in METERS
            tool_thickness_m = None
            if "Tool thickness Lt (cm)" in user_req:
                tool_thickness_cm = user_req["Tool thickness Lt (cm)"]
                tool_thickness_m = tool_thickness_cm / 100.0  # Convert cm to meters
            elif "Tool thickness Lt (m)" in user_req:
                tool_thickness_m = user_req["Tool thickness Lt (m)"]  # Already in meters
            else:
                tool_thickness_m = 0.025  # Default 2.5cm in meters
            
            current_params = {
                "Heating rate r1 (°C/min)": user_req.get("Heating rate r1 (°C/min)"),
                "Heating rate r2 (°C/min)": user_req.get("Heating rate r2 (°C/min)"),
                "Hold Temperature ht1 (°C)": user_req.get("Hold Temperature ht1 (°C)"),
                "Hold Temperature ht2 (°C)": user_req.get("Hold Temperature ht2 (°C)"),
                "Hold duration hd1 (min)": user_req.get("Hold duration hd1 (min)"),
                "Hold duration hd2 (min)": user_req.get("Hold duration hd2 (min)"),
                "Heat transfer coefficient top htop p (W/m2K)": user_req.get("Heat transfer coefficient top htop p (W/m2K)"),
                "Heat transfer coefficient bottom hbot p (W/m2K)": user_req.get("Heat transfer coefficient bottom hbot p (W/m2K)"),
                "Tool thickness Lt (m)": tool_thickness_m  # ✅ Always in METERS
            }
        else:
            # FIXED: Direct format - use CORRECT parameter names from debug log
            params = _latest_input_parameters
            current_params = {
                "Heating rate r1 (°C/min)": params.get("r1"),           # ✅ FIXED: was "ramp1"
                "Heating rate r2 (°C/min)": params.get("r2"),           # ✅ FIXED: was "ramp2"
                "Hold Temperature ht1 (°C)": params.get("ht1"),         # ✅ FIXED: was "hold_temp1"
                "Hold Temperature ht2 (°C)": params.get("ht2"),         # ✅ FIXED: was "hold_temp2"
                "Hold duration hd1 (min)": params.get("hd1"),           # ✅ FIXED: was "hold_duration1"
                "Hold duration hd2 (min)": params.get("hd2"),           # ✅ FIXED: was "hold_duration2"
                "Heat transfer coefficient top htop p (W/m2K)": params.get("htc_top"),
                "Heat transfer coefficient bottom hbot p (W/m2K)": params.get("htc_bottom"),
                "Tool thickness Lt (m)": params.get("tool_thickness", 0.025)  # ✅ Already in METERS
            }
        
        # Validate that we have actual values (not None)
        valid_params = {}
        missing_params = []
        
        for key, value in current_params.items():
            if value is not None:
                valid_params[key] = value
            else:
                missing_params.append(key)
        
        if missing_params:
            return {
                "status": "partial_success",
                "parameters": valid_params,
                "message": f"Some parameters were missing: {missing_params}"
            }
        
        return {"status": "success", "parameters": valid_params}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to extract parameters: {str(e)}"}


'''# No need for _convert_meters_to_cm helper function anymore!
def get_current_parameters() -> dict:
    """Extract current parameters from the latest simulation input with proper format."""
    global _latest_input_parameters
    # === DEBUG CODE - ADD THIS ===
    print(f"\n🔍 DEBUG: get_current_parameters() called")
    print(f"🔍 DEBUG: _latest_input_parameters is None: {_latest_input_parameters is None}")
    
    if _latest_input_parameters is not None:
        print(f"🔍 DEBUG: _latest_input_parameters keys: {list(_latest_input_parameters.keys())}")
        if "user_requirements_json" in _latest_input_parameters:
            user_req = _latest_input_parameters["user_requirements_json"]
            print(f"🔍 DEBUG: user_requirements_json keys: {list(user_req.keys())}")
            
            # Check both thickness formats
            has_cm = "Tool thickness Lt (cm)" in user_req
            has_m = "Tool thickness Lt (m)" in user_req
            print(f"🔍 DEBUG: Has 'Tool thickness Lt (cm)': {has_cm}")
            print(f"🔍 DEBUG: Has 'Tool thickness Lt (m)': {has_m}")
            
            if has_cm:
                print(f"🔍 DEBUG: Tool thickness (cm): {user_req['Tool thickness Lt (cm)']}")
            if has_m:
                print(f"🔍 DEBUG: Tool thickness (m): {user_req['Tool thickness Lt (m)']}")
    print(f"🔍 DEBUG: === END DEBUG ===\n")
    
    if _latest_input_parameters is None:
        return {"status": "error", "message": "No simulation has been run yet"}
    
    try:
        # Extract parameters from the input that was used for simulation
        if "user_requirements_json" in _latest_input_parameters:
            # From requirement gathering format
            user_req = _latest_input_parameters["user_requirements_json"]
            current_params = {
                "Heating rate r1 (°C/min)": user_req.get("Heating rate r1 (°C/min)"),
                "Heating rate r2 (°C/min)": user_req.get("Heating rate r2 (°C/min)"),
                "Hold Temperature ht1 (°C)": user_req.get("Hold Temperature ht1 (°C)"),
                "Hold Temperature ht2 (°C)": user_req.get("Hold Temperature ht2 (°C)"),
                "Hold duration hd1 (min)": user_req.get("Hold duration hd1 (min)"),
                "Hold duration hd2 (min)": user_req.get("Hold duration hd2 (min)"),
                "Heat transfer coefficient top htop p (W/m2K)": user_req.get("Heat transfer coefficient top htop p (W/m2K)"),
                "Heat transfer coefficient bottom hbot p (W/m2K)": user_req.get("Heat transfer coefficient bottom hbot p (W/m2K)"),
                "Tool thickness Lt (cm)": user_req.get("Tool thickness Lt (cm)")
            }
        else:
            # Direct format - convert from PINO format back to user format
            params = _latest_input_parameters
            current_params = {
                "Heating rate r1 (°C/min)": params.get("ramp1"),
                "Heating rate r2 (°C/min)": params.get("ramp2"),
                "Hold Temperature ht1 (°C)": params.get("hold_temp1"),
                "Hold Temperature ht2 (°C)": params.get("hold_temp2"),
                "Hold duration hd1 (min)": params.get("hold_duration1"),
                "Hold duration hd2 (min)": params.get("hold_duration2"),
                "Heat transfer coefficient top htop p (W/m2K)": params.get("htc_top"),
                "Heat transfer coefficient bottom hbot p (W/m2K)": params.get("htc_bottom"),
                "Tool thickness Lt (cm)": _convert_meters_to_cm(params.get("tool_thickness", 0.025))
            }
        
        # Validate that we have actual values (not None)
        valid_params = {}
        missing_params = []
        
        for key, value in current_params.items():
            if value is not None:
                valid_params[key] = value
            else:
                missing_params.append(key)
        
        if missing_params:
            return {
                "status": "partial_success",
                "parameters": valid_params,
                "message": f"Some parameters were missing: {missing_params}"
            }
        
        return {"status": "success", "parameters": valid_params}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to extract parameters: {str(e)}"}
'''

def _count_violations(thermal_lag: float, exotherm: float, min_doc: float, doc_gradient: float) -> int:
    """Count how many objectives are violated (for optimization tracking)."""
    violations = 0
    
    # These are typical targets - the optimization agent will use actual user targets
    if thermal_lag > 15.0:  # Typical thermal lag limit
        violations += 1
    if exotherm > 5.0:  # Typical exotherm limit
        violations += 1
    if min_doc < 0.70:  # Typical 70% minimum DOC
        violations += 1
    if doc_gradient > 0.05:  # Typical 5% DOC variation limit
        violations += 1
        
    return violations


def _convert_meters_to_cm(value_in_meters: float) -> float:
    """Convert meters to centimeters."""
    return value_in_meters * 100.0


def _ensure_pino_format(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert parameter formats to PINO API format with unit conversion.
    Only extracts the specific numeric parameters needed by PINO API.
    """
    if "user_requirements_json" in parameters:
        # Convert from requirement gathering format
        user_req = parameters["user_requirements_json"]
        
        # Extract tool thickness and convert from cm to meters
        tool_thickness_raw = user_req["Tool thickness Lt (cm)"]
        tool_thickness_cm = _extract_numeric_value(tool_thickness_raw)
        tool_thickness_m = tool_thickness_cm / 100.0  # Convert cm to meters
        
        # Extract part thickness and convert from cm to meters if provided
        part_thickness_raw = parameters.get("part_thickness", 3.0)  # This one can have default as it's not from user_req
        part_thickness_cm = _extract_numeric_value(part_thickness_raw)
        part_thickness_m = part_thickness_cm / 100.0  # Convert cm to meters
        
        return {
            "ramp1": float(user_req["Heating rate r1 (°C/min)"]),
            "hold_temp1": float(user_req["Hold Temperature ht1 (°C)"]),
            "hold_duration1": float(user_req["Hold duration hd1 (min)"]),
            "ramp2": float(user_req["Heating rate r2 (°C/min)"]),
            "hold_temp2": float(user_req["Hold Temperature ht2 (°C)"]),
            "hold_duration2": float(user_req["Hold duration hd2 (min)"]),
            "htc_bottom": float(user_req["Heat transfer coefficient bottom hbot p (W/m2K)"]),
            "htc_top": float(user_req["Heat transfer coefficient top htop p (W/m2K)"]),
            "tool_thickness": tool_thickness_m,  # Converted to meters
            "part_thickness": part_thickness_m   # Converted to meters
        }
    else:
        # Direct format - only extract specific PINO parameters, ignore material names and other metadata
        pino_param_mapping = {
            "ramp1": "ramp1",
            "ramp2": "ramp2", 
            "hold_temp1": "hold_temp1",
            "hold_temp2": "hold_temp2",
            "hold_duration1": "hold_duration1",
            "hold_duration2": "hold_duration2",
            "htc_bottom": "htc_bottom",
            "htc_top": "htc_top",
            "tool_thickness": "tool_thickness",
            "part_thickness": "part_thickness"
        }
        
        result = {}
        for pino_key, param_key in pino_param_mapping.items():
            if param_key in parameters:
                value = parameters[param_key]
                # Handle thickness unit conversion
                if "thickness" in param_key:
                    result[pino_key] = _convert_thickness_to_meters(value)
                else:
                    # Ensure we only convert numeric values
                    if isinstance(value, (int, float)):
                        result[pino_key] = float(value)
                    elif isinstance(value, str):
                        try:
                            result[pino_key] = float(value)
                        except ValueError:
                            # Skip non-numeric strings (like material names)
                            continue
                    else:
                        # Skip dictionaries and other non-numeric types
                        continue
        
        return result


def _extract_numeric_value(value):
    """Extract numeric value from string or return as float."""
    if isinstance(value, str):
        # Extract numeric value from string (e.g., "2.5cm" -> 2.5)
        numeric_match = re.search(r'(\d+\.?\d*)', value)
        if numeric_match:
            return float(numeric_match.group(1))
        else:
            raise ValueError(f"Could not extract numeric value from: {value}")
    else:
        return float(value)


def _convert_thickness_to_meters(value):
    """
    Intelligently convert thickness values to meters.
    
    Logic:
    - If value > 0.1, assume it's in cm and convert to meters
    - If value <= 0.1, assume it's already in meters
    
    Examples:
    - 2.2 cm -> 0.022 m
    - 3.5 cm -> 0.035 m  
    - 0.025 m -> 0.025 m (already in meters)
    """
    try:
        numeric_value = float(value)
        
        # If value is likely in cm (>0.1), convert to meters
        # 0.1m = 10cm would be very thick for composite parts
        if numeric_value > 0.1:
            return numeric_value / 100.0  # Convert cm to meters
        else:
            return numeric_value  # Already in meters
            
    except (ValueError, TypeError):
        # If conversion fails, return default thickness in meters
        return 0.025  # 2.5 cm default


def _generate_simulation_report(pino_data: dict) -> str:
    """Generate a comprehensive, user-friendly simulation report."""
    try:
        data = pino_data['data']['composite']
        
        # Extract temperature data from all layers
        bottom_temp = data['bottom_layer']['temperature_c']
        middle_temp = data['middle_layer']['temperature_c']
        top_temp = data['top_layer']['temperature_c']
        overall = data['overall']
        
        # Calculate metrics
        temp_values = [bottom_temp['max_reached'], middle_temp['max_reached'], top_temp['max_reached']]
        thermal_lag = max(temp_values) - min(temp_values)
        max_part_temp = overall['max_temperature_reached']
        exotherm_spike = max_part_temp - 180.0  # Assuming 180°C target
        
        # DOC metrics
        bottom_doc = data['bottom_layer']['cure_degree']['final']
        middle_doc = data['middle_layer']['cure_degree']['final']
        top_doc = data['top_layer']['cure_degree']['final']
        doc_values = [bottom_doc, middle_doc, top_doc]
        doc_gradient = max(doc_values) - min(doc_values)
        avg_doc = overall['final_average_cure']
        
        # Create comprehensive report
        report = f"""
🔬 **SIMULATION RESULTS OVERVIEW**
================================================================

✅ **Simulation completed successfully** in {pino_data.get('inference_time', 0):.1f} seconds

## 🌡️ **THERMAL PERFORMANCE SUMMARY**

**Key Metrics:**
• **Thermal Lag:** {thermal_lag:.1f}°C (temperature difference across part thickness)
• **Maximum Part Temperature:** {max_part_temp:.1f}°C
• **Exotherm Spike:** {exotherm_spike:.1f}°C (above 180°C target)
• **Final Average Temperature:** {overall['final_average_temperature']:.1f}°C

**Temperature Distribution Across Layers:**
```
Top Layer:    Max = {top_temp['max_reached']:.1f}°C    | Final = {top_temp['final']:.1f}°C
Middle Layer: Max = {middle_temp['max_reached']:.1f}°C | Final = {middle_temp['final']:.1f}°C  
Bottom Layer: Max = {bottom_temp['max_reached']:.1f}°C | Final = {bottom_temp['final']:.1f}°C
```

## 🧪 **DEGREE OF CURE (DOC) ANALYSIS**

**Overall Performance:**
• **Average DOC:** {avg_doc:.3f} ({avg_doc*100:.1f}%)
• **Minimum DOC:** {min(doc_values):.3f} ({min(doc_values)*100:.1f}%)
• **Maximum DOC:** {max(doc_values):.3f} ({max(doc_values)*100:.1f}%)
• **DOC Gradient:** {doc_gradient:.3f} ({doc_gradient*100:.1f}% variation)

**DOC Distribution Across Layers:**
```
Top Layer:    {top_doc:.3f} ({top_doc*100:.1f}%)
Middle Layer: {middle_doc:.3f} ({middle_doc*100:.1f}%)
Bottom Layer: {bottom_doc:.3f} ({bottom_doc*100:.1f}%)
```

## 📊 **PROCESS PROFILE HIGHLIGHTS**

**Temperature Evolution:**
The simulation tracked temperature changes throughout the cure cycle, showing how heat transferred through the part thickness and how the exothermic curing reaction affected different layers.

**DOC Progression:**
The degree of cure advanced from 0% to final values as the material underwent chemical crosslinking during the heating and hold phases.

Ready for objective analysis and optimization recommendations!
"""
        
        return report
        
    except Exception as e:
        return f"❌ Failed to generate simulation report: {str(e)}"
