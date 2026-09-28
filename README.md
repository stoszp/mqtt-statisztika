# MQTT topic statisztikát megjelenítő grafikus alkalmazás

ISR-116 - Szkript nyelvek
Stósz Péter
:P 6MK 04:


APP paraméterként megadott MQTT topicra publikált üzenetek számlálása 
és a üzenet payload méretből (byte) számított statisztikák megjelenítése.
3 időablakban vizsgálja / jeleníti meg a statisztikát.
Ez a 3 időablak alapesetben 1 / 2 / 5 perc (mely a WINDOWS konstansban felülbírálható).

A megjelenítést/frissítést két esemény válthatja ki:
1) MQTT üzenet beérkezése (és feldolgozás),
2) perc felbontású időzítő aktiválódása.

A fenti működésből adódik, hogy ha nincs topicra beérkezett üzenet (esemény), 
akkor a 'lejárt' üzenetek eltűnése/purgálása a statisztikából nem szigorúan 60/120/300 másodperces 
mozgóablak szerint történik, hanem csak az időzítő aktiválódásával.

Azért, hogy az MQTT topic olvasása ne pollozó módban történjen, 
az MQTT kezelést egy külön szál végzi és az üzenetkezelés eseményalapú.
A szál a 'főprogrammal' queue-n keresztül kommunikál.

---

Az alkalmazás működéséhez telepíteni kell a paho-mqtt csomagot;
venv aktiválása után pip install paho-mqtt

---

Modulok:
tkinter:			Grafikus felhasználói felület (GUI) építéséhez.
threading:			Háttérszálas (background thread) futtatáshoz, hogy az MQTT kapcsolat ne fagyaszthassa le az ablakot.
queue:				Szálak közötti biztonságos üzenetküldéshez és adatsorok kezeléséhez.
collections.deque:	Bővíthető adatszerkezet a bejövő üzenetek tárolására.
dataclasses:		Egyszerű, adattárolásra optimalizált osztályok létrehozásához.
datetime/timedelta:	Időbélyegek kezeléséhez és az időablakok számításához.
paho.mqtt.client:	MQTT bróker kommunikációhoz (kapcsolódás, feliratkozás, üzenetek fogadása).


Osztályok:
MqttMessageSP:		Idősoros adatosztály.
MqttStatsAppSP:		A Tkinter alapú grafikus felületet és az MQTT klienst összefogó fő vezérlőosztály.


Függvények/metódusok:
APP inicializálás és GUI:
  __init__:			Létrehozza a főablakot, beállítja az eseménykezelőket, elindítja az MQTT háttérszálat és az időzítőket.
  sp_create_gui:	Felépíti a grafikus felületet (címkék, statisztikai táblázat, kilépés gomb).
  sp_run:			Elindítja a Tkinter főciklusát (mainloop).
  sp_close:			Szabályosan lezárja az MQTT kapcsolatot és bezárja az ablakot.

MQTT kommunikáció:
  sp_create_mqtt_client: Konfigurálja és visszaadja az MQTT klienst.
  sp_mqtt_worker:	Háttérszálon futtatja az MQTT kapcsolat fenntartását (loop_forever).
  sp_on_connect:	Kezeli a brókerhez való csatlakozást és a topicra való feliratkozást.
  sp_on_message:	Fogadja a bejövő üzeneteket, sorba (queue) teszi, és Tkinter eseményt vált ki.
  sp_on_disconnect:	Kezeli a[z MQTT] kapcsolat megszakadásának eseményét.

Adatfeldolgozás és statisztika:
  sp_on_mqtt_data_event:	Kiolvassa/kiüríti az üzenetsort, és frissíti a statisztikai táblázatot.
  sp_remove_old_messages:	Eltávolítja a 15 percnél régebbi [idősoros] üzeneteket a memóriából.
  sp_get_messages_for_window: Szűri az üzeneteket a megadott időablak (WINDOWS tuple) alapján.
  sp_calculate_statistics:	Kiszámítja az adott ablakra vonatkozó üzenetszámot, a maximális és az átlagos üzenetméretet.
  sp_update_table:			Frissíti a grafikus felületen lévő táblázat értékeit.

Időzítések:
  sp_schedule_next_minute_event:Beütemezi a következő időzítőeseményt.
  sp_generate_minute_event:		Végrehajtja az ütemezett eseményt.
  sp_set_status:				Frissíti az állapotjelző szöveget.
  sp_set_status_from_thread:	Frissíti a háttérszálról érkező állapotjelző szöveget.

---

Az alkalmazás kezdeti tesztelése MQTTX-szel történt, 
majd nagyobb mennyiségű üzenet előállításhoz készült a sender.py segédprogram.
Ez utóbbi 1-5 másodperces periodicitással küld random 1-1000 byte payload méretű üzenetet
adott topic-ra.

---

Az alkalmazás fejlesztése és tesztelése Ubuntu Linux-on történt.
venv aktiválás Linux környezetben: source .venv/bin/activate
