package com.example.moniteur.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.layout.layout
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.moniteur.LocalApp
import com.example.moniteur.Route
import com.example.moniteur.data.Alert
import com.example.moniteur.data.ApiError
import com.example.moniteur.data.FollowedPatient
import com.example.moniteur.data.Mock
import com.example.moniteur.data.initials
import com.example.moniteur.ui.Avatar
import com.example.moniteur.ui.BodyFigure
import com.example.moniteur.ui.Button
import com.example.moniteur.ui.Card
import com.example.moniteur.ui.Chip
import com.example.moniteur.ui.HapticImpact
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconBadge
import com.example.moniteur.ui.IconName
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
import com.example.moniteur.ui.Switch
import com.example.moniteur.ui.T
import com.example.moniteur.ui.Toggle
import com.example.moniteur.ui.TopBar
import com.example.moniteur.ui.TrajectoryChart
import com.example.moniteur.ui.rememberHaptic
import com.example.moniteur.ui.rowDivider
import com.example.moniteur.ui.t
import com.example.moniteur.ui.tap
import com.example.moniteur.ui.theme.Jakarta
import com.example.moniteur.ui.theme.Pal
import com.example.moniteur.ui.tl
import com.example.moniteur.useAlerts
import com.example.moniteur.useFollowedPatient
import kotlinx.coroutines.launch

private const val ACTIVE_ALERT_WINDOW_MS = 6 * 3600 * 1000L

@Composable
private fun alertTitle(a: Alert, patient: FollowedPatient?) = t("alerts.${a.type}") + " · " + (patient?.fullName ?: "")

@Composable
fun FamilyHomeScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val haptic = rememberHaptic()
    val help = remember { mutableStateListOf(false, true, false) }
    var observed by remember { mutableStateOf(false) }
    val tasks = listOf(t("fam.h1") to t("fam.h1s"), t("fam.h2") to t("fam.h2s"), t("fam.h3") to t("fam.h3s"))
    val me = app.session?.user
    val (_, patient) = useFollowedPatient()
    val alerts = useAlerts(patient?.patientId).data

    // L'alerte ouverte la plus grave des dernières heures pilote la carte de statut
    val active = (alerts ?: emptyList()).filter { it.status == "OPEN" && System.currentTimeMillis() - it.epochMs < ACTIVE_ALERT_WINDOW_MS }.maxByOrNull { it.severity }
    val statusBg = if (active == null) c.green else if (active.severity >= 3) Color(0xFFFFD3D3) else c.peach
    val statusIcon = if (active == null) IconName.check else IconName.bell
    val statusTitle = if (active == null) t("common.onTrack") else if (active.severity >= 3) t("fam.statusUrgent") else t("fam.statusAttention")
    val statusSub = if (active == null) t("fam.noUrgent") else t("alerts.${active.type}") + " · " + formatAgo(active.epochMs)
    val urgentTitle = active?.let { alertTitle(it, patient) }

    Column(Modifier.fillMaxSize()) {
        Screen(padded = true, topPad = 0f) {
            Box(Modifier.layoutFullBleed()) { CaregiverBanner() }
            Row(Modifier.fillMaxWidth().height(60.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Avatar(initials(me?.fullName ?: ""), bg = c.sky, online = true)
                Column(Modifier.weight(1f)) { T(t("home.welcome"), size = 9f, color = c.muted); T(t("fam.hi", "name" to (me?.firstName ?: "")), Modifier.padding(top = 2.dp), size = 14f, w = 800) }
                RoundButton(IconName.bell, { app.goFamilyTab(1) }, 35f)
            }
            Row(Modifier.fillMaxWidth().height(72.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Avatar(initials(patient?.fullName ?: "?"), 47f)
                Column {
                    T(t("fam.following"), size = 5.5f, spacing = 0.7f)
                    T(patient?.fullName ?: t("fam.noPatient"), Modifier.padding(vertical = 2.dp), size = 13f, w = 800)
                    T(if (patient != null) patient.relationship + (patient.deviceId?.let { " · $it" } ?: "") else "", size = 6.5f, color = c.muted)
                }
            }
            Card(
                Modifier.fillMaxWidth().heightIn(min = 92.dp).tap(enabled = active != null) {
                    if (active != null) {
                        if (active.severity >= 3) app.push(Route.FamilyUrgent(urgentTitle, active.message)) else app.goFamilyTab(1)
                    }
                },
                bg = statusBg, pad = 12f,
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(11.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(42.dp).background(c.surface, CircleShape).border(1.3.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { Icon(statusIcon, 20.dp) }
                    Column(Modifier.weight(1f)) {
                        T(t("fam.status"), size = 5.5f, spacing = 0.8f, color = Color(0xFF1B2A4A))
                        T(statusTitle, Modifier.padding(vertical = 2.dp), size = 18f, w = 800, color = Color(0xFF1B2A4A))
                        T(statusSub, size = 6.5f, color = Color(0xFF1B2A4A))
                    }
                    if (active != null) T("›", w = 800, color = Color(0xFF1B2A4A))
                }
            }
            Spacer(Modifier.height(10.dp))
            LiveVitalsCard(patient?.patientId, patient?.deviceId)

            Row(Modifier.padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Card(Modifier.weight(1f).height(130.dp), bg = c.pink, pad = 12f) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { T(t("home.woundTemp"), Modifier.weight(1f), size = 7.5f, w = 800, spacing = 0.7f); SimulatedTag() }
                    T("${Mock.woundTemp}", Modifier.padding(top = 5.dp), size = 31f, w = 800, spacing = -1.6f, suffix = "°C", suffixSize = 12f)
                    T(t("home.normal"), size = 7.5f, color = c.muted)
                    MiniBars()
                }
                Card(Modifier.weight(1f).height(130.dp), bg = c.yellow, pad = 12f) {
                    T(t("home.pain"), size = 7.5f, w = 800, spacing = 0.7f)
                    T("${Mock.pain}", Modifier.padding(top = 5.dp), size = 31f, w = 800, spacing = -1.6f, suffix = "/10", suffixSize = 12f)
                    T(t("fam.sharedBy"), size = 7.5f, color = c.muted)
                    MiniLine()
                }
            }

            Row(
                Modifier.fillMaxWidth().padding(top = 9.dp).height(57.dp).background(c.surface, RoundedCornerShape(14.dp)).border(1.2.dp, c.ink, RoundedCornerShape(14.dp)).tap { app.push(Route.FamilyInfo) }.padding(horizontal = 9.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(Modifier.size(25.dp).background(c.green, CircleShape), contentAlignment = Alignment.Center) { Icon(IconName.check, 16.dp) }
                Column(Modifier.weight(1f)) { T(t("fam.latest"), size = 5.5f, color = c.muted); T(t("fam.latestTitle"), Modifier.padding(top = 3.dp), size = 8f, w = 800) }
                T("›", w = 800)
            }

            SectionRow(t("fam.help"))
            Card(Modifier.fillMaxWidth(), radius = 17f) {
                tasks.forEachIndexed { i, (title, sub) ->
                    Row(Modifier.fillMaxWidth().heightIn(min = 54.dp).rowDivider(c.line, i < 2).padding(horizontal = 10.dp), horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.CenterVertically) {
                        IconBadge(listOf(IconName.activity, IconName.pill, IconName.calendar)[i], listOf(c.sky, c.lavender, c.yellow)[i], 30f)
                        Column(Modifier.weight(1f)) { T(title, size = 8.5f, w = 800); T(sub, Modifier.padding(top = 2.dp), size = 6.5f, color = c.muted) }
                        Box(Modifier.background(if (help[i]) c.green else c.primary, CircleShape).border(1.dp, c.ink, CircleShape).tap { haptic(HapticImpact); help[i] = !help[i] }.padding(horizontal = 10.dp, vertical = 6.dp)) {
                            T(if (help[i]) t("fam.confirmed") else t("fam.willHelp"), size = 7.5f, w = 800, color = if (help[i]) c.text else Color.White)
                        }
                    }
                }
            }

            Row(
                Modifier.fillMaxWidth().padding(top = 9.dp).heightIn(min = 50.dp).background(c.amber, RoundedCornerShape(14.dp)).dashedBorderCompat(c.ink).tap { haptic(HapticImpact); observed = true }.padding(horizontal = 10.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(IconName.message, 18.dp)
                if (observed) T(t("fam.observeSent"), Modifier.weight(1f), size = 8.5f, w = 800)
                else Column(Modifier.weight(1f)) { T(t("fam.observe"), size = 8.5f, w = 800); T(t("fam.observeSub"), Modifier.padding(top = 2.dp), size = 6.5f, color = c.muted) }
            }

            Column(Modifier.fillMaxWidth().padding(top = 9.dp).background(c.readonly, RoundedCornerShape(14.dp)).border(1.2.dp, c.ink, RoundedCornerShape(14.dp)).padding(horizontal = 10.dp, vertical = 8.dp)) {
                T(t("fam.readonly"), Modifier.padding(bottom = 4.dp), size = 5.5f, w = 800, spacing = 0.8f)
                listOf(t("fam.plan") to t("fam.viewOnly"), t("fam.meds") to t("fam.noChanges"), t("fam.checkins") to t("fam.sarahAnswers")).forEach { (a, b) ->
                    Row(Modifier.fillMaxWidth().height(24.dp).topLine(c.line), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { T(a, size = 7f); T(b, size = 6.5f, w = 800, color = c.muted) }
                }
            }
            T(t("fam.caregiverNote"), Modifier.fillMaxWidth().padding(top = 10.dp), size = 6.5f, color = c.muted, center = true)
        }
    }
}

/** Le bandeau reste pleine largeur malgré la gouttière de l'écran. */
private fun Modifier.layoutFullBleed(): Modifier = this.then(
    Modifier.layout { measurable, constraints ->
        val extra = 32.dp.roundToPx()
        val p = measurable.measure(constraints.copy(minWidth = constraints.maxWidth + extra, maxWidth = constraints.maxWidth + extra))
        layout(constraints.maxWidth, p.height) { p.place(-16.dp.roundToPx(), 0) }
    },
)

private fun Modifier.topLine(color: Color): Modifier = this.drawBehind { drawLine(color, Offset(0f, 0f), Offset(size.width, 0f), 1.dp.toPx()) }

@Composable
fun UpdatesScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val (_, patient) = useFollowedPatient()
    val poll = useAlerts(patient?.patientId)
    val alerts = poll.data
    val ctxTitles = patient?.fullName ?: ""
    val typeNames = mapOf("FALL" to t("alerts.FALL"), "TACHYCARDIA" to t("alerts.TACHYCARDIA"), "BRADYCARDIA" to t("alerts.BRADYCARDIA"), "HYPOXIA" to t("alerts.HYPOXIA"))
    fun toneBg(sev: Int) = when (sev) { 1 -> c.green; 2 -> Color(0xFFFFE1B8); else -> Color(0xFFFFD3D3) }

    Screen {
        TopBar(t("updates.top"), back = false, action = { RoundButton(IconName.bell, { app.push(Route.LockPreview("attention")) }) })
        PageTitle(t("updates.title"), size = 26f)
        Muted(if (patient != null) patient.fullName + " · " + t("updates.sub") else t("updates.sub"))
        Card(Modifier.fillMaxWidth(), radius = 19f) {
            if (poll.loading && alerts == null) Box(Modifier.fillMaxWidth().padding(20.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(Modifier.size(24.dp), color = c.primary, strokeWidth = 2.dp) }
            if (poll.error != null && alerts == null) T(t("live.offline"), Modifier.padding(12.dp), size = 8.5f, w = 700, color = c.urgentText)
            if (alerts?.isEmpty() == true) T(t("updates.empty"), Modifier.padding(12.dp), size = 8.5f, color = c.muted)
            alerts?.forEachIndexed { i, a ->
                val urgent = a.severity >= 3
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 76.dp).rowDivider(c.line, i < alerts.lastIndex)
                        .tap(enabled = urgent) { app.push(Route.FamilyUrgent((typeNames[a.type] ?: a.type) + " · " + ctxTitles, a.message)) }.padding(9.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    T(formatAgo(a.epochMs), Modifier.width(56.dp), size = 6.5f, color = c.muted)
                    Box(Modifier.padding(end = 10.dp).size(31.dp).background(toneBg(a.severity), RoundedCornerShape(9.dp)).border(1.dp, c.ink, RoundedCornerShape(9.dp)), contentAlignment = Alignment.Center) { Icon(alertIcon(a.type), 17.dp, Color(0xFF1B2A4A)) }
                    Column(Modifier.weight(1f)) {
                        T(t("alerts.${a.type}") + " · " + t("alerts.severity", "n" to a.severity), size = 8.5f, w = 800)
                        T(a.message, Modifier.padding(top = 2.dp), size = 7.5f, lh = 1.4f, color = c.muted)
                    }
                    if (urgent) T("›", w = 800)
                }
            }
        }
        SectionRow(t("updates.previewsSub"), kicker = t("updates.previews"))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf(Triple("info", t("lock.info"), c.sky), Triple("attention", t("lock.attention"), c.review), Triple("urgent", t("lock.urgent"), c.urgent)).forEach { (tone, label, bg) ->
                Card(Modifier.weight(1f).height(70.dp).tap { app.push(Route.LockPreview(tone)) }, bg = bg, radius = 15f, pad = 10f) {
                    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.SpaceBetween) {
                        Icon(if (tone == "info") IconName.check else IconName.bell, 18.dp, Color(0xFF1B2A4A))
                        T(label, size = 8.5f, w = 800, color = Color(0xFF1B2A4A))
                    }
                }
            }
        }
    }
}

@Composable
fun FamilyRecoveryScreen() {
    val c = Pal.c
    Screen(topPad = 0f) {
        Box(Modifier.layoutFullBleed()) { CaregiverBanner() }
        TopBar(t("famRecovery.top"), back = false)
        PageTitle(t("famRecovery.title"), Modifier.padding(bottom = 9.dp), size = 26f)
        Chip(t("famRecovery.shared"), Modifier.padding(bottom = 10.dp), tone = "lavender")
        Card(Modifier.fillMaxWidth().height(116.dp), radius = 20f, pad = 10f) {
            Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                ScoreRing(Mock.score, label = t("famRecovery.score"))
                Column(Modifier.weight(1f)) { T(t("famRecovery.onTrack"), size = 10f, w = 800); T(t("fam.surgery"), Modifier.padding(top = 3.dp), size = 7f, color = c.muted) }
            }
        }
        SectionRow(t("famRecovery.twin"))
        Row(
            Modifier.fillMaxWidth().height(200.dp).clip(RoundedCornerShape(22.dp)).background(Brush.linearGradient(listOf(Color(0xFFF8FCFF), Color(0xFFDBEEF9), Color(0xFFE6DEF8)), Offset.Zero, Offset.Infinite)).border(1.5.dp, c.ink, RoundedCornerShape(22.dp)),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.width(120.dp), contentAlignment = Alignment.Center) { BodyFigure(92f, 190f) }
            Column(Modifier.weight(1f).padding(end = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Chip(t("common.onTrack") + " ✓", tone = "green")
                T(t("famRecovery.twinSub"), size = 11f, w = 800, color = Color(0xFF1B2A4A))
                Row(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(IconName.camera, 13.dp, Color(0xFF64718A)); T(t("famRecovery.hidden"), Modifier.weight(1f), size = 7f, color = Color(0xFF64718A))
                }
            }
        }
        Card(Modifier.fillMaxWidth().padding(top = 10.dp), bg = c.green, radius = 18f, pad = 11f) {
            T(t("twin.expVsActual"), size = 6.5f, w = 800)
            TrajectoryChart(80f)
        }
        SectionRow(t("famRecovery.milestones"))
        Card(Modifier.fillMaxWidth(), radius = 17f) {
            listOf(Triple(t("reports.ms1"), t("reports.ms1s"), true), Triple(t("reports.ms2"), t("reports.ms2s"), false), Triple(t("reports.ms3"), t("reports.ms3s"), false)).forEachIndexed { i, (title, sub, done) ->
                Row(Modifier.fillMaxWidth().heightIn(min = 48.dp).rowDivider(c.line, i < 2).padding(horizontal = 11.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    StepDot(done, i + 1)
                    Column(Modifier.weight(1f)) { T(title, size = 9f, w = 800); T(sub, Modifier.padding(top = 2.dp), size = 7f, color = c.muted) }
                }
            }
        }
        SectionRow(t("famRecovery.appts"))
        listOf(Triple(t("reports.a1"), t("reports.a1d"), c.lavender), Triple(t("reports.a3"), t("reports.a3d"), c.sky)).forEach { (title, date, bg) ->
            Card(Modifier.fillMaxWidth().padding(bottom = 8.dp), bg = bg, radius = 16f, pad = 10f) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconBadge(IconName.calendar, c.surface, 30f)
                    T(title, Modifier.weight(1f), size = 9.5f, w = 800); T(date, size = 8f, w = 800)
                }
            }
        }
    }
}

@Composable
fun FamilyProfileScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val (_, patient) = useFollowedPatient()
    val name = app.session?.user?.fullName ?: ""
    val toggles = remember { mutableStateListOf(true, true, true, true) }
    val rows = listOf(t("famProfile.n1") to t("famProfile.n1s"), t("famProfile.n2") to t("famProfile.n2s"), t("famProfile.n3") to t("famProfile.n3s"), t("famProfile.n4") to t("famProfile.n4s"))
    val icons = listOf(IconName.checkin, IconName.profile, IconName.bell, IconName.calendar)

    Screen {
        TopBar(t("famProfile.top"), back = false, action = { RoundButton(IconName.gear, { app.push(Route.Settings) }) })
        Row(Modifier.fillMaxWidth().height(78.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Avatar(initials(name), 50f, c.sky)
            Column(Modifier.weight(1f)) {
                T(name, size = 15f, w = 800)
                T(if (patient != null) t("people.caregiver") + " · " + patient.relationship else t("people.caregiver"), Modifier.padding(top = 3.dp), size = 8f, color = c.muted)
            }
        }
        Card(Modifier.fillMaxWidth(), bg = c.ice, radius = 19f, pad = 11f) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Avatar(initials(patient?.fullName ?: "?"), 41f)
                Column(Modifier.weight(1f)) {
                    T(t("famProfile.following"), size = 6f, spacing = 1f)
                    T(patient?.fullName ?: t("fam.noPatient"), Modifier.padding(top = 2.dp), size = 11f, w = 800)
                    T((if (patient?.isPrimaryContact == true) t("access.primary") else "") + (if (patient?.whatsappOptIn == true) " · WhatsApp" else ""), Modifier.padding(top = 2.dp), size = 7f, color = c.muted)
                }
            }
        }
        T(t("famProfile.notif"), Modifier.padding(start = 2.dp, top = 14.dp, bottom = 6.dp), size = 6f, w = 800, spacing = 0.8f)
        Card(Modifier.fillMaxWidth(), radius = 17f) {
            rows.forEachIndexed { i, (title, sub) ->
                ListRow(title, left = { IconBadge(icons[i]) }, sub = sub, last = i == rows.lastIndex, right = { Switch(toggles[i], { toggles[i] = !toggles[i] }) })
            }
        }
        Card(Modifier.fillMaxWidth().padding(top = 10.dp), radius = 17f) {
            ListRow(t("profile.settings"), left = { IconBadge(IconName.gear, c.yellow) }, onClick = { app.push(Route.Settings) }, last = true)
        }
        Button(t("famProfile.leave"), { app.signOut() }, Modifier.padding(top = 14.dp), secondary = true)
    }
}

/** Rejoindre un patient avec son code à 6 chiffres (scan QR remplacé par la saisie du code). */
@Composable
fun JoinPatientScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val scope = rememberCoroutineScope()
    val haptic = rememberHaptic()
    val relations = tl("join.relations")
    var relation by remember { mutableStateOf(relations.first()) }
    var code by remember { mutableStateOf("") }
    var linking by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var joined by remember { mutableStateOf<FollowedPatient?>(null) }
    val focus = remember { FocusRequester() }
    val networkMsg = t("auth.network")

    fun link(value: String) {
        linking = true; error = null
        scope.launch {
            try {
                // WhatsApp seulement si le compte a un numéro (l'API refuse sinon)
                joined = app.api.linkPatient(value, relation, app.session?.user?.whatsappNumber != null)
                haptic(HapticImpact)
            } catch (e: ApiError) {
                if (e.status == 409) joined = runCatching { app.api.followedPatients().firstOrNull() }.getOrNull()
                else error = if (e.status != 0) e.message else networkMsg
            } finally { linking = false }
        }
    }
    LaunchedEffect(code) { if (code.length == 6 && joined == null && !linking) link(code) }

    Screen(Modifier.imePadding()) {
        TopBar(t("join.top"), onBack = { app.signOut() })
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
            Box(Modifier.padding(top = 4.dp).size(56.dp).background(c.lavender, RoundedCornerShape(17.dp)).border(1.5.dp, c.ink, RoundedCornerShape(17.dp)), contentAlignment = Alignment.Center) { Icon(IconName.scan, 30.dp) }
            PageTitle(t("join.title"), Modifier.padding(top = 10.dp, bottom = 9.dp), center = true)
            Muted(t("join.sub"), center = true)
        }
        Column(
            Modifier.fillMaxWidth().height(205.dp).background(c.iceBlue, RoundedCornerShape(22.dp)).dashedBorderCompat(c.ink),
            horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
        ) {
            Box(Modifier.size(104.dp).background(Color.White, RoundedCornerShape(15.dp)), contentAlignment = Alignment.Center) { Corners(Color(0xFF1E88E5), 26.dp, 88.dp, 88.dp); Icon(IconName.camera, 25.dp, Color(0xFF1B2A4A)) }
            T(t("join.scan"), Modifier.padding(top = 9.dp), size = 11f, w = 800)
            T(t("join.scanSub"), Modifier.padding(top = 3.dp), size = 7f, color = c.muted)
        }
        T(t("join.relation"), Modifier.padding(top = 14.dp, bottom = 6.dp), size = 7f, w = 800, spacing = 0.8f)
        Toggle(relations, relation) { relation = it }
        Row(Modifier.fillMaxWidth().height(37.dp), horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f).height(1.dp).background(Color(0xFFCCD3DE))); T(t("join.or"), size = 6.5f, color = c.muted); Box(Modifier.weight(1f).height(1.dp).background(Color(0xFFCCD3DE)))
        }
        Box(Modifier.fillMaxWidth().tap { focus.requestFocus() }) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                for (i in 0 until 6) {
                    val on = code.length == i
                    Box(
                        Modifier.weight(1f).height(47.dp).background(c.surface, RoundedCornerShape(11.dp))
                            .border(if (on) 2.dp else 1.3.dp, if (error != null) c.urgent else if (on) c.primary else c.ink, RoundedCornerShape(11.dp)),
                        contentAlignment = Alignment.Center,
                    ) { T(code.getOrNull(i)?.toString() ?: "", size = 16f, w = 800) }
                }
            }
            BasicTextField(
                code, { error = null; code = it.filter(Char::isDigit).take(6) }, enabled = joined == null && !linking,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                textStyle = TextStyle(color = Color.Transparent, fontSize = 1.sp), cursorBrush = SolidColor(Color.Transparent),
                modifier = Modifier.size(1.dp).alpha(0f).focusRequester(focus),
            )
        }
        if (linking) Box(Modifier.fillMaxWidth().padding(top = 10.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(Modifier.size(22.dp), color = c.primary, strokeWidth = 2.dp) }
        if (error != null) T(error!!, Modifier.padding(top = 6.dp), size = 8f, w = 700, color = c.urgentText)
        joined?.let { j ->
            Row(
                Modifier.fillMaxWidth().padding(top = 12.dp).heightIn(min = 96.dp).background(c.green, RoundedCornerShape(18.dp)).border(1.4.dp, c.ink, RoundedCornerShape(18.dp)).padding(11.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Box(Modifier.size(34.dp).background(c.surface, CircleShape).border(1.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { Icon(IconName.check, 22.dp) }
                Column(Modifier.weight(1f)) {
                    T(t("join.connected"), size = 5.5f, spacing = 0.7f)
                    T(t("join.following", "name" to j.fullName), Modifier.padding(vertical = 3.dp), size = 10f, w = 800)
                    T(t("join.followingSub"), size = 6.5f, lh = 1.4f)
                }
            }
        }
        Button(t("join.go") + "  →", { if (joined != null) app.completeOnboarding() else focus.requestFocus() }, Modifier.padding(top = 12.dp).alpha(if (joined != null) 1f else 0.5f))
    }
}

@Composable
fun LockPreviewScreen(tone: String) {
    val app = LocalApp.current
    val (title, line1, line2, time) = when (tone) {
        "info" -> listOf(t("lock.info"), t("lock.infoT"), t("lock.infoC"), t("lock.now"))
        "attention" -> listOf(t("lock.attention"), t("lock.attT"), t("lock.attC"), t("lock.ago"))
        else -> listOf(t("lock.urgent"), t("lock.urgT"), t("lock.urgC"), t("lock.now"))
    }
    val markBg = when (tone) { "info" -> Color(0xFF1E88E5); "attention" -> Color(0xFFFFB347); else -> Color(0xFFFF6B6B) }
    val ink = Color(0xFF1B2A4A)
    val colors = if (tone == "urgent") listOf(Color(0xFFF7B5B5), Color(0xFFE87979)) else listOf(Color(0xFFB7DFF4), Color(0xFFD8CDF8), Color(0xFFF2D8EA))
    Column(Modifier.fillMaxSize().background(Brush.linearGradient(colors, Offset.Zero, Offset.Infinite)).statusBarsPadding().navigationBarsPadding().padding(horizontal = 18.dp)) {
        Box(Modifier.align(Alignment.End).padding(top = 6.dp).tap { app.pop() }.padding(6.dp)) { Icon(IconName.close, 22.dp, Color(0xFF17223C)) }
        Column(Modifier.fillMaxWidth().padding(top = 20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            T("12:41", size = 68f, w = 800, spacing = -4f, color = Color(0xFF17223C), lh = 1.05f)
            T(t("lock.date"), Modifier.padding(top = 8.dp), size = 13f, w = 700, color = Color(0xFF17223C))
        }
        Row(
            Modifier.fillMaxWidth().padding(top = 90.dp).heightIn(min = 145.dp).background(Color(0xC7FFFFFF), RoundedCornerShape(21.dp)).border(1.dp, Color(0x591B2A4A), RoundedCornerShape(21.dp))
                .tap {
                    app.replace(
                        when (tone) {
                            "info" -> Route.FamilyInfo
                            "attention" -> Route.FamilyAttention
                            else -> Route.FamilyUrgent()
                        },
                    )
                }.padding(13.dp),
            horizontalArrangement = Arrangement.spacedBy(9.dp),
        ) {
            Box(Modifier.size(37.dp).background(markBg, RoundedCornerShape(10.dp)).border(1.2.dp, ink, RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) { Icon(if (tone == "info") IconName.check else IconName.bell, 18.dp, if (tone == "attention") ink else Color.White) }
            Column(Modifier.weight(1f)) {
                T(t("lock.app") + " · " + time, size = 6f, color = Color(0xFF536078))
                T(title, Modifier.padding(top = 6.dp), size = 8f, w = 800, upper = true, color = ink)
                T(line1, Modifier.padding(top = 3.dp), size = 11f, w = 800, lh = 1.35f, color = ink)
                T(line2, Modifier.padding(top = 4.dp), size = 7f, lh = 1.4f, color = Color(0xFF59677E))
            }
        }
        Spacer(Modifier.weight(1f))
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
            listOf(IconName.camera, IconName.activity).forEach { Box(Modifier.size(43.dp).background(Color(0x521B2A4A), CircleShape), contentAlignment = Alignment.Center) { Icon(it, 19.dp, Color.White) } }
        }
        T(t("lock.swipe"), Modifier.fillMaxWidth().padding(bottom = 14.dp), size = 7f, color = Color.White, center = true)
    }
}

@Composable
private fun useAck(): Pair<Boolean, () -> Unit> {
    val app = LocalApp.current
    val haptic = rememberHaptic()
    var seen by remember { mutableStateOf(false) }
    return seen to { haptic(HapticImpact); seen = true; app.familyAck = true }
}

@Composable
fun FamilyInfoScreen() {
    val c = Pal.c
    val (seen, mark) = useAck()
    val rows = listOf(Triple(IconName.checkin, t("info.pain"), t("info.painV")), Triple(IconName.activity, t("info.symptoms"), t("info.noNew")), Triple(IconName.check, t("info.status"), t("common.onTrack")))
    Screen {
        TopBar(t("info.top"))
        Box(Modifier.align(Alignment.CenterHorizontally).padding(top = 34.dp, bottom = 12.dp).size(70.dp).background(c.sky, CircleShape).border(1.5.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { Icon(IconName.check, 27.dp) }
        Chip(t("info.chip"), Modifier.align(Alignment.CenterHorizontally), tone = "blue")
        PageTitle(t("info.title"), center = true, size = 26f)
        Muted(t("info.when"), center = true)
        Card(Modifier.fillMaxWidth().padding(top = 16.dp, bottom = 12.dp), radius = 18f) {
            rows.forEachIndexed { i, (icon, k, v) ->
                Row(Modifier.fillMaxWidth().height(68.dp).rowDivider(c.line, i < 2).padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(11.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(33.dp).background(c.blue, RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) { Icon(icon) }
                    Column { T(k, size = 5.5f, spacing = 0.7f); T(v, Modifier.padding(top = 3.dp), size = 9f, w = 800) }
                }
            }
        }
        Card(Modifier.fillMaxWidth().padding(bottom = 24.dp).heightIn(min = 72.dp), bg = c.green, radius = 15f, pad = 11f) {
            T(t("info.good"), size = 9f, w = 800); T(t("info.routine"), Modifier.padding(top = 4.dp), size = 7f, lh = 1.5f)
        }
        Button(if (seen) t("common.seenDone") + " ✓" else t("common.seen"), mark)
    }
}

@Composable
fun FamilyAttentionScreen() {
    val c = Pal.c
    val ctx = LocalContext.current
    val (seen, mark) = useAck()
    val signals = listOf(Triple(IconName.sensor, t("attention.s1"), t("attention.s1s")), Triple(IconName.camera, t("attention.s2"), t("attention.s2s")), Triple(IconName.checkin, t("attention.s3"), t("attention.s3s")))
    Screen {
        TopBar(t("attention.top"))
        Row(Modifier.fillMaxWidth().heightIn(min = 112.dp).background(c.peach, RoundedCornerShape(19.dp)).border(1.5.dp, c.review, RoundedCornerShape(19.dp)).padding(12.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Box(Modifier.size(39.dp).background(c.review, RoundedCornerShape(11.dp)).border(1.2.dp, c.ink, RoundedCornerShape(11.dp)), contentAlignment = Alignment.Center) { Icon(IconName.thermo, 24.dp, Color(0xFF1B2A4A)) }
            Column(Modifier.weight(1f)) {
                T(t("attention.kicker"), size = 5.5f, spacing = 0.7f, color = c.reviewText)
                T(t("attention.title"), Modifier.padding(vertical = 3.dp), size = 11f, w = 800, lh = 1.35f)
                T(t("attention.sub"), size = 6.5f)
            }
        }
        Card(Modifier.fillMaxWidth().padding(top = 9.dp), radius = 17f, pad = 10f) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column { T(t("attention.changed"), size = 5.5f); T(t("attention.rose"), Modifier.padding(top = 2.dp), size = 9f, w = 800) }
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) { SimulatedTag(); Chip(t("attention.since"), tone = "yellow") }
            }
            MiniLine(color = Color(0xFFEF695D), fill = true, height = 51f)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column { T("7:30 AM", size = 5.5f); T("36.9°C", Modifier.padding(top = 2.dp), size = 9f, w = 800) }
                T("→", w = 800)
                Column { T("10:06 AM", size = 5.5f); T("38.2°C", Modifier.padding(top = 2.dp), size = 9f, w = 800) }
            }
        }
        Card(Modifier.fillMaxWidth().padding(top = 9.dp), radius = 17f, pad = 10f) {
            T(t("attention.signals"), size = 5.5f, w = 800, spacing = 0.7f)
            signals.forEach { (icon, title, sub) ->
                Row(Modifier.fillMaxWidth().padding(top = 4.dp).height(48.dp).topLine(c.line), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(27.dp).background(c.iceBlue, RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) { Icon(icon, 17.dp) }
                    Column(Modifier.weight(1f)) { T(title, size = 7.5f, w = 800); T(sub, Modifier.padding(top = 2.dp), size = 6f, color = c.muted) }
                    Icon(IconName.check, 16.dp, c.trackText)
                }
            }
        }
        Row(Modifier.padding(vertical = 9.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            Button(t("common.callSarah"), { callNumber(ctx, "+10000000001") }, Modifier.weight(0.8f), icon = IconName.phone, flat = true, height = 43f, size = 9f)
            Button(t("attention.surgeon"), { callNumber(ctx, "+10000000002") }, Modifier.weight(1.2f), secondary = true, icon = IconName.phone, flat = true, height = 43f, size = 9f)
        }
        Button(if (seen) t("common.acknowledged") + " ✓" else t("common.seen"), mark)
    }
}

/** Alerte urgente plein écran rouge : réelle (titre/message de l'API) ou démo. */
@Composable
fun FamilyUrgentScreen(title: String?, message: String?) {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val (seen, mark) = useAck()
    val ink = Color(0xFF1B2A4A)
    Screen(bg = Color(0xFFFF6B6B), horizontalPad = 20f, topPad = 13f) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            RoundButton(IconName.close, { app.pop() }, bg = Color(0xB3FFFFFF)); Chip(t("urgent.chip")); Spacer(Modifier.width(38.dp))
        }
        Box(Modifier.align(Alignment.CenterHorizontally).padding(top = 56.dp, bottom = 20.dp).size(92.dp).background(Color.White, CircleShape).border(2.dp, ink, CircleShape), contentAlignment = Alignment.Center) { T("!", size = 50f, w = 800, color = ink) }
        T(title ?: t("urgent.title"), Modifier.fillMaxWidth(), size = 27f, w = 800, center = true, spacing = -1f, color = ink, lh = 1.2f)
        T(message ?: t("urgent.body"), Modifier.fillMaxWidth().padding(top = 14.dp, bottom = 22.dp, start = 16.dp, end = 16.dp), size = 10f, w = 600, center = true, lh = 1.5f, color = ink)
        Column(Modifier.fillMaxWidth().background(Color(0xC7FFFFFF), RoundedCornerShape(16.dp)).border(1.5.dp, ink, RoundedCornerShape(16.dp)).padding(12.dp)) {
            T(t("urgent.act"), size = 11f, w = 800, color = ink); T(t("urgent.actSub"), Modifier.padding(top = 4.dp), size = 7f, lh = 1.45f, color = ink)
        }
        Column(Modifier.padding(top = 18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(t("urgent.emergency"), { callNumber(ctx, "112") }, Modifier.fillMaxWidth(), icon = IconName.phone, flat = true, color = ink)
            Button(t("common.callSarah"), { callNumber(ctx, "+10000000001") }, Modifier.fillMaxWidth(), icon = IconName.phone, flat = true, secondary = true, color = Color.White, textColor = ink)
            Button(if (seen) t("urgent.waySeen") else t("urgent.way"), mark, Modifier.fillMaxWidth(), flat = true, secondary = true, color = Color.White, textColor = ink)
        }
        Row(Modifier.align(Alignment.CenterHorizontally).padding(top = 16.dp).tap { mark() }, horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(IconName.check, 16.dp, ink); T(if (seen) t("common.acknowledged") else t("common.seen"), size = 8f, w = 800, color = ink, underline = true)
        }
    }
}
