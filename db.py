import os
import time
import shutil
import sqlite3

from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine


Base = declarative_base()

# STATUS: pending, waiting_for_capture, succeeded, canceled, timeout

class MyPayment(Base):
    __tablename__ = "payments"
    payment_id = Column(String, primary_key=True)
    user_id = Column(Integer)
    amount = Column(Integer)
    status = Column(String)
    start_time = Column(Integer)
    succeed_time = Column(Integer)
    is_processed = Column(Integer)

    def __init__(
            self,
            user_id,
            amount,
            return_url,
            description,
            payment_id,
            payment_status):
        self.user_id = user_id
        self.amount = amount
        self.start_time = int(time.time())
        self.payment_id = payment_id
        self.status = payment_status
        self.is_processed = 0

    def set_processed(self):
        self.is_processed = 1

    def __repr__(self):
        return f"<MyPayment(id={self.payment_id}, user_id={self.user_id}, amount={self.amount}, status={self.status}, time={self.start_time})>"



class DB:
    def __init__(self, filename, only_read=False, debug=False):
        path = os.path
        if path.isfile(filename) and not only_read:
            data_dir = path.dirname(filename)
            fname = path.basename(filename)
            backup_file = path.join(data_dir, "backups", fname)
            backup_file += "_{}".format(int(time.time()))
            print("Copying {} to {}".format(filename, backup_file))
            shutil.copy(filename, backup_file)

        self.engine = create_engine(
            'sqlite:///{}'.format(filename),
            connect_args={'check_same_thread': False},
            echo=debug
        )
        Session = scoped_session(sessionmaker(bind=self.engine))
        self.session = Session()

        Base.metadata.create_all(self.engine)

    def add_record(self, obj, do_flush=True):
        self.session.add(obj)
        if do_flush:
            self.flush()

    def flush(self):
        self.session.commit()
        self.session.flush()



class PaymentDB(DB):
    def __init__(self, db):
        self.session = db.session

    def get_all(self):
        return self.session.query(MyPayment).all()

    def print_all(self):
        for payment in self.get_all():
            print(payment)

    def get_by_status(self, status):
        query = self.session.query(MyPayment)
        return query.filter(MyPayment.status == status).all()

    def get_succeed(self):
        query = self.session.query(MyPayment)
        return query.filter(MyPayment.status == "succeeded").\
            filter(MyPayment.is_processed == 0).all()

