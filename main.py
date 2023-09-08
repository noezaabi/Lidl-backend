# Third-party imports
import openai
from fastapi import FastAPI, Form, Depends
from decouple import config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Internal imports
from models import Conversation, SessionLocal, Item
from utils import send_message, logger


app = FastAPI()
# Set up the OpenAI API client
openai.api_key = config("OPENAI_API_KEY")
whatsapp_number = config("TO_NUMBER")

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

@app.post("/message")
async def reply(Body: str = Form(), db: Session = Depends(get_db)):
    # Call the OpenAI API to generate text with GPT-3.5
    # response = openai.Completion.create(
    #     engine="gpt-4",
    #     prompt=Body,
    #     max_tokens=200,
    #     n=1,
    #     stop=None,
    #     temperature=0.5,
    # )
    system_msg=f"Tu agis comme un service client pour le magasin de Tacos nommée \"O'tacos\". Tu dois aider ton interlocuteur dans son chjoix en lui donnant le menu si nécessaire. Dans la cas ou le client a fait un choix tu dois lui demander de confirmer son choix et reponds avec un json [nom: nom du produit, prix: prix du produit, quantité: quantité du produit], l\'utilisateur doit egaleent etre en mesure de commander plusieurs produits. Voici le menu: {getMenu()}"
    response = openai.ChatCompletion.create(model="gpt-4",
                                        messages=[{"role": "system", "content": system_msg},
                                         {"role": "user", "content": Body}])

    # The generated text
    chat_response = response.choices[0].text.strip()

    # Store the conversation in the database
    try:
        conversation = Conversation(
            sender=whatsapp_number,
            message=Body,
            response=chat_response
            )
        db.add(conversation)
        db.commit()
        logger.info(f"Conversation #{conversation.id} stored in database")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error storing conversation in database: {e}")
    send_message(whatsapp_number, chat_response)
    return ""