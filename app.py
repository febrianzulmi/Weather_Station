import joblib
import paho.mqtt.client as mqtt
import json
import time
from flask import Flask,  render_template,jsonify
from threading import Thread

# Load the model as a list
model_data = joblib.load('model_rf_new.pkl')
model = model_data[1]

# MQTT setup
mqtt_broker_address = "159.223.61.133"
mqtt_broker_port = 1883
mqtt_topic_sensor = "sensor/all"
mqtt_topic_prediction = "prediction_result"
mqtt_username = "mecharoot"
mqtt_password = "mecharnd595"

sensor_data = {"temperature": 0, "humidity": 0, "wind_speed": 0, "pressure": 0}
new_data_received = False
last_prediction_result = {'prediction': 'Tidak Diketahui'}

# Flask setup
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['GET'])
def get_prediction():
    return jsonify(last_prediction_result)

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    # Subscribe to sensor data topic
    client.subscribe(mqtt_topic_sensor)

def on_message(client, userdata, msg):
    global sensor_data, new_data_received
    try:
        payload = json.loads(msg.payload.decode())
        sensor_data = {
            "temperature": float(payload.get('temperature', 0)) if payload.get('temperature') is not None else 0,
            "wind_speed": float(payload.get('wind_speed', 0)) if payload.get('wind_speed') is not None else 0,
            "pressure": float(payload.get('pressure', 0)) if payload.get('pressure') is not None else 0,
            "humidity": float(payload.get('humidity', 0)) if payload.get('humidity') is not None else 0
        }
        new_data_received = True
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# Set up MQTT client with username and password
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(mqtt_username, mqtt_password)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker_address, mqtt_broker_port, 60)
mqtt_client.loop_start()

def send_prediction_to_mqtt():
    global new_data_received, last_prediction_result
    while True:
        try:
            # Wait for new sensor data
            while not new_data_received:
                time.sleep(1)

            # Using the latest sensor data
            temperature = sensor_data.get('temperature', 0)
            humidity = sensor_data.get('humidity', 0)
            wind_speed = sensor_data.get('wind_speed', 0)
            pressure = sensor_data.get('pressure', 0)

            # Making a prediction using the model
            prediction = model.predict([[temperature, humidity, wind_speed, pressure]])

            # Converting the prediction to text weather
            weather_codes = {0: 'Cerah', 1: 'Berawan', 2: 'Gerimis', 3: 'Hujan Lebat'}
            predicted_weather = weather_codes.get(prediction[0], 'Tidak Diketahui')

            # Update the last prediction result
            last_prediction_result = {'prediction': predicted_weather}

            # Sending the prediction to MQTT topic in JSON format
            mqtt_client.publish(mqtt_topic_prediction, json.dumps(last_prediction_result))
            print("Prediction sent to MQTT")

            # Resetting the flag
            new_data_received = False

        except Exception as e:
            print(f"Error sending prediction to MQTT: {e}")

if __name__ == '__main__':
    # Start Flask web server in a separate thread
    flask_thread = Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8080})
    flask_thread.start()

    # Start sending predictions to MQTT in a separate thread
    prediction_thread = Thread(target=send_prediction_to_mqtt)
    prediction_thread.start()
