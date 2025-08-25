"""
composite_optimization/agent.py
Main Composite Optimization Workflow Agent - Entry Point
Complete self-contained workflow system with no external dependencies
"""

import os
import json
from typing import Optional
from google.genai import types
from google.adk.agents import callback_context as callback_context_module
from google.adk import agents

# Import all phase agents from the new workflow structure
from composite_optimization.sub_agents.requirements.agent import requirements_phase_agent
from composite_optimization.sub_agents.knowledge.agent import knowledge_phase_agent
from composite_optimization.sub_agents.simulation.agent import baseline_simulation_phase_agent
from composite_optimization.sub_agents.optimization.agent import optimization_phase_agent

# Import configuration and prompts
from composite_optimization import prompt
from composite_optimization.config import CONFIG

# ===================== MAIN WORKFLOW CALLBACKS =====================

def initialize_composite_workflow(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Initialize the complete composite optimization workflow."""
    
    # Load configuration into workflow state
    import dataclasses
    config_dict = dataclasses.asdict(CONFIG)
    for key, value in config_dict.items():
        callback_context.state[key] = value
    
    # Initialize workflow metadata
    callback_context.state["workflow_start_time"] = __import__('time').time()
    callback_context.state["workflow_version"] = "1.0.0"
    callback_context.state["system_type"] = "composite_cure_cycle_optimization"
    callback_context.state["current_phase"] = "initialization"
    
    # Initialize phase completion tracking
    callback_context.state["phases_complete"] = {
        "requirements": False,
        "knowledge": False,
        "baseline_simulation": False,
        "optimization": False
    }
    
    # Initialize core workflow state
    callback_context.state["user_objectives"] = {}
    callback_context.state["material_specs"] = {}
    callback_context.state["missing_requirements"] = []
    callback_context.state["requirements_complete"] = False
    
    # Initialize optimization tracking
    callback_context.state["optimization_iteration"] = 0
    callback_context.state["max_optimization_iterations"] = 3
    callback_context.state["best_parameters"] = None
    callback_context.state["best_performance"] = None
    callback_context.state["iteration_history"] = []
    callback_context.state["best_violations_count"] = 999
    
    # Initialize material database
    callback_context.state["supported_materials"] = CONFIG.supported_materials
    callback_context.state["material_database"] = {
        "AS4/8552": {
            "description": "Standard aerospace carbon fiber prepreg",
            "typical_cure_temp": 180.0,
            "gel_time_range": [15, 25],
            "default_htc_range": [50, 150],
            "ramp_rate_range": [1.0, 3.0],
            "hold_temp_range": [170, 190],
            "thick_part_considerations": "Reduce ramp rates 20-30% for parts >3cm, extend hold times"
        },
        "IM7/8552": {
            "description": "High modulus carbon fiber prepreg",
            "typical_cure_temp": 180.0,
            "gel_time_range": [12, 20],
            "default_htc_range": [60, 140],
            "ramp_rate_range": [0.8, 2.5],
            "hold_temp_range": [170, 190],
            "thick_part_considerations": "Very conservative ramp rates needed, significant hold time extension"
        }
    }
    
    # Set workflow ready flag
    callback_context.state["workflow_initialized"] = True
    
    return None

def save_workflow_state(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Save complete workflow state and generate final report."""
    
    workspace_dir = callback_context.state.get("workspace_dir", "./workspace")
    project_name = callback_context.state.get("project_name", "composite_optimization")
    
    # Create workspace directory
    run_cwd = os.path.join(workspace_dir, project_name)
    os.makedirs(run_cwd, exist_ok=True)
    
    # Save complete workflow state
    with open(os.path.join(run_cwd, "workflow_state.json"), "w") as f:
        json.dump(callback_context.state.to_dict(), f, indent=2)
    
    # Save best cure cycle if optimization completed
    best_parameters = callback_context.state.get("best_parameters")
    if best_parameters:
        # Save in JSON format
        with open(os.path.join(run_cwd, "optimized_cure_cycle.json"), "w") as f:
            json.dump(best_parameters, f, indent=2)
        
        # Save in human-readable format
        with open(os.path.join(run_cwd, "cure_cycle_implementation.txt"), "w") as f:
            f.write("OPTIMIZED CURE CYCLE PARAMETERS\n")
            f.write("=" * 50 + "\n\n")
            f.write("Implementation-ready cure cycle parameters:\n\n")
            
            param_display = {
                "ramp1": "Initial heating rate (°C/min)",
                "hold_temp1": "First hold temperature (°C)",
                "hold_duration1": "First hold duration (min)",
                "ramp2": "Final heating rate (°C/min)",
                "hold_temp2": "Final hold temperature (°C)",
                "hold_duration2": "Final hold duration (min)",
                "htc_top": "Top surface heat transfer coefficient (W/m²K)",
                "htc_bottom": "Bottom surface heat transfer coefficient (W/m²K)",
                "tool_thickness": "Tool thickness (m)"
            }
            
            for param_key, description in param_display.items():
                if param_key in best_parameters:
                    value = best_parameters[param_key]
                    f.write(f"{description}: {value}\n")
            
            # Add implementation notes
            f.write(f"\nImplementation Notes:\n")
            f.write(f"- Material: {callback_context.state.get('material_specs', {}).get('material_type', 'N/A')}\n")
            f.write(f"- Part thickness: {callback_context.state.get('material_specs', {}).get('part_thickness', 'N/A')} cm\n")
            f.write(f"- Tool: {callback_context.state.get('material_specs', {}).get('tool_material', 'N/A')}\n")
            f.write(f"- Optimization iterations: {callback_context.state.get('optimization_iteration', 0)}\n")
            f.write(f"- Final violations: {callback_context.state.get('best_violations_count', 'N/A')}\n")
    
    # Save optimization history
    iteration_history = callback_context.state.get("iteration_history", [])
    if iteration_history:
        with open(os.path.join(run_cwd, "optimization_history.json"), "w") as f:
            json.dump(iteration_history, f, indent=2)
    
    # Generate and save final report
    workflow_summary = generate_final_workflow_report(callback_context)
    callback_context.state["final_workflow_report"] = workflow_summary
    
    with open(os.path.join(run_cwd, "final_report.md"), "w") as f:
        f.write(workflow_summary)
    
    return None

def generate_final_workflow_report(callback_context: callback_context_module.CallbackContext) -> str:
    """Generate comprehensive final workflow report."""
    
    # Get workflow timing
    start_time = callback_context.state.get("workflow_start_time", 0)
    end_time = __import__('time').time()
    duration = end_time - start_time
    
    # Get completion status
    phases_complete = callback_context.state.get("phases_complete", {})
    completed_phases = sum(phases_complete.values())
    total_phases = len(phases_complete)
    
    # Get optimization results
    optimization_iterations = callback_context.state.get("optimization_iteration", 0)
    baseline_violations = 999
    final_violations = callback_context.state.get("best_violations_count", 999)
    
    # Get user requirements
    user_objectives = callback_context.state.get("user_objectives", {})
    material_specs = callback_context.state.get("material_specs", {})
    
    report = f"""# 🎯 Composite Cure Cycle Optimization - Final Report

## 📋 **Project Summary**
- **Material**: {material_specs.get('material_type', 'N/A')} ({material_specs.get('part_thickness', 'N/A')}cm thick)
- **Tool**: {material_specs.get('tool_material', 'N/A')} ({material_specs.get('tool_thickness', 'N/A')}cm)
- **Objectives**: {len(user_objectives)} performance targets specified

## ⏱️ **Workflow Execution**
- **Duration**: {duration:.1f} seconds
- **Phases Completed**: {completed_phases}/{total_phases}
- **Optimization Iterations**: {optimization_iterations}/3

## 🎯 **User Objectives**
"""
    
    for obj_name, obj_value in user_objectives.items():
        symbol = "≤" if "max_" in obj_name else "≥"
        units = "°C" if "temp" in obj_name or "lag" in obj_name or "exotherm" in obj_name else "%"
        report += f"- **{obj_name.replace('_', ' ').title()}**: {symbol} {obj_value}{units}\n"
    
    report += f"""
## 📊 **Optimization Results**
- **Baseline Violations**: {baseline_violations if baseline_violations < 999 else 'N/A'}
- **Final Violations**: {final_violations if final_violations < 999 else 'N/A'}
- **Improvement**: {'Yes' if final_violations < baseline_violations else 'No significant improvement'}

## 🏆 **Best Parameters Achieved**
"""
    
    best_parameters = callback_context.state.get("best_parameters", {})
    if best_parameters:
        param_display = {
            "ramp1": "Initial heating rate (°C/min)",
            "ramp2": "Final heating rate (°C/min)",
            "hold_temp1": "First hold temperature (°C)",
            "hold_temp2": "Final hold temperature (°C)",
            "hold_duration1": "First hold duration (min)",
            "hold_duration2": "Final hold duration (min)",
            "htc_top": "Top HTC (W/m²K)",
            "htc_bottom": "Bottom HTC (W/m²K)"
        }
        
        for param_key, description in param_display.items():
            if param_key in best_parameters:
                value = best_parameters[param_key]
                report += f"- **{description}**: {value:.1f}\n"
    else:
        report += "- No optimized parameters available\n"
    
    report += f"""
## ✅ **Phase Completion Status**
"""
    
    phase_descriptions = {
        "requirements": "Conversational requirements gathering",
        "knowledge": "Autoclave processing knowledge retrieval",
        "baseline_simulation": "Initial PINO simulation and analysis", 
        "optimization": "Iterative parameter optimization"
    }
    
    for phase, completed in phases_complete.items():
        status = "✅ Complete" if completed else "❌ Incomplete"
        description = phase_descriptions.get(phase, phase)
        report += f"- **{description}**: {status}\n"
    
    report += f"""
## 🚀 **Implementation Recommendations**

{'### Optimized Parameters Ready for Implementation' if best_parameters else '### Baseline Parameters Available'}

{'Use the optimized cure cycle parameters saved in optimized_cure_cycle.json' if best_parameters else 'Complete the optimization process to get improved parameters'}

### Process Control Recommendations:
- Monitor actual part temperatures during cure (not just programmed temperatures)
- Validate heat transfer coefficients match your specific autoclave setup
- Consider process validation runs before production implementation
- Track degree of cure with DSC or DMA if possible

### Quality Assurance:
- Verify thermal lag stays within specified limits during actual cure
- Monitor for exothermic temperature spikes
- Validate final part cure state meets minimum DOC requirements
- Check cure uniformity across part thickness

## 📞 **System Information**
- **Workflow Version**: {callback_context.state.get('workflow_version', '1.0.0')}
- **Supported Materials**: {', '.join(CONFIG.supported_materials)}
- **Maximum Optimization Iterations**: {CONFIG.max_optimization_iterations}
- **Knowledge Source**: Autoclave processing technical literature

---
*Generated by Composite Cure Cycle Optimization Workflow System*
"""
    
    return report

# ===================== MAIN WORKFLOW PIPELINE =====================

composite_optimization_pipeline = agents.SequentialAgent(
    name="composite_optimization_pipeline",
    description="Complete composite cure cycle optimization workflow with user interaction",
    sub_agents=[
        requirements_phase_agent,           # Phase 1: Parse conversational requirements
        knowledge_phase_agent,             # Phase 2: Extract autoclave processing knowledge  
        baseline_simulation_phase_agent,   # Phase 3: Run initial PINO simulation
        optimization_phase_agent,          # Phase 4: 3-iteration user-approved optimization
    ],
    before_agent_callback=initialize_composite_workflow,
    after_agent_callback=save_workflow_state,
)

# ===================== ROOT AGENT (ADK COMPATIBILITY) =====================

root_agent = agents.Agent(
    model=os.getenv("ROOT_AGENT_MODEL", CONFIG.root_agent_model),
    name="composite_optimization_frontdoor_agent",
    instruction=prompt.FRONTDOOR_INSTRUCTION,
    global_instruction=prompt.SYSTEM_INSTRUCTION,
    sub_agents=[composite_optimization_pipeline],
    generate_content_config=types.GenerateContentConfig(temperature=CONFIG.interaction_temperature),
    description="Expert system for composite cure cycle optimization using workflow-based multi-agent architecture"
)

# ===================== COMPLETE SYSTEM OVERVIEW =====================

"""
COMPLETE COMPOSITE OPTIMIZATION WORKFLOW SYSTEM

## 🏗️ **Architecture Overview**

This system transforms your original LlmAgent-based approach into a professional 
workflow-based multi-agent system following Google ADK best practices.

### **System Capabilities:**
✅ Parse conversational requirements: "exotherm under 3°C, thermal lag under 15°C..."
✅ Support multiple materials: AS4/8552, IM7/8552
✅ URL-based RAG knowledge retrieval from autoclave processing documents
✅ PINO neural PDE simulation for thermal-chemical analysis
✅ Iterative optimization with user approval (max 3 iterations)
✅ Science-based parameter recommendations with technical justification

### **Workflow Phases:**

**Phase 1 - Requirements Gathering:**
- Conversational input parsing
- Clarification of missing information
- Material selection and properties
- Parameter suggestion and validation

**Phase 2 - Knowledge Processing:**
- Document retrieval from autoclave processing literature
- Knowledge synthesis focused on user's specific concerns
- Organization of processing guidelines and parameter relationships

**Phase 3 - Baseline Simulation:**
- Initial PINO simulation with suggested parameters
- Performance analysis against user objectives
- Gap identification and optimization planning

**Phase 4 - Iterative Optimization:**
- Performance analysis of current results
- Science-based parameter recommendations
- User approval for each iteration
- Simulation execution with improved parameters
- Up to 3 iterations with user control

### **Key Workflow Features:**

🔄 **Automatic Flow Control**: SequentialAgent and LoopAgent manage execution
📊 **State Management**: Professional workflow state (no global variables)
👤 **User-in-the-Loop**: Dedicated approval agents control optimization progression
🧠 **Knowledge Integration**: RAG-based scientific reasoning for all recommendations
🔬 **Neural PDE Simulation**: PINO model integration for accurate thermal-chemical modeling
📈 **Iterative Improvement**: Controlled optimization with performance tracking

### **Advantages Over Original LlmAgent System:**

✅ **Better Architecture**: Clear separation of concerns vs monolithic agents
✅ **Professional State Management**: Workflow state vs global variables
✅ **Automatic Flow Control**: Built-in orchestration vs manual coordination
✅ **Better User Experience**: Dedicated interaction agents vs embedded logic
✅ **Easier Maintenance**: Modular design vs complex single-agent instructions
✅ **Better Testing**: Independent agent testing vs full system testing
✅ **Scalable Design**: Easy to extend vs monolithic modification
✅ **Error Recovery**: Phase-level validation vs agent-level error handling

### **Usage Example:**

```python
# Initialize system
from composite_optimization.config import root_agent
from google.adk.runner import Runner
from google.adk.sessions import InMemorySessionService

# Create session
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name="composite_optimization", session_service=session_service)

# User interaction
user_input = "I need to design a cure cycle for a thick AS4/8552 carbon fiber part. It's about 4cm thick and I'm concerned about exotherm and thermal gradients."

# Execute workflow
events = runner.run_async(user_id="user1", session_id="session1", new_message=content)
```

### **Output Files Generated:**
- `workflow_state.json`: Complete workflow state
- `optimized_cure_cycle.json`: Final optimized parameters
- `cure_cycle_implementation.txt`: Human-readable implementation guide
- `optimization_history.json`: Complete iteration history
- `final_report.md`: Comprehensive optimization report

This provides a complete, professional workflow system for composite cure cycle optimization
with user-friendly interaction and science-based recommendations.
"""

# ===================== DIRECTORY STRUCTURE REFERENCE =====================

"""
COMPLETE FILE STRUCTURE:

composite_optimization/
├── agent.py                                    # This file - Main workflow entry point
├── prompt.py                                   # All instruction templates  
├── config.py                                   # Configuration and workflow assembly
├── __init__.py                                 # Package initialization
├── shared_libraries/
│   ├── __init__.py
│   ├── composite_util.py                       # Workflow utilities and helpers
│   └── function_wrappers.py                    # Function tool implementations
└── sub_agents/
    ├── __init__.py
    ├── requirements/
    │   ├── __init__.py
    │   └── agent.py                            # Requirements gathering agents
    ├── knowledge/
    │   ├── __init__.py
    │   └── agent.py                            # Knowledge retrieval and synthesis agents
    ├── simulation/
    │   ├── __init__.py
    │   └── agent.py                            # Baseline simulation agents
    └── optimization/
        ├── __init__.py
        └── agent.py                            # Iterative optimization agents

DEPLOYMENT:
1. Create this directory structure
2. Copy each artifact content to corresponding file
3. Set environment variables (ROOT_AGENT_MODEL, PINO_API_URL)
4. Install dependencies (google-adk, requests, PyMuPDF)
5. Run with ADK Runner

The system is completely self-contained with no external dependencies beyond ADK and PINO API.
"""