# composite_optimizer/sub_agents/optimization/agent.py

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

"""Optimization agent for iterative parameter improvement with scientific backing"""

from google.adk.agents import LlmAgent

from . import prompt
from .tools import (
    track_optimization_iteration,
    reset_optimization_tracking,
    give_context
    )
# Import shared tools from neural_pde module
from ..neural_pde.tools import (
    get_performance_data_for_analysis,
    get_current_parameters
)

from google.genai import types
MODEL = "gemini-2.5-flash"

optimization_agent = LlmAgent(
    model=MODEL,
    name="optimization_agent", 
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        # optionally set other parameters like max_output_tokens, top_p, etc.
    ),
    description=(
        "Expert optimization agent that analyzes simulation results and provides parameter "
        "recommendations with scientific reasoning based on autoclave processing literature."
    ),
    instruction=prompt.OPTIMIZATION_PROMPT,
    output_key="optimization_recommendations_output",
    tools=[
        give_context,
        get_performance_data_for_analysis,
        get_current_parameters,
        track_optimization_iteration,
        reset_optimization_tracking,
    ]
)
