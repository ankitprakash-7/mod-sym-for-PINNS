# composite_optimizer/sub_agents/neural_pde/agent.py

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

"""Neural PDE agent for PINO simulation execution and results analysis"""

from google.adk.agents import LlmAgent

from . import prompt
from .tools import (
    run_pino_simulation,
    get_performance_data_for_analysis,
    get_current_parameters
)
from google.genai import types

#MODEL = "gemini-2.5-pro"
from google.adk.models.anthropic_llm import Claude # Import needed for registration
from google.adk.models.registry import LLMRegistry # Import needed for registration

LLMRegistry.register(Claude)

MODEL = "claude-sonnet-4"

neural_pde_agent = LlmAgent(
    model=MODEL,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        #max_output_tokens=20000
        # optionally set other parameters like max_output_tokens, top_p, etc.
    ),
    name="neural_pde_agent",
    description=(
        "Specialized agent for running PINO simulations, presenting comprehensive results, "
        "and coordinating with optimization workflows for composite cure cycle analysis."
    ),
    instruction=prompt.NEURAL_PDE_PROMPT,
    output_key="simulation_results_output",
    tools=[
        run_pino_simulation,
        get_performance_data_for_analysis,
        get_current_parameters,
    ]
)
