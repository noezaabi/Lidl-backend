# Third-party imports
import openai
from fastapi import FastAPI, Form, Depends
from dotenv import dotenv_values
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import json
import stripe

# Internal imports
from models import Conversation, SessionLocal, Item
from utils import send_message, logger

config = dotenv_values(".env")

conversations = {}

stripe.api_key = 'sk_test_51NnxmGEegxeRLTZUeCytZzpGSfVbHlddHcWE7QWtk4Uj4fkrThqnC89zg0xx3rGkLEarALvEG5kPpyVO8KFA80ns00tNa4LC6q'

def get_payment_link(price_id, quantity):
    payment = stripe.PaymentLink.create(line_items=[{"price": price_id, "quantity": quantity}])

    return payment['url']


def list_prices():
    prices = stripe.Price.list(limit=100)
    for price in prices:
        product = stripe.Product.retrieve(price.product)
        print(f"Price ID: {price.id}, Product Name: {product.name}")

def get_price_id(item_name):
    db=SessionLocal()
    stripe_price_id = db.query(Item).filter(Item.name==item_name).first()

    if stripe_price_id is None:
        return None
    
    return stripe_price_id.stripePriceId



app = FastAPI()
# Set up the OpenAI API client
openai.api_key = config["OPENAI_API_KEY"]
whatsapp_number = config["TO_NUMBER"]

def getMenu():
    # Create a new session
    db = SessionLocal()
    try:
        # Query the Item table
        items = db.query(Item).all()

        # Format the results
        result = "\n".join(f"{i+1}. {item.name}: ${item.price}" for i, item in enumerate(items))
        return result
    finally:
        # Close the session
        db.close()

# Dependency

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()





functions = [
    {
        "name": "get_payment_link",
        "description": "Creates a Stripe payment link, when the customer has confirmed his order and provided his shipping address.",
        "parameters": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Exact item name as described in the menu."},
                "quantity":{"type":"string", "description": "quantity of the item selected by the user."}
                
            },
            "required": ["price_id","quantity"]
        },
        "return_type": "string"
    }
]

@app.post("/message")
async def reply(Body: str = Form(), db: Session = Depends(get_db)):
    user_id = whatsapp_number  # Replace with actual user identification logic
    
    # Initialize or retrieve conversation state
    if user_id not in conversations:
        conversations[user_id] = []
    
    system_msg = f"""Role: You are an AI shopping assistant chatbot specialized in facilitating food orders. Your tone is concise and friendly.

Objective: Assist customers in making food orders, obtaining their address, and sending them a Stripe payment link through function calls.

Constraints:

    Adhere strictly to the provided menu. Here it is {getMenu()}.
    Do not invent items, alter prices, or modify names on the menu.

Initial Interaction:

    When a customer initiates a conversation, your first reply should be something along the lines of: "Hey! I got you, here is our menu: {getMenu()}".
    You are free to adapt your tone to the tone employed by the customer to maximise customer satisfaction and connection.
    
Behavior Guidelines:

    Maintain focus on assisting the customer to order food.
    Offer food recommendations only from the menu.
    If a customer requests an item not on the menu, ask if they meant a different item that is available. The item chosen must strictly be one that is on the menu.
    Try to be as concise as possible.

Ordering Procedure:

    Ask the customer what they would like to order.
    Inquire about the desired quantity.
    Request the delivery address.
    Summarize the order in a clean list, and confirm its accuracy with the customer.
    

Mock Conversation

    Customer: Hey, what's up?
    AI Assistant: Welcome! Here's what we offer: {getMenu()}.
    Customer: I'll go with a Margherita pizza.
    AI Assistant: Great choice! How many Margherita pizzas would you like?
    Customer: Just one.
    AI Assistant: Perfect. Where should we deliver your Margherita pizza?
    Customer: 123 Main St.
    AI Assistant:
     Order Summary:
        Item: Margherita pizza
        Quantity: 1
        Address: 123 Main St

Is this accurate?
    Customer: Yes, that's correct.H"""
    
    #f"You are a friendly AI shopping assistant chatbot that speaks concisely. Here is our menu: {getMenu}. NEVER, under ANY circumstance, make up an item that isn't on the menu, or change the price, or change the name. You basically receive messages from customers, and your job is to understand what the customer would like to order, what his address is, and then send a stripe payment link to him (using function calling). Always stay in character. A customer will start a conversation, and you should respond accordingly. For example, if he says anything at first, you should reply “Hi! Of course! Here is our menu: {getMenu()}”.  Always stay on the topic of getting him to order food. You can advise him food as you see fit (ALWAYS food included IN the menu provided)."

    # Append user and system messages to conversation
    conversations[user_id].append({"role": "system", "content": system_msg})
    conversations[user_id].append({"role": "user", "content": Body})
    
    # Make API request
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=conversations[user_id],
        functions=functions,
        function_call='auto',
        temperature=0.1,
    )
    
    # Retrieve and store assistant message
    assistant_msg = response['choices'][0]['message']['content']
    assistant_msg2 = response['choices'][0]['message']
    conversations[user_id].append({"role": "assistant", "content": assistant_msg})

    if assistant_msg2.get("function_call"):
    # Parse the arguments from the function call
        function_call = assistant_msg2["function_call"]
        if function_call is not None:
             print(function_call)
#ll the get_payment_link function with the generated arguments
             item_name=json.loads(function_call.arguments).get('item')
             quantity=json.loads(function_call.arguments).get('quantity')
             price_id=get_price_id(item_name)
             payment_link = get_payment_link(price_id,quantity)
             send_message(whatsapp_number, f'Excellent. Here is your payment link:{payment_link}')
        
        return ""


    send_message(whatsapp_number, assistant_msg)
    return ""
