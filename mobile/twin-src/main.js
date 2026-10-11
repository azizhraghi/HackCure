// 3D Recovery Twin: holographic "x-ray" body with an anatomical skeleton, heart, vessels and the knee implant.
// Rendered inside a WebView (native) or an iframe (web). Built into src/components/twin/twinHtml.ts by
// scripts/build-twin.mjs. Body: Mixamo X Bot (realistic proportions + rig); the skeleton is placed on its bones.
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

const state = { day: 4, layer: 'Overview', highlighted: null, hr: 72 };
const CYAN = new THREE.Color(0x5fd8ff);
const H = 1.8; // body height after normalisation (m)

// ------------------------------------------------------------------ materials

/** Additive fresnel shell: transparent in the middle, glowing at the silhouette (x-ray hologram). */
function xray({ base = 0x0b3a52, rim = 0x7fe3ff, alpha = 0.04, power = 2.2, strength = 0.95 } = {}) {
  const m = new THREE.MeshStandardMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
  const b = new THREE.Color(base), r = new THREE.Color(rim);
  m.onBeforeCompile = shader => {
    shader.uniforms.sgBase = { value: b };
    shader.uniforms.sgRim = { value: r };
    shader.uniforms.sgAlpha = { value: alpha };
    shader.uniforms.sgStrength = { value: strength };
    m.userData.shader = shader;
    shader.fragmentShader = 'uniform vec3 sgBase; uniform vec3 sgRim; uniform float sgAlpha; uniform float sgStrength;\n' +
      shader.fragmentShader.replace('#include <opaque_fragment>',
        `float sgF = pow(1.0 - abs(dot(normalize(vViewPosition), normalize(normal))), ${power.toFixed(2)});
         gl_FragColor = vec4(mix(sgBase, sgRim, sgF), sgAlpha + sgF * sgStrength);`);
  };
  return m;
}

const boneMat = xray({ base: 0x6f8ea3, rim: 0xf2fbff, alpha: 0.16, power: 1.6, strength: 0.75 });
const organMat = color => xray({ base: color, rim: 0xffd2c8, alpha: 0.35, power: 1.4, strength: 0.6 });

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

function glowSprite(stops, scale) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTexture(stops), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  s.scale.setScalar(scale);
  return s;
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
    ctx.fillStyle = 'rgba(6,20,34,0.85)';
    ctx.strokeStyle = '#5fd8ff';
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(8, 24, 240, 80, 24);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#e8fbff';
    ctx.font = '800 54px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(value, 128, 66);
    tex.needsUpdate = true;
  };
  sprite.update(text);
  return sprite;
}

// ------------------------------------------------------------------ anatomy helpers

const UP = new THREE.Vector3(0, 1, 0);

/** Tapered bone from a to b with rounded ends. */
function bone(a, b, rA, rB = rA, mat = boneMat, knobs = true) {
  const g = new THREE.Group();
  const dir = new THREE.Vector3().subVectors(b, a);
  const len = dir.length();
  if (len < 1e-4) return g;
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(rB, rA, len, 12, 1, true), mat);
  shaft.position.copy(a).addScaledVector(dir, 0.5);
  shaft.quaternion.setFromUnitVectors(UP, dir.clone().normalize());
  g.add(shaft);
  if (knobs) {
    const ka = new THREE.Mesh(new THREE.SphereGeometry(rA * 1.45, 12, 10), mat);
    ka.position.copy(a);
    const kb = new THREE.Mesh(new THREE.SphereGeometry(rB * 1.45, 12, 10), mat);
    kb.position.copy(b);
    g.add(ka, kb);
  }
  return g;
}

function ellipsoid(pos, sx, sy, sz, mat) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(1, 24, 18), mat);
  m.position.copy(pos);
  m.scale.set(sx, sy, sz);
  return m;
}

function tube(points, radius, mat) {
  return new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points), 48, radius, 6, false), mat);
}

/** Rotate a bone by a world-space rotation (pose the rig without knowing each bone's local axes). */
function rotateBoneWorld(b, axis, angle) {
  const parentQ = new THREE.Quaternion();
  b.parent.getWorldQuaternion(parentQ);
  const worldQ = new THREE.Quaternion();
  b.getWorldQuaternion(worldQ);
  const rot = new THREE.Quaternion().setFromAxisAngle(axis, angle);
  b.quaternion.copy(parentQ.invert().multiply(rot).multiply(worldQ));
  b.updateMatrixWorld(true);
}

// ------------------------------------------------------------------ scene

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
  controls.autoRotateSpeed = 1.6;
  controls.autoRotate = true;

  scene.add(new THREE.HemisphereLight(0xcfefff, 0x0a1a2a, 1.2));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(-1.5, 3, 2.5);
  scene.add(key);

  const root = new THREE.Group();
  scene.add(root);
  const anatomy = new THREE.Group();
  root.add(anatomy);
  const overlays = new THREE.Group();
  root.add(overlays);

  // ---- holographic platform
  const ringMat = op => new THREE.MeshBasicMaterial({ color: CYAN, transparent: true, opacity: op, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false });
  const platform = new THREE.Group();
  [[0.46, 0.475, 0.55], [0.36, 0.366, 0.35], [0.26, 0.27, 0.5]].forEach(([a, b, op]) => platform.add(new THREE.Mesh(new THREE.RingGeometry(a, b, 96), ringMat(op))));
  platform.add(new THREE.Mesh(new THREE.CircleGeometry(0.46, 96), new THREE.MeshBasicMaterial({ map: radialTexture([[0, 'rgba(95,216,255,0.28)'], [0.7, 'rgba(95,216,255,0.06)'], [1, 'rgba(95,216,255,0)']]), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
  for (let i = 0; i < 24; i++) { // tick marks
    const tick = new THREE.Mesh(new THREE.PlaneGeometry(0.004, i % 6 === 0 ? 0.05 : 0.025), ringMat(0.6));
    const a = (i / 24) * Math.PI * 2;
    tick.position.set(Math.cos(a) * 0.43, Math.sin(a) * 0.43, 0);
    tick.rotation.z = a + Math.PI / 2;
    platform.add(tick);
  }
  const dashPts = new THREE.Path().absarc(0, 0, 0.41, 0, Math.PI * 2).getPoints(160);
  const dashed = new THREE.Line(new THREE.BufferGeometry().setFromPoints(dashPts), new THREE.LineDashedMaterial({ color: CYAN, dashSize: 0.04, gapSize: 0.03, transparent: true, opacity: 0.8 }));
  dashed.computeLineDistances();
  platform.add(dashed);
  platform.rotation.x = -Math.PI / 2;
  platform.position.y = 0.003;
  root.add(platform);

  // ---- scanning ring (rises along the body)
  const scan = new THREE.Mesh(new THREE.RingGeometry(0.0, 0.34, 96), new THREE.MeshBasicMaterial({
    map: radialTexture([[0, 'rgba(95,216,255,0)'], [0.82, 'rgba(95,216,255,0.05)'], [0.96, 'rgba(160,240,255,0.55)'], [1, 'rgba(95,216,255,0)']]),
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  scan.rotation.x = -Math.PI / 2;
  root.add(scan);

  // ---- knee hotspot (surgery site)
  const glowTex = radialTexture([[0, 'rgba(255,179,71,0.95)'], [0.45, 'rgba(255,140,60,0.45)'], [1, 'rgba(255,120,60,0)']]);
  const heatTex = radialTexture([[0, 'rgba(255,90,90,0.95)'], [0.35, 'rgba(255,200,120,0.8)'], [0.7, 'rgba(95,216,255,0.55)'], [1, 'rgba(95,216,255,0)']]);
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, depthTest: false, transparent: true, blending: THREE.AdditiveBlending }));
  glow.renderOrder = 10;
  const pulse = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTexture([[0, 'rgba(255,179,71,0)'], [0.82, 'rgba(255,179,71,0)'], [0.9, 'rgba(255,179,71,0.9)'], [1, 'rgba(255,179,71,0)']]), depthTest: false, transparent: true, blending: THREE.AdditiveBlending }));
  pulse.renderOrder = 11;
  const hit = new THREE.Mesh(new THREE.SphereGeometry(0.13, 12, 8), new THREE.MeshBasicMaterial({ visible: false }));
  const hotspot = new THREE.Group();
  hotspot.add(glow, pulse, hit);
  overlays.add(hotspot);

  // ---- sensor patch (Sensors layer)
  const sensor = new THREE.Group();
  const patch = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.08, 0.012), new THREE.MeshStandardMaterial({ color: 0xe9f6ff, roughness: 0.35, emissive: 0x0e3d55, emissiveIntensity: 0.6 }));
  sensor.add(patch, new THREE.LineSegments(new THREE.EdgesGeometry(patch.geometry), new THREE.LineBasicMaterial({ color: CYAN })));
  sensor.add(glowSprite([[0, 'rgba(95,216,255,0.6)'], [1, 'rgba(95,216,255,0)']], 0.22));
  overlays.add(sensor);

  // ---- mobility arc + angle label (Mobility layer)
  const mobility = new THREE.Group();
  const arcGeo = new THREE.BufferGeometry();
  const arc = new THREE.Line(arcGeo, new THREE.LineDashedMaterial({ color: CYAN, dashSize: 0.02, gapSize: 0.012, depthTest: false }));
  arc.renderOrder = 14;
  const shin = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: CYAN, depthTest: false }));
  shin.renderOrder = 14;
  const angleLabel = textSprite('74°');
  angleLabel.scale.set(0.2, 0.1, 1);
  mobility.add(arc, shin, angleLabel);
  overlays.add(mobility);

  // ---- muscles (Muscles layer)
  const muscles = new THREE.Group();
  overlays.add(muscles);

  // heart + vessels references (animated)
  let heart = null;
  let heartGlow = null;
  let bodyMat = null;
  let particles = null;
  let knee = new THREE.Vector3(-0.08, 0.53, 0.06);
  let homeTarget = new THREE.Vector3(0, H * 0.5, 0);
  let homeDist = 5;

  const setCamera = (target, dist) => {
    controls.target.copy(target);
    const az = 0.32;
    camera.position.set(target.x + Math.sin(az) * dist, target.y + dist * 0.06, target.z + Math.cos(az) * dist);
    controls.update();
  };

  // ---- load the body (base64 glb injected in window.__GLB)
  const bin = atob(window.__GLB);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);

  new GLTFLoader().parse(buf.buffer, '', gltf => {
    const model = gltf.scene;
    const bones = {};
    model.traverse(o => { if (o.isBone) bones[o.name.replace(/^mixamorig[:_]?/, '')] = o; });
    model.updateMatrixWorld(true);

    // Relaxed pose: arms down along the body instead of the T-pose
    const Z = new THREE.Vector3(0, 0, 1);
    if (bones.LeftArm) rotateBoneWorld(bones.LeftArm, Z, -1.22);
    if (bones.RightArm) rotateBoneWorld(bones.RightArm, Z, 1.22);
    if (bones.LeftForeArm) rotateBoneWorld(bones.LeftForeArm, new THREE.Vector3(1, 0, 0), -0.12);
    if (bones.RightForeArm) rotateBoneWorld(bones.RightForeArm, new THREE.Vector3(1, 0, 0), -0.12);
    model.updateMatrixWorld(true);

    const box = new THREE.Box3().setFromObject(model, true);
    const s = H / (box.max.y - box.min.y);
    model.scale.setScalar(s);
    model.updateMatrixWorld(true);
    const b2 = new THREE.Box3().setFromObject(model, true);
    const center = b2.getCenter(new THREE.Vector3());
    model.position.set(-center.x, -b2.min.y, -center.z);
    model.updateMatrixWorld(true);

    bodyMat = xray({ base: 0x0a3550, rim: 0x8ee8ff, alpha: 0.035, power: 2.4, strength: 1.0 });
    const bodyMeshes = [];
    model.traverse(o => {
      if (o.isMesh) {
        o.material = bodyMat;
        o.renderOrder = 5;
        o.frustumCulled = false;
        bodyMeshes.push(o);
      }
    });
    root.add(model);

    const P = name => (bones[name] ? bones[name].getWorldPosition(new THREE.Vector3()) : null);
    const hips = P('Hips'), spine = P('Spine'), spine1 = P('Spine1'), spine2 = P('Spine2'), neck = P('Neck'), head = P('Head');
    const side = (n, sgn) => P((sgn > 0 ? 'Left' : 'Right') + n);

    // --- spine (vertebrae along the chain, slightly to the back)
    const chain = [hips, spine, spine1, spine2, neck, head].filter(Boolean);
    const spineCurve = new THREE.CatmullRomCurve3(chain.map(p => p.clone().add(new THREE.Vector3(0, 0, -0.035))));
    for (let i = 0; i <= 26; i++) {
      const p = spineCurve.getPoint(i / 26);
      const v = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.018, 0.016, 10), boneMat);
      v.position.copy(p);
      anatomy.add(v);
    }

    // --- skull + jaw
    if (head) {
      anatomy.add(ellipsoid(head.clone().add(new THREE.Vector3(0, 0.1, 0.0)), 0.078, 0.095, 0.092, boneMat));
      anatomy.add(ellipsoid(head.clone().add(new THREE.Vector3(0, 0.03, 0.045)), 0.05, 0.03, 0.045, boneMat));
    }

    // --- rib cage, sternum, clavicles
    if (spine1 && spine2 && neck) {
      const top = neck.y - 0.04, bottom = spine1.y - 0.03;
      for (let i = 0; i < 10; i++) {
        const tt = i / 9;
        const y = top - (top - bottom) * tt;
        const rx = 0.075 + Math.sin(Math.min(1, tt * 1.4) * Math.PI * 0.5) * 0.06;
        const rz = 0.06 + tt * 0.025;
        for (const sgn of [1, -1]) {
          const pts = [];
          for (let k = 0; k <= 14; k++) {
            const th = 0.25 + (k / 14) * 2.45;
            pts.push(new THREE.Vector3(sgn * rx * Math.sin(th), y - 0.035 * (1 - Math.cos(th)) * 0.5, 0.0 - rz * Math.cos(th)));
          }
          anatomy.add(tube(pts, 0.0065, boneMat));
        }
      }
      anatomy.add(bone(new THREE.Vector3(0, top - 0.02, 0.085), new THREE.Vector3(0, bottom + 0.05, 0.1), 0.011, 0.009, boneMat, false));
      for (const sgn of [1, -1]) {
        const arm = side('Arm', sgn);
        if (arm) anatomy.add(bone(new THREE.Vector3(sgn * 0.02, top + 0.015, 0.06), arm.clone().add(new THREE.Vector3(0, 0.02, 0)), 0.008, 0.009));
      }
    }

    // --- pelvis
    if (hips) {
      const pelvis = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.016, 10, 32), boneMat);
      pelvis.position.copy(hips).add(new THREE.Vector3(0, -0.04, 0));
      pelvis.rotation.x = Math.PI / 2 - 0.35;
      anatomy.add(pelvis);
      for (const sgn of [1, -1]) {
        const wing = ellipsoid(hips.clone().add(new THREE.Vector3(sgn * 0.085, 0.02, -0.01)), 0.055, 0.06, 0.02, boneMat);
        wing.rotation.y = sgn * 0.5;
        anatomy.add(wing);
      }
    }

    // --- limbs
    for (const sgn of [1, -1]) {
      const arm = side('Arm', sgn), fore = side('ForeArm', sgn), hand = side('Hand', sgn);
      if (arm && fore) anatomy.add(bone(arm, fore, 0.013, 0.011));
      if (fore && hand) {
        const off = new THREE.Vector3(0, 0, 0.008);
        anatomy.add(bone(fore.clone().add(off), hand.clone().add(off), 0.008, 0.007));
        anatomy.add(bone(fore.clone().sub(off), hand.clone().sub(off), 0.006, 0.008, boneMat, false));
        const dir = new THREE.Vector3().subVectors(hand, fore).normalize();
        anatomy.add(ellipsoid(hand.clone().addScaledVector(dir, 0.05), 0.03, 0.05, 0.012, boneMat));
      }
      const up = side('UpLeg', sgn), leg = side('Leg', sgn), foot = side('Foot', sgn), toe = side('ToeBase', sgn);
      if (up && leg) anatomy.add(bone(up, leg, 0.019, 0.016));
      if (leg && foot) {
        anatomy.add(bone(leg, foot, 0.016, 0.012));
        anatomy.add(bone(leg.clone().add(new THREE.Vector3(sgn * 0.022, -0.03, -0.01)), foot.clone().add(new THREE.Vector3(sgn * 0.018, 0.03, -0.01)), 0.006, 0.006, boneMat, false));
        anatomy.add(ellipsoid(leg.clone().add(new THREE.Vector3(0, 0.01, 0.045)), 0.02, 0.024, 0.01, boneMat)); // patella
      }
      if (foot && toe) anatomy.add(bone(foot.clone().add(new THREE.Vector3(0, -0.04, -0.03)), toe.clone().add(new THREE.Vector3(0, -0.02, 0.02)), 0.014, 0.01));
    }

    // --- organs: lungs, heart, vessels
    if (spine2) {
      for (const sgn of [1, -1]) anatomy.add(ellipsoid(spine2.clone().add(new THREE.Vector3(sgn * 0.06, -0.01, 0.025)), 0.05, 0.09, 0.05, organMat(0x3a5f7a)));
      heart = ellipsoid(spine2.clone().add(new THREE.Vector3(0.025, -0.035, 0.05)), 0.034, 0.042, 0.032, organMat(0xd03040));
      heart.rotation.z = -0.5;
      heart.userData.base = heart.scale.clone();
      anatomy.add(heart);
      heartGlow = glowSprite([[0, 'rgba(255,70,80,0.75)'], [0.5, 'rgba(255,70,80,0.2)'], [1, 'rgba(255,70,80,0)']], 0.2);
      heartGlow.position.copy(heart.position);
      anatomy.add(heartGlow);
    }
    const vessel = new THREE.MeshBasicMaterial({ color: 0xff4d5e, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false });
    if (heart && hips) {
      const aorta = [heart.position.clone(), spine1.clone().add(new THREE.Vector3(0.01, 0, 0.0)), hips.clone().add(new THREE.Vector3(0, 0.03, 0.01))];
      anatomy.add(tube(aorta, 0.006, vessel));
      for (const sgn of [1, -1]) {
        const up = side('UpLeg', sgn), leg = side('Leg', sgn), foot = side('Foot', sgn);
        if (up && leg && foot) anatomy.add(tube([aorta[2], up.clone().add(new THREE.Vector3(-sgn * 0.015, -0.05, 0.03)), leg.clone().add(new THREE.Vector3(-sgn * 0.01, 0.02, -0.02)), foot.clone().add(new THREE.Vector3(0, 0.05, 0))], 0.004, vessel));
        const arm = side('Arm', sgn), hand = side('Hand', sgn);
        if (arm && hand) anatomy.add(tube([heart.position.clone(), arm.clone().add(new THREE.Vector3(0, -0.02, 0.01)), hand.clone()], 0.0035, vessel));
      }
    }

    // --- the right knee: total knee replacement implant + hotspot (the model faces +Z: patient's right is -X)
    const rLeg = side('Leg', -1);
    if (rLeg) {
      knee = rLeg.clone();
      const metal = new THREE.MeshStandardMaterial({ color: 0xdfe6ee, metalness: 1, roughness: 0.18, emissive: 0x16323f, emissiveIntensity: 0.5 });
      const femoral = new THREE.Mesh(new THREE.TorusGeometry(0.024, 0.008, 10, 24, Math.PI * 1.2), metal);
      femoral.position.copy(knee).add(new THREE.Vector3(0, 0.018, 0.005));
      femoral.rotation.set(0, Math.PI / 2, Math.PI * 0.9);
      const tibial = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.026, 0.008, 24), metal);
      tibial.position.copy(knee).add(new THREE.Vector3(0, -0.012, 0));
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.006, 0.004, 0.06, 10), metal);
      stem.position.copy(knee).add(new THREE.Vector3(0, -0.045, 0));
      anatomy.add(femoral, tibial, stem);
    }
    const kneeFront = knee.clone().add(new THREE.Vector3(0, 0, 0.06));
    hotspot.position.copy(kneeFront);
    sensor.position.copy(kneeFront).add(new THREE.Vector3(0, 0.02, 0.005));

    // --- muscles: quadriceps, hamstrings, calves (Muscles layer)
    const muscleMat = xray({ base: 0x7a1f35, rim: 0xff9db2, alpha: 0.12, power: 1.5, strength: 0.7 });
    for (const sgn of [1, -1]) {
      const up = side('UpLeg', sgn), leg = side('Leg', sgn), foot = side('Foot', sgn);
      if (up && leg) {
        const mid = up.clone().lerp(leg, 0.5);
        muscles.add(ellipsoid(mid.clone().add(new THREE.Vector3(0, 0, 0.03)), 0.055, 0.2, 0.05, muscleMat));
        muscles.add(ellipsoid(mid.clone().add(new THREE.Vector3(0, 0, -0.03)), 0.05, 0.18, 0.045, muscleMat));
      }
      if (leg && foot) muscles.add(ellipsoid(leg.clone().lerp(foot, 0.3).add(new THREE.Vector3(0, 0, -0.03)), 0.04, 0.12, 0.04, muscleMat));
    }

    // --- data particles drifting inside the body
    const pts = [];
    const v = new THREE.Vector3();
    bodyMeshes.forEach(mesh => {
      const pos = mesh.geometry.attributes.position;
      for (let i = 0; i < pos.count; i += 9) {
        mesh.getVertexPosition(i, v);
        v.applyMatrix4(mesh.matrixWorld);
        pts.push(v.x * 0.94, v.y, v.z * 0.94);
      }
    });
    const pg = new THREE.BufferGeometry();
    pg.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    particles = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0x9feeff, size: 0.006, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }));
    root.add(particles);

    homeTarget = new THREE.Vector3(0, H * 0.5, 0);
    homeDist = (H * 0.6) / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    controls.minDistance = homeDist * 0.3;
    controls.maxDistance = homeDist * 1.4;
    setCamera(homeTarget, homeDist);
    applyState();
    post({ type: 'ready' });
  }, err => post({ type: 'error', reason: String(err && err.message ? err.message : err) }));

  setCamera(homeTarget, homeDist);

  function applyState() {
    const progress = Math.min(1, Math.max(0, (state.day - 1) / 41));
    const intensity = Math.max(0.3, 0.8 - progress * 0.5);
    const hl = state.highlighted ? 1.22 : 1;
    const layer = state.layer;
    glow.material.map = layer === 'Wound' ? heatTex : glowTex;
    glow.material.opacity = layer === 'Wound' ? 0.9 : intensity;
    glow.userData.base = (layer === 'Wound' ? 0.24 : 0.2) * hl;
    pulse.visible = layer === 'Overview' || layer === 'Wound';
    sensor.visible = layer === 'Sensors';
    mobility.visible = layer === 'Mobility';
    muscles.visible = layer === 'Muscles';
    anatomy.visible = layer !== 'Muscles';

    // Knee flexion arc grows as recovery progresses (74° → 99°)
    const angle = Math.round(74 + progress * 25);
    const bend = THREE.MathUtils.degToRad(8 + progress * 22);
    const r = 0.13;
    const p = [];
    for (let i = 0; i <= 24; i++) {
      const a = Math.PI / 2 + (i / 24) * (Math.PI / 2 + bend);
      p.push(new THREE.Vector3(knee.x + Math.cos(a) * r * 0.25, knee.y + Math.sin(a) * r, knee.z + 0.08 + Math.abs(Math.cos(a)) * 0.02));
    }
    arcGeo.setFromPoints(p);
    arc.computeLineDistances();
    shin.geometry.setFromPoints([knee.clone().add(new THREE.Vector3(0, 0, 0.08)), knee.clone().add(new THREE.Vector3(0, -0.42, 0.08 + Math.sin(bend) * 0.25))]);
    angleLabel.update(`${angle}°`);
    angleLabel.position.copy(knee).add(new THREE.Vector3(-0.2, 0.12, 0.08));
  }

  // ---- messages from the app
  let zoomed = false;
  const onMessage = e => {
    let msg;
    try { msg = typeof e.data === 'string' ? JSON.parse(e.data) : e.data; } catch (err) { return; }
    if (!msg) return;
    if (msg.type === 'state') {
      Object.assign(state, msg);
      applyState();
    } else if (msg.type === 'cmd') {
      if (msg.cmd === 'rotate') controls.autoRotate = !controls.autoRotate;
      if (msg.cmd === 'zoom') {
        zoomed = !zoomed;
        controls.autoRotate = false;
        setCamera(zoomed ? knee.clone() : homeTarget, zoomed ? homeDist * 0.4 : homeDist);
      }
      if (msg.cmd === 'reset') {
        zoomed = false;
        setCamera(homeTarget, homeDist);
      }
    }
  };
  window.addEventListener('message', onMessage);
  document.addEventListener('message', onMessage);

  // ---- tap on the knee
  const ray = new THREE.Raycaster();
  let down = null;
  renderer.domElement.addEventListener('pointerdown', e => { down = { x: e.clientX, y: e.clientY }; controls.autoRotate = false; });
  renderer.domElement.addEventListener('pointerup', e => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 8) return;
    const q = new THREE.Vector2((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
    ray.setFromCamera(q, camera);
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
    dashed.rotation.z = t * 0.35;
    // scanning ring sweeps the body
    const sy = (Math.sin(t * 0.7) * 0.5 + 0.5) * H * 0.95 + 0.02;
    scan.position.y = sy;
    scan.material.opacity = 0.75;
    if (bodyMat && bodyMat.userData.shader) bodyMat.userData.shader.uniforms.sgStrength.value = 0.9 + Math.sin(t * 2.0) * 0.08;
    // heart beats at the patient's heart rate
    if (heart) {
      const beat = (t * (state.hr || 72) / 60) % 1;
      const k = 1 + Math.max(0, Math.sin(beat * Math.PI * 2)) * 0.12 * (beat < 0.5 ? 1 : 0.4);
      heart.scale.copy(heart.userData.base).multiplyScalar(k);
      heartGlow.material.opacity = 0.55 + (k - 1) * 3;
    }
    if (particles) particles.material.opacity = 0.4 + Math.sin(t * 1.3) * 0.15;
    const ph = (t % 1.5) / 1.5;
    const base = glow.userData.base || 0.2;
    glow.scale.setScalar(base * (1 + Math.sin(t * 3) * 0.05));
    pulse.scale.setScalar(base * (0.65 + ph * 1.5) * 0.6);
    pulse.material.opacity = 0.85 * (1 - ph);
    controls.update();
    renderer.render(scene, camera);
  });
}

if (hasWebGL()) {
  try { init(); } catch (e) { post({ type: 'error', reason: String(e && e.message ? e.message : e) }); }
} else {
  post({ type: 'error', reason: 'webgl' });
}
