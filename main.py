from flask import Flask, jsonify
import joblib
import paho.mqtt.client as mqtt
import json

app = Flask(__name__)
model = joblib.load('model_rf_new.pkl')  # Ganti dengan nama file model Anda

# MQTT setup
mqtt_broker_address = "159.223.61.133"
mqtt_broker_port = 1883
mqtt_topic = "sensors/all"  # Ganti dengan topik MQTT yang sesuai
mqtt_username = "mecharoot"  # Ganti dengan username MQTT Anda
mqtt_password = "mecharnd595"  # Ganti dengan password MQTT Anda

sensor_data = {"wind_speed": 0, "temperature": 0, "pressure": 0, "humidity": 0}


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code "+str(rc))
    client.subscribe(mqtt_topic)


def on_message(client, userdata, msg):
    global sensor_data
    try:
        payload = json.loads(msg.payload.decode())
        sensor_data = {
            "wind_speed": float(payload.get('wind_speed', 0)) if payload.get('wind_speed') is not None else 0,
            "temperature": float(payload.get('temperature', 0)) if payload.get('temperature') is not None else 0,
            "pressure": float(payload.get('pressure', 0)) if payload.get('pressure') is not None else 0,
            "humidity": float(payload.get('humidity', 0)) if payload.get('humidity') is not None else 0
        }
    except Exception as e:
        print(f"Error processing MQTT message: {e}")


# Set up MQTT client with username and password
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(mqtt_username, mqtt_password)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker_address, mqtt_broker_port, 60)
mqtt_client.loop_start()


@app.route('/predict', methods=['GET'])
def predict():
    try:
        # Menggunakan data sensor dari MQTT
        wind_speed = sensor_data.get('wind_speed', 0)
        temperature = sensor_data.get('temperature', 0)
        pressure = sensor_data.get('pressure', 0)
        humidity = sensor_data.get('humidity', 0)

        # Membuat prediksi menggunakan model
        prediction = model.predict(
            [[wind_speed, temperature, pressure, humidity]])

        # Mengonversi hasil prediksi ke dalam teks cuaca
        kodecuaca = {
            0: 'Cerah',
            1: 'Berawan',
            2: 'Gerimis',
            3: 'Hujan Lebat'
        }
        prediksi_cuaca = kodecuaca.get(prediction[0], 'Tidak Diketahui')

        # Mengirim hasil prediksi ke MQTT topic dalam format JSON
        result_message = {
            'prediction': prediksi_cuaca
        }
        mqtt_client.publish("prediction_result", json.dumps(result_message))

        # Mengembalikan prediksi sebagai JSON
        return jsonify({'prediction': prediksi_cuaca})
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True)
