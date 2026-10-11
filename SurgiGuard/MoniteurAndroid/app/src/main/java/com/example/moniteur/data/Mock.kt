package com.example.moniteur.data

/** Données fictives du prototype HackCure (jumeau, bilan, médicaments, rééducation…). Les mesures sont SIMULÉES. */
object Mock {
    const val day = 6
    const val score = 87
    const val woundTemp = 36.9
    const val pain = 3
    const val sleep = "8.5h"

    enum class DoseState { TAKEN, SKIPPED }

    class Dose(val id: String, val med: String, val purpose: String, val time: String, val slot: String, val tone: String)

    val doses = listOf(
        Dose("d1", "meds.m1", "meds.m1p", "08:00", "morning", "pink"),
        Dose("d2", "meds.m3", "meds.m3p", "08:00", "morning", "sky"),
        Dose("d3", "meds.m2", "meds.m2p", "09:00", "morning", "yellow"),
        Dose("d4", "meds.m1", "meds.m1p", "14:00", "afternoon", "pink"),
        Dose("d5", "meds.m1", "meds.m1p", "20:00", "evening", "pink"),
        Dose("d6", "meds.m4", "meds.m4p", "20:00", "evening", "lavender"),
    )
}
