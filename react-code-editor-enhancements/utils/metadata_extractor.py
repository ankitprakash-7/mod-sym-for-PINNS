"""
Metadata Extractor
Fast code analysis without LLM calls (~100ms for entire app)
Extracts factual information from code files
"""

import os
import re
import json
import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract metadata from React app files using simple parsing"""
    
    def __init__(self, app_path: str):
        self.app_path = app_path
        self.summaries = {}
        self.file_tree = ""
        self.component_relationships = {}
    
    def analyze_app(self) -> Dict[str, Any]:
        """
        Analyze entire app and return comprehensive metadata
        
        Returns:
            Dict containing file summaries, tree, and relationships
        """
        logger.info(f"Analyzing app at: {self.app_path}")
        
        # Generate file tree
        self.file_tree = self._generate_file_tree()
        
        # Extract metadata from all files
        self.summaries = self._extract_all_metadata()
        
        # Build component relationships
        self.component_relationships = self._build_relationships()
        
        # Get package.json info
        package_info = self._get_package_info()
        
        result = {
            "file_tree": self.file_tree,
            "file_summaries": self.summaries,
            "component_relationships": self.component_relationships,
            "package_info": package_info,
            "total_files": len(self.summaries),
            "component_count": self._count_components()
        }
        
        logger.info(f"Analysis complete: {result['total_files']} files, {result['component_count']} components")
        
        return result
    
    def _generate_file_tree(self) -> str:
        """Generate ASCII file tree visualization"""
        tree_lines = []
        
        def add_tree_line(path, prefix="", is_last=True):
            """Recursively build tree"""
            name = os.path.basename(path)
            connector = "└── " if is_last else "├── "
            tree_lines.append(f"{prefix}{connector}{name}")
            
            if os.path.isdir(path):
                # Get children, skip ignored dirs
                try:
                    children = sorted([
                        os.path.join(path, child)
                        for child in os.listdir(path)
                        if child not in ['node_modules', 'dist', 'build', '.git', '__pycache__']
                    ])
                except PermissionError:
                    return
                
                extension = "    " if is_last else "│   "
                for i, child in enumerate(children):
                    is_last_child = (i == len(children) - 1)
                    add_tree_line(child, prefix + extension, is_last_child)
        
        app_name = os.path.basename(self.app_path)
        tree_lines.append(app_name + "/")
        
        try:
            children = sorted([
                os.path.join(self.app_path, child)
                for child in os.listdir(self.app_path)
                if child not in ['node_modules', 'dist', 'build', '.git']
            ])
            
            for i, child in enumerate(children):
                is_last = (i == len(children) - 1)
                add_tree_line(child, "", is_last)
        except Exception as e:
            logger.error(f"Error generating tree: {e}")
        
        return "\n".join(tree_lines)
    
    def _extract_all_metadata(self) -> Dict[str, Dict]:
        """Extract metadata from all relevant files"""
        summaries = {}
        
        for root, dirs, files in os.walk(self.app_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist', 'build', '.git', '__pycache__']]
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.app_path)
                
                # Process different file types
                if file.endswith(('.jsx', '.tsx', '.js', '.ts')):
                    summaries[rel_path] = self._analyze_component_file(file_path, rel_path)
                elif file == 'package.json':
                    summaries[rel_path] = self._analyze_package_json(file_path, rel_path)
                elif file.endswith('.css'):
                    summaries[rel_path] = self._analyze_css_file(file_path, rel_path)
                elif file.endswith(('.json', '.config.js')):
                    summaries[rel_path] = self._analyze_config_file(file_path, rel_path)
        
        return summaries
    
    def _analyze_component_file(self, file_path: str, rel_path: str) -> Dict:
        """Analyze React component file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {rel_path}: {e}")
            return {"error": str(e)}
        
        metadata = {
            "type": "component",
            "component_name": self._extract_component_name(content),
            "is_functional": self._is_functional_component(content),
            "has_state": 'useState' in content or 'useReducer' in content,
            "state_count": content.count('useState'),
            "hooks_used": self._extract_hooks(content),
            "imports": self._extract_imports(content),
            "external_packages": self._extract_external_packages(content),
            "local_imports": self._extract_local_imports(content),
            "jsx_elements": self._count_jsx_elements(content),
            "event_handlers": self._extract_event_handlers(content),
            "exports_default": 'export default' in content,
            "size_kb": round(os.path.getsize(file_path) / 1024, 2),
            "lines": content.count('\n') + 1
        }
        
        # Generate human-readable summary
        metadata["summary"] = self._format_component_summary(metadata)
        
        return metadata
    
    def _extract_component_name(self, content: str) -> str:
        """Extract component name"""
        patterns = [
            r'export\s+default\s+function\s+(\w+)',
            r'const\s+(\w+)\s*=\s*\(',
            r'function\s+(\w+)\s*\(',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1)
                if name[0].isupper():  # React component naming convention
                    return name
        
        return "Unknown"
    
    def _is_functional_component(self, content: str) -> bool:
        """Check if it's a functional component"""
        return ('function' in content or '=>' in content) and 'return' in content
    
    def _extract_hooks(self, content: str) -> List[str]:
        """Extract React hooks used"""
        hooks = []
        hook_list = [
            'useState', 'useEffect', 'useRef', 'useMemo',
            'useCallback', 'useContext', 'useReducer', 'useLayoutEffect'
        ]
        
        for hook in hook_list:
            if hook in content:
                hooks.append(hook)
        
        return hooks
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract all import statements"""
        pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        return re.findall(pattern, content)
    
    def _extract_external_packages(self, content: str) -> List[str]:
        """Extract external package names from imports"""
        imports = self._extract_imports(content)
        packages = []
        
        for imp in imports:
            if not imp.startswith('.'):  # External package
                if imp.startswith('@'):
                    # Scoped package: @scope/package
                    parts = imp.split('/')
                    pkg = f"{parts[0]}/{parts[1]}" if len(parts) > 1 else parts[0]
                else:
                    pkg = imp.split('/')[0]
                packages.append(pkg)
        
        return list(set(packages))
    
    def _extract_local_imports(self, content: str) -> List[str]:
        """Extract local component imports"""
        imports = self._extract_imports(content)
        return [imp for imp in imports if imp.startswith('.')]
    
    def _count_jsx_elements(self, content: str) -> Dict[str, int]:
        """Count different JSX elements"""
        content_lower = content.lower()
        
        return {
            "buttons": content_lower.count('<button'),
            "inputs": content_lower.count('<input'),
            "forms": content_lower.count('<form'),
            "divs": content_lower.count('<div'),
            "images": content_lower.count('<img'),
            "links": content_lower.count('<a ') + content_lower.count('<a>'),
        }
    
    def _extract_event_handlers(self, content: str) -> List[str]:
        """Extract event handler function names"""
        handlers = []
        
        patterns = [
            r'on\w+\s*=\s*\{(\w+)\}',  # onClick={handler}
            r'const\s+(\w+Handler)',     # const clickHandler
            r'function\s+(handle\w+)',   # function handleClick
        ]
        
        for pattern in patterns:
            handlers.extend(re.findall(pattern, content))
        
        return list(set(handlers))
    
    def _format_component_summary(self, metadata: Dict) -> str:
        """Convert metadata to human-readable summary"""
        parts = [metadata['component_name']]
        
        # Component type
        if metadata['is_functional']:
            parts.append("functional component")
        
        # State
        if metadata['has_state']:
            parts.append(f"{metadata['state_count']} state variable(s)")
        
        # Hooks
        if metadata['hooks_used']:
            hook_str = ', '.join(metadata['hooks_used'][:3])
            if len(metadata['hooks_used']) > 3:
                hook_str += f" +{len(metadata['hooks_used']) - 3} more"
            parts.append(f"uses {hook_str}")
        
        # External packages
        if metadata['external_packages']:
            pkg_str = ', '.join(metadata['external_packages'][:3])
            if len(metadata['external_packages']) > 3:
                pkg_str += f" +{len(metadata['external_packages']) - 3} more"
            parts.append(f"imports {pkg_str}")
        
        # JSX elements (only mention if significant)
        jsx = metadata['jsx_elements']
        elements = []
        for elem, count in jsx.items():
            if count > 0:
                elements.append(f"{count} {elem}")
        
        if elements:
            elem_str = ', '.join(elements[:4])
            parts.append(f"contains {elem_str}")
        
        return " | ".join(parts)
    
    def _analyze_package_json(self, file_path: str, rel_path: str) -> Dict:
        """Analyze package.json"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            deps = data.get('dependencies', {})
            dev_deps = data.get('devDependencies', {})
            
            return {
                "type": "config",
                "summary": f"Package configuration with {len(deps)} dependencies, {len(dev_deps)} dev dependencies",
                "dependencies": deps,
                "devDependencies": dev_deps,
                "size_kb": round(os.path.getsize(file_path) / 1024, 2),
                "lines": sum(1 for _ in open(file_path))
            }
        except Exception as e:
            return {"type": "config", "error": str(e)}
    
    def _analyze_css_file(self, file_path: str, rel_path: str) -> Dict:
        """Analyze CSS file"""
        size_kb = round(os.path.getsize(file_path) / 1024, 2)
        with open(file_path, 'r') as f:
            lines = sum(1 for _ in f)
        
        return {
            "type": "style",
            "summary": f"Stylesheet ({size_kb} KB)",
            "size_kb": size_kb,
            "lines": lines
        }
    
    def _analyze_config_file(self, file_path: str, rel_path: str) -> Dict:
        """Analyze config file"""
        size_kb = round(os.path.getsize(file_path) / 1024, 2)
        
        return {
            "type": "config",
            "summary": f"Configuration file ({size_kb} KB)",
            "size_kb": size_kb
        }
    
    def _build_relationships(self) -> Dict[str, List[str]]:
        """Build component relationship map"""
        relationships = {}
        
        for file_path, metadata in self.summaries.items():
            if metadata.get('type') == 'component':
                comp_name = metadata.get('component_name', 'Unknown')
                local_imports = metadata.get('local_imports', [])
                
                # Map local imports to component names
                imported_components = []
                for imp in local_imports:
                    # Try to find the actual component
                    for other_path, other_meta in self.summaries.items():
                        if other_meta.get('type') == 'component':
                            other_comp = other_meta.get('component_name')
                            if imp.endswith(other_comp) or other_comp in imp:
                                imported_components.append(other_comp)
                
                if imported_components:
                    relationships[comp_name] = imported_components
        
        return relationships
    
    def _get_package_info(self) -> Dict:
        """Get package.json information"""
        package_path = os.path.join(self.app_path, 'package.json')
        
        if os.path.exists(package_path):
            try:
                with open(package_path, 'r') as f:
                    data = json.load(f)
                
                return {
                    "name": data.get('name', 'Unknown'),
                    "version": data.get('version', 'Unknown'),
                    "dependencies": data.get('dependencies', {}),
                    "devDependencies": data.get('devDependencies', {})
                }
            except Exception as e:
                logger.error(f"Error reading package.json: {e}")
        
        return {
            "name": "Unknown",
            "version": "Unknown",
            "dependencies": {},
            "devDependencies": {}
        }
    
    def _count_components(self) -> int:
        """Count total React components"""
        return sum(1 for meta in self.summaries.values() if meta.get('type') == 'component')
