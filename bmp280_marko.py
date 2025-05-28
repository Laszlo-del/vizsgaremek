import requests
import time
import random # Bár a random nincs használva a végső kódban, bent hagytam, ha valaha szükséged lenne rá a teszteléshez.
from smbus2 import SMBus
from bmp280 import BMP280
from gpiozero import PWMLED
from time import sleep

# GPIO pin definíciók a LED-ekhez
# Fontos: Győződj meg róla, hogy ezek a GPIO pinek megfelelnek a fizikai bekötésnek!
blue_led = PWMLED(16)  # Kék LED a GPIO 16 pinhez
red_led = PWMLED(21)   # Piros LED a GPIO 21 pinhez

# ThingSpeak API kulcs
API_KEY = 'YZCROBZ928DEZRNA'

# Adatok küldése a ThingSpeak-re
def send_data_to_thingspeak(temp, pressure):
    """
    Elküldi a hőmérsékletet és légnyomást a Thingspeak csatornára.
    """
    url = f'https://api.thingspeak.com/update?api_key={API_KEY}&field1={temp}&field2={pressure}'
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f"Sikeres adatküldés: Hőmérséklet={temp:.2f}°C, Légnyomás={pressure:.2f}hPa")
    else:
        print(f"Sikertelen adatküldés: HTTP {response.status_code} - {response.text}")

# Initialise the BMP280 szenzor
try:
    bus = SMBus(1)
    bmp280 = BMP280(i2c_dev=bus)
    print("BMP280 szenzor inicializálva.")
except FileNotFoundError:
    print("Hiba: SMBus nem található. Győződj meg róla, hogy az I2C engedélyezve van és a 'smbus2' telepítve van.")
    exit()
except Exception as e:
    print(f"Hiba a BMP280 inicializálásakor: {e}")
    exit()

print("Rendszer indítása... Nyomj CTRL+C-t a kilépéshez.")

# Végtelen ciklus 10 másodperces időközönként
try:
    while True:
        # BMP280 szenzor adatainak bekérése
        temperature = bmp280.get_temperature()
        pressure = bmp280.get_pressure()
        
        # A kiíratás formázása
        print(f"Aktuális adatok: Hőmérséklet={temperature:05.2f}°C, Légnyomás={pressure:05.2f}hPa")

        # LED-ek kapcsolása a hőmérséklet alapján (a 20 fokos limit megtartva)
        if temperature > 20:
            red_led.value = 1    # Piros LED bekapcsolása
            blue_led.value = 0   # Kék LED kikapcsolása
            print("LED állapot: Piros (hőmérséklet > 20°C)")
        else:
            red_led.value = 0    # Piros LED kikapcsolása
            blue_led.value = 1   # Kék LED bekapcsolása
            print("LED állapot: Kék (hőmérséklet <= 20°C)")
        
        # Adatok küldése a Thingspeak-re
        send_data_to_thingspeak(temperature, pressure)
        
        # 10 másodperces várakozás a következő ciklus előtt
        time.sleep(10)

except KeyboardInterrupt:
    print("\nProgram leállítva (CTRL+C).")
except Exception as e:
    print(f"Hiba történt a futás közben: {e}")
finally:
    # Fontos: Felszabadítjuk a GPIO erőforrásokat és kikapcsoljuk a LED-eket kilépéskor
    red_led.close()
    blue_led.close()
    print("GPIO erőforrások felszabadítva, LED-ek kikapcsolva.")
