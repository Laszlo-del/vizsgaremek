import requests
import time
from gpiozero import PWMLED 
import RPi.GPIO as GPIO
import Adafruit_DHT

# GPIO beállítások
GPIO.setmode(GPIO.BCM)

# DHT11 szenzor inicializálása
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 17  # Citromsárga vezeték - GPIO17

# LED-ek beállítása
red_led = PWMLED(21)    # Piros LED - GPIO21
blue_led = PWMLED(20)   # Kék LED - GPIO20

# Helyes API kulcs a saját ThingSpeak csatornádhoz
API_KEY = 'CMQ9KPGXO1O0N9TU'

# Adatküldő függvény
def send_data_to_thingspeak(temp, humid):
    url = f'https://api.thingspeak.com/update?api_key={API_KEY}&field1={temp}&field2={humid}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"✅ Sikeres adatküldés: {temp:.1f}°C, {humid:.1f}%")
        else:
            print(f"⚠️ Sikertelen adatküldés: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Hiba az adatküldés során: {e}")

# Fő ciklus
try:
    while True:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

        if humidity is not None and temperature is not None:
            print(f"\n🌡️ Hőmérséklet: {temperature:.1f}°C")
            print(f"💧 Páratartalom: {humidity:.1f}%")

            # LED vezérlés és jelzés
            if temperature <= 20: 
                red_led.value = 1
                blue_led.value = 0
                print("🔴 Piros LED világít – Hűvös van.")
            else:
                red_led.value = 0
                blue_led.value = 1
                print("🔵 Kék LED világít – Melegebb hőmérséklet.")

            send_data_to_thingspeak(temperature, humidity)

        else:
            print("⚠️ Sikertelen szenzor olvasás. Ellenőrizd a bekötést.")
        
        time.sleep(10)

except KeyboardInterrupt:
    print("\n🛑 Program leállítva a felhasználó által.")
    GPIO.cleanup()
    red_led.close()
    blue_led.close()
