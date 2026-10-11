package com.example.moniteur.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant

/** Point de graphique (moyenne sur un intervalle) renvoyé par /telemetry/history. */
data class HistoryPoint(val timestamp: String, val bpm: Double?, val spo2: Double?, val roomTemp: Double?, val roomHumidity: Double?)

/**
 * Client REST de l'API .NET (Backend/API). Pas de librairie externe : HttpURLConnection + org.json.
 * Les erreurs réseau remontent en ApiError(status = 0).
 */
class Api(
    private val baseUrl: String,
    private val token: String? = null,
    private val onUnauthorized: (() -> Unit)? = null,
) {
    private suspend fun request(path: String, method: String = "GET", body: JSONObject? = null, timeoutMs: Int = 15000): String? =
        withContext(Dispatchers.IO) {
            val conn = try {
                URL(baseUrl.trim().trimEnd('/') + path).openConnection() as HttpURLConnection
            } catch (e: Exception) {
                throw ApiError("network", 0)
            }
            try {
                conn.requestMethod = method
                conn.connectTimeout = timeoutMs
                conn.readTimeout = timeoutMs
                conn.setRequestProperty("Accept", "application/json")
                // Sans cet en-tête, un tunnel ngrok gratuit peut répondre par une page HTML d'avertissement
                conn.setRequestProperty("ngrok-skip-browser-warning", "true")
                if (token != null) conn.setRequestProperty("Authorization", "Bearer $token")
                if (body != null) {
                    conn.doOutput = true
                    conn.setRequestProperty("Content-Type", "application/json")
                    conn.outputStream.use { it.write(body.toString().toByteArray()) }
                }
                val code = conn.responseCode
                val text = (if (code in 200..299) conn.inputStream else conn.errorStream)?.bufferedReader()?.use { it.readText() }
                if (code == 401 && token != null) onUnauthorized?.invoke()
                if (code !in 200..299) throw ApiError(errorMessage(text, code), code)
                if (code == 204) null else text
            } catch (e: ApiError) {
                throw e
            } catch (e: Exception) {
                throw ApiError("network", 0)
            } finally {
                conn.disconnect()
            }
        }

    private fun errorMessage(text: String?, code: Int): String = runCatching {
        val o = JSONObject(text ?: "")
        // Erreurs de validation ASP.NET : { errors: { champ: ["message"] } }
        val errors = o.optJSONObject("errors")
        val first = errors?.keys()?.asSequence()?.firstNotNullOfOrNull { errors.optJSONArray(it)?.optString(0) }
        first ?: o.optString("title").ifBlank { "HTTP $code" }
    }.getOrDefault("HTTP $code")

    private fun authResponse(text: String?): Session {
        val o = JSONObject(text!!)
        return Session(
            token = o.getString("access_token"), expiresAt = o.getString("expires_at"),
            user = parseUser(o.getJSONObject("user")),
            profileId = if (o.isNull("profile_id")) null else o.getString("profile_id"),
        )
    }

    suspend fun login(email: String, password: String): Session =
        authResponse(request("/api/auth/login", "POST", JSONObject().put("email", email).put("password", password)))

    suspend fun register(
        email: String, password: String, role: String, firstName: String, lastName: String, phone: String?, deviceId: String?,
    ): Session = authResponse(
        request(
            "/api/auth/register", "POST",
            JSONObject().put("email", email).put("password", password).put("role", role)
                .put("first_name", firstName).put("last_name", lastName)
                .apply { phone?.let { put("phone", it) }; deviceId?.let { put("device_id", it) } },
        ),
    )

    suspend fun me(): PatientProfile = parseProfile(JSONObject(request("/api/patients/me")!!))

    /** Associe le boîtier ESP32 au patient (204). 409 si déjà pris par un autre patient. */
    suspend fun setDevice(deviceId: String) {
        request("/api/patients/me/device", "PUT", JSONObject().put("device_id", deviceId))
    }

    suspend fun latestTelemetry(patientId: String): Telemetry? =
        request("/api/patients/$patientId/telemetry/latest")?.takeIf { it.isNotBlank() && it != "null" }
            ?.let { parseTelemetry(JSONObject(it)) }

    /** Moyennes par tranche de [intervalMinutes] sur les dernières [hours] heures (pour les graphiques). */
    suspend fun history(patientId: String, hours: Int, intervalMinutes: Int): List<HistoryPoint> {
        val to = Instant.now()
        val from = to.minusSeconds(hours * 3600L)
        val text = request("/api/patients/$patientId/telemetry/history?from=$from&to=$to&interval_minutes=$intervalMinutes") ?: return emptyList()
        val pts = JSONObject(text).optJSONArray("points") ?: return emptyList()
        return pts.mapObjects { o ->
            fun d(k: String) = if (!o.has(k) || o.isNull(k)) null else o.getDouble(k)
            HistoryPoint(o.getString("timestamp"), d("bpm"), d("spo2"), d("room_temp"), d("room_humidity"))
        }
    }

    /** Prises planifiées de [days] jours à partir de [date] (jour local), statut calculé à l'heure locale [asOf]. */
    suspend fun schedule(patientId: String, date: String, days: Int, asOf: String): List<Dose> =
        JSONArray(request("/api/patients/$patientId/medications/schedule?date=$date&days=$days&as_of=$asOf")!!)
            .let { arr -> (0 until arr.length()).map { parseDose(arr.getJSONObject(it)) } }

    /** Le patient répond pour une prise : TAKEN, SKIPPED, ou null pour annuler. */
    suspend fun recordIntake(patientId: String, medicationId: String, date: String, time: String, status: String?) {
        request(
            "/api/patients/$patientId/medications/$medicationId/intakes", "PUT",
            JSONObject().put("date", date).put("time", time).apply { if (status != null) put("status", status) },
        )
    }

    /** Avancement des prises sur [from]..[to] (jours locaux) : totaux. */
    suspend fun adherence(patientId: String, from: String, to: String, asOf: String): AdherenceCounts =
        parseCounts(JSONObject(request("/api/patients/$patientId/medications/adherence?from=$from&to=$to&as_of=$asOf")!!).getJSONObject("overall"))

    suspend fun alerts(patientId: String, limit: Int = 30): List<Alert> =
        JSONArray(request("/api/patients/$patientId/alerts?limit=$limit")!!).let { arr -> (0 until arr.length()).map { parseAlert(arr.getJSONObject(it)) } }

    suspend fun linkPatient(code: String, relationship: String, whatsappOptIn: Boolean): FollowedPatient =
        parseFollowed(
            JSONObject(
                request(
                    "/api/family/link-patient", "POST",
                    JSONObject().put("link_code", code).put("relationship", relationship)
                        .put("whatsapp_opt_in", whatsappOptIn).put("is_primary_contact", false),
                )!!,
            ),
        )

    suspend fun followedPatients(): List<FollowedPatient> =
        JSONArray(request("/api/family/patients")!!).let { arr -> (0 until arr.length()).map { parseFollowed(arr.getJSONObject(it)) } }

    /** Assistant de convalescence, relayé par l'API vers FastAPI/Mistral. */
    suspend fun chat(messages: List<ChatMessage>, lang: String): ChatReply {
        val arr = JSONArray().also { a -> messages.forEach { a.put(JSONObject().put("role", it.role).put("content", it.content)) } }
        val o = JSONObject(request("/chat", "POST", JSONObject().put("messages", arr).put("lang", lang), 30000)!!)
        return ChatReply(o.optString("reply"), o.optBoolean("escalate"))
    }
}
