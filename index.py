import hashlib
import urllib.parse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Configuration (In production, load these from environment variables)
PAYFAST_URL = "https://sandbox.payfast.co.za/eng/process"  # Use 'www' for live
MERCHANT_ID = "XXXXXXXXX"  # Sandbox Merchant ID
MERCHANT_KEY = "XXXXXXXX"  # Sandbox Merchant Key
PASSPHRASE = "XXXXXXXX"  # Sandbox Passphrase

class PaymentRequest(BaseModel):
    item_name: str
    amount: float
    email: str

def generate_signature(data: dict, passphrase: str = None) -> str:
    """
    PayFast requires variables to be in a specific order and concatenated 
    into a query string before hashing.
    """
    # 1. Convert dictionary to URL-encoded string
    # PayFast specific: Sort by key? No, PayFast often requires specific order 
    # but for simple integrations, standard urlencode often works if keys are consistent.
    # We strip empty values as per PayFast specs.
    payload_str = urllib.parse.urlencode(
        {k: v for k, v in data.items() if v is not None}
    )

    # 2. Append passphrase if it exists
    if passphrase:
        payload_str += f"&passphrase={urllib.parse.quote_plus(passphrase)}"

    # 3. Create MD5 Hash
    return hashlib.md5(payload_str.encode("utf-8")).hexdigest()

@app.post("/initiate-payfast")
async def initiate_payment(payment: PaymentRequest):
    try:
        # 1. Prepare standard PayFast data payload
        data = {
            "merchant_id": MERCHANT_ID,
            "merchant_key": MERCHANT_KEY,
            "return_url": "http://localhost:8000/success",
            "cancel_url": "http://localhost:8000/cancel",
            "notify_url": "http://localhost:8000/notify",
            "name_first": "Test",  # Simplified for demo
            "email_address": payment.email,
            "m_payment_id": "1234", # Unique ID from your DB
            "amount": f"{payment.amount:.2f}",
            "item_name": payment.item_name,
        }

        # 2. Generate the security signature
        data["signature"] = generate_signature(data, PASSPHRASE)

        # 3. Construct the full redirect URL
        # The frontend will simply redirect the user to this URL
        query_string = urllib.parse.urlencode(data)
        redirect_url = f"{PAYFAST_URL}?{query_string}"

        return {
            "status": "success", 
            "payment_service": "PayFast",
            "redirect_url": redirect_url,
            "payload_debug": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)