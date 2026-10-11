package com.example.moniteur.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.composed
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.moniteur.LocalApp
import com.example.moniteur.ui.theme.Jakarta
import com.example.moniteur.ui.theme.Palette
import com.example.moniteur.ui.theme.Pal
import com.example.moniteur.ui.theme.fs
import com.example.moniteur.ui.theme.weightOf

const val BORDER = 1.5f

/** Traduction : relit la langue courante, donc recompose quand elle change. */
@Composable
fun t(key: String, vararg args: Pair<String, Any?>): String = LocalApp.current.t(key, *args)

@Composable
fun tl(key: String): List<String> = LocalApp.current.list(key)

@Composable
fun rememberHaptic(): (HapticFeedbackType) -> Unit {
    val h = LocalHapticFeedback.current
    return { type -> runCatching { h.performHapticFeedback(type) } }
}

/** Retour tactile léger / de validation. */
val HapticTick = HapticFeedbackType.TextHandleMove
val HapticImpact = HapticFeedbackType.LongPress

/** Clic avec effet « pressé » (transparence), sans ripple. */
fun Modifier.tap(enabled: Boolean = true, onClick: () -> Unit): Modifier = composed {
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    this.alpha(if (pressed && enabled) 0.7f else 1f).clickable(interactionSource = src, indication = null, enabled = enabled, onClick = onClick)
}

/** Texte Plus Jakarta Sans avec l'échelle de tailles Figma. `suffix` = fin du texte dans une autre taille. */
@Composable
fun T(
    text: String,
    modifier: Modifier = Modifier,
    size: Float = 13f,
    w: Int = 400,
    color: Color? = null,
    center: Boolean = false,
    upper: Boolean = false,
    spacing: Float? = null,
    lh: Float? = null,
    maxLines: Int = Int.MAX_VALUE,
    underline: Boolean = false,
    strike: Boolean = false,
    suffix: String? = null,
    suffixSize: Float = 10f,
    suffixColor: Color? = null,
    suffixW: Int = 800,
) {
    val s = fs(size)
    val col = color ?: Pal.c.text
    val shown = if (upper) text.uppercase() else text
    val deco = when {
        underline && strike -> TextDecoration.combine(listOf(TextDecoration.Underline, TextDecoration.LineThrough))
        underline -> TextDecoration.Underline
        strike -> TextDecoration.LineThrough
        else -> TextDecoration.None
    }
    val style = TextStyle(
        fontFamily = Jakarta, fontWeight = weightOf(w), fontSize = s.sp, color = col,
        letterSpacing = (spacing ?: 0f).sp,
        lineHeight = if (lh != null) (s * lh).sp else androidx.compose.ui.unit.TextUnit.Unspecified,
        textAlign = if (center) TextAlign.Center else TextAlign.Start,
        textDecoration = deco,
    )
    if (suffix == null) {
        androidx.compose.material3.Text(shown, modifier, style = style, maxLines = maxLines, overflow = TextOverflow.Ellipsis)
    } else {
        val a = buildAnnotatedString {
            append(shown)
            withStyle(SpanStyle(fontSize = fs(suffixSize).sp, fontWeight = weightOf(suffixW), color = suffixColor ?: col, letterSpacing = 0.sp)) { append(suffix) }
        }
        androidx.compose.material3.Text(a, modifier, style = style, maxLines = maxLines, overflow = TextOverflow.Ellipsis)
    }
}

/** Petit libellé en majuscules (« TODAY'S TASK »…). */
@Composable
fun Kicker(text: String, modifier: Modifier = Modifier, color: Color? = null, size: Float = 7.5f) =
    T(text, modifier, size = size, w = 800, spacing = 0.9f, upper = true, color = color)

fun Modifier.dashedBorder(color: Color, radius: Dp, width: Dp = BORDER.dp): Modifier = drawBehind {
    val stroke = Stroke(width = width.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 8f)))
    drawRoundRect(color, topLeft = Offset(width.toPx() / 2, width.toPx() / 2), size = Size(size.width - width.toPx(), size.height - width.toPx()),
        cornerRadius = CornerRadius(radius.toPx()), style = stroke)
}

/** Carte à fine bordure marine. */
@Composable
fun Card(
    modifier: Modifier = Modifier,
    bg: Color? = null,
    radius: Float = 19f,
    dashed: Boolean = false,
    pad: Float = 0f,
    borderColor: Color? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val c = Pal.c
    val shape = RoundedCornerShape(radius.dp)
    val ink = borderColor ?: c.ink
    Column(
        modifier
            .background(bg ?: c.surface, shape)
            .then(if (dashed) Modifier.dashedBorder(ink, radius.dp) else Modifier.border(BORDER.dp, ink, shape))
            .clip(shape)
            .padding(pad.dp),
        content = content,
    )
}

/** Bouton principal : bleu, bordure marine et ombre dure de 3 dp. */
@Composable
fun Button(
    text: String? = null,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    secondary: Boolean = false,
    icon: IconName? = null,
    flat: Boolean = false,
    height: Float = 51f,
    color: Color? = null,
    textColor: Color? = null,
    size: Float = 13f,
    enabled: Boolean = true,
    content: (@Composable () -> Unit)? = null,
) {
    val c = Pal.c
    val bg = color ?: if (secondary) c.surface else c.primary
    val fg = textColor ?: if (secondary) c.text else c.onPrimary
    val haptic = rememberHaptic()
    val src = remember { MutableInteractionSource() }
    val pressed by src.collectIsPressedAsState()
    val depth = if (flat) 0f else 3f
    val dy = if (pressed && !flat) depth else 0f
    Box(
        modifier.height((height + depth).dp).clickable(src, null, enabled = enabled) { haptic(HapticImpact); onClick() },
    ) {
        if (!flat) {
            Box(Modifier.fillMaxWidth().height(height.dp).offset(y = depth.dp).background(c.shadow, RoundedCornerShape(15.dp)))
        }
        Row(
            Modifier.fillMaxWidth().height(height.dp).offset(y = dy.dp)
                .background(bg, RoundedCornerShape(15.dp)).border(BORDER.dp, c.ink, RoundedCornerShape(15.dp)),
            horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically,
        ) {
            if (content != null) content() else {
                if (icon != null) { Icon(icon, 18.dp, fg); Spacer(Modifier.width(7.dp)) }
                T(text ?: "", size = size, w = 800, color = fg)
            }
        }
    }
}

@Composable
fun RoundButton(icon: IconName, onClick: () -> Unit, size: Float = 38f, bg: Color? = null) {
    val c = Pal.c
    val haptic = rememberHaptic()
    Box(
        Modifier.size(size.dp).background(bg ?: c.surface, CircleShape).border(BORDER.dp, c.ink, CircleShape)
            .tap { haptic(HapticTick); onClick() },
        contentAlignment = Alignment.Center,
    ) { Icon(icon, 20.dp) }
}

/** .top-bar : bouton retour, titre centré, action optionnelle. */
@Composable
fun TopBar(title: String, back: Boolean = true, action: (@Composable () -> Unit)? = null, onBack: (() -> Unit)? = null) {
    val app = LocalApp.current
    Row(Modifier.fillMaxWidth().height(48.dp).padding(bottom = 7.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.width(96.dp)) { if (back) RoundButton(IconName.arrow, onBack ?: { app.pop() }) }
        T(title, Modifier.weight(1f), size = 15f, w = 800, center = true, maxLines = 1)
        Box(Modifier.width(96.dp), contentAlignment = Alignment.CenterEnd) { action?.invoke() }
    }
}

fun toneColor(c: Palette, tone: String): Color = when (tone) {
    "blue" -> c.blue
    "green", "mint" -> c.green
    "pink" -> c.pink
    "yellow" -> c.yellow
    "lavender" -> c.lavender
    "sky" -> c.sky
    "dark" -> Color(0xDB1B2A4A)
    else -> c.surface
}

@Composable
fun Chip(text: String? = null, modifier: Modifier = Modifier, tone: String = "white", size: Float = 9f, content: (@Composable RowScope.() -> Unit)? = null) {
    val c = Pal.c
    val dark = tone == "dark"
    Row(
        modifier.background(toneColor(c, tone), CircleShape).border(1.2.dp, if (dark) Color.White else c.ink, CircleShape)
            .padding(horizontal = 10.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp, Alignment.CenterHorizontally), verticalAlignment = Alignment.CenterVertically,
    ) {
        if (content != null) content() else T(text ?: "", size = size, w = 800, color = if (dark) Color.White else c.text)
    }
}

/** .toggle : pastille segmentée (Jour / Semaine…). */
@Composable
fun Toggle(options: List<String>, value: String, onChange: (String) -> Unit) {
    val c = Pal.c
    val haptic = rememberHaptic()
    Row(Modifier.height(31.dp).background(c.grey, CircleShape).border(1.2.dp, c.ink, CircleShape).padding(2.dp)) {
        options.forEach { o ->
            Box(
                Modifier.clip(CircleShape).background(if (value == o) c.primary else Color.Transparent).padding(horizontal = 9.dp)
                    .tap { haptic(HapticTick); onChange(o) }.height(27.dp),
                contentAlignment = Alignment.Center,
            ) { T(o, size = 8f, w = 800, maxLines = 1, color = if (value == o) Color.White else c.text) }
        }
    }
}

@Composable
fun Switch(on: Boolean, onToggle: () -> Unit, scale: Float = 1f) {
    val c = Pal.c
    val haptic = rememberHaptic()
    Box(
        Modifier.width((38 * scale).dp).height((22 * scale).dp).background(if (on) c.primary else c.switchOff, CircleShape)
            .border(1.dp, c.ink, CircleShape).padding(2.dp).tap { haptic(HapticTick); onToggle() },
        contentAlignment = Alignment.CenterStart,
    ) {
        Box(
            Modifier.offset(x = if (on) (15 * scale).dp else 0.dp).size((16 * scale).dp).background(Color.White, CircleShape).border(1.dp, c.ink, CircleShape),
        )
    }
}

@Composable
fun SectionRow(title: String, kicker: String? = null, right: String? = null, rightContent: (@Composable () -> Unit)? = null, modifier: Modifier = Modifier.padding(top = 12.dp, bottom = 9.dp)) {
    val c = Pal.c
    Row(modifier.fillMaxWidth().padding(horizontal = 1.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
        Column(Modifier.weight(1f, fill = false)) {
            if (kicker != null) T(kicker, size = 6.5f, w = 700, spacing = 0.9f, upper = true, color = c.muted)
            T(title, Modifier.padding(top = if (kicker != null) 2.dp else 0.dp), size = 13f, w = 800)
        }
        if (rightContent != null) rightContent() else if (right != null) T(right, size = 9f, color = c.muted)
    }
}

@Composable
fun PageTitle(text: String, modifier: Modifier = Modifier.padding(top = 13.dp, bottom = 9.dp), center: Boolean = false, size: Float = 29f) {
    T(text, modifier.fillMaxWidth(), size = size, w = 800, color = Pal.c.title, center = center, spacing = -1.1f, lh = 1.17f)
}

@Composable
fun Muted(text: String, modifier: Modifier = Modifier.padding(bottom = 13.dp), center: Boolean = false) {
    T(text, modifier.fillMaxWidth(), size = 12.5f, color = Pal.c.muted, center = center, lh = 1.55f)
}

@Composable
fun Avatar(initials: String, size: Float = 41f, bg: Color? = null, online: Boolean = false, portrait: Boolean = false) {
    val c = Pal.c
    Box(Modifier.size(size.dp)) {
        Box(
            Modifier.size(size.dp).background(bg ?: if (portrait) Color(0xFFD5C3F7) else c.pink, CircleShape).border(BORDER.dp, c.ink, CircleShape).clip(CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            if (portrait) Box(Modifier.fillMaxWidth().height((size * 0.42f).dp).align(Alignment.TopCenter).background(Color(0xFFF3C5AA)))
            T(initials, size = if (size > 45) 13f else if (size < 34) 7f else 10.5f, w = 800, color = Color(0xFF1B2A4A))
        }
        if (online) Box(Modifier.size(11.dp).align(Alignment.BottomEnd).background(Color(0xFF53D397), CircleShape).border(2.dp, Color.White, CircleShape))
    }
}

/** Petit badge d'icône des listes. */
@Composable
fun IconBadge(icon: IconName, bg: Color? = null, size: Float = 27f, radius: Float = 9f, border: Boolean = true, iconSize: Float = 15f, color: Color? = null) {
    val c = Pal.c
    val shape = RoundedCornerShape(radius.dp)
    Box(
        Modifier.size(size.dp).background(bg ?: c.blue, shape).then(if (border) Modifier.border(1.dp, c.ink, shape) else Modifier),
        contentAlignment = Alignment.Center,
    ) { Icon(icon, iconSize.dp, color) }
}

/** Étiquette « SIMULATED » : les mesures simulées doivent être signalées. */
@Composable
fun SimulatedTag(modifier: Modifier = Modifier) {
    val c = Pal.c
    Box(modifier.background(c.lavender, CircleShape).border(1.dp, c.ink, CircleShape).padding(horizontal = 6.dp, vertical = 3.dp)) {
        T("SIMULATED", size = 5.5f, w = 800, spacing = 0.5f)
    }
}

val LocalBottomInset = staticCompositionLocalOf { true }

/** Écran standard : zone sûre, défilement, gouttière de 16 dp. */
@Composable
fun Screen(
    modifier: Modifier = Modifier,
    scroll: Boolean = true,
    bg: Color? = null,
    padded: Boolean = true,
    horizontalPad: Float = 16f,
    topPad: Float = 4f,
    content: @Composable ColumnScope.() -> Unit,
) {
    val c = Pal.c
    val bottomInset = LocalBottomInset.current
    val base = Modifier.fillMaxSize().background(bg ?: c.bg).statusBarsPadding()
    val inner = Modifier.fillMaxSize()
        .then(if (scroll) Modifier.verticalScroll(rememberScrollState()) else Modifier)
        .then(if (padded) Modifier.padding(start = horizontalPad.dp, end = horizontalPad.dp, top = topPad.dp) else Modifier)
    Box(base) {
        Column(inner.then(modifier)) {
            content()
            if (padded) Spacer(Modifier.height(28.dp))
            if (bottomInset) Spacer(Modifier.windowInsetsPadding(WindowInsets.navigationBars))
        }
    }
}

/** Ligne d'une liste à bordure (profil, réglages…). */
@Composable
fun ListRow(
    title: String,
    modifier: Modifier = Modifier,
    left: (@Composable () -> Unit)? = null,
    sub: String? = null,
    right: (@Composable () -> Unit)? = null,
    onClick: (() -> Unit)? = null,
    last: Boolean = false,
) {
    val c = Pal.c
    Row(
        modifier.fillMaxWidth().then(if (onClick != null) Modifier.tap { onClick() } else Modifier)
            .drawBehind { if (!last) drawLine(c.line, Offset(0f, size.height), Offset(size.width, size.height), 1.dp.toPx()) }
            .heightIn(min = IntrinsicHeightMin).padding(horizontal = 10.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically,
    ) {
        left?.invoke()
        Column(Modifier.weight(1f)) {
            T(title, size = 8.5f, w = 800)
            if (sub != null) T(sub, Modifier.padding(top = 2.dp), size = 6.5f, color = c.muted)
        }
        if (right != null) right() else if (onClick != null) T("›", size = 13f, w = 800)
    }
}

private val IntrinsicHeightMin = 48.dp

/** Séparateur horizontal entre lignes d'une carte. */
fun Modifier.rowDivider(color: Color, show: Boolean = true): Modifier = drawBehind {
    if (show) drawLine(color, Offset(0f, size.height), Offset(size.width, size.height), 1.dp.toPx())
}

/** Champ texte à bordure (connexion, saisie). */
@Composable
fun Field(
    label: String?,
    value: String,
    onChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    keyboard: KeyboardType = KeyboardType.Text,
    password: Boolean = false,
    placeholder: String? = null,
    height: Float = 46f,
    bg: Color? = null,
    fontSize: Float = 13f,
) {
    val c = Pal.c
    Column(modifier.padding(top = if (label != null) 9.dp else 0.dp)) {
        if (label != null) T(label, Modifier.padding(start = 2.dp, bottom = 4.dp), size = 7f, w = 800, spacing = 0.6f)
        Box(
            Modifier.fillMaxWidth().height(height.dp).background(bg ?: c.surface, RoundedCornerShape(12.dp)).border(1.2.dp, c.ink, RoundedCornerShape(12.dp))
                .padding(horizontal = 12.dp),
            contentAlignment = Alignment.CenterStart,
        ) {
            BasicTextField(
                value, onChange, singleLine = true,
                textStyle = TextStyle(fontFamily = Jakarta, fontWeight = FontWeight.SemiBold, fontSize = fontSize.sp, color = c.text),
                cursorBrush = SolidColor(c.primary),
                keyboardOptions = KeyboardOptions(keyboardType = keyboard),
                visualTransformation = if (password) PasswordVisualTransformation() else VisualTransformation.None,
                modifier = Modifier.fillMaxWidth(),
                decorationBox = { inner ->
                    if (value.isEmpty() && placeholder != null) T(placeholder, size = fontSize, w = 600, color = c.faint)
                    inner()
                },
            )
        }
    }
}

@Composable
fun BorderedBox(
    modifier: Modifier = Modifier,
    bg: Color,
    border: Color,
    radius: Float = 14f,
    width: Float = 1.2f,
    content: @Composable BoxScope.() -> Unit,
) {
    val shape = RoundedCornerShape(radius.dp)
    Box(modifier.background(bg, shape).border(BorderStroke(width.dp, border), shape), content = content)
}

typealias BoxScope = androidx.compose.foundation.layout.BoxScope
