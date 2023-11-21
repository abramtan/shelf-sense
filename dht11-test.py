from dht_sensor import read_temp, read_humidity
import time

while(1):
    t = read_temp()
    h = read_humidity()
    print(f'Temp: {t}C     Humidity: {h}%')
    time.sleep(3)