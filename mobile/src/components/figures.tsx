import React, { useEffect } from 'react';
import Animated, { Easing, useAnimatedProps, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated';
import Svg, { Circle, Defs, G, LinearGradient, Path, RadialGradient, Rect, Stop, Text as SvgText } from 'react-native-svg';

const ACircle = Animated.createAnimatedComponent(Circle);

/** Pulsing radius used for hot spots */
function usePulse(duration = 1500) {
  const p = useSharedValue(0);
  useEffect(() => {
    p.value = withRepeat(withTiming(1, { duration, easing: Easing.out(Easing.quad) }), -1, false);
  }, [p, duration]);
  return p;
}

/** BodyFigure from the prototype (Welcome, compact twin) */
export function BodyFigure({ width = 142, height = 294 }: { width?: number; height?: number }) {
  const p = usePulse(1800);
  const ring = useAnimatedProps(() => ({ r: 14 + p.value * 22, opacity: 0.85 * (1 - p.value) }));
  return (
    <Svg width={width} height={height} viewBox="0 0 220 440">
      <Defs>
        <LinearGradient id="body" x1="0" y1="0" x2="1" y2="1"><Stop offset="0" stopColor="#f7fbff" /><Stop offset="0.55" stopColor="#cfeafa" /><Stop offset="1" stopColor="#b7d7ec" /></LinearGradient>
        <RadialGradient id="hot"><Stop offset="0" stopColor="#ff765d" /><Stop offset="0.35" stopColor="#ff957f" stopOpacity={0.75} /><Stop offset="1" stopColor="#ff957f" stopOpacity={0} /></RadialGradient>
      </Defs>
      <Circle cx="110" cy="43" r="29" fill="url(#body)" stroke="#1b2a4a" strokeWidth="2" />
      <Path d="M97 69c-4 9-19 13-29 20-11 8-12 33-15 57l-11 87c-1 11 14 14 18 3l18-82 1 86-15 162c-1 13 17 16 22 3l24-122 24 122c5 13 23 10 22-3l-15-162 1-86 18 82c4 11 19 8 18-3l-11-87c-3-24-4-49-15-57-10-7-25-11-29-20" fill="url(#body)" stroke="#1b2a4a" strokeWidth="2" strokeLinejoin="round" />
      <Path d="M110 74v204M79 240h62M86 146c17 8 31 8 48 0" fill="none" stroke="#87b9d5" strokeWidth="1.3" opacity={0.8} />
      <Circle cx="133" cy="281" r="30" fill="url(#hot)" />
      <ACircle cx="133" cy="281" fill="none" stroke="#ff6f59" strokeWidth={2} animatedProps={ring} />
      <Circle cx="133" cy="281" r="7" fill="#ff6f59" stroke="#fff" strokeWidth="2" />
      <Circle cx="85" cy="147" r="6" fill="#55d99e" stroke="#fff" strokeWidth="2" />
      <Circle cx="136" cy="147" r="6" fill="#42b8ef" stroke="#fff" strokeWidth="2" />
    </Svg>
  );
}

/** Zoomed knee used in TwinDetail */
export function KneeFigure() {
  return (
    <Svg width="100%" height="100%" viewBox="0 0 300 235">
      <Defs>
        <RadialGradient id="kneeGlow"><Stop offset="0" stopColor="#ff967d" stopOpacity={0.95} /><Stop offset="1" stopColor="#ff967d" stopOpacity={0} /></RadialGradient>
      </Defs>
      <Path d="M120 4c-18 42-24 84-10 103 9 12 9 21 2 38-12 27-18 58-12 86M180 4c18 42 24 84 10 103-9 12-9 21-2 38 12 27 18 58 12 86" fill="none" stroke="#d8e9f2" strokeWidth="56" strokeLinecap="round" />
      <Path d="M120 4c-18 42-24 84-10 103 9 12 9 21 2 38-12 27-18 58-12 86M180 4c18 42 24 84 10 103-9 12-9 21-2 38 12 27 18 58 12 86" fill="none" stroke="#1b2a4a" strokeWidth="2" strokeLinecap="round" />
      <Circle cx="189" cy="119" r="46" fill="url(#kneeGlow)" />
      <Circle cx="189" cy="119" r="13" fill="#ff755f" stroke="#1b2a4a" strokeWidth="2" />
      <Path d="M161 119h56M189 91v56" stroke="#fff" strokeWidth="1.5" strokeDasharray="4 4" />
    </Svg>
  );
}

/**
 * 2D glass anatomical twin (RecoveryTwinFigure from the prototype).
 * Used as fallback when WebGL is unavailable for the 3D twin.
 */
export function GlassTwin({ day, layer }: { day: number; layer: string }) {
  const progress = (day - 1) / 41;
  const glow = Math.max(0.24, 0.76 - progress * 0.5);
  const bend = 8 + progress * 22;
  const p = usePulse();
  const ring = useAnimatedProps(() => ({ r: 12 + p.value * 27, opacity: 0.85 * (1 - p.value) }));
  return (
    <Svg width="100%" height="100%" viewBox="0 0 220 440">
      <Defs>
        <LinearGradient id="glassSkin" x1="0" y1="0" x2="1" y2="1"><Stop offset="0" stopColor="#f8fdff" stopOpacity={0.94} /><Stop offset="0.28" stopColor="#d8f0f8" stopOpacity={0.75} /><Stop offset="0.68" stopColor="#9bc9df" stopOpacity={0.66} /><Stop offset="1" stopColor="#6193b2" stopOpacity={0.78} /></LinearGradient>
        <LinearGradient id="glassSkinDark" x1="0" y1="0" x2="1" y2="0.7"><Stop offset="0" stopColor="#b5dded" stopOpacity={0.7} /><Stop offset="0.55" stopColor="#77a9c5" stopOpacity={0.68} /><Stop offset="1" stopColor="#477b9c" stopOpacity={0.8} /></LinearGradient>
        <RadialGradient id="faceVolume" cx="0.36" cy="0.28" r="0.75"><Stop offset="0" stopColor="#ffffff" stopOpacity={0.95} /><Stop offset="0.58" stopColor="#b9dce9" stopOpacity={0.72} /><Stop offset="1" stopColor="#6795af" stopOpacity={0.82} /></RadialGradient>
        <RadialGradient id="torsoVolume" cx="0.35" cy="0.2" r="0.9"><Stop offset="0" stopColor="#effaff" stopOpacity={0.92} /><Stop offset="0.45" stopColor="#b9dfed" stopOpacity={0.72} /><Stop offset="0.78" stopColor="#78abc5" stopOpacity={0.7} /><Stop offset="1" stopColor="#426f8e" stopOpacity={0.82} /></RadialGradient>
        <RadialGradient id="kneeSeverity"><Stop offset="0" stopColor="#ffb347" stopOpacity={0.95} /><Stop offset="0.45" stopColor="#ffcf79" stopOpacity={0.5} /><Stop offset="1" stopColor="#ffb347" stopOpacity={0} /></RadialGradient>
        <LinearGradient id="heatMap" x1="0" x2="1"><Stop offset="0" stopColor="#42b8ef" /><Stop offset="0.5" stopColor="#fbe19b" /><Stop offset="1" stopColor="#ff6b6b" /></LinearGradient>
      </Defs>
      <G stroke="#7ccbf0" strokeWidth={1.7}>
        <Path d="M99 66l-2 17h26l-2-17c-7 4-15 4-22 0Z" fill="url(#glassSkin)" />
        <Path d="M97 78c-8 2-21 5-26 14-7 18-2 45 3 67 4 18 9 39 6 62-1 11 7 22 17 26 8 3 18 3 26 0 10-4 18-15 17-26-3-23 2-44 6-62 5-22 10-49 3-67-5-9-18-12-26-14-8 7-18 7-26 0Z" fill="url(#torsoVolume)" />
        <Path d="M73 92c-9 5-12 17-14 34l-8 61-8 46c-2 10 3 17 9 17 7 0 11-6 12-14l8-44 9-56c3-18 4-34-8-44Z" fill="url(#glassSkinDark)" />
        <Path d="M147 92c9 5 12 17 14 34l8 61 8 46c2 10-3 17-9 17-7 0-11-6-12-14l-8-44-9-56c-3-18-4-34 8-44Z" fill="url(#glassSkin)" />
        <Path d="M80 218c7 12 17 17 30 17s23-5 30-17l5 29c-8 15-20 22-35 22s-27-7-35-22Z" fill="url(#glassSkinDark)" />
        <Path d="M78 243c-3 18-4 38-2 56l-1 42-8 62c-2 13 6 21 16 17l10-7 3-72 9-45 5-29c-8-16-19-22-32-24Z" fill="url(#glassSkinDark)" />
        <Path d="M142 243c3 18 4 38 2 56l1 42 8 62c2 13-6 21-16 17l-10-7-3-72-9-45-5-29c8-16 19-22 32-24Z" fill="url(#glassSkin)" />
        <Path d="M67 403c-4 8-12 14-17 18-3 4 1 8 8 8h24c7 0 10-4 10-12l-9 3c-10 4-18-4-16-17Z" fill="url(#glassSkinDark)" />
        <Path d="M153 403c4 8 12 14 17 18 3 4-1 8-8 8h-24c-7 0-10-4-10-12l9 3c10 4 18-4 16-17Z" fill="url(#glassSkin)" />
        <Circle cx="110" cy="41" r="27" fill="url(#faceVolume)" />
      </G>
      <G fill="none" stroke="#4a7896" strokeWidth={1.5} opacity={0.24}>
        <Path d="M110 76v181M91 96l19 18 19-18M83 244l27 23 27-23M84 257v139M136 257v139" />
        <Path d="M99 87c-9 12-13 28-12 48m34-48c9 12 13 28 12 48M93 154c10 6 24 6 34 0M96 176c9 5 19 5 28 0" />
      </G>
      <G fill="#ee8fa9" stroke="#b75b79" strokeWidth={1} opacity={layer === 'Muscles' ? 0.72 : 0.16}>
        <Path d="M78 250c-6 15-6 31 5 38 7-9 11-23 8-37Z" /><Path d="M129 251c-7 13-5 27 7 37 8-11 9-24 5-37Z" />
        <Path d="M76 292c-2 18-1 33 8 43 8-11 9-27 3-43ZM133 292c-5 17-3 32 5 43 8-11 8-27 5-43Z" />
      </G>
      <G opacity={glow}>
        <Circle cx="84" cy="280" r="39" fill="url(#kneeSeverity)" />
        <ACircle cx="84" cy="280" fill="none" stroke="#ffb347" strokeWidth={2} animatedProps={ring} />
        <Rect x="72" y="270" width="24" height="20" rx="6" fill="#f7fbff" fillOpacity={0.82} stroke="#1b2a4a" strokeWidth="1.5" />
        <Path d="M76 280h16" stroke="#ff8d64" strokeWidth="2" strokeDasharray="3 2" />
        <SvgText x="62" y="276" fontSize="7" fontWeight="800" fill="#1b2a4a">R</SvgText>
      </G>
      {layer === 'Mobility' && (
        <G fill="none" stroke="#1e88e5" strokeWidth={2} rotation={bend} origin="84, 280">
          <Path d="M84 280l-8 104" /><Path d="M84 248a32 32 0 0 0-26 48" strokeDasharray="4 3" />
        </G>
      )}
      {layer === 'Wound' && <G><Circle cx="84" cy="280" r="24" fill="url(#heatMap)" opacity={0.7} /><Path d="M73 280h22" stroke="#fff" strokeWidth={2} strokeDasharray="3 2" /></G>}
      {layer === 'Sensors' && <G fill="#f9fbff" stroke="#1b2a4a" strokeWidth={1.4}><Rect x="72" y="267" width="25" height="25" rx="7" /><Path d="M78 274h13M78 279h13M78 284h8" fill="none" /></G>}
    </Svg>
  );
}
