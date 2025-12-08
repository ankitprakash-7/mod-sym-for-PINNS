"""
React Code Editor FastAPI Microservice
Two-phase LLM approach with intelligent file selection
"""

import os
import json
import shutil
import tempfile
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from utils import (
    GCSManager,
    MetadataExtractor,
    LLMClient,
    PackageManager,
    ResponseParser
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('react_editor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Settings
class Settings(BaseSettings):
    # GCS Configuration
    gcs_code_files_bucket: str = "prompttoapp-codefiles"  # ZIP files bucket
    gcs_code_folders_bucket: str = "prompttoapp-codefolders"  # Unzipped folders bucket
    google_application_credentials: Optional[str] = None
    
    # Vertex AI Configuration
    google_cloud_project: str
    google_cloud_location: str = "us-central1"
    
    # Local Testing
    use_local_files: bool = False
    local_files_path: str = "/tmp/sample_app"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    
    # LLM Configuration
    llm_model: str = "gemini-2.0-flash-exp"
    llm_temperature: float = 0.1
    llm_max_output_tokens: int = 8000
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env


settings = Settings()


# Pydantic Models
class EditRequest(BaseModel):
    app_id: str = Field(..., description="Application ID")
    msg_id: str = Field(..., description="Message ID (new version to create)")
    active_msg_id: str = Field(..., description="Active Message ID (current version to download from)")
    instruction: str = Field(..., description="Natural language editing instruction")


class EditResponse(BaseModel):
    success: bool
    message: str
    files_modified: Optional[list] = None
    files_added: Optional[list] = None
    packages_added: Optional[list] = None
    explanation: Optional[str] = None
    error: Optional[str] = None
    debug_info: Optional[dict] = None


# Global managers
gcs_manager: Optional[GCSManager] = None
llm_client: Optional[LLMClient] = None
package_manager: Optional[PackageManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources"""
    global gcs_manager, llm_client, package_manager
    
    logger.info("Initializing React Code Editor API...")
    
    # Initialize managers
    gcs_manager = GCSManager(
        code_files_bucket=settings.gcs_code_files_bucket,
        code_folders_bucket=settings.gcs_code_folders_bucket,
        use_local=settings.use_local_files,
        local_path=settings.local_files_path
    )
    
    llm_client = LLMClient(
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        model=settings.llm_model
    )
    
    package_manager = PackageManager()
    
    logger.info("✅ API initialized successfully")
    
    yield
    
    # Cleanup
    logger.info("Shutting down API...")
    await package_manager.close()


# FastAPI app
app = FastAPI(
    title="React Code Editor API",
    description="AI-powered React code editing with two-phase LLM approach",
    version="2.0.0",
    lifespan=lifespan
)


@app.post("/edit", response_model=EditResponse)
async def edit_app(request: EditRequest):
    """
    Edit a React application based on natural language instruction
    
    Process:
    1. Download app from GCS
    2. Extract metadata (fast, no LLM)
    3. Phase 1: LLM selects relevant files
    4. Load selected files
    5. Phase 2: LLM generates edits
    6. Apply changes and update packages
    7. Upload back to GCS
    """
    logger.info("="*80)
    logger.info(f"NEW EDIT REQUEST")
    logger.info(f"App ID: {request.app_id}")
    logger.info(f"Active Message ID (download from): {request.active_msg_id}")
    logger.info(f"New Message ID (save to): {request.msg_id}")
    logger.info(f"Instruction: {request.instruction}")
    logger.info("="*80)
    
    temp_dir = None
    
    try:
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="react_edit_")
        logger.info(f"Working directory: {temp_dir}")
        
        # Step 1: Download app from GCS using active_msg_id
        logger.info(f"📥 Step 1: Downloading app from active version ({request.active_msg_id})...")
        try:
            app_path = gcs_manager.download_app(request.app_id, request.active_msg_id, temp_dir)
        except FileNotFoundError as e:
            logger.error(f"App not found: {e}")
            return EditResponse(
                success=False,
                message=f"Active Message ID '{request.active_msg_id}' not found in app '{request.app_id}'",
                error=str(e)
            )
        
        logger.info(f"✅ Downloaded to: {app_path}")
        
        # Step 2: Extract metadata (fast, no LLM)
        logger.info("🔍 Step 2: Extracting metadata...")
        extractor = MetadataExtractor(app_path)
        metadata = extractor.analyze_app()
        
        logger.info(f"✅ Analyzed {metadata['total_files']} files, {metadata['component_count']} components")
        
        # Step 3: Phase 1 - LLM selects files
        logger.info("🤖 Step 3: Phase 1 - Selecting relevant files...")
        file_selection = await llm_client.select_files(request.instruction, metadata)
        
        selected_file_paths = [f['path'] for f in file_selection.get('files_needed', []) if not f.get('is_new', False)]
        new_file_paths = [f for f in file_selection.get('files_needed', []) if f.get('is_new', False)]
        
        logger.info(f"✅ Selected {len(selected_file_paths)} existing files and {len(new_file_paths)} new files to create:")
        for f in file_selection.get('files_needed', []):
            file_type = "NEW" if f.get('is_new', False) else "EXISTING"
            logger.info(f"   • [{file_type}] {f['path']} - {f['reason']}")
        
        # Step 4: Load selected files
        logger.info("📂 Step 4: Loading selected files...")
        selected_files = {}
        
        for file_path in selected_file_paths:
            full_path = os.path.join(app_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    selected_files[file_path] = f.read()
                logger.info(f"   ✅ Loaded: {file_path} ({len(selected_files[file_path])} chars)")
            else:
                logger.warning(f"   ⚠️ File not found: {file_path}")
        
        if not selected_files:
            raise Exception("No files were successfully loaded")
        
        # Step 5: Phase 2 - LLM generates edits
        logger.info("🤖 Step 5: Phase 2 - Generating code edits...")
        llm_response = await llm_client.edit_code(
            request.instruction,
            selected_files,
            metadata,
            file_selection  # Pass Phase 1 result to Phase 2
        )
        
        logger.info(f"✅ Received response ({len(llm_response)} chars)")
        
        # Log first 500 chars of response for debugging
        logger.debug(f"LLM Response preview: {llm_response[:500]}...")
        
        # Step 6: Parse response and apply changes
        logger.info("📝 Step 6: Parsing and applying changes...")
        modified_files, explanation = ResponseParser.parse_modified_files(llm_response)
        
        if not modified_files:
            # Log full response if parsing failed
            logger.error("❌ PARSING FAILED - Full LLM Response:")
            logger.error(llm_response)
            raise Exception("No modified files extracted from LLM response. Check logs for full response.")
        
        logger.info(f"✅ Extracted {len(modified_files)} modified files")
        
        # Validate files
        validation_issues = ResponseParser.validate_files(modified_files)
        if validation_issues:
            logger.warning("⚠️ Validation issues found:")
            for issue in validation_issues:
                logger.warning(f"   • {issue}")
        
        # Step 7: Update packages if needed
        logger.info("📦 Step 7: Checking for new packages...")
        
        # Get current package.json
        package_json_path = os.path.join(app_path, 'package.json')
        current_packages = {}
        
        if os.path.exists(package_json_path):
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                current_packages = package_data.get('dependencies', {})
        
        # Analyze and update packages
        updated_packages = await package_manager.analyze_and_update_packages(
            modified_files,
            current_packages
        )
        
        packages_added = list(set(updated_packages.keys()) - set(current_packages.keys()))
        
        if packages_added:
            logger.info(f"✅ Adding {len(packages_added)} new packages: {packages_added}")
            
            # Update package.json in modified_files
            if 'package.json' in modified_files:
                modified_files['package.json'] = package_manager.update_package_json_content(
                    modified_files['package.json'],
                    updated_packages
                )
            else:
                # Read, update, and add to modified files
                with open(package_json_path, 'r') as f:
                    package_content = f.read()
                modified_files['package.json'] = package_manager.update_package_json_content(
                    package_content,
                    updated_packages
                )
        else:
            logger.info("✅ No new packages needed")
        
        # Step 8: Write modified files
        logger.info("💾 Step 8: Writing modified files to disk...")
        files_written = []
        
        for file_path, content in modified_files.items():
            full_path = os.path.join(app_path, file_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            files_written.append(file_path)
            logger.info(f"   ✅ Wrote: {file_path}")
        
        # Step 9: Upload to GCS
        logger.info(f"☁️ Step 9: Uploading to GCS as new version ({request.msg_id})...")
        upload_result = gcs_manager.upload_app(app_path, request.app_id, request.msg_id)
        
        logger.info(f"✅ Uploaded {upload_result['files_uploaded']} files to GCS")
        logger.info(f"   New version created at: {request.msg_id}")
        logger.info(f"   Original version preserved at: {request.active_msg_id}")
        
        # Determine which files were added vs modified
        existing_files = set(metadata['file_summaries'].keys())
        files_modified_list = [f for f in files_written if f in existing_files]
        files_added_list = [f for f in files_written if f not in existing_files]
        
        logger.info("="*80)
        logger.info("✅ EDIT COMPLETED SUCCESSFULLY")
        logger.info(f"Modified: {len(files_modified_list)} files")
        logger.info(f"Added: {len(files_added_list)} files")
        logger.info(f"Packages added: {len(packages_added)}")
        logger.info("="*80)
        
        return EditResponse(
            success=True,
            message="App edited successfully",
            files_modified=files_modified_list,
            files_added=files_added_list,
            packages_added=packages_added,
            explanation=explanation,
            debug_info={
                "selected_files_count": len(selected_file_paths),
                "estimated_scope": file_selection.get('estimated_scope'),
                "confidence": file_selection.get('confidence'),
                "validation_issues": validation_issues if validation_issues else None
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error during edit process: {str(e)}")
        logger.exception("Full traceback:")
        
        return EditResponse(
            success=False,
            message="Edit failed",
            error=str(e)
        )
        
    finally:
        # Cleanup temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"🧹 Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp directory: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "React Code Editor API",
        "version": "2.0.0",
        "local_mode": settings.use_local_files
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "React Code Editor API",
        "version": "2.0.0",
        "architecture": "Two-phase LLM approach",
        "endpoints": {
            "edit": "POST /edit - Edit React app based on instruction",
            "health": "GET /health - Health check"
        },
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting React Code Editor API...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled auto-reload to avoid log file triggering
        log_level="info"
    )
