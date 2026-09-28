import queue
import threading
import tkinter as tk

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt


MQTT_DATA_EVENT = "<<MqttData>>"
MINUTE_EVENT = "<<MinuteChanged>>"
WINDOWS = (1, 2, 5)


@dataclass
class MqttMessageSP:
    timestamp: datetime
    payload_bytes: int


class MqttStatsAppSP:
    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        mqtt_user: str,
        mqtt_password: str,
        topic: str
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        self.topic = topic
        self.closing = False
        self.mqtt_connected = False
        self.mqtt_queue = queue.Queue()
        self.messages = deque()
        self.root = tk.Tk()
        self.root.title("MQTT üzenetstatisztika")
        self.root.geometry("650x430")
        self.root.minsize(500,380)
        self.root.protocol("WM_DELETE_WINDOW", self.sp_close)
        self.sp_create_gui()
        self.root.bind(MQTT_DATA_EVENT, self.sp_on_mqtt_data_event)
        self.root.bind(MINUTE_EVENT, self.sp_on_minute_event)
        self.mqtt_client = ( self.sp_create_mqtt_client() )
        self.mqtt_thread = threading.Thread(
            target=self.sp_mqtt_worker,
            name="mqtt-worker",
            daemon=True,
        )
        self.mqtt_thread.start()
        self.sp_schedule_next_minute_event()


    def sp_create_gui(self):
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill=tk.X, padx=15, pady=(15, 8))

        self.topic_label = tk.Label(
            info_frame,
            font=("Arial", 12),
            text=f"Topic: {self.topic}"
        )

        self.topic_label.pack(anchor=tk.W, pady=(5, 0))
        self.broker_label = tk.Label(
            info_frame,
            font=("Arial", 12),
            text=(
                f"MQTT bróker: "
                f"{self.broker_host}:"
                f"{self.broker_port}"
            )
        )

        self.broker_label.pack(anchor=tk.W)
        self.status_label = tk.Label(
            info_frame, 
            font=("Arial", 10, "bold"),
            text="MQTT bróker kapcsolódás..."
        )
        self.status_label.pack(anchor=tk.W, pady=(3, 0))
        table_frame = tk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        headers = ("Perc", "Üzenetek száma", "Méret (max)", "Méret (átlag)")
        for column, text in enumerate(headers):
            label = tk.Label(
                table_frame,
                font=("Arial", 12, "bold"),
                text=text,
                relief=tk.RIDGE,
                borderwidth=1,
                padx=10,
                pady=8,
                anchor=tk.CENTER,
            )
            label.grid(row=0, column=column, sticky="nsew")

        self.value_labels = {}

        for row, minutes in enumerate(WINDOWS, start=1):
            minute_label = tk.Label(
                table_frame,
                font=("Arial", 12),
                text=str(minutes),
                relief=tk.RIDGE,
                borderwidth=1,
                padx=10,
                pady=12,
                anchor=tk.CENTER,
            )
            minute_label.grid(row=row, column=0, sticky="nsew")

            for column, metric in enumerate(("count", "max", "average"), start=1):
                value_label = tk.Label(
                    table_frame,
                    font=("Arial", 12),
                    text="0",
                    relief=tk.RIDGE,
                    borderwidth=1,
                    padx=10,
                    pady=12,
                    anchor=tk.CENTER,
                )
                value_label.grid(row=row, column=column, sticky="nsew")
                self.value_labels[(minutes, metric)] = value_label

        for column in range(4):
            table_frame.columnconfigure(column, weight=1)

        for row in range(4):
            table_frame.rowconfigure(row, weight=1)

        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 15))

        self.exit_button = tk.Button(button_frame, text="Kilépés", command=self.sp_close, width=12, height=1)
        self.exit_button.pack(anchor=tk.CENTER)


    def sp_create_mqtt_client(self):
        client = mqtt.Client(callback_api_version=(mqtt.CallbackAPIVersion.VERSION2))
        client.username_pw_set(self.mqtt_user, self.mqtt_password)
        client.on_connect = (self.sp_on_connect)
        client.on_message = (self.sp_on_message)
        client.on_disconnect = (self.sp_on_disconnect)
        return client


    def sp_mqtt_worker(self):
        try:
            self.mqtt_client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.mqtt_client.loop_forever()
        except Exception as exc:
            if not self.closing:
                self.sp_set_status_from_thread(f"MQTT hiba: {exc}")


    def sp_on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.mqtt_connected = False
            self.sp_set_status_from_thread(
                f"MQTT kapcsolódási hiba: " 
                f"{reason_code} (code={int(reason_code)})"
            )
        else:
            self.mqtt_connected = True
            client.subscribe(self.topic, qos=0)
            self.sp_set_status_from_thread("MQTT kapcsolat létrejött, topic feliratkozás sikeres")


    def sp_on_message(self, client, userdata, message):
        self.mqtt_queue.put(MqttMessageSP(timestamp=datetime.now(), payload_bytes=len(message.payload)))
        self.root.event_generate(MQTT_DATA_EVENT, when="tail")


    def sp_on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.mqtt_connected = False
        if not self.closing:
            self.sp_set_status_from_thread("MQTT kapcsolat megszakadt")


    def sp_set_status_from_thread(self, text: str):
        if not self.closing:
            self.root.after(0, lambda: self.sp_set_status(text))


    def sp_set_status(self, text: str):
        if not self.closing:
            self.status_label.config(text=text)


    def sp_on_mqtt_data_event(self, event=None):
        if self.closing:
            return

        while True:
            try:
                message = (self.mqtt_queue.get_nowait())
                self.messages.append(message)
            except queue.Empty:
                break

        self.sp_remove_old_messages()
        self.sp_update_table()


    def sp_schedule_next_minute_event(self):
        if not self.closing:
            now = datetime.now()
            next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
            delay = (next_minute - now).total_seconds()
            delay_ms = max(1, int(delay * 1000))
            self.root.after(delay_ms, self.sp_generate_minute_event)


    def sp_generate_minute_event(self):
        if not self.closing:
            self.root.event_generate(MINUTE_EVENT, when="tail")


    def sp_on_minute_event(self, event=None):
        if not self.closing:
            self.sp_remove_old_messages()
            self.sp_update_table()
            self.sp_schedule_next_minute_event()


    def sp_remove_old_messages(self):
        limit = (datetime.now() - timedelta(minutes=15))
        while (self.messages and self.messages[0].timestamp < limit):
            self.messages.popleft()


    def sp_get_messages_for_window(self, minutes: int):
        limit = (datetime.now() - timedelta(minutes=minutes))
        return [
            message
            for message in self.messages
            if message.timestamp >= limit
        ]

    @staticmethod
    def sp_calculate_statistics(messages):
        if not messages:
            return 0, 0, 0.0

        sizes = [
            message.payload_bytes
            for message in messages
        ]

        count = len(sizes)
        maximum = max(sizes)
        average = (sum(sizes) / count)

        return (count, maximum, average)


    def sp_update_table(self):
        if self.closing:
            return

        for minutes in WINDOWS:
            messages = (self.sp_get_messages_for_window(minutes))
            count, maximum, average = (self.sp_calculate_statistics(messages))
            self.value_labels[(minutes, "count")].config(text=str(count))
            self.value_labels[(minutes, "max")].config(text=str(maximum))
            self.value_labels[(minutes, "average")].config(text=str(round(average)))


    def sp_close(self):
        if self.closing:
            return

        self.closing = True
        self.exit_button.config(state=tk.DISABLED)
        if self.mqtt_connected:
            self.mqtt_client.unsubscribe(self.topic)
            self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()
        self.root.destroy()


    def sp_run(self):
        self.sp_update_table()
        self.root.mainloop()
