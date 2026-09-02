import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client= OpenAI(api_key= os.getenv("OPENAI_API_KEY"))

def answer_merchant_question(question: str, stats: dict, exceptions: list) -> str:

    # Convert the python list of dictionaries to a clean JSON string so the LLM can read it
    exceptions_json = json.dumps(exceptions, indent=2) if exceptions else "No exceptions found."

    context = f"""You are the AI Finance Controller.
    
    CRITICAL INSTRUCTION: You DO have access to specific order IDs and exception data. 
    They are provided to you directly below in the 'Exception Diagnoses (JSON)' section. 
    You must NEVER say you do not have access. Read the provided JSON data carefully and use it to answer the merchant.

    Current Financial Batch State:
    - Total Records Processed: {stats.get('total_records', 0)}
    - Clean Matches: {stats.get('matched_by_code', 0)}
    - Exceptions Found: {stats.get('exceptions_found', 0)}
    - Quarantined Records (Data Errors): {stats.get('quarantined_errors', 0)}
    - Expected Future Cash (T+1/T+2): ₹{stats.get('future_cash', 0)}
    
    Exception Diagnoses (JSON):
    {exceptions_json}
    
    Answer the merchant's query professionally based ONLY on this FinOps data."""

    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": question}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content