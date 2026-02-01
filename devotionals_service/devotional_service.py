import json
import pdfplumber
import os
import time
from datetime import datetime, timedelta
from docx import Document
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime, timedelta
import time

# Load environment variables
load_dotenv()

# Gemini API setup
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# ---------- Text Extraction ----------

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file using pdfplumber."""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(docx_file):
    """Extract text from DOCX file."""
    doc = Document(docx_file)
    return "\n".join([para.text.strip() for para in doc.paragraphs if para.text.strip()])

# ---------- Gemini: Detect Start/End Dates ----------

def detect_date_range_with_gemini(text):
    """
    Use Gemini AI to detect the earliest and latest dates in a devotional document.
    
    Args:
        text (str): The full text of the devotional document
        
    Returns:
        dict: Dictionary containing 'start_date' and 'end_date' or None if detection fails
    """
    model = genai.GenerativeModel("models/gemini-2.0-flash")
    prompt = f"""
You are a JSON-only API.

From the devotional document below, detect the earliest and latest dates of all the devotional entries present.

Return the result strictly in this JSON format:

{{
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD"
}}

Only include these two fields. No explanations, no markdown, no commentary.

Here is the document:
{text}
"""
    try:
        response = model.generate_content(prompt)
        cleaned = response.text.strip("`json\n").strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"[ERROR] Failed to detect date range: {e}")
        return None

# ---------- Gemini: Extract Devotionals ----------

def process_multiple_days_with_gemini(text, dates):
    """
    Extract devotional entries for multiple specific dates using Gemini AI.
    
    Args:
        text (str): The full text of the devotional document
        dates (list): List of dates in YYYY-MM-DD format
        
    Returns:
        str: JSON string containing extracted devotionals or None if extraction fails
    """
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    date_list_str = ", ".join(dates)

    prompt = f"""
You are a JSON-only API.

From the following devotional document, extract ONLY the devotional entries for the following dates: {date_list_str}.

⚠️ Respond with valid JSON only — do NOT include markdown (like ```), code blocks, explanations, or comments.

Use exactly this structure:

{{
  "devotionals": [
    {{
      "date": "YYYY-MM-DD",
      "title": "Title of devotional",
      "bible_verse": "John 3:16",
      "content": "Full content of the devotional"
    }},
    ...
  ]
}}

✅ Output only devotional entries found in the text.
❌ If no entry is found for a date, skip that date.
❌ Do not add extra commentary or formatting.
✅ Ensure the JSON is properly closed and parseable, always. 
✅ Always ensure the JSON is properly closed and parseable.

Here is the document:
{text}
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[ERROR] Gemini failed for dates {date_list_str}: {e}")
        return None

# ---------- Main Loop ----------

def process_devotionals_by_3_day_chunks(
    file_path,
    output_file="parsed_devotionals_3day.json",
    user_start_date=None,
    user_end_date=None
):
    """
    Process devotional document and extract entries in 3-day chunks.
    
    Args:
        file_path (str): Path to the devotional file (PDF or DOCX)
        output_file (str): Path where the output JSON will be saved
        user_start_date (str): Optional start date in YYYY-MM-DD format
        user_end_date (str): Optional end date in YYYY-MM-DD format
    """
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return

    print(f"[INFO] Reading devotional file: {file_path}")
    text = extract_text_from_pdf(file_path) if file_path.endswith(".pdf") else extract_text_from_docx(file_path)

    # Detect or use provided date range
    if user_start_date and user_end_date:
        start_date = datetime.strptime(user_start_date, "%Y-%m-%d")
        end_date = datetime.strptime(user_end_date, "%Y-%m-%d")
    else:
        print("[INFO] Detecting date range from document...")
        date_range = detect_date_range_with_gemini(text)
        if not date_range:
            print("[ERROR] Could not detect start and end dates. Aborting.")
            return
        start_date = datetime.strptime(date_range["start_date"], "%Y-%m-%d") if not user_start_date else datetime.strptime(user_start_date, "%Y-%m-%d")
        end_date = datetime.strptime(date_range["end_date"], "%Y-%m-%d") if not user_end_date else datetime.strptime(user_end_date, "%Y-%m-%d")

    print(f"[INFO] Processing devotionals from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    devotionals = []
    current_date = start_date

    while current_date <= end_date:
        # Get up to 3 valid dates
        dates = []
        for i in range(3):
            target_date = current_date + timedelta(days=i)
            if target_date <= end_date:
                dates.append(target_date.strftime("%Y-%m-%d"))

        print(f"\n[INFO] Requesting devotionals for: {dates}")
        response = process_multiple_days_with_gemini(text, dates)
        if not response:
            print("[INFO] No response. Ending loop.")
            break

        try:
            cleaned = response.strip("`json\n").strip()
            parsed = json.loads(cleaned)

            day_devotionals = parsed.get("devotionals", [])
            if not day_devotionals:
                print("[INFO] No devotionals returned. Ending loop.")
                break

            devotionals.extend(day_devotionals)
            print(f"[SUCCESS] Retrieved {len(day_devotionals)} devotionals.")

            current_date += timedelta(days=len(day_devotionals))
        except Exception as e:
            print(f"[WARNING] Failed to parse response for {dates}: {e}")
            break

        time.sleep(1)

    # Save output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"devotionals": devotionals}, f, ensure_ascii=False, indent=2)

    print(f"\n[COMPLETE] Extracted {len(devotionals)} devotionals. Saved to {output_file}")

# ---------- Run Example ----------

if __name__ == "__main__":
    # Example file paths (uncomment the one you want to use)
    # file_path = "RHAPSODY_OF_REALITIES_DECEMBER_2024.pdf"
    # file_path = "tube_devo_test1.pdf"
    # file_path = "tube_devo_test1.docx"
    # file_path = "Closer to God each day - 365 devotions for everyday living -- Meyer, Joyce -- ( WeLib.org ).pdf"
    # file_path = "Jesus Calling- Seeking Peace in His Presence.pdf"
    file_path = "New Morning Mercies- A Daily Gospel Devotional (Gift -- Tripp, Paul David -- ( WeLib.org ).pdf"
    # file_path = "openheavens.com.ng.pdf"
    # file_path = "MANAGING YOUR EMOTIONS - daily wisdom for remaining stable -- Joyce Meyer -- ( WeLib.org ).pdf"
    
    # Optional date range (or set to None to auto-detect)
    user_start = None  # e.g., "2024-04-01"
    user_end = None    # e.g., "2024-04-30"

    process_devotionals_by_3_day_chunks(
        file_path,
        output_file="parsed_devotionals_subset.json",
        user_start_date=user_start,
        user_end_date=user_end
    )
