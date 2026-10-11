package com.example.moniteur

import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.example.moniteur.screens.AIAssistantScreen
import com.example.moniteur.screens.AuthScreen
import com.example.moniteur.screens.CheckInScreen
import com.example.moniteur.screens.ConsentScreen
import com.example.moniteur.screens.EscalationScreen
import com.example.moniteur.screens.FamilyAccessScreen
import com.example.moniteur.screens.FamilyAttentionScreen
import com.example.moniteur.screens.FamilyHomeScreen
import com.example.moniteur.screens.FamilyInfoScreen
import com.example.moniteur.screens.FamilyProfileScreen
import com.example.moniteur.screens.FamilyRecoveryScreen
import com.example.moniteur.screens.FamilyUrgentScreen
import com.example.moniteur.screens.JoinPatientScreen
import com.example.moniteur.screens.LockPreviewScreen
import com.example.moniteur.screens.MedicationsScreen
import com.example.moniteur.screens.PatientHomeScreen
import com.example.moniteur.screens.ProfileScreen
import com.example.moniteur.screens.ProtocolScreen
import com.example.moniteur.screens.RehabScreen
import com.example.moniteur.screens.ReportsScreen
import com.example.moniteur.screens.RoleSelectionScreen
import com.example.moniteur.screens.SensingRequestScreen
import com.example.moniteur.screens.SettingsScreen
import com.example.moniteur.screens.TwinDetailScreen
import com.example.moniteur.screens.TwinScreen
import com.example.moniteur.screens.UpdatesScreen
import com.example.moniteur.screens.UploadScreen
import com.example.moniteur.screens.WelcomeScreen
import com.example.moniteur.screens.WoundScanScreen
import com.example.moniteur.alarm.MedAlarms
import com.example.moniteur.alarm.localAsOf
import java.time.LocalDate
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.LocalBottomInset
import com.example.moniteur.ui.T
import com.example.moniteur.ui.rememberHaptic
import com.example.moniteur.ui.HapticTick
import com.example.moniteur.ui.t
import com.example.moniteur.ui.tap
import com.example.moniteur.ui.theme.MoniteurTheme
import com.example.moniteur.ui.theme.Pal

@Composable
fun AppRoot(app: AppViewModel) {
    val dark = app.darkMode ?: isSystemInDarkTheme()
    val activity = LocalContext.current as ComponentActivity
    LaunchedEffect(dark) {
        val style = if (dark) SystemBarStyle.dark(android.graphics.Color.TRANSPARENT) else SystemBarStyle.light(android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT)
        activity.enableEdgeToEdge(statusBarStyle = style, navigationBarStyle = style)
    }

    CompositionLocalProvider(LocalApp provides app) {
        MoniteurTheme(dark) {
            val c = Pal.c
            val top = app.stack.lastOrNull()
            val tab = if (app.role == "family") app.familyTab else app.patientTab

            // Retour : dépile, sinon remonte au choix du rôle (connexion / onboarding) ou à l'onglet Accueil
            BackHandler(enabled = top != null || app.role != null && (!app.signedIn || !app.onboarded) || tab != 0) {
                when {
                    top != null -> app.pop()
                    !app.signedIn || !app.onboarded -> if (app.signedIn) app.signOut() else app.chooseRole(null)
                    app.role == "family" -> app.familyTab = 0
                    else -> app.patientTab = 0
                }
            }

            // Appui sur la notification d alarme : ouvre la liste des médicaments
            LaunchedEffect(app.openMedsRequest, app.role, app.onboarded) {
                if (app.openMedsRequest && app.role == "patient" && app.onboarded) {
                    app.openMedsRequest = false
                    if (app.stack.lastOrNull() != Route.Medications) app.push(Route.Medications)
                }
            }

            Box(Modifier.fillMaxSize().background(c.bg)) {
                Root(app)
                AnimatedContent(top, Modifier.fillMaxSize(), transitionSpec = { fadeIn(tween(180)) togetherWith fadeOut(tween(120)) }, label = "route") { r ->
                    if (r != null) Box(Modifier.fillMaxSize().background(if (r is Route.FamilyUrgent) Color(0xFFFF6B6B) else c.bg)) { RouteScreen(r) }
                }
            }
        }
    }
}

@Composable
private fun Root(app: AppViewModel) {
    when {
        app.role == null -> RoleSelectionScreen()
        !app.signedIn -> AuthScreen()
        app.role == "patient" && !app.onboarded -> WelcomeScreen()
        app.role == "patient" -> PatientTabs()
        !app.onboarded -> JoinPatientScreen()
        else -> FamilyTabs()
    }
}

@Composable
private fun RouteScreen(r: Route) {
    when (r) {
        Route.Auth -> AuthScreen()
        Route.Welcome -> WelcomeScreen()
        Route.Upload -> UploadScreen()
        Route.Protocol -> ProtocolScreen()
        Route.TwinDetail -> TwinDetailScreen()
        Route.WoundScan -> WoundScanScreen()
        Route.SensingRequest -> SensingRequestScreen()
        Route.Escalation -> EscalationScreen()
        Route.Rehab -> RehabScreen()
        Route.Medications -> MedicationsScreen()
        is Route.AIAssistant -> AIAssistantScreen(r.question)
        Route.FamilyAccess -> FamilyAccessScreen()
        Route.Consent -> ConsentScreen()
        Route.Settings -> SettingsScreen()
        is Route.LockPreview -> LockPreviewScreen(r.tone)
        Route.FamilyInfo -> FamilyInfoScreen()
        Route.FamilyAttention -> FamilyAttentionScreen()
        is Route.FamilyUrgent -> FamilyUrgentScreen(r.title, r.message)
    }
}

private class TabDef(val labelKey: String, val icon: IconName)

@Composable
private fun BottomNav(tabs: List<TabDef>, selected: Int, onSelect: (Int) -> Unit) {
    val c = Pal.c
    val haptic = rememberHaptic()
    Row(
        Modifier.fillMaxWidth().background(c.navBg).drawBehind { drawLine(c.navLine, Offset(0f, 0f), Offset(size.width, 0f), 1.dp.toPx()) }
            .navigationBarsPadding().padding(top = 8.dp, bottom = 10.dp),
        horizontalArrangement = Arrangement.SpaceAround, verticalAlignment = Alignment.Top,
    ) {
        tabs.forEachIndexed { i, tab ->
            val active = i == selected
            Column(Modifier.weight(1f).tap { if (!active) { haptic(HapticTick); onSelect(i) } }, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Box(
                    Modifier.size(34.dp).background(if (active) c.primary else Color.Transparent, CircleShape).then(if (active) Modifier.border(1.2.dp, c.ink, CircleShape) else Modifier),
                    contentAlignment = Alignment.Center,
                ) { Icon(tab.icon, 19.dp, if (active) Color.White else c.faint) }
                T(t(tab.labelKey), size = 7f, w = if (active) 800 else 500, color = if (active) c.text else c.faint)
            }
        }
    }
}

/** Patient connecté : planning des médicaments -> alarmes, même si l écran des médicaments n est jamais ouvert. */
@Composable
private fun MedAlarmSync() {
    val app = LocalApp.current
    val ctx = LocalContext.current
    val pid = app.session?.profileId
    LaunchedEffect(Unit) { MedAlarms.ensureChannel(ctx) }
    usePolling(Triple(app.apiUrl, pid, "alarms"), 5 * 60_000L, enabled = pid != null) {
        MedAlarms.applySchedule(ctx, app.api.schedule(pid!!, LocalDate.now().toString(), MedAlarms.SYNC_DAYS, localAsOf()))
    }
}

@Composable
private fun PatientTabs() {
    val app = LocalApp.current
    MedAlarmSync()
    val tabs = remember {
        listOf(TabDef("tabs.home", IconName.home), TabDef("tabs.checkin", IconName.checkin), TabDef("tabs.twin", IconName.twin), TabDef("tabs.reports", IconName.report), TabDef("tabs.profile", IconName.profile))
    }
    Column(Modifier.fillMaxSize()) {
        Box(Modifier.weight(1f)) {
            CompositionLocalProvider(LocalBottomInset provides false) {
                when (app.patientTab) {
                    0 -> PatientHomeScreen()
                    1 -> CheckInScreen()
                    2 -> TwinScreen()
                    3 -> ReportsScreen()
                    else -> ProfileScreen()
                }
            }
        }
        BottomNav(tabs, app.patientTab) { app.patientTab = it }
    }
}

/** Surveille les alertes du patient suivi : une nouvelle alerte fait vibrer, une alerte de gravité 3 ouvre l'écran d'urgence. */
@Composable
private fun AlertWatcher() {
    val app = LocalApp.current
    val (_, patient) = useFollowedPatient()
    val alerts = useAlerts(patient?.patientId, 8000).data
    val seen = remember { arrayOfNulls<Set<String>>(1) }
    LaunchedEffect(alerts) {
        val data = alerts ?: return@LaunchedEffect
        val known = seen[0]
        if (known == null) { seen[0] = data.map { it.id }.toSet(); return@LaunchedEffect }
        val fresh = data.filter { it.id !in known }
        if (fresh.isEmpty()) return@LaunchedEffect
        seen[0] = known + fresh.map { it.id }
        app.vibrate(longArrayOf(0, 400, 200, 400))
        fresh.firstOrNull { it.severity >= 3 }?.let { urgent ->
            app.push(Route.FamilyUrgent(app.t("alerts.${urgent.type}") + " · " + (patient?.fullName ?: ""), urgent.message))
        }
    }
}

@Composable
private fun FamilyTabs() {
    val app = LocalApp.current
    val tabs = remember { listOf(TabDef("tabs.home", IconName.home), TabDef("tabs.updates", IconName.bell), TabDef("tabs.recovery", IconName.twin), TabDef("tabs.profile", IconName.profile)) }
    AlertWatcher()
    Column(Modifier.fillMaxSize()) {
        Box(Modifier.weight(1f)) {
            CompositionLocalProvider(LocalBottomInset provides false) {
                when (app.familyTab) {
                    0 -> FamilyHomeScreen()
                    1 -> UpdatesScreen()
                    2 -> FamilyRecoveryScreen()
                    else -> FamilyProfileScreen()
                }
            }
        }
        BottomNav(tabs, app.familyTab) { app.familyTab = it }
    }
}
