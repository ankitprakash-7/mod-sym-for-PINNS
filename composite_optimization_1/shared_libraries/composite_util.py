"""
composite_optimization/shared_libraries/composite_util.py
Self-contained workflow utilities - no external dependencies
All utility functions for the workflow system implemented fresh
"""

from typing import Dict, Any, Optional
from google.adk.tools import ToolContext
from google.adk.agents import callback_context as callback_context_module
import json
import re
import time

# ===================== WORKFLOW STATE MANAGEMENT =====================

def store_in_workflow_state(key: str, value: Any, callback_context: callback_context_module.CallbackContext):
    """Utility to store data in workflow state."""
    callback_context.state[key] = value

def get_from_workflow_state(key: str, callback_context: callback_context_module.CallbackContext, default=None):
    """Utility to retrieve data from workflow state."""
    return callback_context.state.get(key, default)

# ===================== PARAMETER PROCESSING UTILITIES =====================

def extract_parameters_from_state(callback_context: callback_context_module.CallbackContext) -> Dict[str, Any]:
    """Extract current parameters from workflow state."""
    
    # Try different sources in order of preference
    recommended = callback_context.state.get("recommended_parameters", {})
    if recommended:
        return recommended
        
    current = callback_context.state.get("current_parameters", {})
    if current:
        return current
        
    suggested = callback_context.state.get("suggested_parameters", {})
    if suggested:
        return suggested
        
    return {}

def format_parameters_for_display(parameters: Dict[str, Any]) -> str:
    """Format parameters for user presentation."""
    
    if not parameters:
        return "❌ No parameters available"
    
    formatted = "## 🔧 **Cure Cycle Parameters**\n\n"
    
    parameter_display = {
        "Heating rate r1 (°C/min)": parameters.get("ramp1", "N/A"),
        "Heating rate r2 (°C/min)": parameters.get("ramp2", "N/A"), 
        "Hold Temperature ht1 (°C)": parameters.get("hold_temp1", "N/A"),
        "Hold Temperature ht2 (°C)": parameters.get("hold_temp2", "N/A"),
        "Hold duration hd1 (min)": parameters.get("hold_duration1", "N/A"),
        "Hold duration hd2 (min)": parameters.get("hold_duration2", "N/A"),
        "Heat transfer coefficient top (W/m²K)": parameters.get("htc_top", "N/A"),
        "Heat transfer coefficient bottom (W/m²K)": parameters.get("htc_bottom", "N/A"),
        "Tool thickness (cm)": parameters.get("tool_thickness", "N/A")
    }
    
    for param_name, value in parameter_display.items():
        formatted += f"• **{param_name}**: {value}\n"
    
    return formatted

def calculate_performance_gaps(
    current_performance: Dict[str, Any], 
    user_objectives: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate specific gaps between performance and objectives."""
    
    gaps = {}
    
    # Thermal lag analysis
    if "thermal_lag" in current_performance and "max_thermal_lag" in user_objectives:
        current_lag = current_performance["thermal_lag"]
        target_lag = user_objectives["max_thermal_lag"]
        gaps["thermal_lag"] = {
            "current": current_lag,
            "target": target_lag,
            "gap": current_lag - target_lag,
            "status": "PASS" if current_lag <= target_lag else "FAIL"
        }
    
    # Exotherm analysis
    if "exotherm_spike" in current_performance and "max_exotherm" in user_objectives:
        current_exotherm = current_performance["exotherm_spike"]
        target_exotherm = user_objectives["max_exotherm"]
        gaps["exotherm"] = {
            "current": current_exotherm,
            "target": target_exotherm, 
            "gap": current_exotherm - target_exotherm,
            "status": "PASS" if current_exotherm <= target_exotherm else "FAIL"
        }
    
    # DOC analysis
    if "min_doc" in current_performance and "min_doc" in user_objectives:
        current_doc = current_performance["min_doc"] * 100  # Convert to percentage
        target_doc = user_objectives["min_doc"]
        gaps["min_doc"] = {
            "current": current_doc,
            "target": target_doc,
            "gap": current_doc - target_doc,
            "status": "PASS" if current_doc >= target_doc else "FAIL"
        }
    
    # DOC gradient analysis
    if "doc_gradient" in current_performance and "max_doc_gradient" in user_objectives:
        current_gradient = current_performance["doc_gradient"] * 100
        target_gradient = user_objectives["max_doc_gradient"]
        gaps["doc_gradient"] = {
            "current": current_gradient,
            "target": target_gradient,
            "gap": current_gradient - target_gradient,
            "status": "PASS" if current_gradient <= target_gradient else "FAIL"
        }
    
    # Calculate violations count
    violations = sum(1 for gap_data in gaps.values() if gap_data["status"] == "FAIL")
    gaps["violations_count"] = violations
    
    return gaps

# ===================== USER INTERACTION UTILITIES =====================

def parse_user_approval(user_response: str) -> bool:
    """Parse user response for approval."""
    
    positive_indicators = ["yes", "approve", "ok", "proceed", "continue", "run", "go ahead", "sounds good"]
    negative_indicators = ["no", "reject", "stop", "cancel", "don't", "wait", "not yet"]
    
    response_lower = user_response.lower()
    
    # Check for explicit positive
    if any(indicator in response_lower for indicator in positive_indicators):
        return True
        
    # Check for explicit negative  
    if any(indicator in response_lower for indicator in negative_indicators):
        return False
        
    # Default to requiring explicit approval
    return False

def format_optimization_summary(callback_context: callback_context_module.CallbackContext) -> str:
    """Generate final optimization summary from workflow state."""
    
    iteration_history = callback_context.state.get("iteration_history", [])
    best_parameters = callback_context.state.get("best_parameters", {})
    best_performance = callback_context.state.get("best_performance", {})
    user_objectives = callback_context.state.get("user_objectives", {})
    
    summary = "## 🎯 **Optimization Complete**\n\n"
    
    if iteration_history:
        summary += f"**Total Iterations**: {len(iteration_history)}\n"
        summary += f"**Best Performance**: {best_performance.get('violations_count', 'N/A')} violations\n\n"
    
    if best_parameters:
        summary += "**🏆 Best Cure Cycle Parameters:**\n"
        summary += format_parameters_for_display(best_parameters)
        summary += "\n"
    
    if best_performance and user_objectives:
        performance_gaps = calculate_performance_gaps(best_performance, user_objectives)
        summary += "**📊 Final Performance vs Objectives:**\n\n"
        
        for metric, data in performance_gaps.items():
            if metric == "violations_count":
                continue
            
            status_icon = "✅" if data["status"] == "PASS" else "❌"
            summary += f"{status_icon} **{metric.replace('_', ' ').title()}**: {data['current']:.1f} (Target: {data['target']:.1f})\n"
    
    return summary

# ===================== VALIDATION UTILITIES =====================

def validate_requirements_complete(callback_context: callback_context_module.CallbackContext) -> bool:
    """Check if all required information is gathered."""
    
    required_objectives = ["max_exotherm", "max_thermal_lag", "min_doc", "max_doc_gradient"]
    required_specs = ["material_type", "part_thickness", "tool_material", "tool_thickness"]
    
    user_objectives = callback_context.state.get("user_objectives", {})
    material_specs = callback_context.state.get("material_specs", {})
    
    objectives_complete = all(obj in user_objectives for obj in required_objectives)
    specs_complete = all(spec in material_specs for spec in required_specs)
    
    return objectives_complete and specs_complete

def validate_simulation_ready(callback_context: callback_context_module.CallbackContext) -> bool:
    """Check if simulation can be executed."""
    
    required_state = [
        "suggested_parameters",
        "parameters_valid", 
        "user_objectives",
        "material_specs"
    ]
    
    return all(callback_context.state.get(key) is not None for key in required_state)

def validate_optimization_ready(callback_context: callback_context_module.CallbackContext) -> bool:
    """Check if optimization iteration can proceed."""
    
    required_state = [
        "latest_pino_results",
        "current_performance", 
        "user_objectives",
        "autoclave_knowledge"
    ]
    
    return all(callback_context.state.get(key) is not None for key in required_state)

# ===================== MATERIAL DATABASE =====================

def get_material_properties(material_type: str) -> Dict[str, Any]:
    """Get material-specific properties and constraints."""
    
    material_database = {
        "AS4/8552": {
            "description": "Standard aerospace carbon fiber prepreg",
            "typical_cure_temp": 180.0,
            "gel_time_range": [15, 25],
            "default_htc_range": [50, 150],
            "ramp_rate_range": [1.0, 3.0],
            "hold_temp_range": [170, 190],
            "considerations": [
                "Lower ramp rates for thick parts to avoid thermal gradients",
                "Extended hold times may be needed for thick sections",
                "Monitor exotherm carefully with this resin system"
            ]
        },
        "IM7/8552": {
            "description": "High modulus carbon fiber prepreg",
            "typical_cure_temp": 180.0, 
            "gel_time_range": [12, 20],
            "default_htc_range": [60, 140],
            "ramp_rate_range": [0.8, 2.5],
            "hold_temp_range": [170, 190],
            "considerations": [
                "Higher modulus fibers may require more controlled heating",
                "Shorter gel time requires careful timing control",
                "May need lower ramp rates than AS4/8552"
            ]
        }
    }
    
    return material_database.get(material_type, material_database["AS4/8552"])

# ===================== PERFORMANCE ANALYSIS UTILITIES =====================

def analyze_performance_vs_objectives(
    performance_data: Dict[str, Any],
    user_objectives: Dict[str, Any]
) -> str:
    """Generate detailed performance vs objectives analysis."""
    
    gaps = calculate_performance_gaps(performance_data, user_objectives)
    
    analysis = "## 📊 **PERFORMANCE ANALYSIS vs OBJECTIVES**\n\n"
    
    # Performance table
    analysis += "| Metric | Current Value | Target Value | Status | Gap |\n"
    analysis += "|--------|---------------|--------------|--------|---------|\n"
    
    for metric, data in gaps.items():
        if metric == "violations_count":
            continue
            
        current = f"{data['current']:.1f}"
        target_symbol = "≤" if "lag" in metric or "exotherm" in metric else "≥"
        target = f"{target_symbol} {data['target']:.1f}"
        status = "✅ PASS" if data['status'] == "PASS" else "❌ FAIL"
        gap = f"{data['gap']:+.1f}"
        
        metric_display = metric.replace('_', ' ').title()
        analysis += f"| {metric_display} | {current} | {target} | {status} | {gap} |\n"
    
    violations = gaps.get("violations_count", 0)
    total_objectives = len(gaps) - 1
    
    analysis += f"\n**Overall Status**: {violations}/{total_objectives} objectives failed\n\n"
    
    # Specific issue analysis
    if violations > 0:
        analysis += "**🔍 Specific Issues:**\n"
        for metric, data in gaps.items():
            if data.get("status") == "FAIL":
                analysis += f"• **{metric.replace('_', ' ').title()}**: {data['current']:.1f} vs target {data['target']:.1f} (gap: {data['gap']:+.1f})\n"
    else:
        analysis += "🎉 **All objectives met!**\n"
    
    return analysis

# ===================== PARAMETER OPTIMIZATION UTILITIES =====================

def generate_parameter_improvements(
    current_parameters: Dict[str, Any],
    performance_gaps: Dict[str, Any],
    knowledge_guidance: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate improved parameters based on performance analysis."""
    
    improved_parameters = current_parameters.copy()
    optimization_reasoning = {}
    
    # Handle thermal lag issues
    thermal_lag_gap = performance_gaps.get("thermal_lag", {})
    if thermal_lag_gap.get("status") == "FAIL":
        gap = thermal_lag_gap["gap"]
        
        # Reduce ramp rates (primary control for thermal lag)
        if "ramp1" in improved_parameters:
            current_ramp1 = improved_parameters["ramp1"]
            reduction_factor = 0.8 if gap > 5 else 0.9
            improved_parameters["ramp1"] = max(1.0, current_ramp1 * reduction_factor)
            optimization_reasoning["ramp1"] = f"Reduced from {current_ramp1:.1f} to {improved_parameters['ramp1']:.1f} °C/min to reduce thermal lag"
            
        if "ramp2" in improved_parameters:
            current_ramp2 = improved_parameters["ramp2"]
            reduction_factor = 0.75 if gap > 5 else 0.85
            improved_parameters["ramp2"] = max(0.8, current_ramp2 * reduction_factor)
            optimization_reasoning["ramp2"] = f"Reduced from {current_ramp2:.1f} to {improved_parameters['ramp2']:.1f} °C/min for thermal gradient control"
    
    # Handle exotherm issues
    exotherm_gap = performance_gaps.get("exotherm", {})
    if exotherm_gap.get("status") == "FAIL":
        gap = exotherm_gap["gap"]
        
        # Increase heat transfer coefficients
        if "htc_top" in improved_parameters:
            current_htc_top = improved_parameters["htc_top"]
            increase_factor = 1.15 if gap > 2 else 1.1
            improved_parameters["htc_top"] = min(150, current_htc_top * increase_factor)
            optimization_reasoning["htc_top"] = f"Increased from {current_htc_top:.0f} to {improved_parameters['htc_top']:.0f} W/m²K to improve heat dissipation"
            
        if "htc_bottom" in improved_parameters:
            current_htc_bottom = improved_parameters["htc_bottom"]
            increase_factor = 1.1 if gap > 2 else 1.05
            improved_parameters["htc_bottom"] = min(140, current_htc_bottom * increase_factor)
            optimization_reasoning["htc_bottom"] = f"Increased from {current_htc_bottom:.0f} to {improved_parameters['htc_bottom']:.0f} W/m²K for better heat removal"
        
        # Also slightly reduce ramp rates if exotherm is severe
        if gap > 3:
            if "ramp1" in improved_parameters and "ramp1" not in optimization_reasoning:
                current_ramp1 = improved_parameters["ramp1"]
                improved_parameters["ramp1"] = max(1.0, current_ramp1 * 0.9)
                optimization_reasoning["ramp1"] = f"Reduced from {current_ramp1:.1f} to {improved_parameters['ramp1']:.1f} °C/min to control severe exotherm"
    
    # Handle DOC issues
    doc_gap = performance_gaps.get("min_doc", {})
    if doc_gap.get("status") == "FAIL":
        gap = doc_gap["gap"]  # Negative gap means we're under target
        
        # Extend hold times to improve cure
        if "hold_duration2" in improved_parameters:
            current_hold2 = improved_parameters["hold_duration2"]
            extension = min(60, abs(gap) * 3)  # Add time based on gap
            improved_parameters["hold_duration2"] = current_hold2 + extension
            optimization_reasoning["hold_duration2"] = f"Extended from {current_hold2:.0f} to {improved_parameters['hold_duration2']:.0f} min to improve degree of cure"
        
        # Slightly increase hold temperature if gap is large
        if abs(gap) > 10 and "hold_temp2" in improved_parameters:
            current_temp2 = improved_parameters["hold_temp2"]
            improved_parameters["hold_temp2"] = min(190, current_temp2 + 5)
            optimization_reasoning["hold_temp2"] = f"Increased from {current_temp2:.0f} to {improved_parameters['hold_temp2']:.0f} °C to accelerate cure"
    
    # Handle DOC gradient issues
    doc_gradient_gap = performance_gaps.get("doc_gradient", {})
    if doc_gradient_gap.get("status") == "FAIL":
        # Balance heat transfer coefficients for more uniform cure
        if "htc_top" in improved_parameters and "htc_bottom" in improved_parameters:
            htc_top = improved_parameters["htc_top"]
            htc_bottom = improved_parameters["htc_bottom"]
            htc_avg = (htc_top + htc_bottom) / 2
            
            # Move HTCs closer to average for better uniformity
            improved_parameters["htc_top"] = htc_avg + (htc_top - htc_avg) * 0.7
            improved_parameters["htc_bottom"] = htc_avg + (htc_bottom - htc_avg) * 0.7
            
            optimization_reasoning["htc_balance"] = f"Balanced HTCs for uniformity: top {htc_top:.0f}→{improved_parameters['htc_top']:.0f}, bottom {htc_bottom:.0f}→{improved_parameters['htc_bottom']:.0f}"
    
    return {
        "improved_parameters": improved_parameters,
        "optimization_reasoning": optimization_reasoning,
        "improvements_count": len(optimization_reasoning)
    }

# ===================== CONVERSATIONAL PARSING UTILITIES =====================

def extract_user_objectives_from_text(conversation_text: str) -> Dict[str, Any]:
    """Extract objectives from natural language text."""
    
    objectives = {}
    
    # Extract exotherm limit
    exotherm_patterns = [
        r"exotherm.*?under\s*(\d+\.?\d*)[°]?C",
        r"exotherm.*?below\s*(\d+\.?\d*)[°]?C",
        r"exotherm.*?≤\s*(\d+\.?\d*)[°]?C"
    ]
    
    for pattern in exotherm_patterns:
        match = re.search(pattern, conversation_text, re.IGNORECASE)
        if match:
            objectives["max_exotherm"] = float(match.group(1))
            break
    
    # Extract thermal lag limit
    thermal_lag_patterns = [
        r"thermal\s+lag.*?under\s*(\d+\.?\d*)[°]?C",
        r"thermal\s+lag.*?below\s*(\d+\.?\d*)[°]?C",
        r"thermal\s+lag.*?≤\s*(\d+\.?\d*)[°]?C"
    ]
    
    for pattern in thermal_lag_patterns:
        match = re.search(pattern, conversation_text, re.IGNORECASE)
        if match:
            objectives["max_thermal_lag"] = float(match.group(1))
            break
    
    # Extract minimum DOC
    doc_patterns = [
        r"minimum\s*(\d+\.?\d*)%\s*cure",
        r"min.*?(\d+\.?\d*)%.*?cure", 
        r"cure.*?≥\s*(\d+\.?\d*)%"
    ]
    
    for pattern in doc_patterns:
        match = re.search(pattern, conversation_text, re.IGNORECASE)
        if match:
            objectives["min_doc"] = float(match.group(1))
            break
    
    return objectives

def extract_material_specs_from_text(conversation_text: str) -> Dict[str, Any]:
    """Extract material specifications from natural language text."""
    
    specs = {}
    
    # Extract material type
    if re.search(r"AS4[-/\s]8552", conversation_text, re.IGNORECASE):
        specs["material_type"] = "AS4/8552"
    elif re.search(r"IM7[-/\s]8552", conversation_text, re.IGNORECASE):
        specs["material_type"] = "IM7/8552"
    
    # Extract part thickness
    thickness_patterns = [
        r"(\d+\.?\d*)\s*cm\s*thick",
        r"about\s*(\d+\.?\d*)\s*cm",
        r"thickness.*?(\d+\.?\d*)\s*cm"
    ]
    
    for pattern in thickness_patterns:
        match = re.search(pattern, conversation_text, re.IGNORECASE)
        if match:
            specs["part_thickness"] = float(match.group(1))
            break
    
    # Extract tool specifications
    tool_materials = ["aluminum", "steel", "invar"]
    for material in tool_materials:
        if material in conversation_text.lower():
            specs["tool_material"] = material
            
            # Look for tool thickness near material mention
            tool_pattern = rf"(\d+\.?\d*)\s*cm\s*{material}"
            tool_match = re.search(tool_pattern, conversation_text, re.IGNORECASE)
            if tool_match:
                specs["tool_thickness"] = float(tool_match.group(1))
            break
    
    return specs

# ===================== FORMATTING UTILITIES =====================

def format_parameter_comparison(
    current_params: Dict[str, Any],
    new_params: Dict[str, Any],
    reasoning: Dict[str, str]
) -> str:
    """Format parameter comparison table for user approval."""
    
    comparison = "## 🔧 **Parameter Optimization Recommendations**\n\n"
    comparison += "| Parameter | Current | → | Recommended | Reasoning |\n"
    comparison += "|-----------|---------|---|-------------|------------|\n"
    
    parameter_names = {
        "ramp1": "Heating rate r1 (°C/min)",
        "ramp2": "Heating rate r2 (°C/min)",
        "hold_temp1": "Hold Temperature ht1 (°C)",
        "hold_temp2": "Hold Temperature ht2 (°C)",
        "hold_duration1": "Hold duration hd1 (min)",
        "hold_duration2": "Hold duration hd2 (min)",
        "htc_top": "HTC top (W/m²K)",
        "htc_bottom": "HTC bottom (W/m²K)",
        "tool_thickness": "Tool thickness (cm)"
    }
    
    for param_key, display_name in parameter_names.items():
        if param_key in new_params:
            current_val = current_params.get(param_key, "N/A")
            new_val = new_params[param_key]
            change_reason = reasoning.get(param_key, "Maintained")
            
            # Format values appropriately
            if isinstance(current_val, (int, float)) and isinstance(new_val, (int, float)):
                if abs(new_val - current_val) > 0.01:  # Significant change
                    current_str = f"{current_val:.1f}"
                    new_str = f"{new_val:.1f}"
                    arrow = "↗️" if new_val > current_val else "↘️"
                else:
                    current_str = f"{current_val:.1f}"
                    new_str = f"{new_val:.1f}"
                    arrow = "➡️"
            else:
                current_str = str(current_val)
                new_str = str(new_val)
                arrow = "➡️"
            
            comparison += f"| {display_name} | {current_str} | {arrow} | {new_str} | {change_reason} |\n"
    
    return comparison

def create_workflow_summary_report(callback_context: callback_context_module.CallbackContext) -> str:
    """Create comprehensive workflow summary report."""
    
    # Get workflow timing
    start_time = callback_context.state.get("workflow_start_time", time.time())
    end_time = time.time()
    duration = end_time - start_time
    
    # Get phase completion status
    phases_complete = callback_context.state.get("phases_complete", {})
    completed_phases = sum(phases_complete.values())
    
    # Get optimization results
    iteration_count = callback_context.state.get("optimization_iteration", 0)
    best_violations = callback_context.state.get("best_violations_count", 999)
    
    report = f"""
# 🎯 **Composite Cure Cycle Optimization - Complete Report**

## ⏱️ **Workflow Summary**
- **Duration**: {duration:.1f} seconds
- **Phases Completed**: {completed_phases}/4
- **Optimization Iterations**: {iteration_count}
- **Final Violations**: {best_violations}

## 📋 **Phase Status**
"""
    
    phase_icons = {"requirements": "📝", "knowledge": "🧠", "baseline_simulation": "🔬", "optimization": "🔧"}
    for phase, completed in phases_complete.items():
        icon = phase_icons.get(phase, "📌")
        status = "✅ Complete" if completed else "❌ Incomplete"
        report += f"- {icon} **{phase.replace('_', ' ').title()}**: {status}\n"
    
    return report