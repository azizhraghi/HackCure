package com.example.moniteur.screens

import androidx.compose.foundation.Canvas
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.moniteur.LocalApp
import com.example.moniteur.Route
import com.example.moniteur.data.initials
import com.example.moniteur.ui.Avatar
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.RoundButton
import com.example.moniteur.ui.T
import com.example.moniteur.ui.t
import com.example.moniteur.ui.theme.Pal
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.draw.clip
import com.example.moniteur.ui.tap

/** .brand : logo + « SurgiGuard AI ». */
@Composable
fun Brand(family: Boolean = false) {
    val c = Pal.c
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(
            Modifier.size(31.dp).background(if (family) c.lavender else c.primary, RoundedCornerShape(10.dp)).border(1.5.dp, c.ink, RoundedCornerShape(10.dp)),
            contentAlignment = Alignment.Center,
        ) { Icon(if (family) IconName.profile else IconName.activity, 19.dp, if (family) c.text else Color.White) }
        T("SurgiGuard ", size = 18f, w = 700, suffix = "AI", suffixSize = 18f, suffixColor = c.primary, suffixW = 700)
        if (family) {
            Box(Modifier.padding(start = 2.dp).background(c.surface, CircleShape).border(1.dp, c.ink, CircleShape).padding(horizontal = 7.dp, vertical = 3.dp)) {
                T("FAMILY", size = 7f, w = 800, spacing = 0.8f)
            }
        }
    }
}

/** Bandeau bleu du côté famille (lecture seule + changer de rôle). */
@Composable
fun CaregiverBanner() {
    val c = Pal.c
    val app = LocalApp.current
    Row(
        Modifier.fillMaxWidth().height(41.dp).background(c.primary).padding(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(IconName.profile, 15.dp, Color.White)
        T(t("fam.banner") + t("fam.readOnly"), Modifier.weight(1f), size = 8f, color = Color.White)
        Box(
            Modifier.background(Color(0x29FFFFFF), CircleShape).border(1.dp, Color.White, CircleShape).tap { app.signOut() }.padding(horizontal = 8.dp, vertical = 5.dp),
        ) { T(t("fam.switch"), size = 7f, w = 800, color = Color.White) }
    }
}

/** Coins d'un cadre de visée (scan plaie / QR). */
@Composable
fun Corners(color: Color = Color.White, size: Dp = 42.dp, width: Dp = 270.dp, height: Dp = 225.dp) {
    Canvas(Modifier.size(width, height)) {
        val s = size.toPx()
        val w = 3.dp.toPx()
        val r = 13.dp.toPx()
        fun corner(x: Float, y: Float, dx: Float, dy: Float) {
            val p = Path().apply {
                moveTo(x, y + dy * s); lineTo(x, y + dy * r)
                quadraticTo(x, y, x + dx * r, y)
                lineTo(x + dx * s, y)
            }
            drawPath(p, color, style = Stroke(w, cap = androidx.compose.ui.graphics.StrokeCap.Round))
        }
        val iw = this.size.width
        val ih = this.size.height
        corner(0f, 0f, 1f, 1f); corner(iw, 0f, -1f, 1f); corner(0f, ih, 1f, -1f); corner(iw, ih, -1f, -1f)
    }
}

/** En-tête d'accueil : avatar, salutation, boutons rapides. */
@Composable
fun HomeHeader(greeting: String, name: String, avatar: String, avatarBg: Color? = null, actions: @Composable () -> Unit) {
    val c = Pal.c
    Row(Modifier.fillMaxWidth().height(60.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        Avatar(avatar, online = true, bg = avatarBg)
        Column(Modifier.weight(1f)) {
            T(greeting, size = 9f, color = c.muted)
            T(name, Modifier.padding(top = 2.dp), size = 14f, w = 800)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) { actions() }
    }
}

@Composable
fun initialsOf(first: String?, last: String?) = initials("${first ?: ""} ${last ?: ""}")

/** Pastille ronde numérotée / cochée (étapes, jalons). */
@Composable
fun StepDot(done: Boolean, number: Int, size: Dp = 24.dp, doneColor: Color = Pal.c.green) {
    val c = Pal.c
    Box(Modifier.size(size).background(if (done) doneColor else c.surface, CircleShape).border(1.2.dp, c.ink, CircleShape), contentAlignment = Alignment.Center) {
        if (done) Icon(IconName.check, 14.dp) else T("$number", size = 7f, w = 800)
    }
}

/** Ouvre un appel téléphonique (composeur) sans permission. */
fun callNumber(ctx: android.content.Context, number: String) {
    runCatching {
        ctx.startActivity(android.content.Intent(android.content.Intent.ACTION_DIAL, android.net.Uri.parse("tel:$number")).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}
