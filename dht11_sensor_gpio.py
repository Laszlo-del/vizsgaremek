import requests
import time
from gpiozero import PWMLED 
import RPi.GPIO as GPIO
import Adafruit_DHT

# --- 🔢 GPIO PIN BEKÉRÉS --- #
print("Add meg a LED-ek GPIO pinjeit (ha nem használsz egy színt, írj 0-t):")
gpio_kek = int(input("🔵 Kék LED GPIO: "))
gpio_piros = int(input("🔴 Piros LED GPIO: "))
gpio_zold = int(input("🟢 Zöld LED GPIO (nem lesz használva): "))

# --- 🛠️ LED inicializálás csak ha GPIO ≠ 0 --- #
led_kek = PWMLED(gpio_kek) if gpio_kek != 0 else None
led_piros = PWMLED(gpio_piros) if gpio_piros != 0 else None
led_zold = PWMLED(gpio_zold) if gpio_zold != 0 else None  # Nem használjuk most

# --- 🌡️ Szenzor és GPIO setup --- #
GPIO.setmode(GPIO.BCM)
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 17

# --- 🌐 API beállítás --- #
API_KEY = 'CMQ9KPGXO1O0N9TU'

# --- 📤 ThingSpeak küldés --- #
def send_data_to_thingspeak(temp, humid):
    url = f'https://api.thingspeak.com/update?api_key={API_KEY}&field1={temp}&field2={humid}'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"✅ Feltöltve: {temp:.1f}°C, {humid:.1f}%")
        else:
            print(f"⚠️ Hiba: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Hálózati hiba: {e}")

# --- 🔁 Fő ciklus --- #
try:
    while True:
        humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

        if humidity is not None and temperature is not None:
            print(f"\n🌡️ Hőmérséklet: {temperature:.1f}°C")
            print(f"💧 Páratartalom: {humidity:.1f}%")

            # --- LED vezérlés --- #
            if temperature <= 20:
                if led_kek: led_kek.value = 1
                if led_piros: led_piros.value = 0
            else:
                if led_kek: led_kek.value = 0
                if led_piros: led_piros.value = 1

            # Zöld LED kikapcsolása ha létezik
            if led_zold: led_zold.value = 0

            send_data_to_thingspeak(temperature, humidity)
        else:
            print("⚠️ Sikertelen szenzorolvasás.")

        time.sleep(10)

except KeyboardInterrupt:
    print("\n🛑 Program leállítva.")
    GPIO.cleanup()
    if led_kek: led_kek.close()
    if led_piros: led_piros.close()
    if led_zold: led_zold.close()
