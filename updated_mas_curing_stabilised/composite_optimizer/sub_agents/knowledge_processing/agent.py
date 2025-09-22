# composite_optimizer/sub_agents/knowledge_processing/agent.py

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

"""Knowledge processing agent for technical document analysis"""

from google.adk.agents import LlmAgent

from . import prompt
from .tools import give_context
from google.genai import types
from google.adk.models.anthropic_llm import Claude
from google.adk.models.registry import LLMRegistry
#LLMRegistry.register(Claude)
#MODEL = "claude-sonnet-4"
MODEL = "gemini-2.5-pro"

knowledge_processing_agent = LlmAgent(
    model=MODEL,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        # optionally set other parameters like max_output_tokens, top_p, etc.
    ),
    name="knowledge_processing_agent",
    description=(
        "Technical knowledge specialist for composite materials and autoclave equipment. "
        "Extracts and synthesizes information from technical documents and provides "
        "material property data and processing guidelines."
    ),
    instruction=prompt.KNOWLEDGE_PROCESSING_PROMPT,
    output_key="knowledge_processing_output",
    tools=[give_context]
)
