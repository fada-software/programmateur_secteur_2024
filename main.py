#==============================================================================
# Projet : programmateur secteur 2024
# Date: 08/12/2024
# Author: fada-software
# micropyhton sur ESP32, version 1.26.1
# https://micropython.org/download/esp32/
# IDE : Thonny 4.1.7
#==============================================================================

from machine import RTC #RTC
from machine import Pin #GPIO
import network #connexion wifi
import ntptime #serveur NTP
import socket #serveur web
import time #tempo time.sleep & time.localtime()
import asyncio #multitache

#==========================================================================
#GPIO
#==========================================================================
builtin_led = Pin(2, Pin.OUT)
led_r = Pin(27, Pin.OUT)
led_g = Pin(14, Pin.OUT)
led_b = Pin(12, Pin.OUT)
ssr = Pin(26, Pin.OUT)
inter = Pin(25, Pin.IN, Pin.PULL_UP)
do_1 = Pin(33, Pin.OUT)
do_2 = Pin(32, Pin.OUT)

builtin_led.value(0) #0=off
led_r.value(0)
led_g.value(0)
led_b.value(0)
ssr.value(1) #allumé par défaut à la mise sous tension
do_1.value(0)
do_2.value(0)

#==========================================================================
#couleur LED RGB
#==========================================================================
#Couleurs (format RGB)
COLOR_BLACK = 0b000
COLOR_RED = 0b100
COLOR_GREEN = 0b010
COLOR_BLUE = 0b001
COLOR_MAGENTA = 0b101
COLOR_CYAN = 0b011
COLOR_YELLOW = 0b110
COLOR_WHITE = 0b111

def LED_RGB_displayColor(color):
    led_r.value((color & 0b100) >> 2)
    led_g.value((color & 0b010) >> 1)
    led_b.value(color & 0b001)

#==========================================================================
#init RTC ESP32, variales globales
#==========================================================================
#dictionnaires des jours et mois
dict_jours = {0:"lundi", 1:"mardi", 2:"mercredi", 3:"jeudi", 4:"vendredi", 5:"samedi", 6:"dimanche"}
dict_mois = {1:"janvier", 2:"fevrier", 3:"mars", 4:"avril", 5:"mai", 6:"juin", 7:"juillet", 8:"aout", 9:"septembre", 10:"octobre", 11:"novembre", 12:"decembre"}
rtc = RTC()
# print(rtc.datetime()) #(year, month, day, weekday, hours, minutes, seconds, subseconds)
# print(time.localtime()) # (year, month, mday, hour, minute, second, weekday, yearday)

wlan = network.WLAN(network.STA_IF)
WIFI_SSID = 'YOUR_WIFI_SSID'
WIFI_PASSWORD = 'YOUR_WIFI_PASSWORD'
heure_allumage = ''
heure_semaine_on   = '19:00'
heure_semaine_off  = '23:00'
heure_weekend_on   = '08:00'
heure_weekend_off  = '23:00'

config_filename = 'heures.txt'

power_state = 1 #idem que ssr.value(1) #allumé par défaut à la mise sous tension

#==========================================================================
# affichage de heures ON/OFF
#==========================================================================
def affichage_heures_ON_OFF():
    print('Semaine ON  : ' + heure_semaine_on)
    print('Semaine OFF : ' + heure_semaine_off)
    print('Weekend ON  : ' + heure_weekend_on)
    print('Weekend OFF : ' + heure_weekend_off)

#==========================================================================
# lecture des heures OIN/OFF dans le fichier de config heures.txt
#==========================================================================
def lecture_fichier_config():
    global heure_semaine_on 
    global heure_semaine_off
    global heure_weekend_on 
    global heure_weekend_off
    try:
        filename = open(config_filename,'r')
    except: #fonctionne sur PC, mais pas sur micropython
        print('fichier introuvable, creation fichier')
        filename = open(config_filename,'w')
        filename.write('Semaine ON  |19:07\n')
        filename.write('Semaine OFF |23:07\n')
        filename.write('Weekend ON  |08:07\n')
        filename.write('Weekend OFF |23:07\n')
    mylist = filename.read().splitlines() 
    # print(mylist)
    heure_semaine_on   = mylist[0].split('|')[1]
    heure_semaine_off  = mylist[1].split('|')[1]
    heure_weekend_on   = mylist[2].split('|')[1]
    heure_weekend_off  = mylist[3].split('|')[1]
    affichage_heures_ON_OFF()
    filename.close()

#==========================================================================
#retourne la date & heure en string
#==========================================================================
def string_date_heure():
    (annee, mois, jour, jour_semaine, heures, minutes, secondes, sub_secondes) = rtc.datetime() # get tuple with date and time
    maintenant = (f'{dict_jours[jour_semaine]} {jour} {dict_mois[mois]} {annee} {heures}h{minutes}m{secondes}s')
    return maintenant

#==========================================================================
#correction heure d'été manuelle
#==========================================================================
# https://www.engineersgarage.com/micropython-esp8266-esp32-rtc-utc-local-time/
# sec = ntptime.time()
# timezone_hour = 1
# (year, month, day, hours, minutes, seconds, weekday, yearday) = time.localtime(sec + timezone_hour * 3600)
# rtc.datetime((year, month, day, 0, hours, minutes, seconds, 0))
#==========================================================================
#correction heure d'été automatique
#==========================================================================
#https://forum.micropython.org/viewtopic.php?f=2&t=4034
# Micropython esp8266
# This code returns the Central European Time (CET) including daylight saving
# Winter (CET) is UTC+1H Summer (CEST) is UTC+2H
# Changes happen last Sundays of March (CEST) and October (CET) at 01:00 UTC
# Ref. formulas : http://www.webexhibits.org/daylightsaving/i.html
#                 Since 1996, valid through 2099
def cettime():
    year = time.localtime()[0]       #get current year
    HHMarch   = time.mktime((year,3 ,(31-(int(5*year/4+4))%7),1,0,0,0,0,0)) #Time of March change to CEST
    HHOctober = time.mktime((year,10,(31-(int(5*year/4+1))%7),1,0,0,0,0,0)) #Time of October change to CET
    now=time.time()
    if now < HHMarch :               # we are before last sunday of march
        cet=time.localtime(now+3600) # CET:  UTC+1H
    elif now < HHOctober :           # we are before last sunday of october
        cet=time.localtime(now+7200) # CEST: UTC+2H
    else:                            # we are after last sunday of october
        cet=time.localtime(now+3600) # CET:  UTC+1H
    return(cet)

def update_cettime():
    (year, month, day, hours, minutes, seconds, weekday, yearday) = cettime()
    rtc.datetime((year, month, day, 0, hours, minutes, seconds, 0))

#==========================================================================
#serveur web
#==========================================================================
#https://www.gcworks.fr/tutoriel/esp/Serveurweb.html
#entrée heure : https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/time
def web_page():
    print(string_date_heure())

    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>ESP32 Serveur Web</title>
            <style>
                h1 { font-size: 24px; }
                p { font-size: 20px; }
            </style>
        </head>
        <body>
            <p><span>Heure allumage : """ + heure_allumage + """</span></p>
            <p><span>Heure courante : """ + string_date_heure() + """</span></p>
            <h1>Horaires Programmateur</h1>
            <form action="/" method="get" target="_blank">
            <input type="submit" value="Enregistrer" />
            <h1>semaine</h1>
            <label for="semaine_on">ON :</label>
            <input type="time" id="semaine_on" name="semaine_on" value="{VAR1}" required />
            <label for="semaine_off">OFF :</label>
            <input type="time" id="semaine_off" name="semaine_off" value="{VAR2}" required />

            <h1>weekend</h1>
            <label for="weekend_on">ON :</label>
            <input type="time" id="weekend_on" name="weekend_on" value="{VAR3}" required />
            <label for="weekend_off">OFF :</label>
            <input type="time" id="weekend_off" name="weekend_off" value="{VAR4}" required />

            </form>
        </body>
    </html>
    """.format(VAR1=heure_semaine_on, VAR2=heure_semaine_off, VAR3=heure_weekend_on, VAR4=heure_weekend_off)
    return html

# recup paramètres page HTML
# https://github.com/orgs/micropython/discussions/10981
def parse_params(part):
    parameters = {}
    for piece in part.split(" "):
        if "/?" in piece:
            piece = piece.replace("/?", "")
            amp_split = piece.split("&")
            for param_set in amp_split:
                eq_split = param_set.split("=")
                parameters[eq_split[0]] = eq_split[1]
    return parameters

#exemple utilisé :
# https://gist.github.com/aallan/3d45a062f26bc425b22a17ec9c81e3b6
#autre exemple :
#https://thepythoncode.com/assistant/transformation-details/micropython-web-server-with-uasyncio/?utm_content=cmp-true
async def serve_client(reader, writer):
    global heure_semaine_on  
    global heure_semaine_off 
    global heure_weekend_on  
    global heure_weekend_off 
    
    LED_RGB_displayColor(COLOR_YELLOW)
    print("Client connected")
    request = await reader.readline()
    print("Request:", request)
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass
    
    request = str(request).replace("b'","").replace("'","")
    request = request.split("\\r\\n")
    
    for part in request:
        print(part)

    for part in request:
        if "/?" and "GET" in part:
            params = parse_params(part)
    
    if params:
        print(f"Params: {params}\n")
        # Params: {'weekend_on': '23%3A23', 'semaine_off': '07%3A08', 'weekend_off': '23%3A56', 'semaine_on': '04%3A05'}
        # heure_semaine_on   = params["semaine_on"].replace('%3A',':')
        # heure_semaine_off  = params["semaine_off"].replace('%3A',':')
        # heure_weekend_on   = params["weekend_on"].replace('%3A',':')
        # heure_weekend_off  = params["weekend_off"].replace('%3A',':')

        #enregistrement des heures ON/OFF dans un fichier texte
        filename = open(config_filename,'w')
        filename.write('Semaine ON  |' + params["semaine_on"].replace('%3A',':') + '\n')
        filename.write('Semaine OFF |' + params["semaine_off"].replace('%3A',':') + '\n')
        filename.write('Weekend ON  |' + params["weekend_on"].replace('%3A',':') + '\n')
        filename.write('Weekend OFF |' + params["weekend_off"].replace('%3A',':') + '\n')
        filename.close()
        lecture_fichier_config()

    response = web_page()
    writer.write('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
    writer.write(response)

    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")

    time.sleep(1) #pour laisser la LED allumée 1s
    LED_RGB_displayColor(COLOR_BLACK)

#==========================================================================
#connexion wifi
#==========================================================================
def connect_to_network():
    global WIFI_SSID, WIFI_PASSWORD
    print(string_date_heure())
    LED_RGB_displayColor(COLOR_CYAN)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to wifi network...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
            print('.',end='')
    print('network config:', wlan.ifconfig())
    ips_and_mask = wlan.ifconfig()
    my_ip = ips_and_mask[0]
    print(f"http://{my_ip}/\n")
    time.sleep(1) #pour laisser la LED allumée au moins 1s
    LED_RGB_displayColor(COLOR_BLACK)

#==========================================================================
# mise à jour heure avec serveur NTP
#==========================================================================
def ntp_time_update():
    NTP_triggered = False
    LED_RGB_displayColor(COLOR_MAGENTA)
    ntptime.host = "pool.ntp.org"
    ntptime.timeout = 1
    print(string_date_heure())
    print('mise a jour NTP...')
    while not NTP_triggered:
        try:
            ntptime.settime() #recupere heure UTC sur serveur NTP, et met à jour rtc.datetime() et time.localtime() !
            NTP_triggered = True
            update_cettime() #ajustement decalage horaire (timezone)
            print(string_date_heure())
            time.sleep(1) #pour laisser la LED allumée au moins 1s
            LED_RGB_displayColor(COLOR_BLACK)
        except:
            print('.',end='')
            NTP_triggered = False
            time.sleep(30) #nouvel essai toutes les 30s

#==========================================================================
#power ON / OFF
#==========================================================================
def power_on():
    global power_state
    if power_state == 0:
        print(string_date_heure())
        print('Power ON')
        ssr.value(1)
        power_state = 1
        LED_RGB_displayColor(COLOR_GREEN)
        time.sleep(1) #pour laisser la LED allumée 1s
        LED_RGB_displayColor(COLOR_BLACK)
    
def power_off():
    global power_state
    if power_state == 1:
        wlan.active(False) #extinction wifi ESP32 quand on est power OFF
        print(string_date_heure())
        print('Power OFF')
        ssr.value(0)
        power_state = 0
        LED_RGB_displayColor(COLOR_RED)
        time.sleep(1) #pour laisser la LED allumée 1s
        LED_RGB_displayColor(COLOR_BLACK)

#==========================================================================
# MAIN
#==========================================================================
async def main():
    global heure_allumage
    lecture_fichier_config()
    connect_to_network()
    ntp_time_update()
    heure_allumage = string_date_heure() #affiché sur page web, pour vérifier si le module reboot tout seul
    print('Heure allumage :', heure_allumage)
    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))

    while True:
        if inter.value() == 1: #inter in ON position. Note : l'inter force également l'allumage du relais en HW.
            # print('Interrupteur ON')
            power_on()
        else: #inter in AUTO position
            # print('Interrupteur AUTO')
            (year, month, mday, hour, minute, second, weekday, yearday) = time.localtime()
            #weekday=0 : monday / 6 : sunday
            if weekday >= 5: #weekend
                horaire_minute_on = int(heure_weekend_on[0:2]) * 60 + int(heure_weekend_on[3:5])
                horaire_minute_off = int(heure_weekend_off[0:2]) * 60 + int(heure_weekend_off[3:5])
            else: #week
                horaire_minute_on = int(heure_semaine_on[0:2]) * 60 + int(heure_semaine_on[3:5])
                horaire_minute_off = int(heure_semaine_off[0:2]) * 60 + int(heure_semaine_off[3:5])

            horaire_minute_actuel = hour * 60 + minute
            if horaire_minute_actuel >= horaire_minute_on and horaire_minute_actuel < horaire_minute_off:
                power_on()
            else:
                power_off()

        if power_state == 1 and not wlan.isconnected(): #pour se reconnecter et se remettre à l'heure après un power_on()
            print(string_date_heure())
            print("Remise a l'heure")
            connect_to_network()
            ntp_time_update()
        
        await asyncio.sleep_ms(1000) #1s available time for web server task

#==========================================================================
# lancement main avec asyncio
#==========================================================================
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop() #resets the loop’s state
