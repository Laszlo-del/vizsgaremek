import time
import requests
from gpiozero import PWMLED
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

red_led = PWMLED(21)   # Piros LED GPIO21
blue_led = PWMLED(20)  # Kék LED GPIO20

API_KEY = '3QHRPL6BSMJJPJLV'

temperature = 17.0
humidity = 50.0
step = 0.5

def send_to_thingspeak(temp, humid):
    url = f"https://api.thingspeak.com/update?api_key={API_KEY}&field1={temp}&field2={humid}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"📡 Adat elküldve: {temp:.1f}°C, {humid:.1f}%")
        else:
            print(f"⚠️ Hibás válasz: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Hálózati hiba: {e}")

try:
    while temperature <= 22.0:
        print(f"\n🌡️ Hőmérséklet: {temperature:.1f}°C")
        print(f"💧 Páratartalom: {humidity:.1f}%")

        if temperature < 20.0:
            red_led.value = 1
            blue_led.value = 0
            print("🔴 Piros LED világít – 20°C alatt.")
        else:
            red_led.value = 0
            blue_led.value = 1
            print("🔵 Kék LED világít – 20°C felett.")

        send_to_thingspeak(temperature, humidity)

        temperature += step
        humidity += 0.3
        time.sleep(2)

    print("\n✅ Mérés vége.")

except KeyboardInterrupt:
    print("\n🛑 Program leállítva a felhasználó által.")

finally:
    red_led.off()
    blue_led.off()
    red_led.close()
    blue_led.close()
    GPIO.cleanup()
