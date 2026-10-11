package com.example.moniteur.ui.theme

import androidx.compose.ui.graphics.Color

/** Palette de l'app (portée de AppMobile/SurgiGuardApp/src/theme/tokens.ts). */
data class Palette(
    val bg: Color, val page: Color, val surface: Color, val ink: Color, val shadow: Color, val title: Color, val text: Color,
    val muted: Color, val faint: Color, val primary: Color, val onPrimary: Color,
    val blue: Color, val sky: Color, val task: Color, val green: Color, val pink: Color, val yellow: Color, val lavender: Color,
    val lilacBg: Color, val mint: Color, val ice: Color, val iceBlue: Color, val peach: Color, val amber: Color, val readonly: Color,
    val line: Color, val lineSoft: Color, val grey: Color, val switchOff: Color,
    val track: Color, val review: Color, val urgent: Color, val trackText: Color, val reviewText: Color, val urgentText: Color,
    val warnBorder: Color, val warnBg: Color, val warnDot: Color,
    val navBg: Color, val navLine: Color, val scrim: Color, val glass: Color, val quote: Color,
    val stageA: Color, val stageB: Color, val stageC: Color,
    val isDark: Boolean,
)

private fun c(hex: Long) = Color(0xFF000000 or hex)

val LightPalette = Palette(
    bg = c(0xf9fbff), page = c(0xedf2fa), surface = c(0xffffff), ink = c(0x1b2a4a), shadow = c(0x1b2a4a), title = c(0x111b31),
    text = c(0x1b2a4a), muted = c(0x64718a), faint = c(0x7d889c), primary = c(0x1e88e5), onPrimary = c(0xffffff),
    blue = c(0xdcefff), sky = c(0xa9e3fa), task = c(0x72c9f2), green = c(0xbff3d9), pink = c(0xf4c7ea), yellow = c(0xfbe19b),
    lavender = c(0xcdbbf6), lilacBg = c(0xeee9ff), mint = c(0xe7f9ef), ice = c(0xeef9fe), iceBlue = c(0xe2f5fc),
    peach = c(0xfff0d6), amber = c(0xfff3cf), readonly = c(0xeef1f6),
    line = c(0xe1e5ed), lineSoft = c(0xd9e5ed), grey = c(0xe4e9f2), switchOff = c(0xdce1e9),
    track = c(0x5ED3A0), review = c(0xFFB347), urgent = c(0xFF6B6B), trackText = c(0x218d65), reviewText = c(0xa65f00),
    urgentText = c(0xc64e48), warnBorder = c(0xef7168), warnBg = c(0xfff0ee), warnDot = c(0xff8d81),
    navBg = Color(0xF7FFFFFF), navLine = c(0xdde3ed), scrim = Color(0x471B2A4A), glass = Color(0xE0FFFFFF), quote = c(0xeef7ff),
    stageA = c(0xf9fdff), stageB = c(0xe4f2fb), stageC = c(0xe6def8),
    isDark = false,
)

val DarkPalette = Palette(
    bg = c(0x0e1628), page = c(0x0a1120), surface = c(0x16213a), ink = c(0x8fa3c9), shadow = c(0x03060d), title = c(0xf1f5ff),
    text = c(0xe6ecfa), muted = c(0x9aa8c2), faint = c(0x7f8daa), primary = c(0x2f93ea), onPrimary = c(0xffffff),
    blue = c(0x1d3253), sky = c(0x1d4660), task = c(0x1b5b7c), green = c(0x1a4637), pink = c(0x4a2946), yellow = c(0x4f431f),
    lavender = c(0x372d5e), lilacBg = c(0x221d3d), mint = c(0x15302a), ice = c(0x13283a), iceBlue = c(0x163049),
    peach = c(0x3d2e17), amber = c(0x3a3218), readonly = c(0x1b2741),
    line = c(0x26324d), lineSoft = c(0x26324d), grey = c(0x22304d), switchOff = c(0x2a3754),
    track = c(0x5ED3A0), review = c(0xFFB347), urgent = c(0xFF6B6B), trackText = c(0x6fe0b0), reviewText = c(0xffc070),
    urgentText = c(0xff8a84), warnBorder = c(0xef7168), warnBg = c(0x3a1c22), warnDot = c(0xff8d81),
    navBg = Color(0xF70E1628), navLine = c(0x26324d), scrim = Color(0x80000000), glass = Color(0xE616213A), quote = c(0x14263f),
    stageA = c(0x1a2a45), stageB = c(0x132238), stageC = c(0x211d3a),
    isDark = true,
)
