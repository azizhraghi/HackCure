// 3D Recovery Twin rendered inside a WebView.
// Built into src/components/twin/twinHtml.ts by scripts/build-twin.mjs.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

const post = msg => window.ReactNativeWebView && window.ReactNativeWebView.postMessage(JSON.stringify(msg));

function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch (e) {
    return false;
  }
}

const state = { day: 4, layer: 'Overview', highlighted: null, dark: false };
const NAVY = 0x1b2a4a;

function radialTexture(stops) {
  const size = 128;
  const cv = document.createElement('canvas');
  cv.width = cv.height = size;
  const ctx = cv.getContext('2d');
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  stops.forEach(([o, col]) => g.addColorStop(o, col));
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function textSprite(text) {
  const cv = document.createElement('canvas');
  cv.width = 256;
  cv.height = 128;
  const ctx = cv.getContext('2d');
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  sprite.renderOrder = 20;
  sprite.update = value => {
    ctx.clearRect(0, 0, 256, 128);
    ctx.fillStyle = 'rgba(255,255,255,0.92)';
    ctx.strokeStyle = '#1b2a4a';
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.roundRect(8, 24, 240, 80, 24);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#1b2a4a';
    ctx.font = '800 54px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(value, 128, 66);
    tex.needsUpdate = true;
  };
  sprite.update(text);
  return sprite;
}

function glassMaterial() {
  const m = new THREE.MeshPhysicalMaterial({
    color: 0xc6e6f4,
    roughness: 0.22,
    metalness: 0,
    clearcoat: 1,
    clearcoatRoughness: 0.12,
    transparent: true,
    opacity: 0.8,
    emissive: 0x2f6f96,
    emissiveIntensity: 0.1,
    depthWrite: true,
  });
  // Fresnel rim light, like the "rimLight" gradient of the 2D design
  m.onBeforeCompile = shader => {
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <emissivemap_fragment>',
      `#include <emissivemap_fragment>
       float sgFres = pow(1.0 - clamp(dot(normalize(vViewPosition), normal), 0.0, 1.0), 2.4);
       totalEmissiveRadiance += vec3(0.49, 0.80, 0.94) * sgFres * 1.25;`,
    );
  };
  return m;
}

function outlineMaterial() {
  const m = new THREE.MeshBasicMaterial({ color: NAVY, side: THREE.BackSide });
  m.onBeforeCompile = shader => {
    shader.vertexShader = shader.vertexShader.replace(
      '#include <begin_vertex>',
      `#include <begin_vertex>
       transformed += normalize(objectNormal) * 0.0085;`,
    );
  };
  return m;
}

function init() {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  document.body.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, window.innerWidth / window.innerHeight, 0.01, 100);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enablePan = false;
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minPolarAngle = 0.5;
  controls.maxPolarAngle = Math.PI - 0.6;
  controls.autoRotateSpeed = 2.2;

  scene.add(new THREE.HemisphereLight(0xffffff, 0xb7d7ec, 1.7));
  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(-2, 3, 3);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x7ccbf0, 2.4);
  rim.position.set(2, 2, -3);
  scene.add(rim);

  const root = new THREE.Group();
  scene.add(root);

  const H = 1.8; // model height after normalisation
  const overlays = new THREE.Group();
  root.add(overlays);

  // Platform rings (.platform in the design)
  const ringMat = new THREE.MeshBasicMaterial({ color: 0x1e88e5, transparent: true, opacity: 0.18, side: THREE.DoubleSide });
  const ring1 = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.44, 64), ringMat);
  const ring2 = new THREE.Mesh(new THREE.RingGeometry(0.27, 0.285, 64), ringMat.clone());
  ring2.material.opacity = 0.3;
  const disc = new THREE.Mesh(new THREE.CircleGeometry(0.42, 64), new THREE.MeshBasicMaterial({ color: 0x1e88e5, transparent: true, opacity: 0.06 }));
  [ring1, ring2, disc].forEach(r => { r.rotation.x = -Math.PI / 2; r.position.y = 0.002; root.add(r); });
  const dashPts = new THREE.Path().absarc(0, 0, 0.35, 0, Math.PI * 2).getPoints(96);
  const dashed = new THREE.Line(new THREE.BufferGeometry().setFromPoints(dashPts), new THREE.LineDashedMaterial({ color: 0x1e88e5, dashSize: 0.03, gapSize: 0.025, transparent: true, opacity: 0.7 }));
  dashed.computeLineDistances();
  dashed.rotation.x = -Math.PI / 2;
  dashed.position.y = 0.004;
  root.add(dashed);

  // Hotspot
  const glowTex = radialTexture([[0, 'rgba(255,179,71,0.95)'], [0.45, 'rgba(255,207,121,0.5)'], [1, 'rgba(255,179,71,0)']]);
  const heatTex = radialTexture([[0, 'rgba(255,107,107,0.95)'], [0.35, 'rgba(251,225,155,0.85)'], [0.7, 'rgba(66,184,239,0.6)'], [1, 'rgba(66,184,239,0)']]);
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, depthTest: false, transparent: true }));
  glow.renderOrder = 10;
  const pulse = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTexture([[0, 'rgba(255,179,71,0)'], [0.82, 'rgba(255,179,71,0)'], [0.9, 'rgba(255,179,71,0.9)'], [1, 'rgba(255,179,71,0)']]), depthTest: false, transparent: true }));
  pulse.renderOrder = 11;
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.022, 24, 16), new THREE.MeshBasicMaterial({ color: 0xff755f, depthTest: false }));
  core.renderOrder = 12;
  const coreRing = new THREE.Mesh(new THREE.TorusGeometry(0.026, 0.005, 8, 32), new THREE.MeshBasicMaterial({ color: 0xffffff, depthTest: false }));
  coreRing.renderOrder = 13;
  const hit = new THREE.Mesh(new THREE.SphereGeometry(0.13, 12, 8), new THREE.MeshBasicMaterial({ visible: false }));
  const hotspot = new THREE.Group();
  hotspot.add(glow, pulse, core, coreRing, hit);
  overlays.add(hotspot);

  // Sensor patch (Sensors layer)
  const sensor = new THREE.Group();
  const patch = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.09, 0.02), new THREE.MeshStandardMaterial({ color: 0xf9fbff, roughness: 0.5 }));
  const patchEdges = new THREE.LineSegments(new THREE.EdgesGeometry(patch.geometry), new THREE.LineBasicMaterial({ color: NAVY }));
  sensor.add(patch, patchEdges);
  for (let i = 0; i < 3; i++) {
    const l = new THREE.Mesh(new THREE.BoxGeometry(i === 2 ? 0.035 : 0.06, 0.006, 0.004), new THREE.MeshBasicMaterial({ color: NAVY }));
    l.position.set(i === 2 ? -0.012 : 0, 0.022 - i * 0.02, 0.012);
    sensor.add(l);
  }
  overlays.add(sensor);

  // Mobility arc + angle label
  const mobility = new THREE.Group();
  const arcGeo = new THREE.BufferGeometry();
  const arc = new THREE.Line(arcGeo, new THREE.LineDashedMaterial({ color: 0x1e88e5, dashSize: 0.02, gapSize: 0.012, depthTest: false }));
  arc.renderOrder = 14;
  const shin = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0x1e88e5, depthTest: false }));
  shin.renderOrder = 14;
  const angleLabel = textSprite('74°');
  angleLabel.scale.set(0.2, 0.1, 1);
  mobility.add(arc, shin, angleLabel);
  overlays.add(mobility);

  // Muscle groups (Muscles layer)
  const muscles = new THREE.Group();
  const muscleMat = new THREE.MeshStandardMaterial({ color: 0xee8fa9, transparent: true, opacity: 0.55, roughness: 0.6, depthWrite: false });
  overlays.add(muscles);

  let knee = new THREE.Vector3(-0.1, 0.5, 0.05);
  let homeTarget = new THREE.Vector3(0, H * 0.5, 0);
  let homeDist = 5;

  const setCamera = (target, dist) => {
    controls.target.copy(target);
    const az = 0.32;
    camera.position.set(target.x + Math.sin(az) * dist, target.y + dist * 0.08, target.z + Math.cos(az) * dist);
    controls.update();
  };

  // ---- load the model (base64 glb injected in window.__GLB) ----
  const bin = atob(window.__GLB);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);

  new GLTFLoader().parse(buf.buffer, '', gltf => {
    const model = gltf.scene;
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model, true);
    const size = box.getSize(new THREE.Vector3());
    const s = H / size.y;
    model.scale.setScalar(s);
    model.updateMatrixWorld(true);
    const b2 = new THREE.Box3().setFromObject(model, true);
    const center = b2.getCenter(new THREE.Vector3());
    model.position.set(-center.x, -b2.min.y, -center.z);
    model.updateMatrixWorld(true);

    const meshes = [];
    model.traverse(o => { if (o.isMesh) meshes.push(o); });
    meshes.forEach(mesh => {
      mesh.material = glassMaterial();
      mesh.renderOrder = 2;
      const outline = mesh.clone();
      outline.material = outlineMaterial();
      outline.renderOrder = 1;
      mesh.parent.add(outline);
    });
    root.add(model);
    model.updateMatrixWorld(true);

    // Locate the patient's right knee: vertices around 28% of the height, on the patient's right side
    const v = new THREE.Vector3();
    const kneeBand = [];
    const thighBand = [];
    const calfBand = [];
    meshes.forEach(mesh => {
      const pos = mesh.geometry.attributes.position;
      const step = Math.max(1, Math.floor(pos.count / 6000));
      for (let i = 0; i < pos.count; i += step) {
        mesh.getVertexPosition(i, v);
        v.applyMatrix4(mesh.matrixWorld);
        const h = v.y / H;
        if (h > 0.25 && h < 0.31) kneeBand.push(v.clone());
        if (h > 0.36 && h < 0.44) thighBand.push(v.clone());
        if (h > 0.12 && h < 0.2) calfBand.push(v.clone());
      }
    });
    const avg = (pts, side) => {
      const sel = pts.filter(p => (side < 0 ? p.x < 0 : p.x > 0));
      const out = new THREE.Vector3();
      if (!sel.length) return out;
      sel.forEach(p => out.add(p));
      out.divideScalar(sel.length);
      out.z = Math.max(...sel.map(p => p.z));
      return out;
    };
    // The model faces +Z, so the patient's right leg is on the -X side
    knee = avg(kneeBand, -1);
    knee.z += 0.01;
    hotspot.position.copy(knee);
    sensor.position.copy(knee).add(new THREE.Vector3(0, 0, 0.012));

    [[thighBand, -1], [thighBand, 1], [calfBand, -1], [calfBand, 1]].forEach(([band, side], i) => {
      const p = avg(band, side);
      p.z -= 0.05;
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(i < 2 ? 0.055 : 0.042, i < 2 ? 0.16 : 0.13, 6, 12), muscleMat);
      m.position.copy(p);
      muscles.add(m);
    });

    homeTarget = new THREE.Vector3(0, H * 0.5, 0);
    homeDist = (H * 0.62) / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    controls.minDistance = homeDist * 0.35;
    controls.maxDistance = homeDist * 1.4;
    setCamera(homeTarget, homeDist);
    applyState();
    post({ type: 'ready' });
  }, err => post({ type: 'error', reason: String(err && err.message ? err.message : err) }));

  setCamera(homeTarget, homeDist);

  function applyState() {
    const progress = (state.day - 1) / 41;
    const intensity = Math.max(0.24, 0.76 - progress * 0.5);
    const hl = state.highlighted ? 1.22 : 1;
    const layer = state.layer;
    glow.material.map = layer === 'Wound' ? heatTex : glowTex;
    glow.material.opacity = layer === 'Wound' ? 0.85 : intensity + 0.2;
    glow.userData.base = (layer === 'Wound' ? 0.22 : 0.3) * hl;
    pulse.visible = layer === 'Overview' || layer === 'Wound';
    sensor.visible = layer === 'Sensors';
    mobility.visible = layer === 'Mobility';
    muscles.visible = layer === 'Muscles';
    muscleMat.opacity = 0.55;

    // Knee angle arc grows as recovery progresses (74° → 99°)
    const angle = Math.round(74 + progress * 25);
    const bend = THREE.MathUtils.degToRad(8 + progress * 22);
    const r = 0.13;
    const pts = [];
    for (let i = 0; i <= 24; i++) {
      const a = Math.PI / 2 + (i / 24) * (Math.PI / 2 + bend);
      pts.push(new THREE.Vector3(knee.x + Math.cos(a) * r * 0.25, knee.y + Math.sin(a) * r, knee.z + 0.03 + Math.abs(Math.cos(a)) * 0.02));
    }
    arcGeo.setFromPoints(pts);
    arc.computeLineDistances();
    shin.geometry.setFromPoints([knee.clone().add(new THREE.Vector3(0, 0, 0.04)), knee.clone().add(new THREE.Vector3(0, -0.42, 0.04 + Math.sin(bend) * 0.25))]);
    angleLabel.update(`${angle}°`);
    angleLabel.position.copy(knee).add(new THREE.Vector3(-0.2, 0.12, 0.05));
  }

  // ---- messages from React Native ----
  let zoomed = false;
  const onMessage = e => {
    let msg;
    try { msg = JSON.parse(e.data); } catch (err) { return; }
    if (msg.type === 'state') {
      Object.assign(state, msg);
      applyState();
    } else if (msg.type === 'cmd') {
      if (msg.cmd === 'rotate') controls.autoRotate = !controls.autoRotate;
      if (msg.cmd === 'zoom') {
        zoomed = !zoomed;
        controls.autoRotate = false;
        setCamera(zoomed ? knee.clone() : homeTarget, zoomed ? homeDist * 0.42 : homeDist);
      }
      if (msg.cmd === 'reset') {
        zoomed = false;
        controls.autoRotate = false;
        setCamera(homeTarget, homeDist);
      }
    }
  };
  window.addEventListener('message', onMessage);
  document.addEventListener('message', onMessage);

  // ---- tap on the knee ----
  const ray = new THREE.Raycaster();
  let down = null;
  renderer.domElement.addEventListener('pointerdown', e => { down = { x: e.clientX, y: e.clientY }; });
  renderer.domElement.addEventListener('pointerup', e => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 8) return;
    const p = new THREE.Vector2((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
    ray.setFromCamera(p, camera);
    if (ray.intersectObject(hit, false).length) post({ type: 'tap', part: 'knee' });
  });

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const t = clock.getElapsedTime();
    root.scale.set(1, 1 + Math.sin(t * 1.57) * 0.006, 1); // breathe
    dashed.rotation.z = t * 0.5;
    const ph = (t % 1.5) / 1.5;
    const base = glow.userData.base || 0.3;
    glow.scale.setScalar(base * (1 + Math.sin(t * 3) * 0.05));
    pulse.scale.setScalar(base * (0.65 + ph * 1.5) * 0.6);
    pulse.material.opacity = 0.85 * (1 - ph);
    coreRing.quaternion.copy(camera.quaternion);
    controls.update();
    renderer.render(scene, camera);
  });
}

if (hasWebGL()) {
  try { init(); } catch (e) { post({ type: 'error', reason: String(e && e.message ? e.message : e) }); }
} else {
  post({ type: 'error', reason: 'webgl' });
}
