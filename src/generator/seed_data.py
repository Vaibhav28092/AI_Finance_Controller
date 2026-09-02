import pandas as pd
import random
import os
from datetime import datetime
import string


def generate_indian_utr():
    bank_code = random.choice(['HDFC', 'ICIC', 'SBI', 'AXIS'])

    date_part = datetime.now().strftime('%d%m%y')

    random_part = "".join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=10
        )
    )

    return f"{bank_code}{date_part}{random_part}"


def generate_synthetic_data(num_records=100, anomaly_rate=0.2):
    orders, settlements, bank_feed = [], [], []

    for i in range(num_records):
        order_id = f"order_{1000 + i}"
        utr = generate_indian_utr()
        bank_utr = utr
        amount = round(random.uniform(500.0, 5000.0), 2)


        # Synthetic simulation assumption:
        # Standard payment gateway charges: 2% fee and 18% GST on the fee.
        fee = round(amount * 0.02, 2)
        gst = round(fee * 0.18, 2)
        net = round(amount - fee - gst, 2)


        # Clean data (Perfect math)

        internal_amount = amount
        gateway_net = net
        bank_credit = net
        transaction_date = datetime.now().strftime("%d-%m-%y")

        # Inject Anomalies 

        if random.random() < anomaly_rate:

            # ADDED 'UNSETTLED' to test the Cash Forecaster
            anomaly_type = random.choice(["FEE_SPIKE", "MISSING_UTR", "BANK_SHORT", "UNSETTLED"])
            if anomaly_type == "FEE_SPIKE":
                fee = round(amount*0.03, 2)  # Introduce a fee spike anomaly
                gst = round(fee * 0.18, 2)
                gateway_net = round(amount - fee - gst, 2)
                bank_credit = gateway_net  # Bank credit reflects the anomaly
            elif anomaly_type == "MISSING_UTR":
                bank_utr = ""  # Bank API failure to provide UTR
            elif anomaly_type == "BANK_SHORT":
                short_amount = round(random.uniform(10.0, 50.0),2)
                bank_credit = round(gateway_net - short_amount, 2)  # Bank deducts random fee between 10 to 50.
            elif anomaly_type == "UNSETTLED":
                # Order exists, but hasn't reached the gateway/bank yet
                gateway_net = 0.0
                bank_credit = 0.0
                fee = 0.0
                gst = 0.0
                utr = ""
                bank_utr = ""


        # Append to respective lists

        orders.append({"order_id": order_id, "internal_amount": internal_amount, "transaction_date": transaction_date})

        if gateway_net > 0 or anomaly_type == "UNSETTLED":
            settlements.append(
            {
            "order_id": order_id, 
             "gross_amount": amount,
             "fee": fee,
             "gst": gst,
             "net_settled": gateway_net,
             "utr": utr,
             "transaction_date": transaction_date
            }
        )  

        if bank_credit > 0 or (utr != "" and bank_utr != ""):
            bank_feed.append(
            {
                "utr": bank_utr,
                "bank_credit": bank_credit, 
                "transaction_date": transaction_date
            }          
        )

    # Save the generated data to CSV files

    os.makedirs("data", exist_ok=True)

    pd.DataFrame(orders).to_csv("data/orders.csv", index=False)
    pd.DataFrame(settlements).to_json("data/settlements.json", orient="records", indent=4)
    pd.DataFrame(bank_feed).to_csv("data/bank_feed.csv", index=False)

    print(f"Synthetic reconciliation data generated successfully.")

if __name__ == "__main__":
    generate_synthetic_data()