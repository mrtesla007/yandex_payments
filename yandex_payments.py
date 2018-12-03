import yandex_checkout
from yandex_checkout import Payment, Configuration
import uuid
import sqlalchemy
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SHOP_ID = 
SECRET_KEY = ''

Configuration.configure(SHOP_ID,SECRET_KEY)
engine = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()


class Transaction(Base):
    __tablename__ = 'Transactions'
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String)
    user_id = Column(String)
    value = Column(Float)
    
    def __init__(self, user_id, value, return_url, description, session):
        self.user_id = user_id
        self.value = value
        
        idempotence_key = str(uuid.uuid4())
        # Create payment
        payment = Payment.create({
        "amount": {
          "value": value,
          "currency": "RUB"
        },
        "payment_method_data": {
          "type": "bank_card"
        },
        "confirmation": {
          "type": "redirect",
          "return_url": return_url
        },
        "description": description
        }, idempotence_key)
        self.transaction_id = str(payment.id)
        
        session.add(self)
        
    def __repr__(self):
        return "<Transcation('%s', '%s', '%s', '%s')>" % (self.transaction_id, self.user_id, self.value)

    def pay(self):
        payment = Payment.find_one(self.transaction_id)
        if (payment.status == "waiting_for_capture"):
            idempotence_key = str(uuid.uuid4())
            response = payment.capture(  
                payment.id,
              {
                "amount": {
                  "value": self.value,
                  "currency": "RUB"
                }
              },
              idempotence_key
            )
            return True
        return False
    
    def cancel(self, payment_id):
        payment = Payment.find_one(self.transaction_id)
        if (payment.status == "waiting_for_capture"):
            idempotence_key = str(uuid.uuid4())
            response = Payment.cancel(
              payment.id,
              idempotence_key
            )
            return True
        return False
        
# Create Table
Base.metadata.create_all(engine)

Session = sessionmaker()
Session.configure(bind=engine)
session = Session()
