#Programm zur Ermittlung und Verbesserung des Stromverbrauches
#Autor: Tim-Luca Neujahr
#Version: 0.3 - Deep Sleep

# --- Bibliotheken importieren ---
from aht10library import AHT10
from machine import SoftI2C, Pin
import machine                  
import network
import time
from umqtt.simple import MQTTClient
import ujson

# --- Konfiguration ---
# WLAN-Konfiguration
wlan_ssid = "BZTG-IoT"
wlan_passwort = "WerderBremen24"

# -- MQTT --
mqtt_broker = "85.215.147.110"
mqtt_port = 1883
mqtt_user = "tim"
mqtt_password = "Tim"
mqtt_publish_thema = "esp32/AHT10"
client_id = "esp32-s3-deepsleep" # Client ID für Deep Sleep angepasst
mqtt_client = None

# I2C Schnittstellen Konfiguration
i2c = SoftI2C(scl=Pin(9), sda=Pin(10))

# WLAN-Interface
wlan = network.WLAN(network.STA_IF)

# AHT10 Sensor initialisieren
sensor = AHT10(i2c)

# === Funktionen ===

def verbinde_wlan():
    print("Verbinde mit WLAN:", wlan_ssid)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(wlan_ssid, wlan_passwort)
        verbindungs_versuche = 0
        while not wlan.isconnected() and verbindungs_versuche < 15:
            print(".", end="")
            time.sleep(1)
            verbindungs_versuche += 1
    if wlan.isconnected():
        print("\nWLAN verbunden. IP-Info:", wlan.ifconfig())
        return True
    else:
        print("\nWLAN-Verbindung fehlgeschlagen.")
        wlan.active(False) # Bei Fehler WLAN wieder deaktivieren
        return False

def trenne_wlan():
    if wlan and wlan.isconnected():
        wlan.disconnect()
    wlan.active(False)
    print("WLAN getrennt und deaktiviert.")

def verbinde_mqtt():
    global mqtt_client
    if mqtt_client is None:
        mqtt_client = MQTTClient(client_id, mqtt_broker, port=mqtt_port, user=mqtt_user, password=mqtt_password)
    try:
        print("Verbinde mit MQTT Broker...")
        mqtt_client.connect()
        print("MQTT verbunden.")
        return True
    except Exception as e:
        print(f"MQTT Verbindungsfehler: {e}")
        mqtt_client = None
        return False

def sende_mqtt(thema, daten):
    global mqtt_client
    if mqtt_client is None or not wlan.isconnected(): return False
    try:
        nutzlast = ujson.dumps(daten)
        mqtt_client.publish(thema, nutzlast)
        return True
    except Exception as e:
        print(f"MQTT Sende-Fehler: {e}")
        return False

# ==============================================================
# ========== HAUPTPROGRAMM MIT DEEP SLEEP  ==========
# ==============================================================

# 1. Versuche, eine WLAN-Verbindung herzustellen.
if verbinde_wlan():

    # 2. Wenn WLAN erfolgreich ist, versuche MQTT-Verbindung.
    if verbinde_mqtt():

        # 3. Sensordaten auslesen
        luftfeuchtigkeit = sensor.humidity()
        temperatur = sensor.temperature()
        print(f"Messung: Temperatur={temperatur:.2f}°C, Luftfeuchtigkeit={luftfeuchtigkeit:.2f}%")

        # 4. Daten für den Versand vorbereiten
        messdaten = {
            "temperatur": round(temperatur, 2),
            "luftfeuchtigkeit": round(luftfeuchtigkeit, 2)
        }

        # 5. Daten über MQTT senden
        if sende_mqtt(mqtt_publish_thema, messdaten):
            print("Daten erfolgreich an MQTT gesendet.")
        else:
            print("Senden der Daten fehlgeschlagen.")
        
        # Kurze Pause (1 Sekunde), um sicherzustellen, dass die Nachricht Zeit hat, gesendet zu werden
        time.sleep(1)
        
        # Verbindungen sauber trennen, bevor es in den Schlaf geht
        try:
            mqtt_client.disconnect()
        except Exception as e:
            pass # Ignoriere Fehler beim Trennen
        trenne_wlan()

else:
    # Falls schon die WLAN-Verbindung fehlschlägt, gibt es eine Meldung.
    print("Keine WLAN-Verbindung möglich. Gehe trotzdem schlafen, um Strom zu sparen.")


# 6. ESP32 in den Deep Sleep schicken
# Die Zeit wird in Millisekunden (ms) angegeben. 58000 ms = 58 Sekunden.
# Dies erfüllt die Anforderung von 55-59 Sekunden.
sleep_duration_ms = 58000
print(f"Gehe für {sleep_duration_ms / 1000} Sekunden in den Deep Sleep...")
machine.deepsleep(sleep_duration_ms)