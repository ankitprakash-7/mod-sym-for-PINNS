"""
composite_optimization/sub_agents/knowledge/agent.py
Complete Knowledge Phase Implementation - Self-contained
No external dependencies - integrates URL-based RAG functionality
"""

from google.adk import agents
from google.genai import types
from google.adk.agents import callback_context as callback_context_module
from google.adk.tools import FunctionTool, ToolContext
from typing import Optional, Dict, Any

# Import from new workflow structure only
from composite_optimization.shared_libraries.function_wrappers import (
    give_context_function_tool,
    knowledge_synthesis_function_tool,
    WORKFLOW_FUNCTION_TOOLS
)
from composite_optimization.shared_libraries.composite_util import (
    get_from_workflow_state,
    store_in_workflow_state
)
from composite_optimization import prompt

# ===================== KNOWLEDGE PHASE CALLBACK FUNCTIONS =====================

def initialize_knowledge_state(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Initialize state for knowledge retrieval phase."""
    callback_context.state["current_phase"] = "knowledge"
    callback_context.state["autoclave_knowledge"] = None
    callback_context.state["knowledge_extracted"] = False
    callback_context.state["processing_guidelines"] = {}
    callback_context.state["parameter_guidance"] = {}
    
    # Determine knowledge focus based on user requirements
    user_objectives = callback_context.state.get("user_objectives", {})
    material_specs = callback_context.state.get("material_specs", {})
    
    knowledge_focus = []
    if "max_exotherm" in user_objectives:
        knowledge_focus.append("exotherm_control")
    if "max_thermal_lag" in user_objectives:
        knowledge_focus.append("thermal_lag_management")
    if material_specs.get("part_thickness", 0) > 3.0:
        knowledge_focus.append("thick_part_processing")
    
    callback_context.state["knowledge_focus"] = knowledge_focus
    
    # Set autoclave document URL
    callback_context.state["autoclave_doc_url"] = "https://drive.google.com/file/d/1T--rE4mDHEkx8dT2bzOepwP3omlE5nFY/view?usp=sharing"
    
    return None

def validate_knowledge_extracted(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Validate that knowledge was successfully extracted."""
    
    autoclave_knowledge = callback_context.state.get("autoclave_knowledge")
    if not autoclave_knowledge or len(autoclave_knowledge) < 100:
        return types.Content(
            role='assistant',
            parts=[types.Part(text="❌ Knowledge extraction failed or incomplete. Retrying...")]
        )
    
    callback_context.state["knowledge_extracted"] = True
    return None

def organize_knowledge_for_optimization(
    callback_context: callback_context_module.CallbackContext
) -> Optional[types.Content]:
    """Organize extracted knowledge for optimization phase use."""
    
    # Validate knowledge synthesis is complete
    processing_guidelines = callback_context.state.get("processing_guidelines", {})
    parameter_guidance = callback_context.state.get("parameter_guidance", {})
    
    if not processing_guidelines or not parameter_guidance:
        return types.Content(
            role='assistant',
            parts=[types.Part(text="❌ Knowledge synthesis incomplete")]
        )
    
    # Mark knowledge phase as complete
    callback_context.state["phases_complete"]["knowledge"] = True
    callback_context.state["knowledge_ready_for_optimization"] = True
    
    # Create summary for next phase
    focus_areas = callback_context.state.get("knowledge_focus", [])
    knowledge_summary = f"✅ Knowledge organized for {len(focus_areas)} focus areas: {focus_areas}"
    callback_context.state["knowledge_summary"] = knowledge_summary
    
    return None

# ===================== KNOWLEDGE PHASE SUB-AGENTS =====================

# Agent 1: Document retrieval (your knowledge_processing_agent functionality)
document_retrieval_agent = agents.Agent(
    model="gemini-2.0-flash",  # Your specified model for knowledge processing
    name="document_retrieval_agent",
    description="Extract autoclave processing knowledge from technical documents",
    instruction="""
🧠 **Autoclave Knowledge Extraction Specialist**

You extract technical knowledge from autoclave processing documents using URL-based RAG.

## Your Process:
1. Read autoclave_doc_url from workflow state  
2. Read knowledge_focus from workflow state to understand user's specific needs
3. Use give_context_workflow_tool to extract knowledge from the autoclave processing document
4. Focus extraction on user's concerns (exotherm control, thermal lag, thick part processing)

## Focus Areas Based on User Requirements:
- **exotherm_control**: If user specified exotherm limits
- **thermal_lag_management**: If user specified thermal lag concerns  
- **thick_part_processing**: If part thickness > 3cm

## Extract Information About:
- Heat transfer coefficient guidelines and ranges
- Temperature ramp rate effects and limitations
- Hold time optimization strategies
- Tool thickness considerations  
- Processing best practices for thick parts
- Material-specific processing guidelines

Store comprehensive autoclave processing knowledge for optimization agents.
""",
    tools=[give_context_function_tool],
    after_model_callback=validate_knowledge_extracted,
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# Agent 2: Knowledge synthesis and organization  
knowledge_synthesis_agent = agents.Agent(
    model="gemini-2.0-flash",
    name="knowledge_synthesis_agent",
    description="Organize retrieved knowledge for optimization use", 
    instruction="""
📋 **Knowledge Organization Specialist**

You organize extracted autoclave knowledge for optimization agents.

## Your Process:
1. Read autoclave_knowledge and knowledge_focus from workflow state
2. Use knowledge_synthesis_tool to organize knowledge by user's focus areas
3. Extract parameter relationships and optimization constraints
4. Store organized knowledge for optimization phase

## Organization Structure:
- **Processing Guidelines**: Best practices for each focus area
- **Parameter Guidance**: How each parameter affects performance  
- **Optimization Constraints**: Technical limits and valid ranges

## Focus Areas to Organize:
- **exotherm_control**: Strategies for managing exothermic reactions
- **thermal_lag_management**: Methods for minimizing thermal gradients
- **thick_part_processing**: Special considerations for thick parts

## Output:
Structured knowledge ready for optimization phase:
- Clear cause-effect relationships
- Specific parameter recommendations
- Scientific justification for optimization decisions
- Material and thickness-specific considerations

This organized knowledge guides intelligent parameter optimization.
""",
    tools=[knowledge_synthesis_function_tool],
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

# ===================== COMPLETE KNOWLEDGE PHASE =====================

knowledge_phase_agent = agents.SequentialAgent(
    name="knowledge_phase_agent", 
    description="Complete knowledge retrieval and processing using URL-based RAG",
    sub_agents=[
        document_retrieval_agent,      # Extract from autoclave processing document
        knowledge_synthesis_agent,     # Organize for optimization use
    ],
    before_agent_callback=initialize_knowledge_state,
    after_agent_callback=organize_knowledge_for_optimization,
)

# ===================== KNOWLEDGE PHASE WORKFLOW NOTES =====================

"""
KNOWLEDGE PHASE WORKFLOW:

Input from Requirements Phase:
{
  "user_objectives": {"max_exotherm": 3.0, "max_thermal_lag": 15.0, ...},
  "material_specs": {"material_type": "AS4/8552", "part_thickness": 4.0, ...},
  "suggested_parameters": {...initial parameters...}
}

Knowledge Phase Processing:

1. initialize_knowledge_state:
   - Sets knowledge_focus based on user objectives and part thickness
   - For 4cm thick part with exotherm/thermal lag concerns:
     knowledge_focus = ["exotherm_control", "thermal_lag_management", "thick_part_processing"]

2. document_retrieval_agent:
   - Extracts comprehensive autoclave processing knowledge
   - Stores in workflow state: autoclave_knowledge

3. knowledge_synthesis_agent:
   - Organizes knowledge by focus areas
   - Creates processing_guidelines and parameter_guidance
   - Stores structured knowledge for optimization

Output to Simulation Phase:
{
  ...existing state...,
  "autoclave_knowledge": "...comprehensive processing guidelines...",
  "processing_guidelines": {
    "exotherm": {"strategies": [...], "critical_parameters": [...]},
    "thermal_lag": {"strategies": [...], "critical_parameters": [...]},
    "thick_parts": {"strategies": [...], "critical_parameters": [...]}
  },
  "parameter_guidance": {
    "exotherm": {"ramp_rates": "...", "htc_values": "..."},
    "thermal_lag": {"ramp_rates": "...", "htc_balance": "..."},
    "thick_parts": {"ramp_rates": "...", "hold_times": "..."}
  },
  "phases_complete": {"requirements": True, "knowledge": True}
}

This organized knowledge enables intelligent optimization in the next phases.
"""