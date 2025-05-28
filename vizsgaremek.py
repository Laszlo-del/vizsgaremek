import time
from gpiozero import PWMLED
import Adafruit_DHT
import RPi.GPIO as GPIO
import requests
import datetime

# --- GPIO Beállítások ---
# Beállítja a GPIO pinek számozási módját BCM (Broadcom chip) módra.
# Ez azt jelenti, hogy a GPIO számozást használjuk, nem a fizikai pin számokat.
GPIO.setmode(GPIO.BCM)

# --- DHT Szenzor Beállítások ---
DHT_SENSOR = Adafruit_DHT.DHT11 # A használt DHT szenzor típusa (DHT11 vagy DHT22)
DHT_PIN = 17 # A DHT szenzor adatlábának GPIO pinje. Ezt a GPIO számot módosítsd, ha máshova kötötted!

# --- Hőmérsékleti Limit a LED Jelzéshez ---
TEMP_LIMIT = 20 # A hőmérséklet határ (Celsius fokban), ami alapján a LED-ek színe vált.

# --- LED Színek Listája ---
COLORS = ['piros', 'zöld', 'kék'] # A programban használt LED színek listája.

# --- Alapértelmezett GPIO Kiosztás a LED-ekhez ---
# Ezek az alapértelmezett GPIO pinek, amelyeket a LED-ekhez használunk.
# Fontos: Minden LED-et köss be egy megfelelő előtét-ellenállással, hogy ne sérüljön a LED és a Raspberry Pi!
gpio_pins = {
    'piros': 21,
    'zöld': 16, # Ha nincs zöld LED-ed, ezt a GPIO-t használhatod másra, vagy figyelmen kívül hagyhatod.
    'kék': 20
}

# --- Alapértelmezett LED Szín Viselkedés ---
# Meghatározza, hogy melyik LED világítson a hőmérsékleti limit alatt vagy felett.
led_below_limit = 'kék'   # Ha a hőmérséklet <= TEMP_LIMIT, akkor a kék LED világít.
led_above_limit = 'piros' # Ha a hőmérséklet > TEMP_LIMIT, akkor a piros LED világít.

# --- Thingspeak Beállítások ---
# Kérlek, győződj meg róla, hogy ezek az API kulcsok és a csatorna ID helyesek!
THINGSPEAK_WRITE_API_KEY = 'ZRSWQ48LKWHEEW6G' # A Thingspeak csatornád 'Write API Key'-e. Ezzel küldesz adatokat.
THINGSPEAK_USER_API_KEY = '' # A Thingspeak fiókod 'User API Key'-e. Ezt az 'Account' -> 'My Profile' alatt találod. Szükséges az adatok törléséhez.
THINGSPEAK_CHANNEL_ID = '2974228' # A Thingspeak csatornád azonosítója (Channel ID).

THINGSPEAK_URL = "https://api.thingspeak.com/update" # A Thingspeak adatküldő URL-je.
THINGSPEAK_DELETE_URL_BASE = "https://api.thingspeak.com/channels/" # A Thingspeak adattörlő URL-jének alapja.

# LED példányok tárolására szolgáló szótár.
leds = {}

# --- Segédfüggvények ---

def init_leds():
    """
    Inicializálja a LED-eket a jelenlegi GPIO beállítások alapján, vagy frissíti azokat.
    Ez a függvény felszabadítja az előzőleg foglalt GPIO erőforrásokat és újra létrehozza a LED objektumokat.
    """
    global leds
    # Felszabadítja a korábbi GPIO erőforrásokat, ha már léteznek LED objektumok.
    for led in leds.values():
        if isinstance(led, PWMLED): # Ellenőrizzük, hogy PWMLED objektum-e, mielőtt bezárjuk.
            led.close()
    
    # Újra inicializálja a LED-eket az aktuális gpio_pins beállítások alapján.
    leds = {}
    for color, pin in gpio_pins.items():
        try:
            # Létrehozza a PWMLED objektumot a megadott GPIO pinen.
            leds[color] = PWMLED(pin)
        except Exception as e:
            # Hiba esetén értesítést küld és nullára állítja a LED objektumot.
            print(f"⚠️ Hiba a {color} LED inicializálásakor a {pin} GPIO-n: {e}")
            print("Kérlek, ellenőrizd, hogy a GPIO pin szabad-e és létezik-e.")
            leds[color] = None # Jelzi, hogy ez a LED nem inicializálható.

    print("✅ LED-ek inicializálva az új GPIO-kkal.")


def set_led(color):
    """
    Beállítja a megadott színű LED-et (bekapcsolja), a többi LED-et kikapcsolja.
    """
    # Minden LED kikapcsolása.
    for led_name, led_object in leds.items():
        if led_object is not None: # Csak akkor próbálja meg beállítani, ha inicializálva lett.
            led_object.value = 0 # Kikapcsolja a LED-et.
    
    # A kiválasztott LED bekapcsolása.
    if color in leds and leds[color] is not None:
        leds[color].value = 1 # Bekapcsolja a LED-et.
        # Kiírja, melyik LED világít, és milyen hőmérsékleti feltételhez tartozik.
        print(f"🔔 LED: {color.upper()} ({'<=20°C' if color == led_below_limit else '>20°C'})")
    else:
        print(f"⚠️ Hibás vagy nem inicializált LED szín megadva: {color}")

def send_to_thingspeak(temp, hum):
    """
    Elküldi a hőmérsékletet és páratartalmat a Thingspeak csatornára.
    """
    # Ellenőrzi, hogy az API kulcs és a csatorna ID be van-e állítva.
    if not THINGSPEAK_WRITE_API_KEY or not THINGSPEAK_CHANNEL_ID:
        print("❌ Thingspeak API kulcs vagy csatorna ID hiányzik. Adatküldés kihagyva.")
        return

    try:
        # Összeállítja az adatcsomagot (payload) a Thingspeak számára.
        # A hőmérséklet és páratartalom kerekítése két tizedesjegyre.
        payload = {
            'api_key': THINGSPEAK_WRITE_API_KEY,
            'field1': round(temp, 2), # A hőmérséklet az 1. mezőbe.
            'field2': round(hum, 2)    # A páratartalom a 2. mezőbe.
        }
        # Elküldi az adatokat HTTP GET kéréssel a Thingspeak URL-re.
        response = requests.get(THINGSPEAK_URL, params=payload)

        # Ellenőrzi a válasz státuszkódját. 200 = OK.
        if response.status_code == 200:
            print("⬆️ Adatok elküldve Thingspeakre.")
        else:
            print(f"❌ Hiba a Thingspeak küldéskor: HTTP {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        # Hálózati hibák kezelése (pl. nincs internetkapcsolat).
        print(f"⚠️ Hálózati hiba a Thingspeak küldéskor: {e}")

def delete_thingspeak_data(minutes_ago):
    """
    Törli az adatokat a Thingspeak csatornáról egy megadott időintervallumból.
    Ehhez a 'User API Key' szükséges.
    """
    # Ellenőrzi, hogy a User API kulcs és a csatorna ID be van-e állítva.
    if not THINGSPEAK_USER_API_KEY or not THINGSPEAK_CHANNEL_ID:
        print("❌ Thingspeak User API kulcs vagy csatorna ID hiányzik. Törlés kihagyva.")
        return

    # Kiszámítja az időpontot, ameddig törölni kell az adatokat.
    delete_before_date = datetime.datetime.now() - datetime.timedelta(minutes=minutes_ago)

    # Összeállítja a törlési URL-t.
    delete_url = f"{THINGSPEAK_DELETE_URL_BASE}{THINGSPEAK_CHANNEL_ID}/feeds.json"
    # Összeállítja a paramétereket a törlési kérelemhez.
    # Az 'end' paraméter ISO 8601 formátumban, UTC időzónában.
    params = {
        'api_key': THINGSPEAK_USER_API_KEY,
        'end': delete_before_date.isoformat(sep='T', timespec='seconds') + 'Z'
    }

    print(f"Adatok törlése a {THINGSPEAK_CHANNEL_ID} csatornáról {minutes_ago} perccel ezelőtti időpontig ({delete_before_date.strftime('%Y-%m-%d %H:%M:%S')} előtt).")
    try:
        # Elküldi a törlési kérést HTTP DELETE metódussal.
        response = requests.delete(delete_url, params=params)

        # Ellenőrzi a válasz státuszkódját.
        if response.status_code == 200:
            print("✅ Adatok sikeresen törölve a Thingspeakről!")
        else:
            print(f"❌ Hiba a Thingspeak törléskor: HTTP {response.status_code} - {response.text}")
            print("Tipp: Ellenőrizd a USER_API_KEY-t, az kell a törléshez!")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Hálózati hiba a Thingspeak törléskor: {e}")

# --- Konfigurációs Menüpontok ---

def change_gpio_pins():
    """
    Lehetővé teszi a piros, zöld és kék LED-ek GPIO portjainak módosítását.
    A felhasználó egyesével adhatja meg az új GPIO számokat.
    """
    print("\n🎛️ GPIO portok módosítása:")
    for color in COLORS: # Végigmegy a színeken (piros, zöld, kék).
        while True:
            try:
                # Bekéri az új GPIO számot, megjelenítve a jelenlegi beállítást.
                pin_input = input(f"{color.upper()} LED GPIO (jelenleg {gpio_pins.get(color, 'nincs beállítva')}): ")
                if pin_input.strip() == '': # Ha a felhasználó üresen hagyja, a jelenlegi érték megmarad.
                    print(f"⏩ {color.upper()} LED GPIO megtartva: {gpio_pins.get(color, 'nincs beállítva')}")
                    break
                pin = int(pin_input) # Számmá konvertálja a bevitelt.
                # Ellenőrzi, hogy érvényes GPIO számot adott-e meg (0-27 között).
                if 0 <= pin <= 27:
                    gpio_pins[color] = pin # Frissíti a gpio_pins szótárban az értéket.
                    break
                else:
                    print("⚠️ Érvénytelen GPIO szám. Kérlek, 0 és 27 közötti számot adj meg.")
            except ValueError:
                print("⚠️ Hibás érték. Kérlek, csak számot adj meg.")
    init_leds() # Az új GPIO pinekkel újra inicializálja a LED-eket.

def change_led_behavior():
    """
    Lehetővé teszi a hőmérséklethez tartozó LED színek beállítását.
    A felhasználó kiválaszthatja, melyik LED világítson a TEMP_LIMIT alatt és felett.
    """
    global led_below_limit, led_above_limit
    print(f"\n🎨 LED színek beállítása a hőmérséklet alapján ({TEMP_LIMIT}°C a határ):")
    
    # Beállítás a TEMP_LIMIT alatt.
    while True:
        below_input = input(f"{TEMP_LIMIT}°C alatt milyen LED szín legyen (piros/zöld/kék, jelenleg: {led_below_limit}): ").strip().lower()
        if below_input in COLORS:
            led_below_limit = below_input
            break
        elif below_input == '':
            print("Megtartva a jelenlegi beállítás.")
            break
        else:
            print("⚠️ Hibás szín! Kérlek, válassz a 'piros', 'zöld', 'kék' közül.")
            
    # Beállítás a TEMP_LIMIT felett.
    while True:
        above_input = input(f"{TEMP_LIMIT}°C felett milyen LED szín legyen (piros/zöld/kék, jelenleg: {led_above_limit}): ").strip().lower()
        if above_input in COLORS:
            led_above_limit = above_input
            break
        elif above_input == '':
            print("Megtartva a jelenlegi beállítás.")
            break
            
        else:
            print("⚠️ Hibás szín! Kérlek, válassz a 'piros', 'zöld', 'kék' közül.")

    print(f"✅ Beállítva: <={TEMP_LIMIT}°C ➜ {led_below_limit.upper()}, >{TEMP_LIMIT}°C ➜ {led_above_limit.upper()}")

def change_thingspeak_settings():
    """
    Lehetővé teszi a Thingspeak beállítások (Csatorna ID, Író API kulcs, Felhasználói API kulcs) módosítását.
    """
    global THINGSPEAK_CHANNEL_ID, THINGSPEAK_WRITE_API_KEY, THINGSPEAK_USER_API_KEY
    print("\n☁️ Thingspeak beállítások módosítása:")
    
    # Bekéri a Csatorna ID-t. Ha üresen hagyja, a jelenlegi megmarad.
    channel_id_input = input(f"Thingspeak csatorna ID (jelenleg '{THINGSPEAK_CHANNEL_ID}'): ").strip()
    if channel_id_input:
        THINGSPEAK_CHANNEL_ID = channel_id_input

    # Bekéri az Író API kulcsot. Ha üresen hagyja, a jelenlegi megmarad.
    write_api_key_input = input(f"Thingspeak Író API kulcs (jelenleg '{THINGSPEAK_WRITE_API_KEY}'): ").strip()
    if write_api_key_input:
        THINGSPEAK_WRITE_API_KEY = write_api_key_input

    # Bekéri a Felhasználói API kulcsot. Ha üresen hagyja, a jelenlegi megmarad.
    user_api_key_input = input(f"Thingspeak Felhasználói API kulcs (jelenleg '{THINGSPEAK_USER_API_KEY}', törléshez szükséges): ").strip()
    if user_api_key_input:
        THINGSPEAK_USER_API_KEY = user_api_key_input
        
    print("✅ Thingspeak beállítások frissítve.")

def perform_thingspeak_data_delete():
    """
    Bekéri a felhasználótól, hogy hány perccel ezelőtti adatokat töröljön, majd végrehajtja a törlést.
    """
    try:
        minutes = int(input("Hány perccel ezelőtti adatokat töröljünk? (pl. 5 perc az utolsó 5 percet törli): "))
        if minutes >= 0:
            delete_thingspeak_data(minutes)
        else:
            print("⚠️ Érvénytelen időtartam, pozitív számot adj meg!")
    except ValueError:
        print("⚠️ Hibás érték, csak számot adj meg!")

# --- Fő Működési Ciklus ---

def run_sensor_loop_and_thingspeak():
    """
    Ez a fő működési ciklus, ami folyamatosan olvassa a szenzor adatait,
    vezérli a LED-eket és küldi az adatokat a Thingspeakre.
    """
    print("\n▶️ Rendszer indítása... Nyomj CTRL+C-t a kilépéshez.")
    try:
        while True: # Végtelen ciklus a folyamatos működéshez.
            humidity, temp = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN) # Szenzor adatok olvasása.
            if temp is not None and humidity is not None:
                # Ha sikeresen olvasott adatokat, kiírja és vezérli a LED-eket.
                print(f"\n🌡️ Hőmérséklet: {temp:.1f}°C, 💧 Páratartalom: {humidity:.1f}%")
                
                # LED beállítása a hőmérsékleti limit alapján.
                if temp <= TEMP_LIMIT:
                    set_led(led_below_limit)
                else:
                    set_led(led_above_limit)
                
                # Adatok küldése Thingspeakre.
                send_to_thingspeak(temp, humidity)
            else:
                # Hiba esetén értesítést küld és kikapcsolja az összes LED-et.
                print("❌ Szenzorhiba! Ellenőrizd a bekötést és a szenzort. Nincs adat.")
                for led_object in leds.values():
                    if led_object is not None:
                        led_object.value = 0 # Minden LED kikapcsolása hiba esetén.
            time.sleep(15) # Várakozás 15 másodperc a következő mérésig (Thingspeak API limit miatt).

    except KeyboardInterrupt:
        # CTRL+C megnyomásakor lép ki ebből a ciklusból.
        print("\n🛑 Kilépés a ciklusból...")
    except Exception as e:
        # Egyéb váratlan hibák kezelése.
        print(f"Hiba történt a futás közben: {e}")
    finally:
        # Ez a rész mindig lefut, függetlenül attól, hogy hiba történt-e vagy kilépett a felhasználó.
        GPIO.cleanup() # Felszabadítja az összes használt GPIO erőforrást.
        for led_object in leds.values():
            if led_object is not None:
                led_object.close() # Bezárja a gpiozero LED objektumokat.
        print("GPIO erőforrások felszabadítva.")


# --- Főmenü ---

def main_menu():
    """
    Megjeleníti a főmenüt és kezeli a felhasználói interakciókat.
    Ez a program belépési pontja.
    """
    init_leds() # A program indításakor inicializálja a LED-eket az alapértelmezett beállításokkal.
    while True: # Végtelen ciklus a menü megjelenítéséhez, amíg a felhasználó ki nem lép.
        print("\n--- SmartTempHub Főmenü ---")
        print("1. GPIO portok módosítása")
        print("2. LED színek beállítása hőmérséklet alapján")
        print("3. Thingspeak beállítások módosítása")
        print("4. Thingspeak adatok törlése (időalapú)")
        print("5. Rendszer indítása (Szenzor + LED + Thingspeak)")
        print("6. Kilépés")

        choice = input("Válasszon (1-6): ").strip() # Bekéri a felhasználó választását.

        if choice == '1':
            change_gpio_pins()
        elif choice == '2':
            change_led_behavior()
        elif choice == '3':
            change_thingspeak_settings()
        elif choice == '4':
            perform_thingspeak_data_delete()
        elif choice == '5':
            run_sensor_loop_and_thingspeak()
            # Ha a futás befejeződött (pl. CTRL+C miatt), visszatér a főmenübe.
            # Ekkor újra inicializáljuk a LED-eket, hogy a menüből visszatérve is működjenek.
            init_leds() 
        elif choice == '6':
            print("👋 Kilépés a programból...")
            GPIO.cleanup() # Kilépéskor is tisztítja a GPIO-kat.
            for led_object in leds.values():
                if led_object is not None:
                    led_object.close() # Biztosítja a LED objektumok bezárását is.
            break # Kilép a főmenü ciklusból.
        else:
            print("❌ Érvénytelen választás. Kérlek, válassz 1 és 6 között.")

# A program indítása a főmenü meghívásával, amikor a szkriptet közvetlenül futtatják.
if __name__ == "__main__":
    main_menu()
