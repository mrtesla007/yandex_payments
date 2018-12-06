import time
import uuid

from yandex_checkout import Payment, Configuration

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy import create_engine, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

import config

Base = declarative_base()

# STATUS: pending, waiting_for_capture, succeeded, canceled, timeout


class MyPayment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    payment_id = Column(String)
    user_id = Column(String)
    pay_amount = Column(Float)
    status = Column(String)
    time = Column(Float)

    def __init__(
            self,
            user_id,
            pay_amount,
            return_url,
            description,
            payment_id,
            payment_status):
        self.user_id = user_id
        self.pay_amount = pay_amount
        self.time = time.time()
        self.payment_id = payment_id
        self.status = payment_status

    def __repr__(self):
        return "<MyPayment({}, {}, {}, {}, {})>".format(
            self.payment_id, self.user_id, self.pay_amount, self.status, self.time)



class DB:
    def __init__(self, filename):
        self.engine = create_engine(
            "sqlite:///{}".format(filename),
            echo=False)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.conn = self.engine.connect()
        Base.metadata.create_all(self.engine)

    def add(self, obj):
        self.session.add(obj)

    def delete(self, obj):
        self.session.delete(obj)

    def change_status(self, payment, new_status):
        if payment.status != new_status:
            payment.status = new_status
            self.flush()

    def flush(self):
        self.session.commit()
        self.session.flush()

    def get_all_payments(self):
        return self.session.query(MyPayment).all()

    def print_all_payments(self):
        for payment in self.get_all_payments():
            print(payment)

    def get_payments(self, status):
        query = self.session.query(MyPayment)
        return query.filter(MyPayment.status == status).all()




class Kassa(object):
    def __init__(self, SHOP_ID, SECRET_KEY):
        Configuration.configure(SHOP_ID, SECRET_KEY)

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

    def confirm(self, payment_id):
        payment = Payment.find_one(payment_id)
        assert self.is_paid(payment)
        idempotence_key = str(uuid.uuid4())
        pay_amount = payment.amount.value
        response = Payment.capture(
            payment_id,
            {
                "amount": {
                    "value": pay_amount,
                    "currency": "RUB"
                }
            },
            idempotence_key
        )

        return response.status == "succeeded"

    def cancel(self, payment_id):
        payment = Payment.find_one(payment_id)
        assert self.is_paid(payment)
        idempotence_key = str(uuid.uuid4())
        response = Payment.cancel(
            payment_id,
            idempotence_key
        )
        return response.status == "canceled"

    def get_status(self, payment_id):
        payment = Payment.find_one(payment_id)
        return payment.status




class PaymentProcessor:
    def __init__(self, db, kassa):
        self.db = db
        self.kassa = kassa

    def add_payment(self, user_id, pay_amount, return_url, description):
        ya_payment = self.kassa.send_payment(pay_amount, return_url, description)
        confim_url = ya_payment.confirmation.confirmation_url

        db_payment = MyPayment(
            user_id,
            pay_amount,
            return_url,
            description,
            str(ya_payment.id),
            str(ya_payment.status))
        self.db.add(db_payment)
        self.db.flush()
        return confim_url


    def check_payments(self):
        self._pending_check()
        self._waiting_capture_check()
        self.db.flush()
        
    def _pending_check(self):
        for payment in self.db.get_payments(status="pending"):
            # If status was changed by ya_kasssa
            payment_id = str(payment.payment_id)
            status = self.kassa.get_status(payment_id)
            if status != payment.status:
                payment.status = status
                
            # If user doesn't pay in TIME_LIMIT
            sec_ago = time.time() - payment.time
            if sec_ago > config.TIME_LIMIT:
                payment.status = "timeout"


    def _waiting_capture_check(self):
        payments = self.db.get_payments(status="waiting_for_capture")
        kassa = self.kassa
        for payment in payments:
            payment_id = str(payment.payment_id)
            status = kassa.get_status(payment_id)
            if status == "waiting_for_capture":
                kassa.confirm(payment_id)
                status = kassa.get_status(payment_id)
                
            if status != payment.status:
                payment.status = status
            
    # If user all the same decided to pay after TIME_LIMIT. 
    # Need to check with lower rate, so wasn't included to check_payments(db, kassa)
    def timeout_check(self):
        db, kassa = self.db, self.kassa
        for payment in db.get_payments(status="timeout"):
            payment_id = str(payment.payment_id)
            status = kassa.get_status(payment_id)
            if status == 'canceled':
                payment.status = status
                
            if status == 'waiting_for_capture':
                kassa.confirm(payment_id)
                status = kassa.get_status(payment_id)
                payment.status = status
        db.flush()
            


if __name__ == "__main__":
    database = DB("./database/test.sqlite")
    ya_kassa = Kassa(config.SHOP_ID, config.SECRET_KEY)

    processor = PaymentProcessor(database, ya_kassa)

    url = processor.add_payment("Alex", 1, "google.com", "description")
    print(url)

    print("Before:\n")
    database.print_all_payments()

    processor.check_payments()

    print("\nAfter:\n")
    database.print_all_payments()

    processor.timeout_check()

    print("\nAfter timeout_check:\n")
    database.print_all_payments()
