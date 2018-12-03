import time
import threading

tr0 =Transaction("1", 200.0, "google.com", "1", session)
tr1 =Transaction("2", 300.0, "google.com", "1", session)
tr2 =Transaction("3", 400.0, "google.com", "1", session)
tr3 =Transaction("2", 500.0, "google.com", "1", session)
tr4 =Transaction("1", 600.0, "google.com", "1", session)

def try_to_pay(tr):
    while True:
        print ('Tic')
        time.sleep(1)
        if tr.pay() == True:
            return True
        print ('Toc')


t1 = threading.Thread(target=try_to_pay, args=[tr0])
t2 = threading.Thread(target=try_to_pay, args=[tr1])
t1.start()
t2.start()
