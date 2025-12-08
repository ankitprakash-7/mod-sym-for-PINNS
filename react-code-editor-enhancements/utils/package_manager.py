"""
Package Manager
Automatically detect and add missing packages to package.json
"""

import re
import json
import logging
import httpx
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class PackageManager:
    """Manage npm packages and dependencies"""
    
    # Predefined package versions for common packages
    KNOWN_PACKAGES = {
        # Charts
        "recharts": "^2.12.7",
        "chart.js": "^4.4.0",
        "react-chartjs-2": "^5.2.0",
        "victory": "^37.0.2",
        
        # Animation
        "framer-motion": "^11.0.0",
        "react-spring": "^9.7.3",
        "gsap": "^3.12.5",
        
        # Forms
        "react-hook-form": "^7.50.0",
        "formik": "^2.4.5",
        "yup": "^1.3.3",
        
        # UI Components
        "lucide-react": "^0.263.1",
        "@radix-ui/react-dialog": "^1.0.5",
        "@radix-ui/react-dropdown-menu": "^2.0.6",
        "@radix-ui/react-select": "^2.0.0",
        "@headlessui/react": "^1.7.18",
        
        # Utilities
        "axios": "^1.6.0",
        "date-fns": "^3.0.0",
        "clsx": "^2.1.0",
        "classnames": "^2.5.1",
        "lodash": "^4.17.21",
        
        # State Management
        "zustand": "^4.5.0",
        "redux": "^5.0.1",
        "@reduxjs/toolkit": "^2.0.1",
        
        # Routing
        "react-router-dom": "^6.21.0",
        
        # Data Fetching
        "swr": "^2.2.4",
        "@tanstack/react-query": "^5.17.0",
        
        # Icons
        "@heroicons/react": "^2.1.1",
        "react-icons": "^5.0.1",
        
        # Boilerplate (should already exist)
        "react": "^19.1.0",
        "react-dom": "^19.1.0",
        "vite": "^7.0.4",
        "tailwindcss": "^3.4.17",
        "@vitejs/plugin-react": "^4.2.1",
    }
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=5.0)
    
    async def analyze_and_update_packages(self, modified_files: Dict[str, str], current_packages: Dict[str, str]) -> Dict[str, str]:
        """
        Analyze modified files and update package.json with missing dependencies
        
        Args:
            modified_files: Dict of file paths to their modified content
            current_packages: Current dependencies from package.json
            
        Returns:
            Updated dependencies dict
        """
        logger.info("Analyzing packages in modified files")
        
        # Extract all imported packages from modified files
        imported_packages = self._extract_imported_packages(modified_files)
        
        logger.info(f"Found {len(imported_packages)} imported packages")
        
        # Find missing packages
        missing_packages = imported_packages - set(current_packages.keys())
        
        if not missing_packages:
            logger.info("No missing packages detected")
            return current_packages
        
        logger.info(f"Missing packages: {missing_packages}")
        
        # Get versions for missing packages
        new_packages = await self._get_package_versions(missing_packages)
        
        # Merge with current packages
        updated_packages = {**current_packages, **new_packages}
        
        # Sort packages alphabetically
        updated_packages = dict(sorted(updated_packages.items()))
        
        logger.info(f"Added {len(new_packages)} new packages")
        
        return updated_packages
    
    def _extract_imported_packages(self, files: Dict[str, str]) -> Set[str]:
        """Extract all external package names from import statements"""
        packages = set()
        
        for file_path, content in files.items():
            # Skip non-JS/JSX files
            if not file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                continue
            
            # Find all import statements
            import_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
            matches = re.findall(import_pattern, content)
            
            for match in matches:
                # Skip local imports (starting with . or /)
                if match.startswith('.') or match.startswith('/'):
                    continue
                
                # Extract package name
                if match.startswith('@'):
                    # Scoped package: @scope/package
                    parts = match.split('/')
                    if len(parts) >= 2:
                        package = f"{parts[0]}/{parts[1]}"
                    else:
                        package = parts[0]
                else:
                    # Regular package
                    package = match.split('/')[0]
                
                packages.add(package)
        
        return packages
    
    async def _get_package_versions(self, packages: Set[str]) -> Dict[str, str]:
        """Get versions for packages"""
        versions = {}
        
        for package in packages:
            # Check if we have a known version
            if package in self.KNOWN_PACKAGES:
                versions[package] = self.KNOWN_PACKAGES[package]
                logger.debug(f"Using known version for {package}: {self.KNOWN_PACKAGES[package]}")
            else:
                # Fetch from npm registry
                version = await self._fetch_latest_version(package)
                if version:
                    versions[package] = version
                else:
                    # Fallback to latest
                    versions[package] = "latest"
                    logger.warning(f"Could not determine version for {package}, using 'latest'")
        
        return versions
    
    async def _fetch_latest_version(self, package: str) -> str:
        """Fetch latest version from npm registry"""
        try:
            url = f"https://registry.npmjs.org/{package}/latest"
            response = await self.http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                version = data.get('version')
                if version:
                    logger.debug(f"Fetched version for {package}: ^{version}")
                    return f"^{version}"
            
            logger.warning(f"Could not fetch version for {package}: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching version for {package}: {e}")
            return None
    
    def update_package_json_content(self, content: str, new_dependencies: Dict[str, str]) -> str:
        """Update package.json content with new dependencies"""
        try:
            data = json.loads(content)
            
            # Update dependencies
            data['dependencies'] = new_dependencies
            
            # Pretty print with 2-space indentation
            updated_content = json.dumps(data, indent=2)
            
            logger.info("Updated package.json content")
            
            return updated_content
            
        except Exception as e:
            logger.error(f"Error updating package.json: {e}")
            return content
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
