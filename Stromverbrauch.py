#Programm zur Ermittlung und Verbesserung des Stromverbrauches
#Autor: Tim-Luca Neujahr
#Version: 0.1

#import der Bibliothek
from aht10library import AHT10
from machine import SoftI2C, Pin
import network
import time
from umqtt.simple import MQTTClient
import ujson

# WLAN-Konfiguration
wlan_ssid = "BZTG-IoT"
wlan_passwort = "WerderBremen24"

# -- MQTT --
mqtt_broker = "85.215.147.110"     # IP-Adresse des MQTT-Brokers
mqtt_port = 1883                                # Port des MQTT-Brokers (Standardmäßig 1883)
mqtt_user = "tim"                        # Falls eingerichtet Nutzername und Passwort zum verbinden mit dem MQTT-Broker
mqtt_password = "Tim"
mqtt_publish_thema = "esp32/AHT10"      # Das Publish Thema bennenen. Muss übereinstimmen mit MQTT IN in Node-Red!
client_id = "esp32-s3"
mqtt_client = None 
# I2C Schnittstellen Konfiguration (Die Eingänge müssen entsprechend angepasst werden)
i2c = SoftI2C(scl=Pin(9), sda=Pin(10))
wlan = network.WLAN(network.STA_IF)

#Variable initalisieren für leichteren Zugriff auf den AHT10.
sensor = AHT10(i2c)

# === Funktionen ===
def verbinde_wlan(): # Verbindet mit dem konfigurierten WLAN.
    print("Verbinde mit WLAN:", wlan_ssid)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(wlan_ssid, wlan_passwort)
        verbindungs_versuche = 0
        while not wlan.isconnected() and verbindungs_versuche < 20:
            print(".", end="")
            time.sleep(1)
            verbindungs_versuche += 1
    if wlan.isconnected():
        print("\nWLAN verbunden. IP-Info:", wlan.ifconfig())
        return True
    else:
        print("\nWLAN-Verbindung fehlgeschlagen.")
        wlan.active(False)
        return False

def trenne_wlan(): # Trennt die WLAN-Verbindung
    if wlan and wlan.isconnected():
        wlan.disconnect()
    wlan.active(False)
    print("WLAN getrennt und deaktiviert.")
    
# Baut eine Verbindung zum konfigurierten MQTT-Broker auf
def verbinde_mqtt(): 
    global mqtt_client
    if mqtt_client is None:
        mqtt_client = MQTTClient(client_id, mqtt_broker, port=mqtt_port, user=mqtt_user, password=mqtt_password)
        print("Verbinde mit MQTT Broker...")
        mqtt_client.connect()
        print("MQTT verbunden.")

    try:
        print("Verbinde mit MQTT Broker...")
        mqtt_client.connect()
        print("MQTT verbunden.")
        return True
    
    except Exception as e:
            print(f"MQTT Verbindungsfehler: {e}")
           # Bei einem Fehler den Client zurücksetzen, damit es neu versucht wird
            mqtt_client = None
            return False
    
def sende_mqtt(thema, daten): #Sendet die Daten an den MQTT-Broker
    global mqtt_client
    if mqtt_client is None or not wlan.isconnected(): return False
    try:
        nutzlast = ujson.dumps(daten)
        mqtt_client.publish(thema, nutzlast)
        return True
    except Exception as e:
        print(f"MQTT Sende-Fehler: {e}")
        try:
            if mqtt_client: mqtt_client.disconnect()
        except Exception: pass
        mqtt_client = None
        return False
    
def sensor_auslesen():
    #Luftfeuchtigkeit auslesen umgerechnet in Prozent.
    luftfeuchtigkeit = sensor.humidity()

    #Temperatur ausmessen umgerechnet in Celsius.
    temperatur = sensor.temperature()
    
while True:
    try:
        if not wlan.isconnected():
            print("WLAN nicht verbunden. Versuche zu verbinden...")
            verbinde_wlan()
            if not wlan.isconnected():
                time.sleep(5)
                continue

        if mqtt_client is None:
            verbinde_mqtt()
            if mqtt_client is None:
                time.sleep(5)
                continue

        # Sensordaten auslesen
        luftfeuchtigkeit = sensor.humidity()
        temperatur = sensor.temperature()
        print(f"Messung: Temperatur={temperatur:.2f}°C, Luftfeuchtigkeit={luftfeuchtigkeit:.2f}%")

        # Daten für den Versand vorbereiten
        messdaten = {
            "temperatur": round(temperatur, 2),
            "luftfeuchtigkeit": round(luftfeuchtigkeit, 2)
        }

        # Daten über MQTT senden
        if sende_mqtt(mqtt_publish_thema, messdaten):
            print("Daten erfolgreich an MQTT gesendet.")
        else:
            print("Senden der Daten fehlgeschlagen.")

        # ENTFERNT: mqtt_client.check_msg() ist nicht mehr nötig.

        time.sleep(10) # Warte 10 Sekunden bis zur nächsten Messung

    except Exception as e:
        print(f"Ein unerwarteter Fehler in der Hauptschleife ist aufgetreten: {e}")
        if mqtt_client:
            try:
                mqtt_client.disconnect()
            except:
                pass
        mqtt_client = None
        print("Verbindung zurückgesetzt. Neustart-Versuch in 15 Sekunden...")
        time.sleep(60)