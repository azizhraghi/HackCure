package com.example.moniteur.screens

import android.annotation.SuppressLint
import android.os.Handler
import android.os.Looper
import android.webkit.JavascriptInterface
import android.webkit.RenderProcessGoneDetail
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.example.moniteur.ui.BodyFigure
import com.example.moniteur.ui.T
import org.json.JSONObject

/** Commandes envoyées au jumeau 3D : rotate / zoom / reset. */
class Twin3DHandle {
    internal var web: WebView? = null
    fun command(cmd: String) = send(JSONObject().put("type", "cmd").put("cmd", cmd))
    internal fun send(msg: JSONObject) {
        val js = "window.dispatchEvent(new MessageEvent('message',{data:${JSONObject.quote(msg.toString())}}))"
        web?.post { web?.evaluateJavascript(js, null) }
    }
}

private var cachedHtml: String? = null

/**
 * Jumeau numérique 3D (three.js + modèle GLB) dans un WebView : même page HTML que l'app React Native
 * (assets/twin.html, générée depuis twinHtml.ts). Le shim ReactNativeWebView relaie les messages vers Kotlin.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun Twin3D(
    handle: Twin3DHandle,
    day: Int,
    layer: String,
    highlighted: String?,
    onTapKnee: () -> Unit,
    loadingLabel: String,
    fallbackLabel: String,
) {
    val ctx = LocalContext.current
    var ready by remember { mutableStateOf(false) }
    var failed by remember { mutableStateOf(false) }

    LaunchedEffect(ready, day, layer, highlighted) {
        if (ready) {
            handle.send(JSONObject().put("type", "state").put("day", day).put("layer", layer).put("highlighted", highlighted ?: JSONObject.NULL))
        }
    }

    if (failed) {
        Box(Modifier.fillMaxSize()) {
            Box(Modifier.align(Alignment.Center).padding(bottom = 40.dp)) { BodyFigure(110f, 228f) }
            T(fallbackLabel, Modifier.align(Alignment.BottomCenter).padding(bottom = 62.dp), size = 6f, w = 700, color = Color(0xFF70809A), center = true)
        }
        return
    }

    Box(Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { c ->
                val main = Handler(Looper.getMainLooper())
                WebView(c).apply {
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    setBackgroundColor(android.graphics.Color.TRANSPARENT)
                    overScrollMode = android.view.View.OVER_SCROLL_NEVER
                    isVerticalScrollBarEnabled = false
                    addJavascriptInterface(object {
                        @JavascriptInterface
                        fun postMessage(s: String) {
                            main.post {
                                runCatching {
                                    val m = JSONObject(s)
                                    when (m.optString("type")) {
                                        "ready" -> ready = true
                                        "error" -> failed = true
                                        "tap" -> if (m.optString("part") == "knee") onTapKnee()
                                    }
                                }
                            }
                        }
                    }, "NativeBridge")
                    webViewClient = object : WebViewClient() {
                        override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                            if (request?.isForMainFrame == true) failed = true
                        }
                        override fun onRenderProcessGone(view: WebView?, detail: RenderProcessGoneDetail?): Boolean { failed = true; return true }
                    }
                    val html = cachedHtml ?: ctx.assets.open("twin.html").bufferedReader().use { it.readText() }.also { cachedHtml = it }
                    val shim = "<script>window.ReactNativeWebView={postMessage:function(s){NativeBridge.postMessage(s)}}</script>"
                    handle.web = this
                    loadDataWithBaseURL("https://twin.local/", html.replaceFirst("<head>", "<head>$shim"), "text/html", "utf-8", null)
                }
            },
            onRelease = { it.destroy(); handle.web = null },
        )
        if (!ready) {
            Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally) {
                CircularProgressIndicator(Modifier.size(26.dp), color = Color(0xFF1E88E5), strokeWidth = 2.dp)
                T(loadingLabel, Modifier.padding(top = 8.dp), size = 8f, w = 700, color = Color(0xFF70809A))
            }
        }
    }
}
