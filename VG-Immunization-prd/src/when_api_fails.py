from google import genai
from google.genai.types import HttpOptions
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"), http_options=HttpOptions(api_version="v1"))
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="How does AI work?",
)
print(response.text)