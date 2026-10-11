package com.example.moniteur.screens

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.example.moniteur.LocalApp
import com.example.moniteur.data.ApiError
import com.example.moniteur.ui.Button
import com.example.moniteur.ui.Card
import com.example.moniteur.ui.Chip
import com.example.moniteur.ui.Icon
import com.example.moniteur.ui.IconName
import com.example.moniteur.ui.RoundButton
import com.example.moniteur.ui.Screen
import com.example.moniteur.ui.T
import com.example.moniteur.ui.TopBar
import com.example.moniteur.ui.t
import com.example.moniteur.ui.tap
import com.example.moniteur.ui.theme.Pal
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File

/**
 * Photo de la plaie au changement de pansement (D1-F), branchée sur l'API .NET qui relaie vers le backend IA :
 * fenêtre de pansement du plan de soins, confirmation du patient, photo (appareil photo ou galerie), puis
 * contour calculé par OpenCV, qualité, comparaison avec la photo de référence, description par un LLM vision.
 * Rien n'est un diagnostic : l'équipe soignante regarde la photo.
 */
@Composable
fun WoundScanScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf<JSONObject?>(null) }
    var confirmed by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var preview by remember { mutableStateOf<Bitmap?>(null) }
    var result by remember { mutableStateOf<JSONObject?>(null) }
    var overlay by remember { mutableStateOf<Bitmap?>(null) }
    val photoFile = remember { File(ctx.cacheDir, "wound_capture.jpg") }
    val photoUri = remember { FileProvider.getUriForFile(ctx, ctx.packageName + ".files", photoFile) }

    LaunchedEffect(Unit) { status = runCatching { app.api.wound() }.getOrNull() }

    fun send(bytes: ByteArray) {
        busy = true; error = null; result = null; overlay = null
        scope.launch {
            try {
                val r = app.api.uploadWoundPhoto(bytes, confirmed)
                result = r
                // La lecture par l'IA arrive après l'analyse par le code : on recharge la photo quelques fois
                repeat(15) {
                    val d1 = result?.optJSONObject("d1")
                    if (overlay == null && d1 != null && !d1.isNull("overlay_url")) {
                        overlay = app.api.woundMedia(d1.getString("overlay_url"))?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }
                    }
                    if (result?.optJSONObject("vision_review") != null) return@launch
                    delay(2000)
                    val list = runCatching { app.api.wound() }.getOrNull()?.optJSONArray("photos")
                    val id = r.optString("observation_id")
                    for (i in 0 until (list?.length() ?: 0)) {
                        val p = list!!.getJSONObject(i)
                        if (p.optString("observation_id") == id) result = p
                    }
                }
            } catch (e: ApiError) {
                error = if (e.status == 0) t0(app, "scan.failed") else e.message
            } finally {
                busy = false
            }
        }
    }

    fun sendUri(uri: Uri) {
        val bmp = ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) } ?: return
        val scaled = scaleDown(bmp, 1600)
        preview = scaled
        val out = ByteArrayOutputStream()
        scaled.compress(Bitmap.CompressFormat.JPEG, 90, out)
        send(out.toByteArray())
    }

    val takePicture = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok -> if (ok) sendUri(photoUri) }
    val pickPhoto = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> if (uri != null) sendUri(uri) }

    val st = status?.optJSONObject("status")
    val permitted = st?.optBoolean("permitted") == true
    Screen(padded = true) {
        TopBar(t("scan.top"), action = { RoundButton(IconName.close, { app.pop() }) })
        Card(Modifier.fillMaxWidth(), pad = 14f, radius = 20f) {
            T(t("scan.dressingTitle"), size = 14f, w = 800)
            T(st?.optString("reason") ?: t("scan.loading"), Modifier.padding(top = 4.dp), size = 9f, color = if (permitted) c.text else c.reviewText)
            Row(Modifier.padding(top = 10.dp).tap { confirmed = !confirmed }, verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(22.dp).background(if (confirmed) c.green else c.surface, RoundedCornerShape(5.dp)).border(1.4.dp, c.ink, RoundedCornerShape(5.dp)), contentAlignment = Alignment.Center) {
                    if (confirmed) Icon(IconName.check, 15.dp)
                }
                T(t("scan.confirm"), Modifier.padding(start = 8.dp), size = 9f, w = 700)
            }
            Row(Modifier.padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(t("scan.takePhoto"), { takePicture.launch(photoUri) }, Modifier.weight(1f), icon = IconName.camera, enabled = confirmed && !busy)
                Button(t("scan.choosePhoto"), { pickPhoto.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) },
                    Modifier.weight(1f), secondary = true, enabled = confirmed && !busy)
            }
        }

        if (busy && result == null) Row(Modifier.padding(top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp); T(t("scan.captured"), Modifier.padding(start = 8.dp), size = 9f)
        }
        error?.let { T("${t("scan.failed")} ($it)", Modifier.padding(top = 10.dp), size = 9f, color = c.urgentText) }

        val r = result
        val d1 = r?.optJSONObject("d1")
        if (r != null && d1 != null) {
            Card(Modifier.fillMaxWidth().padding(top = 12.dp), pad = 12f, radius = 18f) {
                T(t("scan.d1Title"), size = 6f, color = c.muted)
                val img = overlay ?: preview
                img?.let {
                    Image(it.asImageBitmap(), null, Modifier.fillMaxWidth().padding(top = 6.dp).aspectRatio(it.width.toFloat() / it.height).clip(RoundedCornerShape(10.dp)), contentScale = ContentScale.Fit)
                }
                val seg = d1.optJSONObject("segmentation")
                T(if (seg?.optBoolean("found") == true) t("scan.d1Outlined") else t("scan.d1NotFound"), Modifier.padding(top = 4.dp), size = 8f, color = c.muted)
                val q = d1.optJSONObject("quality")
                val cmp = d1.optJSONObject("comparison")
                FlowRow(Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(5.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Chip(t("scan.d1Quality") + ": " + (q?.optString("status") ?: "?"), tone = if (q?.optString("status") == "good") "green" else "yellow")
                    if (cmp == null) Chip(t("scan.d1Reference"), tone = "blue")
                    else Chip(if (cmp.optBoolean("available")) cmp.optString("summary") else t("scan.notCompared"), tone = if (cmp.optString("trend") == "more_red") "yellow" else "blue")
                }
                val problems = q?.optJSONArray("problems")
                if (problems != null && problems.length() > 0) {
                    T("⚠ " + (0 until problems.length()).joinToString(" · ") { problems.getString(it) } + ": " + t("scan.retakeHint"),
                        Modifier.padding(top = 6.dp), size = 8.5f, w = 700, color = c.reviewText)
                }
                T(t("scan.d1Ai"), Modifier.padding(top = 10.dp), size = 9f, w = 800)
                val v = r.optJSONObject("vision_review")
                when {
                    v == null -> Row(Modifier.padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(Modifier.size(14.dp), strokeWidth = 2.dp); T(t("scan.d1AiPending"), Modifier.padding(start = 6.dp), size = 8f, color = c.muted)
                    }
                    v.optBoolean("available") -> Column(Modifier.padding(top = 4.dp)) {
                        val f = v.optJSONArray("findings")
                        if (f == null || f.length() == 0) T(t("scan.d1AiNothing"), size = 8f, color = c.muted)
                        for (i in 0 until (f?.length() ?: 0)) {
                            val o = f!!.getJSONObject(i)
                            T("• " + o.optString("finding") + "  (" + o.optString("confidence") + ")", size = 8.5f)
                        }
                        if (v.optString("mode") != "live") T(v.optString("uncertainty"), Modifier.padding(top = 2.dp), size = 7.5f, color = c.muted)
                    }
                    else -> T(v.optString("reason"), Modifier.padding(top = 4.dp), size = 8f, color = c.muted)
                }
                T(if (!r.isNull("review_alert_id") && r.optString("review_alert_id").isNotEmpty()) t("scan.d1Review") else t("scan.d1Received"),
                    Modifier.padding(top = 10.dp), size = 9f, w = 700)
            }
        }
        T(t("scan.disclaimerD1"), Modifier.padding(vertical = 10.dp), size = 7f, color = c.muted)
        Button(if (result != null) t("scan.saved") else t("common.close"), { app.pop() })
    }
}

private fun t0(app: com.example.moniteur.AppViewModel, key: String) = app.t(key)

private fun scaleDown(b: Bitmap, maxSide: Int): Bitmap {
    val s = maxSide.toFloat() / maxOf(b.width, b.height)
    return if (s >= 1f) b else Bitmap.createScaledBitmap(b, (b.width * s).toInt(), (b.height * s).toInt(), true)
}
