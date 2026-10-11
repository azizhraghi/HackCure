package com.example.moniteur.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.moniteur.LocalApp
import com.example.moniteur.Route
import com.example.moniteur.data.HistoryPoint
import com.example.moniteur.data.Mock
import com.example.moniteur.data.initials
import com.example.moniteur.ui.Avatar
import com.example.moniteur.ui.Button
import com.example.moniteur.ui.Card
import com.example.moniteur.ui.Chip
import com.example.moniteur.ui.Ecg
import com.example.moniteur.ui.HapticImpact
import com.example.moniteur.ui.HapticTick
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconBadge
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.KneeFigure
import com.example.moniteur.ui.ListRow
import com.example.moniteur.ui.MiniBars
import com.example.moniteur.ui.MiniLine
import com.example.moniteur.ui.Muted
import com.example.moniteur.ui.PageTitle
import com.example.moniteur.ui.RoundButton
import com.example.moniteur.ui.Screen
import com.example.moniteur.ui.ScoreRing
import com.example.moniteur.ui.SectionRow
import com.example.moniteur.ui.SimulatedTag
import com.example.moniteur.ui.Spark
import com.example.moniteur.ui.T
import com.example.moniteur.ui.Toggle
import com.example.moniteur.ui.TopBar
import com.example.moniteur.ui.TrajectoryChart
import com.example.moniteur.ui.WoundThumb
import com.example.moniteur.ui.rememberCountUp
import com.example.moniteur.ui.rememberHaptic
import com.example.moniteur.ui.rowDivider
import com.example.moniteur.ui.dashedBorder
import com.example.moniteur.ui.t
import com.example.moniteur.ui.tap
import com.example.moniteur.ui.theme.Pal
import com.example.moniteur.ui.tl
import com.example.moniteur.ui.toneColor
import com.example.moniteur.usePolling
import com.example.moniteur.useMyProfile
import kotlin.math.max
import kotlin.math.min

@Composable
private fun Shortcut(icon: IconName, title: String, sub: String, bg: Color, modifier: Modifier, onClick: () -> Unit) {
    val c = Pal.c
    val haptic = rememberHaptic()
    Card(modifier.tap { haptic(HapticImpact); onClick() }, bg = bg, radius = 17f, pad = 11f) {
        Column(Modifier.heightIn(min = 52.dp)) {
            IconBadge(icon, c.surface, 28f)
            T(title, Modifier.padding(top = 7.dp), size = 9.5f, w = 800)
            T(sub, Modifier.padding(top = 2.dp), size = 7f, color = c.muted)
        }
    }
}

@Composable
fun PatientHomeScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val haptic = rememberHaptic()
    var taskDone by remember { mutableStateOf(false) }
    var taskHidden by remember { mutableStateOf(false) }
    val user = app.session?.user
    val profile = useMyProfile().data

    Screen {
        HomeHeader(t("home.welcome"), "${user?.firstName ?: ""} 👋", initials(user?.fullName ?: "")) {
            RoundButton(IconName.sparkle, { app.push(Route.AIAssistant()) }, 35f)
            RoundButton(IconName.bell, { app.push(Route.SensingRequest) }, 35f)
        }
        PageTitle(t("home.title"))

        LiveVitalsCard(app.session?.profileId, profile?.deviceId)

        // Alerte capteur -> demande de mesure active
        Card(Modifier.fillMaxWidth().padding(bottom = 10.dp).tap { app.push(Route.SensingRequest) }, bg = c.lilacBg, radius = 16f, pad = 10f) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                IconBadge(IconName.sensor, c.surface, 32f, 10f)
                Column(Modifier.weight(1f)) {
                    T(t("home.alert"), size = 7f, w = 800, spacing = 0.8f, upper = true, color = c.muted)
                    T(t("home.alertSub"), Modifier.padding(top = 2.dp), size = 9.5f, w = 800)
                }
                Box(Modifier.background(c.primary, CircleShape).border(1.dp, c.ink, CircleShape).padding(horizontal = 10.dp, vertical = 6.dp)) {
                    T(t("home.alertCta"), size = 8f, w = 800, color = Color.White)
                }
            }
        }

        if (!taskHidden) {
            Card(Modifier.fillMaxWidth().tap { app.push(Route.WoundScan) }, bg = c.task, radius = 22f, pad = 16f) {
                Box(Modifier.fillMaxWidth().heightIn(min = 99.dp)) {
                    Box(
                        Modifier.align(Alignment.TopEnd).offset(x = 5.dp, y = (-6).dp).size(26.dp).background(Color(0x80FFFFFF), CircleShape).border(1.2.dp, c.ink, CircleShape)
                            .tap { taskHidden = true },
                        contentAlignment = Alignment.Center,
                    ) { Icon(IconName.close, 16.dp) }
                    Column {
                        T(t("home.task"), size = 8f, w = 800, spacing = 1.2f)
                        T(t("home.taskTitle"), Modifier.padding(top = 6.dp), size = 16f, w = 800, lh = 1.3f, strike = taskDone)
                        Row(Modifier.fillMaxWidth().padding(top = 11.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            T(t("home.about"), size = 8f)
                            Box(
                                Modifier.background(if (taskDone) c.green else c.surface, CircleShape).border(1.2.dp, c.ink, CircleShape)
                                    .tap { haptic(HapticImpact); taskDone = !taskDone }.padding(horizontal = 12.dp, vertical = 7.dp),
                            ) { T((if (taskDone) "✓ " else "") + t("common.done") + " ›", size = 9f, w = 800) }
                        }
                    }
                }
            }
        }

        Row(Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Card(Modifier.weight(1f).height(145.dp), bg = c.pink, pad = 12f) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    T(t("home.woundTemp"), Modifier.weight(1f), size = 7.5f, w = 800, spacing = 0.7f)
                    SimulatedTag()
                }
                T("${Mock.woundTemp}", Modifier.padding(top = 5.dp), size = 31f, w = 800, spacing = -1.6f, suffix = "°C", suffixSize = 12f)
                T(t("home.normal"), size = 7.5f, color = c.muted)
                MiniBars()
            }
            Card(Modifier.weight(1f).height(145.dp), bg = c.yellow, pad = 12f) {
                T(t("home.pain"), size = 7.5f, w = 800, spacing = 0.7f)
                T("${Mock.pain}", Modifier.padding(top = 5.dp), size = 31f, w = 800, spacing = -1.6f, suffix = "/10", suffixSize = 12f)
                T(t("home.painDown"), size = 7.5f, w = 700, color = c.trackText)
                MiniLine()
            }
        }

        Row(Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Shortcut(IconName.pill, t("home.meds"), t("home.medsSub"), c.lavender, Modifier.weight(1f)) { app.push(Route.Medications) }
            Shortcut(IconName.sparkle, t("home.ai"), t("home.aiSub"), c.sky, Modifier.weight(1f)) { app.push(Route.AIAssistant()) }
        }

        SectionRow(t("home.check"), rightContent = { T(t("common.viewDetails"), Modifier.tap { app.goPatientTab(3) }, size = 8f, w = 800, color = c.primary) })
        Card(Modifier.fillMaxWidth().height(116.dp), radius = 20f, pad = 10f) {
            Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                ScoreRing(Mock.score, label = t("home.score"))
                Column(Modifier.weight(1f)) {
                    T(t("home.onTrack"), size = 10f, w = 800)
                    T(t("home.ahead"), Modifier.padding(top = 3.dp, bottom = 10.dp), size = 7f, color = c.muted)
                    Row(horizontalArrangement = Arrangement.spacedBy(13.dp)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                            T("☾", size = 13f)
                            Column { T(Mock.sleep, size = 9f, w = 800); T(t("home.lastNight"), size = 6f, color = c.muted) }
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                            T("◷", size = 13f)
                            Column { T(t("common.day") + " ${Mock.day}", size = 9f, w = 800); T(t("home.of42"), size = 6f, color = c.muted) }
                        }
                    }
                }
            }
        }

        Card(Modifier.fillMaxWidth().padding(top = 10.dp), bg = c.mint, radius = 16f, pad = 11f) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                IconBadge(IconName.calendar, c.surface, 32f, 10f)
                Column(Modifier.weight(1f)) {
                    T(t("home.appt"), size = 6.5f, w = 800, spacing = 0.8f, color = c.muted)
                    T(t("home.apptTitle"), Modifier.padding(top = 2.dp), size = 10f, w = 800)
                    T(t("home.apptSub"), Modifier.padding(top = 1.dp), size = 7.5f, color = c.muted)
                }
            }
        }
    }
}

@Composable
private fun ScaleCard(label: String, value: Int, onChange: (Int) -> Unit, bg: Color, icon: IconName, none: String, worst: String) {
    val c = Pal.c
    val haptic = rememberHaptic()
    Card(Modifier.fillMaxWidth().padding(bottom = 9.dp), bg = bg, pad = 12f) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconBadge(icon, c.surface, 28f)
            T(label, Modifier.weight(1f), size = 10f, w = 800)
            T("$value", size = 24f, w = 800, spacing = -1f, suffix = "/10", suffixSize = 10f)
        }
        Slider(
            value.toFloat(), { v -> val r = Math.round(v); if (r != value) haptic(HapticTick); onChange(r) }, valueRange = 0f..10f, steps = 9,
            colors = SliderDefaults.colors(thumbColor = Color(0xFF1E88E5), activeTrackColor = Color(0xFF1B2A4A), inactiveTrackColor = Color(0x401B2A4A), activeTickColor = Color.Transparent, inactiveTickColor = Color.Transparent),
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            T("0 · $none", size = 7f, color = c.muted); T("10 · $worst", size = 7f, color = c.muted)
        }
    }
}

@Composable
private fun ChipToggle(label: String, on: Boolean, danger: Boolean = false, onClick: () -> Unit) {
    val c = Pal.c
    val haptic = rememberHaptic()
    Row(
        Modifier.background(if (on) (if (danger) c.urgent else c.pink) else c.surface, CircleShape).border(1.2.dp, c.ink, CircleShape)
            .tap { haptic(HapticTick); onClick() }.padding(horizontal = 12.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        if (on) Icon(IconName.check, 12.dp, if (danger) Color.White else c.text)
        T(label, size = 9f, w = 800, color = if (on && danger) Color.White else c.text)
    }
}

@Composable
fun CheckInScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val ctx = LocalContext.current
    val haptic = rememberHaptic()
    var pain by remember { mutableStateOf(3) }
    var fatigue by remember { mutableStateOf(4) }
    var mobility by remember { mutableStateOf(5) }
    var wound by remember { mutableStateOf(setOf<Int>()) }
    var other by remember { mutableStateOf(setOf<Int>()) }
    var sent by remember { mutableStateOf(false) }
    val woundChips = tl("checkin.woundChips")
    val otherChips = tl("checkin.otherChips")
    // Écoulement, chaleur, frissons, fièvre : signes d'alerte ; essoufflement / douleur au mollet : urgence
    val warning = 2 in wound || 3 in wound || 0 in other || 1 in other || pain >= 7
    val emergency = 4 in other || 5 in other

    Screen {
        TopBar(t("checkin.top"), back = false)
        if (sent) {
            Column(Modifier.fillMaxWidth().padding(top = 40.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.size(70.dp).background(c.green, CircleShape).border(1.5.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { Icon(IconName.check, 32.dp) }
                PageTitle(t("checkin.sentTitle"), center = true)
                Muted(t("checkin.sentSub"), center = true)
            }
            if (warning) Card(Modifier.fillMaxWidth(), bg = c.peach, radius = 16f, pad = 12f, borderColor = c.review) { T(t("checkin.warning"), size = 9f, w = 700, lh = 1.45f) }
            Button(t("common.edit"), { sent = false }, Modifier.padding(top = 20.dp), secondary = true)
            return@Screen
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Shortcut(IconName.activity, t("checkin.rehab"), t("checkin.rehabSub"), c.sky, Modifier.weight(1f)) { app.push(Route.Rehab) }
            Shortcut(IconName.camera, t("checkin.scan"), t("checkin.scanSub"), c.lavender, Modifier.weight(1f)) { app.push(Route.WoundScan) }
        }
        T(t("checkin.kicker"), Modifier.padding(top = 18.dp), size = 9f, w = 800, spacing = 1.5f, color = c.primary)
        PageTitle(t("checkin.title"), Modifier.padding(top = 6.dp, bottom = 9.dp))
        Muted(t("checkin.sub"))
        ScaleCard(t("checkin.pain"), pain, { pain = it }, c.yellow, IconName.activity, t("checkin.none"), t("checkin.worst"))
        ScaleCard(t("checkin.fatigue"), fatigue, { fatigue = it }, c.lavender, IconName.moon, t("checkin.none"), t("checkin.worst"))
        ScaleCard(t("checkin.mobility"), mobility, { mobility = it }, c.sky, IconName.rotate, t("checkin.none"), t("checkin.worst"))

        SectionRow(t("checkin.wound"))
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            woundChips.forEachIndexed { i, x -> ChipToggle(x, i in wound) { wound = if (i in wound) wound - i else wound + i } }
        }
        SectionRow(t("checkin.other"))
        FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            otherChips.forEachIndexed { i, x -> ChipToggle(x, i in other, danger = i >= 4) { other = if (i in other) other - i else other + i } }
        }
        if (emergency) {
            Card(Modifier.fillMaxWidth().padding(top = 12.dp).tap { callNumber(ctx, "112") }, bg = c.urgent, radius = 16f, pad = 12f) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconBadge(IconName.phone, Color.White, 32f)
                    T(t("checkin.emergency"), Modifier.weight(1f), size = 9f, w = 800, color = Color(0xFF1B2A4A), lh = 1.4f)
                }
            }
        } else if (warning) {
            Box(Modifier.fillMaxWidth().padding(top = 12.dp).background(c.peach, RoundedCornerShape(16.dp)).border(1.5.dp, c.review, RoundedCornerShape(16.dp)).padding(12.dp)) {
                T(t("checkin.warning"), size = 9f, w = 700, lh = 1.45f)
            }
        }
        Button(t("checkin.submit"), { haptic(HapticImpact); sent = true }, Modifier.padding(top = 16.dp))
    }
}

private class Callout(val key: String, val icon: IconName, val label: String, val value: String, val trend: String, val expected: String, val review: Boolean, val status: String)

@Composable
fun TwinScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val handle = remember { Twin3DHandle() }
    val haptic = rememberHaptic()
    var weekView by remember { mutableStateOf(false) }
    var layer by remember { mutableStateOf("Overview") }
    var day by remember { mutableStateOf(4) }
    var selected by remember { mutableStateOf<String?>(null) }
    val layers = listOf("Overview", "Wound", "Mobility", "Sensors", "Muscles")
    val layerNames = tl("twin.layers")
    val progress = (day - 1) / 41f
    val mobility = Math.round(64 + progress * 55)
    val healing = Math.round(91 + progress * 10)
    val mobilityShown = rememberCountUp(mobility)
    val healingShown = rememberCountUp(healing)
    val angle = Math.round(74 + progress * 25)
    val dayLabel = t("common.day")
    val weekLabel = t("common.week")

    val callouts = listOf(
        Callout("mobility", IconName.rotate, t("twin.mobility"), "$mobilityShown%", "↑", t("twin.expected", "v" to "${min(95, mobility + 7)}%"), false, t("common.onTrack")),
        Callout("temp", IconName.thermo, t("twin.temp"), "37.8°C", "↑", t("twin.expected", "v" to "≤37.4°C"), true, t("twin.needsAttention")),
        Callout("pain", IconName.activity, t("twin.pain"), "3/10", "↓", t("twin.expected", "v" to "4/10"), false, t("common.onTrack")),
        Callout("wound", IconName.camera, t("twin.wound"), "$healingShown/100", "↑", t("twin.expected", "v" to "89/100"), false, t("common.onTrack")),
    )
    val sel = callouts.find { it.key == selected }

    Screen {
        TopBar(t("twin.top"), back = false, action = {
            Toggle(listOf(dayLabel, weekLabel), if (weekView) weekLabel else dayLabel) { weekView = it == weekLabel }
        })
        Row(Modifier.horizontalScroll(rememberScrollState()).padding(top = 2.dp, bottom = 8.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            layers.forEachIndexed { i, x ->
                Box(
                    Modifier.background(if (layer == x) c.primary else c.surface, CircleShape).border(1.dp, if (layer == x) c.ink else Color(0xFFBDC7D6), CircleShape)
                        .tap { haptic(HapticTick); layer = x }.padding(horizontal = 10.dp, vertical = 7.dp),
                ) { T(layerNames.getOrElse(i) { x }, size = 7.5f, w = 700, color = if (layer == x) Color.White else c.text) }
            }
        }

        Box(
            Modifier.fillMaxWidth().height(509.dp).clip(RoundedCornerShape(25.dp))
                .background(Brush.radialGradient(0f to c.stageA, 0.54f to c.stageB, 1f to c.stageC, radius = 900f))
                .border(1.5.dp, c.ink, RoundedCornerShape(25.dp)),
        ) {
            Box(Modifier.fillMaxWidth().padding(top = 103.dp).height(70.dp)) {
                Ecg()
                Box(Modifier.padding(start = 12.dp, top = 3.dp).background(Color(0xBFFFFFFF), CircleShape).padding(horizontal = 6.dp, vertical = 3.dp)) { T("72 bpm", size = 6f, w = 800, color = Color(0xFF1E88E5)) }
            }
            Twin3D(handle, day, layer, selected, { app.push(Route.TwinDetail) }, t("twin.loading"), t("twin.fallback"))

            // pastille d'état
            Row(
                Modifier.padding(start = 12.dp, top = 11.dp).height(25.dp).background(c.glass, CircleShape).border(1.dp, c.ink, CircleShape).padding(horizontal = 9.dp),
                horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically,
            ) { Icon(IconName.check, 13.dp, c.trackText); T(t("twin.status", "day" to day), size = 6.5f, w = 800, color = c.trackText) }

            // commandes de vue
            Row(
                Modifier.align(Alignment.TopEnd).padding(end = 10.dp, top = 42.dp).background(c.glass, RoundedCornerShape(10.dp)).border(1.dp, c.ink, RoundedCornerShape(10.dp)).clip(RoundedCornerShape(10.dp)),
            ) {
                listOf("rotate", "zoom", "reset").forEachIndexed { i, cmd ->
                    Box(Modifier.size(34.dp).tap { haptic(HapticTick); handle.command(cmd) }, contentAlignment = Alignment.Center) {
                        when (cmd) {
                            "rotate" -> Icon(IconName.rotate, 15.dp)
                            "zoom" -> T("＋", size = 14f, w = 800)
                            else -> T("⌂", size = 14f, w = 800)
                        }
                    }
                }
            }

            // cartes de mesures
            fun place(key: String): Modifier = when (key) {
                "mobility" -> Modifier.align(Alignment.TopStart).padding(start = 9.dp, top = 116.dp)
                "temp" -> Modifier.align(Alignment.TopEnd).padding(end = 9.dp, top = 105.dp)
                "pain" -> Modifier.align(Alignment.TopStart).padding(start = 9.dp, top = 281.dp)
                else -> Modifier.align(Alignment.TopEnd).padding(end = 9.dp, top = 267.dp)
            }
            callouts.forEach { item ->
                val on = selected == item.key
                val tone = if (item.review) c.review else c.track
                Box(place(item.key).width(113.dp)) {
                    Column(
                        Modifier.fillMaxWidth().heightIn(min = 65.dp).background(c.glass, RoundedCornerShape(12.dp))
                            .border(if (on) 1.5.dp else 1.dp, if (on) c.primary else Color(0x941B2A4A), RoundedCornerShape(12.dp))
                            .tap { haptic(HapticTick); selected = item.key }.padding(start = 10.dp, top = 7.dp, end = 7.dp, bottom = 7.dp),
                    ) {
                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                            Box(Modifier.size(23.dp).background(if (item.review) Color(0xFFFFF0D8) else Color(0xFFE8F5F1), RoundedCornerShape(7.dp)), contentAlignment = Alignment.Center) { Icon(item.icon, 14.dp, Color(0xFF1B2A4A)) }
                            Column(Modifier.weight(1f)) {
                                T(item.label, size = 5.5f, w = 800, maxLines = 1)
                                T(item.value + " ", Modifier.padding(top = 2.dp), size = 10f, w = 800, suffix = item.trend, suffixSize = 7f, suffixColor = if (item.review) c.reviewText else c.trackText)
                            }
                        }
                        T(item.status + " · " + item.expected, Modifier.padding(top = 4.dp), size = 5f, w = 600, color = c.muted, lh = 1.3f)
                    }
                    Box(Modifier.matchParentSize().padding(vertical = 9.dp)) { Box(Modifier.width(3.dp).fillMaxHeight().background(tone, RoundedCornerShape(topEnd = 4.dp, bottomEnd = 4.dp))) }
                }
            }

            // lectures par couche
            if (layer == "Wound") Row(
                Modifier.align(Alignment.BottomStart).padding(start = 25.dp, bottom = 62.dp).background(c.glass, RoundedCornerShape(10.dp)).border(1.dp, c.ink, RoundedCornerShape(10.dp)).padding(5.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) { WoundThumb(35f, 31f, 6f); T(t("scan.day1"), size = 4.5f) }
                T("→", w = 800)
                Column(horizontalAlignment = Alignment.CenterHorizontally) { WoundThumb(35f, 31f, 6f); T(t("common.today"), size = 4.5f) }
            }
            if (layer == "Mobility") Column(
                Modifier.align(Alignment.BottomEnd).padding(end = 12.dp, bottom = 62.dp).width(109.dp).background(c.glass, RoundedCornerShape(10.dp)).border(1.dp, c.ink, RoundedCornerShape(10.dp)).padding(7.dp),
            ) { T(t("twin.kneeAngle"), size = 6f); T("$angle°", size = 16f, w = 800); T(t("twin.goal"), size = 6f, color = c.muted) }
            if (layer == "Sensors") FlowRow(
                Modifier.align(Alignment.BottomStart).padding(start = 12.dp, end = 12.dp, bottom = 62.dp), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Chip("37.8°C", tone = "yellow"); Chip(t("twin.moisture"), tone = "blue")
                Box(Modifier.background(Color.White, CircleShape).padding(horizontal = 6.dp, vertical = 4.dp)) { T(t("twin.signal"), size = 5.5f, color = Color(0xFF1B2A4A)) }
                SimulatedTag()
            }
            if (layer == "Muscles") Row(
                Modifier.align(Alignment.BottomStart).padding(start = 12.dp, bottom = 62.dp).background(c.surface, RoundedCornerShape(9.dp)).border(1.dp, c.ink, RoundedCornerShape(9.dp)).padding(6.dp),
                horizontalArrangement = Arrangement.spacedBy(7.dp),
            ) {
                listOf(t("twin.low") to Color(0xFFF2C1CF), t("twin.moderate") to Color(0xFFDF7EA0), t("twin.active") to Color(0xFFB54C73)).forEach { (l, col) ->
                    Row(horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.CenterVertically) { Box(Modifier.size(7.dp).background(col, CircleShape)); T(l, size = 5f) }
                }
            }

            // curseur de jour
            Row(Modifier.align(Alignment.BottomCenter).padding(start = 13.dp, end = 13.dp, bottom = 10.dp), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.Bottom) {
                T("$dayLabel 1", Modifier.padding(bottom = 7.dp), size = 5.5f, w = 800)
                Box(Modifier.weight(1f)) {
                    Slider(
                        day.toFloat(), { day = Math.round(it) }, valueRange = 1f..42f, steps = 40,
                        colors = SliderDefaults.colors(thumbColor = Color(0xFF1E88E5), activeTrackColor = Color(0xFF1E88E5), inactiveTrackColor = Color(0xFFA9E3FA), activeTickColor = Color.Transparent, inactiveTickColor = Color.Transparent),
                    )
                    Box(Modifier.align(Alignment.TopCenter).offset(y = (-14).dp).background(Color(0xFF1B2A4A), RoundedCornerShape(7.dp)).padding(horizontal = 8.dp, vertical = 4.dp)) {
                        T("$dayLabel $day · " + if (day == 4) t("twin.todayTag") else if (day < 4) t("twin.past") else t("twin.preview"), size = 5.5f, w = 800, color = Color.White)
                    }
                }
                T("$dayLabel 42", Modifier.padding(bottom = 7.dp), size = 5.5f, w = 800)
            }

            // feuille de preuves
            if (sel != null) Box(Modifier.align(Alignment.BottomCenter)) {
                Box(
                    Modifier.fillMaxWidth().height(174.dp).background(c.surface, RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp))
                        .border(1.5.dp, c.ink, RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp)).padding(start = 14.dp, top = 14.dp, end = 14.dp, bottom = 10.dp),
                ) {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Column(Modifier.width(118.dp).fillMaxHeightCompat(), verticalArrangement = Arrangement.SpaceBetween) {
                            Column {
                                T(t("twin.trend"), size = 5.5f, spacing = 0.7f)
                                T(sel.label, Modifier.padding(top = 3.dp), size = 9f, w = 800)
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
                                if (sel.key == "wound") WoundThumb(34f, 34f, 7f)
                                else Box(Modifier.size(30.dp).background(c.iceBlue, RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) { Icon(if (sel.key == "temp") IconName.sensor else IconName.activity, 17.dp) }
                                Column(Modifier.weight(1f)) {
                                    T(t("twin.latest"), size = 4.8f)
                                    T(if (sel.key == "wound") t("twin.photoAnalyzed") else t("twin.liveReading"), Modifier.padding(top = 2.dp), size = 5.5f, w = 800, lh = 1.3f)
                                }
                            }
                        }
                        Column(Modifier.weight(1f).padding(top = 20.dp)) {
                            MiniLine(color = if (selected == "temp") Color(0xFFFFB347) else Color(0xFF1E88E5), fill = true, height = 64f)
                            if (selected == "temp") SimulatedTag(Modifier.padding(top = 6.dp))
                        }
                    }
                    Box(
                        Modifier.align(Alignment.TopEnd).offset(x = 3.dp, y = (-5).dp).size(30.dp).background(c.surface, CircleShape).border(1.dp, c.ink, CircleShape).tap { selected = null },
                        contentAlignment = Alignment.Center,
                    ) { Icon(IconName.close, 14.dp) }
                }
            }
        }

        Card(Modifier.fillMaxWidth().height(92.dp).padding(top = 0.dp).tap { app.goPatientTab(3) }, bg = c.green, radius = 18f, pad = 10f) {
            Row(Modifier.fillMaxSize()) {
                Column(Modifier.fillMaxWidth(0.52f)) {
                    T(t("twin.expVsActual"), size = 6.5f, w = 800)
                    T(t("common.onTrack") + " ", Modifier.padding(top = 5.dp), size = 14f, w = 800, suffix = "✓", suffixSize = 14f, suffixColor = c.trackText)
                    T(t("twin.ahead"), Modifier.padding(top = 4.dp), size = 7f)
                }
                Box(Modifier.weight(1f)) {
                    MiniLine(Modifier.padding(top = 0.dp), color = Color(0xFF1E88E5), fill = true)
                    MiniLine(Modifier.padding(top = 7.dp), color = Color(0xFF70809D), dashed = true)
                }
            }
        }
    }
}

private fun Modifier.fillMaxHeightCompat(): Modifier = this.then(Modifier.fillMaxSize())

private fun avg(pts: List<HistoryPoint>, f: (HistoryPoint) -> Double?): List<Double> = pts.mapNotNull(f)

@Composable
fun ReportsScreen() {
    val c = Pal.c
    val app = LocalApp.current
    var week by remember { mutableStateOf(true) }
    val profileId = app.session?.profileId
    // Historique réel stocké par l'API (alimenté par le pont MQTT)
    val history = usePolling(Triple(app.apiUrl, profileId, week), 30000, enabled = profileId != null) {
        app.api.history(profileId!!, if (week) 168 else 24, if (week) 60 else 15)
    }
    val pts = history.data ?: emptyList()
    val bpmS = avg(pts) { it.bpm }.filter { it > 0 }
    val spo2S = avg(pts) { it.spo2 }.filter { it > 0 }
    val tempS = avg(pts) { it.roomTemp }
    fun last(l: List<Double>, d: Int, unit: String) = if (l.isEmpty()) "--" else String.format("%.${d}f", l.last()) + unit

    class V(val label: String, val value: String, val bg: Color, val values: List<Double>, val col: Color, val icon: IconName)
    val vitals = listOf(
        V(t("reports.temp"), last(tempS, 1, "°C"), c.pink, tempS, Color(0xFFEF695D), IconName.thermo),
        V(t("reports.hr"), last(bpmS, 0, " bpm"), c.sky, bpmS, Color(0xFF1E88E5), IconName.heart),
        V(t("live.spo2"), last(spo2S, 0, " %"), c.green, spo2S, Color(0xFF218D65), IconName.drop),
    )
    val milestones = listOf(Triple(t("reports.ms1"), t("reports.ms1s"), true), Triple(t("reports.ms2"), t("reports.ms2s"), false), Triple(t("reports.ms3"), t("reports.ms3s"), false))
    val appts = listOf(
        listOf(t("reports.a1"), t("reports.a1s"), t("reports.a1d")) to (IconName.activity to c.lavender),
        listOf(t("reports.a2"), t("reports.a2s"), t("reports.a2d")) to (IconName.check to c.yellow),
        listOf(t("reports.a3"), t("reports.a3s"), t("reports.a3d")) to (IconName.calendar to c.sky),
    )
    val docs = listOf(t("upload.discharge"), t("upload.operative"), t("upload.labs"), t("upload.meds"))
    val dayLabel = t("common.day")
    val weekLabel = t("common.week")

    Screen {
        TopBar(t("reports.top"), back = false, action = {
            Toggle(listOf(dayLabel, weekLabel), if (week) weekLabel else dayLabel) { week = it == weekLabel }
        })
        T(t("reports.kicker"), Modifier.padding(top = 6.dp), size = 9f, w = 800, spacing = 1.5f, color = c.primary)
        PageTitle(t("reports.title"), Modifier.padding(top = 6.dp, bottom = 9.dp))

        Card(Modifier.fillMaxWidth(), bg = c.green, radius = 20f, pad = 12f) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    T(t("reports.trajectory"), size = 13f, w = 800)
                    T(t("reports.trajectorySub"), Modifier.padding(top = 2.dp), size = 7.5f, color = c.muted)
                }
                Chip(t("common.onTrack") + " ✓")
            }
            Box(Modifier.padding(top = 8.dp).fillMaxWidth().background(c.surface, RoundedCornerShape(14.dp)).border(1.dp, c.ink, RoundedCornerShape(14.dp)).padding(8.dp)) { TrajectoryChart(110f) }
            Row(Modifier.padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(16.dp, 3.dp).background(c.primary, RoundedCornerShape(2.dp))); T(t("reports.observed"), size = 8f, w = 700)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(16.dp, 2.dp).background(c.muted)); T(t("reports.expected"), size = 8f, w = 700)
                }
            }
        }

        SectionRow(t("reports.vitals"), rightContent = {
            if (pts.isEmpty()) SimulatedTag() else T(if (week) "7 j" else "24 h", size = 8f, w = 700, color = c.muted)
        })
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            vitals.forEach { v ->
                Card(Modifier.weight(1f), bg = v.bg, radius = 17f, pad = 10f) {
                    Icon(v.icon, 16.dp)
                    T(v.label, Modifier.padding(top = 6.dp), size = 7f, w = 800, maxLines = 1)
                    T(v.value, Modifier.padding(top = 2.dp), size = 15f, w = 800, spacing = -0.5f, maxLines = 1)
                    T(t("reports.avg"), size = 6f, color = c.muted)
                    Spark(v.values, v.col)
                }
            }
        }

        SectionRow(t("reports.milestones"))
        Card(Modifier.fillMaxWidth(), radius = 17f) {
            milestones.forEachIndexed { i, (title, sub, done) ->
                Row(Modifier.fillMaxWidth().heightIn(min = 50.dp).rowDivider(c.line, i < 2).padding(horizontal = 11.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    StepDot(done, i + 1)
                    Column(Modifier.weight(1f)) { T(title, size = 9f, w = 800); T(sub, Modifier.padding(top = 2.dp), size = 7f, color = c.muted) }
                }
            }
        }

        SectionRow(t("reports.appts"))
        appts.forEach { (txt, style) ->
            Card(Modifier.fillMaxWidth().padding(bottom = 8.dp), bg = style.second, radius = 16f, pad = 10f) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconBadge(style.first, c.surface, 32f, 10f)
                    Column(Modifier.weight(1f)) { T(txt[0], size = 9.5f, w = 800); T(txt[1], Modifier.padding(top = 2.dp), size = 7.5f, color = c.muted) }
                    Box(Modifier.background(c.surface, CircleShape).border(1.dp, c.ink, CircleShape).padding(horizontal = 8.dp, vertical = 5.dp)) { T(txt[2], size = 7.5f, w = 800) }
                }
            }
        }

        SectionRow(t("reports.docs"), right = "${docs.size}")
        Card(Modifier.fillMaxWidth(), radius = 17f) {
            docs.forEachIndexed { i, d ->
                Row(Modifier.fillMaxWidth().height(46.dp).rowDivider(c.line, i < docs.lastIndex).padding(horizontal = 11.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(27.dp, 29.dp).background(c.iceBlue, RoundedCornerShape(7.dp)).border(1.dp, c.ink, RoundedCornerShape(7.dp)), contentAlignment = Alignment.Center) { Icon(IconName.file, 16.dp) }
                    T(d, Modifier.weight(1f), size = 9.5f, w = 800)
                    T("›", size = 11f, w = 800)
                }
            }
        }
    }
}

@Composable
fun ProfileScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val profile = useMyProfile().data
    val name = app.session?.user?.fullName ?: ""
    val family = profile?.familyMembers ?: emptyList()
    val tones = listOf("sky", "pink", "yellow", "lavender")

    Screen {
        TopBar(t("profile.top"), back = false, action = { RoundButton(IconName.gear, { app.push(Route.Settings) }) })
        Row(Modifier.fillMaxWidth().height(78.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Avatar(initials(name), 50f)
            Column(Modifier.weight(1f)) {
                T(name, size = 15f, w = 800)
                T(t("profile.dayOf"), Modifier.padding(top = 3.dp), size = 8f, color = c.muted)
            }
            Box(Modifier.background(c.surface, CircleShape).border(1.dp, c.ink, CircleShape).tap { app.push(Route.Settings) }.padding(horizontal = 11.dp, vertical = 7.dp)) { T(t("common.edit"), size = 8f, w = 800) }
        }

        Card(Modifier.fillMaxWidth().padding(bottom = 10.dp), bg = c.ice, radius = 21f, pad = 11f) {
            Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column { T(t("profile.circle"), size = 6f, spacing = 1f); T(t("profile.caregivers"), Modifier.padding(top = 2.dp), size = 12f, w = 800) }
                Box(Modifier.background(c.primary, CircleShape).border(1.dp, c.ink, CircleShape).tap { app.push(Route.FamilyAccess) }.padding(horizontal = 11.dp, vertical = 7.dp)) { T(t("profile.invite"), size = 8f, w = 800, color = Color.White) }
            }
            if (family.isEmpty()) T(t("access.none"), Modifier.padding(vertical = 8.dp), size = 8f, color = c.muted)
            family.forEachIndexed { i, m ->
                Row(Modifier.fillMaxWidth().heightIn(min = 47.dp).rowDivider(c.lineSoft), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Avatar(initials(m.fullName), 31f, toneColor(c, tones[i % tones.size]))
                    Column(Modifier.weight(1f)) { T(m.fullName, size = 8.5f, w = 800); T(m.relationship, Modifier.padding(top = 2.dp), size = 6.5f, color = c.muted) }
                    Chip(if (m.isPrimaryContact) t("access.primary") else t("people.family"), tone = if (m.isPrimaryContact) "blue" else "pink")
                }
            }
            Row(
                Modifier.fillMaxWidth().padding(top = 8.dp).heightIn(min = 46.dp).background(c.surface, RoundedCornerShape(12.dp)).dashedBorderCompat(c.ink).tap { app.push(Route.FamilyAccess) }.padding(horizontal = 8.dp, vertical = 5.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                T("▦", size = 22f)
                Column(Modifier.weight(1f)) { T(t("profile.shareTitle"), size = 8f, w = 800); T(t("profile.shareSub"), Modifier.padding(top = 2.dp), size = 6f, color = c.muted) }
                T("›", w = 800)
            }
        }

        Card(Modifier.fillMaxWidth().padding(bottom = 10.dp), bg = c.mint, radius = 21f, pad = 11f) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column { T(t("profile.assigned"), size = 6f, spacing = 1f); T(t("profile.team"), Modifier.padding(top = 2.dp), size = 12f, w = 800) }
                Chip(t("profile.connected"), tone = "green")
            }
            Row(Modifier.padding(top = 8.dp, bottom = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Avatar("ER", 39f, portrait = true)
                Column {
                    T("Dr. Elena Ruiz", size = 10f, w = 800)
                    T(t("people.surgeon"), Modifier.padding(top = 2.dp), size = 7f)
                    T(t("people.hospital"), Modifier.padding(top = 2.dp), size = 6.5f, color = c.muted)
                }
            }
            Button(t("profile.messageTeam"), { app.push(Route.AIAssistant()) }, Modifier.fillMaxWidth(), secondary = true, icon = IconName.message, flat = true, height = 38f, size = 11f)
        }

        Card(Modifier.fillMaxWidth(), radius = 17f) {
            ListRow(t("profile.privacy"), left = { IconBadge(IconName.shield, border = false) }, onClick = { app.push(Route.Consent) })
            ListRow(t("access.top"), left = { IconBadge(IconName.profile, c.lavender, border = false) }, onClick = { app.push(Route.FamilyAccess) })
            ListRow(t("profile.settings"), left = { IconBadge(IconName.gear, c.yellow, border = false) }, onClick = { app.push(Route.Settings) }, last = true)
        }
    }
}

fun Modifier.dashedBorderCompat(color: Color): Modifier = this.dashedBorder(color, 12.dp)

@Composable
fun TwinDetailScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val items = listOf(
        listOf(t("twinDetail.temperature"), "36.9°C") to (c.yellow to IconName.thermo),
        listOf(t("twinDetail.moisture"), "42%") to (c.pink to IconName.drop),
        listOf(t("twinDetail.redness"), t("twinDetail.low")) to (c.pink to IconName.activity),
        listOf(t("twinDetail.kneeAngle"), "92°") to (c.yellow to IconName.rotate),
    )
    Screen {
        TopBar(t("twinDetail.top"), back = false, action = { RoundButton(IconName.close, { app.pop() }) })
        Box(
            Modifier.fillMaxWidth().height(278.dp).clip(RoundedCornerShape(24.dp)).background(Brush.verticalGradient(listOf(Color(0xFFF8FCFF), Color(0xFFDBEEF9)))).border(1.5.dp, c.ink, RoundedCornerShape(24.dp)),
        ) {
            KneeFigure()
            Chip(t("twinDetail.healing"), Modifier.padding(start = 12.dp, top = 12.dp), tone = "green")
            T(t("common.day") + " 6", Modifier.align(Alignment.TopEnd).padding(end = 12.dp, top = 15.dp), size = 8f, w = 800, color = Color(0xFF1B2A4A))
        }
        Column(
            Modifier.fillMaxWidth().offset(y = (-17).dp).background(c.surface, RoundedCornerShape(topStart = 27.dp, topEnd = 27.dp))
                .border(1.5.dp, c.ink, RoundedCornerShape(topStart = 27.dp, topEnd = 27.dp)).padding(start = 16.dp, end = 16.dp, top = 13.dp, bottom = 30.dp),
        ) {
            Box(Modifier.align(Alignment.CenterHorizontally).padding(bottom = 12.dp).size(42.dp, 4.dp).background(Color(0xFFCBD2DE), RoundedCornerShape(5.dp)))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column { T(t("twinDetail.kicker"), size = 7f, spacing = 1f); T(t("twinDetail.top"), Modifier.padding(top = 2.dp), size = 20f, w = 800) }
                Chip(t("common.onTrack"), tone = "green")
            }
            Spacer(Modifier.height(10.dp))
            items.chunked(2).forEach { row ->
                Row(Modifier.padding(bottom = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { (txt, style) ->
                        Card(Modifier.weight(1f).height(87.dp), bg = style.first, radius = 17f, pad = 10f) {
                            Box(Modifier.fillMaxSize()) {
                                Box(Modifier.align(Alignment.TopEnd)) { Icon(style.second, 18.dp) }
                                Column { T(txt[0], size = 8f, w = 700); T(txt[1], Modifier.padding(top = 12.dp), size = 22f, w = 800) }
                            }
                        }
                    }
                }
            }
            Row(Modifier.fillMaxWidth().padding(top = 6.dp, bottom = 8.dp, start = 2.dp, end = 2.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                T(t("twinDetail.lastPhoto"), size = 11f, w = 800); T(t("twinDetail.when"), size = 7f, color = c.muted)
            }
            Card(Modifier.fillMaxWidth().height(67.dp), bg = c.iceBlue, radius = 15f, pad = 7f) {
                Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.CenterVertically) {
                    WoundThumb(dashed = true)
                    Column(Modifier.weight(1f)) { T(t("twinDetail.normal"), size = 8f, w = 800); T(t("twinDetail.reduced"), Modifier.padding(top = 3.dp), size = 6.5f) }
                    Box(Modifier.background(c.surface, CircleShape).border(1.dp, c.ink, CircleShape).tap { app.push(Route.WoundScan) }.padding(horizontal = 9.dp, vertical = 6.dp)) { T(t("twinDetail.compare"), size = 7f, w = 800) }
                }
            }
            Button(t("twinDetail.scanNow"), { app.push(Route.WoundScan) }, Modifier.padding(top = 14.dp), icon = IconName.camera)
        }
    }
}
