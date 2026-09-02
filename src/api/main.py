from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
import os
import uuid
import pandas as pd
from dotenv import load_dotenv

# From folder
from src.core.parser import SecureFinancePipeline, SecurityViolation, DataParsingError
from src.core.matcher import run_reconciliation
from src.agent.investigator import diagnose_exception
from src.agent.qa_agent import answer_merchant_question
from src.agent.schemas import ChatRequest

load_dotenv()
app = FastAPI(title = "Secure Recon API")

API_KEY = os.getenv("API_KEY","Key_2026")

if not API_KEY:
    raise RuntimeError("CRITICAL SECURITY ERROR: API_SECRET_KEY is not set in the environment variables.")

api_key_header = APIKeyHeader(name="API-KEY", auto_error = True)

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code = 403, detail = "Invalid API Key")
    return api_key


parser_engine = SecureFinancePipeline(max_file_size_mb=50)
batch_store = {}

@app.post("/api/reconcile", dependencies =[Depends(verify_api_key)])
async def reconcile_api(
    orders: UploadFile = File(...),
    settlements: UploadFile = File(...),
    bank: UploadFile = File(...)
):
    try:
       
       # Read  files into RAM.
       orders_bytes = await orders.read()
       sett_bytes =  await settlements.read()
       bank_bytes = await bank.read()

       # Secure Parsing
       df_orders = parser_engine.process(orders_bytes, orders.filename)
       df_sett = parser_engine.process(sett_bytes, settlements.filename)
       df_bank = parser_engine.process(bank_bytes, bank.filename)

       # Deterministic Matching
       clean, exceptions, unsettled, data_errors, future_cash = run_reconciliation(df_orders, df_sett, df_bank)

       # AI Diagnosis
       ai_diagnosis = []
       for _, row in exceptions.iterrows():
            try:
                row_data = row.fillna("").to_dict()
                diag = diagnose_exception(row_data)
                
                # Check if order_id is missing/blank
                raw_order_id = str(row_data.get("order_id", "")).strip()
                raw_utr = str(row_data.get("utr", "UNKNOWN")).strip()
                
                if not raw_order_id or raw_order_id.lower() == "nan":
                    # Display the UTR in the Order ID column for Orphan Credits
                    diag["order_id"] = f"BANK_ONLY ({raw_utr})"
                else:
                    diag["order_id"] = raw_order_id
                    
                diag["utr"] = raw_utr
                ai_diagnosis.append(diag)
            except Exception as e:
                print(f" AI INVESTIGATOR ERROR: {e} ")
                pass


       # Save State
       batch_id = str(uuid.uuid4())
       summary_stats = {
           "total_records": len(clean)+len(exceptions)+len(unsettled)+len(data_errors),
           "matched_by_code": len(clean),
           "exceptions_found": len(exceptions),
           "quarantined_errors": len(data_errors),
           "future_cash": future_cash
       }


       batch_store[batch_id] = {"stats": summary_stats, "exceptions": ai_diagnosis}

       return {
           "batch_id": batch_id,
            "summary": summary_stats,
            "ai_investigation_results": ai_diagnosis,
            "unsettled_data": unsettled.fillna("").to_dict(orient="records"),
            "data_errors": data_errors.fillna("").to_dict(orient="records")
       }

    except SecurityViolation as sv:
        raise HTTPException(status_code = 403, detail = str(sv))
    except DataParsingError as dpe:
        raise HTTPException(status_code = 422, detail = str(dpe))
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Internal Server Error: {str(e)}")


@app.post("/api/chat", dependencies = [Depends(verify_api_key)])
async def chat_api(req: ChatRequest):
    batch = batch_store.get(req.batch_id)
    if not batch:
        raise HTTPException(status_code = 404, detail="Batch Id not found.")
    answer = answer_merchant_question(req.question, batch["stats"], batch["exceptions"])
    return{"answer": answer}

                            

