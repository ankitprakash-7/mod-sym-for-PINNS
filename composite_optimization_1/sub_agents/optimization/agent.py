"""
composite_optimization/sub_agents/optimization/agent.py
Optimization Phase Agents - Complete iterative optimization with user approval
Implements 3-iteration LoopAgent with user-in-the-loop approval
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
    verifier_function_tool,
    user_approval_function_tool,
    optimization_tracking_function_tool,
    WORKFLOW_FUNCTION_TOOLS
)
from composite_optimization.shared_libraries.composite_util import (
    calculate_performance_gaps,
    generate_parameter_improvements,
    format_parameter_comparison,
    parse_user_approval,
    validate_optimization_ready,
    format_optimization_summary
)
from composite_optimization import prompt

# ===================== OPTIMIZATION CALLBACK FUNCTIONS =====================

def initialize_optimization_state(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Initialize optimization loop state."""
    callback_context.state["current_phase"] = "optimization"
    callback_context.state["optimization_iteration"] = 0
    callback_context.state["max_optimization_iterations"] = 3
    callback_context.state["user_approved_next"] = False
    callback_context.state["optimization_complete"] = False
    
    # Initialize tracking
    callback_context.state["iteration_history"] = []
    callback_context.state["best_parameters"] = None
    callback_context.state["best_performance"] = None
    callback_context.state["best_violations_count"] = 999
    
    # Set initial state for first iteration
    callback_context.state["ready_for_optimization"] = True
    
    return None

def check_should_continue_optimization(
    callback_context: callback_context_module.CallbackContext,
    llm_request=None
) -> Optional[types.Content]:
    """
    Check if optimization loop should continue.
    Stops if max iterations reached OR user didn't approve.
    """
    
    current_iter = callback_context.state.get("optimization_iteration", 0)
    max_iter = callback_context.state.get("max_optimization_iterations", 3)
    
    # Always allow first iteration (iteration 0)
    if current_iter == 0:
        return None
    
    # For subsequent iterations, check user approval
    user_approved = callback_context.state.get("user_approved_next", False)
    
    # Stop if max iterations reached
    if current_iter >= max_iter:
        callback_context.state["optimization_complete"] = True
        callback_context.state["completion_reason"] = f"Maximum iterations ({max_iter}) reached"
        return types.Content(
            role='assistant',
            parts=[types.Part(text=f"🔄 Optimization complete: Maximum {max_iter} iterations reached.")]
        )
    
    # Stop if user didn't approve continuation
    if not user_approved:
        callback_context.state["optimization_complete"] = True
        callback_context.state["completion_reason"] = "User declined to continue"
        return types.Content(
            role='assistant', 
            parts=[types.Part(text="🛑 Optimization stopped: User chose not to continue.")]
        )
    
    return None

def update_optimization_iteration(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Update iteration state after each optimization cycle."""
    
    current_iter = callback_context.state.get("optimization_iteration", 0)
    
    # Store iteration results
    performance_data = callback_context.state.get("current_performance", {})
    parameters = callback_context.state.get("current_parameters", {})
    
    if performance_data and parameters:
        iteration_record = {
            "iteration": current_iter + 1,
            "parameters": parameters.copy(),
            "performance": performance_data.copy(),
            "timestamp": __import__('time').time()
        }
        
        # Update iteration history
        history = callback_context.state.get("iteration_history", [])
        history.append(iteration_record)
        callback_context.state["iteration_history"] = history
        
        # Update best results if this iteration is better
        violations_count = performance_data.get('violations_count', 999)
        best_violations = callback_context.state.get("best_violations_count", 999)
        
        if violations_count < best_violations:
            callback_context.state["best_parameters"] = parameters.copy()
            callback_context.state["best_performance"] = performance_data.copy()
            callback_context.state["best_violations_count"] = violations_count
    
    # Increment iteration counter
    callback_context.state["optimization_iteration"] = current_iter + 1
    
    # Reset user approval for next iteration
    callback_context.state["user_approved_next"] = False
    
    return None

def finalize_optimization(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Finalize optimization and mark phase complete."""
    callback_context.state["phases_complete"]["optimization"] = True
    callback_context.state["optimization_complete"] = True
    
    # Generate final summary
    final_summary = format_optimization_summary(callback_context)
    callback_context.state["final_optimization_summary"] = final_summary
    
    return None

def reset_user_approval(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Reset user approval flag for new iteration."""
    callback_context.state["user_approved_next"] = False
    return None

# ===================== OPTIMIZATION WORKFLOW TOOL FUNCTIONS =====================

def parameter_optimization_workflow_tool(
    optimization_request: str,
    tool_context: ToolContext
) -> str:
    """
    Generate optimized parameters based on performance analysis and scientific knowledge.
    
    Args:
        optimization_request: Description of optimization needs
        tool_context: ADK tool context for state management
        
    Returns:
        str: Optimized parameters with scientific reasoning
    """
    
    # Get current state
    current_parameters = tool_context.state.get("current_parameters", {})
    performance_gaps = tool_context.state.get("performance_gaps", {})
    autoclave_knowledge = tool_context.state.get("autoclave_knowledge", "")
    parameter_guidance = tool_context.state.get("parameter_guidance", {})
    
    if not current_parameters:
        return "❌ No current parameters available for optimization"
    
    if not performance_gaps:
        return "❌ No performance analysis available for optimization"
    
    # Generate parameter improvements
    improvement_result = generate_parameter_improvements(
        current_parameters, 
        performance_gaps, 
        parameter_guidance
    )
    
    improved_parameters = improvement_result["improved_parameters"]
    optimization_reasoning = improvement_result["optimization_reasoning"]
    improvements_count = improvement_result["improvements_count"]
    
    # Store recommendations in workflow state
    tool_context.state["recommended_parameters"] = improved_parameters
    tool_context.state["optimization_reasoning"] = optimization_reasoning
    tool_context.state["parameter_improvements_count"] = improvements_count
    
    return f"✅ Generated {improvements_count} parameter improvements based on performance analysis"

def user_approval_presentation_tool(
    tool_context: ToolContext
) -> str:
    """
    Present recommended parameters to user for approval.
    
    Args:
        tool_context: ADK tool context for state management
        
    Returns:
        str: Formatted parameter presentation for user approval
    """
    
    current_parameters = tool_context.state.get("current_parameters", {})
    recommended_parameters = tool_context.state.get("recommended_parameters", {})
    optimization_reasoning = tool_context.state.get("optimization_reasoning", {})
    performance_gaps = tool_context.state.get("performance_gaps", {})
    
    if not recommended_parameters:
        return "❌ No recommended parameters available for presentation"
    
    # Create comprehensive approval presentation
    presentation = "## 🎯 **OPTIMIZATION RECOMMENDATIONS**\n\n"
    
    # Show why optimization is needed
    if performance_gaps:
        failed_objectives = [k for k, v in performance_gaps.items() 
                           if k != "violations_count" and v.get("status") == "FAIL"]
        if failed_objectives:
            presentation += f"**Issues to Address**: {len(failed_objectives)} failed objectives\n"
            for obj in failed_objectives:
                gap_data = performance_gaps[obj]
                presentation += f"• {obj.replace('_', ' ').title()}: {gap_data['current']:.1f} vs {gap_data['target']:.1f} (gap: {gap_data['gap']:+.1f})\n"
            presentation += "\n"
    
    # Show parameter changes
    presentation += format_parameter_comparison(current_parameters, recommended_parameters, optimization_reasoning)
    
    # Show expected improvements
    presentation += "\n## 📈 **Expected Improvements**\n\n"
    for param, reasoning in optimization_reasoning.items():
        presentation += f"• **{param}**: {reasoning}\n"
    
    # Clear approval question
    presentation += "\n## ❓ **Approval Required**\n\n"
    presentation += "**Do you approve these parameter changes and want to run the next simulation?**\n"
    presentation += "- Say 'yes' or 'approve' to proceed\n"
    presentation += "- Say 'no' or 'stop' to end optimization\n"
    
    return presentation

def simulation_execution_workflow_tool(
    execution_context: str,
    tool_context: ToolContext
) -> str:
    """
    Execute simulation with approved parameters.
    
    Args:
        execution_context: Context for simulation execution
        tool_context: ADK tool context for state management
        
    Returns:
        str: Simulation execution results
    """
    
    # Check if user approved
    user_approved = tool_context.state.get("user_approved_next", False)
    if not user_approved:
        return "🛑 Simulation skipped - user did not approve parameters"
    
    # Get recommended parameters
    recommended_parameters = tool_context.state.get("recommended_parameters", {})
    if not recommended_parameters:
        return "❌ No recommended parameters available for simulation"
    
    # Update current parameters to recommended ones
    tool_context.state["current_parameters"] = recommended_parameters.copy()
    
    # Note: Actual simulation will be executed by pino_simulation_tool in the agent
    tool_context.state["simulation_with_new_parameters"] = True
    current_iter = tool_context.state.get("optimization_iteration", 0)
    
    return f"✅ Ready to execute simulation with optimized parameters (iteration {current_iter + 1})"

# ===================== CREATE OPTIMIZATION FUNCTION TOOLS =====================

parameter_optimization_function_tool = FunctionTool.create(parameter_optimization_workflow_tool)
user_approval_presentation_function_tool = FunctionTool.create(user_approval_presentation_tool)
simulation_execution_function_tool = FunctionTool.create(simulation_execution_workflow_tool)

# ===================== OPTIMIZATION PHASE SUB-AGENTS =====================

# Agent 1: Analyze current performance
performance_analysis_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="performance_analysis_agent",
    description="Analyze current simulation results against user objectives",
    instruction="""
You analyze current simulation performance to guide optimization.

## Your Process:
1. Use performance_analysis_tool to extract metrics from latest simulation
2. Compare against user objectives stored in workflow state
3. Calculate specific gaps for failed objectives
4. Store detailed analysis for parameter optimization

## Analysis Requirements:
- Extract exact numerical performance (thermal lag, exotherm, DOC values)
- Compare against user targets with specific gaps
- Identify which objectives passed/failed
- Prioritize issues by severity for optimization focus

## Store in Workflow State:
- current_performance: Raw performance metrics
- performance_gaps: Detailed gap analysis with pass/fail status
- optimization_priorities: Which issues to address first

This analysis drives parameter optimization decisions.
""",
    tools=[performance_analysis_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 2: Generate parameter recommendations
parameter_optimization_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="parameter_optimization_agent",
    description="Generate improved parameter recommendations with scientific reasoning",
    instruction="""
You generate ONE SET of improved parameters for the next iteration.

## Your Process:
1. Read performance_gaps and autoclave_knowledge from workflow state
2. Read current_parameters to understand starting point
3. Use parameter_optimization_tool to generate improvements
4. Use verifier_tool to validate recommended parameters
5. Store recommendations with scientific reasoning

## Optimization Strategy:
- Focus on most critical failed objectives first
- Make incremental, realistic improvements (not dramatic changes)
- Use scientific knowledge to justify each parameter change
- Ensure all parameters remain within valid ranges

## Parameter Relationships:
- **Thermal lag**: Primary control through ramp rate reduction
- **Exotherm**: Increase HTCs for better heat dissipation
- **DOC**: Extend hold times or slightly increase temperatures
- **DOC gradient**: Balance heat transfer coefficients

## Store Results:
- recommended_parameters: Improved parameter set
- optimization_reasoning: Scientific justification for each change
- expected_improvements: Quantitative predictions

Focus on ONE iteration improvement with clear reasoning.
""",
    tools=[parameter_optimization_function_tool, verifier_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.3),
)

# Agent 3: Present parameters and get user approval
user_approval_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="user_approval_agent",
    description="Present recommended parameters to user and get approval",
    instruction="""
You present parameter recommendations to user and get approval for next simulation.

## Your Process:
1. Use user_approval_presentation_tool to format parameter recommendations
2. Show clear before/after parameter comparison
3. Include scientific reasoning for each change
4. Ask explicit approval question
5. Use user_approval_tracking_tool to store user response

## Presentation Requirements:
- Clear table showing current → recommended parameters
- Scientific reasoning for each parameter change
- Expected improvement for each failed objective
- Explicit approval question

## Approval Question Format:
"**Do you approve these parameter changes and want to run the next simulation?**"
- Be clear that approval is needed to continue
- Explain consequences of approval (simulation will run)
- Make it easy for user to approve or decline

## Store User Decision:
User response controls whether optimization loop continues.
- "yes/approve/ok" → user_approved_next = True
- "no/stop/wait" → user_approved_next = False

This approval controls the optimization loop continuation.
""",
    tools=[user_approval_presentation_function_tool, user_approval_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 4: Execute simulation with approved parameters
simulation_execution_agent = agents.Agent(
    model="gemini-2.5-pro", 
    name="simulation_execution_agent",
    description="Execute PINO simulation with approved parameters",
    instruction="""
You execute simulation with user-approved parameters.

## Your Process:
1. Check user_approved_next status in workflow state
2. If approved: Use simulation_execution_tool to prepare execution
3. Use pino_simulation_tool to run PINO simulation with recommended parameters
4. Store new results in workflow state
5. Use optimization_tracking_tool to track iteration progress

## Execution Conditions:
- Only execute if user_approved_next = True
- Use recommended_parameters from workflow state
- Update current_parameters with new values
- Store results for next iteration analysis

## Communication:
- Confirm simulation execution status
- Report key performance highlights
- Note iteration progress (e.g., "Iteration 2/3 complete")
- Prepare for next iteration or completion

## Error Handling:
- Report simulation failures clearly
- Maintain workflow state consistency
- Allow for retry if needed

Focus on reliable execution and clear status reporting.
""",
    tools=[simulation_execution_function_tool, pino_simulation_function_tool, optimization_tracking_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 5: Optimization summary and final recommendations
optimization_summary_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="optimization_summary_agent",
    description="Provide final optimization summary and recommendations",
    instruction="""
You provide final optimization summary and best cure cycle recommendations.

## Your Process:
1. Read complete iteration_history from workflow state
2. Identify best_parameters and best_performance achieved
3. Compare final results with original baseline
4. Provide clear implementation recommendations

## Summary Requirements:
- Complete optimization journey overview
- Best parameters achieved with performance
- Improvement over baseline (if any)
- Clear implementation guidance
- Any remaining considerations or recommendations

## Output Format:
```
# 🎯 **Optimization Complete**

## 📊 **Final Results**
- Iterations completed: X/3
- Best performance: X violations (down from X baseline)
- Key improvements: [specific improvements achieved]

## 🏆 **Recommended Cure Cycle**
[Best parameters in clear format]

## 📈 **Performance Achieved**
[Final performance vs objectives table]

## 🚀 **Implementation Recommendations**
[Practical guidance for using these parameters]
```

Provide actionable, implementable results.
""",
    tools=[],  # No tools needed - summary only
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# ===================== OPTIMIZATION WORKFLOW STRUCTURE =====================

# Single optimization iteration (Sequential)
optimization_iteration_agent = agents.SequentialAgent(
    name="optimization_iteration_agent",
    description="One complete optimization iteration with user approval",
    sub_agents=[
        performance_analysis_agent,      # Analyze current simulation results
        parameter_optimization_agent,    # Generate improved recommendations
        user_approval_agent,            # Present to user and get approval
        simulation_execution_agent,     # Execute simulation if approved
    ],
    before_agent_callback=reset_user_approval,      # Reset approval flag each iteration
    after_agent_callback=update_optimization_iteration,  # Update iteration tracking
)

# Complete optimization phase (Loop with 3-iteration limit)
optimization_loop_agent = agents.LoopAgent(
    name="optimization_loop_agent",
    description="Iterative optimization with user approval (maximum 3 iterations)",
    sub_agents=[optimization_iteration_agent],
    max_iterations=3,  # Your requirement: maximum 3 optimization cycles
    before_agent_callback=check_should_continue_optimization,  # Check continuation conditions
)

# Complete optimization phase including final summary
optimization_phase_agent = agents.SequentialAgent(
    name="optimization_phase_agent",
    description="Complete optimization workflow with iterative improvement and final summary",
    sub_agents=[
        optimization_loop_agent,        # The 3-iteration optimization loop
        optimization_summary_agent,     # Final summary and recommendations
    ],
    before_agent_callback=initialize_optimization_state,
    after_agent_callback=finalize_optimization,
)

# ===================== OPTIMIZATION WORKFLOW EXAMPLE =====================

"""
OPTIMIZATION PHASE WORKFLOW EXECUTION:

Input from Simulation Phase:
{
  "baseline_performance": {"thermal_lag": 18.5, "exotherm_spike": 4.2, "min_doc": 0.685, ...},
  "performance_gaps": {"thermal_lag": {"status": "FAIL", "gap": 3.5}, ...},
  "current_parameters": {...baseline parameters...},
  "autoclave_knowledge": "...processing guidelines...",
  "phases_complete": {"requirements": True, "knowledge": True, "baseline_simulation": True}
}

Optimization Loop Execution (max 3 iterations):

ITERATION 1:
├── performance_analysis_agent: 
│   └── Analyzes baseline performance, identifies 3 failed objectives
├── parameter_optimization_agent:
│   └── Recommends: slower ramp rates (2.2→1.8°C/min), higher HTCs (100→115 W/m²K)
├── user_approval_agent:
│   └── Presents: "Do you approve these changes and want to run simulation?"
│   └── User: "Yes, proceed"
│   └── Stores: user_approved_next = True
└── simulation_execution_agent:
    └── Executes simulation with new parameters
    └── Results: thermal_lag improved to 16.2°C, exotherm to 3.8°C

ITERATION 2 (if user approved and violations still exist):
├── performance_analysis_agent: 
│   └── Analyzes new results, still 2 failed objectives
├── parameter_optimization_agent:
│   └── Further recommendations based on remaining issues
├── user_approval_agent:
│   └── User: "Yes, one more iteration"
└── simulation_execution_agent:
    └── Executes with iteration 2 parameters

ITERATION 3 (if user approved):
├── [Same pattern...]
└── Final iteration

FINAL SUMMARY:
optimization_summary_agent:
└── Provides complete optimization report with best parameters

FINAL OUTPUT STATE:
{
  "optimization_iteration": 3,
  "best_parameters": {...optimized cure cycle...},
  "best_performance": {"violations_count": 1},  # Improved from 3
  "iteration_history": [...complete history...],
  "phases_complete": {"requirements": True, "knowledge": True, "baseline_simulation": True, "optimization": True},
  "final_optimization_summary": "...complete report..."
}

User gets final optimized cure cycle with implementation guidance!
"""