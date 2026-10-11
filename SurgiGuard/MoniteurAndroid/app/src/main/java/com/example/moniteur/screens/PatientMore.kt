package com.example.moniteur.screens

import android.content.Intent
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import com.example.moniteur.LocalApp
import com.example.moniteur.Route
import com.example.moniteur.data.ApiError
import com.example.moniteur.data.ChatMessage
import com.example.moniteur.data.Mock
import com.example.moniteur.data.initials
import com.example.moniteur.ui.ArcGauge
import com.example.moniteur.ui.Avatar
import com.example.moniteur.ui.Button
import com.example.moniteur.ui.Card
import com.example.moniteur.ui.Chip
import com.example.moniteur.ui.HapticImpact
import com.example.moniteur.ui.HapticTick
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconBadge
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.MiniLine
import com.example.moniteur.ui.Muted
import com.example.moniteur.ui.PageTitle
import com.example.moniteur.ui.RoundButton
import com.example.moniteur.ui.Screen
import com.example.moniteur.ui.ScoreRing
import com.example.moniteur.ui.SectionRow
import com.example.moniteur.ui.SimulatedTag
import com.example.moniteur.ui.Switch
import com.example.moniteur.ui.SvgCanvas
import com.example.moniteur.ui.T
import com.example.moniteur.ui.Toggle
import com.example.moniteur.ui.TopBar
import com.example.moniteur.ui.WoundThumb
import com.example.moniteur.ui.rememberHaptic
import com.example.moniteur.ui.rowDivider
import com.example.moniteur.ui.svgPath
import com.example.moniteur.ui.t
import com.example.moniteur.ui.tap
import com.example.moniteur.ui.theme.Jakarta
import com.example.moniteur.ui.theme.Pal
import com.example.moniteur.ui.theme.fs
import com.example.moniteur.ui.tl
import com.example.moniteur.ui.toneColor
import com.example.moniteur.useMyProfile
import com.example.moniteur.usePolling
import com.example.moniteur.alarm.MedAlarms
import com.example.moniteur.alarm.localAsOf
import com.example.moniteur.data.Dose
import java.time.LocalDate
import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.mutableStateMapOf
import androidx.core.content.ContextCompat
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Aspect « caméra indisponible » : peau + plaie (dégradés radiaux). */
@Composable
private fun MockSkin(modifier: Modifier) {
    Canvas(modifier) {
        drawRect(Brush.radialGradient(0f to Color(0xFFE4B39D), 0.45f to Color(0xFFC58E7E), 0.78f to Color(0xFF34475A), 1f to Color(0xFF273748), center = center, radius = size.maxDimension * 0.7f))
        val cx = size.width / 2
        val cy = size.height * 0.4f
        drawOval(
            Brush.radialGradient(0.1f to Color(0xFFA54C48), 0.25f to Color(0xFFDB746B), 0.45f to Color(0xFFE9A08F), 0.47f to Color(0x00E9A08F), center = Offset(cx, cy), radius = 68.dp.toPx()),
            Offset(cx - 68.dp.toPx(), cy - 30.dp.toPx()), Size(136.dp.toPx(), 60.dp.toPx()),
        )
    }
}

@Composable
private fun WoundHalf(label: String, today: Boolean, modifier: Modifier) {
    Box(modifier.background(if (today) Color(0xFFE2B29C) else Color(0xFFDCA892)), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(if (today) 60.dp else 76.dp, 27.dp).alpha(if (today) 0.76f else 1f).rotate(-6f)) {
            drawRect(Brush.radialGradient(0f to Color(0xFFA34F49), 0.35f to Color(0xFFDC7A6D), 0.67f to Color(0x00DC7A6D), center = center, radius = size.width / 2))
        }
        T(label, Modifier.align(Alignment.TopStart).padding(6.dp), size = 6f, w = 800, color = Color.White)
    }
}

@Composable
private fun Ripple(inset: Int, delayMs: Int) {
    val t = rememberInfiniteTransition(label = "ripple")
    val p by t.animateFloat(0f, 1f, infiniteRepeatable(tween(1800, delayMillis = delayMs, easing = LinearEasing), RepeatMode.Restart), label = "p")
    Box(Modifier.fillMaxSize().padding(inset.dp).scale(0.85f + p * 0.25f).alpha(1f - p * 0.6f).border(1.dp, Color(0xFF9679E2), CircleShape))
}

@Composable
fun SensingRequestScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val steps = tl("sensing.steps")
    Box(Modifier.fillMaxSize().background(c.scrim).statusBarsPadding().navigationBarsPadding().padding(20.dp), contentAlignment = Alignment.Center) {
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).background(c.lilacBg, RoundedCornerShape(27.dp)).border(1.5.dp, c.ink, RoundedCornerShape(27.dp)).padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Box(Modifier.align(Alignment.End).offset(x = 7.dp, y = (-7).dp).size(30.dp).background(c.surface, CircleShape).border(1.2.dp, c.ink, CircleShape).tap { app.pop() }, contentAlignment = Alignment.Center) { Icon(IconName.close, 20.dp) }
            Box(Modifier.size(95.dp), contentAlignment = Alignment.Center) {
                Ripple(0, 0); Ripple(10, 500)
                Box(Modifier.size(51.dp).background(c.surface, RoundedCornerShape(17.dp)).border(1.5.dp, c.ink, RoundedCornerShape(17.dp)), contentAlignment = Alignment.Center) { Icon(IconName.sensor, 28.dp) }
            }
            Row(Modifier.padding(top = 3.dp), horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) { Chip(t("sensing.chip"), tone = "lavender"); SimulatedTag() }
            T(t("sensing.title"), Modifier.padding(top = 10.dp), size = 22f, w = 800, center = true, spacing = -0.7f, lh = 1.18f)
            T(t("sensing.body"), Modifier.padding(top = 9.dp, bottom = 14.dp, start = 5.dp, end = 5.dp), size = 10f, center = true, lh = 1.5f, color = c.muted)
            Button(t("sensing.photo"), { app.replace(Route.WoundScan) }, Modifier.fillMaxWidth(), icon = IconName.camera, flat = true, height = 45f)
            Button(t("common.later"), { app.pop() }, Modifier.fillMaxWidth().padding(top = 8.dp), secondary = true, flat = true, height = 45f)
            Column(Modifier.fillMaxWidth().padding(top = 16.dp).rowDividerTop(Color(0xFFC6BFDC)).padding(top = 12.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { T(t("sensing.evidence"), size = 8f, w = 800); T(t("sensing.count"), size = 8f) }
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    steps.forEachIndexed { i, s ->
                        Column(Modifier.width(62.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Box(Modifier.size(21.dp).background(if (i < 3) c.primary else c.surface, CircleShape).border(1.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { T(if (i < 3) "✓" else "4", size = 7f, w = 800, color = if (i < 3) Color.White else c.text) }
                            T(s, Modifier.padding(top = 4.dp), size = 5.5f, center = true)
                        }
                    }
                }
            }
            T(t("sensing.seeAlert"), Modifier.padding(top = 14.dp).tap { app.replace(Route.Escalation) }, size = 8f, w = 800, color = c.primary, underline = true)
        }
    }
}

private fun Modifier.rowDividerTop(color: Color): Modifier = this.drawBehind { drawLine(color, Offset(0f, 0f), Offset(size.width, 0f), 1.dp.toPx()) }

@Composable
fun EscalationScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val ctx = LocalContext.current
    class Step(val icon: IconName, val title: String, val sub: String, val time: String)
    val timeline = listOf(
        Step(IconName.sensor, t("escalation.s1"), t("escalation.s1s"), "07:30"),
        Step(IconName.camera, t("escalation.s2"), t("escalation.s2s"), "09:42"),
        Step(IconName.checkin, t("escalation.s3"), t("escalation.s3s"), "10:06"),
    )
    val loop = tl("escalation.loopSteps")
    val loopDone = 2

    Screen {
        TopBar(t("escalation.top"))
        Row(Modifier.fillMaxWidth().height(68.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
            Avatar("ER", 43f, portrait = true)
            Column(Modifier.weight(1f)) {
                T(t("escalation.shared"), size = 6f, spacing = 0.8f)
                T("Dr. Elena Ruiz", Modifier.padding(vertical = 2.dp), size = 11f, w = 800)
                T(t("escalation.sent"), size = 7f, color = c.muted)
            }
            Box(Modifier.size(21.dp).background(c.green, CircleShape), contentAlignment = Alignment.Center) { Icon(IconName.check, 16.dp) }
        }
        PageTitle(t("escalation.title"), size = 26f)

        Row(
            Modifier.fillMaxWidth().heightIn(min = 92.dp).background(c.warnBg, RoundedCornerShape(18.dp)).border(1.5.dp, Color(0xFFEB6C63), RoundedCornerShape(18.dp)).padding(11.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(Modifier.size(29.dp).background(Color(0xFFEF6C63), CircleShape).border(1.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { T("!", w = 800, color = Color.White) }
            Column(Modifier.weight(1f)) {
                T(t("escalation.attention"), size = 6f, w = 800, spacing = 0.8f, color = c.urgentText)
                T(t("escalation.abnormal"), Modifier.padding(vertical = 3.dp), size = 10f, w = 800)
                T(t("escalation.abnormalSub"), size = 7f, lh = 1.4f)
            }
        }

        Row(
            Modifier.fillMaxWidth().padding(top = 8.dp).heightIn(min = 50.dp).background(c.amber, RoundedCornerShape(14.dp)).border(1.2.dp, c.ink, RoundedCornerShape(14.dp))
                .tap { app.familyAck = !app.familyAck }.padding(horizontal = 9.dp, vertical = 7.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(IconName.bell, 16.dp)
            Column(Modifier.weight(1f)) { T(t("escalation.family"), size = 8f, w = 800); T(t("escalation.familySub"), Modifier.padding(top = 2.dp), size = 6f, color = c.muted) }
            T("›", w = 800)
        }
        if (app.familyAck) Row(
            Modifier.fillMaxWidth().padding(top = 6.dp).height(29.dp).background(c.green, CircleShape).border(1.dp, c.ink, CircleShape),
            horizontalArrangement = Arrangement.spacedBy(6.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically,
        ) { Icon(IconName.check, 15.dp); T(t("escalation.seen"), size = 7f, w = 800) }

        Card(Modifier.fillMaxWidth().padding(top = 9.dp), radius = 20f, pad = 11f) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column { T(t("escalation.package"), size = 6f, spacing = 0.8f); T(t("escalation.changed"), Modifier.padding(top = 2.dp), size = 14f, w = 800) }
                Chip(t("escalation.sources"), tone = "blue")
            }
            Column(Modifier.padding(vertical = 9.dp)) {
                timeline.forEach { s ->
                    Row(Modifier.fillMaxWidth().heightIn(min = 45.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        IconBadge(s.icon, c.blue, 27f, 9f)
                        Column(Modifier.weight(1f)) { T(s.title, size = 8f, w = 800); T(s.sub, Modifier.padding(top = 2.dp), size = 6.5f, color = c.muted) }
                        T(s.time, size = 6f, color = c.faint)
                    }
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                Column(Modifier.weight(1.15f).height(90.dp).background(Color(0xFFFFF5E1), RoundedCornerShape(12.dp)).border(1.1.dp, c.ink, RoundedCornerShape(12.dp)).padding(7.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { T(t("escalation.temperature"), size = 5.5f, w = 800, color = Color(0xFF1B2A4A)); SimulatedTag() }
                    T("38.2°C ", size = 15f, w = 800, color = Color(0xFF1B2A4A), suffix = "↑", suffixSize = 9f, suffixColor = Color(0xFFE7514A))
                    MiniLine(color = Color(0xFFEF695D), fill = true, height = 35f)
                }
                Box(Modifier.weight(0.85f).height(90.dp).background(Color(0xFFFDE8E5), RoundedCornerShape(12.dp)).border(1.1.dp, c.ink, RoundedCornerShape(12.dp)).padding(7.dp), contentAlignment = Alignment.Center) {
                    Row(horizontalArrangement = Arrangement.spacedBy(3.dp)) { WoundThumb(46f, 52f, 7f, border = false); WoundThumb(46f, 52f, 7f, worse = true, border = false) }
                    Box(Modifier.align(Alignment.BottomCenter).background(Color.White, RoundedCornerShape(5.dp)).padding(horizontal = 4.dp, vertical = 1.dp)) { T(t("escalation.compare"), size = 5.5f, color = Color(0xFF1B2A4A)) }
                }
            }
            Column(Modifier.fillMaxWidth().padding(top = 8.dp).background(c.quote, RoundedCornerShape(topEnd = 9.dp, bottomEnd = 9.dp)).padding(start = 12.dp, top = 7.dp, end = 9.dp, bottom = 7.dp)) {
                T(t("escalation.quote"), size = 7f, w = 700, lh = 1.4f)
                T(t("escalation.quoteSrc"), Modifier.padding(top = 3.dp), size = 5.5f, w = 500, color = c.muted)
            }
            T("✦ " + t("escalation.uncertainty"), Modifier.fillMaxWidth().padding(top = 8.dp), size = 6f, color = c.muted, center = true)
        }

        Card(Modifier.fillMaxWidth().padding(top = 9.dp), bg = c.ice, radius = 18f, pad = 11f) {
            T(t("escalation.loop"), size = 6f, spacing = 0.8f)
            T(t("escalation.loopTitle"), Modifier.padding(top = 2.dp, bottom = 8.dp), size = 12f, w = 800)
            loop.forEachIndexed { i, step ->
                Row(Modifier.heightIn(min = 26.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(19.dp).background(if (i < loopDone) c.primary else if (i == loopDone) c.yellow else c.surface, CircleShape).border(1.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) {
                        if (i < loopDone) Icon(IconName.check, 11.dp, Color.White) else T("${i + 1}", size = 6.5f, w = 800)
                    }
                    T(step, size = 8f, w = if (i == loopDone) 800 else 600, color = if (i > loopDone) c.muted else c.text)
                }
            }
        }
        Row(Modifier.padding(top = 9.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(t("escalation.call"), { callNumber(ctx, "+10000000000") }, Modifier.weight(1f), icon = IconName.phone, flat = true, height = 43f, size = 11f)
            Button(t("escalation.message"), { app.push(Route.AIAssistant()) }, Modifier.weight(1f), secondary = true, icon = IconName.message, flat = true, height = 43f, size = 11f)
        }
    }
}

@Composable
fun RehabScreen() {
    val c = Pal.c
    var week by remember { mutableStateOf(false) }
    val done = remember { mutableStateListOf(true, false, false) }
    val haptic = rememberHaptic()
    val exercises = listOf(t("rehab.ex1") to t("rehab.ex1s"), t("rehab.ex2") to t("rehab.ex2s"), t("rehab.ex3") to t("rehab.ex3s"))
    val dayLabel = t("common.day")
    val weekLabel = t("common.week")

    Screen {
        TopBar(t("rehab.top"), action = { Toggle(listOf(dayLabel, weekLabel), if (week) weekLabel else dayLabel) { week = it == weekLabel } })
        Card(Modifier.fillMaxWidth().height(279.dp), bg = c.sky, radius = 23f, pad = 14f) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                T(t("rehab.goal"), size = 7f, w = 800, spacing = 1f); Chip(t("rehab.target"))
            }
            ArcGauge(if (week) 76 else 82, t("rehab.flexion"))
            T(t("rehab.push"), Modifier.fillMaxWidth().offset(y = (-5).dp), size = 12f, w = 800, center = true, lh = 1.4f)
        }

        Box(Modifier.fillMaxWidth().padding(top = 9.dp).height(221.dp).clip(RoundedCornerShape(21.dp)).border(1.5.dp, c.ink, RoundedCornerShape(21.dp))) {
            // Pose simulée (caméra non branchée)
            Canvas(Modifier.fillMaxSize()) {
                drawRect(Brush.linearGradient(listOf(Color(0xFFD7D5CF), Color(0xFF9EA4A0)), Offset.Zero, Offset(size.width, size.height)))
                drawRect(Color(0xFF7D8C82), Offset(0f, size.height - 48.dp.toPx()), Size(size.width, 48.dp.toPx()))
            }
            SvgCanvas(Modifier.fillMaxSize(), 350f, 220f) {
                drawCircle(Color(0xFF495963), 14f, Offset(195f, 31f))
                drawRoundRect(Color(0xFF5D7180), Offset(174f, 41f), Size(42f, 89f), CornerRadius(20f))
                drawPath(svgPath("M193 58 180 130 250 177"), Color(0xFF66E7B1), style = Stroke(3f))
                drawPath(svgPath("M180 100a30 30 0 0 1 27 44"), Color(0xFFFBE19B), style = Stroke(2f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f, 3f))))
                listOf(Triple(193f, 58f, 5f), Triple(180f, 130f, 7f), Triple(250f, 177f, 5f)).forEach { (x, y, r) ->
                    drawCircle(Color(0xFF1E88E5), r, Offset(x, y)); drawCircle(Color.White, r, Offset(x, y), style = Stroke(2f))
                }
            }
            Column(Modifier.offset(107.dp, 103.dp).size(58.dp).background(Color(0xFFFBE19B), CircleShape).border(1.4.dp, Color(0xFF1B2A4A), CircleShape), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                T("92°", size = 17f, w = 800, color = Color(0xFF1B2A4A)); T(t("rehab.targetSmall"), size = 5f, color = Color(0xFF1B2A4A))
            }
            Chip(t("rehab.reps"), Modifier.align(Alignment.BottomCenter).padding(bottom = 9.dp), tone = "dark")
            Box(Modifier.padding(10.dp).background(Color(0xBF141E2D), RoundedCornerShape(9.dp)).padding(horizontal = 7.dp, vertical = 5.dp)) {
                T("● ", size = 6f, color = Color(0xFFFF5D58), spacing = 0.5f, suffix = t("rehab.live"), suffixSize = 6f, suffixColor = Color.White, suffixW = 400)
            }
        }

        Row(Modifier.padding(top = 9.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            listOf(
                listOf(t("rehab.maxAngle"), "98°", "", t("rehab.plus")) to c.yellow,
                listOf(t("rehab.repsK"), "12", "/20", t("rehab.form")) to c.pink,
                listOf(t("rehab.painAfter"), "3", "/10", t("rehab.within")) to c.green,
            ).forEach { (v, bg) ->
                Card(Modifier.weight(1f).height(98.dp), bg = bg, radius = 16f, pad = 10f) {
                    T(v[0], size = 6f, w = 800)
                    T(v[1], Modifier.padding(top = 11.dp, bottom = 3.dp), size = 21f, w = 800, suffix = v[2], suffixSize = 8f)
                    T(v[3], size = 6.5f)
                }
            }
        }

        SectionRow(t("rehab.exercises"), rightContent = { T("✓ " + t("rehab.approved"), size = 8f, w = 700, color = c.trackText) })
        Card(Modifier.fillMaxWidth(), radius = 17f) {
            exercises.forEachIndexed { i, (name, sub) ->
                Row(
                    Modifier.fillMaxWidth().heightIn(min = 52.dp).rowDivider(c.line, i < 2).tap { haptic(HapticImpact); done[i] = !done[i] }.padding(horizontal = 11.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconBadge(IconName.activity, listOf(c.sky, c.lavender, c.yellow)[i], 30f, iconSize = 16f)
                    Column(Modifier.weight(1f)) { T(name, size = 9f, w = 800, strike = done[i]); T(sub, Modifier.padding(top = 2.dp), size = 7f, color = c.muted) }
                    Box(Modifier.size(24.dp).background(if (done[i]) c.green else c.surface, CircleShape).border(1.2.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { if (done[i]) Icon(IconName.check, 14.dp) }
                }
            }
        }
    }
}

@Composable
fun MedicationsScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val haptic = rememberHaptic()
    val pid = app.session?.profileId
    val askQuestion = t("ai.suggestions").split("|").getOrNull(2)
    val overrides = remember { mutableStateMapOf<String, String>() }
    var error by remember { mutableStateOf<String?>(null) }
    val networkMsg = t("auth.network")

    // Prescription du médecin (API) : planning des 3 prochains jours -> alarmes, + avancement sur 7 jours
    val poll = usePolling(Triple(app.apiUrl, pid, "meds"), 15000, enabled = pid != null) {
        val today = LocalDate.now()
        val asOf = localAsOf()
        val doses = app.api.schedule(pid!!, today.toString(), MedAlarms.SYNC_DAYS, asOf)
        MedAlarms.applySchedule(ctx, doses)
        val adh = runCatching { app.api.adherence(pid, today.minusDays(6).toString(), today.toString(), asOf) }.getOrNull()
        doses to adh
    }
    LaunchedEffect(poll.data) { overrides.clear() }

    val today = LocalDate.now().toString()
    val doses = (poll.data?.first ?: emptyList()).filter { it.date == today }
    fun statusOf(d: Dose) = overrides[d.key] ?: d.status
    val taken = doses.count { statusOf(it) == "TAKEN" }
    val next = doses.firstOrNull { statusOf(it) == "PENDING" }
    val percent = poll.data?.second?.percent?.let { Math.round(it).toInt() }

    fun respond(d: Dose, status: String?) {
        haptic(if (status == "TAKEN") HapticImpact else HapticTick)
        scope.launch {
            try {
                app.api.recordIntake(pid!!, d.medicationId, d.date, d.time, status)
                overrides[d.key] = status ?: "PENDING"
                MedAlarms.markLocal(ctx, d.medicationId, d.date, d.time, status ?: "PENDING")
                error = null
                poll.refresh()
            } catch (e: ApiError) {
                error = if (e.status != 0) e.message else networkMsg
            }
        }
    }

    // Android 13+ : les alarmes sont des notifications, il faut l autorisation
    var notifOk by remember {
        mutableStateOf(Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED)
    }
    val permLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { notifOk = it }

    Screen {
        TopBar(t("meds.top"))
        T(t("meds.kickerN", "n" to doses.size), Modifier.padding(top = 6.dp), size = 9f, w = 800, spacing = 1.5f, color = c.primary)
        PageTitle(t("meds.title"), Modifier.padding(top = 6.dp, bottom = 9.dp))
        Chip(modifier = Modifier.padding(bottom = 12.dp), tone = "green") { Icon(IconName.shield, 12.dp); T(t("meds.verified"), size = 9f, w = 800) }

        if (!notifOk) Card(Modifier.fillMaxWidth().padding(bottom = 10.dp), bg = c.peach, radius = 16f, pad = 11f, borderColor = c.review) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                IconBadge(IconName.bell, c.surface, 32f)
                T(t("meds.noNotif"), Modifier.weight(1f), size = 9f, w = 700, lh = 1.4f)
                Box(Modifier.background(c.primary, CircleShape).border(1.dp, c.ink, CircleShape).tap { permLauncher.launch(Manifest.permission.POST_NOTIFICATIONS) }.padding(horizontal = 11.dp, vertical = 7.dp)) { T(t("meds.allow"), size = 8f, w = 800, color = Color.White) }
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Card(Modifier.weight(1.1f).height(128.dp), bg = c.sky, radius = 19f, pad = 12f) {
                T(t("meds.next"), size = 7.5f, w = 800, spacing = 0.7f)
                if (next != null) {
                    T(next.time, Modifier.padding(top = 6.dp), size = 26f, w = 800, spacing = -1f)
                    T(next.name, size = 9f, w = 800, maxLines = 1)
                    T(t("meds.alarmInfo"), Modifier.padding(top = 2.dp), size = 7f, color = c.muted)
                } else T("✓", Modifier.padding(top = 10.dp), size = 22f, w = 800)
            }
            Card(Modifier.weight(1f).height(128.dp), radius = 19f, pad = 10f) {
                Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                    T(t("meds.adherence"), size = 7.5f, w = 800, spacing = 0.7f)
                    Box(Modifier.padding(top = 6.dp)) { ScoreRing(percent ?: 0, 64f, thickness = 7f) }
                    T(t("meds.adherence7"), Modifier.padding(top = 4.dp), size = 6.5f, color = c.muted, center = true)
                }
            }
        }

        if (error != null) T(error!!, Modifier.padding(top = 8.dp), size = 8f, w = 700, color = c.urgentText)
        if (poll.loading && poll.data == null) Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(Modifier.size(24.dp), color = c.primary, strokeWidth = 2.dp) }
        else if (poll.error != null && poll.data == null) T(t("live.offline"), Modifier.padding(top = 14.dp), size = 9f, w = 700, color = c.urgentText)
        else if (doses.isEmpty()) Card(Modifier.fillMaxWidth().padding(top = 14.dp), bg = c.mint, radius = 16f, pad = 12f) { T(t("meds.noMeds"), size = 9f, w = 700, lh = 1.45f) }
        else if (next == null && doses.none { statusOf(it) == "MISSED" }) T(t("meds.todayDone"), Modifier.padding(top = 10.dp), size = 9f, w = 800, color = c.trackText)

        listOf("morning", "afternoon", "evening").forEach { slot ->
            val list = doses.filter { (it.time.take(2).toIntOrNull() ?: 0).let { h -> if (h < 12) "morning" else if (h < 18) "afternoon" else "evening" } == slot }
            if (list.isEmpty()) return@forEach
            SectionRow(t("meds.$slot"), right = "${list.size}")
            Card(Modifier.fillMaxWidth(), radius = 17f) {
                list.forEachIndexed { i, d ->
                    val s = statusOf(d)
                    Row(
                        Modifier.fillMaxWidth().heightIn(min = 60.dp).rowDivider(c.line, i < list.lastIndex).alpha(if (s == "SKIPPED") 0.55f else 1f).padding(horizontal = 10.dp, vertical = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(Modifier.size(34.dp).background(if (s == "MISSED") c.warnBg else c.lavender, RoundedCornerShape(10.dp)).border(1.dp, c.ink, RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) { Icon(IconName.pill, 18.dp) }
                        Column(Modifier.weight(1f)) {
                            T(d.name, size = 9f, w = 800, strike = s == "TAKEN")
                            T(listOfNotNull(d.time, d.dosage?.takeIf { it.isNotBlank() }, d.instructions?.takeIf { it.isNotBlank() }).joinToString(" · "), Modifier.padding(top = 2.dp), size = 7f, color = c.muted)
                        }
                        when (s) {
                            "TAKEN", "SKIPPED" -> Box(Modifier.tap { respond(d, null) }) {
                                Chip(if (s == "TAKEN") "✓ " + t("meds.taken") else t("meds.skipped"), tone = if (s == "TAKEN") "green" else "white")
                            }
                            else -> Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                if (s == "MISSED") T(t("meds.missedTag"), size = 7f, w = 800, color = c.urgentText)
                                Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                                    Box(Modifier.border(1.dp, c.ink, CircleShape).tap { respond(d, "SKIPPED") }.padding(horizontal = 9.dp, vertical = 7.dp)) { T(t("meds.skip"), size = 8f, w = 800) }
                                    Box(Modifier.background(c.primary, CircleShape).border(1.dp, c.ink, CircleShape).tap { respond(d, "TAKEN") }.padding(horizontal = 11.dp, vertical = 7.dp)) { T(t("meds.take"), size = 8f, w = 800, color = Color.White) }
                                }
                            }
                        }
                    }
                }
            }
        }

        Button(t("meds.ask"), { app.push(Route.AIAssistant(askQuestion)) }, Modifier.padding(top = 14.dp), secondary = true, icon = IconName.sparkle)
        T("$taken/${doses.size} · " + t("settings.disclaimer"), Modifier.fillMaxWidth().padding(top = 10.dp), size = 6f, color = c.muted, center = true)
    }
}

private data class Bubble(val role: String, val content: String, val error: Boolean = false, val escalate: Boolean = false)

@Composable
private fun AssistantBubble(text: String, error: Boolean = false) {
    val c = Pal.c
    Row(Modifier.padding(top = 10.dp).fillMaxWidth(0.92f), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(Modifier.size(30.dp).background(c.lavender, RoundedCornerShape(10.dp)).border(1.2.dp, c.ink, RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) { Icon(IconName.sparkle, 16.dp) }
        Box(Modifier.weight(1f, fill = false).background(if (error) c.warnBg else c.surface, RoundedCornerShape(5.dp, 18.dp, 18.dp, 18.dp)).border(1.2.dp, if (error) c.warnBorder else c.ink, RoundedCornerShape(5.dp, 18.dp, 18.dp, 18.dp)).padding(horizontal = 12.dp, vertical = 9.dp)) {
            T(text, size = 11f, w = 500, lh = 1.45f)
        }
    }
}

/** Assistant de convalescence : /chat (API .NET) -> FastAPI -> Mistral. */
@Composable
fun AIAssistantScreen(initialQuestion: String?) {
    val c = Pal.c
    val app = LocalApp.current
    val scope = rememberCoroutineScope()
    val haptic = rememberHaptic()
    val messages = remember { mutableStateListOf<Bubble>() }
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    val scroll = rememberScrollState()
    val errorText = t("ai.error")

    fun ask(text: String) {
        val q = text.trim()
        if (q.isEmpty() || busy) return
        haptic(HapticImpact)
        messages.add(Bubble("user", q))
        val history = messages.filter { !it.error }.map { ChatMessage(it.role, it.content) }
        input = ""; busy = true
        scope.launch {
            try {
                val res = app.api.chat(history, app.lang)
                messages.add(Bubble("assistant", res.reply, escalate = res.escalate))
            } catch (e: ApiError) {
                messages.add(Bubble("assistant", errorText, error = true))
            } finally { busy = false }
        }
    }
    LaunchedEffect(Unit) { if (initialQuestion != null) ask(initialQuestion) }
    LaunchedEffect(messages.size, busy) { scroll.animateScrollTo(scroll.maxValue) }

    Column(Modifier.fillMaxSize().background(c.bg).statusBarsPadding().navigationBarsPadding().imePadding()) {
        Box(Modifier.padding(horizontal = 16.dp)) { TopBar(t("ai.top")) }
        Column(Modifier.weight(1f).verticalScroll(scroll).padding(horizontal = 16.dp).padding(bottom = 16.dp)) {
            Chip(modifier = Modifier.align(Alignment.CenterHorizontally).padding(bottom = 12.dp), tone = "lavender") { Icon(IconName.sparkle, 12.dp); T(t("ai.kicker"), size = 8f, w = 800) }
            AssistantBubble(t("ai.hello"))
            if (messages.isEmpty()) {
                FlowRow(Modifier.padding(top = 6.dp, start = 38.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    tl("ai.suggestions").forEach { s ->
                        Box(Modifier.background(c.surface, CircleShape).border(1.2.dp, c.ink, CircleShape).tap { ask(s) }.padding(horizontal = 11.dp, vertical = 8.dp)) { T(s, size = 9f, w = 700) }
                    }
                }
            }
            messages.forEach { m ->
                if (m.role == "user") {
                    Box(Modifier.align(Alignment.End).padding(top = 10.dp).fillMaxWidth(0.82f), contentAlignment = Alignment.CenterEnd) {
                        Box(Modifier.background(c.primary, RoundedCornerShape(18.dp, 18.dp, 5.dp, 18.dp)).border(1.2.dp, c.ink, RoundedCornerShape(18.dp, 18.dp, 5.dp, 18.dp)).padding(horizontal = 12.dp, vertical = 9.dp)) {
                            T(m.content, size = 11f, w = 600, color = Color.White, lh = 1.4f)
                        }
                    }
                } else AssistantBubble(m.content, m.error)
            }
            if (busy) Row(Modifier.padding(top = 10.dp, start = 38.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(Modifier.size(16.dp), color = c.primary, strokeWidth = 2.dp); T(t("ai.thinking"), size = 9f, color = c.muted)
            }
            if (messages.any { it.escalate }) Card(Modifier.fillMaxWidth().padding(top = 12.dp), bg = c.peach, radius = 16f, pad = 11f, borderColor = c.review) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconBadge(IconName.phone, c.surface, 32f)
                    Column(Modifier.weight(1f)) { T(t("ai.escalate"), size = 9.5f, w = 800); T(t("ai.escalateSub"), Modifier.padding(top = 2.dp), size = 7.5f, color = c.muted) }
                    Box(Modifier.background(c.primary, CircleShape).border(1.dp, c.ink, CircleShape).tap { app.push(Route.Escalation) }.padding(horizontal = 11.dp, vertical = 7.dp)) { T(t("ai.contact"), size = 8f, w = 800, color = Color.White) }
                }
            }
            T(t("ai.disclaimer"), Modifier.fillMaxWidth().padding(top = 16.dp), size = 7f, color = c.muted, center = true)
        }
        Row(
            Modifier.fillMaxWidth().background(c.navBg).padding(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.weight(1f).heightIn(min = 46.dp, max = 110.dp).background(c.surface, RoundedCornerShape(15.dp)).border(1.5.dp, c.ink, RoundedCornerShape(15.dp)).padding(horizontal = 14.dp, vertical = 12.dp), contentAlignment = Alignment.CenterStart) {
                BasicTextField(
                    input, { input = it },
                    textStyle = TextStyle(fontFamily = Jakarta, fontWeight = FontWeight.Medium, fontSize = fs(12f).sp, color = c.text),
                    cursorBrush = SolidColor(c.primary), modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send), keyboardActions = KeyboardActions(onSend = { ask(input) }),
                    decorationBox = { inner -> if (input.isEmpty()) T(t("ai.placeholder"), size = 12f, w = 500, color = c.faint); inner() },
                )
            }
            Box(Modifier.size(46.dp).background(if (input.isNotBlank()) c.primary else c.grey, RoundedCornerShape(15.dp)).border(1.5.dp, c.ink, RoundedCornerShape(15.dp)).tap(enabled = !busy && input.isNotBlank()) { ask(input) }, contentAlignment = Alignment.Center) {
                Icon(IconName.send, 20.dp, if (input.isNotBlank()) Color.White else c.faint)
            }
        }
    }
}

/** Code d'invitation 6 chiffres + proches liés (vraies données de l'API). */
@Composable
fun FamilyAccessScreen() {
    val c = Pal.c
    val ctx = LocalContext.current
    val haptic = rememberHaptic()
    val sharing = remember { mutableStateListOf(true, true, true, true, true) }
    val profile = useMyProfile().data
    val members = profile?.familyMembers ?: emptyList()
    val code = profile?.linkCode?.takeIf { it.length == 6 } ?: "······"
    val tones = listOf(c.sky, c.pink, c.yellow, c.lavender)
    val icons = listOf(IconName.sensor, IconName.camera, IconName.checkin, IconName.pill, IconName.activity)
    val items = tl("access.items")
    val shareMsg = if (profile != null) t("access.shareMsg", "code" to profile.linkCode) else ""

    Screen {
        TopBar(t("access.top"))
        Card(Modifier.fillMaxWidth(), bg = c.sky, radius = 20f, pad = 11f) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Column(Modifier.weight(1f).height(113.dp), verticalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        T(t("access.secure"), size = 6f, spacing = 0.8f)
                        T(t("access.invite"), Modifier.padding(vertical = 5.dp), size = 13f, w = 800)
                        T(t("access.expires"), size = 6.5f, color = c.muted)
                    }
                    Column {
                        T(t("access.code"), size = 5.5f, spacing = 0.7f)
                        T(code.take(3) + " " + code.drop(3), Modifier.padding(top = 2.dp), size = 19f, w = 800, spacing = 3f)
                    }
                }
                // QR stylisé
                FlowRow(Modifier.size(91.dp, 113.dp).background(Color.White, RoundedCornerShape(10.dp)).border(1.2.dp, c.ink, RoundedCornerShape(10.dp)).padding(8.dp), horizontalArrangement = Arrangement.spacedBy(4.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    for (i in 0 until 9) {
                        val hollow = i in listOf(1, 3, 7)
                        Box(Modifier.size(22.dp, 28.dp).background(if (hollow) Color.White else Color(0xFF1B2A4A), RoundedCornerShape(2.dp)).then(if (hollow) Modifier.border(2.dp, Color(0xFF1B2A4A), RoundedCornerShape(2.dp)) else Modifier))
                    }
                }
            }
            Row(
                Modifier.fillMaxWidth().padding(top = 8.dp).height(35.dp).background(c.surface, RoundedCornerShape(10.dp)).border(1.2.dp, c.ink, RoundedCornerShape(10.dp))
                    .tap { haptic(HapticImpact); if (profile != null) ctx.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, shareMsg), null).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) },
                horizontalArrangement = Arrangement.spacedBy(6.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically,
            ) { Icon(IconName.upload, 15.dp); T(t("access.share"), size = 8f, w = 800) }
        }

        SectionRow(t("access.linked"), right = t("access.people", "n" to members.size), modifier = Modifier.padding(top = 12.dp, bottom = 6.dp))
        Card(Modifier.fillMaxWidth(), radius = 15f) {
            if (members.isEmpty()) T(t("access.none"), Modifier.padding(10.dp), size = 8f, color = c.muted)
            members.forEachIndexed { i, m ->
                Row(Modifier.fillMaxWidth().height(48.dp).rowDivider(c.line, i < members.lastIndex).padding(horizontal = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Avatar(initials(m.fullName), 31f, tones[i % tones.size])
                    Column(Modifier.weight(1f)) {
                        T(m.fullName, size = 8f, w = 800)
                        T(m.relationship + " · " + (if (m.isPrimaryContact) t("access.primary") else t("access.viewOnly")) + (if (m.whatsappOptIn) " · WhatsApp" else ""), Modifier.padding(top = 2.dp), size = 6f, color = c.muted)
                    }
                }
            }
        }

        SectionRow(t("access.see"), rightContent = { T(t("access.anytime"), size = 7f, color = c.muted) }, modifier = Modifier.padding(top = 12.dp, bottom = 6.dp))
        Card(Modifier.fillMaxWidth(), radius = 15f) {
            items.forEachIndexed { i, title ->
                Row(Modifier.fillMaxWidth().height(50.dp).rowDivider(c.line, i < items.lastIndex).padding(horizontal = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(27.dp).background(c.iceBlue, RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) { Icon(icons[i % icons.size], 15.dp) }
                    Column(Modifier.weight(1f)) { T(title, size = 8f, w = 800); T(if (sharing[i]) t("access.canSee") else t("access.hidden"), Modifier.padding(top = 2.dp), size = 6f, color = c.muted) }
                    Switch(sharing[i], { sharing[i] = !sharing[i] }, 0.9f)
                }
            }
        }
    }
}

@Composable
fun ConsentScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val haptic = rememberHaptic()
    val enabled = remember { mutableStateListOf(true, true, true, false) }
    var saved by remember { mutableStateOf(false) }
    LaunchedEffect(saved) { if (saved) { delay(800); app.pop() } }
    val items = listOf(
        Triple(IconName.camera, t("consent.i1") to t("consent.i1s"), c.sky), Triple(IconName.sensor, t("consent.i2") to t("consent.i2s"), c.green),
        Triple(IconName.checkin, t("consent.i3") to t("consent.i3s"), c.yellow), Triple(IconName.activity, t("consent.i4") to t("consent.i4s"), c.lavender),
    )
    Screen {
        TopBar(t("consent.top"))
        Box(Modifier.align(Alignment.CenterHorizontally).padding(top = 16.dp, bottom = 7.dp).size(187.dp, 88.dp)) {
            Box(Modifier.fillMaxWidth().padding(horizontal = 47.dp).align(Alignment.Center).height(2.dp).background(Color(0xFF8CA1B7)))
            Box(Modifier.align(Alignment.CenterStart)) { Avatar("SM", 55f) }
            Box(Modifier.align(Alignment.CenterEnd)) { Avatar("ER", 55f, portrait = true) }
            Box(Modifier.align(Alignment.Center).size(34.dp, 38.dp).background(c.primary, RoundedCornerShape(10.dp, 10.dp, 17.dp, 17.dp)), contentAlignment = Alignment.Center) { Icon(IconName.check, 19.dp, Color.White) }
        }
        PageTitle(t("consent.title"), center = true)
        Muted(t("consent.intro"), Modifier.padding(horizontal = 17.dp, vertical = 0.dp).padding(bottom = 13.dp), center = true)
        Card(Modifier.fillMaxWidth().height(61.dp), bg = c.mint, radius = 16f, pad = 8f) {
            Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Avatar("ER", 39f, portrait = true)
                Column(Modifier.weight(1f)) { T("Dr. Elena Ruiz", size = 8.5f, w = 800); T(t("consent.specialty"), Modifier.padding(top = 2.dp), size = 6f) }
                Chip(t("consent.verified"), tone = "green")
            }
        }
        Card(Modifier.fillMaxWidth().padding(top = 10.dp), radius = 18f) {
            items.forEachIndexed { i, (icon, txt, bg) ->
                Row(Modifier.fillMaxWidth().heightIn(min = 64.dp).rowDivider(c.line, i < 3).padding(horizontal = 10.dp, vertical = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    IconBadge(icon, bg, 30f, iconSize = 18f)
                    Column(Modifier.weight(1f)) { T(txt.first, size = 8.5f, w = 800); T(txt.second, Modifier.padding(top = 3.dp), size = 6f, color = c.muted) }
                    Switch(enabled[i], { enabled[i] = !enabled[i] })
                }
            }
        }
        Row(Modifier.padding(vertical = 11.dp, horizontal = 5.dp), horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(IconName.check, 15.dp, c.trackText); T(t("consent.foot"), Modifier.weight(1f), size = 6.5f, color = c.muted)
        }
        Button(if (saved) t("consent.saved") else t("consent.confirm"), { haptic(HapticImpact); saved = true })
        T(t("common.notNow"), Modifier.align(Alignment.CenterHorizontally).padding(top = 18.dp).tap { app.pop() }, size = 12f, w = 700, underline = true)
    }
}
