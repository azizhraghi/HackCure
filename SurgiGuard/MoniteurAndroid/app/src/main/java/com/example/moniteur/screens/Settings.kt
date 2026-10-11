package com.example.moniteur.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.moniteur.LocalApp
import com.example.moniteur.data.ApiError
import com.example.moniteur.data.MqttConfig
import com.example.moniteur.data.MqttState
import com.example.moniteur.ui.Button
import com.example.moniteur.ui.Card
import com.example.moniteur.ui.Field
import com.example.moniteur.ui.HapticTick
import com.example.moniteur.ui.IconBadge
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.ListRow
import com.example.moniteur.ui.Screen
import com.example.moniteur.ui.Switch
import com.example.moniteur.ui.T
import com.example.moniteur.ui.TopBar
import com.example.moniteur.ui.rememberHaptic
import com.example.moniteur.ui.t
import com.example.moniteur.ui.tap
import com.example.moniteur.ui.theme.Pal
import com.example.moniteur.useMyProfile
import kotlinx.coroutines.launch

@Composable
private fun Label(text: String) = T(text, Modifier.padding(start = 2.dp, top = 14.dp, bottom = 6.dp), size = 6f, w = 800, spacing = 0.8f)

@Composable
fun SettingsScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val scope = rememberCoroutineScope()
    val haptic = rememberHaptic()
    val isDark = app.darkMode ?: isSystemInDarkTheme()
    var url by remember { mutableStateOf(app.apiUrl) }
    var device by remember { mutableStateOf("") }
    var deviceMsg by remember { mutableStateOf<String?>(null) }
    val mqttState by app.mqtt.state.collectAsState()
    val profile = useMyProfile().data
    val isPatient = app.role == "patient"
    val savedMsg = t("settings.deviceSaved")
    val networkMsg = t("auth.network")

    Screen(Modifier.imePadding()) {
        TopBar(t("settings.top"))
        Label(t("settings.appearance"))
        Card(Modifier.fillMaxWidth(), radius = 17f) {
            ListRow(t("settings.dark"), left = { IconBadge(IconName.moon, c.lavender) }, sub = t("settings.darkSub"), right = { Switch(isDark, { app.setDark(!isDark) }) }, last = true)
        }

        Label(t("settings.language"))
        Card(Modifier.fillMaxWidth(), radius = 17f, pad = 6f) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("en" to "English", "fr" to "Français").forEach { (code, name) ->
                    val on = app.lang == code
                    Box(
                        Modifier.weight(1f).height(44.dp).background(if (on) c.primary else Color.Transparent, RoundedCornerShape(12.dp))
                            .then(if (on) Modifier.border(1.2.dp, c.ink, RoundedCornerShape(12.dp)) else Modifier).tap { haptic(HapticTick); app.changeLang(code) },
                        contentAlignment = Alignment.Center,
                    ) { T(name, size = 11f, w = 800, color = if (on) Color.White else c.text) }
                }
            }
        }

        Label(t("settings.server"))
        Card(Modifier.fillMaxWidth(), radius = 17f, pad = 10f) {
            T(t("settings.serverSub"), Modifier.padding(bottom = 6.dp), size = 7f, color = c.muted)
            Field(null, url, { url = it }, keyboard = KeyboardType.Uri, height = 44f, bg = c.bg, fontSize = 12f)
            Button(t("common.save"), { app.saveApiUrl(url); url = app.apiUrl }, Modifier.padding(top = 8.dp), secondary = true, flat = true, height = 38f, size = 11f)
        }

        // Liaison temps réel avec l'ESP32 (broker EMQX)
        Label(t("settings.mqtt"))
        Card(Modifier.fillMaxWidth(), radius = 17f, pad = 10f) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(10.dp).background(when (mqttState) { MqttState.CONNECTED -> c.track; MqttState.CONNECTING -> c.review; else -> c.urgent }, CircleShape))
                T(t("mqtt.$mqttState"), size = 9f, w = 800)
            }
            T(t("settings.mqttSub", "broker" to MqttConfig.BROKER, "topic" to MqttConfig.TOPIC), Modifier.padding(top = 6.dp), size = 7f, color = c.muted)
        }

        if (isPatient) {
            Label(t("settings.device"))
            Card(Modifier.fillMaxWidth(), radius = 17f, pad = 10f) {
                T(t("settings.deviceSub"), Modifier.padding(bottom = 6.dp), size = 7f, color = c.muted)
                T(profile?.deviceId?.let { t("live.device", "id" to it) } ?: t("live.noDevice"), Modifier.padding(bottom = 6.dp), size = 8f, w = 800)
                Field(null, device, { device = it }, height = 44f, bg = c.bg, fontSize = 12f, placeholder = "ESP32_001")
                if (deviceMsg != null) T(deviceMsg!!, Modifier.padding(top = 6.dp), size = 8f, w = 700, color = if (deviceMsg == savedMsg) c.trackText else c.urgentText)
                Button(t("settings.deviceSave"), {
                    val id = device.trim()
                    if (id.isNotEmpty()) scope.launch {
                        deviceMsg = try { app.api.setDevice(id); savedMsg } catch (e: ApiError) { if (e.status != 0) e.message else networkMsg }
                    }
                }, Modifier.padding(top = 8.dp), flat = true, height = 38f, size = 11f)
            }
        }

        Label(t("settings.account"))
        Card(Modifier.fillMaxWidth(), radius = 17f) {
            ListRow(t("settings.switchRole"), left = { IconBadge(IconName.rotate, c.yellow) }, sub = t("settings.switchRoleSub"), onClick = { app.signOut() }, last = true)
        }

        Column(Modifier.fillMaxWidth().padding(top = 22.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(4.dp)) {
            T(t("settings.about"), size = 8f, w = 800, color = c.muted)
            T(t("settings.disclaimer"), size = 7f, color = c.muted, center = true)
        }
    }
}
