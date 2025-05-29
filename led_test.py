import time
from gpiozero import LED

red_led = LED(21)   # Piros LED – GPIO21
blue_led = LED(20)  # Kék LED – GPIO20

try:
    while True:
        print("🔴 Piros LED bekapcsol")
        red_led.on()
        blue_led.off()
        time.sleep(2)

        print("🔵 Kék LED bekapcsol")
        red_led.off()
        blue_led.on()
        time.sleep(2)

except KeyboardInterrupt:
    print("\n🛑 Leállítva")

finally:
    red_led.off()
    blue_led.off()
