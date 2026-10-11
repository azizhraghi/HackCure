package com.example.moniteur.alarm

import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import com.example.moniteur.I18n
import com.example.moniteur.MainActivity
import com.example.moniteur.R
import com.example.moniteur.data.Api
import com.example.moniteur.data.Dose
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** Heure locale du téléphone au format attendu par l'API (as_of). */
fun localAsOf(): String = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm"))

/** Session lue directement dans les préférences : les récepteurs d'alarme tournent sans l'interface. */
private class Stored(ctx: Context) {
    private val prefs = ctx.getSharedPreferences("sg.appState.v1", Context.MODE_PRIVATE)
    val apiUrl: String = prefs.getString("apiUrl", null) ?: ""
    val lang: String = prefs.getString("lang", null) ?: "fr"
    val token: String?
    val patientId: String?

    init {
        val o = prefs.getString("session", null)?.let { runCatching { JSONObject(it) }.getOrNull() }
        val isPatient = o?.optJSONObject("user")?.optString("role") == "PATIENT"
        token = if (isPatient) o?.optString("token") else null
        patientId = if (isPatient && o != null && !o.isNull("profileId")) o.getString("profileId") else null
    }
}

/**
 * Alarmes de prise de médicaments.
 *
 * - Le planning des 3 prochains jours (prescrit par le médecin, renvoyé par l'API) est mis en cache puis programmé avec
 *   AlarmManager (exact, même téléphone en veille).
 * - À l'heure de la prise : notification d'alarme (son d'alarme + vibration, répétés jusqu'à ce que le patient réagisse)
 *   avec les actions « Pris » / « Ignorer » qui répondent à l'API sans ouvrir l'app.
 * - Chaque alarme, un redémarrage du téléphone et un rappel toutes les 30 min resynchronisent le planning
 *   (nouveaux médicaments du médecin, prises déjà validées).
 */
object MedAlarms {
    const val CHANNEL = "med_alarm_v1"
    const val ACTION_ALARM = "com.example.moniteur.DOSE_ALARM"
    const val ACTION_TAKEN = "com.example.moniteur.DOSE_TAKEN"
    const val ACTION_SKIP = "com.example.moniteur.DOSE_SKIP"
    const val ACTION_SYNC = "com.example.moniteur.DOSE_SYNC"
    const val EXTRA_OPEN_MEDS = "open_meds"
    const val SYNC_DAYS = 3

    private const val PREFS = "sg.medAlarms.v1"

    fun ensureChannel(ctx: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = ctx.getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL) != null) return
        val channel = NotificationChannel(CHANNEL, I18n(ctx).t(Stored(ctx).lang, "med.channel"), NotificationManager.IMPORTANCE_HIGH).apply {
            description = I18n(ctx).t(Stored(ctx).lang, "med.channelDesc")
            setSound(
                RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM),
                AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build(),
            )
            enableVibration(true)
            vibrationPattern = longArrayOf(0, 600, 300, 600, 300, 600)
            lockscreenVisibility = Notification.VISIBILITY_PUBLIC
        }
        nm.createNotificationChannel(channel)
    }

    // ---------- Cache du planning ----------

    private fun prefs(ctx: Context) = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun save(ctx: Context, doses: List<Dose>) {
        val arr = JSONArray()
        doses.forEach { d ->
            arr.put(JSONObject().put("m", d.medicationId).put("n", d.name).put("g", d.dosage).put("i", d.instructions).put("d", d.date).put("t", d.time).put("s", d.status))
        }
        prefs(ctx).edit().putString("doses", arr.toString()).apply()
    }

    fun load(ctx: Context): List<Dose> {
        val raw = prefs(ctx).getString("doses", null) ?: return emptyList()
        return runCatching {
            val arr = JSONArray(raw)
            (0 until arr.length()).map {
                val o = arr.getJSONObject(it)
                Dose(o.getString("m"), o.getString("n"), if (o.isNull("g")) null else o.getString("g"), if (o.isNull("i")) null else o.getString("i"), o.getString("d"), o.getString("t"), o.getString("s"))
            }
        }.getOrDefault(emptyList())
    }

    /** Enregistre localement la réponse du patient (annule l'alarme de cette prise). */
    fun markLocal(ctx: Context, medicationId: String, date: String, time: String, status: String) {
        val updated = load(ctx).map { if (it.medicationId == medicationId && it.date == date && it.time == time) it.copy(status = status) else it }
        save(ctx, updated)
        scheduleAll(ctx)
    }

    /** Vide le cache et annule toutes les alarmes (déconnexion). */
    fun clear(ctx: Context) {
        cancelAll(ctx)
        prefs(ctx).edit().clear().apply()
        cancelSync(ctx)
    }

    // ---------- Programmation ----------

    private fun alarmManager(ctx: Context) = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager

    private fun dosePendingIntent(ctx: Context, d: Dose, flags: Int = PendingIntent.FLAG_UPDATE_CURRENT): PendingIntent? {
        val intent = Intent(ctx, MedAlarmReceiver::class.java).setAction(ACTION_ALARM)
            .setData(Uri.parse("sg://dose/${d.medicationId}/${d.date}/${d.time}"))
            .putExtra("m", d.medicationId).putExtra("n", d.name).putExtra("g", d.dosage).putExtra("i", d.instructions)
            .putExtra("d", d.date).putExtra("t", d.time)
        return PendingIntent.getBroadcast(ctx, 0, intent, flags or PendingIntent.FLAG_IMMUTABLE)
    }

    private fun epochOf(d: Dose): Long {
        val dt = LocalDateTime.of(LocalDate.parse(d.date), java.time.LocalTime.parse(d.time))
        return dt.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()
    }

    private fun cancelAll(ctx: Context) {
        val am = alarmManager(ctx)
        prefs(ctx).getStringSet("scheduled", emptySet())!!.forEach { key ->
            val p = key.split("|")
            if (p.size == 3) dosePendingIntent(ctx, Dose(p[0], "", null, null, p[1], p[2], "PENDING"), PendingIntent.FLAG_NO_CREATE)?.let { am.cancel(it); it.cancel() }
        }
        prefs(ctx).edit().remove("scheduled").apply()
    }

    /** (Re)programme une alarme par prise future non encore validée. */
    fun scheduleAll(ctx: Context) {
        cancelAll(ctx)
        val am = alarmManager(ctx)
        val now = System.currentTimeMillis()
        val keys = mutableSetOf<String>()
        val exact = Build.VERSION.SDK_INT < Build.VERSION_CODES.S || am.canScheduleExactAlarms()
        load(ctx).filter { it.status == "PENDING" && epochOf(it) > now }.forEach { d ->
            val pi = dosePendingIntent(ctx, d) ?: return@forEach
            val at = epochOf(d)
            if (exact) am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi) else am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi)
            keys.add(d.key)
        }
        prefs(ctx).edit().putStringSet("scheduled", keys).apply()
    }

    private fun syncPendingIntent(ctx: Context, flags: Int = PendingIntent.FLAG_UPDATE_CURRENT): PendingIntent? =
        PendingIntent.getBroadcast(ctx, 1, Intent(ctx, MedAlarmReceiver::class.java).setAction(ACTION_SYNC), flags or PendingIntent.FLAG_IMMUTABLE)

    /** Rappel de resynchronisation toutes les 30 min (nouveaux médicaments prescrits par le médecin). */
    fun scheduleSync(ctx: Context) {
        val pi = syncPendingIntent(ctx) ?: return
        alarmManager(ctx).setInexactRepeating(AlarmManager.RTC_WAKEUP, System.currentTimeMillis() + AlarmManager.INTERVAL_HALF_HOUR, AlarmManager.INTERVAL_HALF_HOUR, pi)
    }

    private fun cancelSync(ctx: Context) {
        syncPendingIntent(ctx, PendingIntent.FLAG_NO_CREATE)?.let { alarmManager(ctx).cancel(it); it.cancel() }
    }

    // ---------- Synchronisation avec l'API ----------

    /** Remplace le cache par le planning de l'API et reprogramme les alarmes. À appeler hors du thread principal. */
    suspend fun applySchedule(ctx: Context, doses: List<Dose>) {
        save(ctx, doses)
        scheduleAll(ctx)
        scheduleSync(ctx)
    }

    /** Resynchronise depuis l'API avec la session enregistrée ; sans réseau, on garde le cache existant. */
    fun syncBlocking(ctx: Context): Boolean {
        val s = Stored(ctx)
        val token = s.token ?: return false
        val pid = s.patientId ?: return false
        return runCatching {
            val doses = runBlocking { Api(s.apiUrl, token).schedule(pid, LocalDate.now().toString(), SYNC_DAYS, localAsOf()) }
            save(ctx, doses)
            true
        }.getOrDefault(false).also { scheduleAll(ctx) }
    }

    /** Envoie la réponse du patient depuis la notification. */
    fun recordBlocking(ctx: Context, medicationId: String, date: String, time: String, status: String): Boolean {
        val s = Stored(ctx)
        val token = s.token ?: return false
        val pid = s.patientId ?: return false
        val ok = runCatching { runBlocking { Api(s.apiUrl, token).recordIntake(pid, medicationId, date, time, status) } }.isSuccess
        // Même hors ligne, on arrête l'alarme localement : le patient a répondu
        markLocal(ctx, medicationId, date, time, status)
        return ok
    }

    // ---------- Notification ----------

    fun notificationId(d: Dose) = d.key.hashCode()

    fun showAlarm(ctx: Context, d: Dose) {
        ensureChannel(ctx)
        val lang = Stored(ctx).lang
        val i18n = I18n(ctx)
        val detail = listOfNotNull(d.dosage?.takeIf { it.isNotBlank() }, d.time).joinToString(" · ")
        val open = PendingIntent.getActivity(
            ctx, notificationId(d), Intent(ctx, MainActivity::class.java).putExtra(EXTRA_OPEN_MEDS, true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        fun action(act: String, label: String): NotificationCompat.Action {
            val intent = Intent(ctx, MedActionReceiver::class.java).setAction(act).setData(Uri.parse("sg://dose/${d.medicationId}/${d.date}/${d.time}/$act"))
                .putExtra("m", d.medicationId).putExtra("d", d.date).putExtra("t", d.time).putExtra("nid", notificationId(d))
            val pi = PendingIntent.getBroadcast(ctx, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            return NotificationCompat.Action.Builder(0, label, pi).build()
        }
        val n = NotificationCompat.Builder(ctx, CHANNEL)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(i18n.t(lang, "med.alarmTitle", "name" to d.name))
            .setContentText(detail)
            .setStyle(NotificationCompat.BigTextStyle().bigText(listOfNotNull(detail, d.instructions?.takeIf { it.isNotBlank() }).joinToString("\n")))
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM), android.media.AudioManager.STREAM_ALARM)
            .setVibrate(longArrayOf(0, 600, 300, 600, 300, 600))
            .setContentIntent(open)
            .setOngoing(true)
            .setAutoCancel(true)
            .addAction(action(ACTION_TAKEN, i18n.t(lang, "med.actionTaken")))
            .addAction(action(ACTION_SKIP, i18n.t(lang, "med.actionSkip")))
            .build()
        // Son et vibration répétés jusqu'à ce que le patient réagisse
        n.flags = n.flags or Notification.FLAG_INSISTENT
        runCatching { ctx.getSystemService(NotificationManager::class.java).notify(notificationId(d), n) }
    }
}

/** Reçoit l'heure d'une prise (alarme), le rappel de synchronisation et le redémarrage du téléphone. */
class MedAlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val pending = goAsync()
        Thread {
            try {
                when (intent.action) {
                    MedAlarms.ACTION_ALARM -> {
                        val d = Dose(
                            intent.getStringExtra("m") ?: return@Thread, intent.getStringExtra("n") ?: "", intent.getStringExtra("g"), intent.getStringExtra("i"),
                            intent.getStringExtra("d") ?: return@Thread, intent.getStringExtra("t") ?: return@Thread, "PENDING",
                        )
                        // Alerte d'abord : le réseau peut être lent ou absent
                        if (MedAlarms.load(context).firstOrNull { it.key == d.key }?.status.let { it == null || it == "PENDING" }) MedAlarms.showAlarm(context, d)
                        MedAlarms.syncBlocking(context)
                    }
                    else -> { // ACTION_SYNC, BOOT_COMPLETED, MY_PACKAGE_REPLACED
                        MedAlarms.syncBlocking(context)
                        MedAlarms.scheduleSync(context)
                    }
                }
            } finally {
                pending.finish()
            }
        }.start()
    }
}

/** Boutons « Pris » / « Ignorer » de la notification. */
class MedActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val m = intent.getStringExtra("m") ?: return
        val d = intent.getStringExtra("d") ?: return
        val t = intent.getStringExtra("t") ?: return
        val status = if (intent.action == MedAlarms.ACTION_TAKEN) "TAKEN" else "SKIPPED"
        context.getSystemService(NotificationManager::class.java).cancel(intent.getIntExtra("nid", 0))
        val pending = goAsync()
        Thread {
            try {
                MedAlarms.recordBlocking(context, m, d, t, status)
            } finally {
                pending.finish()
            }
        }.start()
    }
}
