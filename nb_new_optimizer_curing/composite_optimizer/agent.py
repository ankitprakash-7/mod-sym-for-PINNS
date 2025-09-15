# composite_optimizer/agent.py

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

"""Composite cure cycle optimization coordinator agent"""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .sub_agents.requirement_gathering import requirement_gathering_agent
from .sub_agents.knowledge_processing import knowledge_processing_agent
from .sub_agents.neural_pde import neural_pde_agent
from .sub_agents.optimization import optimization_agent
from google.genai import types

MODEL = "gemini-2.5-pro"
# coordinator_tools.py

def extract_json_parameters(optimization_output: str) -> dict:
    """
    Extract JSON parameters from optimization agent output for neural PDE simulation.
    
    Args:
        optimization_output: Complete text output from optimization agent
        
    Returns:
        dict: Extracted parameters ready for neural PDE or error status
    """
    import re
    import json
    
    try:
        # Look for JSON block at start of output (optimization agent puts it first)
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, optimization_output, re.DOTALL)
        
        if not matches:
            return {
                "status": "error",
                "message": "No JSON parameter block found in optimization output. The optimization agent should start with a JSON block.",
                "extracted_parameters": None
            }
        
        # Parse the first JSON block (should be the parameters)
        params_json = json.loads(matches[0])
        
        # Validate required structure
        if "user_requirements_json" not in params_json:
            return {
                "status": "error", 
                "message": "JSON block missing 'user_requirements_json' structure",
                "extracted_parameters": None
            }
            
        # Check for all required parameters
        required_params = [
            "Heating rate r1 (°C/min)",
            "Heating rate r2 (°C/min)", 
            "Hold Temperature ht1 (°C)",
            "Hold Temperature ht2 (°C)",
            "Hold duration hd1 (min)",
            "Hold duration hd2 (min)",
            "Heat transfer coefficient top htop p (W/m2K)",
            "Heat transfer coefficient bottom hbot p (W/m2K)",
            "Tool thickness Lt (cm)"
        ]
        
        user_params = params_json["user_requirements_json"]
        missing_params = [param for param in required_params if param not in user_params]
                
        if missing_params:
            return {
                "status": "error",
                "message": f"Missing required parameters in JSON: {missing_params}",
                "extracted_parameters": None
            }
        
        # Validate parameter ranges (constraint compliance)
        constraints = {
            "Heating rate r1 (°C/min)": [1.2, 3.0],
            "Heating rate r2 (°C/min)": [1.2, 3.0],
            "Hold Temperature ht1 (°C)": [100, 120],
            "Hold Temperature ht2 (°C)": [175, 185],
            "Hold duration hd1 (min)": [50, 70],
            "Hold duration hd2 (min)": [115, 125],
            "Heat transfer coefficient top htop p (W/m2K)": [70, 120],
            "Heat transfer coefficient bottom hbot p (W/m2K)": [40, 90],
            "Tool thickness Lt (cm)": [2.0, 4.0]
        }
        
        violations = []
        for param, (min_val, max_val) in constraints.items():
            value = float(user_params[param])
            if value < min_val or value > max_val:
                violations.append(f"{param}: {value} outside [{min_val}, {max_val}]")
        
        if violations:
            return {
                "status": "error",
                "message": f"Parameters outside valid ranges: {violations}",
                "extracted_parameters": None
            }
            
        return {
            "status": "success",
            "message": "Parameters successfully extracted and validated",
            "extracted_parameters": params_json
        }
        
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON format in optimization output: {str(e)}",
            "extracted_parameters": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error during parameter extraction: {str(e)}",
            "extracted_parameters": None
        }


# Add to coordinator agent tools list:
# tools=[
#     AgentTool(agent=requirement_gathering_agent),
#     AgentTool(agent=knowledge_processing_agent), 
#     AgentTool(agent=neural_pde_agent),
#     AgentTool(agent=optimization_agent),
#     extract_json_parameters,  # <-- Add this tool
# ]


composite_optimizer_coordinator = LlmAgent(
    name="composite_optimizer_coordinator",
    model=MODEL,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        # optionally set other parameters like max_output_tokens, top_p, etc.
    ),
    description=(
        "Coordinates the complete composite cure cycle optimization workflow. "
        "Guides users through requirements gathering, parameter suggestion, "
        "simulation, and iterative optimization to achieve optimal cure cycles."
    ),
    instruction=prompt.COMPOSITE_OPTIMIZER_COORDINATOR_PROMPT,
    output_key="composite_optimizer_coordinator_output",
    tools=[
        AgentTool(agent=requirement_gathering_agent),
        AgentTool(agent=knowledge_processing_agent),
        AgentTool(agent=neural_pde_agent),
        AgentTool(agent=optimization_agent),
        extract_json_parameters
    ],
)

root_agent = composite_optimizer_coordinator
