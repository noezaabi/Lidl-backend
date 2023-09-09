# Standard library import
import logging
from models import Item, SessionLocal

# Third-party imports
from twilio.rest import Client
from dotenv import dotenv_values

config = dotenv_values(".env")


# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
account_sid = config["TWILIO_ACCOUNT_SID"]
auth_token = config["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)
twilio_number = config['TWILIO_NUMBER']

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sending message logic through Twilio Messaging API
def send_message(to_number, body_text):
    try:
        message = client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            body=body_text,
            to=f"whatsapp:{to_number}"
            )
        logger.info(f"Message sent to {to_number}: {message.body}")
    except Exception as e:
        logger.error(f"Error sending message to {to_number}: {e}")
    
def getMenu():
    # Create a new session
    db = SessionLocal()
    try:
        # Query the Item table
        items = db.query(Item).all()

        # Format the results
        result = "\n".join(f"{i+1}. {item.name}: {item.price}" for i, item in enumerate(items))
        return result
    finally:
        # Close the session
        db.close()