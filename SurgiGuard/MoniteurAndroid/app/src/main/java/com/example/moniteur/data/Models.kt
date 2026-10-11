package com.example.moniteur.data

import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

/** Modèles de l'API (JSON snake_case). */

data class User(
    val id: String,
    val email: String,
    val role: String,
    val firstName: String,
    val lastName: String,
    val phone: String?,
    val whatsappNumber: String?,
) {
    val fullName get() = "$firstName $lastName".trim()
}

data class Session(val token: String, val expiresAt: String, val user: User, val profileId: String?) {
    fun isExpired() = runCatching { Instant.parse(expiresAt).toEpochMilli() <= System.currentTimeMillis() }.getOrDefault(false)
}

data class Telemetry(
    val timestamp: String,
    val deviceId: String?,
    val bpm: Int?,
    val spo2: Double?,
    val roomTemp: Double?,
    val roomHumidity: Double?,
    val motionState: String?,
    val fallDetected: Boolean,
    /** true si la mesure vient directement du broker MQTT (temps réel), false si elle vient de l'API. */
    val live: Boolean = false,
) {
    val epochMs: Long get() = runCatching { Instant.parse(timestamp).toEpochMilli() }.getOrDefault(0L)
}

data class LinkedFamilyMember(
    val familyMemberId: String,
    val fullName: String,
    val phone: String?,
    val relationship: String,
    val isPrimaryContact: Boolean,
    val whatsappOptIn: Boolean,
)

data class PatientProfile(
    val id: String,
    val user: User,
    val deviceId: String?,
    val linkCode: String,
    val familyMembers: List<LinkedFamilyMember>,
)

data class FollowedPatient(
    val patientId: String,
    val fullName: String,
    val deviceId: String?,
    val relationship: String,
    val isPrimaryContact: Boolean,
    val whatsappOptIn: Boolean,
    val latestTelemetry: Telemetry?,
)

data class Alert(
    val id: String,
    val patientId: String,
    val type: String,
    val severity: Int,
    val message: String,
    val status: String,
    val createdAt: String,
) {
    val epochMs: Long get() = runCatching { Instant.parse(createdAt).toEpochMilli() }.getOrDefault(0L)
}

/** Prise planifiée : médicament + jour local + heure + statut (PENDING / TAKEN / SKIPPED / MISSED). */
data class Dose(
    val medicationId: String,
    val name: String,
    val dosage: String?,
    val instructions: String?,
    val date: String,
    val time: String,
    val status: String,
) {
    val key get() = "$medicationId|$date|$time"
}

data class AdherenceCounts(val scheduled: Int, val taken: Int, val skipped: Int, val missed: Int, val pending: Int, val percent: Double?)

fun parseDose(o: JSONObject) = Dose(
    o.getString("medication_id"), o.getString("name"), o.str("dosage"), o.str("instructions"),
    o.getString("date"), o.getString("time"), o.getString("status"),
)

fun parseCounts(o: JSONObject) = AdherenceCounts(
    o.getInt("scheduled"), o.getInt("taken"), o.getInt("skipped"), o.getInt("missed"), o.getInt("pending"), o.dbl("adherence_percent"),
)

data class ChatMessage(val role: String, val content: String)
data class ChatReply(val reply: String, val escalate: Boolean)

/** status 0 = serveur injoignable (réseau, tunnel, timeout). */
class ApiError(message: String, val status: Int) : Exception(message)

// ---------- Parsing ----------

private fun JSONObject.str(key: String): String? = if (!has(key) || isNull(key)) null else getString(key)
private fun JSONObject.dbl(key: String): Double? = if (!has(key) || isNull(key)) null else getDouble(key)
private fun JSONObject.int(key: String): Int? = if (!has(key) || isNull(key)) null else getDouble(key).toInt()

fun parseUser(o: JSONObject) = User(
    id = o.getString("id"), email = o.getString("email"), role = o.getString("role"),
    firstName = o.optString("first_name"), lastName = o.optString("last_name"),
    phone = o.str("phone"), whatsappNumber = o.str("whatsapp_number"),
)

fun parseTelemetry(o: JSONObject) = Telemetry(
    timestamp = o.getString("timestamp"), deviceId = o.str("device_id"), bpm = o.int("bpm"), spo2 = o.dbl("spo2"),
    roomTemp = o.dbl("room_temp"), roomHumidity = o.dbl("room_humidity"), motionState = o.str("motion_state"),
    fallDetected = o.optBoolean("fall_detected", false),
)

fun parseProfile(o: JSONObject) = PatientProfile(
    id = o.getString("id"), user = parseUser(o.getJSONObject("user")), deviceId = o.str("device_id"),
    linkCode = o.optString("link_code"),
    familyMembers = o.optJSONArray("family_members").mapObjects {
        LinkedFamilyMember(
            it.getString("family_member_id"), it.optString("full_name"), it.str("phone"), it.optString("relationship"),
            it.optBoolean("is_primary_contact"), it.optBoolean("whatsapp_opt_in"),
        )
    },
)

fun parseFollowed(o: JSONObject) = FollowedPatient(
    patientId = o.getString("patient_id"), fullName = o.optString("full_name"), deviceId = o.str("device_id"),
    relationship = o.optString("relationship"), isPrimaryContact = o.optBoolean("is_primary_contact"),
    whatsappOptIn = o.optBoolean("whatsapp_opt_in"),
    latestTelemetry = o.optJSONObject("latest_telemetry")?.let(::parseTelemetry),
)

fun parseAlert(o: JSONObject) = Alert(
    id = o.getString("id"), patientId = o.getString("patient_id"), type = o.getString("type"),
    severity = o.getInt("severity"), message = o.optString("message"), status = o.optString("status"),
    createdAt = o.getString("created_at"),
)

inline fun <T> JSONArray?.mapObjects(f: (JSONObject) -> T): List<T> {
    if (this == null) return emptyList()
    return (0 until length()).map { f(getJSONObject(it)) }
}

fun initials(name: String): String =
    name.split(Regex("\\s+")).filter { it.isNotBlank() }.take(2).joinToString("") { it.first().uppercase() }
