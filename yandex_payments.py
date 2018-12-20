import uuid

from yandex_checkout import Payment, Configuration

class YandexKassa:
    def __init__(self, SHOP_ID, SECRET_KEY):
        Configuration.configure(SHOP_ID, SECRET_KEY)

    def send_payment(self, amount, return_url, description):
        idempotence_key = str(uuid.uuid4())
        payment = Payment.create({
            "amount": {
                "value": amount,
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": description
        }, idempotence_key)

        payment.confirmation_url = payment.confirmation.confirmation_url
        return payment

    def is_paid(self, payment):
        return payment.status == "waiting_for_capture"

    def confirm(self, payment_id):
        payment = Payment.find_one(payment_id)
        assert self.is_paid(payment)
        idempotence_key = str(uuid.uuid4())
        amount = payment.amount.value
        response = Payment.capture(
            payment_id,
            {
                "amount": {
                    "value": amount,
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


