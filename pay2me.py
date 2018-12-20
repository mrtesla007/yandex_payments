import uuid
import hashlib
import requests

BASE_URL = "https://api.pay2me.world/api/v3/deals"

URL_CREATE = BASE_URL
URL_CANCEL = f"{BASE_URL}/cancel/"
URL_COMPLETE = f"{BASE_URL}/complete/"
URL_STATUS = f"{BASE_URL}/status/"


class Pay2meRequests:
    def __init__(self, api_key, secret_key, timeout_sec=10):
        self.header = {
            "Content-Type" : "application/json; charset=utf-8",
            "Accept" : "application/json",
            "X-API-KEY" : api_key
        }
        self.secret_key = secret_key
        self.timeout = timeout_sec

    def get(self, url, **kargs):
        my_kargs = self._prepare_kargs(kargs)
        r = requests.get(url, **my_kargs)
        return r.json()

    def post(self, url, **kargs):
        my_kargs = self._prepare_kargs(kargs)
        return requests.post(url, **my_kargs).json()

    def put(self, url, **kargs):
        my_kargs = self._prepare_kargs(kargs)
        return requests.put(url, **my_kargs).json()

    def _prepare_kargs(self, kargs):
        if "json" in kargs:
            kargs["json"] = self._sign_json(kargs["json"])

        kargs["timeout"] = self.timeout
        kargs["headers"] = self.header
        return kargs

    # signature = md5(utf(sort_params(params) + secret_key)))
    def _sign_json(self, in_json):
        out_json = dict(in_json)
        out_json["signature"] = self.calc_signature(in_json)
        return out_json

    def calc_signature(self, in_json):
        _params = ""
        for key in sorted(in_json.keys()):
            _params += str(in_json[key])
    
        line = (_params + self.secret_key).encode("utf-8")
        signature = hashlib.md5(line)
        return signature.hexdigest()


class Pay2MePayment():    
    status_map = {
            "created" : "pending",
            "paymentprocessing" : "pending",
            "paid" : "succeeded",
            "completed" : "succeeded",
            "payoutprocessing" : "succeeded",
            "canceled" : "canceled",
            "canceling" : "canceled",
            "paymentprocesserror" : "timeout", #"error"
            "payoutprocesserror" : "timeout",
            "cancelerror" : "timeout"
    }
    
    def __init__(self, json):
        self.id = json["object_id"]
        self.confirmation_url = json["redirect"]
        self.status = self.status_map[json["status"]]
        self.pay_amount = json["order_amount"]
        self.description = json["order_desc"]
        self.raw_json = json

    def get_status(self):
        return self.status

    def is_paid(self):
        return self.status == "succeeded"


class Pay2MeKassa:
    def __init__(self, api_key, secret_key):
        self.req = Pay2meRequests(api_key, secret_key)

    def send_payment(self, pay_amount, return_url, description):
        assert pay_amount >= 10.0
        order_id = str(uuid.uuid4())
        json = {"order_id": order_id,
                "order_desc": description,
                "order_amount": pay_amount,
               }
        payment = Pay2MePayment(self.req.post(URL_CREATE, json=json))
        return payment
      
    def confirm(self, payment_id):
        return True
        
#     def confirm(self, payment_id):
#         payment = self.find_one(payment_id)
#         assert self.is_paid(payment)        
#         signature = calc_signature({"order_id": payment["order_id"],
#                                    "order_desc": payment["order_desc"],
#                                    "order_amount": payment["order_amount"]})
#         json = {"signature": signature}
#         response = self.req.put(URL_COMPLETE+payment_id, json=json)
#         return response["status"] == "confirmed"
    
    def cancel(self, payment_id):
        payment = self.find_one(payment_id)
        assert self.is_paid(payment)
        json = {key: payment.raw_json[key] for key in ("order_id", "order_desc", "order_amount")}
        signature = self.req.calc_signature(json)
        json = {"signature": signature}
        response = self.req.put(URL_CANCEL + payment_id, json=json)
        #JSON is not like in the docs
        print (response)
        return response["DealStateId"] == "Canceling"
        #return response["status"] == "canceled"
    
    def find_one(self, payment_id):
        return Pay2MePayment(self.req.get(URL_STATUS + payment_id))
    
    def find_all(self, payment_id):
        payments = []
        for payment in payment_id:
            payments.append(self.find_one(payment))
        return payments
    
    def is_paid(self, payment):
        return payment.is_paid()
    
    def get_status(self, payment_id):
        payment = self.find_one(payment_id)
        return payment.get_status()
