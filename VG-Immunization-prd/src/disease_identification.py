import google.generativeai as genai

genai.configure(api_key="AQ.Ab8RN6LCRtvVjBrNywHVWR_DIvKfq37FFeruZxHKzkl2lqyinw")
model = genai.GenerativeModel("gemini-3.5-flash")

vaccine_name = "DTaP, Tdap, DT"
prompt = f'''
What disease(s) do the vaccines '{vaccine_name}' protect against? 
Reply with just the disease name(s) alphabetically for each individual vaccine. 
Also make sure the output reflects what the differences are for each vaccine's purpose.
'''
response = model.generate_content(prompt)
print(response.text)