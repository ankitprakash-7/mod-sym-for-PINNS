"""
Response Parser
Parse LLM responses and extract modified files
"""

import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parse LLM code editing responses"""
    
    @staticmethod
    def parse_modified_files(response: str) -> Tuple[Dict[str, str], str]:
        """
        Parse modified files from LLM response
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Tuple of (modified_files dict, explanation)
        """
        logger.info("Parsing LLM response")
        
        modified_files = {}
        explanation = ""
        
        # Try primary format: MODIFIED_FILE_START/END
        files = ResponseParser._extract_primary_format(response)
        
        if files:
            modified_files = files
            logger.info(f"Extracted {len(files)} files using primary format")
        else:
            # Fallback to alternative formats
            logger.warning("Primary format not found, trying fallback formats")
            files = ResponseParser._extract_fallback_formats(response)
            modified_files = files
            logger.info(f"Extracted {len(files)} files using fallback format")
        
        # Extract explanation
        explanation = ResponseParser._extract_explanation(response)
        
        # Clean up file contents
        modified_files = {
            path: ResponseParser._clean_content(content)
            for path, content in modified_files.items()
        }
        
        return modified_files, explanation
    
    @staticmethod
    def _extract_primary_format(response: str) -> Dict[str, str]:
        """Extract files using MODIFIED_FILE_START/END format"""
        files = {}
        
        # Pattern: MODIFIED_FILE_START: path ... MODIFIED_FILE_END: path
        pattern = r'MODIFIED_FILE_START:\s*([^\n]+)\s*\n(.*?)\nMODIFIED_FILE_END:\s*\1'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for file_path, content in matches:
            file_path = file_path.strip()
            content = content.strip()
            
            if content and len(content) > 20:  # Minimum content length
                files[file_path] = content
                logger.debug(f"Extracted: {file_path} ({len(content)} chars)")
        
        return files
    
    @staticmethod
    def _extract_fallback_formats(response: str) -> Dict[str, str]:
        """Try alternative extraction formats"""
        files = {}
        
        # Format 1: File path followed by code block
        pattern1 = r'(?:^|\n)((?:src/|)[^\s\n]+\.(?:jsx|js|tsx|ts|json|css))\s*\n```(?:jsx|javascript|js|json|css)?\s*\n(.*?)\n```'
        matches1 = re.findall(pattern1, response, re.DOTALL | re.MULTILINE)
        
        for file_path, content in matches1:
            if content.strip() and len(content.strip()) > 20:
                files[file_path.strip()] = content.strip()
        
        # Format 2: Header with file path and code block
        pattern2 = r'###?\s*((?:src/|)[^\n]+\.(?:jsx|js|tsx|ts|json|css))\s*\n```(?:jsx|javascript|js|json|css)?\s*\n(.*?)\n```'
        matches2 = re.findall(pattern2, response, re.DOTALL | re.MULTILINE)
        
        for file_path, content in matches2:
            if content.strip() and len(content.strip()) > 20:
                files[file_path.strip()] = content.strip()
        
        return files
    
    @staticmethod
    def _extract_explanation(response: str) -> str:
        """Extract explanation from response"""
        # Look for EXPLANATION: marker
        match = re.search(r'EXPLANATION:\s*(.+?)(?:\n\n|$)', response, re.DOTALL)
        
        if match:
            explanation = match.group(1).strip()
            # Limit explanation length
            if len(explanation) > 500:
                explanation = explanation[:500] + "..."
            return explanation
        
        # Fallback: try to find any explanation text
        lines = response.split('\n')
        for i, line in enumerate(lines):
            if 'explanation' in line.lower() or 'changes' in line.lower():
                # Get next few lines
                explanation_lines = lines[i:i+5]
                explanation = ' '.join(explanation_lines)
                if len(explanation) > 500:
                    explanation = explanation[:500] + "..."
                return explanation
        
        return "Code modified successfully"
    
    @staticmethod
    def _clean_content(content: str) -> str:
        """Clean up file content"""
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Remove markdown code block markers if present
        if content.startswith('```'):
            lines = content.split('\n')
            # Remove first line (```jsx or similar)
            if lines[0].strip().startswith('```'):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines)
        
        # Remove any remaining ``` markers
        content = content.replace('```jsx', '').replace('```javascript', '')
        content = content.replace('```json', '').replace('```css', '')
        content = content.replace('```', '')
        
        # Clean up extra whitespace but preserve code structure
        content = content.strip()
        
        return content
    
    @staticmethod
    def validate_files(files: Dict[str, str]) -> list:
        """Validate extracted files and return list of issues"""
        issues = []
        
        for file_path, content in files.items():
            # Check file path
            if not file_path.endswith(('.jsx', '.js', '.tsx', '.ts', '.json', '.css')):
                issues.append(f"{file_path}: Unexpected file extension")
            
            # Check content length
            if len(content) < 50:
                issues.append(f"{file_path}: Content too short ({len(content)} chars)")
            
            # For JS/JSX files, check for basic structure
            if file_path.endswith(('.jsx', '.tsx', '.js', '.ts')):
                if 'import' not in content and 'require' not in content:
                    issues.append(f"{file_path}: Missing imports (might be incomplete)")
                
                if 'export' not in content and 'module.exports' not in content:
                    issues.append(f"{file_path}: Missing exports (might be incomplete)")
                
                # Check for markdown artifacts
                if content.startswith('```') or '```' in content[:100]:
                    issues.append(f"{file_path}: Contains markdown code block markers")
                
                # Check for balanced braces
                if content.count('{') != content.count('}'):
                    issues.append(f"{file_path}: Unbalanced braces")
            
            # For JSON files, validate JSON
            if file_path.endswith('.json'):
                try:
                    import json
                    json.loads(content)
                except json.JSONDecodeError as e:
                    issues.append(f"{file_path}: Invalid JSON - {str(e)}")
        
        return issues
