import { useEffect, useState, type ReactNode } from "react";

type IconName =
  | "arrow"
  | "bell"
  | "search"
  | "camera"
  | "upload"
  | "image"
  | "file"
  | "check"
  | "home"
  | "checkin"
  | "twin"
  | "report"
  | "profile"
  | "close"
  | "phone"
  | "message"
  | "thermo"
  | "drop"
  | "activity"
  | "rotate"
  | "scan"
  | "sensor";

const paths: Record<IconName, ReactNode> = {
  arrow: <path d="m15 18-6-6 6-6" />,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M10 21h4" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  camera: <><path d="M4 7h3l2-3h6l2 3h3v12H4z" /><circle cx="12" cy="13" r="4" /></>,
  upload: <><path d="M12 16V4m-5 5 5-5 5 5" /><path d="M5 16v4h14v-4" /></>,
  image: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="2" /><path d="m3 17 5-5 4 4 3-3 6 6" /></>,
  file: <><path d="M6 2h8l4 4v16H6z" /><path d="M14 2v5h5M9 12h6M9 16h6" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  home: <><path d="m3 11 9-8 9 8" /><path d="M5 10v10h14V10M9 20v-6h6v6" /></>,
  checkin: <><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></>,
  twin: <><circle cx="12" cy="5" r="3" /><path d="M8 22v-6l-2-4 3-3h6l3 3-2 4v6M9 10l3 5 3-5" /></>,
  report: <><path d="M5 20V10M12 20V4M19 20v-7" /><path d="M3 20h18" /></>,
  profile: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  close: <path d="m7 7 10 10M17 7 7 17" />,
  phone: <><path d="M7 3h3l2 5-2 2a15 15 0 0 0 4 4l2-2 5 2v3c0 2-2 4-4 4A14 14 0 0 1 3 7c0-2 2-4 4-4Z" /></>,
  message: <path d="M4 4h16v13H8l-4 4z" />,
  thermo: <><path d="M10 14.8V5a2 2 0 1 1 4 0v9.8a4 4 0 1 1-4 0Z" /><path d="M12 9v8" /></>,
  drop: <path d="M12 2s7 8 7 13a7 7 0 0 1-14 0c0-5 7-13 7-13Z" />,
  activity: <path d="M2 12h4l2-7 4 14 3-10 2 3h5" />,
  rotate: <><path d="M20 7a9 9 0 0 0-15-2L3 7" /><path d="M3 3v4h4M4 17a9 9 0 0 0 15 2l2-2" /><path d="M21 21v-4h-4" /></>,
  scan: <><path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5" /><circle cx="12" cy="12" r="4" /></>,
  sensor: <><circle cx="12" cy="12" r="2" /><path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2" /></>,
};

function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function StatusBar() {
  return <div className="status"><b>12:41</b><div className="status-icons"><span className="signal">▮▮▮</span><span className="wifi">⌁</span><span className="battery" /></div></div>;
}

function Phone({ children, caption, nav = false, active = "home", id }: { children: ReactNode; caption: string; nav?: boolean; active?: IconName; id?: string }) {
  return <div className="phone-wrap" id={id}>
    <div className="phone">
      <StatusBar />
      <div className={`screen ${nav ? "has-nav" : ""}`}>{children}</div>
      {nav && <BottomNav active={active} />}
      <div className="home-indicator" />
    </div>
    <div className="caption">{caption}</div>
  </div>;
}

function RoundButton({ icon }: { icon: IconName }) {
  return <button className="round-button" aria-label={icon}><Icon name={icon} /></button>;
}

function BottomNav({ active }: { active: IconName }) {
  const items: [IconName, string][] = [["home", "Home"], ["checkin", "Check-in"], ["twin", "Twin"], ["report", "Reports"], ["profile", "Profile"]];
  return <div className="bottom-nav">{items.map(([icon, label]) => <button className={active === icon ? "active" : ""} key={label}><span><Icon name={icon} size={19} /></span><small>{label}</small></button>)}</div>;
}

function TopBar({ title, back = true, action }: { title: string; back?: boolean; action?: ReactNode }) {
  return <div className="top-bar">{back ? <RoundButton icon="arrow" /> : <span />}<div className="top-title">{title}</div>{action || <span className="top-spacer" />}</div>;
}

function Button({ children, secondary = false, icon, onClick }: { children: ReactNode; secondary?: boolean; icon?: IconName; onClick?: () => void }) {
  return <button className={`primary-button ${secondary ? "secondary" : ""}`} onClick={onClick}>{icon && <Icon name={icon} size={18} />}{children}</button>;
}

function Chip({ children, tone = "white" }: { children: ReactNode; tone?: string }) {
  return <span className={`chip ${tone}`}>{children}</span>;
}

function MiniLine({ color = "#1B2A4A", fill = false, dashed = false }: { color?: string; fill?: boolean; dashed?: boolean }) {
  return <svg className="mini-line" viewBox="0 0 120 44" preserveAspectRatio="none">
    {fill && <path d="M2 38 C16 36 20 18 33 24 S51 34 64 17 83 28 96 14 118 8 118 8V44H2Z" fill={`${color}22`} stroke="none" />}
    <path d="M2 38 C16 36 20 18 33 24 S51 34 64 17 83 28 96 14 118 8" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" strokeDasharray={dashed ? "5 5" : ""} />
    <circle cx="118" cy="8" r="3.5" fill={color} />
  </svg>;
}

function MiniBars() {
  return <div className="mini-bars">{[48, 70, 42, 83, 59, 74, 91].map((h, i) => <span key={i} style={{ height: `${h}%` }} />)}</div>;
}

function Stepper() {
  const steps = ["Upload", "Analyze", "Review", "Start"];
  return <div className="stepper">{steps.map((s, i) => <div className={i === 0 ? "current" : ""} key={s}><span>{i === 0 ? "1" : i + 1}</span><small>{s}</small></div>)}</div>;
}

function BodyFigure({ zoom = false }: { zoom?: boolean }) {
  if (zoom) return <svg viewBox="0 0 300 235" className="knee-figure">
    <defs><radialGradient id="kneeGlow"><stop stopColor="#ff967d" stopOpacity=".95" /><stop offset="1" stopColor="#ff967d" stopOpacity="0" /></radialGradient></defs>
    <path d="M120 4c-18 42-24 84-10 103 9 12 9 21 2 38-12 27-18 58-12 86M180 4c18 42 24 84 10 103-9 12-9 21-2 38 12 27 18 58 12 86" fill="none" stroke="#d8e9f2" strokeWidth="56" strokeLinecap="round" />
    <path d="M120 4c-18 42-24 84-10 103 9 12 9 21 2 38-12 27-18 58-12 86M180 4c18 42 24 84 10 103-9 12-9 21-2 38 12 27 18 58 12 86" fill="none" stroke="#1b2a4a" strokeWidth="2" strokeLinecap="round" />
    <circle cx="189" cy="119" r="46" fill="url(#kneeGlow)" /><circle cx="189" cy="119" r="13" fill="#ff755f" stroke="#1b2a4a" strokeWidth="2" />
    <path d="M161 119h56M189 91v56" stroke="#fff" strokeWidth="1.5" strokeDasharray="4 4" />
  </svg>;
  return <svg viewBox="0 0 220 440" className="body-figure">
    <defs>
      <linearGradient id="body" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#f7fbff" /><stop offset=".55" stopColor="#cfeafa" /><stop offset="1" stopColor="#b7d7ec" /></linearGradient>
      <radialGradient id="hot"><stop stopColor="#ff765d" /><stop offset=".35" stopColor="#ff957f" stopOpacity=".75" /><stop offset="1" stopColor="#ff957f" stopOpacity="0" /></radialGradient>
    </defs>
    <circle cx="110" cy="43" r="29" fill="url(#body)" stroke="#1b2a4a" strokeWidth="2" />
    <path d="M97 69c-4 9-19 13-29 20-11 8-12 33-15 57l-11 87c-1 11 14 14 18 3l18-82 1 86-15 162c-1 13 17 16 22 3l24-122 24 122c5 13 23 10 22-3l-15-162 1-86 18 82c4 11 19 8 18-3l-11-87c-3-24-4-49-15-57-10-7-25-11-29-20" fill="url(#body)" stroke="#1b2a4a" strokeWidth="2" strokeLinejoin="round" />
    <path d="M110 74v204M79 240h62M86 146c17 8 31 8 48 0" fill="none" stroke="#87b9d5" strokeWidth="1.3" opacity=".8" />
    <circle cx="133" cy="281" r="30" fill="url(#hot)" className="pulse" />
    <circle cx="133" cy="281" r="7" fill="#ff6f59" stroke="#fff" strokeWidth="2" />
    <circle cx="85" cy="147" r="6" fill="#55d99e" stroke="#fff" strokeWidth="2" />
    <circle cx="136" cy="147" r="6" fill="#42b8ef" stroke="#fff" strokeWidth="2" />
  </svg>;
}

function Welcome() {
  return <Phone caption="01 — Welcome & onboarding">
    <div className="welcome">
      <div className="brand"><span className="brand-mark"><Icon name="activity" size={19} /></span>SurgiGuard <b>AI</b></div>
      <div className="onboard-art">
        <div className="orb orb-one" /><div className="orb orb-two" />
        <BodyFigure />
        <div className="site-label"><span /> Recovery starts here</div>
      </div>
      <div className="eyebrow">YOUR RECOVERY, REIMAGINED</div>
      <div className="hero-title">One surgery.<br />One personalized<br /><em>recovery.</em></div>
      <p className="muted lead">Your AI-powered companion for a safer, calmer recovery at home.</p>
      <Button>Get started <span>→</span></Button>
      <button className="text-button">I already have an account</button>
    </div>
  </Phone>;
}

function UploadReports() {
  const files = [["Discharge summary", "2.4 MB", "done"], ["Operative report", "1.8 MB", "done"], ["Lab results", "Processing…", "wait"], ["Medication list", "Ready", "done"]];
  return <Phone caption="02 — Upload medical reports">
    <TopBar title="Medical records" />
    <Stepper />
    <div className="page-title">Add your medical<br />reports</div>
    <p className="muted">We'll build your personal recovery plan from these documents.</p>
    <div className="upload-card">
      <div className="upload-icon"><Icon name="upload" size={25} /></div>
      <b>Upload your documents</b><small>PDF, JPG or PNG · max 20 MB</small>
      <button><Icon name="camera" /> Scan discharge document</button>
      <div className="upload-actions"><button><Icon name="file" /> Upload PDF</button><button><Icon name="image" /> Gallery</button></div>
    </div>
    <div className="section-row"><b>Uploaded files</b><small>4 files</small></div>
    <div className="file-list">{files.map(([name, sub, state]) => <div className="file-row" key={name}><span className="file-icon"><Icon name="file" size={17} /></span><div><b>{name}</b><small>{sub}</small></div><span className={`file-status ${state}`}>{state === "done" ? <Icon name="check" size={14} /> : <i />}</span></div>)}</div>
    <Button>Analyze with AI <span>→</span></Button>
  </Phone>;
}

function Protocol() {
  const cards = [
    ["Medication", "4 medicines · 3 schedules", "pink", "09:00"],
    ["Activity restrictions", "Weight bearing as tolerated", "yellow", "14 days"],
    ["Rehabilitation exercises", "3 exercises · twice daily", "lavender", "Start today"],
    ["Follow-up visits", "Next visit on June 18", "sky", "2 visits"],
  ];
  return <Phone caption="03 — AI protocol compiler">
    <TopBar title="AI protocol" />
    <div className="ready-mark"><Icon name="check" size={25} /></div>
    <div className="page-title centered">Your recovery<br />protocol is ready</div>
    <p className="muted centered">Compiled from 4 medical documents</p>
    <div className="surgery-card">
      <div className="knee-icon">◒</div><div><small>DETECTED SURGERY</small><b>Total knee replacement</b><span>Right knee · June 04, 2025</span></div><Icon name="check" size={19} />
    </div>
    <div className="protocol-grid">{cards.map(([title, copy, tone, tag]) => <div className={`protocol-card ${tone}`} key={title}><small>{title}</small><b>{copy}</b><span>{tag}</span></div>)}</div>
    <div className="warning-card"><span>!</span><div><b>Warning signs</b><small>Fever over 38°C, spreading redness, drainage</small></div></div>
    <div className="module-title">Monitoring modules activated</div>
    <div className="chip-cloud">{["Wound camera", "Dressing sensor", "Pain tracking", "Knee-angle rehab"].map(x => <Chip key={x} tone="blue">{x}</Chip>)}</div>
    <div className="button-row"><Button secondary>Edit</Button><Button>Confirm & create Twin</Button></div>
  </Phone>;
}

function HomeScreen() {
  return <Phone caption="04 — Recovery home" nav active="home">
    <div className="home-head"><div className="avatar">MM<span /></div><div><small>Welcome back</small><b>Maya <span className="wave">👋</span></b></div><div className="head-actions"><RoundButton icon="search" /><RoundButton icon="bell" /></div></div>
    <div className="page-title">Here's your recovery<br />at a glance</div>
    <div className="task-card">
      <button className="task-close"><Icon name="close" size={16} /></button><small>TODAY'S TASK</small><b>Take a wound photo<br />and do 10 knee bends</b><div className="task-footer"><span>About 5 min</span><button>Done <b>›</b></button></div>
    </div>
    <div className="metric-pair">
      <div className="metric-card pink"><small>WOUND TEMP</small><b>36.9<sup>°C</sup></b><span>Normal range</span><MiniBars /></div>
      <div className="metric-card yellow"><small>PAIN TODAY</small><b>3<sup>/10</sup></b><span className="down">↓ 1 from yesterday</span><MiniLine /></div>
    </div>
    <div className="section-row recovery-title"><b>Recovery Check</b><button>View details</button></div>
    <div className="recovery-card">
      <div className="score-ring"><div><b>87<sup>%</sup></b><small>recovery score</small></div></div>
      <div className="score-copy"><b>You're right on track</b><span>2% ahead of expected recovery</span><div className="recovery-stats"><div>☾ <span><b>8.5h</b><small>last night</small></span></div><div>◷ <span><b>Day 6</b><small>of 42</small></span></div></div></div>
    </div>
  </Phone>;
}

function Toggle() {
  const [period, setPeriod] = useState("Day");
  return <div className="toggle">{["Day", "Week"].map(p => <button key={p} className={period === p ? "active" : ""} onClick={() => setPeriod(p)}>{p}</button>)}</div>;
}

function CountUp({ value, decimals = 0, suffix = "" }: { value: number; decimals?: number; suffix?: string }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    let frame = 0;
    const frames = 24;
    const timer = window.setInterval(() => {
      frame += 1;
      setShown(value * Math.min(frame / frames, 1));
      if (frame === frames) window.clearInterval(timer);
    }, 28);
    return () => window.clearInterval(timer);
  }, [value]);
  return <>{shown.toFixed(decimals)}{suffix}</>;
}

function RecoveryTwinFigure({ day, layer, highlighted }: { day: number; layer: string; highlighted: string | null }) {
  const progress = (day - 1) / 41;
  const bend = 8 + progress * 22;
  const glow = Math.max(.24, .76 - progress * .5);
  return <div className={`medical-twin ${layer.toLowerCase()} ${highlighted ? `highlight-${highlighted}` : ""}`}>
    <svg className="expected-ghost" viewBox="0 0 220 440" aria-label="Expected recovery silhouette">
      <circle cx="110" cy="40" r="27" /><path d="M96 67C83 76 73 84 70 107L59 226M124 67c13 9 23 17 26 40l11 119M96 70l-17 166 7 166M124 70l17 166-7 166M86 238l24 42 24-42" />
    </svg>
    <svg className="glass-body" viewBox="0 0 220 440" aria-label="Semi-transparent anatomical recovery model">
      <defs>
        <linearGradient id="glassSkin" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#f8fdff" stopOpacity=".94" /><stop offset=".28" stopColor="#d8f0f8" stopOpacity=".75" /><stop offset=".68" stopColor="#9bc9df" stopOpacity=".66" /><stop offset="1" stopColor="#6193b2" stopOpacity=".78" /></linearGradient>
        <linearGradient id="glassSkinDark" x1="0" y1="0" x2="1" y2=".7"><stop stopColor="#b5dded" stopOpacity=".7" /><stop offset=".55" stopColor="#77a9c5" stopOpacity=".68" /><stop offset="1" stopColor="#477b9c" stopOpacity=".8" /></linearGradient>
        <radialGradient id="faceVolume" cx=".36" cy=".28" r=".75"><stop stopColor="#ffffff" stopOpacity=".95" /><stop offset=".58" stopColor="#b9dce9" stopOpacity=".72" /><stop offset="1" stopColor="#6795af" stopOpacity=".82" /></radialGradient>
        <radialGradient id="torsoVolume" cx=".35" cy=".2" r=".9"><stop stopColor="#effaff" stopOpacity=".92" /><stop offset=".45" stopColor="#b9dfed" stopOpacity=".72" /><stop offset=".78" stopColor="#78abc5" stopOpacity=".7" /><stop offset="1" stopColor="#426f8e" stopOpacity=".82" /></radialGradient>
        <linearGradient id="rimLight" x1="0" x2="1"><stop stopColor="#ffffff" /><stop offset=".5" stopColor="#7ccbf0" /><stop offset="1" stopColor="#ffffff" /></linearGradient>
        <radialGradient id="kneeSeverity"><stop stopColor="#ffb347" stopOpacity=".95" /><stop offset=".45" stopColor="#ffcf79" stopOpacity=".5" /><stop offset="1" stopColor="#ffb347" stopOpacity="0" /></radialGradient>
        <linearGradient id="heatMap" x1="0" x2="1"><stop stopColor="#42b8ef" /><stop offset=".5" stopColor="#fbe19b" /><stop offset="1" stopColor="#ff6b6b" /></linearGradient>
        <filter id="bodyDepth" x="-35%" y="-20%" width="170%" height="150%"><feGaussianBlur in="SourceAlpha" stdDeviation="2.2" result="blur" /><feOffset dx="4" dy="6" result="offset" /><feColorMatrix in="offset" values="0 0 0 0 0.12 0 0 0 0 0.29 0 0 0 0 0.42 0 0 0 .3 0" /><feBlend in="SourceGraphic" /></filter>
      </defs>
      <g className="body-breathe">
        <g className="human-model" filter="url(#bodyDepth)">
          <ellipse cx="110" cy="41" rx="25" ry="30" fill="url(#faceVolume)" stroke="url(#rimLight)" strokeWidth="1.8" />
          <path className="ear" d="M86 36c-6-2-7 9-1 13M134 36c6-2 7 9 1 13" />
          <path className="face-detail" d="M101 36c2-2 5-2 7 0m5 0c2-2 5-2 7 0M110 37l-2 10 4 1M104 54c4 3 8 3 12 0" />
          <path className="neck" d="M99 66l-2 17h26l-2-17c-7 4-15 4-22 0Z" fill="url(#glassSkin)" stroke="url(#rimLight)" strokeWidth="1.5" />
          <path className="torso" d="M97 78c-8 2-21 5-26 14-7 18-2 45 3 67 4 18 9 39 6 62-1 11 7 22 17 26 8 3 18 3 26 0 10-4 18-15 17-26-3-23 2-44 6-62 5-22 10-49 3-67-5-9-18-12-26-14-8 7-18 7-26 0Z" fill="url(#torsoVolume)" stroke="url(#rimLight)" strokeWidth="1.8" />
          <path className="arm right-arm" d="M73 92c-9 5-12 17-14 34l-8 61-8 46c-2 10 3 17 9 17 7 0 11-6 12-14l8-44 9-56c3-18 4-34-8-44Z" fill="url(#glassSkinDark)" stroke="url(#rimLight)" strokeWidth="1.6" />
          <path className="arm left-arm" d="M147 92c9 5 12 17 14 34l8 61 8 46c2 10-3 17-9 17-7 0-11-6-12-14l-8-44-9-56c-3-18-4-34 8-44Z" fill="url(#glassSkin)" stroke="url(#rimLight)" strokeWidth="1.6" />
          <path className="hand-detail" d="M43 233l-3 13m8-13-1 16m128-16 3 13m-8-13 1 16" />
          <path className="hips" d="M80 218c7 12 17 17 30 17s23-5 30-17l5 29c-8 15-20 22-35 22s-27-7-35-22Z" fill="url(#glassSkinDark)" stroke="url(#rimLight)" strokeWidth="1.6" />
          <path className="leg right-leg" d="M78 243c-3 18-4 38-2 56l-1 42-8 62c-2 13 6 21 16 17l10-7 3-72 9-45 5-29c-8-16-19-22-32-24Z" fill="url(#glassSkinDark)" stroke="url(#rimLight)" strokeWidth="1.8" />
          <path className="leg left-leg" d="M142 243c3 18 4 38 2 56l1 42 8 62c2 13-6 21-16 17l-10-7-3-72-9-45-5-29c8-16 19-22 32-24Z" fill="url(#glassSkin)" stroke="url(#rimLight)" strokeWidth="1.8" />
          <path className="foot right-foot" d="M67 403c-4 8-12 14-17 18-3 4 1 8 8 8h24c7 0 10-4 10-12l-9 3c-10 4-18-4-16-17Z" fill="url(#glassSkinDark)" stroke="url(#rimLight)" strokeWidth="1.6" />
          <path className="foot left-foot" d="M153 403c4 8 12 14 17 18 3 4-1 8-8 8h-24c-7 0-10-4-10-12l9 3c10 4 18-4 16-17Z" fill="url(#glassSkin)" stroke="url(#rimLight)" strokeWidth="1.6" />
          <path className="body-highlight" d="M96 83c-10 16-11 51-5 81 5 24 6 51 0 73M81 255c4 9 7 17 7 29l-4 49-7 70M145 103c5 31-4 66-5 91" />
          <path className="body-shadow" d="M123 82c14 29 8 71 4 105-2 20 1 42 10 54M137 257c-5 17-5 34-2 50l3 91" />
        </g>
        <g className="anatomy-lines">
          <path d="M110 76v181M91 96l19 18 19-18M83 244l27 23 27-23M84 257v139M136 257v139" />
          <path d="M99 87c-9 12-13 28-12 48m34-48c9 12 13 28 12 48M93 154c10 6 24 6 34 0M96 176c9 5 19 5 28 0" />
          <circle cx="84" cy="280" r="10" /><path d="M75 280h18M84 271v18" />
        </g>
        <g className="muscle-groups">
          <path d="M78 250c-6 15-6 31 5 38 7-9 11-23 8-37Z" /><path d="M91 251c8 12 6 26-8 37" />
          <path d="M129 251c-7 13-5 27 7 37 8-11 9-24 5-37Z" /><path d="M141 252c7 12 5 25-5 36" />
          <path d="M76 292c-2 18-1 33 8 43 8-11 9-27 3-43ZM133 292c-5 17-3 32 5 43 8-11 8-27 5-43Z" />
        </g>
        <g className="right-knee" style={{ opacity: glow }}>
          <circle className="knee-glow" cx="84" cy="280" r="39" fill="url(#kneeSeverity)" />
          <circle className="alert-ring" cx="84" cy="280" r="18" />
          <rect x="72" y="270" width="24" height="20" rx="6" fill="#f7fbff" fillOpacity=".82" stroke="#1b2a4a" strokeWidth="1.5" />
          <path d="M76 280h16" stroke="#ff8d64" strokeWidth="2" strokeDasharray="3 2" />
          <text x="66" y="276">R</text>
        </g>
        <g className="mobility-overlay" transform={`rotate(${bend} 84 280)`}>
          <path d="M84 280l-8 104" /><path className="angle-arc-twin" d="M84 248a32 32 0 0 0-26 48" />
          <text x="48" y="257">{Math.round(74 + progress * 25)}°</text>
        </g>
        <g className="wound-overlay"><circle cx="84" cy="280" r="24" fill="url(#heatMap)" opacity=".7" /><path d="M73 280h22" /></g>
        <g className="sensor-overlay"><rect x="72" y="267" width="25" height="25" rx="7" /><path d="M78 274h13M78 279h13M78 284h8" /></g>
      </g>
    </svg>
    {layer === "Wound" && <div className="wound-strip"><span><i className="wound-thumb" /><small>Day 1</small></span><b>→</b><span><i className="wound-thumb after" /><small>Today</small></span></div>}
    {layer === "Mobility" && <div className="overlay-readout">Knee angle <b>{Math.round(74 + progress * 25)}°</b><span>Goal 110°</span></div>}
    {layer === "Sensors" && <div className="sensor-readout"><Chip tone="yellow">37.8°C</Chip><Chip tone="blue">Moisture 42%</Chip><small>▮▮▮ Signal · 82% battery</small><b>SIMULATED</b></div>}
    {layer === "Muscles" && <div className="muscle-legend"><span><i /> Low</span><span><i /> Moderate</span><span><i /> Active</span></div>}
  </div>;
}

function TwinScreen() {
  const [layer, setLayer] = useState("Overview");
  const [day, setDay] = useState(4);
  const [selected, setSelected] = useState<string | null>(null);
  const progress = (day - 1) / 41;
  const mobility = Math.round(64 + progress * 55);
  const healing = Math.round(91 + progress * 10);
  const callouts = [
    { key: "mobility", icon: "rotate" as IconName, label: "Mobility", value: `${mobility}%`, trend: "↑", expected: `expected ${Math.min(95, mobility + 7)}%`, tone: "track", status: "On track" },
    { key: "temp", icon: "thermo" as IconName, label: "Temp", value: "37.8°C", trend: "↑", expected: "expected ≤37.4°C", tone: "review", status: "Needs attention" },
    { key: "pain", icon: "activity" as IconName, label: "Pain", value: "3/10", trend: "↓", expected: "expected 4/10", tone: "track", status: "On track" },
    { key: "wound", icon: "camera" as IconName, label: "Wound healing score", value: `${healing}/100`, trend: "↑", expected: "expected 89/100", tone: "track", status: "On track" },
  ];
  return <Phone caption="05 — Digital Twin overview" nav active="twin">
    <TopBar title="My Recovery Twin" action={<Toggle />} />
    <div className="layer-tabs">{["Overview", "Wound", "Mobility", "Sensors", "Muscles"].map(x => <button onClick={() => setLayer(x)} className={layer === x ? "active" : ""} key={x}>{x}</button>)}</div>
    <div className="twin-stage">
      <div className="twin-status"><Icon name="check" size={13} /> Recovery on track · Day {day}/42</div>
      <div className="heart-rate"><span>72 bpm</span><svg className="ecg" viewBox="0 0 390 70"><path d="M0 35h70l10-13 12 34 15-49 14 28h45l9-10 11 20 13-10h191" /></svg></div>
      <div className="platform"><i /></div>
      <RecoveryTwinFigure day={day} layer={layer} highlighted={selected} />
      <svg className="twin-connectors" viewBox="0 0 360 509">
        <path d="M104 148 149 232 165 280" /><path d="M256 137 210 217 165 280" /><path d="M105 313 139 292 165 280" /><path d="M255 300 207 288 165 280" />
        {[["104","148"],["256","137"],["105","313"],["255","300"],["165","280"]].map(([cx,cy], i) => <circle key={i} cx={cx} cy={cy} r={i === 4 ? "5" : "3"} />)}
      </svg>
      {callouts.map((item, i) => <button className={`twin-callout-card ${item.key} ${item.tone} ${selected === item.key ? "selected" : ""}`} style={{ animationDelay: `${i * 80}ms` }} onClick={() => setSelected(item.key)} key={item.key}>
        <i /><span><Icon name={item.icon} size={14} /></span><p><small>{item.label}</small><b>{item.key === "mobility" ? <CountUp value={mobility} suffix="%" /> : item.key === "wound" ? <CountUp value={healing} suffix="/100" /> : item.value} <em>{item.trend}</em></b><strong><u>{item.status}</u> · {item.label.split(" ")[0]} {item.value} · {item.expected}</strong></p>
      </button>)}
      <div className="view-controls"><button aria-label="Rotate view"><Icon name="rotate" size={15} /></button><button aria-label="Zoom in">＋</button><button aria-label="Reset view">⌂</button></div>
      <div className="twin-day-slider"><span>Day 1</span><div><input aria-label="Recovery day" type="range" min="1" max="42" value={day} onChange={e => setDay(Number(e.target.value))} /><b style={{ left: `${progress * 100}%` }}>Day {day} · {day === 4 ? "Today" : day < 4 ? "Past" : "Preview"}</b></div><span>Day 42</span></div>
      {selected && <div className="twin-evidence-sheet">
        <button className="sheet-close" onClick={() => setSelected(null)} aria-label="Close detail"><Icon name="close" size={14} /></button>
        <div><small>7-DAY TREND</small><b>{callouts.find(x => x.key === selected)?.label}</b></div>
        <div className="evidence-chart"><i /><MiniLine color={selected === "temp" ? "#FFB347" : "#1e88e5"} fill /></div>
        <div className="latest-evidence">{selected === "wound" ? <div className="wound-thumb" /> : <span><Icon name={selected === "temp" ? "sensor" : "activity"} size={17} /></span>}<p><small>LATEST EVIDENCE</small><b>{selected === "wound" ? "Photo analyzed today, 9:42 AM" : "Live reading · updated 2 min ago"}</b></p></div>
      </div>}
    </div>
    <div className="expected-card"><div className="chart-copy"><small>EXPECTED VS ACTUAL</small><b>On track <span>✓</span></b><p>You're 2 days ahead</p></div><div className="dual-chart"><MiniLine color="#1e88e5" fill /><MiniLine color="#70809d" dashed /></div></div>
  </Phone>;
}

function TwinDetail() {
  const detail = [["Temperature", "36.9°C", "yellow", "thermo"], ["Moisture", "42%", "pink", "drop"], ["Redness", "Low", "pink", "activity"], ["Knee angle", "92°", "yellow", "rotate"]];
  return <Phone caption="06 — Twin body-part detail">
    <TopBar title="Right knee" action={<RoundButton icon="close" />} />
    <div className="detail-stage"><BodyFigure zoom /><Chip tone="green">Healing well ✓</Chip><span className="day-tag">Day 6</span></div>
    <div className="bottom-sheet">
      <div className="sheet-handle" /><div className="sheet-title"><div><small>BODY PART DETAIL</small><b>Right knee</b></div><Chip tone="green">On track</Chip></div>
      <div className="overview-grid">{detail.map(([t, v, tone, icon]) => <div className={`overview-item ${tone}`} key={t}><Icon name={icon as IconName} size={18} /><small>{t}</small><b>{v}</b></div>)}<button className="view-more">View more</button></div>
      <div className="photo-title"><b>Last wound photo</b><small>Today, 9:42 AM</small></div>
      <div className="photo-card"><div className="wound-thumb"><span /></div><div><b>Healing normally</b><small>Redness reduced by 8%</small></div><button>Compare</button></div>
    </div>
  </Phone>;
}

function WoundScan() {
  return <Phone caption="07 — AI wound scan">
    <TopBar title="Wound scan" action={<RoundButton icon="close" />} />
    <div className="camera-view">
      <div className="camera-gradient" /><div className="scan-frame"><i /><i /><i /><i /><div className="wound-shape" /></div>
      <Chip tone="dark">Align the wound inside the frame</Chip>
      <div className="camera-tools"><span>Auto</span><button><Icon name="camera" size={26} /></button><span>Flash off</span></div>
    </div>
    <div className="scan-result">
      <div className="section-row"><div><small>AI COMPARISON</small><b>Healing progress</b></div><Chip tone="green">Looking good</Chip></div>
      <div className="comparison"><div className="wound-image old"><span>DAY 1</span><i /></div><div className="wound-image today"><span>TODAY</span><i /></div><div className="compare-handle">‹ ›</div></div>
      <div className="result-chips"><Chip tone="pink">Redness <b>↑ 12%</b></Chip><Chip tone="yellow">Swelling <b>→ stable</b></Chip><Chip tone="green">Area <b>↓ 8%</b></Chip><Chip tone="blue">Discharge <b>none</b></Chip></div>
      <Button>Save scan</Button>
    </div>
  </Phone>;
}

function SensingRequest() {
  return <Phone caption="08 — Active sensing request" nav active="twin">
    <div className="blur-page">
      <div className="home-head"><div className="avatar">MM</div><div><small>Good morning</small><b>Maya</b></div><RoundButton icon="bell" /></div>
      <div className="page-title">Recovery activity</div>
      <div className="ghost-card" /><div className="ghost-row"><div /><div /></div>
    </div>
    <div className="modal-scrim">
      <div className="sensor-modal">
        <button className="modal-close"><Icon name="close" /></button>
        <div className="sensor-illustration"><span className="sensor-ripple r1" /><span className="sensor-ripple r2" /><span className="sensor-device"><Icon name="sensor" size={28} /></span></div>
        <Chip tone="lavender">DRESSING SENSOR</Chip>
        <div className="modal-title">A small temperature<br />rise was detected</div>
        <p>Can you take a quick photo of your wound? This helps us understand what changed.</p>
        <Button icon="camera">Take photo</Button><Button secondary>Later</Button>
        <div className="evidence"><div className="evidence-title"><b>Evidence collected</b><span>3 of 4</span></div><div className="evidence-dots">{["Sensor alert", "Photo request", "Symptom check", "Evidence ready"].map((x, i) => <div className={i < 3 ? "done" : ""} key={x}><span>{i < 3 ? "✓" : "4"}</span><small>{x}</small></div>)}</div></div>
      </div>
    </div>
  </Phone>;
}

function ArcGauge() {
  const bars = Array.from({ length: 16 });
  return <div className="arc-gauge"><svg viewBox="0 0 280 150">{bars.map((_, i) => {
    const angle = -168 + i * 10.5; const x = 140 + Math.cos(angle * Math.PI / 180) * 107; const y = 135 + Math.sin(angle * Math.PI / 180) * 107;
    return <rect key={i} x={x - 5} y={y - 15} width="10" height="30" rx="5" fill={i < 13 ? "#1e88e5" : "#fff"} transform={`rotate(${angle + 90} ${x} ${y})`} />;
  })}</svg><div><b>82<sup>%</sup></b><small>Flexion</small></div></div>;
}

function Rehab() {
  return <Phone caption="09 — Rehab knee angle" nav active="checkin">
    <TopBar title="Knee rehab" action={<Toggle />} />
    <div className="rehab-card"><div className="rehab-label"><small>TODAY'S GOAL</small><Chip tone="white">Target 110°</Chip></div><ArcGauge /><p>Almost done, keep pushing<br />strong today <span>💪</span></p></div>
    <div className="pose-camera">
      <div className="pose-head" /><div className="pose-body" /><div className="pose-leg upper" /><div className="pose-leg lower" />
      <svg viewBox="0 0 350 220"><path d="M193 58 180 130 250 177" /><circle cx="193" cy="58" r="5" /><circle cx="180" cy="130" r="7" /><circle cx="250" cy="177" r="5" /><path className="angle-arc" d="M180 100a30 30 0 0 1 27 44" /></svg>
      <div className="angle-label">92°<small>target 110°</small></div><Chip tone="dark">8 reps left</Chip><div className="live-dot">● LIVE</div>
    </div>
    <div className="rehab-metrics"><div className="yellow"><small>MAX ANGLE</small><b>98°</b><span>+6° today</span></div><div className="pink"><small>REPS</small><b>12<sup>/20</sup></b><span>Great form</span></div><div className="mint"><small>PAIN AFTER</small><b>3<sup>/10</sup></b><span>Within range</span></div></div>
  </Phone>;
}

function Escalation({ acknowledged, openFamilyAlert }: { acknowledged: boolean; openFamilyAlert: () => void }) {
  return <Phone caption="10 — Doctor evidence package" id="patient-dressing-alert">
    <TopBar title="Clinical alert" />
    <div className="alert-shared"><div className="doctor-avatar">DR</div><div><small>ALERT SHARED</small><b>Dr. Elena Ruiz</b><span>Sent today at 10:18 AM</span></div><span className="sent-check"><Icon name="check" size={16} /></span></div>
    <div className="page-title compact">Your care team has<br />the full picture</div>
    <div className="trajectory"><span>!</span><div><small>ATTENTION NEEDED</small><b>Abnormal recovery trajectory detected</b><p>Your temperature and redness have increased together.</p></div></div>
    <button className="family-alert-link" onClick={openFamilyAlert}><Icon name="bell" size={16} /><span><b>Family notified</b><small>Ahmed received a needs-attention alert</small></span><strong>›</strong></button>
    {acknowledged && <div className="seen-confirmation"><Icon name="check" size={15} /> Ahmed has seen your alert</div>}
    <div className="evidence-package">
      <div className="package-title"><div><small>AI EVIDENCE PACKAGE</small><b>What changed</b></div><Chip tone="blue">4 sources</Chip></div>
      <div className="timeline">
        <div><span><Icon name="sensor" /></span><p><b>Dressing sensor</b><small>Temperature rising since 7:30 AM</small></p><time>07:30</time></div>
        <div><span><Icon name="camera" /></span><p><b>Wound camera</b><small>Redness increased by 12%</small></p><time>09:42</time></div>
        <div><span><Icon name="checkin" /></span><p><b>Symptom check</b><small>Patient reported chills</small></p><time>10:06</time></div>
      </div>
      <div className="evidence-visuals"><div className="temp-chart"><small>TEMPERATURE</small><b>38.2°C <em>↑</em></b><MiniLine color="#ef695d" fill /></div><div className="compare-mini"><div className="wound-thumb" /><div className="wound-thumb worse" /><span>Day 1 → Today</span></div></div>
      <blockquote>“Call your surgeon if fever is over 38°C or redness spreads.”<small>— Discharge instruction, page 3</small></blockquote>
    </div>
    <div className="button-row sticky-actions"><Button icon="phone">Call clinic</Button><Button secondary icon="message">Send message</Button></div>
  </Phone>;
}

function RoleSelection() {
  const [role, setRole] = useState<"patient" | "family">("patient");
  return <Phone caption="00 — Role selection">
    <div className="role-page">
      <div className="brand"><span className="brand-mark"><Icon name="activity" size={19} /></span>SurgiGuard <b>AI</b></div>
      <div className="role-kicker">LET'S GET STARTED</div>
      <div className="page-title role-title">Who are you?</div>
      <p className="muted">Choose how you'll use SurgiGuard. You can change this later.</p>
      <button className={`role-card patient-role compact-role ${role === "patient" ? "selected" : ""}`} onClick={() => setRole("patient")}>
        <span className="role-check">{role === "patient" && <Icon name="check" size={15} />}</span>
        <span className="role-illustration patient-illustration"><span className="person-head" /><span className="person-body" /><i>♥</i></span>
        <span className="role-copy"><b>I'm the patient</b><small>Manage my recovery at home</small></span>
        <strong>→</strong>
      </button>
      <button className={`role-card family-role compact-role ${role === "family" ? "selected" : ""}`} onClick={() => setRole("family")}>
        <span className="role-check">{role === "family" && <Icon name="check" size={15} />}</span>
        <span className="role-illustration doctor-illustration"><span className="person-head" /><span className="person-body" /><i>⌁</i></span>
        <span className="role-copy"><b>I'm a family member</b><small>Follow someone I care about</small></span>
        <strong>→</strong>
      </button>
      <div className="role-note"><Icon name="check" size={16} /><span><b>Your data stays private</b><small>Encrypted and shared only with your care team.</small></span></div>
      <Button>Continue <span>→</span></Button>
    </div>
  </Phone>;
}

function DoctorLogin() {
  return <Phone caption="00B — Clinician login">
    <TopBar title="" />
    <div className="login-page">
      <div className="clinician-mark"><Icon name="activity" size={28} /></div>
      <div className="brand login-brand">SurgiGuard <b>AI</b><span>CLINICIAN</span></div>
      <div className="page-title centered">Welcome back,<br />doctor</div>
      <p className="muted centered">Securely access your patient recovery dashboard.</p>
      <label className="field-label">CLINIC ID</label>
      <div className="login-field"><Icon name="profile" size={18} /><span>SG-CLINIC-2048</span></div>
      <label className="field-label">PASSWORD</label>
      <div className="login-field"><span className="lock-dot">••••••••</span><button>Show</button></div>
      <div className="login-options"><span>✓ Keep me signed in</span><button>Forgot password?</button></div>
      <Button>Sign in securely <span>→</span></Button>
      <div className="sso-divider"><span>or continue with</span></div>
      <Button secondary>Hospital SSO</Button>
      <div className="secure-note"><span>◆</span> HIPAA-compliant · End-to-end encrypted</div>
    </div>
  </Phone>;
}

function FamilyProfile() {
  return <Phone caption="11 — Family access & care team" nav active="profile">
    <TopBar title="Profile" action={<RoundButton icon="message" />} />
    <div className="profile-hero"><div className="avatar profile-avatar">MM</div><div><b>Maya Miller</b><small>Recovery day 6 of 42</small></div><button>Edit</button></div>
    <div className="family-card">
      <div className="section-row"><div><small>YOUR SUPPORT CIRCLE</small><b>Family & caregivers</b></div><button className="invite-button">+ Invite</button></div>
      <div className="member-row"><div className="member-avatar blue">JM</div><div><b>James Miller</b><small>Partner</small></div><Chip tone="blue">Caregiver</Chip></div>
      <div className="member-row"><div className="member-avatar pink">EL</div><div><b>Emma Lee</b><small>Sister</small></div><Chip tone="pink">Family</Chip></div>
      <div className="member-row"><div className="member-avatar yellow">DM</div><div><b>David Miller</b><small>Father</small></div><Chip tone="yellow">View only</Chip></div>
      <button className="share-access"><span className="qr-mini">▦</span><span><b>Share access instantly</b><small>Generate a secure QR code or invite link</small></span><strong>›</strong></button>
    </div>
    <div className="care-card">
      <div className="section-row"><div><small>ASSIGNED CLINICIAN</small><b>Care team</b></div><Chip tone="green">● Connected</Chip></div>
      <div className="surgeon-row"><div className="doctor-avatar portrait">ER</div><div><b>Dr. Elena Ruiz</b><small>Orthopedic surgeon</small><span>St. Joseph Medical Center</span></div></div>
      <Button secondary icon="message">Message care team</Button>
    </div>
    <div className="profile-links"><div><span>◎</span><b>Privacy & consent</b><strong>›</strong></div><div><span>⚙</span><b>Recovery preferences</b><strong>›</strong></div></div>
  </Phone>;
}

function FamilyNav({ active }: { active: string }) {
  const items: [IconName, string][] = [["home", "Home"], ["bell", "Updates"], ["twin", "Recovery"], ["profile", "Profile"]];
  return <div className="bottom-nav family-nav">{items.map(([icon, label]) => <button className={active === label ? "active" : ""} key={label}><span><Icon name={icon} size={19} /></span><small>{label}</small></button>)}</div>;
}

function FamilyPhone({ children, caption, active, id }: { children: ReactNode; caption: string; active?: string; id?: string }) {
  return <div className="phone-wrap" id={id}><div className="phone"><StatusBar /><div className={`screen ${active ? "has-nav" : ""}`}>{children}</div>{active && <FamilyNav active={active} />}<div className="home-indicator" /></div><div className="caption">{caption}</div></div>;
}

function FamilyAccess({ openJoin }: { openJoin: () => void }) {
  const [sharing, setSharing] = useState([true, true, true, true, true]);
  const [members, setMembers] = useState(["Ahmed Khan", "Emma Lee"]);
  const items: [IconName, string][] = [["sensor", "Sensor data"], ["camera", "Wound photos"], ["checkin", "Symptoms & pain"], ["file", "Medications"], ["activity", "Exercises"]];
  return <Phone caption="11 — Patient family access" nav active="profile" id="patient-family-access">
    <TopBar title="Family access" />
    <div className="invite-panel">
      <div><small>SECURE INVITE</small><b>Invite a family member</b><span>Expires in 24 hours</span></div>
      <div className="qr-code" aria-label="QR code"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
      <div className="pair-code"><small>6-DIGIT CODE</small><b>482 916</b></div>
      <button className="copy-link" onClick={openJoin}><Icon name="upload" size={15} /> Share secure link</button>
    </div>
    <div className="section-row family-section"><b>Linked family members</b><small>{members.length} people</small></div>
    <div className="linked-list">{members.map((name, i) => <div key={name}><div className={`member-avatar ${i ? "pink" : "blue"}`}>{name.split(" ").map(x => x[0]).join("")}</div><span><b>{name}</b><small>{i ? "Sister" : "Partner"} · View only</small></span><button onClick={() => setMembers(v => v.filter(x => x !== name))}>Remove</button></div>)}</div>
    <div className="section-row family-section"><div><b>What family can see</b><small>You can change this anytime</small></div></div>
    <div className="privacy-list">{items.map(([icon, title], i) => <div key={title}><span><Icon name={icon} size={15} /></span><p><b>{title}</b><small>Family can see this</small></p><button className={`switch ${sharing[i] ? "on" : ""}`} onClick={() => setSharing(v => v.map((x, n) => n === i ? !x : x))}><i /></button></div>)}</div>
  </Phone>;
}

function JoinPatient({ openHome }: { openHome: () => void }) {
  return <FamilyPhone caption="F01 — Join a patient" id="family-join">
    <TopBar title="Join a patient" />
    <div className="join-hero"><span><Icon name="scan" size={30} /></span><div className="page-title centered">Connect to Sarah's<br />recovery</div><p className="muted centered">Scan Sarah's invite QR code or enter the secure code.</p></div>
    <button className="scan-card"><div className="scan-frame"><i /><i /><i /><i /><Icon name="camera" size={25} /></div><b>Scan QR code</b><small>Point your camera at Sarah's invite</small></button>
    <div className="or-divider"><span>or type the 6-digit code</span></div>
    <div className="code-boxes">{["4", "8", "2", "9", "1", "6"].map((n, i) => <span key={i}>{n}</span>)}</div>
    <div className="joined-card"><span><Icon name="check" size={22} /></span><div><small>CONNECTED SECURELY</small><b>You're now following Sarah's recovery</b><p>You can see her status, shared updates, alerts, and approved recovery data.</p></div></div>
    <Button onClick={openHome}>Go to Sarah's recovery <span>→</span></Button>
  </FamilyPhone>;
}

function FamilyHome({ openUpdates }: { openUpdates: () => void }) {
  return <FamilyPhone caption="F02 — Family home · read only" active="Home" id="family-home">
    <div className="caregiver-banner"><Icon name="profile" size={15} /><span>Family view · <b>Read only</b></span><button>Switch patient</button></div>
    <div className="home-head caregiver-head"><div className="avatar blue-avatar">AK<span /></div><div><small>Welcome back</small><b>Hi, Ahmed</b></div><RoundButton icon="bell" /></div>
    <div className="family-patient-card"><div className="avatar">SM</div><div><small>YOU'RE FOLLOWING</small><b>Sarah Miller</b><span>Total knee replacement · Day 6 of 42</span></div></div>
    <div className="family-status on-track"><span><Icon name="check" size={20} /></span><div><small>CURRENT STATUS</small><b>On track</b><p>No urgent changes · Updated 12 min ago</p></div></div>
    <div className="metric-pair caregiver-metrics"><div className="metric-card pink"><small>WOUND TEMP</small><b>36.9<sup>°C</sup></b><span>Normal range</span><MiniBars /></div><div className="metric-card yellow"><small>PAIN TODAY</small><b>3<sup>/10</sup></b><span>Shared by Sarah</span><MiniLine /></div></div>
    <button className="latest-update" onClick={openUpdates}><span><Icon name="check" size={16} /></span><div><small>LATEST UPDATE · 10:18 AM</small><b>Sarah completed today's check-in</b></div><strong>›</strong></button>
    <div className="readonly-card"><small>READ-ONLY ACCESS</small><div><span>Recovery plan</span><b>View only</b></div><div><span>Medications</span><b>No changes</b></div><div><span>Check-ins</span><b>Sarah answers</b></div></div>
  </FamilyPhone>;
}

function FamilyUpdates() {
  const updates: [string, IconName, string, string][] = [
    ["10:18 AM", "check", "track", "Sarah completed today's check-in"],
    ["9:42 AM", "camera", "review", "SurgiGuard asked Sarah for a wound photo"],
    ["9:40 AM", "thermo", "review", "Sarah's dressing temperature changed"],
    ["8:15 AM", "activity", "track", "Morning exercise task completed"],
    ["7:30 AM", "bell", "urgent", "An alert was sent to Sarah and her care team"],
    ["Yesterday", "file", "private", "Sarah keeps this private"],
  ];
  return <FamilyPhone caption="F03 — Family updates" active="Updates" id="family-updates">
    <TopBar title="Updates" back={false} action={<RoundButton icon="bell" />} />
    <div className="page-title compact">Sarah's recovery<br />updates</div>
    <p className="muted">Newest first · Shared according to Sarah's privacy choices</p>
    <div className="updates-list">{updates.map(([time, icon, tone, text]) => <div className={tone} key={`${time}-${text}`}><time>{time}</time><span><Icon name={icon} size={17} /></span><p>{text}</p></div>)}</div>
  </FamilyPhone>;
}

type FamilyAlertTone = "info" | "attention" | "urgent";

const familyAlerts = {
  info: {
    label: "Update",
    title: "Sarah completed today's check-in",
    copy: "Pain is 3/10 and no new symptoms were reported.",
    time: "now",
  },
  attention: {
    label: "Needs attention",
    title: "Sarah's dressing is warmer than expected",
    copy: "SurgiGuard asked her for a wound photo.",
    time: "2m ago",
  },
  urgent: {
    label: "Urgent",
    title: "Sarah reported an emergency symptom",
    copy: "Immediate action may be needed.",
    time: "now",
  },
} as const;

function LockNotification({ tone, open }: { tone: FamilyAlertTone; open: () => void }) {
  const alert = familyAlerts[tone];
  return <Phone caption={`F04 — ${alert.label} lock-screen notification`}>
    <div className={`lock-screen ${tone}`}>
      <div className="lock-time"><b>12:41</b><span>Tuesday, June 10</span></div>
      <button className="lock-notification" onClick={open}>
        <span className="notification-mark"><Icon name={tone === "info" ? "check" : "bell"} size={18} /></span>
        <span className="notification-copy"><small><b>SURGIGUARD AI</b> · {alert.time}</small><strong>{alert.label}</strong><span>{alert.title}</span><em>{alert.copy}</em></span>
      </button>
      <div className="lock-actions"><span><Icon name="camera" size={19} /></span><span>⌁</span></div>
      <small className="swipe-up">⌃ &nbsp; Swipe up to open</small>
    </div>
  </Phone>;
}

function FamilyInfoAlert({ acknowledge }: { acknowledge: () => void }) {
  const [seen, setSeen] = useState(false);
  const markSeen = () => { setSeen(true); acknowledge(); };
  return <FamilyPhone caption="F05 — Info update detail" id="family-info">
    <TopBar title="Recovery update" />
    <div className="alert-detail-icon info"><Icon name="check" size={27} /></div>
    <Chip tone="blue">INFORMATION</Chip>
    <div className="page-title compact centered">Sarah completed<br />today's check-in</div>
    <p className="muted centered">Today at 10:18 AM</p>
    <div className="info-summary"><div><span><Icon name="checkin" /></span><p><small>PAIN</small><b>3 out of 10</b></p></div><div><span><Icon name="activity" /></span><p><small>SYMPTOMS</small><b>No new symptoms</b></p></div><div><span><Icon name="check" /></span><p><small>STATUS</small><b>On track</b></p></div></div>
    <div className="plain-note"><b>Good to know</b><p>This is a routine update. Sarah's recovery remains on track.</p></div>
    <Button onClick={markSeen}>{seen ? "Seen" : "I've seen this"} {seen && <Icon name="check" size={17} />}</Button>
  </FamilyPhone>;
}

function FamilyAttentionAlert({ acknowledge }: { acknowledge: () => void }) {
  const [seen, setSeen] = useState(false);
  const markSeen = () => { setSeen(true); acknowledge(); };
  return <FamilyPhone caption="F06 — Needs attention detail" id="family-attention">
    <TopBar title="Needs attention" />
    <div className="attention-heading"><span><Icon name="thermo" size={24} /></span><div><small>NEEDS ATTENTION</small><b>Sarah's dressing is warmer than expected</b><p>SurgiGuard asked her for a wound photo.</p></div></div>
    <div className="change-card"><div className="section-row"><div><small>WHAT CHANGED</small><b>Temperature rose 1.3°C</b></div><Chip tone="yellow">Since 7:30 AM</Chip></div><MiniLine color="#ef695d" fill /><div className="temperature-row"><span>7:30 AM <b>36.9°C</b></span><strong>→</strong><span>10:06 AM <b>38.2°C</b></span></div></div>
    <div className="signals-card"><small>SIGNALS THAT AGREE</small><div><span><Icon name="sensor" size={17} /></span><p><b>Dressing sensor</b><small>Temperature rising steadily</small></p><Icon name="check" size={16} /></div><div><span><Icon name="camera" size={17} /></span><p><b>Wound photo requested</b><small>Waiting for Sarah to upload</small></p><Icon name="check" size={16} /></div><div><span><Icon name="checkin" size={17} /></span><p><b>Symptom check</b><small>Sarah reported feeling warm</small></p><Icon name="check" size={16} /></div></div>
    <div className="contact-actions"><Button icon="phone">Call Sarah</Button><Button secondary icon="phone">Contact her surgeon's office</Button></div>
    <Button onClick={markSeen}>{seen ? "Alert acknowledged" : "I've seen this"} {seen && <Icon name="check" size={17} />}</Button>
  </FamilyPhone>;
}

function FamilyUrgentAlert({ acknowledge }: { acknowledge: () => void }) {
  const [seen, setSeen] = useState(false);
  const markSeen = () => { setSeen(true); acknowledge(); };
  return <FamilyPhone caption="F07 — Urgent alert detail" id="family-urgent">
    <div className="urgent-family-alert">
      <div className="urgent-top"><RoundButton icon="close" /><Chip>URGENT ALERT</Chip><span /></div>
      <div className="urgent-symbol">!</div>
      <div className="urgent-title">Sarah reported an<br />emergency symptom</div>
      <p>Sarah reported sudden trouble breathing at 12:39 PM.</p>
      <div className="urgent-guidance"><b>Act now</b><span>Call emergency services first. Do not wait for a reply from Sarah or her care team.</span></div>
      <div className="urgent-buttons"><Button icon="phone">Call emergency services</Button><Button secondary icon="phone">Call Sarah</Button><Button secondary onClick={markSeen}>{seen ? "Seen · I'm on my way" : "I'm on my way"}</Button></div>
      <button className="urgent-seen" onClick={markSeen}><Icon name="check" size={16} /> {seen ? "Alert acknowledged" : "I've seen this"}</button>
    </div>
  </FamilyPhone>;
}

function ConsentScreen() {
  const [enabled, setEnabled] = useState([true, true, true, false]);
  const items = [["camera", "Wound photos", "Images and AI wound measurements"], ["sensor", "Sensor data", "Temperature and dressing moisture"], ["checkin", "Symptoms", "Pain, swelling and daily check-ins"], ["activity", "Rehab videos", "Exercise clips and joint angles"]] as const;
  return <Phone caption="13 — Data sharing consent">
    <TopBar title="Data sharing" />
    <div className="consent-visual"><div className="avatar">MM</div><span className="consent-line" /><div className="doctor-avatar portrait">ER</div><span className="consent-shield"><Icon name="check" size={19} /></span></div>
    <div className="page-title centered">Share my recovery data<br />with Dr. Elena Ruiz</div>
    <p className="muted centered consent-intro">Choose what your surgeon can see. You can update or revoke access at any time.</p>
    <div className="consent-doctor"><div className="doctor-avatar portrait">ER</div><div><b>Dr. Elena Ruiz</b><small>Orthopedic Surgery · St. Joseph</small></div><Chip tone="green">Verified</Chip></div>
    <div className="consent-list">{items.map(([icon,title,copy], i) => <div key={title}><span className={`consent-icon c${i}`}><Icon name={icon} size={18} /></span><p><b>{title}</b><small>{copy}</small></p><button className={`switch ${enabled[i] ? "on" : ""}`} onClick={() => setEnabled(v => v.map((x,n) => n === i ? !x : x))}><i /></button></div>)}</div>
    <div className="consent-foot"><Icon name="check" size={15} /><span>Your consent is securely recorded and visible to you.</span></div>
    <Button>Confirm sharing</Button><button className="text-button">Not now</button>
  </Phone>;
}

type Triage = "urgent" | "review" | "track";
const triage = { urgent: "#FF6B6B", review: "#FFB347", track: "#5ED3A0" };

function ClinicianNav({ active }: { active: string }) {
  const items: [IconName, string][] = [["bell", "Inbox"], ["profile", "Patients"], ["file", "Daily Report"], ["report", "Analytics"], ["twin", "Profile"]];
  return <div className="bottom-nav clinician-nav">{items.map(([icon,label]) => <button key={label} className={active === label ? "active" : ""}><span><Icon name={icon} size={19} /></span><small>{label}</small></button>)}</div>;
}

function DoctorPhone({ children, caption, active }: { children: ReactNode; caption: string; active?: string }) {
  return <div className="phone-wrap"><div className="phone clinician-phone"><StatusBar /><div className={`screen ${active ? "has-nav" : ""}`}>{children}</div>{active && <ClinicianNav active={active} />}<div className="home-indicator" /></div><div className="caption">{caption}</div></div>;
}

function TriageChip({ level, children }: { level: Triage; children: ReactNode }) {
  return <span className={`triage-chip ${level}`}>{children}</span>;
}

function DoctorHome() {
  return <DoctorPhone caption="C01 — Doctor home" active="Inbox">
    <div className="home-head"><div className="doctor-avatar portrait">ER<span /></div><div><small>Good morning</small><b>Dr. Elena Ruiz</b></div><div className="head-actions"><RoundButton icon="search" /><div className="badged"><RoundButton icon="bell" /><i>2</i></div></div></div>
    <div className="page-title compact">Today at a glance</div>
    <div className="triage-summary">{[["urgent","2","Urgent"],["review","5","Need review"],["track","31","On track"]].map(([level,num,label]) => <div className={level} key={level}><b>{num}</b><small>{label}</small><span>●</span></div>)}</div>
    <div className="emergency-card"><div className="section-row"><div><small>PRIORITY QUEUE</small><b>Emergency alerts</b></div><TriageChip level="urgent">2 urgent</TriageChip></div><UrgentPatient initials="MJ" name="Marcus Jones" surgery="Knee replacement · Day 6" alert="Fever + redness rising" time="12 min ago" /><UrgentPatient initials="AK" name="Ana Kim" surgery="Hip replacement · Day 3" alert="O₂ low + dizziness" time="28 min ago" /></div>
    <div className="report-ready"><div className="report-icon"><Icon name="file" /></div><div><small>DAILY REPORT</small><b>Ready to review</b><span>38 patients · 7 need attention</span></div><button>Open report</button></div>
    <div className="weekly-alerts"><div><small>ALERTS THIS WEEK</small><b>18 total</b><span>↓ 12% from last week</span></div><div className="alert-bars">{[38,61,45,82,55,74,31].map((h,i) => <i key={i} style={{height:`${h}%`,background: i === 3 ? triage.urgent : i === 5 ? triage.review : "#A9E3FA"}} />)}</div></div>
  </DoctorPhone>;
}

function UrgentPatient({ initials,name,surgery,alert,time }: { initials:string;name:string;surgery:string;alert:string;time:string }) {
  return <div className="urgent-patient"><div className="member-avatar pink">{initials}</div><div className="urgent-copy"><b>{name}</b><small>{surgery}</small><TriageChip level="urgent">{alert}</TriageChip></div><div className="urgent-action"><small>{time}</small><button>Review</button></div></div>;
}

function AlertsInbox() {
  const alerts = [
    ["MJ","Marcus Jones","67 · Knee replacement","Day 6","Temperature ↑ 1.8°C, redness ↑ 15%, pain 3→7","urgent","3 of 3 signals agree","12m"],
    ["AK","Ana Kim","59 · Hip replacement","Day 3","O₂ 91%, dizziness reported, poor sleep","urgent","2 of 3 signals agree","28m"],
    ["RS","Robert Shaw","72 · Shoulder repair","Day 8","Pain increasing, missed two exercises","review","2 of 3 signals agree","1h"],
    ["LP","Lena Park","48 · ACL repair","Day 12","Knee angle 8° below expected","review","1 of 3 signals","2h"],
  ];
  return <DoctorPhone caption="C02 — Emergency alerts inbox" active="Inbox">
    <TopBar title="Alerts" back={false} action={<RoundButton icon="search" />} />
    <div className="filter-tabs"><button className="active">All <i>7</i></button><button>Urgent <i>2</i></button><button>Review <i>5</i></button><button>Resolved</button></div>
    <div className="sort-row"><b>Priority first</b><button>Sort: Severity⌄</button></div>
    <div className="alerts-list">{alerts.map((a,i) => <div className={`alert-list-card ${a[5]}`} key={a[1]}><span className="severity-bar" /><div className="alert-card-head"><div className="member-avatar blue">{a[0]}</div><div><b>{a[1]}</b><small>{a[2]} · {a[3]}</small></div><span>{a[7]} ago</span></div><p>{a[4]}</p><div className="signal-row"><div><span><Icon name="sensor" size={13} />✓</span><span><Icon name="camera" size={13} />✓</span><span><Icon name="checkin" size={13} />✓</span></div><b>{a[6]}</b></div><div className="confidence"><i style={{width:i === 3 ? "35%" : i === 2 ? "68%" : "100%"}} /></div><div className="swipe-actions"><button><Icon name="phone" size={13} /> Call</button><button><Icon name="message" size={13} /> Message</button><button>Mark reviewed</button></div></div>)}</div>
  </DoctorPhone>;
}

function PatientList() {
  const patients = [["MJ","Marcus Jones","Knee replacement","6","42","urgent"],["AK","Ana Kim","Hip replacement","3","36","urgent"],["RS","Robert Shaw","Shoulder repair","8","35","review"],["LP","Lena Park","ACL repair","12","42","review"],["GH","Grace Hall","Knee replacement","18","42","track"],["TW","Theo Wong","Hip replacement","24","36","track"]];
  return <DoctorPhone caption="C03 — Patient list" active="Patients">
    <TopBar title="My patients" back={false} action={<div className="view-toggle"><button className="active">List</button><button>Grid</button></div>} />
    <div className="doctor-search"><Icon name="search" size={17} /><span>Search patients</span><button>⌘ K</button></div>
    <div className="patient-filters"><button>Surgery type ⌄</button><button>Risk level ⌄</button><button>Post-op day ⌄</button></div>
    <div className="patient-count"><b>38 patients</b><span><i className="dot urgent" />2 urgent <i className="dot track" />31 on track</span></div>
    <div className="patients-list">{patients.map((p,i) => <div className="patient-row" key={p[1]}><span className={`patient-status ${p[5]}`} /><div className={`member-avatar ${i%2 ? "pink":"blue"}`}>{p[0]}</div><div className="patient-info"><b>{p[1]}</b><small>{p[2]}</small><span>Day {p[3]} of {p[4]}</span></div><svg viewBox="0 0 70 32"><path d={i < 2 ? "M2 7C20 5 22 10 34 14S52 27 68 28" : i < 4 ? "M2 19C17 10 30 20 43 15S59 17 68 11" : "M2 25C14 23 23 18 34 17S53 10 68 7"} /><circle cx="68" cy={i < 2 ? 28 : i < 4 ? 11 : 7} r="3" /></svg><strong>›</strong></div>)}</div>
  </DoctorPhone>;
}

function CompactTwin() {
  return <div className="compact-twin"><BodyFigure /><div className="twin-callout">Right knee<b>Hotspot</b></div><span className="tap-hint">Tap to explore</span></div>;
}

function PatientEvidence() {
  return <DoctorPhone caption="C04 — Patient evidence package" active="Patients">
    <div className="patient-detail-head"><RoundButton icon="arrow" /><div><b>Marcus Jones</b><small>Knee replacement · Day 6</small></div><RoundButton icon="phone" /><RoundButton icon="message" /></div>
    <div className="doctor-tabs"><button className="active">Overview</button><button>Sensors</button><button>Wound photos</button><button>Symptoms</button><button>Rehab</button><button>Documents</button></div>
    <div className="abnormal-card"><span>!</span><div><small>URGENT · TODAY, 10:32</small><b>Abnormal recovery trajectory detected</b><p>3 independent signals indicate possible infection.</p></div></div>
    <div className="evidence-hero"><CompactTwin /><div className="change-timeline"><small>WHAT CHANGED & WHEN</small><div><time>08:10</time><span><Icon name="sensor" size={13} /></span><p><b>Dressing sensor</b><small>Temperature rise</small></p><MiniLine color="#FF6B6B" /></div><div><time>09:45</time><span><Icon name="camera" size={13} /></span><p><b>Wound photo</b><small>Redness +15%</small></p><div className="tiny-wounds"><i /><i /></div></div><div><time>10:20</time><span><Icon name="checkin" size={13} /></span><p><b>Patient check-in</b><small>Pain 7/10 · discharge</small></p></div><div><time>10:30</time><span><Icon name="activity" size={13} /></span><p><b>Rehab</b><small>85° · expected 105°</small></p></div></div></div>
    <div className="instruction-card"><small>RELEVANT DISCHARGE INSTRUCTION</small><p>“Contact your surgeon if fever is above 38°C or if redness spreads.”</p><span>Document p. 3</span></div>
    <div className="deviation-card"><div><small>EXPECTED VS ACTUAL</small><b>Recovery deviation</b><span>–18% from expected</span></div><svg viewBox="0 0 160 65"><path className="area" d="M3 54C38 39 72 31 106 18S141 8 157 5L157 42C132 37 111 46 86 44S42 51 3 56Z" /><path className="expected" d="M3 54C38 39 72 31 106 18S141 8 157 5" /><path className="actual" d="M3 56C42 51 62 42 86 44S132 37 157 42" /></svg></div>
    <div className="ai-disclaimer">✦ AI-assisted, clinical decision remains yours.</div>
  </DoctorPhone>;
}

function WoundComparisonDoctor() {
  return <DoctorPhone caption="C05 — Wound comparison">
    <TopBar title="Wound comparison" action={<button className="annotate-top">Annotate</button>} />
    <div className="patient-mini"><div className="member-avatar blue">MJ</div><div><b>Marcus Jones</b><small>Right knee · Day 6</small></div><TriageChip level="urgent">Urgent</TriageChip></div>
    <div className="wound-full"><div className="wound-skin"><i /><span className="measure-line m1">4.8 cm</span><span className="measure-line m2">1.7 cm</span></div><div className="zoom-tools"><button>−</button><span>100%</span><button>+</button><button><Icon name="scan" size={17} /></button></div><div className="image-label">TODAY · 09:45</div></div>
    <div className="day-thumbnails">{["Day 1","Day 4","Today"].map((x,i) => <button className={i===2 ? "active" : ""} key={x}><span className={`wound-thumb w${i}`} /><b>{x}</b><small>{i===0 ? "Jun 4" : i===1 ? "Jun 7" : "Jun 10"}</small></button>)}</div>
    <div className="ai-measurements"><div className="section-row"><div><small>AI MEASUREMENTS</small><b>Change since Day 1</b></div><Chip tone="pink">High confidence</Chip></div><div className="measurement-grid"><div className="urgent"><small>REDNESS</small><b>↑ 15%</b></div><div className="track"><small>WOUND AREA</small><b>↓ 3%</b></div><div className="review"><small>SWELLING</small><b>↑ Rising</b></div><div className="urgent"><small>DISCHARGE</small><b>Detected</b></div></div></div>
    <div className="button-row wound-actions"><Button secondary icon="scan">Annotate</Button><Button icon="camera">Request new photo</Button></div>
  </DoctorPhone>;
}

function DoctorActions() {
  const actions: [IconName,string,string][] = [["phone","Call patient","Connect now"],["message","Send message","Secure chat"],["camera","Request more data","Photo or symptom check"],["file","Adjust recovery protocol","Medication or rehab"],["activity","Schedule urgent visit","Book clinic slot"],["bell","Escalate to the ER","Send emergency guidance"]];
  return <DoctorPhone caption="C06 — Doctor actions">
    <div className="action-backdrop"><div className="patient-detail-head"><RoundButton icon="arrow" /><div><b>Marcus Jones</b><small>Urgent alert</small></div></div><div className="ghost-clinical" /><div className="ghost-clinical small" /></div>
    <div className="doctor-sheet"><div className="sheet-handle" /><div className="sheet-title"><div><small>RESPOND TO ALERT</small><b>How do you want to respond?</b></div><RoundButton icon="close" /></div><div className="doctor-actions-grid">{actions.map(([icon,title,sub],i) => <button className={i===5 ? "danger" : ""} key={title}><span><Icon name={icon} /></span><b>{title}</b><small>{sub}</small><strong>›</strong></button>)}</div><label className="field-label">ADD A CLINICAL NOTE</label><div className="clinical-note">Patient contacted. Reviewing symptoms and advising next steps…<span>0/500</span></div><Button>Send response</Button><div className="notify-toast"><Icon name="check" size={17} /> Patient notified</div></div>
  </DoctorPhone>;
}

function RiskRing() {
  return <div className="risk-ring"><div><b>38</b><small>patients</small></div></div>;
}

function DailyReport() {
  return <DoctorPhone caption="C07 — Daily report" active="Daily Report">
    <TopBar title="Daily report" back={false} action={<Toggle />} />
    <div className="report-date">Tuesday, June 10 <span>Updated 6 min ago</span></div>
    <div className="daily-summary"><div><small>DAILY OVERVIEW</small><b>38 patients monitored</b><p>Your highest priority is 2 urgent alerts.</p></div><div className="summary-numbers"><span><b>2</b>Urgent</span><span><b>5</b>Review</span><span><b>0</b>Missed</span></div></div>
    <div className="risk-card"><RiskRing /><div><small>RISK DISTRIBUTION</small><p><span className="dot urgent" /><b>Urgent</b><strong>2 · 5%</strong></p><p><span className="dot review" /><b>Needs review</b><strong>5 · 13%</strong></p><p><span className="dot track" /><b>On track</b><strong>31 · 82%</strong></p></div></div>
    <div className="report-sections"><div className="expanded"><header><span className="dot urgent" /><b>Urgent</b><i>2</i><strong>⌃</strong></header><div><span>MJ</span><p><b>Marcus Jones</b><small>Fever and wound redness rising</small></p><button>Open</button></div><div><span>AK</span><p><b>Ana Kim</b><small>Low O₂ and dizziness reported</small></p><button>Open</button></div></div>{[["review","Needs review","5"],["track","Stable","31"],["neutral","Missing data","0"]].map(x => <div className="collapsed" key={x[1]}><span className={`dot ${x[0]}`} /><b>{x[1]}</b><i>{x[2]}</i><small>{x[1] === "Missing data" ? "No photo/check-in today" : ""}</small><strong>⌄</strong></div>)}</div>
    <div className="auto-report"><span>Send daily at <b>07:00</b></span><button className="switch on"><i /></button></div>
    <Button secondary icon="file">Export PDF</Button>
  </DoctorPhone>;
}

function Analytics() {
  return <DoctorPhone caption="C08 — Clinical analytics" active="Analytics">
    <TopBar title="Analytics" back={false} action={<RoundButton icon="file" />} />
    <div className="analytics-filter"><button>Last 7 days</button><button className="active">30 days</button><button>All</button></div>
    <div className="analytics-hero"><div><small>CARE IMPACT</small><b>14</b><span>Avoided emergency visits</span><p>↑ 18% vs previous period</p></div><div className="impact-rings"><i /><i /><span><Icon name="check" /></span></div></div>
    <div className="analytics-grid">
      <div className="analytics-card score-card"><small>AVG RECOVERY SCORE</small><b>86<sup>%</sup></b><span>Across all surgeries</span><div className="surgery-bars"><i style={{height:"76%"}} /><i style={{height:"91%"}} /><i style={{height:"66%"}} /><i style={{height:"84%"}} /></div><div className="axis"><span>Knee</span><span>Hip</span><span>ACL</span><span>Shoulder</span></div></div>
      <div className="analytics-card response-card"><small>ALERT RESPONSE</small><b>8.4<sup>min</sup></b><span>Average response time</span><MiniLine color="#1E88E5" fill /><em>↓ 2.1 min faster</em></div>
      <div className="analytics-card signs-card"><small>TOP WARNING SIGNS</small>{[["Rising temperature","38%","urgent"],["Increased pain","31%","review"],["Redness","24%","pink"],["Low mobility","18%","blue"]].map(x => <p key={x[0]}><b>{x[0]}</b><i><span className={x[2]} style={{width:x[1]}} /></i><strong>{x[1]}</strong></p>)}</div>
      <div className="analytics-card compliance-card"><small>PATIENT COMPLIANCE</small><div className="compliance-ring"><b>91%</b></div><p><span>Photos</span><b>94%</b></p><p><span>Check-ins</span><b>88%</b></p></div>
    </div>
  </DoctorPhone>;
}

function DoctorProfile() {
  const [toggles,setToggles] = useState([true,true,true,false]);
  return <DoctorPhone caption="C09 — Clinician profile & settings" active="Profile">
    <TopBar title="Profile & settings" back={false} action={<button className="annotate-top">Edit</button>} />
    <div className="doctor-profile-card"><div className="doctor-avatar portrait large">ER<span /></div><div><b>Dr. Elena Ruiz</b><small>Orthopedic surgeon</small><span>St. Joseph Medical Center</span><em>Provider ID · 493822</em></div><Chip tone="green">Verified</Chip></div>
    <div className="settings-title">NOTIFICATION SETTINGS</div>
    <div className="settings-card">
      <Setting icon="bell" title="Urgent alerts" copy="Push notification + sound" on={toggles[0]} toggle={() => setToggles(v=>v.map((x,i)=>i===0?!x:x))} />
      <div className="critical-row"><span>Critical mode</span><small>Bypasses silent mode</small><Chip tone="pink">Recommended</Chip></div>
      <Setting icon="file" title="Daily report" copy="Every day at 07:00" on={toggles[1]} toggle={() => setToggles(v=>v.map((x,i)=>i===1?!x:x))} />
      <Setting icon="report" title="Weekly summary" copy="Every Monday at 08:00" on={toggles[2]} toggle={() => setToggles(v=>v.map((x,i)=>i===2?!x:x))} />
    </div>
    <div className="delegate-card"><div className="delegate-icon"><Icon name="profile" /></div><div><b>Delegate to a colleague</b><small>Route alerts while you're off-duty</small></div><button className={`switch ${toggles[3]?"on":""}`} onClick={()=>setToggles(v=>v.map((x,i)=>i===3?!x:x))}><i /></button></div>
    <div className="section-row team-title"><div><small>COLLABORATORS</small><b>Care team</b></div><button>Manage</button></div>
    <div className="clinical-team"><div className="stacked-avatars"><span>JW</span><span>NP</span><span>+3</span></div><div><b>5 team members</b><small>2 nurses · 2 assistants · 1 coordinator</small></div><strong>›</strong></div>
    <div className="profile-links clinician-links"><div><span>⌁</span><b>Security & hospital SSO</b><strong>›</strong></div><div><span>?</span><b>Help & clinical support</b><strong>›</strong></div></div>
  </DoctorPhone>;
}

function Setting({icon,title,copy,on,toggle}:{icon:IconName;title:string;copy:string;on:boolean;toggle:()=>void}) {
  return <div className="setting-row"><span><Icon name={icon} size={17} /></span><p><b>{title}</b><small>{copy}</small></p><button className={`switch ${on?"on":""}`} onClick={toggle}><i /></button></div>;
}

export default function App() {
  const [familyAcknowledged, setFamilyAcknowledged] = useState(true);
  const goTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "center" });
  const acknowledge = () => {
    setFamilyAcknowledged(true);
    window.setTimeout(() => goTo("patient-dressing-alert"), 250);
  };
  return <main className="presentation">
    <header className="presentation-header"><div className="brand"><span className="brand-mark"><Icon name="activity" size={19} /></span>SurgiGuard <b>AI</b></div><div><span>POSTOPERATIVE HOME RECOVERY</span><b>Patient experience · Mobile</b></div></header>
    <div className="phone-grid"><RoleSelection /><Welcome /><UploadReports /><Protocol /><HomeScreen /><TwinScreen /><TwinDetail /><WoundScan /><SensingRequest /><Rehab /><Escalation acknowledged={familyAcknowledged} openFamilyAlert={() => { setFamilyAcknowledged(false); goTo("family-attention"); }} /><FamilyAccess openJoin={() => goTo("family-join")} /><FamilyProfile /><ConsentScreen /></div>
    <header className="presentation-header family-header"><div className="brand"><span className="brand-mark family"><Icon name="profile" size={19} /></span>SurgiGuard <b>AI</b><em>FAMILY</em></div><div><span>CONNECTED RECOVERY SUPPORT</span><b>Shared updates · Read-only access</b></div></header>
    <div className="phone-grid family-grid"><JoinPatient openHome={() => goTo("family-home")} /><FamilyHome openUpdates={() => goTo("family-updates")} /><FamilyUpdates /><LockNotification tone="info" open={() => goTo("family-info")} /><FamilyInfoAlert acknowledge={acknowledge} /><LockNotification tone="attention" open={() => goTo("family-attention")} /><FamilyAttentionAlert acknowledge={acknowledge} /><LockNotification tone="urgent" open={() => goTo("family-urgent")} /><FamilyUrgentAlert acknowledge={acknowledge} /></div>
    <header className="presentation-header clinician-header"><div className="brand"><span className="brand-mark clinician"><Icon name="activity" size={19} /></span>SurgiGuard <b>AI</b><em>CLINICIAN</em></div><div><span>CLINICAL COMMAND CENTER</span><b>Fast triage · Complete evidence</b></div></header>
    <div className="phone-grid clinician-grid"><DoctorLogin /><DoctorHome /><AlertsInbox /><PatientList /><PatientEvidence /><WoundComparisonDoctor /><DoctorActions /><DailyReport /><Analytics /><DoctorProfile /></div>
  </main>;
}
