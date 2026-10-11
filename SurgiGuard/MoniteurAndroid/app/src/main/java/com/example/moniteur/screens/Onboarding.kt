package com.example.moniteur.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.moniteur.LocalApp
import com.example.moniteur.Route
import com.example.moniteur.data.Api
import com.example.moniteur.data.ApiError
import com.example.moniteur.ui.BodyFigure
import com.example.moniteur.ui.Button
import com.example.moniteur.ui.Card
import com.example.moniteur.ui.Chip
import com.example.moniteur.ui.Field
import com.example.moniteur.ui.HapticTick
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.Muted
import com.example.moniteur.ui.PageTitle
import com.example.moniteur.ui.Screen
import com.example.moniteur.ui.SectionRow
import com.example.moniteur.ui.Stepper
import com.example.moniteur.ui.T
import com.example.moniteur.ui.TopBar
import com.example.moniteur.ui.rememberHaptic
import com.example.moniteur.ui.rowDivider
import com.example.moniteur.ui.t
import com.example.moniteur.ui.tap
import com.example.moniteur.ui.theme.Pal
import com.example.moniteur.ui.tl
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
private fun Person(heart: Boolean) {
    val c = Pal.c
    val ink = Color(0xFF1B2A4A)
    Box(
        Modifier.size(88.dp, 112.dp).clip(RoundedCornerShape(44.dp, 44.dp, 18.dp, 18.dp)).background(Color(0x7AFFFFFF))
            .border(1.3.dp, c.ink, RoundedCornerShape(44.dp, 44.dp, 18.dp, 18.dp)),
    ) {
        Box(Modifier.offset(13.dp, 50.dp).size(60.dp, 68.dp).background(if (heart) Color(0xFFF7FAFF) else Color.White, RoundedCornerShape(28.dp, 28.dp, 4.dp, 4.dp)).border(1.5.dp, ink, RoundedCornerShape(28.dp, 28.dp, 4.dp, 4.dp)))
        Box(Modifier.offset(26.dp, 15.dp).size(34.dp, 38.dp).background(Color(0xFFF0C7AD), RoundedCornerShape(20.dp)).border(1.5.dp, ink, RoundedCornerShape(20.dp)))
        Box(Modifier.fillMaxWidth().offset(y = 70.dp), contentAlignment = Alignment.Center) {
            if (heart) Icon(IconName.heart, 22.dp, Color(0xFFFF6B6B), 2.4f) else Icon(IconName.activity, 24.dp, ink, 2f)
        }
    }
}

@Composable
private fun RoleCard(selected: Boolean, onClick: () -> Unit, bg: Color, title: String, sub: String, heart: Boolean) {
    val c = Pal.c
    val haptic = rememberHaptic()
    val shape = RoundedCornerShape(23.dp)
    Box(
        Modifier.fillMaxWidth().padding(top = 12.dp).height(156.dp).background(bg, shape)
            .border(if (selected) 2.5.dp else 1.5.dp, if (selected) c.primary else c.ink, shape).tap { haptic(HapticTick); onClick() }.padding(16.dp),
    ) {
        Row(Modifier.fillMaxSize(), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Person(heart)
            Column(Modifier.weight(1f)) {
                T(title, size = 14f, w = 800, lh = 1.35f)
                T(sub, Modifier.padding(top = 7.dp), size = 8f, color = c.muted)
            }
            T("→", size = 19f, w = 800)
        }
        Box(
            Modifier.align(Alignment.TopEnd).offset(x = 4.dp, y = (-5).dp).size(24.dp).background(if (selected) c.primary else Color(0x99FFFFFF), CircleShape).border(1.2.dp, c.ink, CircleShape),
            contentAlignment = Alignment.Center,
        ) { if (selected) Icon(IconName.check, 15.dp, Color.White) }
    }
}

@Composable
fun RoleSelectionScreen() {
    val c = Pal.c
    val app = LocalApp.current
    var role by remember { mutableStateOf("patient") }
    Screen(horizontalPad = 23f, topPad = 13f) {
        Brand()
        Spacer(Modifier.height(50.dp))
        T(t("role.kicker"), size = 9f, w = 800, spacing = 1.7f, color = c.primary)
        PageTitle(t("role.title"), Modifier.padding(top = 6.dp, bottom = 9.dp), size = 34f)
        Muted(t("role.sub"))
        RoleCard(role == "patient", { role = "patient" }, c.sky, t("role.patient"), t("role.patientSub"), true)
        RoleCard(role == "family", { role = "family" }, c.lavender, t("role.family"), t("role.familySub"), false)
        Row(Modifier.padding(vertical = 17.dp, horizontal = 7.dp), horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(IconName.shield, 16.dp, c.trackText)
            Column {
                T(t("role.privateTitle"), size = 8f, w = 800)
                T(t("role.privateSub"), Modifier.padding(top = 2.dp), size = 7f, color = c.muted)
            }
        }
        Button(t("common.continue") + "  →", { app.chooseRole(role) })
    }
}

/** Connexion / inscription sur l'API, après le choix du rôle. */
@Composable
fun AuthScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val scope = rememberCoroutineScope()
    var login by remember { mutableStateOf(false) }
    var first by remember { mutableStateOf("") }
    var last by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var deviceId by remember { mutableStateOf("ESP32_001") }
    var server by remember { mutableStateOf(app.apiUrl) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    val isPatient = app.role != "family"
    val required = t("auth.required")
    val network = t("auth.network")
    val staff = t("auth.staff")
    val haptic = rememberHaptic()

    fun submit() {
        val register = !login
        if (email.isBlank() || password.isBlank() || (register && (first.isBlank() || last.isBlank()))) { error = required; return }
        busy = true; error = null
        val url = server.trim()
        if (url != app.apiUrl) app.saveApiUrl(url)
        scope.launch {
            try {
                val api = Api(url)
                val session = if (register) {
                    api.register(email.trim(), password, if (isPatient) "PATIENT" else "FAMILY_MEMBER", first.trim(), last.trim(),
                        phone.trim().ifBlank { null }, if (isPatient) deviceId.trim().ifBlank { null } else null)
                } else api.login(email.trim(), password)
                if (session.user.role != "PATIENT" && session.user.role != "FAMILY_MEMBER") { error = staff; return@launch }
                // Patient existant : direct à l'app ; proche : seulement une fois lié à un patient
                var onboarded = !register
                if (session.user.role == "FAMILY_MEMBER") onboarded = Api(url, session.token).followedPatients().isNotEmpty()
                haptic(com.example.moniteur.ui.HapticImpact)
                app.signIn(session, onboarded)
            } catch (e: ApiError) {
                error = if (e.status != 0) e.message else network
            } finally { busy = false }
        }
    }

    Screen(Modifier.imePadding()) {
        TopBar(t("auth.top"), onBack = { app.signOut() })
        Brand()
        PageTitle(if (login) t("auth.titleLogin") else t("auth.titleRegister"), Modifier.padding(top = 14.dp, bottom = 9.dp))
        Muted(if (isPatient) t("auth.subPatient") else t("auth.subFamily"))
        if (!login) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Field(t("auth.firstName"), first, { first = it }, Modifier.weight(1f))
                Field(t("auth.lastName"), last, { last = it }, Modifier.weight(1f))
            }
        }
        Field(t("auth.email"), email, { email = it }, keyboard = KeyboardType.Email)
        Field(t("auth.password"), password, { password = it }, password = true)
        if (!login) Field(t("auth.phone"), phone, { phone = it }, keyboard = KeyboardType.Phone)
        if (!login && isPatient) Field(t("auth.deviceId"), deviceId, { deviceId = it }, placeholder = "ESP32_001")
        if (error != null) T(error!!, Modifier.padding(top = 10.dp), size = 8.5f, w = 700, color = c.urgentText)
        Button(if (login) t("auth.login") else t("auth.register"), { if (!busy) submit() }, Modifier.padding(top = 16.dp)) {
            if (busy) CircularProgressIndicator(Modifier.size(22.dp), color = Color.White, strokeWidth = 2.dp)
            else T(if (login) t("auth.login") else t("auth.register"), size = 13f, w = 800, color = Color.White)
        }
        T(
            if (login) t("auth.toRegister") else t("auth.toLogin"),
            Modifier.padding(top = 14.dp).align(Alignment.CenterHorizontally).tap { error = null; login = !login },
            size = 10f, w = 700, underline = true,
        )
        Card(Modifier.fillMaxWidth().padding(top = 20.dp), radius = 15f, pad = 10f) {
            T(t("auth.server"), Modifier.padding(bottom = 6.dp), size = 6.5f, w = 800, spacing = 0.8f)
            Field(null, server, { server = it }, keyboard = KeyboardType.Uri, height = 40f, bg = c.bg, fontSize = 12f)
        }
    }
}

@Composable
fun WelcomeScreen() {
    val c = Pal.c
    val app = LocalApp.current
    Screen(horizontalPad = 24f, topPad = 12f) {
        Brand()
        Box(
            Modifier.padding(top = 13.dp).fillMaxWidth().height(328.dp).clip(RoundedCornerShape(28.dp))
                .background(Brush.linearGradient(0f to Color(0xFFDFF7F2), 0.56f to Color(0xFFBDE8FB), 1f to Color(0xFFD8CBF8), start = Offset.Zero, end = Offset.Infinite))
                .border(1.5.dp, c.ink, RoundedCornerShape(28.dp)),
            contentAlignment = Alignment.TopCenter,
        ) {
            Box(Modifier.padding(top = 15.dp).size(280.dp).background(Color(0x33FFFFFF), CircleShape).border(1.dp, Color(0x291B2A4A), CircleShape))
            Box(Modifier.padding(top = 50.dp).size(210.dp).background(Color(0x33FFFFFF), CircleShape).border(1.dp, Color(0x291B2A4A), CircleShape))
            Box(Modifier.align(Alignment.BottomCenter).offset(y = 20.dp).size(260.dp, 45.dp).background(Color(0x7AFFFFFF), CircleShape))
            Box(Modifier.padding(top = 15.dp)) { BodyFigure() }
            Row(Modifier.align(Alignment.TopEnd).padding(top = 197.dp, end = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.width(40.dp).height(1.dp).background(Color(0xFF1B2A4A)))
                Row(
                    Modifier.background(Color.White, RoundedCornerShape(12.dp)).border(1.3.dp, Color(0xFF1B2A4A), RoundedCornerShape(12.dp)).padding(horizontal = 10.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.size(7.dp).background(Color(0xFFFF715E), CircleShape))
                    T(t("welcome.siteLabel"), size = 8f, w = 800, color = Color(0xFF1B2A4A))
                }
            }
        }
        T(t("welcome.eyebrow"), Modifier.padding(top = 22.dp, bottom = 8.dp), size = 9f, w = 800, spacing = 1.5f, color = c.primary)
        T(t("welcome.t1") + "\n" + t("welcome.t2") + "\n", size = 31f, w = 800, spacing = -1.4f, color = c.title, lh = 1.1f, suffix = t("welcome.t3"), suffixSize = 31f, suffixColor = c.primary)
        Muted(t("welcome.lead"), Modifier.padding(top = 11.dp, bottom = 16.dp).fillMaxWidth(0.92f))
        Button(t("welcome.start") + "  →", { app.push(Route.Upload) })
        T(t("welcome.account"), Modifier.padding(top = 18.dp).align(Alignment.CenterHorizontally).tap { app.completeOnboarding() }, size = 12f, w = 700, underline = true)
    }
}

private data class FileItem(val key: String, val size: String, val done: Boolean)

@Composable
fun UploadScreen() {
    val c = Pal.c
    val app = LocalApp.current
    var files by remember {
        mutableStateOf(listOf(FileItem("upload.discharge", "2.4 MB", true), FileItem("upload.operative", "1.8 MB", true), FileItem("upload.labs", "", false), FileItem("upload.meds", "", true)))
    }
    var analyzing by remember { mutableStateOf(false) }
    val haptic = rememberHaptic()
    // Les résultats de labo finissent leur « traitement » après un instant
    LaunchedEffect(Unit) { delay(2500); files = files.map { if (!it.done) it.copy(done = true, size = "0.9 MB") else it } }
    LaunchedEffect(analyzing) { if (analyzing) { delay(1600); analyzing = false; app.push(Route.Protocol) } }

    @Composable
    fun UploadBtn(icon: IconName, label: String, modifier: Modifier) {
        Row(
            modifier.heightIn(min = 34.dp).background(c.surface, RoundedCornerShape(10.dp)).border(1.2.dp, c.ink, RoundedCornerShape(10.dp)).tap { haptic(HapticTick) },
            horizontalArrangement = Arrangement.spacedBy(6.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically,
        ) { Icon(icon, 18.dp); T(label, size = 9f, w = 800) }
    }

    Screen {
        TopBar(t("upload.top"))
        Stepper(tl("upload.steps"), 0)
        PageTitle(t("upload.title"))
        Muted(t("upload.sub"))
        Card(Modifier.fillMaxWidth(), bg = c.sky, radius = 21f, dashed = true, pad = 14f) {
            Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                Box(Modifier.size(43.dp).background(c.surface, CircleShape).border(1.4.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { Icon(IconName.upload, 25.dp) }
                T(t("upload.card"), Modifier.padding(top = 6.dp), size = 13f, w = 800)
                T(t("upload.cardSub"), Modifier.padding(top = 3.dp, bottom = 10.dp), size = 8.5f, color = c.muted)
                UploadBtn(IconName.camera, t("upload.scan"), Modifier.fillMaxWidth())
                Row(Modifier.padding(top = 7.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    UploadBtn(IconName.file, t("upload.pdf"), Modifier.weight(1f))
                    UploadBtn(IconName.image, t("upload.gallery"), Modifier.weight(1f))
                }
            }
        }
        SectionRow(t("upload.files"), right = t("upload.count", "n" to files.size))
        Card(Modifier.fillMaxWidth().padding(bottom = 12.dp), radius = 18f) {
            files.forEachIndexed { i, f ->
                Row(
                    Modifier.fillMaxWidth().height(50.dp).padding(horizontal = 11.dp).then(if (i < files.lastIndex) Modifier.rowDividerLine(c.line) else Modifier),
                    horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.size(27.dp, 29.dp).background(c.iceBlue, RoundedCornerShape(7.dp)).border(1.dp, c.ink, RoundedCornerShape(7.dp)), contentAlignment = Alignment.Center) { Icon(IconName.file, 17.dp) }
                    Column(Modifier.weight(1f)) {
                        T(t(f.key), size = 9.5f, w = 800)
                        T(if (!f.done) t("upload.processing") else f.size.ifBlank { t("upload.ready") }, Modifier.padding(top = 2.dp), size = 7.5f, color = c.muted)
                    }
                    Box(Modifier.size(20.dp).background(if (f.done) c.green else c.yellow, CircleShape), contentAlignment = Alignment.Center) {
                        if (f.done) Icon(IconName.check, 14.dp) else CircularProgressIndicator(Modifier.size(12.dp), color = c.text, strokeWidth = 1.5.dp)
                    }
                }
            }
        }
        Button(if (analyzing) t("upload.analyzing") else t("upload.analyze") + "  →", { if (!analyzing) analyzing = true })
    }
}

@Composable
fun ProtocolScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val cards = listOf("med" to c.pink, "act" to c.yellow, "reh" to c.lavender, "fol" to c.sky)
    Screen {
        TopBar(t("protocol.top"))
        Box(Modifier.padding(top = 5.dp, bottom = 6.dp).align(Alignment.CenterHorizontally).size(48.dp).background(c.green, CircleShape).border(1.5.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { Icon(IconName.check, 25.dp) }
        PageTitle(t("protocol.title"), center = true)
        Muted(t("protocol.sub"), center = true)
        Card(Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 9.dp).heightIn(min = 75.dp), bg = c.green, pad = 11f) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(39.dp).background(c.surface, CircleShape).border(1.2.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { T("◒", size = 22f) }
                Column(Modifier.weight(1f)) {
                    T(t("protocol.detected"), size = 7f, w = 700, spacing = 0.8f)
                    T(t("protocol.surgery"), Modifier.padding(vertical = 3.dp), size = 11f, w = 800)
                    T(t("protocol.surgerySub"), size = 8f)
                }
                Icon(IconName.check, 19.dp)
            }
        }
        cards.chunked(2).forEach { row ->
            Row(Modifier.padding(bottom = 7.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                row.forEach { (k, bg) ->
                    Card(Modifier.weight(1f).heightIn(min = 80.dp), bg = bg, radius = 15f, pad = 10f) {
                        Box(Modifier.fillMaxWidth().heightIn(min = 60.dp)) {
                            Column {
                                T(t("protocol.${k}T"), size = 7.5f, w = 800, upper = true)
                                T(t("protocol.${k}C"), Modifier.padding(top = 5.dp).widthIn115(), size = 9f, w = 800, lh = 1.35f)
                            }
                            Box(Modifier.align(Alignment.BottomEnd).background(Color(0xADFFFFFF), RoundedCornerShape(10.dp)).padding(horizontal = 6.dp, vertical = 3.dp)) {
                                T(t("protocol.${k}Tag"), size = 6.5f, w = 800, color = Color(0xFF1B2A4A))
                            }
                        }
                    }
                }
            }
        }
        Row(
            Modifier.fillMaxWidth().padding(top = 0.dp).heightIn(min = 47.dp).background(c.warnBg, RoundedCornerShape(14.dp)).border(1.5.dp, c.warnBorder, RoundedCornerShape(14.dp)).padding(8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(26.dp).background(c.warnDot, CircleShape).border(1.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) { T("!", size = 12f, w = 800, color = Color(0xFF1B2A4A)) }
            Column(Modifier.weight(1f)) {
                T(t("protocol.warning"), size = 9f, w = 800)
                T(t("protocol.warningSub"), Modifier.padding(top = 2.dp), size = 7f)
            }
        }
        Row(Modifier.padding(top = 9.dp), horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(IconName.shield, 14.dp, c.trackText)
            T(t("protocol.approved"), size = 8f, w = 700, color = c.trackText)
        }
        T(t("protocol.modules"), Modifier.padding(top = 10.dp, bottom = 6.dp), size = 9f, w = 800)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(5.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            tl("protocol.chips").forEach { Chip(it, tone = "blue") }
        }
        Row(Modifier.padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(t("common.edit"), { app.pop() }, Modifier.fillMaxWidth(0.32f), secondary = true)
            Button(t("protocol.confirm"), { app.completeOnboarding() }, Modifier.weight(1f), size = 12f)
        }
    }
}

private fun Modifier.widthIn115(): Modifier = this.then(Modifier.fillMaxWidth(0.85f))

/** Trait fin sous une ligne de liste. */
fun Modifier.rowDividerLine(color: Color): Modifier = this.rowDivider(color)
