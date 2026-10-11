package com.example.moniteur

import android.content.Context
import org.json.JSONObject

/**
 * Traductions : res/raw/i18n_en.json et i18n_fr.json, générés depuis AppMobile/SurgiGuardApp/src/i18n
 * (clés à plat « home.title », interpolation {{n}}, listes séparées par « | »).
 */
class I18n(ctx: Context) {
    private val dicts: Map<String, Map<String, String>> = mapOf(
        "en" to load(ctx, R.raw.i18n_en),
        "fr" to load(ctx, R.raw.i18n_fr),
    )

    private fun load(ctx: Context, res: Int): Map<String, String> {
        val o = JSONObject(ctx.resources.openRawResource(res).bufferedReader().use { it.readText() })
        return o.keys().asSequence().associateWith { o.getString(it) }
    }

    fun t(lang: String, key: String, vararg args: Pair<String, Any?>): String {
        var s = dicts[lang]?.get(key) ?: dicts["en"]?.get(key) ?: return key
        for ((k, v) in args) s = s.replace("{{$k}}", v.toString())
        return s
    }
}
