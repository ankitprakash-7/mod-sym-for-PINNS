"""
composite_optimization/sub_agents/requirements/agent.py
Requirements Phase Agents - Self-contained implementation
Handles conversational requirement gathering with no external dependencies
"""

from google.adk import agents
from google.genai import types
from google.adk.agents import callback_context as callback_context_module
from google.adk.tools import FunctionTool, ToolContext
from typing import Optional, Dict, Any

# Import from new workflow structure only
from composite_optimization.shared_libraries.function_wrappers import (
    conversational_parser_function_tool,
    intelligent_parameter_suggestion_function_tool,
    verifier_function_tool,
    WORKFLOW_FUNCTION_TOOLS
)
from composite_optimization.shared_libraries.composite_util import (
    validate_requirements_complete,
    format_parameters_for_display,
    get_material_properties
)
from composite_optimization import prompt

# ===================== REQUIREMENTS PHASE CALLBACK FUNCTIONS =====================

def initialize_requirements_state(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Initialize state for requirements gathering phase."""
    callback_context.state["current_phase"] = "requirements"
    callback_context.state["user_objectives"] = {}
    callback_context.state["material_specs"] = {}
    callback_context.state["missing_requirements"] = []
    callback_context.state["requirements_complete"] = False
    callback_context.state["parameters_suggested"] = False
    
    # Initialize supported materials
    callback_context.state["supported_materials"] = ["AS4/8552", "IM7/8552"]
    
    return None

def check_requirements_complete(
    callback_context: callback_context_module.CallbackContext,
    llm_request=None
) -> Optional[types.Content]:
    """Check if requirements gathering can be skipped."""
    
    if validate_requirements_complete(callback_context):
        callback_context.state["requirements_complete"] = True
        # Skip clarification if already complete
        return types.Content(
            role='assistant',
            parts=[types.Part(text="✅ Requirements already complete - skipping clarification")]
        )
    
    return None

def prepare_parameter_suggestion(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Prepare data for parameter suggestion."""
    
    # Combine material specs and objectives for parameter suggestion
    material_specs = callback_context.state.get("material_specs", {})
    user_objectives = callback_context.state.get("user_objectives", {})
    
    # Create context for parameter suggestion
    suggestion_context = {**material_specs, **user_objectives}
    callback_context.state["suggestion_context"] = suggestion_context
    
    return None

def validate_suggested_parameters(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Validate that parameters were successfully suggested and validated."""
    
    if not callback_context.state.get("parameters_valid", False):
        return types.Content(
            role='assistant',
            parts=[types.Part(text="❌ Parameter validation failed. Need to regenerate suggestions.")]
        )
    
    callback_context.state["parameters_suggested"] = True
    callback_context.state["phases_complete"]["requirements"] = True
    return None

def check_material_selection_needed(
    callback_context: callback_context_module.CallbackContext,
    llm_request=None
) -> Optional[types.Content]:
    """Check if material selection is needed."""
    
    material_specs = callback_context.state.get("material_specs", {})
    if "material_type" not in material_specs:
        return None  # Let material selection agent handle it
    
    # Material already specified, skip to parameter suggestion
    return types.Content(
        role='assistant',
        parts=[types.Part(text=f"✅ Material type already specified: {material_specs['material_type']}")]
    )

# ===================== REQUIREMENT WORKFLOW TOOL FUNCTIONS =====================

def requirement_update_workflow_tool(
    clarified_info: Dict[str, Any],
    tool_context: ToolContext
) -> str:
    """
    Update workflow state with clarified requirement information.
    
    Args:
        clarified_info: Dictionary with clarified requirements
        tool_context: ADK tool context for state management
        
    Returns:
        str: Confirmation of updated requirements
    """
    
    # Update existing state
    current_objectives = tool_context.state.get("user_objectives", {})
    current_specs = tool_context.state.get("material_specs", {})
    missing_reqs = tool_context.state.get("missing_requirements", [])
    
    # Update with clarified information
    for key, value in clarified_info.items():
        if key in ["max_exotherm", "max_thermal_lag", "min_doc", "max_doc_gradient"]:
            current_objectives[key] = value
            if key in missing_reqs:
                missing_reqs.remove(key)
        else:
            current_specs[key] = value
            if key in missing_reqs:
                missing_reqs.remove(key)
    
    # Update workflow state
    tool_context.state["user_objectives"] = current_objectives
    tool_context.state["material_specs"] = current_specs
    tool_context.state["missing_requirements"] = missing_reqs
    
    return f"✅ Requirements updated. Still missing: {missing_reqs if missing_reqs else 'None - Complete!'}"

def material_database_workflow_tool(
    material_type: str,
    tool_context: ToolContext
) -> str:
    """
    Set material-specific parameters and constraints.
    
    Args:
        material_type: Type of composite material (AS4/8552, IM7/8552)
        tool_context: ADK tool context for state management
        
    Returns:
        str: Material-specific parameters and considerations
    """
    
    material_data = get_material_properties(material_type)
    
    # Store in workflow state
    tool_context.state["material_properties"] = material_data
    tool_context.state["parameter_constraints"] = {
        "ramp_rate_range": material_data["ramp_rate_range"],
        "htc_range": material_data["default_htc_range"],
        "hold_temp_range": material_data["hold_temp_range"]
    }
    
    return f"✅ Material data loaded for {material_type}: {material_data['description']}"

# Create requirement-specific function tools
requirement_update_function_tool = FunctionTool.create(requirement_update_workflow_tool)
material_database_function_tool = FunctionTool.create(material_database_workflow_tool)

# ===================== REQUIREMENTS PHASE SUB-AGENTS =====================

# Agent 1: Parse conversational input
conversational_input_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="conversational_input_agent",
    description="Parse natural language requirements into structured data",
    instruction="""
You are a friendly composite curing expert who parses natural language requirements.

## Your Job:
Parse user input like: "I need an exotherm under 3°C, thermal lag under 15°C, and minimum 70% cure. The tool is 2.5cm aluminum."

## Extract and Structure:
- **Material Type**: AS4/8552, IM7/8552, etc.
- **Part Thickness**: Extract number and units (cm, mm)
- **Tool Material & Thickness**: Aluminum, steel, etc. with dimensions
- **Performance Objectives**: 
  - Max exotherm (°C above air temperature)
  - Max thermal lag (°C between part and air)
  - Min degree of cure (%)
  - Max DOC gradient (% - ask if not specified)

## Use conversational_parser_tool to:
- Extract objectives and material specs from natural language
- Store structured data in workflow state
- Identify missing requirements for clarification

## Communication Style:
Be conversational and helpful. Focus on what was successfully parsed and what needs clarification.
""",
    tools=[conversational_parser_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 2: Ask clarifying questions
requirement_clarification_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="requirement_clarification_agent", 
    description="Ask focused follow-up questions for missing requirements",
    instruction="""
You ask specific, technical questions for missing requirements.

## Your Process:
1. Check missing_requirements from workflow state
2. Ask focused questions with example values
3. Use requirement_update_tool to store clarified information

## Example Questions by Missing Item:
- **material_type**: "What composite material are you using? (e.g., AS4/8552, IM7/8552)"
- **part_thickness**: "What's the part thickness? (e.g., 4cm, 3.5cm)"
- **max_exotherm**: "What's your maximum acceptable exotherm? (e.g., ≤ 3°C above air temperature)"
- **max_thermal_lag**: "What's your thermal lag limit? (e.g., ≤ 15°C between part and air)"
- **min_doc**: "What minimum degree of cure do you need? (e.g., ≥ 70%)"
- **max_doc_gradient**: "How uniform must the cure be? (e.g., DOC gradient ≤ 2%)"
- **tool_material**: "What's your tool material? (aluminum, steel, invar)"
- **tool_thickness**: "What's your tool thickness? (e.g., 2.5cm)"

## Communication:
Be conversational but precise. Ask one focused question at a time.
""",
    tools=[requirement_update_function_tool],
    before_model_callback=check_requirements_complete,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)

# Agent 3: Handle material selection
material_selection_agent = agents.Agent(
    model="gemini-2.5-pro", 
    name="material_selection_agent",
    description="Process material type and set material-specific parameters",
    instruction="""
You handle different composite material types and set material-specific properties.

## Supported Materials:
1. **AS4/8552**: Standard aerospace prepreg
   - Typical cure temp: 180°C
   - Gel time range: 15-25 min
   - Default HTC range: 50-150 W/m²K
   
2. **IM7/8552**: High modulus carbon fiber  
   - Typical cure temp: 180°C
   - Gel time range: 12-20 min
   - Default HTC range: 60-140 W/m²K

## Your Process:
1. Read material_type from workflow state
2. Use material_database_tool to set material-specific properties
3. Store material properties and constraints for parameter suggestion
4. Note any material-specific optimization considerations

## Focus:
Set up material-specific parameter ranges and constraints for optimization.
""",
    tools=[material_database_function_tool],
    before_model_callback=check_material_selection_needed,
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 4: Generate parameter suggestions
parameter_suggestion_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="parameter_suggestion_agent",
    description="Generate intelligent cure cycle parameter suggestions",
    instruction="""
You generate initial cure cycle parameters based on complete requirements.

## Your Process:
1. Read suggestion_context from workflow state (material_specs + user_objectives)
2. Use intelligent_parameter_suggestion_tool to generate starting parameters
3. Use verifier_tool to validate suggested parameters  
4. Present parameters clearly to user

## Output Format:
```
## 🔧 **Suggested Cure Cycle Parameters**

Based on your {material_type} material ({part_thickness}cm thick) and objectives:

• **Heating rate r1**: {value} °C/min
• **Hold Temperature ht1**: {value} °C  
• **Hold duration hd1**: {value} min
• **Heating rate r2**: {value} °C/min
• **Hold Temperature ht2**: {value} °C
• **Hold duration hd2**: {value} min
• **Heat transfer coefficient top**: {value} W/m²K
• **Heat transfer coefficient bottom**: {value} W/m²K
• **Tool thickness**: {value} cm

**Reasoning**: [Explain choices based on material and thickness]

Ready to proceed with baseline simulation using these parameters?
```

Store validated parameters in workflow state for simulation phase.
""",
    tools=[intelligent_parameter_suggestion_function_tool, verifier_function_tool],
    before_agent_callback=prepare_parameter_suggestion,
    after_agent_callback=validate_suggested_parameters,
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)

# Agent 5: Final validation
objective_validation_agent = agents.Agent(
    model="gemini-2.5-pro",
    name="objective_validation_agent",
    description="Final validation that all requirements are complete and valid",
    instruction="""
You perform final validation that all requirements are complete and ready for the next phase.

## Your Process:
1. Check that user_objectives and material_specs are complete in workflow state
2. Validate that suggested_parameters are available and valid
3. Confirm readiness for knowledge retrieval phase
4. Provide summary of collected requirements

## Validation Checklist:
- All 4 objectives specified (exotherm, thermal lag, min DOC, DOC gradient)
- Material type and part thickness specified
- Tool material and thickness specified
- Parameters suggested and validated

## Output:
Clear summary of complete requirements and confirmation to proceed.
""",
    tools=[],  # No tools needed - validation only
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# ===================== COMPLETE REQUIREMENTS PHASE =====================

requirements_phase_agent = agents.SequentialAgent(
    name="requirements_phase_agent", 
    description="Complete requirements gathering with conversational interaction",
    sub_agents=[
        conversational_input_agent,      # Parse natural language input
        requirement_clarification_agent, # Ask for missing information  
        material_selection_agent,        # Set material-specific properties
        parameter_suggestion_agent,      # Generate initial parameters
        objective_validation_agent,      # Final validation
    ],
    before_agent_callback=initialize_requirements_state,
    after_agent_callback=None,  # Validation handled by individual agents
)

# ===================== EXAMPLE WORKFLOW FOR USER INPUT =====================

"""
USER INPUT EXAMPLE:
"I need to design a cure cycle for a thick AS4/8552 carbon fiber part. It's about 4cm thick and I'm concerned about exotherm and thermal gradients."

FOLLOW-UP:
"I need an exotherm under 3°C, thermal lag under 15°C, and minimum 70% cure. The tool is 2.5cm aluminum."

WORKFLOW EXECUTION:

1. conversational_input_agent:
   - Parses: "AS4/8552", "4cm thick", mentions "exotherm and thermal gradients"
   - Stores partial requirements
   - Notes missing specific limits

2. requirement_clarification_agent:
   - Asks: "What specific limits do you have for exotherm and thermal lag?"
   - User provides: "exotherm under 3°C, thermal lag under 15°C, minimum 70% cure, 2.5cm aluminum tool"
   - Updates workflow state with complete objectives

3. material_selection_agent:
   - Processes AS4/8552 material type
   - Sets material-specific properties and constraints
   - Prepares for parameter suggestion

4. parameter_suggestion_agent:
   - Generates conservative parameters for 4cm thick AS4/8552
   - Validates parameters are within acceptable ranges
   - Presents to user with reasoning

5. objective_validation_agent:
   - Confirms all requirements are complete
   - Validates parameters are ready
   - Marks requirements phase complete

FINAL STATE:
{
  "user_objectives": {"max_exotherm": 3.0, "max_thermal_lag": 15.0, "min_doc": 70.0, "max_doc_gradient": 2.0},
  "material_specs": {"material_type": "AS4/8552", "part_thickness": 4.0, "tool_material": "aluminum", "tool_thickness": 2.5},
  "suggested_parameters": {...conservative parameters for thick part...},
  "requirements_complete": True,
  "phases_complete": {"requirements": True}
}

Ready for Knowledge Phase!
"""