package com.example.moniteur.screens

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import android.util.Size
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
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

/**
 * Photo de la plaie quand le patient change son pansement (D1-F).
 * La caméra s'ouvre directement dans l'écran (CameraX) avec un cadre de visée ; le patient déclenche, vérifie la photo,
 * confirme qu'il change son pansement maintenant, puis l'envoie : API .NET -> backend IA (contour OpenCV, qualité,
 * comparaison avec la photo de référence, description par un LLM vision). Rien n'est un diagnostic.
 */
@Composable
fun WoundScanScreen() {
    val c = Pal.c
    val app = LocalApp.current
    val ctx = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()

    var hasCamera by remember { mutableStateOf(ContextCompat.checkSelfPermission(ctx, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) }
    var status by remember { mutableStateOf<JSONObject?>(null) }
    var confirmed by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var shot by remember { mutableStateOf<Bitmap?>(null) }      // photo prise, pas encore envoyée
    var result by remember { mutableStateOf<JSONObject?>(null) }
    var overlay by remember { mutableStateOf<Bitmap?>(null) }
    var torch by remember { mutableStateOf(false) }
    // ~2 Mpx suffisent pour l'analyse ; la pleine résolution (48 Mpx sur certains téléphones = 192 Mo) fait planter l'affichage
    val imageCapture = remember {
        ImageCapture.Builder()
            .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
            .setResolutionSelector(ResolutionSelector.Builder().setResolutionStrategy(
                ResolutionStrategy(Size(1920, 1440), ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER)).build())
            .build()
    }
    var camera by remember { mutableStateOf<androidx.camera.core.Camera?>(null) }

    val askCamera = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { hasCamera = it }
    LaunchedEffect(Unit) {
        if (!hasCamera) askCamera.launch(Manifest.permission.CAMERA)
        status = runCatching { app.api.wound() }.getOrNull()
    }
    LaunchedEffect(torch, camera) { camera?.cameraControl?.enableTorch(torch) }

    fun send(bmp: Bitmap) {
        busy = true; error = null; result = null; overlay = null
        val out = ByteArrayOutputStream()
        scaleDown(bmp, 1600).compress(Bitmap.CompressFormat.JPEG, 90, out)
        scope.launch {
            try {
                val r = app.api.uploadWoundPhoto(out.toByteArray(), confirmed)
                result = r
                // L'analyse par le code est immédiate ; la lecture par l'IA arrive ensuite : on recharge quelques fois
                repeat(40) {  // the trained model + evidence map take ~10-20 s on the server CPU
                    val d1 = result?.optJSONObject("d1")
                    if (overlay == null && d1 != null && !d1.isNull("overlay_url")) {
                        overlay = app.api.woundMedia(d1.getString("overlay_url"))?.let { BitmapFactory.decodeByteArray(it, 0, it.size) }
                    }
                    if (result?.optJSONObject("vision_review") != null) return@launch
                    delay(2000)
                    val list = runCatching { app.api.wound() }.getOrNull()?.optJSONArray("photos")
                    for (i in 0 until (list?.length() ?: 0)) {
                        val p = list!!.getJSONObject(i)
                        if (p.optString("observation_id") == r.optString("observation_id")) result = p
                    }
                }
            } catch (e: ApiError) {
                error = if (e.status == 0) app.t("scan.failed") else e.message
            } finally {
                busy = false
            }
        }
    }

    fun capture() {
        imageCapture.takePicture(ContextCompat.getMainExecutor(ctx), object : ImageCapture.OnImageCapturedCallback() {
            override fun onCaptureSuccess(image: ImageProxy) {
                shot = image.toUprightBitmap()
                image.close()
                torch = false
            }
            override fun onError(exception: ImageCaptureException) { error = exception.message }
        })
    }

    val pickPhoto = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri: Uri? ->
        if (uri != null) shot = decodeSampled(ctx, uri, 1600)
    }

    val st = status?.optJSONObject("status")
    Screen(padded = true) {
        TopBar(t("scan.top"), action = { RoundButton(IconName.close, { app.pop() }) })

        // ---------------------------------------------------------------- caméra / photo prise
        Box(Modifier.fillMaxWidth().height(420.dp).clip(RoundedCornerShape(22.dp)).background(Color(0xFF1B2533)), contentAlignment = Alignment.Center) {
            val taken = result?.let { overlay } ?: shot
            when {
                taken != null -> Image(taken.asImageBitmap(), null, Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
                hasCamera -> {
                    AndroidView(
                        factory = { context ->
                            PreviewView(context).also { view ->
                                view.scaleType = PreviewView.ScaleType.FILL_CENTER
                                val future = ProcessCameraProvider.getInstance(context)
                                future.addListener({
                                    val provider = future.get()
                                    val preview = Preview.Builder().build().also { it.surfaceProvider = view.surfaceProvider }
                                    provider.unbindAll()
                                    camera = runCatching {
                                        provider.bindToLifecycle(lifecycle, CameraSelector.DEFAULT_BACK_CAMERA, preview, imageCapture)
                                    }.recoverCatching {
                                        provider.bindToLifecycle(lifecycle, CameraSelector.DEFAULT_FRONT_CAMERA, preview, imageCapture)
                                    }.getOrElse { e -> error = e.message; null }
                                }, ContextCompat.getMainExecutor(context))
                            }
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                    Box(Modifier.align(Alignment.Center)) { Corners() }
                    Chip(t("scan.align"), Modifier.align(Alignment.TopCenter).padding(top = 12.dp), tone = "dark")
                }
                else -> Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(24.dp)) {
                    Icon(IconName.camera, 34.dp, Color.White)
                    T(t("scan.permission"), Modifier.padding(top = 8.dp), size = 9f, color = Color.White, center = true)
                    Button(t("scan.allow"), { askCamera.launch(Manifest.permission.CAMERA) }, Modifier.padding(top = 10.dp))
                }
            }
            // barre du bas : galerie · déclencheur · lampe   (ou reprendre une fois la photo prise)
            Row(Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(horizontal = 24.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                if (shot == null) {
                    T(t("scan.choosePhoto"), Modifier.tap { pickPhoto.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }, size = 8f, w = 700, color = Color.White)
                    Box(Modifier.size(66.dp).background(c.primary, CircleShape).border(4.dp, Color.White, CircleShape)
                        .tap(enabled = hasCamera && camera != null) { capture() }, contentAlignment = Alignment.Center) { Icon(IconName.camera, 28.dp, Color.White) }
                    T(if (torch) t("scan.flashOn") else t("scan.flashOff"), Modifier.tap { torch = !torch }, size = 8f, w = 700, color = Color.White)
                } else if (result == null && !busy) {
                    Chip(t("scan.retake"), Modifier.tap { shot = null; error = null }, tone = "dark")
                }
            }
        }

        // ---------------------------------------------------------------- confirmation + envoi
        if (shot != null && result == null) {
            Card(Modifier.fillMaxWidth().padding(top = 10.dp), pad = 14f, radius = 20f) {
                Row(Modifier.tap { confirmed = !confirmed }, verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(22.dp).background(if (confirmed) c.green else c.surface, RoundedCornerShape(5.dp)).border(1.4.dp, c.ink, RoundedCornerShape(5.dp)), contentAlignment = Alignment.Center) {
                        if (confirmed) Icon(IconName.check, 15.dp)
                    }
                    T(t("scan.confirm"), Modifier.padding(start = 8.dp), size = 9f, w = 700)
                }
                if (st != null && !st.optBoolean("permitted")) T(t("scan.outsideWindow"), Modifier.padding(top = 6.dp), size = 8f, color = c.muted)
                Button(if (busy) t("scan.captured") else t("scan.analyse"), { shot?.let { send(it) } }, Modifier.padding(top = 10.dp),
                    icon = IconName.camera, enabled = confirmed && !busy)
                if (busy) Row(Modifier.padding(top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp); T(t("scan.captured"), Modifier.padding(start = 8.dp), size = 8.5f)
                }
            }
        }
        error?.let { T("${t("scan.failed")} ($it)", Modifier.padding(top = 10.dp), size = 9f, color = c.urgentText) }

        // ---------------------------------------------------------------- résultat
        val r = result
        val d1 = r?.optJSONObject("d1")
        if (r != null && d1 != null) {
            Card(Modifier.fillMaxWidth().padding(top = 12.dp), pad = 12f, radius = 18f) {
                T(t("scan.d1Title"), size = 6f, color = c.muted)
                val seg = d1.optJSONObject("segmentation")
                T(if (seg?.optBoolean("found") == true) t("scan.d1Outlined") else t("scan.d1NotFound"), Modifier.padding(top = 4.dp), size = 8.5f)
                val q = d1.optJSONObject("quality")
                val cmp = d1.optJSONObject("comparison")
                FlowRow(Modifier.padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(5.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Chip(t("scan.d1Quality") + ": " + (q?.optString("status") ?: "?"), tone = if (q?.optString("status") == "good") "green" else "yellow")
                    if (cmp == null) Chip(t("scan.d1Reference"), tone = "blue")
                    else Chip(if (cmp.optBoolean("available")) cmp.optString("summary") else t("scan.notCompared"), tone = if (cmp.optString("trend") == "more_red") "yellow" else "blue")
                    if (r.optBoolean("outside_planned_window")) Chip(t("scan.patientInitiated"), tone = "lavender")
                }
                val problems = q?.optJSONArray("problems")
                if (problems != null && problems.length() > 0) {
                    T("⚠ " + (0 until problems.length()).joinToString(" · ") { problems.getString(it) } + ": " + t("scan.retakeHint"),
                        Modifier.padding(top = 6.dp), size = 8.5f, w = 700, color = c.reviewText)
                }
                val md = r.optJSONObject("model")
                val attrs = md?.optJSONObject("attributes")
                if (md?.optBoolean("available") == true && attrs != null) {
                    T(t("scan.modelTitle"), Modifier.padding(top = 10.dp), size = 9f, w = 800)
                    if (!md.optBoolean("in_distribution", true)) T(t("scan.modelUnfamiliar"), size = 8.5f, color = c.reviewText)
                    val shown = md.optJSONArray("patient_attributes")
                    for (i in 0 until (shown?.length() ?: 0)) {
                        val a = attrs.optJSONObject(shown!!.getString(i)) ?: continue
                        T("• " + a.optString("text"), size = 8.5f, color = if (a.optString("decision") == "yes") c.reviewText else c.text)
                    }
                    T(t("scan.modelNote"), Modifier.padding(top = 2.dp), size = 7.5f, color = c.muted)
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
                T(if (r.optString("review_alert_id").let { it.isNotEmpty() && it != "null" }) t("scan.d1Review") else t("scan.d1Received"),
                    Modifier.padding(top = 10.dp), size = 9f, w = 700)
            }
            Button(t("scan.newPhoto"), { shot = null; result = null; overlay = null; confirmed = false }, Modifier.padding(top = 10.dp), secondary = true)
        }
        T(t("scan.disclaimerD1"), Modifier.padding(vertical = 10.dp), size = 7f, color = c.muted)
        Button(if (result != null) t("scan.saved") else t("common.close"), { app.pop() })
    }

    DisposableEffect(Unit) { onDispose { runCatching { camera?.cameraControl?.enableTorch(false) } } }
}

/** Image de la caméra réduite (côté max 1600 px) et remise à l'endroit (rotation du capteur). */
private fun ImageProxy.toUprightBitmap(): Bitmap {
    val full = toBitmap()
    val small = scaleDown(full, 1600)
    if (small !== full) full.recycle()
    val deg = imageInfo.rotationDegrees
    if (deg == 0) return small
    val m = Matrix().apply { postRotate(deg.toFloat()) }
    return Bitmap.createBitmap(small, 0, 0, small.width, small.height, m, true)
}

/** Photo de la galerie décodée directement en taille réduite (jamais la pleine résolution en mémoire). */
private fun decodeSampled(ctx: android.content.Context, uri: Uri, maxSide: Int): Bitmap? {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
    var sample = 1
    while (maxOf(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
    val opts = BitmapFactory.Options().apply { inSampleSize = sample }
    return ctx.contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opts) }?.let { scaleDown(it, maxSide) }
}

private fun scaleDown(b: Bitmap, maxSide: Int): Bitmap {
    val s = maxSide.toFloat() / maxOf(b.width, b.height)
    return if (s >= 1f) b else Bitmap.createScaledBitmap(b, (b.width * s).toInt(), (b.height * s).toInt(), true)
}
