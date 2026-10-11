package com.example.moniteur.data

import android.util.Log
import com.hivemq.client.mqtt.MqttGlobalPublishFilter
import com.hivemq.client.mqtt.datatypes.MqttQos
import com.hivemq.client.mqtt.mqtt3.Mqtt3AsyncClient
import com.hivemq.client.mqtt.mqtt3.Mqtt3Client
import com.hivemq.client.mqtt.mqtt3.message.publish.Mqtt3Publish
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.time.Instant
import java.util.UUID

/** Broker EMQX : mêmes valeurs que IOT/src/config.h (l'ESP32 publie, l'app s'abonne). */
object MqttConfig {
    const val BROKER = "h1211a42.ala.eu-central-1.emqxsl.com"
    const val PORT = 8883
    const val USER = "HackcureUser"
    const val PASS = "Hackcure"
    const val TOPIC = "Hackcure/data"
}

enum class MqttState { DISCONNECTED, CONNECTING, CONNECTED }

/**
 * Abonné MQTT (TLS 8883) au topic de l'ESP32 : fournit les mesures en temps réel (~1 s) sans passer par l'API.
 * L'API stocke de son côté les mêmes messages (MqttBridgeService) pour l'historique.
 */
class MqttLive(private val scope: CoroutineScope) {
    private val _state = MutableStateFlow(MqttState.DISCONNECTED)
    val state: StateFlow<MqttState> = _state

    /** Dernier message reçu, tous boîtiers confondus (l'appelant filtre sur deviceId). */
    private val _last = MutableStateFlow<Telemetry?>(null)
    val last: StateFlow<Telemetry?> = _last

    private var client: Mqtt3AsyncClient? = null
    private var job: Job? = null

    fun start() {
        if (job?.isActive == true) return
        job = scope.launch(Dispatchers.IO) {
            val c = Mqtt3Client.builder()
                .identifier("moniteur-android-" + UUID.randomUUID().toString().take(8))
                .serverHost(MqttConfig.BROKER)
                .serverPort(MqttConfig.PORT)
                .sslWithDefaultConfig()
                .simpleAuth().username(MqttConfig.USER).password(MqttConfig.PASS.toByteArray()).applySimpleAuth()
                .addDisconnectedListener { _state.value = MqttState.DISCONNECTED }
                .buildAsync()
            client = c
            c.publishes(MqttGlobalPublishFilter.ALL) { publish: Mqtt3Publish ->
                parse(String(publish.payloadAsBytes))?.let { Log.d(TAG, "message ${it.deviceId} bpm=${it.bpm} spo2=${it.spo2}"); _last.value = it }
            }
            while (isActive) {
                if (c.state.isConnected) {
                    _state.value = MqttState.CONNECTED
                } else {
                    _state.value = MqttState.CONNECTING
                    try {
                        c.connectWith().keepAlive(30).cleanSession(true).send().get()
                        c.subscribeWith().topicFilter(MqttConfig.TOPIC).qos(MqttQos.AT_MOST_ONCE).send().get()
                        _state.value = MqttState.CONNECTED
                        Log.i(TAG, "connecté à ${MqttConfig.BROKER}, topic ${MqttConfig.TOPIC}")
                    } catch (e: Exception) {
                        _state.value = MqttState.DISCONNECTED
                        Log.w(TAG, "connexion MQTT impossible : ${e.message}", e)
                    }
                }
                delay(5000)
            }
        }
    }

    fun stop() {
        job?.cancel()
        job = null
        runCatching { client?.disconnect() }
        client = null
        _state.value = MqttState.DISCONNECTED
    }

    companion object {
        private const val TAG = "MqttLive"

        /** Message ESP32 {device_id,temp,hum,bpm,spo2,activity,motion} -> mesure. Les `null` JSON restent null. */
        fun parse(json: String): Telemetry? = try {
            val o = JSONObject(json)
            fun num(k: String): Double? = if (!o.has(k) || o.isNull(k)) null else o.optDouble(k).takeIf { !it.isNaN() }
            val activity = num("activity")
            val motion = when {
                activity != null -> if (activity >= 1.5) "AGITE" else if (activity >= 0.3) "LEGER" else "IMMOBILE"
                else -> if (o.has("motion")) o.optString("motion").uppercase().replace(' ', '_') else null
            }
            Telemetry(
                timestamp = Instant.now().toString(),
                deviceId = if (o.has("device_id") && !o.isNull("device_id")) o.getString("device_id") else null,
                bpm = num("bpm")?.toInt(),
                spo2 = num("spo2"),
                roomTemp = num("temp"),
                roomHumidity = num("hum"),
                motionState = motion,
                fallDetected = o.optBoolean("fall_detected", false),
                live = true,
            )
        } catch (e: Exception) {
            null
        }
    }
}
