# composite_optimizer/sub_agents/knowledge_processing/tools.py

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

"""Tools for knowledge processing and document analysis"""

import fitz  # PyMuPDF
import requests
from io import BytesIO


def give_context(url: str) -> dict:
    """
    Extracts and returns the main textual content from the specified PDF URL.
    This is used to extract autoclave specifications from technical documents.

    Args:
        url: URL of the PDF document containing autoclave specifications

    Returns:
        dict: Status and extracted text content from the PDF document
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        pdf_file = BytesIO(response.content)
        doc = fitz.open(stream=pdf_file, filetype="pdf")
        text = ""
        
        for page in doc:
            text += page.get_text()
        
        doc.close()
        
        return {
            "status": "success",
            "content": text,
            "message": f"Successfully extracted content from PDF document",
            "url": url,
            "text_length": len(text)
        }
        
    except requests.RequestException as e:
        return {
            "status": "error",
            "message": f"Error downloading PDF from {url}: {str(e)}",
            "url": url,
            "content": None
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Error processing PDF document: {str(e)}",
            "url": url,
            "content": None
        }