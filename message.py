import vonage

# Create an instance of the Vonage client with your credentials
client = vonage.Client(key="a18a6465", secret="w5p8n9Lc4TNmulMP")

# Create an instance of the SMS client
sms = vonage.Sms(client)

responseData = sms.send_message(
    {
        "from": "DiaRec",  # Sender name (or phone number)
        "to": "639278826869",  # Recipient phone number in international format
        "text": "Hello, this is a test message sent using the Vonage SMS API!",
    }
)

# Check the response
if responseData["messages"][0]["status"] == "0":
    print("Message sent successfully.")
else:
    print(f"Message failed with error: {responseData['messages'][0]['error-text']}")
