import os
import io
import json
import time
import re
import gc
from pathlib import Path
from typing import Optional, List, Dict

# FastAPI imports
from fastapi import FastAPI, File, UploadFile, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse

# Document processing imports
import pdfplumber
from docx import Document
import google.generativeai as genai
from google.api_core import exceptions

# System monitoring
# import psutil

# Configuration
DEFAULT_CHUNK_SIZE = 25000
MAX_SINGLE_CHUNK = 30000
CHUNK_OVERLAP = 2000

# Configure Gemini AI (make sure to set your API key)
# genai.configure(api_key="YOUR_GEMINI_API_KEY")


# =============================================================================
# TEXT EXTRACTION FUNCTIONS
# =============================================================================

def extract_text_from_pdf_content(file_content: bytes) -> str:
    """Extract text from PDF file content using pdfplumber"""
    try:
        pdf_file = io.BytesIO(file_content)
        text = ""
        
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text(layout=True)
                if page_text:
                    text += f"--- Page {page_num + 1} ---\n"
                    text += page_text + "\n\n"
                
                # Extract tables if present
                tables = page.extract_tables()
                if tables:
                    for table_num, table in enumerate(tables):
                        text += f"--- Table {table_num + 1} on Page {page_num + 1} ---\n"
                        for row in table:
                            if row:
                                text += " | ".join([cell or "" for cell in row]) + "\n"
                        text += "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")


def extract_text_from_docx_content(file_content: bytes) -> str:
    """Extract text from DOCX file content"""
    try:
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)
        
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error extracting text from DOCX: {str(e)}")


def extract_text_from_txt_content(file_content: bytes) -> str:
    """Extract text from TXT file content"""
    try:
        # Try different encodings
        for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
            try:
                text = file_content.decode(encoding)
                return text.strip()
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail
        raise ValueError("Could not decode text file with any supported encoding")
        
    except Exception as e:
        raise ValueError(f"Error extracting text from TXT: {str(e)}")


# =============================================================================
# SMART CHUNKING FUNCTIONS
# =============================================================================

def smart_chunk_devotional_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> List[str]:
    """Split text at devotional boundaries, not arbitrary character limits"""
    
    # Common devotional separators (adjust based on your document format)
    separators = [
        r'\n\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}',  # Date patterns like "12/25/2024"
        r'\n\s*\w+\s+\d{1,2},?\s+\d{4}',      # "December 25, 2024"
        r'\n\s*DAY\s+\d+',                     # "DAY 1", "DAY 2"
        r'\n\s*\d{1,2}(st|nd|rd|th)\s+\w+',   # "1st January"
        r'\n\s*\d{1,2}\.\s*\w+',              # "25. December"
    ]
    
    # Find all potential devotional start positions
    split_positions = []
    for pattern in separators:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            split_positions.append(match.start())
    
    # Sort positions and remove duplicates
    split_positions = sorted(set(split_positions))
    
    if not split_positions:
        print("No devotional patterns found - using paragraph chunking")
        paragraphs = text.split('\n\n')
        return create_chunks_from_paragraphs(paragraphs, chunk_size)
    
    print(f"Found {len(split_positions)} potential devotional boundaries")
    
    # Create chunks based on devotional boundaries
    chunks = []
    start = 0
    current_chunk = ""
    
    for pos in split_positions:
        section = text[start:pos]
        
        if len(current_chunk + section) <= chunk_size:
            current_chunk += section
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = section
        
        start = pos
    
    # Add remaining text
    if start < len(text):
        remaining = text[start:]
        if len(current_chunk + remaining) <= chunk_size:
            current_chunk += remaining
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            chunks.append(remaining.strip())
    
    if current_chunk and current_chunk.strip() not in [c.strip() for c in chunks]:
        chunks.append(current_chunk.strip())
    
    return [chunk for chunk in chunks if chunk.strip()]


def create_chunks_from_paragraphs(paragraphs: List[str], chunk_size: int) -> List[str]:
    """Fallback chunking by paragraphs"""
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk + paragraph) <= chunk_size:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def create_overlapping_chunks(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Create overlapping chunks to ensure no devotional is split"""
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunks.append(text[start:])
            break
        
        # Find a good break point (end of paragraph or sentence)
        break_point = end
        for i in range(max(0, end - overlap), end):
            if i < len(text) - 1 and text[i:i+2] == '\n\n':  # Paragraph break
                break_point = i + 2
                break
            elif i < len(text) and text[i] in '.!?':  # Sentence end
                break_point = i + 1
        
        chunks.append(text[start:break_point])
        start = max(start + 1, break_point - overlap)  # Overlap to catch split devotionals
    
    return [chunk for chunk in chunks if chunk.strip()]


# =============================================================================
# GEMINI AI PROCESSING FUNCTIONS
# =============================================================================

def process_with_gemini_safe(text: str, auth_token: str, church_id: Optional[str] = None, timeout: int = 300) -> str:
    """Process text with Gemini AI with safety measures"""
    
    # Check available memory
    # memory = psutil.virtual_memory()
    # if memory.percent > 85:
    #     print("Warning: High memory usage detected")
    #     gc.collect()
    
    try:
        # Validate inputs
        if not text or not text.strip():
            raise ValueError("No text provided for processing")
        
        if not auth_token:
            raise ValueError("Authentication token is required")
        
        # Limit text based on available resources
        max_chars = min(MAX_SINGLE_CHUNK, len(text))
        # if memory.percent > 70:
        #     max_chars = min(20000, len(text))
        # max_chars = min(20000, len(text))
        limited_text = text[:max_chars]
        
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        prompt = f"""
        Extract structured devotional data from this document.
        
        Instructions:
        1. Identify each devotional entry carefully
        2. Extract the date in YYYY-MM-DD format (convert month names to numbers)
        3. Extract the title/heading of each devotional
        4. Extract the bible verse reference and text
        5. Extract the full devotional content/message
        6. Only include COMPLETE devotionals
        
        Return ONLY valid JSON in this exact format:
        {{
          "church_id": "{church_id or 'unknown'}",
          "total_devotionals": <number>,
          "devotionals": [
            {{
              "date": "YYYY-MM-DD",
              "title": "Title of devotional",
              "bible_verse": "Verse reference and text",
              "content": "Full content of the devotional"
            }}
          ]
        }}

        Document content:
        {limited_text}
        """
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=4096,
                candidate_count=1,
            )
        )
        
        if not response or not response.text:
            raise ValueError("Empty response from Gemini AI")
        
        # Clean and validate response
        response_text = response.text.strip()
        
        # Remove markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Validate JSON
        parsed_response = json.loads(response_text)
        
        # Ensure required fields
        if "devotionals" not in parsed_response:
            parsed_response["devotionals"] = []
        
        parsed_response["church_id"] = church_id or "unknown"
        parsed_response["total_devotionals"] = len(parsed_response.get("devotionals", []))
        
        return json.dumps(parsed_response, indent=2)
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        error_response = {
            "error": f"Invalid JSON response from Gemini AI: {str(e)}",
            "church_id": church_id or "unknown",
            "total_devotionals": 0,
            "devotionals": []
        }
        return json.dumps(error_response)
    except exceptions.DeadlineExceeded:
        print("Gemini API timeout")
        error_response = {
            "error": "Processing timeout - document too large or slow network",
            "church_id": church_id or "unknown",
            "total_devotionals": 0,
            "devotionals": []
        }
        return json.dumps(error_response)
    except Exception as e:
        print(f"Gemini processing error: {str(e)}")
        error_response = {
            "error": str(e),
            "church_id": church_id or "unknown",
            "total_devotionals": 0,
            "devotionals": []
        }
        return json.dumps(error_response)
    finally:
        gc.collect()
        print("All done")


def process_large_document_smart(text: str, auth_token: str, church_id: Optional[str] = None) -> str:
    """Process large documents with smart devotional-aware chunking"""
    
    print(f"Document size: {len(text)} characters - using smart chunking")
    
    # Smart chunking at devotional boundaries
    chunks = smart_chunk_devotional_text(text, chunk_size=DEFAULT_CHUNK_SIZE)
    print(f"Created {len(chunks)} smart chunks")
    
    all_devotionals = []
    processed_dates = set()  # Track dates to avoid duplicates
    
    for i, chunk in enumerate(chunks):
        try:
            print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            
            # Add delay to avoid rate limiting
            if i > 0:
                time.sleep(2)
            
            # Enhanced prompt for chunk processing
            chunk_prompt = f"""
            Extract devotionals from this text chunk. This may be part of a larger document.
            
            IMPORTANT: Only extract COMPLETE devotionals. If a devotional appears to be cut off at the beginning or end, ignore it.
            
            Return JSON format:
            {{
              "devotionals": [
                {{
                  "date": "YYYY-MM-DD",
                  "title": "complete title",
                  "bible_verse": "complete verse",
                  "content": "complete content"
                }}
              ]
            }}
            
            Text chunk:
            {chunk}
            """
            
            model = genai.GenerativeModel("models/gemini-1.5-flash")
            response = model.generate_content(
                chunk_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                )
            )
            
            # Parse response
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            if response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            chunk_data = json.loads(response_text)
            
            if "devotionals" in chunk_data:
                for devotional in chunk_data["devotionals"]:
                    # Check for completeness and avoid duplicates
                    if (devotional.get("date") and 
                        devotional.get("title") and 
                        devotional.get("content") and
                        len(devotional["content"]) > 50 and  # Minimum content length
                        devotional["date"] not in processed_dates):
                        
                        all_devotionals.append(devotional)
                        processed_dates.add(devotional["date"])
                        
                print(f"Chunk {i+1}: Found {len(chunk_data['devotionals'])} devotionals")
                
        except Exception as e:
            print(f"Error processing chunk {i+1}: {str(e)}")
            continue
    
    # Sort devotionals by date
    try:
        all_devotionals.sort(key=lambda x: x.get("date", ""))
    except Exception as e:
        print(f"Error sorting devotionals: {str(e)}")
    
    final_result = {
        "church_id": church_id or "unknown",
        "total_devotionals": len(all_devotionals),
        "devotionals": all_devotionals,
        "processing_info": {
            "total_chunks": len(chunks),
            "original_text_length": len(text)
        }
    }
    
    print(f"Final result: {len(all_devotionals)} complete devotionals extracted")
    return json.dumps(final_result, indent=2)


# =============================================================================
# MAIN PROCESSING FUNCTIONS
# =============================================================================

def process_devotional_document(filename: str, file_content: bytes, auth_token: str, church_id: Optional[str] = None) -> str:
    """Process uploaded devotional document with smart handling"""
    
    file_extension = Path(filename).suffix.lower()
    
    try:
        # Extract text based on file type
        if file_extension == ".pdf":
            text = extract_text_from_pdf_content(file_content)
            print(f"Extracted texts from PDF:\n {text[:200]}...")
        elif file_extension in [".docx", ".doc"]:
            text = extract_text_from_docx_content(file_content)
            print(f"Extracted texts from Doc:\n {text[:200]}...")
        elif file_extension == ".txt":
            text = extract_text_from_txt_content(file_content)
            print(f"Extracted texts from TXT:\n {text[:200]}...")
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        if not text or not text.strip():
            raise ValueError("No text could be extracted from the file")
        
        print(f"Total extracted text length: {len(text)} characters")
        
        # Choose processing method based on text size
        if len(text) > MAX_SINGLE_CHUNK:
            print("Large document detected - using smart chunking")
            response = process_large_document_smart(text, auth_token, church_id)
        else:
            print("Processing as single document")
            response = process_with_gemini_safe(text, auth_token, church_id)
        
        return response
        
    except Exception as e:
        print(f"Error processing devotional document: {str(e)}")
        raise


def process_local_devotional_file(file_path: str, auth_token: Optional[str] = None, church_id: Optional[str] = None) -> Optional[str]:
    """Process a local PDF, DOCX, or TXT file and extract structured devotionals"""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found!")
        return None

    try:
        # Read file content as bytes
        with open(file_path, 'rb') as file:
            file_content = file.read()
        
        # Get filename from path
        filename = os.path.basename(file_path)
        
        print(f"Processing local file: {filename}")
        
        # Use the main processing function
        response = process_devotional_document(
            filename=filename, 
            file_content=file_content,
            auth_token=auth_token or "local_token",
            church_id=church_id
        )
        
        print(f"\nDevotional processing completed!")
        return response
        
    except Exception as e:
        print(f"Error processing local file: {str(e)}")
        return None


# Example Usage
# file_path = "tube_devo_test1.docx"
# file_path = "tube_devo_test1.pdf"
file_path = "RHAPSODY_OF_REALITIES_DECEMBER_2024.pdf"
process_local_devotional_file(file_path)
