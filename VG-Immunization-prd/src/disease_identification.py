from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

vaccine_name = "DTaP, Tdap, DT"
prompt = f'''
What disease(s) do the vaccines '{vaccine_name}' protect against? 
Reply with just the disease name(s) alphabetically for each individual vaccine. 
Also make sure the output reflects what the differences are for each vaccine's purpose.
'''
response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
print(response.text)