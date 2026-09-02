import os
from openai import OpenAI
from src.agent.schemas import ExceptionDiagnosis
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key= os.getenv("OPENAI_API_KEY"))

def diagnose_exception(row_dict: dict) -> dict:

    prompt = f""""Diagnose this financial discrepancy: {row_dict}. 
                  Compare 'merchant_amount', 'gross_amount', 'net_settled', and 'bank_credit'.
                  Check if 'gst' is exactly 18% of the 'fee'. Identify why the math fails.
                  
                  CRITICAL RULE: If 'merchant_amount' is 0 or empty, but 'bank_credit' is greater than 0, 
                  the root_cause MUST be 'ORPHAN_BANK_CREDIT'. Explain that this is an unallocated bank deposit 
                  that bypassed the merchant checkout and requires UTR tracing."""


    response = client.beta.chat.completions.parse(
        model = "gpt-4o-mini",
        messages = [{"role": "user", "content": prompt}],
        response_format = ExceptionDiagnosis
    )

    return response.choices[0].message.parsed.model_dump()