# composite_optimizer/sub_agents/requirement_gathering/agent.py

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

"""Requirement gathering agent for composite cure cycle specifications"""

from google.adk.agents import LlmAgent

from . import prompt
from .tools import intelligent_parameter_suggestion, verifier, store_user_objectives
from google.genai import types
MODEL = "gemini-2.5-pro"

requirement_gathering_agent = LlmAgent(
    model=MODEL,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        # optionally set other parameters like max_output_tokens, top_p, etc.
    ),
    name="requirement_gathering_agent",
    description=(
        "Interactive expert for gathering composite cure cycle requirements and "
        "generating scientifically-backed initial parameters with user approval."
    ),
    instruction=prompt.REQUIREMENT_GATHERING_PROMPT,
    output_key="requirements_and_parameters_output",
    tools=[
        intelligent_parameter_suggestion,
        store_user_objectives
    ]
)
