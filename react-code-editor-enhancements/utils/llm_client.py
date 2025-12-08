"""
LLM Client
Two-phase approach:
1. Phase 1: File Selection (lightweight LLM call)
2. Phase 2: Code Editing (full LLM call)
"""

import json
import logging
from typing import Dict, List, Any
from google import genai

logger = logging.getLogger(__name__)


class LLMClient:
    """Handle LLM interactions for code editing"""
    
    def __init__(self, project: str, location: str, model: str = "gemini-2.0-flash-exp"):
        self.project = project
        self.location = location
        self.model = model
        
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
        
        logger.info(f"LLM Client initialized: {model} in {location}")
    
    async def select_files(self, instruction: str, metadata: Dict) -> Dict:
        """
        Phase 1: Select which files need to be examined
        
        Args:
            instruction: User's editing instruction
            metadata: App metadata (summaries, tree, relationships)
            
        Returns:
            Dict with selected files and reasoning
        """
        logger.info("Phase 1: Selecting files")
        
        prompt = self._build_file_selection_prompt(instruction, metadata)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 8192,
                }
            )
            
            response_text = response.text.strip()
            logger.debug(f"File selection response: {response_text[:200]}...")
            
            # Parse JSON response
            result = self._parse_file_selection_response(response_text)
            
            logger.info(f"Selected {len(result.get('files_needed', []))} files")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in file selection: {e}")
            # Fallback: select all component files
            return self._fallback_file_selection(metadata)
    
    async def edit_code(self, instruction: str, selected_files: Dict[str, str], metadata: Dict, file_selection_result: Dict = None) -> str:
        """
        Phase 2: Generate edited code
        
        Args:
            instruction: User's editing instruction
            selected_files: Dict of EXISTING file paths to their content
            metadata: App metadata for context
            file_selection_result: Result from Phase 1 (includes new files to create)
            
        Returns:
            LLM response with modified files
        """
        logger.info(f"Phase 2: Editing {len(selected_files)} existing files")
        
        # Extract new files from Phase 1
        new_files = []
        if file_selection_result:
            new_files = [f for f in file_selection_result.get('files_needed', []) if f.get('is_new', False)]
            if new_files:
                logger.info(f"Phase 1 indicated {len(new_files)} new files to create:")
                for nf in new_files:
                    logger.info(f"  • {nf['path']} - {nf['reason']}")
        
        prompt = self._build_code_editing_prompt(instruction, selected_files, metadata, new_files)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": 16000,
                }
            )
            
            response_text = response.text.strip()
            logger.info(f"Received editing response ({len(response_text)} chars)")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error in code editing: {e}")
            raise Exception(f"LLM code editing failed: {str(e)}")
    
    def _build_file_selection_prompt(self, instruction: str, metadata: Dict) -> str:
        """Build prompt for Phase 1: File Selection"""
        
        # Format file summaries
        summaries_text = self._format_file_summaries(metadata['file_summaries'])
        
        # Format component relationships
        relationships_text = self._format_relationships(metadata['component_relationships'])
        
        # Current packages
        packages = metadata['package_info'].get('dependencies', {})
        packages_text = ", ".join(packages.keys()) if packages else "None"
        
        prompt = f"""You are a file selection assistant for a React code editing system.

# YOUR TASK
Analyze the user's instruction and determine which EXISTING files need to be read AND which NEW files need to be created.

# APP STRUCTURE
{metadata['file_tree']}

# FILE SUMMARIES
{summaries_text}

# COMPONENT RELATIONSHIPS
{relationships_text}

# CURRENT DEPENDENCIES
{packages_text}

# USER INSTRUCTION
"{instruction}"

# CRITICAL INTELLIGENCE REQUIRED
Analyze the instruction carefully and infer:

1. **NEW FILES TO CREATE** - If the instruction implies:
   - "add routing/pages" → Need to create page files (Home.jsx, About.jsx, etc.)
   - "add a modal/component" → Need to create new component file
   - "split into sections" → Need to create separate component files
   - "add authentication" → Need Auth components (Login.jsx, Signup.jsx, etc.)
   
2. **EXISTING FILES TO MODIFY** - Which files integrate the changes:
   - Main App.jsx to wire up routing/new components
   - Parent components that need to import new components
   - package.json for new dependencies

3. **SMART DEFAULTS FOR NEW FILES**:
   - Pages → src/pages/[Name].jsx
   - Components → src/components/[Name].jsx  
   - Utilities → src/utils/[name].js
   - Context → src/contexts/[Name]Context.jsx

# EXAMPLES OF INTELLIGENT FILE SELECTION

Example 1: "add routing to split page into home and contact"
- NEW: src/pages/Home.jsx, src/pages/Contact.jsx
- EXISTING: src/App.jsx, package.json
- REASON: Need page files + App to setup routing + package.json for react-router-dom

Example 2: "add dark mode toggle"
- EXISTING: src/App.jsx, main component files
- REASON: Modify existing files for theme state and styling

Example 3: "create a settings modal"
- NEW: src/components/SettingsModal.jsx
- EXISTING: src/App.jsx or parent component, package.json
- REASON: New modal component + integrate in parent + maybe dialog package

# GUIDELINES
- Be smart: Infer what NEW files are needed even if not explicitly stated
- Be minimal: Select only necessary EXISTING files
- Always include package.json if new packages needed
- Use standard React conventions for file paths
- Maximum 10 files total (new + existing)

# RESPONSE FORMAT
Respond with a JSON object (NO markdown, just raw JSON):
{{
  "files_needed": [
    {{
      "path": "src/App.jsx",
      "reason": "Need to add routing setup and import pages",
      "is_new": false
    }},
    {{
      "path": "src/pages/Home.jsx",
      "reason": "New page component for home route",
      "is_new": true
    }},
    {{
      "path": "src/pages/Contact.jsx",
      "reason": "New page component for contact route",
      "is_new": true
    }},
    {{
      "path": "package.json",
      "reason": "Need to add react-router-dom dependency",
      "is_new": false
    }}
  ],
  "new_files_count": 2,
  "existing_files_count": 2,
  "estimated_scope": "small|medium|large",
  "requires_new_packages": true|false,
  "confidence": "high|medium|low"
}}

Respond with JSON only, no additional text.
"""
        
        return prompt
    
    def _build_code_editing_prompt(self, instruction: str, selected_files: Dict[str, str], metadata: Dict, new_files: List[Dict] = None) -> str:
        """Build prompt for Phase 2: Code Editing"""
        
        # Format selected files
        files_content = self._format_files_content(selected_files)
        
        # Format new files list
        new_files_text = ""
        if new_files:
            new_files_text = "\n# NEW FILES TO CREATE\n"
            new_files_text += "Phase 1 analysis determined these NEW files are needed:\n"
            for nf in new_files:
                new_files_text += f"- {nf['path']}: {nf['reason']}\n"
            new_files_text += "\nYou MUST create these files with complete content.\n"
        
        prompt = f"""You are an expert React code editor. You will receive files from a React application and an instruction to modify the code.

# APP CONTEXT
File Tree:
{metadata['file_tree']}

Component Relationships:
{self._format_relationships(metadata['component_relationships'])}

Current Dependencies:
{json.dumps(metadata['package_info'].get('dependencies', {}), indent=2)}

# EXISTING FILES (to modify)
{files_content}
{new_files_text}
# USER INSTRUCTION
"{instruction}"

# YOUR TASK
1. Modify EXISTING files according to the instruction
2. CREATE all NEW files indicated above (if any)
3. Ensure all changes are complete and syntactically correct
4. Maintain existing code style and patterns
5. If new packages needed, update package.json
6. Provide complete file contents (not just snippets)

# CRITICAL OUTPUT FORMAT
You MUST use this EXACT format for EVERY file (existing OR new):

MODIFIED_FILE_START: relative/path/to/file.jsx
[COMPLETE FILE CONTENT HERE - including all imports, all functions, all exports]
MODIFIED_FILE_END: relative/path/to/file.jsx

Example for existing file:
MODIFIED_FILE_START: src/App.jsx
import React from 'react'
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom'
import Home from './pages/Home'

function App() {{
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={{<Home />}} />
      </Routes>
    </BrowserRouter>
  )
}}

export default App
MODIFIED_FILE_END: src/App.jsx

Example for new file:
MODIFIED_FILE_START: src/pages/Home.jsx
import React from 'react'

function Home() {{
  return (
    <div>
      <h1>Welcome Home</h1>
    </div>
  )
}}

export default Home
MODIFIED_FILE_END: src/pages/Home.jsx

EXPLANATION: Brief explanation of changes

# REQUIREMENTS
- Use EXACT delimiters: MODIFIED_FILE_START: and MODIFIED_FILE_END:
- Include COMPLETE file content (all imports, all functions, all exports)  
- Output ALL files: modified existing files + all new files
- Use exact paths (for new files, use paths from NEW FILES list above)
- Ensure valid React/JavaScript syntax
- Update package.json if adding packages
- NO markdown code blocks (```), just raw code
- Maintain formatting and indentation

# IMPORTANT
- Even if a file wasn't in "EXISTING FILES" section, if it's listed in "NEW FILES TO CREATE", you MUST output it
- Don't skip new files - they are critical to making the feature work

Now provide ALL modified and new files in the EXACT format above!
"""
        
        return prompt
        """Build prompt for Phase 2: Code Editing"""
        
        # Format selected files
        files_content = self._format_files_content(selected_files)
        
        prompt = f"""You are an expert React code editor. You will receive files from a React application and an instruction to modify the code.

# APP CONTEXT
File Tree:
{metadata['file_tree']}

Component Relationships:
{self._format_relationships(metadata['component_relationships'])}

Current Dependencies:
{json.dumps(metadata['package_info'].get('dependencies', {}), indent=2)}

# FILES TO EDIT
{files_content}

# USER INSTRUCTION
"{instruction}"

# YOUR TASK
1. Modify the code according to the instruction
2. Ensure all changes are complete and syntactically correct
3. Maintain the existing code style and patterns
4. If new packages are needed, include them in package.json
5. Provide complete file contents (not just snippets)
6. **If creating NEW files**: Specify clear paths like "src/pages/Contact.jsx" or "src/components/AboutSection.jsx"

# CRITICAL OUTPUT FORMAT
You MUST use this EXACT format for EVERY file (existing OR new):

MODIFIED_FILE_START: relative/path/to/file.jsx
[COMPLETE FILE CONTENT HERE - including all imports, all functions, all exports]
MODIFIED_FILE_END: relative/path/to/file.jsx

MODIFIED_FILE_START: src/pages/Contact.jsx
[COMPLETE NEW FILE CONTENT - if creating new file]
MODIFIED_FILE_END: src/pages/Contact.jsx

MODIFIED_FILE_START: package.json
[COMPLETE package.json if modified]
MODIFIED_FILE_END: package.json

EXPLANATION: Brief explanation of what was changed

# IMPORTANT RULES FOR NEW FILES
- If creating new pages/components, use paths like: src/pages/PageName.jsx or src/components/ComponentName.jsx
- Always include the COMPLETE content for new files (imports, component definition, export)
- If adding routing, remember to install react-router-dom and update package.json
- For multi-page apps, create: App.jsx (with router), individual page files, and update package.json

# REQUIREMENTS
- Use EXACT delimiters: MODIFIED_FILE_START: and MODIFIED_FILE_END:
- Include COMPLETE file content (all imports, all functions, all exports)
- For NEW files: specify full path like "src/pages/About.jsx"
- For EXISTING files: use paths exactly as shown above
- Ensure valid React/JavaScript syntax
- If adding new packages, update package.json with appropriate versions
- NO markdown code blocks (```), just raw code
- Maintain existing formatting and indentation style

# EXAMPLE OUTPUT FOR NEW FILE CREATION
If user asks "add a contact page", you should output:

MODIFIED_FILE_START: src/pages/Contact.jsx
import React from 'react'

function Contact() {{
  return (
    <div>
      <h1>Contact Us</h1>
      <p>Get in touch</p>
    </div>
  )
}}

export default Contact
MODIFIED_FILE_END: src/pages/Contact.jsx

MODIFIED_FILE_START: src/App.jsx
[... complete updated App.jsx with routing ...]
MODIFIED_FILE_END: src/App.jsx

MODIFIED_FILE_START: package.json
[... package.json with react-router-dom added ...]
MODIFIED_FILE_END: package.json

EXPLANATION: Created Contact page and added routing

Now provide the modified files in the EXACT format above!
"""
        
        return prompt
    
    def _format_file_summaries(self, summaries: Dict) -> str:
        """Format file summaries for prompt"""
        lines = []
        
        for file_path, metadata in summaries.items():
            summary = metadata.get('summary', 'No summary')
            size = metadata.get('size_kb', 0)
            file_lines = metadata.get('lines', 0)
            
            lines.append(f"\n{file_path}")
            lines.append(f"├── Summary: {summary}")
            lines.append(f"├── Size: {size} KB | {file_lines} lines")
            
            # Add specific details for components
            if metadata.get('type') == 'component':
                if metadata.get('external_packages'):
                    lines.append(f"└── External packages: {', '.join(metadata['external_packages'])}")
                else:
                    lines.append(f"└── No external packages")
        
        return "\n".join(lines)
    
    def _format_relationships(self, relationships: Dict) -> str:
        """Format component relationships"""
        if not relationships:
            return "No component relationships detected"
        
        lines = []
        for comp, imports in relationships.items():
            lines.append(f"{comp} → {', '.join(imports)}")
        
        return "\n".join(lines)
    
    def _format_files_content(self, files: Dict[str, str]) -> str:
        """Format file contents for prompt"""
        lines = []
        
        for file_path, content in files.items():
            lines.append(f"\n{'='*60}")
            lines.append(f"FILE: {file_path}")
            lines.append(f"{'='*60}")
            lines.append(content)
        
        return "\n".join(lines)
    
    def _parse_file_selection_response(self, response: str) -> Dict:
        """Parse JSON response from file selection"""
        try:
            # Try to extract JSON from response
            # Handle cases where LLM adds markdown or extra text
            
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            
            response = response.strip()
            
            # Parse JSON
            result = json.loads(response)
            
            # Validate structure
            if 'files_needed' not in result:
                raise ValueError("Missing 'files_needed' in response")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response: {response[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
    
    def _fallback_file_selection(self, metadata: Dict) -> Dict:
        """Fallback file selection if LLM fails"""
        logger.warning("Using fallback file selection")
        
        # Select main component files
        files_needed = []
        
        for file_path, meta in metadata['file_summaries'].items():
            if meta.get('type') == 'component':
                files_needed.append({
                    "path": file_path,
                    "reason": "Fallback selection"
                })
        
        # Always include package.json
        files_needed.append({
            "path": "package.json",
            "reason": "Always needed"
        })
        
        return {
            "files_needed": files_needed[:7],  # Limit to 7
            "estimated_scope": "unknown",
            "requires_new_packages": False,
            "confidence": "low"
        }
