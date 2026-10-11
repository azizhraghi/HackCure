package com.example.moniteur.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.example.moniteur.data.MqttState
import com.example.moniteur.data.Telemetry
import com.example.moniteur.ui.Card
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.T
import com.example.moniteur.ui.t
import com.example.moniteur.ui.theme.LightPalette
import com.example.moniteur.ui.theme.Pal
import com.example.moniteur.useLiveTelemetry
import java.text.DateFormat
import java.util.Date

const val STALE_AFTER_S = 120

@Composable
fun formatAgo(epochMs: Long, nowMs: Long = System.currentTimeMillis()): String {
    val s = maxOf(0L, (nowMs - epochMs) / 1000)
    return when {
        s < 60 -> t("live.secondsAgo", "n" to s)
        s < 3600 -> t("live.minutesAgo", "n" to Math.round(s / 60.0))
        else -> t("live.at", "time" to DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(epochMs)))
    }
}

fun alertIcon(type: String): IconName = when (type) {
    "FALL" -> IconName.activity
    "HYPOXIA" -> IconName.drop
    else -> IconName.heart
}

@Composable
private fun Tile(icon: IconName, label: String, value: String, unit: String, bg: Color, modifier: Modifier) {
    val ink = Color(0xFF1B2A4A)
    Column(modifier.heightIn(min = 74.dp).background(bg, RoundedCornerShape(14.dp)).border(1.dp, ink, RoundedCornerShape(14.dp)).padding(9.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, 14.dp, ink)
            T(label, size = 7f, w = 800, spacing = 0.6f, color = ink, maxLines = 1)
        }
        T(value, Modifier.padding(top = 4.dp), size = 24f, w = 800, spacing = -1f, color = ink, suffix = unit, suffixSize = 10f)
    }
}

private fun fmt(v: Number?, decimals: Int = 0): String = if (v == null) "--" else String.format("%.${decimals}f", v.toDouble())

/** Dernière mesure de l'ESP32 : MQTT en direct (~1 s), repli sur l'API. */
@Composable
fun LiveVitalsCard(patientId: String?, deviceId: String?) {
    val c = Pal.c
    val live = useLiveTelemetry(patientId, deviceId)
    val data: Telemetry? = live.data
    val ageS = data?.let { (live.nowMs - it.epochMs) / 1000 }
    val fresh = live.error == null && ageS != null && ageS < STALE_AFTER_S
    val dot = if (live.error != null) c.urgent else if (fresh) c.track else c.switchOff

    Card(Modifier.fillMaxWidth().padding(bottom = 10.dp), radius = 20f, pad = 11f) {
        Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            T(t("live.kicker"), size = 7.5f, w = 800, spacing = 0.8f)
            Box(Modifier.size(9.dp).background(dot, CircleShape).border(1.dp, c.ink, CircleShape))
        }
        when {
            live.loading && data == null -> Box(Modifier.fillMaxWidth().padding(vertical = 18.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = c.primary, modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
            }
            live.error != null && data == null -> T(t("live.offline"), size = 9f, w = 700, color = c.urgentText)
            data == null -> T(t(if (deviceId == null) "live.noDevice" else "live.noData"), size = 9f, color = c.muted)
            else -> {
                if (data.fallDetected) {
                    Row(
                        Modifier.fillMaxWidth().padding(bottom = 8.dp).background(c.urgent, RoundedCornerShape(12.dp)).border(1.2.dp, c.ink, RoundedCornerShape(12.dp)).padding(8.dp),
                        horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(IconName.activity, 16.dp, Color.White)
                        T(t("live.fall"), size = 9f, w = 800, color = Color.White)
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Tile(IconName.heart, t("live.bpm"), fmt(data.bpm), " bpm", LightPalette.pink, Modifier.weight(1f))
                    Tile(IconName.drop, t("live.spo2"), fmt(data.spo2), " %", LightPalette.sky, Modifier.weight(1f))
                }
                Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Tile(IconName.thermo, t("live.roomTemp"), fmt(data.roomTemp, 1), " °C", LightPalette.yellow, Modifier.weight(1f))
                    Tile(IconName.sensor, t("live.humidity"), fmt(data.roomHumidity), " %", LightPalette.green, Modifier.weight(1f))
                }
                T(
                    if (live.error != null) t("live.offline") else t(if (fresh) "live.updated" else "live.stale", "ago" to formatAgo(data.epochMs, live.nowMs)),
                    Modifier.padding(top = 8.dp), size = 7f, color = if (live.error != null) c.urgentText else c.muted,
                )
            }
        }
        // Source des données : MQTT direct ou API
        Row(Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(7.dp).background(
                    when {
                        live.viaMqtt -> c.track
                        live.mqtt == MqttState.CONNECTED -> c.review
                        else -> c.switchOff
                    },
                    CircleShape,
                ),
            )
            T(if (live.viaMqtt) t("live.mqttOn") else if (live.mqtt == MqttState.CONNECTED) t("live.mqttWaiting") else t("live.mqttOff"), size = 6.5f, w = 700, color = c.muted)
            if (deviceId != null) {
                Spacer(Modifier.width(2.dp))
                T("· " + t("live.device", "id" to deviceId), size = 6.5f, color = c.muted)
            }
        }
    }
}
