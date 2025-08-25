"""
composite_optimization/config.py
Complete Configuration and Workflow Assembly
Self-contained configuration bringing all phases together
"""

import os
import dataclasses
from typing import Optional, List
from google.adk import agents
from google.genai import types
from google.adk.agents import callback_context as callback_context_module

# ===================== CONFIGURATION DATACLASS =====================

@dataclasses.dataclass
class CompositeOptimizationConfig:
    """Complete configuration for composite optimization workflow."""
    
    # Model settings
    agent_model: str = "gemini-2.5-pro"
    knowledge_model: str = "gemini-2.0-flash"
    root_agent_model: str = "gemini-2.5-pro"
    
    # Optimization settings
    max_optimization_iterations: int = 3
    optimization_temperature: float = 0.3
    analysis_temperature: float = 0.0
    interaction_temperature: float = 0.1
    
    # Material support
    supported_materials: List[str] = None
    
    # Workspace settings
    workspace_dir: str = "./workspace"
    project_name: str = "composite_optimization"
    save_intermediate_results: bool = True
    
    # Simulation settings
    pino_api_url: str = "http://localhost:8000"
    simulation_timeout: int = 120
    
    # Knowledge settings
    autoclave_doc_url: str = "https://drive.google.com/file/d/1T--rE4mDHEkx8dT2bzOepwP3omlE5nFY/view?usp=sharing"
    
    # Workflow settings
    enable_detailed_logging: bool = True
    save_iteration_history: bool = True
    
    def __post_init__(self):
        if self.supported_materials is None:
            self.supported_materials = ["AS4/8552", "IM7/8552"]

# Global configuration instance
CONFIG = CompositeOptimizationConfig()

# ===================== MAIN WORKFLOW ASSEMBLY =====================

def initialize_complete_workflow(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Initialize the complete workflow with all configuration and state setup."""
    
    # Load configuration into workflow state
    config_dict = dataclasses.asdict(CONFIG)
    for key, value in config_dict.items():
        callback_context.state[key] = value
    
    # Initialize workflow metadata
    callback_context.state["workflow_start_time"] = __import__('time').time()
    callback_context.state["workflow_version"] = "1.0.0"
    callback_context.state["current_phase"] = "initialization"
    
    # Initialize phase completion tracking
    callback_context.state["phases_complete"] = {
        "requirements": False,
        "knowledge": False,
        "baseline_simulation": False, 
        "optimization": False
    }
    
    # Initialize material database
    callback_context.state["material_database"] = {
        "AS4/8552": {
            "description": "Standard aerospace carbon fiber prepreg",
            "typical_cure_temp": 180.0,
            "gel_time_range": [15, 25],
            "default_htc_range": [50, 150],
            "ramp_rate_range": [1.0, 3.0],
            "hold_temp_range": [170, 190],
            "thick_part_considerations": "Reduce ramp rates by 20-30% for parts >3cm"
        },
        "IM7/8552": {
            "description": "High modulus carbon fiber prepreg",
            "typical_cure_temp": 180.0,
            "gel_time_range": [12, 20], 
            "default_htc_range": [60, 140],
            "ramp_rate_range": [0.8, 2.5],
            "hold_temp_range": [170, 190],
            "thick_part_considerations": "Very conservative ramp rates needed, extend hold times"
        }
    }
    
    # Initialize workflow state tracking
    callback_context.state["user_objectives"] = {}
    callback_context.state["material_specs"] = {}
    callback_context.state["missing_requirements"] = []
    callback_context.state["requirements_complete"] = False
    
    # Initialize optimization tracking
    callback_context.state["optimization_iteration"] = 0
    callback_context.state["best_parameters"] = None
    callback_context.state["best_performance"] = None
    callback_context.state["iteration_history"] = []
    callback_context.state["best_violations_count"] = 999
    
    # Set workflow ready flag
    callback_context.state["workflow_initialized"] = True
    
    return None

def save_complete_workflow_state(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Save complete workflow state and generate final implementation report."""
    
    workspace_dir = callback_context.state.get("workspace_dir", "./workspace")
    project_name = callback_context.state.get("project_name", "composite_optimization")
    
    # Create workspace directory
    run_cwd = os.path.join(workspace_dir, project_name)
    os.makedirs(run_cwd, exist_ok=True)
    
    # Save complete workflow state
    with open(os.path.join(run_cwd, "complete_workflow_state.json"), "w") as f:
        import json
        json.dump(callback_context.state.to_dict(), f, indent=2)
    
    # Save best cure cycle parameters
    best_parameters = callback_context.state.get("best_parameters")
    if best_parameters:
        with open(os.path.join(run_cwd, "optimized_cure_cycle.json"), "w") as f:
            json.dump(best_parameters, f, indent=2)
        
        # Also save in human-readable format
        with open(os.path.join(run_cwd, "cure_cycle_parameters.txt"), "w") as f:
            f.write("OPTIMIZED CURE CYCLE PARAMETERS\n")
            f.write("=" * 40 + "\n\n")
            
            param_names = {
                "ramp1": "Heating rate 1 (°C/min)",
                "ramp2": "Heating rate 2 (°C/min)",
                "hold_temp1": "Hold temperature 1 (°C)",
                "hold_temp2": "Hold temperature 2 (°C)",
                "hold_duration1": "Hold duration 1 (min)",
                "hold_duration2": "Hold duration 2 (min)",
                "htc_top": "Heat transfer coefficient top (W/m²K)",
                "htc_bottom": "Heat transfer coefficient bottom (W/m²K)",
                "tool_thickness": "Tool thickness (cm)"
            }
            
            for param_key, display_name in param_names.items():
                if param_key in best_parameters:
                    value = best_parameters[param_key]
                    if param_key == "tool_thickness":
                        value = value * 100  # Convert back to cm
                    f.write(f"{display_name}: {value}\n")
    
    # Save optimization history
    iteration_history = callback_context.state.get("iteration_history", [])
    if iteration_history:
        with open(os.path.join(run_cwd, "optimization_history.json"), "w") as f:
            json.dump(iteration_history, f, indent=2)
    
    # Generate workflow completion summary
    workflow_end_time = __import__('time').time()
    workflow_start_time = callback_context.state.get("workflow_start_time", workflow_end_time)
    duration = workflow_end_time - workflow_start_time
    
    phases_complete = callback_context.state.get("phases_complete", {})
    completed_phases = sum(phases_complete.values())
    total_phases = len(phases_complete)
    
    optimization_iterations = callback_context.state.get("optimization_iteration", 0)
    final_violations = callback_context.state.get("best_violations_count", 999)
    
    completion_summary = {
        "workflow_duration_seconds": duration,
        "phases_completed": f"{completed_phases}/{total_phases}",
        "optimization_iterations_completed": optimization_iterations,
        "final_objective_violations": final_violations,
        "workflow_success": completed_phases >= 3,  # At least requirements, knowledge, simulation
        "optimization_attempted": optimization_iterations > 0,
        "performance_improved": final_violations < 999
    }
    
    callback_context.state["workflow_completion_summary"] = completion_summary
    
    # Save summary report
    with open(os.path.join(run_cwd, "workflow_summary.json"), "w") as f:
        json.dump(completion_summary, f, indent=2)
    
    return None

# ===================== IMPORT ALL PHASE AGENTS =====================

# Import phase agents from their respective modules
from composite_optimization.sub_agents.requirements.agent import requirements_phase_agent
from composite_optimization.sub_agents.knowledge.agent import knowledge_phase_agent  
from composite_optimization.sub_agents.simulation.agent import baseline_simulation_phase_agent
from composite_optimization.sub_agents.optimization.agent import optimization_phase_agent

# Import prompts
from composite_optimization import prompt

# ===================== COMPLETE WORKFLOW PIPELINE =====================

composite_optimization_pipeline = agents.SequentialAgent(
    name="composite_optimization_pipeline",
    description="Complete composite cure cycle optimization workflow with user interaction",
    sub_agents=[
        requirements_phase_agent,           # Phase 1: Conversational requirements gathering
        knowledge_phase_agent,             # Phase 2: URL-based RAG knowledge retrieval
        baseline_simulation_phase_agent,   # Phase 3: Initial PINO simulation & analysis
        optimization_phase_agent,          # Phase 4: 3-iteration user-approved optimization
    ],
    before_agent_callback=initialize_complete_workflow,
    after_agent_callback=save_complete_workflow_state,
)

# ===================== ROOT AGENT FOR ADK COMPATIBILITY =====================

root_agent = agents.Agent(
    model=os.getenv("ROOT_AGENT_MODEL", CONFIG.root_agent_model),
    name="composite_optimization_frontdoor_agent",
    instruction=prompt.FRONTDOOR_INSTRUCTION,
    global_instruction=prompt.SYSTEM_INSTRUCTION,
    sub_agents=[composite_optimization_pipeline],
    generate_content_config=types.GenerateContentConfig(temperature=CONFIG.interaction_temperature),
    description="Frontdoor agent for composite cure cycle optimization workflow system"
)

# ===================== WORKFLOW EXECUTION EXAMPLE =====================

"""
COMPLETE WORKFLOW EXECUTION EXAMPLE:

USER INPUT:
"I need to design a cure cycle for a thick AS4/8552 carbon fiber part. It's about 4cm thick and I'm concerned about exotherm and thermal gradients."

FOLLOW-UP USER INPUT:
"I need an exotherm under 3°C, thermal lag under 15°C, and minimum 70% cure. The tool is 2.5cm aluminum."

COMPLETE WORKFLOW EXECUTION:

┌─ PHASE 1: REQUIREMENTS ─┐
│ ├── conversational_input_agent        │ Parses: "AS4/8552", "4cm thick", exotherm/thermal concerns
│ ├── requirement_clarification_agent   │ Asks: "What specific limits?" → Gets: "3°C, 15°C, 70%, 2.5cm aluminum"
│ ├── material_selection_agent          │ Sets: AS4/8552 properties, thick part considerations
│ ├── parameter_suggestion_agent        │ Generates: Conservative parameters for 4cm thick part
│ └── objective_validation_agent        │ Validates: All requirements complete
└─ PHASE 1 COMPLETE ─┘

State after Phase 1:
{
  "user_objectives": {"max_exotherm": 3.0, "max_thermal_lag": 15.0, "min_doc": 70.0, "max_doc_gradient": 2.0},
  "material_specs": {"material_type": "AS4/8552", "part_thickness": 4.0, "tool_material": "aluminum", "tool_thickness": 2.5},
  "suggested_parameters": {"ramp1": 1.8, "ramp2": 1.2, "hold_temp1": 115, "hold_temp2": 180, "hold_duration1": 60, "hold_duration2": 150, "htc_top": 100, "htc_bottom": 85, "tool_thickness": 0.025},
  "phases_complete": {"requirements": True}
}

┌─ PHASE 2: KNOWLEDGE ─┐
│ ├── document_retrieval_agent          │ Extracts: Autoclave processing guidelines (exotherm + thermal lag focus)
│ └── knowledge_synthesis_agent         │ Organizes: Processing guidelines, parameter relationships
└─ PHASE 2 COMPLETE ─┘

State after Phase 2:
{
  ...existing...,
  "autoclave_knowledge": "...comprehensive guidelines...",
  "processing_guidelines": {"exotherm": {...}, "thermal_lag": {...}, "thick_parts": {...}},
  "parameter_guidance": {"exotherm": {...}, "thermal_lag": {...}},
  "phases_complete": {"requirements": True, "knowledge": True}
}

┌─ PHASE 3: BASELINE SIMULATION ─┐
│ ├── baseline_simulation_agent         │ Executes: PINO simulation with suggested parameters
│ ├── baseline_analysis_agent           │ Analyzes: Performance vs objectives (finds 3 violations)
│ └── baseline_presentation_agent       │ Presents: "Thermal lag 18.5°C vs 15°C, proceed with optimization?"
└─ PHASE 3 COMPLETE ─┘

State after Phase 3:
{
  ...existing...,
  "baseline_results": {...PINO results...},
  "performance_gaps": {"thermal_lag": {"current": 18.5, "target": 15.0, "gap": 3.5, "status": "FAIL"}, ...},
  "baseline_analysis_summary": "3/4 objectives failed",
  "phases_complete": {"requirements": True, "knowledge": True, "baseline_simulation": True}
}

┌─ PHASE 4: OPTIMIZATION (LoopAgent, max 3 iterations) ─┐
│ 
│ ITERATION 1:
│ ├── performance_analysis_agent        │ Analyzes: Current performance gaps
│ ├── parameter_optimization_agent      │ Recommends: ramp1: 1.8→1.5, htc_top: 100→115
│ ├── user_approval_agent              │ Presents: Parameter changes → User: "Yes, proceed"
│ └── simulation_execution_agent       │ Executes: Simulation with improved parameters
│ 
│ ITERATION 2 (if user approved and violations remain):
│ ├── performance_analysis_agent        │ Analyzes: Improved results (2 violations remaining)
│ ├── parameter_optimization_agent      │ Recommends: Further refinements
│ ├── user_approval_agent              │ User: "Yes, one more try"
│ └── simulation_execution_agent       │ Executes: Second optimization
│ 
│ ITERATION 3 (if user approved):
│ ├── [Same pattern continues...]
│ └── Final iteration
│ 
│ ├── optimization_summary_agent        │ Provides: Complete optimization report
└─ PHASE 4 COMPLETE ─┘

FINAL STATE:
{
  "optimization_iteration": 3,
  "best_parameters": {...final optimized cure cycle...},
  "best_performance": {"violations_count": 1},  # Improved from 3
  "iteration_history": [...complete optimization journey...],
  "phases_complete": {"requirements": True, "knowledge": True, "baseline_simulation": True, "optimization": True},
  "workflow_completion_summary": {...final metrics...}
}

USER RECEIVES:
- Optimized cure cycle parameters ready for implementation
- Complete performance analysis showing improvements
- Scientific justification for all parameter choices
- Implementation guidance and recommendations
"""

# ===================== COMPLETE WORKFLOW SYSTEM =====================

# This is the complete workflow system structure
def create_complete_workflow():
    """Create the complete composite optimization workflow system."""
    
    # Import all phase agents
    from composite_optimization.sub_agents.requirements.agent import requirements_phase_agent
    from composite_optimization.sub_agents.knowledge.agent import knowledge_phase_agent  
    from composite_optimization.sub_agents.simulation.agent import baseline_simulation_phase_agent
    from composite_optimization.sub_agents.optimization.agent import optimization_phase_agent
    
    # Create main pipeline
    pipeline = agents.SequentialAgent(
        name="composite_optimization_pipeline",
        description="Complete composite cure cycle optimization workflow",
        sub_agents=[
            requirements_phase_agent,           # Conversational requirements
            knowledge_phase_agent,             # URL-based RAG knowledge
            baseline_simulation_phase_agent,   # Initial simulation & analysis
            optimization_phase_agent,          # 3-iteration optimization loop
        ],
        before_agent_callback=initialize_complete_workflow,
        after_agent_callback=save_complete_workflow_state,
    )
    
    # Create root agent
    root = agents.Agent(
        model=os.getenv("ROOT_AGENT_MODEL", CONFIG.root_agent_model),
        name="composite_optimization_frontdoor_agent",
        instruction=prompt.FRONTDOOR_INSTRUCTION,
        global_instruction=prompt.SYSTEM_INSTRUCTION,
        sub_agents=[pipeline],
        generate_content_config=types.GenerateContentConfig(temperature=CONFIG.interaction_temperature),
        description="Composite cure cycle optimization expert with workflow-based multi-agent system"
    )
    
    return root

# Create the complete system
composite_optimization_root_agent = create_complete_workflow()

# For ADK compatibility, export as root_agent
root_agent = composite_optimization_root_agent

# ===================== DEPLOYMENT AND USAGE INSTRUCTIONS =====================

"""
DEPLOYMENT INSTRUCTIONS:

1. **Directory Structure Setup**:
   ```
   composite_optimization/
   ├── agent.py                     # Main workflow (from first artifact)
   ├── prompt.py                    # All prompts (from prompt artifact)  
   ├── config.py                    # This configuration file
   ├── shared_libraries/
   │   ├── __init__.py
   │   ├── composite_util.py        # Utilities (from composite_util artifact)
   │   └── function_wrappers.py     # Function tools (from function_wrappers artifact)
   └── sub_agents/
       ├── __init__.py
       ├── requirements/
       │   ├── __init__.py
       │   └── agent.py            # Requirements agents (from requirements artifact)
       ├── knowledge/
       │   ├── __init__.py  
       │   └── agent.py            # Knowledge agents (from knowledge artifact)
       ├── simulation/
       │   ├── __init__.py
       │   └── agent.py            # Simulation agents (from simulation artifact)
       └── optimization/
           ├── __init__.py
           └── agent.py            # Optimization agents (from optimization artifact)
   ```

2. **Environment Variables**:
   ```bash
   export ROOT_AGENT_MODEL="gemini-2.5-pro"
   export PINO_API_URL="http://localhost:8000"  # Your PINO service URL
   export WORKSPACE_DIR="./workspace"
   ```

3. **Dependencies**:
   ```bash
   pip install google-adk
   pip install requests
   pip install PyMuPDF  # For PDF processing (optional - has fallbacks)
   ```

4. **Usage**:
   ```python
   from google.adk.runner import Runner
   from google.adk.sessions import InMemorySessionService
   from composite_optimization.config import root_agent
   
   # Create session and runner
   session_service = InMemorySessionService()
   session = await session_service.create_session(
       app_name="composite_optimization", 
       user_id="user1", 
       session_id="session1"
   )
   
   runner = Runner(
       agent=root_agent, 
       app_name="composite_optimization",
       session_service=session_service
   )
   
   # Run workflow
   user_query = "I need to design a cure cycle for a thick AS4/8552 carbon fiber part..."
   content = types.Content(role='user', parts=[types.Part(text=user_query)])
   
   events = runner.run_async(
       user_id="user1", 
       session_id="session1", 
       new_message=content
   )
   
   async for event in events:
       if event.is_final_response():
           print("System:", event.content.parts[0].text)
   ```

ADVANTAGES OVER CURRENT LLMAGENT SYSTEM:

✅ **Clear Separation of Concerns**: Each agent has single responsibility
✅ **Automatic State Management**: No global variables, proper workflow state
✅ **Built-in Flow Control**: SequentialAgent and LoopAgent handle orchestration
✅ **User Interaction Integration**: Dedicated approval agents with state control
✅ **Error Handling**: Validation at each phase boundary
✅ **Easier Testing**: Test individual agents and phases independently
✅ **Better Maintainability**: Clear module boundaries and dependencies
✅ **Scalable Architecture**: Easy to add new phases or modify existing ones
✅ **Professional Workflow**: Follows ML engineering reference patterns

MIGRATION BENEFITS:

- Replace manual orchestration with automatic workflow control
- Replace global state with proper workflow state management  
- Replace embedded user interaction with dedicated approval agents
- Replace complex single-agent logic with clean phase separation
- Better error recovery and debugging capabilities
- Professional multi-agent architecture following Google ADK best practices
"""