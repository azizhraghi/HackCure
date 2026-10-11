/**
 * Camera capture page for the guided movement tests (Developer 1, d1 neuro). Runs inside a WebView (phone) or an
 * iframe (browser). MediaPipe runs on the device: the video never leaves it; only joint positions / face scores
 * ("frames", the format of d1 neuro Frame) are posted back to the app, which sends them to the backend.
 * Same conversion as backend/web/story.html. Config comes from window.__CAPTURE = { test, seconds, kinds, labels }.
 */
const html = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>
html,body{margin:0;height:100%;background:#0b1626;color:#fff;font-family:system-ui,sans-serif;overflow:hidden}
#wrap{position:relative;width:100%;height:100%}
video{width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
#msg{position:absolute;left:12px;right:12px;bottom:12px;padding:8px 12px;border-radius:14px;background:rgba(6,20,34,.78);font-size:14px;font-weight:700;text-align:center}
#count{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:84px;font-weight:900;text-shadow:0 2px 12px #000}
#bar{position:absolute;left:0;top:0;height:5px;background:#5fd8ff;width:0}
#rec{position:absolute;top:12px;left:12px;padding:4px 10px;border-radius:99px;background:#e5484d;font-size:12px;font-weight:800;display:none}
</style></head><body><div id="wrap"><video id="v" playsinline muted></video><div id="bar"></div><div id="rec">● REC</div><div id="count"></div><div id="msg"></div></div>
<script type="module">
const C = window.__CAPTURE || {};
const L = C.labels || {};
const send = m => { const d = JSON.stringify(m); if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(d); else parent.postMessage({ __motion: d }, '*'); };
const $ = id => document.getElementById(id);
const say = t => { $('msg').textContent = t; };
const MP = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14', MODELS = 'https://storage.googleapis.com/mediapipe-models';
const FILES = { pose: MODELS + '/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task',
  hands: MODELS + '/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
  face: MODELS + '/face_landmarker/face_landmarker/float16/latest/face_landmarker.task' };
const POSE_IDX = { nose: 0, left_shoulder: 11, right_shoulder: 12, left_elbow: 13, right_elbow: 14, left_wrist: 15, right_wrist: 16, left_index: 19, right_index: 20 };
function headAngles(m) {
  const r = (i, j) => m.data[j * 4 + i], deg = x => (x * 180) / Math.PI;
  return [deg(Math.atan2(-r(2, 0), Math.hypot(r(2, 1), r(2, 2)))), deg(Math.atan2(r(2, 1), r(2, 2))), deg(Math.atan2(r(1, 0), r(0, 0)))];
}
let stream = null;
const stop = () => { if (stream) stream.getTracks().forEach(t => t.stop()); stream = null; };
window.addEventListener('pagehide', stop);
async function run() {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error('camera_unavailable');
    say(L.loading || 'Loading…');
    const lib = await import(MP + '/vision_bundle.mjs');
    const files = await lib.FilesetResolver.forVisionTasks(MP + '/wasm');
    const models = {};
    for (const k of C.kinds) {
      const base = { modelAssetPath: FILES[k] };
      models[k] = k === 'pose' ? await lib.PoseLandmarker.createFromOptions(files, { baseOptions: base, runningMode: 'VIDEO', numPoses: 2 })
        : k === 'hands' ? await lib.HandLandmarker.createFromOptions(files, { baseOptions: base, runningMode: 'VIDEO', numHands: 2 })
        : await lib.FaceLandmarker.createFromOptions(files, { baseOptions: base, runningMode: 'VIDEO', numFaces: 2, outputFaceBlendshapes: true, outputFacialTransformationMatrixes: true });
    }
    stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: 'user' }, audio: false });
    const v = $('v'); v.srcObject = stream; await v.play();
    say(L.ready || 'Get ready');
    for (const n of [3, 2, 1]) { $('count').textContent = n; await new Promise(r => setTimeout(r, 800)); }
    $('count').textContent = ''; $('rec').style.display = 'block';
    const frames = [], t0 = performance.now(); let last = -1;
    await new Promise(resolve => {
      const tick = () => {
        const now = performance.now(), el = (now - t0) / 1000;
        $('bar').style.width = Math.min(100, (el / C.seconds) * 100) + '%';
        say((L.recording || 'Recording') + ' · ' + Math.max(0, Math.ceil(C.seconds - el)) + ' s');
        if (el >= C.seconds) return resolve();
        if (v.currentTime !== last) {
          last = v.currentTime;
          const f = { t: el, people: 1 };
          if (models.pose) { const r = models.pose.detectForVideo(v, now); f.people = Math.max(f.people, r.landmarks.length);
            if (r.landmarks.length) { f.pose = {}; for (const [n, i] of Object.entries(POSE_IDX)) { const p = r.landmarks[0][i]; f.pose[n] = [p.x, p.y, p.visibility ?? 0]; } } }
          if (models.hands) { const r = models.hands.detectForVideo(v, now);
            r.landmarks.forEach(pts => { const w = pts[0], p = f.pose; let side = 'right';
              if (p && p.left_wrist && p.right_wrist) { const d = s => Math.hypot(w.x - p[s + '_wrist'][0], w.y - p[s + '_wrist'][1]); side = d('left') < d('right') ? 'left' : 'right'; }
              f[side + '_hand'] = pts.map(q => [q.x, q.y]); }); }
          if (models.face) { const r = models.face.detectForVideo(v, now); f.people = Math.max(f.people, r.faceLandmarks.length);
            if (r.faceBlendshapes && r.faceBlendshapes.length) f.face = Object.fromEntries(r.faceBlendshapes[0].categories.map(c => [c.categoryName, c.score]));
            if (r.facialTransformationMatrixes && r.facialTransformationMatrixes.length) f.head = headAngles(r.facialTransformationMatrixes[0]); }
          frames.push(f);
        }
        requestAnimationFrame(tick);
      };
      tick();
    });
    stop();
    $('rec').style.display = 'none';
    say(L.measuring || 'Measuring…');
    send({ type: 'frames', frames });
  } catch (e) {
    stop();
    const reason = String((e && (e.name || e.message)) || e);
    say(L.failed || 'Camera not available');
    send({ type: 'error', reason });
  }
}
run();
</script></body></html>`;

export default html;
