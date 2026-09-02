import io
import os
import re
import magic
import pyclamd
import pandas as pd
import pdfplumber


class SecurityViolation(Exception):
    """Raised when a file fails MIME checks, size limits, or AV scans."""
    pass

class DataParsingError(Exception):
    """Raised when a file is safe, but the data is unreadable or corrupted."""
    pass

class SecureFinancePipeline:
    """Handles security gating, safe parsing, and header normalization."""


    HEADER_PATTERNS = {
        "order_id": r"(order[_\s]?id|txn[_\s]?id|transaction[_\s]?id|reference[_\s]?no|^id$)",
        "merchant_amount": r"(internal[_\s]?amount|order[_\s]?val(ue)?|price|order[_\s]?amount)",
        "gross_amount": r"(gross[_\s]?amount|gross[_\s]?val(ue)?|total[_\s]?amount|^amount$|\bamount$)",
        "utr": r"(utr|utr[_\s]?no|bank[_\s]?ref|rrn|neft[_\s]?ref|imps[_\s]?ref)",
        "net_settled": r"(net[_\s]?amount|net[_\s]?settled|payout|settlement[_\s]?amount)",
        "fee": r"(^fee$|fee[_\s]?amount|mdr|gateway[_\s]?fee|processing[_\s]?fee|charges)",
        "gst": r"(tax|gst|service[_\s]?tax|igst|cgst)",
        "bank_credit": r"(credit|bank[_\s]?credit|deposit|cr[_\s]?amount|received)"
    }

    def __init__(self, max_file_size_mb: int = 50):
        self.max_file_bytes = max_file_size_mb * 1024 * 1024  # Convert MB to bytes

        self.allowed_mime_types = {
            ".csv": ["text/csv", "text/plain"],
            ".txt": ["text/plain"],
            ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
            ".xls": ["application/vnd.ms-excel"],
            ".json": ["application/json", "text/plain"],
            ".jsonl": ["application/json", "text/plain"],
            ".parquet": ["application/octet-stream"],
            ".pdf": ["application/pdf"]

        }


        # Initialize ClamAV
        try:
            self.av = pyclamd.ClamdNetworkSocket()
        except pyclamd.ConnectionError:
            print("Warning: ClamdAV Daemon offline. Security scans will fail in production.")
            self.av = None

    # -----------------------Security Methods------------------------------

    def _verify_mime_type(self, file_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[-1].lower()
        if ext not in self.allowed_mime_types:
            raise SecurityViolation(f"File extension '{ext}' is not allowed.")

        actual_mime = magic.from_buffer(file_bytes[:2048], mime=True)
        if actual_mime not in self.allowed_mime_types[ext]:
            raise SecurityViolation(f"MIME Spoofing detected! Extension is '{ext}', but file is '{actual_mime}'.")
        
        return ext

    def _scan_for_malware(self, file_bytes: bytes) -> None:
        if not self.av:

            # For local hackathon dev: log a warning and pass safely instead of crashing

            print("⚠️ Warning: ClamAV is offline. Bypassing malware scan for local development.")
            return

        result = self.av.instream(io.BytesIO(file_bytes))
        if result:
            virus_name = result["stream"][1]
            raise SecurityViolation(f"Malware detected: {virus_name}. File quarantined.")

    # ----------------------Parsing Methods------------------------------

    @classmethod
    def _adapt_headers(cls, df: pd.DataFrame) -> pd.DataFrame:
        cols = df.columns
        rename_mapping = {}

        for standard_key, pattern in cls.HEADER_PATTERNS.items():
            for col in cols:
                # Prevent already-mapped columns from being overwritten
                if col in rename_mapping:
                    continue
                cleaned = str(col).strip().lower()
                if re.search(pattern, cleaned) and standard_key not in rename_mapping.values():
                    rename_mapping[col] = standard_key
                    break  # Stop after the first match for this standard key

        return df.rename(columns=rename_mapping)



    @classmethod
    def _parse_pdf_tables(cls, byte_stream: io.BytesIO) -> pd.DataFrame:
        all_raw_rows = []
        
        with pdfplumber.open(byte_stream) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    # Maintain structural integrity while cleaning empty strings
                    cleaned_table = [[str(cell).strip() if cell is not None else "" for cell in row] for row in table]
                    all_raw_rows.extend(cleaned_table)

        if not all_raw_rows or len(all_raw_rows) < 1:
            raise DataParsingError("Could not extract structured tables from PDF.")

        header_index = -1
        
        # Scan through rows to look for patterns matching standard finance keys
        for idx, row in enumerate(all_raw_rows):
            match_count = 0
            for cell in row:
                cleaned_cell = cell.lower()
                # Run cell value against your registered REGEX mapping expressions
                for pattern in cls.HEADER_PATTERNS.values():
                    if cleaned_cell and re.search(pattern, cleaned_cell):
                        match_count += 1
                        break # Prevent double flags for a single string cell

            # If at least 2 cells match our target key layouts, consider this row the real header
            if match_count >= 2:
                header_index = idx
                break

        # Slicing Engine execution based on dynamic search analysis
        if header_index != -1:
            true_headers = all_raw_rows[header_index]
            actual_data_rows = all_raw_rows[header_index + 1:]
            
            # If nothing exists beneath found header, throw parsing error
            if not actual_data_rows:
                raise DataParsingError("Header identified, but no tabular tracking data follows below it.")
                
            df = pd.DataFrame(actual_data_rows, columns=true_headers)
        else:
            # Fallback block: If validation failed entirely, use first index with warning logs
            print("Warning: Direct header target signature matching failed. Falling back to Row 0.")
            df = pd.DataFrame(all_raw_rows[1:], columns=all_raw_rows[0])

        # Remove rows that are entirely empty strings or NaN fields
        df = df.replace("", pd.NA).dropna(how="all")
        return df



    # ------------------Main Entry Point----------------------

    def process(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Main method to ingest, secure, and parse a file."""


        #1. Quota Check

        if len(file_bytes) > self.max_file_bytes:
            raise SecurityViolation(f"File exceeds the maximum allowed size of {self.max_file_bytes/1024/1024}MB")

        #2. Security Checks

        ext = self._verify_mime_type(file_bytes, filename)
        self._scan_for_malware(file_bytes)

        #3. Parsing

        byte_stream = io.BytesIO(file_bytes)
        try:
            if ext in [".csv", ".txt"]:
                df = pd.read_csv(byte_stream, encoding_errors='replace', dtype=str)
            elif ext in [".xlsx", ".xls"]:
                df = pd.read_excel(byte_stream, engine='openpyxl', dtype=str)
            elif ext in [".json", ".jsonl"]:
                lines = True if ext == ".jsonl" else False
                df = pd.read_json(byte_stream, lines=lines, dtype=str)
            elif ext == ".parquet":
                df = pd.read_parquet(byte_stream)
            elif ext == ".pdf":
                df = self._parse_pdf_tables(byte_stream)
        except Exception as e:
            raise DataParsingError(f"Failed to safely parse the file: {e}")

        # 4. Standardize and Return

        return self._adapt_headers(df)
        
