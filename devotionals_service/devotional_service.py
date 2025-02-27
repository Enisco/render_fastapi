import json
import pdfplumber
from docx import Document
import os
import google.generativeai as genai

gemini_ai_api_key = "AIzaSyDgFx4bfhJG4RkzxEs10J6yZkK-3jVfYmU"
genai.configure(api_key=gemini_ai_api_key)


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


def process_with_gemini(text):
    """Send text to Gemini AI for structured devotional extraction."""
    model = genai.GenerativeModel("models/gemini-1.5-flash")

    prompt = f"""
    Extract structured data from the following document.
    The document contains daily devotionals, each starting with a date, followed by a title, and then multi-paragraph content.

    Extract and return as JSON in the following format:
    {{
      "devotionals": [
        {{
          "date": "YYYY-MM-DD",
          "title": "Title of devotional",
          "content": "Full content of the devotional"
        }},
        ...
      ]
    }}

    Here is the document content:
    {text}
    """

    response = model.generate_content(prompt)

    return response.text


def process_devotional_document(file_path):
    """Process the received PDF or DOCX file and extract structured devotionals"""

    if file_path.endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        text = extract_text_from_docx(file_path)
    else:
        print("Error: Unsupported file type")
        return

    # Process extracted text with Gemini AI
    response = process_with_gemini(text)
    print(f"\ndevotional response: {response}:")
    return response


def process_local_devotional_file(file_path):
    """Process a local PDF or DOCX file and extract structured devotionals"""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found!")
        return

    if file_path.endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        text = extract_text_from_docx(file_path)
    else:
        print("Error: Unsupported file type")
        return

    # Process extracted text with Gemini AI
    response = process_with_gemini(text)
    print(f"\ndevotional response: {response}:")
    return response


# Example Usage
# file_path = "tube_devo_test1.docx"
# file_path = "tube_devo_test1.pdf"
file_path = "RHAPSODY_OF_REALITIES_DECEMBER_2024.pdf"
process_local_devotional_file(file_path)
