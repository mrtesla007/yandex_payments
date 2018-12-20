import time

from yandex_payments import YandexKassa
from pay2me import Pay2MeKassa

from config import YA_KASSA, PAY2ME
from db import MyPayment, DB, PaymentDB


class PaymentProcessor:
    def __init__(self, payment_db, kassa, timelimit=60*30):
        self.payment_db = payment_db
        if kassa == "yandex":
        	self.kassa = YandexKassa(YA_KASSA.ID, YA_KASSA.KEY)
        else:
        	self.kassa = Pay2MeKassa(PAY2ME.ID, PAY2ME.KEY)
        self.timelimit = timelimit

    def add_payment(self, user_id, amount, return_url, description):
        ya_payment = self.kassa.send_payment(amount, return_url, description)
        confim_url = ya_payment.confirmation_url

        db_payment = MyPayment(
            user_id,
            amount,
            return_url,
            description,
            str(ya_payment.id),
            str(ya_payment.status))
        self.payment_db.add_record(db_payment)
        return confim_url


    def check_payments(self):
        self._pending_check()
        self._waiting_capture_check()
        self.payment_db.flush()
        
    def _pending_check(self):
        for payment in self.payment_db.get_by_status("pending"):
            # If status was changed by ya_kasssa
            payment_id = str(payment.payment_id)
            status = self.kassa.get_status(payment_id)
            if status != payment.status:
                payment.status = status
                
            # If user doesn't pay in TIME_LIMIT
            sec_ago = time.time() - payment.start_time
            if sec_ago > self.timelimit:
                payment.status = "timeout"


    def _waiting_capture_check(self):
        payments = self.payment_db.get_by_status("waiting_for_capture")
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
        db, kassa = self.payment_db, self.kassa
        for payment in db.get_by_status("timeout"):
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
    import config

    payment_db = PaymentDB(DB("./data/test.sqlite"))

    processor = PaymentProcessor(payment_db, kassa="pay2me")

    url = processor.add_payment("Alex", 20, "google.com", "description")
    print(url)

    print("Before:\n")
    payment_db.print_all()

    processor.check_payments()

    print("\nAfter:\n")
    payment_db.print_all()

    processor.timeout_check()

    print("\nAfter timeout_check:\n")
    payment_db.print_all()
