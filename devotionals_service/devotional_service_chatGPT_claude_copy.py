import json
import pdfplumber
from docx import Document
import os
from openai import OpenAI
import atexit
import signal
import sys

# Initialize OpenAI client
openai_api_key = "sk-lDSgtaTXlza3GHbI5dac6COJKcf5noO6gaml0xwSyFT3BlbkFJqIGmo4J39750bF-e80l9mv_c7Zep1gOdPtpG6CSoYA"
client = OpenAI(api_key=openai_api_key)

# Global variable to track if cleanup has been done
_cleanup_done = False

def cleanup_openai():
    """Clean up OpenAI resources"""
    global _cleanup_done
    if not _cleanup_done:
        try:
            # Close any open connections
            if 'client' in globals() and client:
                client.close()
        except Exception:
            pass  # Ignore cleanup errors
        _cleanup_done = True

def signal_handler(signum, frame):
    """Handle system signals for graceful shutdown"""
    cleanup_openai()
    sys.exit(0)

# Register cleanup functions
atexit.register(cleanup_openai)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(docx_file):
    """Extract text from a DOCX file."""
    doc = Document(docx_file)
    return "\n".join(
        [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    ).strip()

def process_with_chatgpt(text):
    """Send text to ChatGPT for structured devotional extraction."""
    try:
        prompt = f"""
        Extract structured data from the following document.
        The document contains daily devotionals, each starting with a date, followed by a title, the bible verse(s) and then multi-paragraph content.

        Extract and return as JSON in the following format:
        {{
          "devotionals": [
            {{
              "date": "YYYY-MM-DD",
              "title": "Title of devotional",
              "bible_verse": "Text of the bible verse (John, 12:14)",
              "content": "Full content of the devotional"
            }},
            ...
          ]
        }}

        Here is the document content:
        {text}
        """

        response = client.chat.completions.create(
            model="gpt-4",  # You can also use "gpt-3.5-turbo" for faster/cheaper processing
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured data from devotional documents. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,  # Adjust based on your needs
            temperature=0.1   # Low temperature for consistent extraction
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error processing with ChatGPT: {e}")
        return None

def process_devotional_document(file_path, auth_token):
    """Process the received PDF or DOCX file and extract structured devotionals"""
    
    try:
        if file_path.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
            print(f"Extracted texts from PDF:\n {text.strip()}")
        elif file_path.endswith(".docx"):
            text = extract_text_from_docx(file_path)
            print(f"Extracted texts from Doc:\n {text.strip()}")
        else:
            print("Error: Unsupported file type")
            return None

        # Process extracted text with ChatGPT
        response = process_with_chatgpt(text)
        if response:
            print(f"\ndevotional response: {response}")
        return response
        
    except Exception as e:
        print(f"Error processing document: {e}")
        return None
    finally:
        # Ensure cleanup happens
        cleanup_openai()

def process_local_devotional_file(file_path):
    """Process a local PDF or DOCX file and extract structured devotionals"""
    
    try:
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found!")
            return None

        if file_path.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif file_path.endswith(".docx"):
            text = extract_text_from_docx(file_path)
        else:
            print("Error: Unsupported file type")
            return None

        # Process extracted text with ChatGPT
        response = process_with_chatgpt(text)
        if response:
            print(f"\n[Last 6000 characters of response]:\n{response[-6000:]}")
            print(f"\ndevotional response: {response}")
        return response
        
    except Exception as e:
        print(f"Error processing local file: {e}")
        return None
    finally:
        # Ensure cleanup happens
        cleanup_openai()

if __name__ == "__main__":
    # Example Usage
    # file_path = "tube_devo_test1.docx"
    # file_path = "tube_devo_test1.pdf"
    file_path = "RHAPSODY_OF_REALITIES_DECEMBER_2024.pdf"
    
    try:
        result = process_local_devotional_file(file_path)
        if result:
            print("Processing completed successfully!")
        else:
            print("Processing failed!")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Final cleanup
        cleanup_openai()
        print("Cleanup completed.")