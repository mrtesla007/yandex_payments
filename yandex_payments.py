import os
from yandex_checkout import Payment, Configuration
import uuid
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config

Base = declarative_base()

def check_payments(db, Kassa):
    for instanse in db.session.query(Transaction).order_by(Transaction.id):
        if Kassa.status(instanse.transaction_id) == "waiting_for_capture":
            Kassa.confirm(instanse.transaction_id)
        if (Kassa.status(instanse.transaction_id) != instanse.status): 
            instanse.status = Kassa.status(instanse.transaction_id)
    
def add_payment(db, user_id, pay_amount, return_url, description):
    tr = Transaction(user_id, pay_amount, return_url, description)
    db.add(tr)
    return tr.transaction_id
    
class DB(object):
    def __init__(self, filename):
        self.engine = create_engine(
            'sqlite:///{}'.format(filename),
            echo=True)      

        Session = sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()
        
        Base.metadata.create_all(self.engine)
        
    def add(self, obj):
        self.session.add(obj)
        
    def flush(self):
        self.session.commit()
        self.session.flush()
        
    def get_all_transactions(self):
        return self.session.query(Transaction).all()
    
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String)
    user_id = Column(String)
    pay_amount = Column(Float)
    status = Column(String)
    
    def __init__(self, user_id, pay_amount, return_url, description):
        self.user_id = user_id
        self.pay_amount = pay_amount
        # Create payment
        payment = Kassa.send_payment(pay_amount, return_url, description)
        self.transaction_id = str(payment.id)
        self.status = str(payment.status)
        
    def __repr__(self):
        return "<Transcation('%s', '%s', '%s', '%s')>" % (self.transaction_id, self.user_id, self.pay_amount, self.status)

class Kassa(object):
    def __init__(self, SHOP_ID, SECRET_KEY):
        Configuration.configure(SHOP_ID,SECRET_KEY)
    
    @staticmethod
    def send_payment(pay_amount, return_url, description):
        idempotence_key = str(uuid.uuid4())
        # Create payment
        try:
            payment = Payment.create({
            "amount": {
              "value": pay_amount,
              "currency": "RUB"
            },
            "confirmation": {
              "type": "redirect",
              "return_url": return_url
            },
            "description": description
            }, idempotence_key)
            return payment
        except Exception as exc:
            print("Unexpected error:", exc)        
            return None
    
    def is_paid(self, transaction_id):
        try:
            payment = Payment.find_one(str(transaction_id))
            if (payment.status == "waiting_for_capture"):
                return True
            return False
        except Exception as exc:
            print("Unexpected error:", exc)        
            return False
        
    def confirm(self, transaction_id):
        try:
            payment = Payment.find_one(str(transaction_id))
            if is_paid(transaction_id):
                idempotence_key = str(uuid.uuid4())
                payment.capture(  
                    payment.id,
                  {
                    "amount": {
                      "value": self.pay_amount,
                      "currency": "RUB"
                    }
                  },
                  idempotence_key
                )
                return True
            return False
        except Exception as exc:
            print("Unexpected error:", exc)        
            return False
    
    def cancel(self, transaction_id):
        try:
            payment = Payment.find_one(str(transaction_id))
            if is_paid(transaction_id):
                idempotence_key = str(uuid.uuid4())
                response = Payment.cancel(
                  payment.id,
                  idempotence_key
                )
                return True
            return False
        except Exception as exc:
            print("Unexpected error:", exc)        
            return False
    
    def status(self, transaction_id):
        try:
            payment = Payment.find_one(str(transaction_id))
            return payment.status
        except Exception as exc:
            print("Unexpected error:", exc) 
            return None
        
if __name__=="__main__":
    db = DB("./database/test.sqlite")
    Kassa = Kassa(config.SHOP_ID, config.SECRET_KEY)
    add_payment(db,"Alex",100.0,"google.com", "description")
    #db.get_all_transactions()
    check_payments(db, Kassa)

