from google import genai
from google.genai import types
import json
from dotenv import load_dotenv
import os
import pathlib
import pandas as pd

load_dotenv()
def load_file(path):
    suffix = pathlib.Path(path).suffix.lower()
    if suffix == ".csv":
        return None
    mime_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png"
    }
    mime_type = mime_types.get(suffix, "application/pdf")
    return types.Part.from_bytes(
        mime_type=mime_type,
        data=pathlib.Path(path).read_bytes()
    )

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Prompt: extract vaccine records into Dataset A schema
prompt = """Extract all vaccine dose records from this Certificate of Immunization (COI) document.

For each dose found in the table, return a nested JSON object with these fields:
- user_id: a unique id like "user_001", "user_002", etc. that represents each individual vaccination record
- patient_name: full name of the vaccination record's owner
- record_id: a unique id like "rec_001", "rec_002", etc.
- vaccine_name: the vaccine name/abbreviation as shown (e.g., "DTaP-Hib-IPV", "MMRV")
- dose_date: the date in ISO 8601 format (YYYY-MM-DD)
- manufacturer: leave as "Unknown" if not specified
- lot_number: leave as "Unknown" if not specified
- provider: Administering provider/physician, leave as "Unknown" if not specified
- clinic: use the Clinic or facility name if available, or else put "Unknown"

Return ONLY a JSON array of these objects, no other text, no markdown formatting."""
def clean_json(text):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return text.strip()

def extract_csv(path):
    df = pd.read_csv(path)
    
    # process in chunks of 100 rows at a time
    chunk_size = 100
    all_records = []
    
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        csv_text = chunk.to_string(index=False)
        
        print(f"Processing rows {i} to {i+len(chunk)}...")
        
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[f"{prompt}\n\nHere is the CSV data:\n{csv_text}"]
        )
        
        try:
            records = json.loads(clean_json(response.text))
            all_records.extend(records)
        except json.JSONDecodeError as e:
            print(f"Failed to parse chunk {i}: {e}")
            continue
    
    print(f"Extracted {len(all_records)} total records")
    return all_records

def extract_file(file_path):
    file = load_file(file_path)
    response = client.models.generate_content(model="gemini-3.5-flash", contents=[file, prompt])

    records = json.loads(clean_json(response.text))

    with open("data/extracted_records.json", "w") as f:
        json.dump(records, f, indent=2)

    print(f"\nExtracted {len(records)} records → saved to extracted_records.json")

extract_file("data/immprintmanualcoi.pdf")