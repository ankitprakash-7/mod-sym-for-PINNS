"""
composite_optimization/sub_agents/simulation/agent.py
Simulation Phase Agents - Self-contained implementation
Handles baseline simulation with PINO neural PDE model
"""

from google.adk import agents
from google.genai import types
from google.adk.agents import callback_context as callback_context_module
from google.adk.tools import FunctionTool, ToolContext
from typing import Optional, Dict, Any

# Import from new workflow structure only
from composite_optimization.shared_libraries.function_wrappers import (
    pino_simulation_function_tool,
    performance_analysis_function_tool,
    WORKFLOW_FUNCTION_TOOLS
)
from composite_optimization.shared_libraries.composite_util import (
    extract_parameters_from_state,
    calculate_performance_gaps,
    format_parameters_for_display,
    analyze_performance_vs_objectives,
    validate_simulation_ready
)
from composite_optimization import prompt

# ===================== SIMULATION PHASE CALLBACK FUNCTIONS =====================

def initialize_simulation_state(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Initialize state for baseline simulation phase."""
    callback_context.state["current_phase"] = "simulation"
    callback_context.state["baseline_simulation_complete"] = False
    callback_context.state["baseline_results"] = None
    callback_context.state["baseline_performance"] = None
    callback_context.state["simulation_ready"] = False
    return None

def prepare_baseline_simulation(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Prepare parameters for baseline simulation."""
    
    # Get suggested parameters from requirements phase
    suggested_params = callback_context.state.get("suggested_parameters", {})
    if not suggested_params:
        return types.Content(
            role='assistant',
            parts=[types.Part(text="❌ No suggested parameters available from requirements phase")]
        )
    
    # Validate parameters are ready for simulation
    parameters_valid = callback_context.state.get("parameters_valid", False)
    if not parameters_valid:
        return types.Content(
            role='assistant',
            parts=[types.Part(text="❌ Parameters not validated - cannot proceed with simulation")]
        )
    
    # Set as current parameters for simulation
    callback_context.state["current_parameters"] = suggested_params
    callback_context.state["simulation_ready"] = True
    return None

def store_baseline_results(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Store baseline simulation results for optimization comparison."""
    
    # Store baseline for later comparison
    latest_results = callback_context.state.get("latest_pino_results")
    current_performance = callback_context.state.get("current_performance")
    
    if latest_results and current_performance:
        callback_context.state["baseline_results"] = latest_results
        callback_context.state["baseline_performance"] = current_performance
        callback_context.state["baseline_simulation_complete"] = True
        callback_context.state["phases_complete"]["baseline_simulation"] = True
    
    return None

def check_simulation_ready(
    callback_context: callback_context_module.CallbackContext,
    llm_request=None
) -> Optional[types.Content]:
    """Check if simulation can proceed."""
    
    if not validate_simulation_ready(callback_context):
        missing_items = []
        if not callback_context.state.get("current_parameters"):
            missing_items.append("parameters")
        if not callback_context.state.get("parameters_valid"):
            missing_items.append("parameter validation")
        if not callback_context.state.get("user_objectives"):
            missing_items.append("objectives")
            
        return types.Content(
            role='assistant',
            parts=[types.Part(text=f"❌ Simulation not ready. Missing: {missing_items}")]
        )
    
    return None

# ===================== SIMULATION WORKFLOW TOOL FUNCTIONS =====================

def baseline_simulation_workflow_tool(
    tool_context: ToolContext
) -> str:
    """
    Execute baseline simulation with suggested parameters.
    
    Args:
        tool_context: ADK tool context for state management
        
    Returns:
        str: Baseline simulation results
    """
    
    # Get parameters from workflow state
    parameters = tool_context.state.get("current_parameters", {})
    if not parameters:
        return "❌ No parameters available for baseline simulation"
    
    # Execute simulation using the workflow tool
    # This will automatically store results in workflow state
    simulation_result = "Baseline simulation executed with suggested parameters"
    
    # Mark baseline as executed
    tool_context.state["baseline_executed"] = True
    tool_context.state["simulation_type"] = "baseline"
    
    return f"✅ Baseline simulation complete"

def baseline_analysis_workflow_tool(
    tool_context: ToolContext
) -> str:
    """
    Analyze baseline simulation results against user objectives.
    
    Args:
        tool_context: ADK tool context for state management
        
    Returns:
        str: Baseline performance analysis
    """
    
    # Get performance data from latest simulation
    current_performance = tool_context.state.get("current_performance", {})
    user_objectives = tool_context.state.get("user_objectives", {})
    
    if not current_performance:
        return "❌ No performance data available for analysis"
    
    if not user_objectives:
        return "❌ No user objectives available for comparison"
    
    # Calculate performance gaps
    performance_gaps = calculate_performance_gaps(current_performance, user_objectives)
    tool_context.state["performance_gaps"] = performance_gaps
    
    # Create baseline analysis summary
    violations = performance_gaps.get("violations_count", 0)
    total_objectives = len(performance_gaps) - 1  # Exclude violations_count
    
    analysis_summary = f"📊 Baseline Analysis: {violations}/{total_objectives} objectives failed"
    tool_context.state["baseline_analysis_summary"] = analysis_summary
    
    return f"✅ Baseline analysis complete: {analysis_summary}"

def baseline_presentation_workflow_tool(
    tool_context: ToolContext
) -> str:
    """
    Present baseline results to user in clear, actionable format.
    
    Args:
        tool_context: ADK tool context for state management
        
    Returns:
        str: Formatted baseline presentation for user
    """
    
    performance_gaps = tool_context.state.get("performance_gaps", {})
    current_performance = tool_context.state.get("current_performance", {})
    user_objectives = tool_context.state.get("user_objectives", {})
    
    if not performance_gaps:
        return "❌ No performance analysis available for presentation"
    
    # Generate comprehensive baseline presentation
    presentation = "## 📊 **BASELINE SIMULATION RESULTS**\n\n"
    
    # Performance vs objectives table
    presentation += "**Performance vs Your Objectives:**\n\n"
    presentation += "| Metric | Current Value | Target | Status | Gap |\n"
    presentation += "|--------|---------------|---------|---------|--------|\n"
    
    for metric, data in performance_gaps.items():
        if metric == "violations_count":
            continue
        
        current = f"{data['current']:.1f}"
        if "lag" in metric or "exotherm" in metric:
            target = f"≤ {data['target']:.1f}"
        else:
            target = f"≥ {data['target']:.1f}"
        
        status = "✅ PASS" if data['status'] == "PASS" else "❌ FAIL"
        gap = f"{data['gap']:+.1f}"
        
        metric_display = metric.replace('_', ' ').title()
        presentation += f"| {metric_display} | {current} | {target} | {status} | {gap} |\n"
    
    violations = performance_gaps.get("violations_count", 0)
    total_objectives = len(performance_gaps) - 1
    
    presentation += f"\n**Overall Status**: {violations}/{total_objectives} objectives failed\n\n"
    
    # Layer-by-layer analysis if available
    layer_temps = current_performance.get("layer_temps", {})
    layer_docs = current_performance.get("layer_docs", {})
    
    if layer_temps and layer_docs:
        presentation += "**Detailed Layer Analysis:**\n\n"
        presentation += "| Layer | Max Temp (°C) | Final DOC (%) |\n"
        presentation += "|-------|---------------|---------------|\n"
        
        for layer in ["top", "middle", "bottom"]:
            if layer in layer_temps and layer in layer_docs:
                temp = layer_temps[layer]
                doc = layer_docs[layer] * 100
                presentation += f"| {layer.title()} | {temp:.1f} | {doc:.1f} |\n"
    
    # User decision point
    if violations > 0:
        presentation += "\n🔧 **Ready to proceed with optimization to improve these results?**\n"
        tool_context.state["recommend_optimization"] = True
    else:
        presentation += "\n🎉 **All objectives met! Would you like to optimize further for even better performance?**\n"
        tool_context.state["recommend_optimization"] = False
    
    return presentation

# ===================== CREATE SIMULATION FUNCTION TOOLS =====================

baseline_simulation_function_tool = FunctionTool.create(baseline_simulation_workflow_tool)
baseline_analysis_function_tool = FunctionTool.create(baseline_analysis_workflow_tool) 
baseline_presentation_function_tool = FunctionTool.create(baseline_presentation_workflow_tool)

# ===================== SIMULATION PHASE SUB-AGENTS =====================

# Agent 1: Execute baseline simulation
baseline_simulation_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="baseline_simulation_agent",
    description="Execute baseline PINO simulation with suggested parameters",
    instruction="""
You execute the baseline simulation to establish performance before optimization.

## Your Process:
1. Confirm current_parameters are available in workflow state
2. Use pino_simulation_tool to execute PINO neural PDE simulation
3. Use baseline_simulation_tool to mark baseline execution
4. Confirm simulation completed successfully

## Communication:
- Report simulation execution status
- Confirm results stored in workflow state
- Note any issues or warnings

## Key Points:
- This establishes the baseline that optimization will improve
- Results are stored for comparison with optimization iterations
- Must complete successfully before proceeding to analysis

Focus on clear execution status and error handling.
""",
    tools=[pino_simulation_function_tool, baseline_simulation_function_tool],
    before_model_callback=check_simulation_ready,
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 2: Analyze baseline performance
baseline_analysis_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="baseline_analysis_agent", 
    description="Analyze baseline simulation performance against user objectives",
    instruction="""
You analyze baseline simulation results against user objectives with exact numbers.

## Your Process:
1. Use performance_analysis_tool to extract performance data from simulation
2. Use baseline_analysis_tool to compare against user objectives
3. Calculate specific gaps between current and target performance
4. Identify which objectives passed/failed and by exactly how much

## Requirements:
- Provide EXACT numerical analysis (no vague statements)
- Calculate specific gaps (e.g., "thermal lag is 18.5°C vs 15°C target = 3.5°C over")
- Clear pass/fail status for each objective
- Store detailed analysis for optimization phase use

## Focus:
- Thermal lag analysis (temperature uniformity)
- Exotherm spike analysis (peak temperature control)
- Degree of cure analysis (minimum and gradient)
- Layer-by-layer performance breakdown

This analysis drives the optimization strategy and parameter adjustments.
""",
    tools=[performance_analysis_function_tool, baseline_analysis_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 3: Present baseline results to user
baseline_presentation_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="baseline_presentation_agent",
    description="Present baseline results to user in clear, actionable format",
    instruction="""
You present baseline simulation results to the user in a clear, professional format.

## Your Process:  
1. Use baseline_presentation_tool to format comprehensive results
2. Show detailed performance vs objectives comparison
3. Highlight specific gaps and issues that need optimization
4. Ask user about proceeding with optimization

## Presentation Requirements:
- Clear performance vs target table with exact numbers
- Specific numerical gaps (not vague descriptions like "didn't meet targets")
- Explicit pass/fail status for each objective
- Layer-by-layer analysis if available
- Professional but accessible language

## User Decision Point:
Present clear question: "Would you like to proceed with optimization to improve these results?"

## Key Messages:
- If objectives failed: Focus on specific improvements needed
- If all objectives met: Highlight success and offer further optimization
- Always be specific about what needs improvement and by how much

This presentation helps user understand current performance and decide on optimization.
""",
    tools=[baseline_presentation_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# ===================== COMPLETE BASELINE SIMULATION PHASE =====================

baseline_simulation_phase_agent = agents.SequentialAgent(
    name="baseline_simulation_phase_agent",
    description="Complete baseline simulation workflow before optimization",
    sub_agents=[
        baseline_simulation_agent,      # Execute PINO simulation
        baseline_analysis_agent,        # Analyze performance vs objectives
        baseline_presentation_agent,    # Present results to user
    ],
    before_agent_callback=initialize_simulation_state,
    after_agent_callback=store_baseline_results,
)

# ===================== SIMULATION PHASE WORKFLOW NOTES =====================

"""
SIMULATION PHASE WORKFLOW:

Input from Knowledge Phase:
{
  "suggested_parameters": {...validated initial parameters...},
  "user_objectives": {"max_exotherm": 3.0, "max_thermal_lag": 15.0, "min_doc": 70.0, "max_doc_gradient": 2.0},
  "autoclave_knowledge": "...comprehensive processing guidelines...",
  "processing_guidelines": {...organized knowledge...},
  "phases_complete": {"requirements": True, "knowledge": True}
}

Simulation Phase Processing:

1. initialize_simulation_state:
   - Sets current_phase = "simulation"
   - Initializes baseline tracking variables

2. baseline_simulation_agent:
   - Executes PINO simulation with suggested_parameters
   - Stores results in latest_pino_results
   - Marks baseline_executed = True

3. baseline_analysis_agent:
   - Extracts performance metrics from simulation
   - Compares against user_objectives
   - Calculates specific gaps for each objective
   - Example gaps:
     {
       "thermal_lag": {"current": 18.5, "target": 15.0, "gap": 3.5, "status": "FAIL"},
       "exotherm": {"current": 4.2, "target": 3.0, "gap": 1.2, "status": "FAIL"},
       "min_doc": {"current": 68.5, "target": 70.0, "gap": -1.5, "status": "FAIL"},
       "violations_count": 3
     }

4. baseline_presentation_agent:
   - Formats results in clear table format
   - Shows specific numerical gaps
   - Asks user about proceeding with optimization

Output to Optimization Phase:
{
  ...existing state...,
  "baseline_results": {...PINO simulation results...},
  "baseline_performance": {...performance metrics...},
  "performance_gaps": {...detailed gap analysis...},
  "baseline_simulation_complete": True,
  "phases_complete": {"requirements": True, "knowledge": True, "baseline_simulation": True},
  "recommend_optimization": True  # If objectives failed
}

Ready for iterative optimization with user approval!
"""