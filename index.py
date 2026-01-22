#LN Import the library used to create secure hashes (fingerprints) for data protection
import hashlib
#LN Import the tool that helps convert text into a format safe for web URLs
import urllib.parse
#LN Import the tools to build the API server and handle web errors
from fastapi import FastAPI, HTTPException
#LN Import the tool that checks if data sent to us is in the correct format
from pydantic import BaseModel

#LN Create the main application object for our web server
app = FastAPI()

# Configuration (In production, load these from environment variables)
#LN Store the PayFast web address (Sandbox mode) where we send payments
PAYFAST_URL = "https://sandbox.payfast.co.za/eng/process"  # Use 'www' for live
#LN Store our unique shop ID given by PayFast
MERCHANT_ID = "XXXXXXXXX"  # Sandbox Merchant ID
#LN Store the secret key that acts like a password for our shop ID
MERCHANT_KEY = "XXXXXXXX"  # Sandbox Merchant Key
#LN Store the extra security word we set up in our PayFast account
PASSPHRASE = "XXXXXXXX"  # Sandbox Passphrase

#LN Define a blueprint for the data we expect users to send us
class PaymentRequest(BaseModel):
    #LN Expect a text value for the name of the product
    item_name: str
    #LN Expect a number (decimal) for the price
    amount: float
    #LN Expect a text value for the customer's email
    email: str

#LN Define a function to create a security seal (signature) for the payment data
def generate_signature(data: dict, passphrase: str = None) -> str:
    """
    PayFast requires variables to be in a specific order and concatenated 
    into a query string before hashing.
    """
    # 1. Convert dictionary to URL-encoded string
    # PayFast specific: Sort by key? No, PayFast often requires specific order 
    # but for simple integrations, standard urlencode often works if keys are consistent.
    # We strip empty values as per PayFast specs.
    
    #LN Convert our data dictionary into a single text string safe for URLs
    payload_str = urllib.parse.urlencode(
        #LN Loop through the data and remove any empty items before converting
        {k: v for k, v in data.items() if v is not None}
    )

    # 2. Append passphrase if it exists
    #LN Check if we have a security passphrase configured
    if passphrase:
        #LN Add the passphrase to the end of our data string
        payload_str += f"&passphrase={urllib.parse.quote_plus(passphrase)}"

    # 3. Create MD5 Hash
    #LN Scramble the data string into a unique code (MD5 hash) and return it
    return hashlib.md5(payload_str.encode("utf-8")).hexdigest()

#LN Tell the server to listen for POST messages at this specific address
@app.post("/initiate-payfast")
#LN Define the function that runs when a payment request comes in
async def initiate_payment(payment: PaymentRequest):
    #LN Start a block of code where we watch for potential errors
    try:
        # 1. Prepare standard PayFast data payload
        #LN Create a dictionary containing all the details PayFast needs
        data = {
            #LN Add our shop ID
            "merchant_id": MERCHANT_ID,
            #LN Add our secret key
            "merchant_key": MERCHANT_KEY,
            #LN Add the address to send users after they pay successfully
            "return_url": "http://localhost:8000/success",
            #LN Add the address to send users if they cancel
            "cancel_url": "http://localhost:8000/cancel",
            #LN Add the address for PayFast to verify the payment secretly
            "notify_url": "http://localhost:8000/notify",
            #LN Add a dummy first name for testing
            "name_first": "Test",  # Simplified for demo
            #LN Add the customer's email from the request
            "email_address": payment.email,
            #LN Add a unique ID for this specific order
            "m_payment_id": "1234", # Unique ID from your DB
            #LN Add the price, formatted to exactly 2 decimal places
            "amount": f"{payment.amount:.2f}",
            #LN Add the product name from the request
            "item_name": payment.item_name,
        }

        # 2. Generate the security signature
        #LN Create the security seal using our function and add it to the data
        data["signature"] = generate_signature(data, PASSPHRASE)

        # 3. Construct the full redirect URL
        # The frontend will simply redirect the user to this URL
        
        #LN Turn the final data bundle into a URL-safe text string
        query_string = urllib.parse.urlencode(data)
        #LN Combine the PayFast address and our data string to make the final link
        redirect_url = f"{PAYFAST_URL}?{query_string}"

        #LN Send the success message and the payment link back to the user
        return {
            "status": "success", 
            "payment_service": "PayFast",
            "redirect_url": redirect_url,
            "payload_debug": data
        }

    #LN Catch any errors that happened in the 'try' block
    except Exception as e:
        #LN Stop the process and send a "Server Error" message to the user
        raise HTTPException(status_code=500, detail=str(e))

#LN Check if this file is running directly (not imported)
if __name__ == "__main__":
    #LN Import the engine that runs the web server
    import uvicorn
    #LN Start the server so it can be accessed from any computer on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)