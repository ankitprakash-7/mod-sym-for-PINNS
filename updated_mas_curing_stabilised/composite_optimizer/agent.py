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
from .sub_agents.optimization.tools import select_best_iteration
from google.genai import types
from google.adk.models.anthropic_llm import Claude
from google.adk.models.registry import LLMRegistry

MODEL = "claude-sonnet-4"


def extract_json_parameters(agent_output: str, agent_type: str = "optimization") -> dict:
    """
    Extract JSON parameters from agent output for neural PDE simulation.
    Works for both requirement_gathering and optimization agents.
    
    Args:
        agent_output: Complete text output from agent
        agent_type: Type of agent ("requirement_gathering" or "optimization")
        
    Returns:
        dict: Extracted parameters ready for neural PDE or error status
    """
    import re
    import json
    
    try:
        json_block_pattern = r'```json\s*(.*?)\s*```'
        json_matches = re.findall(json_block_pattern, agent_output, re.DOTALL)
        
        if not json_matches:
            return {
                "status": "error",
                "message": f"No JSON parameter block found in {agent_type} output. The agent should start with a JSON block.",
                "extracted_parameters": None
            }
        
        json_content = json_matches[0].strip()
        params_json = json.loads(json_content)
        
        if "user_requirements_json" not in params_json:
            return {
                "status": "error", 
                "message": "JSON block missing 'user_requirements_json' structure",
                "extracted_parameters": None
            }
            
        required_params = [
            "Heating rate r1 (°C/min)",
            "Heating rate r2 (°C/min)", 
            "Hold Temperature ht1 (°C)",
            "Hold Temperature ht2 (°C)",
            "Hold duration hd1 (min)",
            "Hold duration hd2 (min)",
            "Heat transfer coefficient top htop p (W/m2K)",
            "Heat transfer coefficient bottom hbot p (W/m2K)",
            "Tool thickness Lt (m)",
            "Part thickness Lp (m)"
        ]
        
        user_params = params_json["user_requirements_json"]
        missing_params = [param for param in required_params if param not in user_params]
                
        if missing_params:
            return {
                "status": "error",
                "message": f"Missing required parameters in JSON: {missing_params}",
                "extracted_parameters": None
            }
        
        # Check for array values (common mistake)
        for param_name, param_value in user_params.items():
            if isinstance(param_value, list):
                return {
                    "status": "error",
                    "message": f"Parameter '{param_name}' has array value {param_value}, but should be a single numeric value",
                    "extracted_parameters": None
                }
        
        # Validate constraint ranges
        constraints = {
            "Heating rate r1 (°C/min)": [1.5, 3.0],
            "Heating rate r2 (°C/min)": [1.5, 3.0],
            "Hold Temperature ht1 (°C)": [105, 120],
            "Hold Temperature ht2 (°C)": [170, 185],
            "Hold duration hd1 (min)": [50, 65],
            "Hold duration hd2 (min)": [105, 120],
            "Heat transfer coefficient top htop p (W/m2K)": [70, 120],
            "Heat transfer coefficient bottom hbot p (W/m2K)": [50, 100],
            "Tool thickness Lt (m)": [0.02, 0.05],
            "Part thickness Lp (m)": [0.025, 0.035]
        }
        
        violations = []
        for param, (min_val, max_val) in constraints.items():
            if param in user_params:
                try:
                    value = float(user_params[param])
                    if value < min_val or value > max_val:
                        violations.append(f"{param}: {value} outside inference service range [{min_val}, {max_val}]")
                except (ValueError, TypeError):
                    violations.append(f"{param}: invalid numeric value '{user_params[param]}'")
        
        if violations:
            return {
                "status": "error",
                "message": f"Parameters outside inference service compatible ranges: {violations}",
                "extracted_parameters": None
            }
            
        return {
            "status": "success",
            "message": f"Parameters successfully extracted and validated from {agent_type} agent output",
            "extracted_parameters": params_json
        }
        
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON format in {agent_type} output: {str(e)}",
            "extracted_parameters": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error during parameter extraction from {agent_type} output: {str(e)}",
            "extracted_parameters": None
        }


composite_optimizer_coordinator = LlmAgent(
    name="composite_optimizer_coordinator",
    model=MODEL,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
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
        extract_json_parameters,
        select_best_iteration
    ],
)

root_agent = composite_optimizer_coordinator
