package com.example.moniteur.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import com.example.moniteur.R

val LocalPalette = staticCompositionLocalOf { LightPalette }

val Jakarta = FontFamily(
    Font(R.font.jakarta_regular, FontWeight.Normal),
    Font(R.font.jakarta_medium, FontWeight.Medium),
    Font(R.font.jakarta_semibold, FontWeight.SemiBold),
    Font(R.font.jakarta_bold, FontWeight.Bold),
    Font(R.font.jakarta_extrabold, FontWeight.ExtraBold),
)

/** Poids CSS du prototype (400..800) -> FontWeight. */
fun weightOf(w: Int): FontWeight = when {
    w >= 800 -> FontWeight.ExtraBold
    w >= 700 -> FontWeight.Bold
    w >= 600 -> FontWeight.SemiBold
    w >= 500 -> FontWeight.Medium
    else -> FontWeight.Normal
}

/**
 * Les tailles Figma (5-9 px) sont illisibles sur un téléphone : les petites tailles sont remontées
 * vers 12, les grandes restent exactes (même règle que fs() dans l'app React Native).
 */
fun fs(size: Float): Float = if (size >= 12f) size else Math.round((size + (12f - size) * 0.42f) * 10f) / 10f

@Composable
fun MoniteurTheme(dark: Boolean, content: @Composable () -> Unit) {
    val p = if (dark) DarkPalette else LightPalette
    val scheme = if (dark) {
        darkColorScheme(primary = p.primary, background = p.bg, surface = p.surface, onSurface = p.text, onBackground = p.text)
    } else {
        lightColorScheme(primary = p.primary, background = p.bg, surface = p.surface, onSurface = p.text, onBackground = p.text)
    }
    CompositionLocalProvider(LocalPalette provides p) {
        MaterialTheme(colorScheme = scheme, content = content)
    }
}

object Pal {
    val c: Palette @Composable get() = LocalPalette.current
}
