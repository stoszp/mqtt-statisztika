from appsp import MqttStatsAppSP

def main():
    app = MqttStatsAppSP(
        broker_host="broker.freemqtt.com", 
        broker_port=1883, 
        mqtt_user="freemqtt", 
        mqtt_password="public",
        topic="a5f287a4-d45c-4450-9858-013ff79574f7/topic"
    )
    app.sp_run()

if __name__ == "__main__":
    main()
