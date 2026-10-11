package com.example.moniteur.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Matrix
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.moniteur.ui.theme.Pal

/** Même jeu d'icônes (traits) que le prototype Figma / l'app React Native, viewBox 24x24. */
enum class IconName {
    arrow, bell, search, camera, upload, image, file, check, home, checkin, twin, report, profile, close, phone, message,
    thermo, drop, activity, rotate, scan, sensor, pill, sparkle, calendar, globe, moon, gear, send, shield, plus, chevron, heart,
}

private fun circle(cx: Float, cy: Float, r: Float) = "M${cx - r},${cy}a$r,$r 0 1,0 ${2 * r},0a$r,$r 0 1,0 ${-2 * r},0z"

private fun rect(x: Float, y: Float, w: Float, h: Float, r: Float) =
    "M${x + r},${y}h${w - 2 * r}a$r,$r 0 0 1 $r,${r}v${h - 2 * r}a$r,$r 0 0 1 ${-r},${r}h${-(w - 2 * r)}a$r,$r 0 0 1 ${-r},${-r}v${-(h - 2 * r)}a$r,$r 0 0 1 $r,${-r}z"

private class IconDef(val paths: List<String>, val rotateDeg: Float = 0f)

private fun def(vararg p: String, rotate: Float = 0f) = IconDef(p.toList(), rotate)

private fun iconDef(name: IconName): IconDef = when (name) {
    IconName.arrow -> def("m15 18-6-6 6-6")
    IconName.chevron -> def("m9 18 6-6-6-6")
    IconName.bell -> def("M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9", "M10 21h4")
    IconName.search -> def(circle(11f, 11f, 7f), "m20 20-4-4")
    IconName.camera -> def("M4 7h3l2-3h6l2 3h3v12H4z", circle(12f, 13f, 4f))
    IconName.upload -> def("M12 16V4m-5 5 5-5 5 5", "M5 16v4h14v-4")
    IconName.image -> def(rect(3f, 4f, 18f, 16f, 2f), circle(9f, 10f, 2f), "m3 17 5-5 4 4 3-3 6 6")
    IconName.file -> def("M6 2h8l4 4v16H6z", "M14 2v5h5M9 12h6M9 16h6")
    IconName.check -> def("m5 12 4 4L19 6")
    IconName.home -> def("m3 11 9-8 9 8", "M5 10v10h14V10M9 20v-6h6v6")
    IconName.checkin -> def(circle(12f, 12f, 9f), "m8 12 3 3 5-6")
    IconName.twin -> def(circle(12f, 5f, 3f), "M8 22v-6l-2-4 3-3h6l3 3-2 4v6M9 10l3 5 3-5")
    IconName.report -> def("M5 20V10M12 20V4M19 20v-7", "M3 20h18")
    IconName.profile -> def(circle(12f, 8f, 4f), "M4 21a8 8 0 0 1 16 0")
    IconName.close -> def("m7 7 10 10M17 7 7 17")
    IconName.phone -> def("M7 3h3l2 5-2 2a15 15 0 0 0 4 4l2-2 5 2v3c0 2-2 4-4 4A14 14 0 0 1 3 7c0-2 2-4 4-4Z")
    IconName.message -> def("M4 4h16v13H8l-4 4z")
    IconName.thermo -> def("M10 14.8V5a2 2 0 1 1 4 0v9.8a4 4 0 1 1-4 0Z", "M12 9v8")
    IconName.drop -> def("M12 2s7 8 7 13a7 7 0 0 1-14 0c0-5 7-13 7-13Z")
    IconName.activity -> def("M2 12h4l2-7 4 14 3-10 2 3h5")
    IconName.rotate -> def("M20 7a9 9 0 0 0-15-2L3 7", "M3 3v4h4M4 17a9 9 0 0 0 15 2l2-2", "M21 21v-4h-4")
    IconName.scan -> def("M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5", circle(12f, 12f, 4f))
    IconName.sensor -> def(circle(12f, 12f, 2f), "M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2")
    IconName.pill -> def(rect(2.5f, 8f, 19f, 8f, 4f), "m9.5 8.4 5 7.2", rotate = -35f)
    IconName.sparkle -> def(
        "M12 3c.6 4.2 2.8 6.4 7 7-4.2.6-6.4 2.8-7 7-.6-4.2-2.8-6.4-7-7 4.2-.6 6.4-2.8 7-7ZM19 16c.3 1.6 1 2.3 2.6 2.6-1.6.3-2.3 1-2.6 2.6-.3-1.6-1-2.3-2.6-2.6 1.6-.3 2.3-1 2.6-2.6Z",
    )
    IconName.calendar -> def(rect(3f, 5f, 18f, 16f, 3f), "M3 10h18M8 3v4M16 3v4")
    IconName.globe -> def(circle(12f, 12f, 9f), "M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18")
    IconName.moon -> def("M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z")
    IconName.gear -> def(circle(12f, 12f, 3f), "M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1")
    IconName.send -> def("M3 11 21 3l-8 18-2-8-8-2Z")
    IconName.shield -> def("M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5l8-3Z")
    IconName.plus -> def("M12 5v14M5 12h14")
    IconName.heart -> def("M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z")
}

private val cache = HashMap<IconName, List<Path>>()

private fun pathsOf(name: IconName): List<Path> = cache.getOrPut(name) {
    val d = iconDef(name)
    d.paths.map { s ->
        val p = PathParser().parsePathString(s).toPath()
        if (d.rotateDeg != 0f) {
            val m = Matrix()
            m.translate(12f, 12f)
            m.rotateZ(d.rotateDeg)
            m.translate(-12f, -12f)
            p.transform(m)
        }
        p
    }
}

@Composable
fun Icon(name: IconName, size: Dp = 20.dp, color: Color? = null, strokeWidth: Float = 1.8f) {
    val tint = color ?: Pal.c.text
    val paths = remember(name) { pathsOf(name) }
    Canvas(Modifier.size(size)) {
        val s = this.size.width / 24f
        withTransform({ scale(s, s, pivot = Offset.Zero) }) {
            paths.forEach { drawPath(it, tint, style = Stroke(width = strokeWidth, cap = StrokeCap.Round, join = StrokeJoin.Round)) }
        }
    }
}
