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

# STATUS: pending, waiting_for_capture, succeeded, canceled, timeout

# Not tested
def check_payments(db, Kassa):
    for payment in db.get_payments(status='pending'):
        sec_ago = time.time() - payment.time
        if sec_ago > config.TIME_LIMIT:
            payment.status = "timeout"
            db.flush()

    for payment in db.get_payments(status='waiting_for_capture'):
        transaction_id = payment.transaction_id
        status = Kassa.get_status(transaction_id) 
        if status == "waiting_for_capture":
            Kassa.confirm(transaction_id)

        if (status != payment.status):
            payment.status = status
            db.flush()
    
def add_payment(db, user_id, pay_amount, return_url, description):
    payment = Kassa.send_payment(pay_amount, return_url, description)
    tr = Transaction(user_id, pay_amount, return_url, description, payment.id, payment.status)
    db.add(tr)
    db.flush()
    return payment.confirmation.confirmation_url
    
class DB(object):
    def __init__(self, filename):
        self.engine = create_engine(
            'sqlite:///{}'.format(filename),
            echo=False)
    
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.conn = self.engine.connect()
        Base.metadata.create_all(self.engine)
        
    def add(self, obj):
        self.session.add(obj)
        
    def delete(self, id_num):
        elem = self.session.query(Transaction).get(id_num)
        self.session.delete(elem)
    
    def change_status(self, transaction, new_status):
        if transaction.status != new_status:
            transaction.status = new_status
            self.flush()
        
    def flush(self):
        self.session.commit()
        self.session.flush()
        
    def get_all_transactions(self):
        return self.session.query(Transaction).all()

    def get_payments(self, status):
        query = self.session.query(Transaction)
        query = query.filter(Transaction.status == status)
        return query.all()
    
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String)
    user_id = Column(String)
    pay_amount = Column(Float)
    status = Column(String)
    time = Column(Float)
    
    def __init__(self, user_id, pay_amount, return_url, description, payment_id, payment_status):
        self.user_id = user_id
        self.pay_amount = pay_amount
        self.time = time.time()
        self.transaction_id = str(payment_id)
        self.status = str(payment_status)
        
    def __repr__(self):
        return "<Transcation({}, {}, {}, {}, {})>".format(self.transaction_id, self.user_id, self.pay_amount, self.status, self.time)

    
class Kassa(object):
    def __init__(self, SHOP_ID, SECRET_KEY):
        Configuration.configure(SHOP_ID,SECRET_KEY)
    
    def send_payment(self, pay_amount, return_url, description):
        idempotence_key = str(uuid.uuid4())
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
       
    
    def is_paid(self, payment):
        return payment.status == "waiting_for_capture"

    # Not tested
    def confirm(self, transaction_id):
        payment = Payment.find_one(str(transaction_id))
        assert self.is_paid(payment)
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

        return response.status == 'succeeded'


    # Not tested
    def cancel(self, transaction_id):
        payment = Payment.find_one(str(transaction_id))
        assert self.is_paid(payment)
        idempotence_key = str(uuid.uuid4())
        response = Payment.cancel( #ПРоверять результат 
          payment.id,
          idempotence_key
        )
        return response.status == 'canceled'
    
    # Корректность статусов всех транзакицй
    def get_status(self, transaction_id):
        payment = Payment.find_one(str(transaction_id))
        return payment.status
        

if __name__=="__main__":
    db = DB("./database/test.sqlite")
    Kassa = Kassa(config.SHOP_ID, config.SECRET_KEY)
    url = add_payment(db,"Alex",1,"google.com", "description")
    print (url)
    # add_payment(db,"Sasha",1,"google.com", "description")
    # add_payment(db,"Masha",1,"google.com", "description")
    # add_payment(db,"Kolya",1,"google.com", "description")
    # add_payment(db,"Nikita",1,"google.com", "description")
    for tr in db.get_all_transactions():
        print(tr)

    check_payments(db, Kassa)

    for tr in db.get_all_transactions():
        print(tr)
