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

MODEL = "gemini-2.5-pro"

composite_optimizer_coordinator = LlmAgent(
    name="composite_optimizer_coordinator",
    model=MODEL,
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
    ],
)

root_agent = composite_optimizer_coordinator