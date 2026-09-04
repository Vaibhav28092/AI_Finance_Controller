# AI Finance Controller: Expense Intelligence

A secure, AI-driven pipeline designed to automate the ingestion, sanitization, and analysis of disparate financial documents (merchant settlements, bank statements, and invoices). This system detects anomalies, standardizes financial headers, and utilizes AI to flag potential fraud or hidden gateway fees.

## Live Demo
* **Live App:** [https://ai-finance-controller28.streamlit.app/](https://ai-finance-controller28.streamlit.app/)
* **Demo Video:** [Insert YouTube/Loom Link Here]

## The Problem & Solution

**The Problem:** Finance teams and small business owners waste countless hours manually reconciling data across various bank formats and payment gateways. Furthermore, uploading third-party financial documents exposes internal systems to disguised malware payloads.

**The Solution:** An automated microservice architecture that securely sanitizes uploads at the OS level, dynamically parses and standardizes data structures (CSV, Excel, JSON, PDF), and feeds clean data into an LLM for instant anomaly detection and reconciliation.

## Architecture & Security Engineering

This project was engineered to provide enterprise-grade security while successfully operating within the strict **512MB RAM constraints** of free-tier cloud environments (Render). 

* **Deep MIME Verification:** Utilizes the Linux `libmagic` C-library to verify the hex signatures of uploaded files, instantly blocking malicious executables disguised as financial reports (e.g., `.exe` renamed to `.csv`).
* **Cloud Antivirus Scanning:** Initially designed to run a local ClamAV daemon (`pyclamd`). To avoid Out-of-Memory (OOM) crashes on the 512MB Render server, the architecture was pivoted to utilize the **VirusTotal API**. 
* **Asynchronous Pacing:** Implemented a strategic delay mechanism to handle concurrent multi-file uploads safely without triggering VirusTotal's free-tier burst rate limits (4 requests/minute).
* **Smart Parsing Engine:** Uses dynamic Regex matching to map unpredictable merchant headers (e.g., `txn_id`, `reference_no`, `order val`) into a standardized Pandas DataFrame schema. Includes `pdfplumber` for structured table extraction from PDF invoices.

## Tech Stack

* **Frontend:** Streamlit
* **Backend:** FastAPI, Uvicorn
* **Containerization:** Docker (Python 3.11-slim)
* **Data Processing:** Pandas, PyArrow, OpenPyXL, PDFPlumber
* **Security:** `python-magic` (`libmagic1`), VirusTotal API
* **AI Engine:** OpenAI API

## Local Setup & Installation

**1. Clone the repository**
```bash
git clone [https://github.com/Vaibhav28092/AI_Finance_Controller.git](https://github.com/Vaibhav28092/AI_Finance_Controller.git)
cd AI_Finance_Controller
```

**2. Setup the Environment Variables Files**
On the  terminal use this:
```text
New-Item .env
```

open that .env file in VS Code and paste your three keys inside it:
```text
OPEN_API_KEY = your_actual_api_key_here
VIRUSTOTAL_API_KEY=your_actual_api_key_here
BACKEND_API_KEY = 'your_custom_secret_key_here' or 'KEY_2026' use this key
```

**3. Step 3: Install the required libraries**
```bash
pip install -r requirements.txt
```
**4. Turn on the Backend (FastAPI) to run locally after installing libraries**
```bash
uvicorn src.api.main:app --reload --port 8000
```
(leave this terminal windows open and running)

Note:- I host backend on this url: [https://ai-finance-controller-ogvh.onrender.com](https://ai-finance-controller-ogvh.onrender.com)

**5. Turn ON the Frontend(Streamlit):**

(In the second new terminal run this)

```bash
streamlit run app.py
```
**6. Run via Docker(Optional)**
```bash
docker build -t ai-finance-controller .
docker run -p 8000:8000 --env-file .env ai-finance-controller
```

## 📂 Project Structure

```text
AI_Finance_Controller/
├── .streamlit/
│       └── config.toml      # Contains customization of streamlit
├── data/                    # Data stores here after creating synthetic data
│   ├── orders.csv
│   ├── settlements.json
│   ├── bank_feed.csv
│
├── src/
│   ├──agent/
│   │   └── investigator.py  # Helps to identify the exceptions
│   │   └── qa_agent.py      # Q&A Chatbot 
│   │   └── schemas.py       # On the basis of given rules chatbot answers
│   ├── api/
│   │   └── main.py          # FastAPI application & routing
│   ├── core/
│   │   └── parser.py        # Security pipeline, MIME checks, VT API, Data parsing
│   │   └── matcher.py
│   ├── generator/
│   │   └── seed_data.py     # Generates Synthetic Data     
├── app.py                   # Streamlit frontend dashboard
├── Dockerfile               # Production container configuration
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (git-ignored)
├── .gitignore
└──  README.md
```




 
