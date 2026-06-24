from google import genai
from google.genai import types
import json
from dotenv import load_dotenv
import os
import pathlib

load_dotenv()
pdf_bytes = pathlib.Path("data/immprintmanualcoi.pdf").read_bytes()
pdf_file1 = types.Part.from_bytes(
    mime_type= "application/pdf",
    data = pdf_bytes
)

image_bytes = pathlib.Path("data/3758110765_57001f4395_o.jpg").read_bytes()
pdf_file2 = types.Part.from_bytes(
    mime_type= "image/jpeg",
    data= image_bytes
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

response = client.models.generate_content(model="gemini-3.5-flash", contents=[pdf_file2, prompt])
# response = model.generate_content([pdf_file2, prompt])

# Clean up response
text = response.text.strip()
if text.startswith("```"):
    text = text.split("```")[1]
    if text.startswith("json"):
        text = text[4:]

# Parse and pretty-print
records = json.loads(text)
print(json.dumps(records, indent=2))

# Save to file
with open("data/extracted_records.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"\nExtracted {len(records)} records → saved to extracted_records.json")