"""
Google Cloud Storage Manager
Handles downloads and uploads to both buckets
"""

import os
import shutil
import zipfile
import logging
from pathlib import Path
from typing import Optional
from google.cloud import storage

logger = logging.getLogger(__name__)


class GCSManager:
    """Manages Google Cloud Storage operations for app code"""
    
    def __init__(self, code_files_bucket: str, code_folders_bucket: str, use_local: bool = False, local_path: Optional[str] = None):
        self.use_local = use_local
        self.local_path = local_path
        
        if not use_local:
            self.storage_client = storage.Client()
            # code_files_bucket = ZIP files
            # code_folders_bucket = Unzipped folders
            self.zip_bucket = self.storage_client.bucket(code_files_bucket)
            self.folders_bucket = self.storage_client.bucket(code_folders_bucket)
            logger.info(f"GCS Manager initialized - ZIP bucket: {code_files_bucket}, Folders bucket: {code_folders_bucket}")
        else:
            logger.info(f"GCS Manager initialized in LOCAL MODE: {local_path}")
    
    def download_app(self, app_id: str, msg_id: str, dest_path: str) -> str:
        """
        Download app zip from GCS and extract
        
        Args:
            app_id: Application ID
            msg_id: Message ID
            dest_path: Local destination path
            
        Returns:
            Path to extracted app directory
            
        Raises:
            FileNotFoundError: If msg_id doesn't exist in GCS
        """
        if self.use_local:
            return self._download_local(dest_path)
        
        zip_path = os.path.join(dest_path, "app.zip")
        extract_path = os.path.join(dest_path, "app")
        
        # Download from: prompttoapp-codefiles/{app_id}/{msg_id}.zip (ZIP bucket)
        gcs_path = f"{app_id}/{msg_id}.zip"
        
        logger.info(f"Downloading app from GCS ZIP bucket: {gcs_path}")
        
        try:
            blob = self.zip_bucket.blob(gcs_path)
            
            if not blob.exists():
                raise FileNotFoundError(
                    f"Message ID '{msg_id}' not found in app '{app_id}'. "
                    f"GCS path: {gcs_path}"
                )
            
            # Download zip
            os.makedirs(dest_path, exist_ok=True)
            blob.download_to_filename(zip_path)
            
            logger.info(f"Downloaded {os.path.getsize(zip_path)} bytes")
            
            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            
            logger.info(f"Extracted app to: {extract_path}")
            
            # Clean up zip
            os.remove(zip_path)
            
            return extract_path
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to download app from GCS: {e}")
            raise Exception(f"GCS download failed: {str(e)}")
    
    def _download_local(self, dest_path: str) -> str:
        """Copy local files for testing"""
        extract_path = os.path.join(dest_path, "app")
        
        if not os.path.exists(self.local_path):
            raise FileNotFoundError(f"Local path not found: {self.local_path}")
        
        # Copy directory
        shutil.copytree(self.local_path, extract_path, dirs_exist_ok=True)
        logger.info(f"Copied local app to: {extract_path}")
        
        return extract_path
    
    def upload_app(self, app_path: str, app_id: str, msg_id: str) -> dict:
        """
        Upload app to both GCS buckets:
        1. Unzipped files to: prompttoapp-codefolders/{app_id}/{msg_id}/ (Folders bucket)
        2. Zip file to: prompttoapp-codefiles/{app_id}/{msg_id}.zip (ZIP bucket)
        
        Args:
            app_path: Local path to app directory
            app_id: Application ID
            msg_id: Message ID
            
        Returns:
            Dict with upload status
        """
        if self.use_local:
            return self._upload_local(app_path)
        
        try:
            # Step 1: Upload unzipped files to FOLDERS bucket
            logger.info(f"Uploading unzipped files to FOLDERS bucket: {app_id}/{msg_id}/")
            files_uploaded = self._upload_unzipped_files(app_path, app_id, msg_id)
            
            # Step 2: Create and upload zip to ZIP bucket
            logger.info(f"Creating and uploading zip to ZIP bucket: {app_id}/{msg_id}.zip")
            zip_path = self._create_zip(app_path)
            self._upload_zip(zip_path, app_id, msg_id)
            
            # Clean up
            os.remove(zip_path)
            
            logger.info(f"Successfully uploaded app: {files_uploaded} files")
            
            return {
                "success": True,
                "files_uploaded": files_uploaded,
                "folders_path": f"{app_id}/{msg_id}/",
                "zip_path": f"{app_id}/{msg_id}.zip"
            }
            
        except Exception as e:
            logger.error(f"Failed to upload app to GCS: {e}")
            raise Exception(f"GCS upload failed: {str(e)}")
    
    def _upload_unzipped_files(self, app_path: str, app_id: str, msg_id: str) -> int:
        """Upload all files to folders_bucket (unzipped files bucket)"""
        base_gcs_path = f"{app_id}/{msg_id}"
        file_count = 0
        
        for root, dirs, files in os.walk(app_path):
            # Skip node_modules and build directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist', 'build', '.git']]
            
            for file in files:
                local_file_path = os.path.join(root, file)
                rel_path = os.path.relpath(local_file_path, app_path)
                gcs_path = f"{base_gcs_path}/{rel_path}"
                
                blob = self.folders_bucket.blob(gcs_path)
                blob.upload_from_filename(local_file_path)
                file_count += 1
        
        return file_count
    
    def _create_zip(self, app_path: str) -> str:
        """Create zip file of app directory"""
        zip_path = f"{app_path}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(app_path):
                # Skip node_modules
                dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist', 'build', '.git']]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, app_path)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def _upload_zip(self, zip_path: str, app_id: str, msg_id: str):
        """Upload zip to zip_bucket (ZIP files bucket)"""
        gcs_path = f"{app_id}/{msg_id}.zip"
        
        blob = self.zip_bucket.blob(gcs_path)
        blob.upload_from_filename(zip_path)
        
        logger.info(f"Uploaded zip ({os.path.getsize(zip_path)} bytes) to ZIP bucket: {gcs_path}")
    
    def _upload_local(self, app_path: str) -> dict:
        """Mock upload for local testing"""
        logger.info(f"LOCAL MODE: Would upload app from: {app_path}")
        
        # Count files
        file_count = sum(1 for _ in Path(app_path).rglob('*') if _.is_file())
        
        return {
            "success": True,
            "files_uploaded": file_count,
            "code_files_path": "local/mock/path/",
            "zip_path": "local/mock/path.zip"
        }
