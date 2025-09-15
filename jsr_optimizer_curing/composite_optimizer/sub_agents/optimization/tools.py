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

"""Enhanced tools for optimization iteration tracking and management with parameter extraction"""

import fitz  # PyMuPDF
import requests
from io import BytesIO
import random
from typing import Dict, Any, List, Optional
import json
import time
import re

# Global variables to track optimization state
_optimization_iteration = 0
_best_parameters = None
_best_performance = None
_iteration_history = []
_user_objectives = None
_initial_parameters = None


def extract_structured_parameters(optimization_output: str) -> dict:
    """
    Extract JSON parameters from optimization agent output.
    Simple regex-based extraction of the JSON block.
    
    Args:
        optimization_output: The full text output from optimization agent
        
    Returns:
        dict: Status and extracted parameters
    """
    try:
        # Look for JSON block in the output
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, optimization_output, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            parameters = json.loads(json_str)
            return {
                "status": "success",
                "parameters": parameters,
                "message": "Successfully extracted structured parameters from optimization output"
            }
        else:
            return {
                "status": "error",
                "message": "No JSON parameter block found in optimization output",
                "parameters": None
            }
    except json.JSONDecodeError as e:
        return {
            "status": "error", 
            "message": f"Failed to parse JSON parameters: {str(e)}",
            "parameters": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to extract parameters: {str(e)}",
            "parameters": None
        }


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


def select_best_iteration(user_objectives: dict) -> dict:
    """
    Use LLM reasoning to select the best iteration based on user objectives.
    Simple approach: closest to objectives wins.
    
    Args:
        user_objectives: User's performance targets
        
    Returns:
        dict: Best iteration selection with reasoning
    """
    global _iteration_history, _user_objectives
    
    if not _iteration_history:
        return {
            "status": "error",
            "message": "No iterations available for comparison"
        }
    
    if len(_iteration_history) == 1:
        return {
            "status": "success",
            "best_iteration": _iteration_history[0],
            "reasoning": "Only one iteration available",
            "comparison_summary": "No comparison needed - single iteration"
        }
    
    # Prepare iteration comparison data
    iteration_comparison = []
    
    for iteration in _iteration_history:
        iter_data = iteration['performance_metrics']
        iter_num = iteration['iteration']
        
        # Calculate objective gaps (positive = exceeds target, negative = meets target)
        thermal_lag_gap = iter_data.get('thermal_lag', 999) - user_objectives.get('max_thermal_lag', 15)
        exotherm_gap = iter_data.get('exotherm_spike', 999) - user_objectives.get('max_exotherm_spike', 5)
        doc_gap = user_objectives.get('min_degree_of_cure', 70) - (iter_data.get('min_doc', 0) * 100)  # Convert to %
        doc_gradient_gap = (iter_data.get('doc_gradient', 999) * 100) - user_objectives.get('max_doc_gradient', 5)  # Convert to %
        
        # Count objectives met (gap <= 0 means objective met)
        objectives_met = sum([
            1 if thermal_lag_gap <= 0 else 0,
            1 if exotherm_gap <= 0 else 0, 
            1 if doc_gap <= 0 else 0,
            1 if doc_gradient_gap <= 0 else 0
        ])
        
        # Calculate total violation severity (sum of positive gaps)
        total_violation = max(0, thermal_lag_gap) + max(0, exotherm_gap) + max(0, doc_gap) + max(0, doc_gradient_gap)
        
        iteration_comparison.append({
            "iteration": iter_num,
            "performance": iter_data,
            "parameters": iteration['parameters'],
            "objectives_met": objectives_met,
            "total_violation": total_violation,
            "gaps": {
                "thermal_lag": thermal_lag_gap,
                "exotherm": exotherm_gap,
                "doc": doc_gap,
                "doc_gradient": doc_gradient_gap
            }
        })
    
    # Simple selection logic: Most objectives met first, then lowest total violation
    best_iteration = max(iteration_comparison, key=lambda x: (x['objectives_met'], -x['total_violation']))
    
    # Generate LLM reasoning
    reasoning = f"""
## 🏆 BEST ITERATION SELECTION ANALYSIS

**Selection Criteria:** Closest to user objectives wins
**User Objectives:**
- Max Thermal Lag: ≤{user_objectives.get('max_thermal_lag', 15)}°C
- Max Exotherm Spike: ≤{user_objectives.get('max_exotherm_spike', 5)}°C  
- Min Degree of Cure: ≥{user_objectives.get('min_degree_of_cure', 70)}%
- Max DOC Variation: ≤{user_objectives.get('max_doc_gradient', 5)}%

**Iteration Comparison:**
"""
    
    for comp in iteration_comparison:
        iter_num = comp['iteration']
        obj_met = comp['objectives_met']
        perf = comp['performance']
        
        status = "🏆 SELECTED" if comp == best_iteration else ""
        reasoning += f"""
**Iteration {iter_num}:** {obj_met}/4 objectives met {status}
- Thermal Lag: {perf.get('thermal_lag', 0):.1f}°C (Gap: {comp['gaps']['thermal_lag']:+.1f}°C)
- Exotherm: {perf.get('exotherm_spike', 0):.1f}°C (Gap: {comp['gaps']['exotherm']:+.1f}°C)
- Min DOC: {perf.get('min_doc', 0)*100:.1f}% (Gap: {comp['gaps']['doc']:+.1f}%)
- DOC Gradient: {perf.get('doc_gradient', 0)*100:.1f}% (Gap: {comp['gaps']['doc_gradient']:+.1f}%)
- Total Violation Score: {comp['total_violation']:.1f}
"""
    
    reasoning += f"""
**Selection Decision:**
Iteration {best_iteration['iteration']} selected because it achieved {best_iteration['objectives_met']}/4 objectives with the lowest total violation score of {best_iteration['total_violation']:.1f}.

**Why This Iteration Wins:**
- Meets the most user objectives ({best_iteration['objectives_met']}/4)
- Has the smallest combined gap from all targets
- Represents the closest overall performance to user requirements
"""

    # Get the actual iteration data
    selected_iteration_data = next(iter_data for iter_data in _iteration_history 
                                  if iter_data['iteration'] == best_iteration['iteration'])
    
    return {
        "status": "success",
        "best_iteration": selected_iteration_data,
        "best_iteration_number": best_iteration['iteration'],
        "objectives_met": best_iteration['objectives_met'],
        "total_violation_score": best_iteration['total_violation'],
        "reasoning": reasoning,
        "comparison_summary": f"Selected iteration {best_iteration['iteration']} out of {len(_iteration_history)} iterations - meets {best_iteration['objectives_met']}/4 objectives",
        "all_iterations_comparison": iteration_comparison
    }


def give_context() -> dict:
    """
    Sample give_context() function that returns realistic autoclave processing literature content.
    This simulates what the real PDF extraction would return.
    """
    
    sample_literature_content = """
# Autoclave Processing of Advanced Composites - Technical Guidelines

## Chapter 3: Temperature Control and Heating Rates

### 3.1 Optimal Heating Rate Selection
The selection of appropriate heating rates is critical for achieving uniform cure in thick composite laminates. Research by Johnson et al. (2019) demonstrates that heating rates exceeding 3°C/min can lead to significant thermal gradients in parts thicker than 2.5cm.

For carbon fiber/epoxy systems:
- Thin laminates (<2cm): 2.5-3.0°C/min acceptable
- Medium thickness (2-4cm): 1.5-2.5°C/min recommended  
- Thick laminates (>4cm): 1.2-2.0°C/min to prevent thermal shock

### 3.2 Heat Transfer Coefficient Optimization
Autoclave heat transfer coefficients typically range from 70-120 W/m²K for top surfaces exposed to circulating air. Bottom surface HTCs are reduced due to tooling thermal resistance, typically 40-90 W/m²K.

Studies by Chen and Rodriguez (2020) show that HTC ratios (top/bottom) of 1.3-1.8 provide optimal thermal uniformity for most composite systems.

## Chapter 4: Cure Kinetics and Temperature Management

### 4.1 Exotherm Control Strategies
The autocatalytic cure reaction in epoxy systems can generate significant heat, particularly in thick sections. The heat generation rate follows:

dQ/dt = ρ × Htotal × (dα/dt)

Where typical values for AS4/8552 system:
- Htotal = 560 kJ/kg (total heat of reaction)
- ρ = 1580 kg/m³ (density)

### 4.2 Temperature Hold Strategy
Research indicates that dual-temperature hold cycles provide superior control:

1. **First Hold (110-120°C)**: Controls viscosity and allows gas evacuation
   - Duration: 50-70 minutes for consolidation
   - Prevents premature gelation

2. **Second Hold (175-185°C)**: Achieves full cure
   - Duration: 115-125 minutes for complete crosslinking
   - Temperature must be maintained within ±2°C for uniform properties

## Chapter 5: Thermal Lag Minimization

### 5.1 Thermal Diffusion Analysis
Thermal lag in composite parts follows the relationship:

ΔT ≈ (dT/dt) × L² / (6α)

Where:
- dT/dt = heating rate (°C/s)
- L = part thickness (m)  
- α = thermal diffusivity (m²/s ≈ 5.1×10⁻⁷ for carbon/epoxy)

For a 3cm thick AS4/8552 laminate at 2°C/min heating:
ΔT ≈ (2/60) × (0.03)² / (6 × 5.1×10⁻⁷) ≈ 9.8°C thermal lag

### 5.2 Thickness Scaling Effects
Thermal lag scales quadratically with thickness. Parts exceeding 3cm require:
- Reduced heating rates (proportional to 1/L²)
- Extended hold times (proportional to L)
- Careful HTC balancing to prevent surface overheating

## Chapter 6: Tooling Thermal Effects

### 6.1 Tool Material Impact
Aluminum tooling (k = 200 W/mK):
- Provides rapid heat transfer to part bottom surface
- Reduces thermal lag but may cause bottom surface overheating
- Requires HTC bottom values of 70-90 W/m²K

Steel tooling (k = 45 W/mK):
- Slower heat transfer, more gradual heating
- Better for thick parts requiring thermal control
- Optimal HTC bottom values of 40-70 W/m²K

### 6.2 Tool Thickness Considerations
Tool thickness affects thermal mass and heating uniformity:
- Thin tools (2-2.5cm): Fast response, potential temperature overshoot
- Thick tools (3-4cm): Slower response, better temperature stability
- Optimal range: 2.5-3.5cm for most applications

## Chapter 7: Degree of Cure Optimization

### 7.1 Cure Progression Monitoring
Degree of cure (α) evolution follows Kamal-Sourour kinetics:

dα/dt = (K₁ + K₂αᵐ)(1-α)ⁿ

For AS4/8552 system:
- K₁ = 2.5×10⁸ exp(-85000/RT) s⁻¹
- K₂ = 1.8×10⁶ exp(-65000/RT) s⁻¹  
- m = 0.8, n = 1.8

### 7.2 Cure Uniformity Requirements
Industrial standards require:
- Minimum DOC: ≥70% throughout thickness
- DOC variation: ≤5% from surface to core
- Final average DOC: ≥85% for structural applications

Research by Williams et al. (2021) shows that cure gradients >8% can reduce mechanical properties by 15-25%.

## Chapter 8: Process Optimization Guidelines

### 8.1 Multi-Parameter Optimization
When single parameter adjustments reach physical limits:

1. **Thermal lag reduction**: Reduce heating rates AND extend hold times
2. **Exotherm control**: Lower cure temperature AND increase HTC asymmetry  
3. **DOC improvement**: Extend final hold AND optimize temperature profile

### 8.2 Constraint-Based Optimization
Manufacturing constraints often limit theoretical optima:
- Heating rate limits: 1.2-3.0°C/min (autoclave capability)
- Temperature limits: 175-185°C (material degradation threshold)
- Time constraints: 115-125min final hold (production efficiency)

Compensation strategies include:
- Multi-parameter balancing when individual limits reached
- HTC optimization within autoclave capability ranges
- Tool selection to enhance thermal management

## References
Johnson, A., Smith, B., & Lee, C. (2019). "Thermal Management in Thick Composite Laminates." Journal of Composite Manufacturing, 45(3), 234-251.

Chen, L., & Rodriguez, M. (2020). "Heat Transfer Coefficient Optimization for Autoclave Processing." Composites Science and Technology, 187, 107-118.

Williams, R., Thompson, K., & Davis, P. (2021). "Cure Uniformity Effects on Mechanical Properties." Advanced Composite Materials, 29(4), 445-462.
"""

    return {
        "status": "success",
        "content": sample_literature_content,
        "message": "Successfully extracted content from autoclave processing literature",
        "url": "sample://autoclave_processing_guidelines.pdf",
        "text_length": len(sample_literature_content),
        "page_count": 8,
        "extraction_method": "Sample literature content for testing"
    }
