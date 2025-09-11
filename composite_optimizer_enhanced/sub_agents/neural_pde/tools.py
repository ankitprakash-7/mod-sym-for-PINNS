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

# Global variable to store latest results for optimization agent
_latest_pino_results = None


def run_pino_simulation(parameters: Dict[str, Any]) -> dict:
    """
    Execute physics-informed neural operator simulation with proper unit handling.
    
    Args:
        parameters: Dictionary containing cure cycle parameters
        
    Returns:
        dict: Detailed simulation results in user-friendly format
    """
    global _latest_pino_results
    
    try:
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
    """Extract current parameters from the latest simulation with proper unit conversion."""
    global _latest_pino_results
    
    if _latest_pino_results is None:
        return {"status": "error", "message": "No simulation data available"}
    
    try:
        # Extract current parameters from PINO results
        process_params = _latest_pino_results['data']['process_parameters']
        
        # Convert back to user format with proper unit conversion
        current_params = {
            "Heating rate r1 (°C/min)": process_params.get('ramp1', 0),
            "Heating rate r2 (°C/min)": process_params.get('ramp2', 0),
            "Hold Temperature ht1 (°C)": process_params.get('hold_temp1', 0),
            "Hold Temperature ht2 (°C)": process_params.get('hold_temp2', 0),
            "Hold duration hd1 (min)": process_params.get('hold_duration1', 0),
            "Hold duration hd2 (min)": process_params.get('hold_duration2', 0),
            "Heat transfer coefficient top htop p (W/m2K)": process_params.get('htc_top', 0),
            "Heat transfer coefficient bottom hbot p (W/m2K)": process_params.get('htc_bottom', 0),
            "Tool thickness Lt (cm)": process_params.get('tool_thickness', 0) * 100  # Convert meters back to cm
        }
        
        return {"status": "success", "parameters": current_params}
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to extract parameters: {str(e)}"}


def _ensure_pino_format(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert various parameter formats to PINO API format with intelligent unit conversion.
    Handles cm to meters conversion automatically for thickness parameters.
    """
    if "user_requirements_json" in parameters:
        # Convert from requirement gathering format
        user_req = parameters["user_requirements_json"]
        
        # Extract tool thickness and convert from cm to meters
        tool_thickness_raw = user_req.get("Tool thickness Lt (cm)", 2.5)
        tool_thickness_cm = _extract_numeric_value(tool_thickness_raw, 2.5)
        tool_thickness_m = tool_thickness_cm / 100.0  # Convert cm to meters
        
        # Extract part thickness and convert from cm to meters if provided
        part_thickness_raw = parameters.get("part_thickness", 3.0)
        part_thickness_cm = _extract_numeric_value(part_thickness_raw, 3.0)
        part_thickness_m = part_thickness_cm / 100.0  # Convert cm to meters
        
        return {
            "ramp1": float(user_req.get("Heating rate r1 (°C/min)", 2.2)),
            "hold_temp1": float(user_req.get("Hold Temperature ht1 (°C)", 115)),
            "hold_duration1": float(user_req.get("Hold duration hd1 (min)", 60)),
            "ramp2": float(user_req.get("Heating rate r2 (°C/min)", 2.2)),
            "hold_temp2": float(user_req.get("Hold Temperature ht2 (°C)", 180)),
            "hold_duration2": float(user_req.get("Hold duration hd2 (min)", 120)),
            "htc_bottom": float(user_req.get("Heat transfer coefficient bottom hbot p (W/m2K)", 75)),
            "htc_top": float(user_req.get("Heat transfer coefficient top htop p (W/m2K)", 100)),
            "tool_thickness": tool_thickness_m,  # Now in meters
            "part_thickness": part_thickness_m   # Now in meters
        }
    else:
        # Direct format - ensure all numeric and convert thickness units intelligently
        defaults = {
            "ramp1": 2.2, "hold_temp1": 115, "hold_duration1": 60,
            "ramp2": 2.2, "hold_temp2": 180, "hold_duration2": 120,
            "htc_bottom": 75, "htc_top": 100,
            "tool_thickness": 0.025, "part_thickness": 0.030
        }
        
        result = {}
        for key, default_value in defaults.items():
            value = parameters.get(key, default_value)
            
            # Handle thickness unit conversion intelligently
            if "thickness" in key:
                result[key] = _convert_thickness_to_meters(value)
            else:
                result[key] = float(value)
        
        return result


def _extract_numeric_value(value, default_value):
    """Extract numeric value from string or return as float."""
    if isinstance(value, str):
        # Extract numeric value from string (e.g., "2.5cm" -> 2.5)
        numeric_match = re.search(r'(\d+\.?\d*)', value)
        return float(numeric_match.group(1)) if numeric_match else default_value
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
