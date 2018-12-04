import datetime
import time
from yandex_checkout import Payment, Configuration
import uuid
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import create_engine, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import config

Base = declarative_base()

# STATUS: pending, waiting_for_capture, succeeded, canceled

# Not tested
def check_payments(db, Kassa):
    for instance in db.session.query(Transaction).filter(Transaction.status == 'pending'):
        time = instance.time
        minutes = int(time.split(":")[0]) * 60 + int(time.split(":")[0])
        delta_time = datetime.datetime.now().hour * 60 + datetime.datetime.now().minute - minutes
        if delta_time > config.TIME_LIMIT:
            print('--------------------------------------------------------------------------')
            db.delete(instance.id)
#            Kassa.cancel(instance.transaction_id) 

    for instanse in db.session.query(Transaction).filter(Transaction.status == 'waiting_for_capture'):
        transaction_id = Kassa.get_status(instanse.transaction_id) 
        status = Kassa.get_status(instanse.status) 
        if status == "waiting_for_capture":
            Kassa.confirm(transaction_id)
        if (status != instanse.status):
            db.change_status(instanse.id, status)
    
def add_payment(db, user_id, pay_amount, return_url, description):
    payment = Kassa.send_payment(pay_amount, return_url, description)
    tr = Transaction(user_id, pay_amount, return_url, description, payment.id, payment.status)
    db.add(tr)
    return payment.confirmation.confirmation_url
    
class DB(object):
    def __init__(self, filename):
        self.engine = create_engine(
            'sqlite:///{}'.format(filename),
            echo=True)
    
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.conn = self.engine.connect()
        Base.metadata.create_all(self.engine)
        
    def add(self, obj):
        self.session.add(obj)
        
    def delete(self, id_num):
        elem = self.session.query(Transaction).get(id_num)
        self.session.delete(elem)
    
    def change_status(self, id_num, status):
        elem = self.session.query(Transaction).get(id_num)
        elem.status = status 
        
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
    time = Column(String) # Float?
    
    def __init__(self, user_id, pay_amount, return_url, description, payment_id, payment_status):
        self.user_id = user_id
        self.pay_amount = pay_amount
        self.time =  "{}:{}".format(datetime.datetime.now().hour,datetime.datetime.now().minute)
        self.transaction_id = str(payment_id)
        self.status = str(payment_status)
        
    def __repr__(self):
        return "<Transcation({}, {}, {}, {}, {})>".format(self.transaction_id, self.user_id, self.pay_amount, self.status, self.time)
    
class Kassa(object):
    def __init__(self, SHOP_ID, SECRET_KEY):
        Configuration.configure(SHOP_ID,SECRET_KEY)
    
    def send_payment(self, pay_amount, return_url, description):
        idempotence_key = str(uuid.uuid4())
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
            payment = Payment.find_one(str(transaction_id))
            if (payment.status == "waiting_for_capture"):
                return True
            return False
    # Not tested
    def confirm(self, transaction_id):
        payment = Payment.find_one(str(transaction_id))
        assert self.is_paid(transaction_id)
        idempotence_key = str(uuid.uuid4())
        response = payment.capture( 
            payment.id,
          {
            "amount": {
              "value": self.pay_amount,
              "currency": "RUB"
            }
          },
          idempotence_key
        )
        if response.status == 'succeeded':
            return True
        else:
            return False
    # Not tested
    def cancel(self, transaction_id):
        payment = Payment.find_one(str(transaction_id))
        assert self.is_paid(transaction_id)
        idempotence_key = str(uuid.uuid4())
        response = Payment.cancel( #ПРоверять результат 
          payment.id,
          idempotence_key
        )
        if response.status == 'canceled':
            return True
        else:
            return False
    
    # Корректность статусов всех транзакицй
    def get_status(self, transaction_id):
        payment = Payment.find_one(str(transaction_id))
        return payment.status
        
if __name__=="__main__":
    db = DB("./database/test.sqlite")
    Kassa = Kassa(config.SHOP_ID, config.SECRET_KEY)
    url = add_payment(db,"Alex",1,"google.com", "description")
    print (url)
    add_payment(db,"Sasha",1,"google.com", "description")
    add_payment(db,"Masha",1,"google.com", "description")
    add_payment(db,"Kolya",1,"google.com", "description")
    add_payment(db,"Nikita",1,"google.com", "description")
    print (db.get_all_transactions())
    check_payments(db, Kassa)
    print (db.get_all_transactions())
