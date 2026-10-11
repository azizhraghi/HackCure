package com.example.moniteur.ui

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
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.moniteur.ui.theme.Pal
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

fun svgPath(d: String): Path = PathParser().parsePathString(d).toPath()

/** Canvas à repère SVG (viewBox vw x vh). meet = proportions conservées, sinon étiré (preserveAspectRatio none). */
@Composable
fun SvgCanvas(modifier: Modifier, vw: Float, vh: Float, meet: Boolean = false, draw: DrawScope.() -> Unit) {
    Canvas(modifier) {
        val sx = size.width / vw
        val sy = size.height / vh
        if (meet) {
            val s = min(sx, sy)
            withTransform({
                translate((size.width - vw * s) / 2f, (size.height - vh * s) / 2f)
                scale(s, s, pivot = Offset.Zero)
            }) { draw() }
        } else {
            withTransform({ scale(sx, sy, pivot = Offset.Zero) }) { draw() }
        }
    }
}

private const val LINE = "M2 38 C16 36 20 18 33 24 S51 34 64 17 83 28 96 14 118 8"
private val linePath = svgPath(LINE)
private val lineFill = svgPath("$LINE V44 H2 Z")

/** .mini-line : courbe d'illustration. */
@Composable
fun MiniLine(modifier: Modifier = Modifier, color: Color? = null, fill: Boolean = false, dashed: Boolean = false, height: Float = 44f) {
    val col = color ?: Pal.c.text
    SvgCanvas(modifier.fillMaxWidth().padding(top = 5.dp).height(height.dp), 120f, 44f) {
        if (fill) drawPath(lineFill, col.copy(alpha = 0.13f))
        drawPath(linePath, col, style = Stroke(3f, cap = StrokeCap.Round, pathEffect = if (dashed) PathEffect.dashPathEffect(floatArrayOf(5f, 5f)) else null))
        drawCircle(col, 3.5f, Offset(118f, 8f))
    }
}

/** .mini-bars */
@Composable
fun MiniBars(values: List<Int> = listOf(48, 70, 42, 83, 59, 74, 91), color: Color? = null) {
    val col = color ?: Pal.c.text
    Row(Modifier.padding(top = 9.dp).height(40.dp), horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.Bottom) {
        values.forEach { h -> Box(Modifier.width(7.dp).fillMaxHeight(h / 100f).background(col.copy(alpha = 0.87f), RoundedCornerShape(5.dp))) }
    }
}

/** .score-ring : anneau de progression. */
@Composable
fun ScoreRing(value: Int, size: Float = 88f, label: String? = null, thickness: Float = 9f) {
    val c = Pal.c
    Box(Modifier.size(size.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(size.dp)) {
            val th = thickness.dp.toPx()
            val d = this.size.width - th
            drawArc(c.grey, 0f, 360f, false, Offset(th / 2, th / 2), Size(d, d), style = Stroke(th))
            drawArc(c.primary, -90f, 360f * value / 100f, false, Offset(th / 2, th / 2), Size(d, d), style = Stroke(th))
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            T("$value", size = if (size > 80) 23f else 17f, w = 800, spacing = -1f, suffix = "%", suffixSize = 10f)
            if (label != null) T(label, size = 5.5f, w = 600, upper = true)
        }
    }
}

/** .arc-gauge : 16 barres arrondies sur un arc (Rééducation). */
@Composable
fun ArcGauge(value: Int, label: String) {
    val c = Pal.c
    val filled = Math.round(value / 100f * 16)
    Box(Modifier.fillMaxWidth().height(185.dp)) {
        SvgCanvas(Modifier.fillMaxSize(), 280f, 150f, meet = true) {
            for (i in 0 until 16) {
                val angle = -168f + i * 10.5f
                val x = 140f + cos(angle * PI.toFloat() / 180f) * 107f
                val y = 135f + sin(angle * PI.toFloat() / 180f) * 107f
                rotate(angle + 90f, pivot = Offset(x, y)) {
                    drawRoundRect(if (i < filled) c.primary else Color.White, Offset(x - 5f, y - 15f), Size(10f, 30f), androidx.compose.ui.geometry.CornerRadius(5f))
                }
            }
        }
        Column(Modifier.fillMaxWidth().align(Alignment.Center).padding(top = 40.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            T("$value", size = 45f, w = 800, spacing = -2f, suffix = "%", suffixSize = 16f)
            T(label, Modifier.padding(top = 2.dp), size = 9f, w = 800)
        }
    }
}

/** .stepper : étapes de l'onboarding. */
@Composable
fun Stepper(steps: List<String>, current: Int = 0) {
    val c = Pal.c
    Box(Modifier.fillMaxWidth().padding(top = 6.dp, bottom = 17.dp), contentAlignment = Alignment.TopCenter) {
        Canvas(Modifier.fillMaxWidth().height(21.dp).padding(horizontal = 47.dp)) {
            drawLine(Color(0xFFAEB8C9), Offset(0f, 10.dp.toPx()), Offset(size.width, 10.dp.toPx()), 1.5.dp.toPx(), pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 8f)))
        }
        Row(horizontalArrangement = Arrangement.Center) {
            steps.forEachIndexed { i, s ->
                Column(Modifier.width(78.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        Modifier.size(21.dp).background(if (i < current) c.green else if (i == current) c.primary else c.bg, CircleShape)
                            .border(1.2.dp, if (i <= current) c.ink else Color(0xFFAAB4C5), CircleShape),
                        contentAlignment = Alignment.Center,
                    ) { T(if (i < current) "✓" else "${i + 1}", size = 8f, w = 800, color = if (i == current) Color.White else c.text) }
                    T(s, Modifier.padding(top = 4.dp), size = 8f, w = 700, color = if (i == current) c.text else c.faint)
                }
            }
        }
    }
}

/** Compteur animé (CountUp du prototype). */
@Composable
fun rememberCountUp(value: Int): Int {
    var shown by remember { mutableFloatStateOf(0f) }
    LaunchedEffect(value) {
        for (f in 1..24) { shown = value * f / 24f; delay(28) }
    }
    return Math.round(shown)
}

/** Vignette de plaie (dégradé radial). */
@Composable
fun WoundThumb(width: Float = 54f, height: Float = 51f, radius: Float = 10f, worse: Boolean = false, dashed: Boolean = false, border: Boolean = true) {
    val c = Pal.c
    val shape = RoundedCornerShape(radius.dp)
    Canvas(Modifier.size(width.dp, height.dp).clip(shape).then(if (border) Modifier.border(1.dp, c.ink, shape) else Modifier)) {
        val a = if (worse) Color(0xFFC3463D) else Color(0xFFD36962)
        val b = if (worse) Color(0xFFEE8B7A) else Color(0xFFF4AA9B)
        val cc = if (worse) Color(0xFFE9AB95) else Color(0xFFECC2AE)
        val d = Color(0xFFDFB299)
        drawRect(
            Brush.radialGradient(
                0.08f to a, 0.09f to b, 0.2f to b, 0.21f to cc, 0.48f to cc, 0.49f to d, 1f to d,
                center = center, radius = size.width / 2f,
            ),
        )
        if (dashed) drawLine(Color(0xFF7E3535), Offset(size.width * .22f, size.height * .52f), Offset(size.width * .8f, size.height * .44f), 3f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 8f)))
    }
}

private val trajArea = svgPath("M3 56C30 50 55 40 80 30S130 14 157 8V65H3Z")
private val trajExpected = svgPath("M3 54C38 45 72 36 106 24S141 12 157 10")
private val trajActual = svgPath("M3 56C30 50 55 40 80 30S130 14 157 8")

/** Trajectoire attendue vs observée (Rapports + Jumeau). */
@Composable
fun TrajectoryChart(height: Float = 120f, modifier: Modifier = Modifier) {
    val c = Pal.c
    SvgCanvas(modifier.fillMaxWidth().height(height.dp), 160f, 65f) {
        drawPath(trajArea, Brush.verticalGradient(listOf(c.primary.copy(alpha = 0.25f), c.primary.copy(alpha = 0f)), 0f, 65f))
        drawPath(trajExpected, c.muted, style = Stroke(2f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(5f, 4f))))
        drawPath(trajActual, c.primary, style = Stroke(2.6f, cap = StrokeCap.Round))
        drawCircle(c.primary, 3f, Offset(157f, 8f))
    }
}

/** Courbe des valeurs réelles (historique API) ; ligne plate si une seule valeur. */
@Composable
fun Spark(values: List<Double>, color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier.fillMaxWidth().height(40.dp)) {
        if (values.isEmpty()) return@Canvas
        val min = values.min()
        val max = values.max()
        val sx = size.width / 104f
        val sy = size.height / 40f
        fun pt(i: Int, v: Double): Offset {
            val x = if (values.size == 1) 100f else i.toFloat() / (values.size - 1) * 100f
            val y = 36f - ((v - min) / (if (max - min == 0.0) 1.0 else max - min)).toFloat() * 30f
            return Offset(x * sx, y * sy)
        }
        val p = Path()
        values.forEachIndexed { i, v -> val o = pt(i, v); if (i == 0) p.moveTo(o.x, o.y) else p.lineTo(o.x, o.y) }
        drawPath(p, color, style = Stroke(2.4.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round))
        drawCircle(color, 3.dp.toPx(), pt(values.lastIndex, values.last()))
    }
}

@Composable
private fun pulse(durationMs: Int = 1800): Float {
    val t = rememberInfiniteTransition(label = "pulse")
    val v by t.animateFloat(0f, 1f, infiniteRepeatable(tween(durationMs, easing = LinearEasing), RepeatMode.Restart), label = "p")
    return v
}

private val bodyOutline = svgPath("M97 69c-4 9-19 13-29 20-11 8-12 33-15 57l-11 87c-1 11 14 14 18 3l18-82 1 86-15 162c-1 13 17 16 22 3l24-122 24 122c5 13 23 10 22-3l-15-162 1-86 18 82c4 11 19 8 18-3l-11-87c-3-24-4-49-15-57-10-7-25-11-29-20")
private val bodyLines = svgPath("M110 74v204M79 240h62M86 146c17 8 31 8 48 0")

/** BodyFigure du prototype (Bienvenue, jumeau compact). */
@Composable
fun BodyFigure(width: Float = 142f, height: Float = 294f) {
    val p = pulse()
    SvgCanvas(Modifier.size(width.dp, height.dp), 220f, 440f, meet = true) {
        val g = Brush.linearGradient(0f to Color(0xFFF7FBFF), 0.55f to Color(0xFFCFEAFA), 1f to Color(0xFFB7D7EC), start = Offset(0f, 0f), end = Offset(220f, 440f))
        val ink = Color(0xFF1B2A4A)
        drawCircle(g, 29f, Offset(110f, 43f)); drawCircle(ink, 29f, Offset(110f, 43f), style = Stroke(2f))
        drawPath(bodyOutline, g); drawPath(bodyOutline, ink, style = Stroke(2f, join = StrokeJoin.Round))
        drawPath(bodyLines, Color(0xFF87B9D5).copy(alpha = 0.8f), style = Stroke(1.3f))
        drawCircle(Brush.radialGradient(listOf(Color(0xFFFF765D), Color(0xFFFF957F).copy(alpha = 0.75f), Color(0x00FF957F)), Offset(133f, 281f), 30f), 30f, Offset(133f, 281f))
        drawCircle(Color(0xFFFF6F59).copy(alpha = 0.85f * (1 - p)), 14f + p * 22f, Offset(133f, 281f), style = Stroke(2f))
        drawCircle(Color(0xFFFF6F59), 7f, Offset(133f, 281f)); drawCircle(Color.White, 7f, Offset(133f, 281f), style = Stroke(2f))
        drawCircle(Color(0xFF55D99E), 6f, Offset(85f, 147f)); drawCircle(Color.White, 6f, Offset(85f, 147f), style = Stroke(2f))
        drawCircle(Color(0xFF42B8EF), 6f, Offset(136f, 147f)); drawCircle(Color.White, 6f, Offset(136f, 147f), style = Stroke(2f))
    }
}

private val kneeLegs = svgPath("M120 4c-18 42-24 84-10 103 9 12 9 21 2 38-12 27-18 58-12 86M180 4c18 42 24 84 10 103-9 12-9 21-2 38 12 27 18 58 12 86")

/** Genou agrandi (détail du jumeau). */
@Composable
fun KneeFigure(modifier: Modifier = Modifier) {
    SvgCanvas(modifier.fillMaxSize(), 300f, 235f, meet = true) {
        drawPath(kneeLegs, Color(0xFFD8E9F2), style = Stroke(56f, cap = StrokeCap.Round))
        drawPath(kneeLegs, Color(0xFF1B2A4A), style = Stroke(2f, cap = StrokeCap.Round))
        drawCircle(Brush.radialGradient(listOf(Color(0xF2FF967D), Color(0x00FF967D)), Offset(189f, 119f), 46f), 46f, Offset(189f, 119f))
        drawCircle(Color(0xFFFF755F), 13f, Offset(189f, 119f)); drawCircle(Color(0xFF1B2A4A), 13f, Offset(189f, 119f), style = Stroke(2f))
        drawLine(Color.White, Offset(161f, 119f), Offset(217f, 119f), 1.5f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f, 4f)))
        drawLine(Color.White, Offset(189f, 91f), Offset(189f, 147f), 1.5f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(4f, 4f)))
    }
}

/** ECG défilant en fond du jumeau. */
@Composable
fun Ecg(modifier: Modifier = Modifier) {
    val t = rememberInfiniteTransition(label = "ecg")
    val x by t.animateFloat(0f, 1f, infiniteRepeatable(tween(2500, easing = LinearEasing), RepeatMode.Restart), label = "x")
    val path = remember { svgPath("M0 35h70l10-13 12 34 15-49 14 28h45l9-10 11 20 13-10h191") }
    Canvas(modifier.fillMaxWidth().height(70.dp)) {
        val s = size.height / 70f
        for (k in 0..2) {
            withTransform({ translate(-x * 390f * s + k * 390f * s, 0f); scale(s, s, pivot = Offset.Zero) }) {
                drawPath(path, Color(0xFF1E88E5).copy(alpha = 0.4f), style = Stroke(2f))
            }
        }
    }
}
