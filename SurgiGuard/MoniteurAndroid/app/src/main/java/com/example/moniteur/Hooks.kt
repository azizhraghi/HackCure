package com.example.moniteur

import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import com.example.moniteur.data.Alert
import com.example.moniteur.data.ApiError
import com.example.moniteur.data.FollowedPatient
import com.example.moniteur.data.MqttState
import com.example.moniteur.data.PatientProfile
import com.example.moniteur.data.Telemetry
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay

class Poll<T>(val data: T?, val error: ApiError?, val loading: Boolean, val refresh: () -> Unit)

/** Charge une fois puis toutes les [intervalMs] ms tant que l'app est au premier plan (0 = une fois). */
@Composable
fun <T> usePolling(key: Any?, intervalMs: Long, enabled: Boolean = true, fetch: suspend () -> T): Poll<T> {
    var data by remember(key) { mutableStateOf<T?>(null) }
    var error by remember(key) { mutableStateOf<ApiError?>(null) }
    var loading by remember(key) { mutableStateOf(enabled) }
    var tick by remember(key) { mutableIntStateOf(0) }
    val fetcher by rememberUpdatedState(fetch)
    val lifecycle = LocalLifecycleOwner.current.lifecycle

    LaunchedEffect(key, enabled, intervalMs, tick) {
        if (!enabled) return@LaunchedEffect
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            while (true) {
                try {
                    data = fetcher()
                    error = null
                } catch (e: CancellationException) {
                    throw e
                } catch (e: ApiError) {
                    error = e
                } catch (e: Exception) {
                    error = ApiError(e.message ?: "", 0)
                }
                loading = false
                if (intervalMs <= 0) break
                delay(intervalMs)
            }
        }
    }
    return Poll(data, error, loading) { tick++ }
}

@Composable
private fun sessionKey(app: AppViewModel) = app.apiUrl to app.session?.token

@Composable
fun useMyProfile(): Poll<PatientProfile> {
    val app = LocalApp.current
    return usePolling(sessionKey(app), 30000, enabled = app.signedIn) { app.api.me() }
}

/** Côté famille : premier patient suivi par le proche connecté. */
@Composable
fun useFollowedPatient(): Pair<Poll<List<FollowedPatient>>, FollowedPatient?> {
    val app = LocalApp.current
    val poll = usePolling(sessionKey(app), 30000, enabled = app.signedIn) { app.api.followedPatients() }
    return poll to poll.data?.firstOrNull()
}

@Composable
fun useAlerts(patientId: String?, intervalMs: Long = 10000): Poll<List<Alert>> {
    val app = LocalApp.current
    return usePolling(Triple(sessionKey(app), patientId, 1), intervalMs, enabled = patientId != null) { app.api.alerts(patientId!!) }
}

/** Mesure courante : MQTT (temps réel) si un message du boîtier est arrivé il y a moins de 15 s, sinon dernière mesure de l'API. */
class LiveTelemetry(val data: Telemetry?, val error: ApiError?, val loading: Boolean, val mqtt: MqttState, val viaMqtt: Boolean, val nowMs: Long)

const val MQTT_FRESH_MS = 15_000L

@Composable
fun useLiveTelemetry(patientId: String?, deviceId: String?): LiveTelemetry {
    val app = LocalApp.current
    val api = usePolling(Triple(sessionKey(app), patientId, 2), 2000, enabled = patientId != null) { app.api.latestTelemetry(patientId!!) }
    val mqttLast by app.mqtt.last.collectAsState()
    val mqttState by app.mqtt.state.collectAsState()
    val now by produceState(System.currentTimeMillis()) { while (true) { delay(1000); value = System.currentTimeMillis() } }

    val m = mqttLast
    val fresh = m != null && deviceId != null && m.deviceId == deviceId && now - m.epochMs < MQTT_FRESH_MS
    val data = if (fresh) m else api.data
    return LiveTelemetry(data, if (fresh) null else api.error, api.loading && data == null, mqttState, fresh, now)
}
