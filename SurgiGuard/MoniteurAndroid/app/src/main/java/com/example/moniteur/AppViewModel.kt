package com.example.moniteur

import android.app.Application
import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.lifecycle.AndroidViewModel
import com.example.moniteur.data.Api
import com.example.moniteur.data.MqttLive
import com.example.moniteur.data.Session
import com.example.moniteur.data.User
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import org.json.JSONObject

/** Écrans empilés par-dessus la racine (la racine dépend de la session : rôle, connexion, onboarding). */
sealed interface Route {
    data object Auth : Route
    data object Welcome : Route
    data object Upload : Route
    data object Protocol : Route
    data object TwinDetail : Route
    data object WoundScan : Route
    data object SensingRequest : Route
    data object Escalation : Route
    data object Rehab : Route
    data object Medications : Route
    data class AIAssistant(val question: String? = null) : Route
    data object FamilyAccess : Route
    data object Consent : Route
    data object Settings : Route
    data class LockPreview(val tone: String) : Route
    data object FamilyInfo : Route
    data object FamilyAttention : Route
    data class FamilyUrgent(val title: String? = null, val message: String? = null) : Route
}

val LocalApp = staticCompositionLocalOf<AppViewModel> { error("AppViewModel manquant") }

/**
 * État global : session JWT, rôle, langue, thème, URL du serveur, navigation et flux MQTT temps réel.
 * Persisté dans SharedPreferences (équivalent de AsyncStorage dans l'app React Native).
 */
class AppViewModel(app: Application) : AndroidViewModel(app) {
    private val prefs = app.getSharedPreferences("sg.appState.v1", Context.MODE_PRIVATE)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val i18n = I18n(app)

    val mqtt = MqttLive(scope)

    var role by mutableStateOf<String?>(null); private set            // "patient" | "family"
    var apiUrl by mutableStateOf(DEFAULT_API_URL); private set
    var session by mutableStateOf<Session?>(null); private set
    var lang by mutableStateOf("fr"); private set
    var darkMode by mutableStateOf<Boolean?>(null); private set        // null = suivre le système
    var familyAck by mutableStateOf(true)

    /** Posé par un appui sur la notification d'alarme : AppRoot ouvre alors l'écran des médicaments. */
    var openMedsRequest by mutableStateOf(false)
    private var onboardedRoles by mutableStateOf(setOf<String>())

    /** Pile de navigation au-dessus de la racine. */
    val stack = mutableStateListOf<Route>()
    var patientTab by mutableStateOf(0)
    var familyTab by mutableStateOf(0)

    init {
        restore()
        if (session != null) mqtt.start()
    }

    val signedIn get() = session != null
    val onboarded get() = role != null && role in onboardedRoles

    val api: Api get() = Api(apiUrl, session?.token) { signOut() }

    fun t(key: String, vararg args: Pair<String, Any?>): String = i18n.t(lang, key, *args)
    fun list(key: String): List<String> = i18n.t(lang, key).split("|")

    // ---------- Navigation ----------

    fun push(r: Route) { stack.add(r) }
    fun pop() { if (stack.isNotEmpty()) stack.removeAt(stack.lastIndex) }
    fun replace(r: Route) { pop(); push(r) }
    fun goPatientTab(i: Int) { stack.clear(); patientTab = i }
    fun goFamilyTab(i: Int) { stack.clear(); familyTab = i }

    // ---------- Actions ----------

    fun chooseRole(r: String?) { role = r; stack.clear(); persist() }

    fun completeOnboarding() {
        val r = role ?: return
        if (r !in onboardedRoles) onboardedRoles = onboardedRoles + r
        stack.clear(); persist()
    }

    fun saveApiUrl(url: String) { apiUrl = url.trim().ifBlank { DEFAULT_API_URL }; persist() }

    fun signIn(s: Session, onboarded: Boolean) {
        val newRole = if (s.user.role == "FAMILY_MEMBER") "family" else "patient"
        session = s
        role = newRole
        onboardedRoles = if (onboarded) onboardedRoles + newRole else onboardedRoles - newRole
        stack.clear(); persist()
        mqtt.start()
    }

    /** Déconnecte et revient au choix du rôle. */
    fun signOut() {
        com.example.moniteur.alarm.MedAlarms.clear(getApplication())
        role = null; session = null
        stack.clear(); persist()
        mqtt.stop()
    }

    fun changeLang(l: String) { lang = l; persist() }
    fun setDark(d: Boolean?) { darkMode = d; persist() }

    fun vibrate(pattern: LongArray) {
        val ctx = getApplication<Application>()
        val v = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (ctx.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager).defaultVibrator
        } else {
            @Suppress("DEPRECATION") ctx.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
        v.vibrate(VibrationEffect.createWaveform(pattern, -1))
    }

    // ---------- Persistance ----------

    private fun persist() {
        val s = session
        prefs.edit()
            .putString("role", role)
            .putString("apiUrl", apiUrl)
            .putString("lang", lang)
            .putString("dark", darkMode?.toString())
            .putStringSet("onboarded", onboardedRoles)
            .putString(
                "session",
                s?.let {
                    JSONObject().put("token", it.token).put("expiresAt", it.expiresAt).put("profileId", it.profileId)
                        .put(
                            "user",
                            JSONObject().put("id", it.user.id).put("email", it.user.email).put("role", it.user.role)
                                .put("first_name", it.user.firstName).put("last_name", it.user.lastName)
                                .put("phone", it.user.phone).put("whatsapp_number", it.user.whatsappNumber),
                        ).toString()
                },
            )
            .apply()
    }

    private fun restore() {
        role = prefs.getString("role", null)
        apiUrl = prefs.getString("apiUrl", null) ?: DEFAULT_API_URL
        lang = prefs.getString("lang", null) ?: if (java.util.Locale.getDefault().language == "fr") "fr" else "en"
        darkMode = prefs.getString("dark", null)?.toBooleanStrictOrNull()
        onboardedRoles = prefs.getStringSet("onboarded", emptySet())!!.toSet()
        session = prefs.getString("session", null)?.let { raw ->
            runCatching {
                val o = JSONObject(raw)
                val u = o.getJSONObject("user")
                Session(
                    o.getString("token"), o.getString("expiresAt"),
                    User(
                        u.getString("id"), u.getString("email"), u.getString("role"), u.optString("first_name"), u.optString("last_name"),
                        if (u.isNull("phone")) null else u.getString("phone"),
                        if (u.isNull("whatsapp_number")) null else u.getString("whatsapp_number"),
                    ),
                    if (o.isNull("profileId")) null else o.getString("profileId"),
                )
            }.getOrNull()?.takeUnless { it.isExpired() }
        }
        if (session == null) role = null
    }

    override fun onCleared() {
        mqtt.stop()
        scope.cancel()
    }

    companion object {
        /**
         * URL de l'API : tunnel ngrok (change à chaque redémarrage de ngrok, voir `curl localhost:4040/api/tunnels`). Émulateur Android : http://10.0.2.2:8080 = le PC. Téléphone en USB : `adb reverse tcp:8080 tcp:8080`
         * puis http://localhost:8080 (ou l'IP du PC sur le Wi-Fi). Modifiable dans l'écran de connexion et les Réglages.
         */
        const val DEFAULT_API_URL = "https://03f9-196-176-231-29.ngrok-free.app"
    }
}
