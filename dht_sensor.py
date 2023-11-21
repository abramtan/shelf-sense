import Adafruit_DHT as dht

# set DATA pin
DHT = 4

def read_temp():
    # read temperature and humidity from DHT11
    h,t = dht.read_retry(dht.DHT11, DHT)

    return t-10

def read_humidity():
    # read temperature and humidity from DHT11
    h,t = dht.read_retry(dht.DHT11, DHT)

    return h