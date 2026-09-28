import random
import string
import time
import paho.mqtt.client as mqtt

# @Linux: source .venv/bin/activate

broker_host = "broker.freemqtt.com"
broker_port = 1883
mqtt_user = "freemqtt"
mqtt_password = "public"
topic = "a5f287a4-d45c-4450-9858-013ff79574f7/topic"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(mqtt_user, mqtt_password)

print("Kapcsolódás a brókerhez...")
client.connect(broker_host, broker_port, 60)
client.loop_start()

print("Periodikus publikálás elindítva. Kilépéshez nyomj ^C-t!")

try:
    while True:
        p_size = random.randint(1, 1000)
        payload = "".join(random.choices(string.ascii_letters + string.digits, k=p_size))

        client.publish(topic, payload, qos=1)
        print(f"Elküldve {p_size} byte")

        dT = random.randint(1, 5)
        time.sleep(dT)

except KeyboardInterrupt:
    print("\n[!] ^C érzékelve, leállás...")
    client.loop_stop()
    client.disconnect()
    print("Leállítva.")
