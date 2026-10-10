import React, { useEffect, useState } from 'react';
import { View, type StyleProp, type ViewStyle } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, RadialGradient, Rect, Stop } from 'react-native-svg';
import { useTheme } from '../theme/ThemeContext';
import { T } from './T';

const LINE = 'M2 38 C16 36 20 18 33 24 S51 34 64 17 83 28 96 14 118 8';

/** .mini-line sparkline */
export function MiniLine({ color, fill, dashed, height = 44, style }: { color?: string; fill?: boolean; dashed?: boolean; height?: number; style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  const col = color ?? c.text;
  return (
    <Svg width="100%" height={height} viewBox="0 0 120 44" preserveAspectRatio="none" style={[{ marginTop: 5, overflow: 'visible' }, style as any]}>
      {fill && <Path d={`${LINE}V44H2Z`} fill={col} fillOpacity={0.13} />}
      <Path d={LINE} fill="none" stroke={col} strokeWidth={3} strokeLinecap="round" strokeDasharray={dashed ? '5 5' : undefined} />
      <Circle cx="118" cy="8" r="3.5" fill={col} />
    </Svg>
  );
}

/** .mini-bars */
export function MiniBars({ values = [48, 70, 42, 83, 59, 74, 91], color }: { values?: number[]; color?: string }) {
  const { c } = useTheme();
  return (
    <View style={{ height: 40, flexDirection: 'row', alignItems: 'flex-end', gap: 5, marginTop: 9 }}>
      {values.map((h, i) => <View key={i} style={{ width: 7, height: `${h}%`, backgroundColor: color ?? c.text, borderRadius: 5, opacity: 0.87 }} />)}
    </View>
  );
}

/** .score-ring — conic progress ring */
export function ScoreRing({ value, size = 88, label, thickness = 9 }: { value: number; size?: number; label?: string; thickness?: number }) {
  const { c } = useTheme();
  const r = (size - thickness) / 2;
  const circ = 2 * Math.PI * r;
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute', transform: [{ rotate: '-90deg' }] }}>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={c.grey} strokeWidth={thickness} fill="none" />
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={c.primary} strokeWidth={thickness} fill="none" strokeDasharray={`${(circ * value) / 100} ${circ}`} />
      </Svg>
      <T size={size > 80 ? 23 : 17} w={800} spacing={-1}>{value}<T size={10} w={800}>%</T></T>
      {label && <T size={5.5} upper w={600}>{label}</T>}
    </View>
  );
}

/** .arc-gauge — 16 rounded bars on an arc (Rehab) */
export function ArcGauge({ value = 82, label }: { value?: number; label: string }) {
  const { c } = useTheme();
  const filled = Math.round((value / 100) * 16);
  return (
    <View style={{ height: 185 }}>
      <Svg width="100%" height="100%" viewBox="0 0 280 150">
        {Array.from({ length: 16 }).map((_, i) => {
          const angle = -168 + i * 10.5;
          const x = 140 + Math.cos((angle * Math.PI) / 180) * 107;
          const y = 135 + Math.sin((angle * Math.PI) / 180) * 107;
          return <Rect key={i} x={x - 5} y={y - 15} width="10" height="30" rx="5" fill={i < filled ? c.primary : '#fff'} transform={`rotate(${angle + 90} ${x} ${y})`} />;
        })}
      </Svg>
      <View style={{ position: 'absolute', left: 0, right: 0, top: '38%', alignItems: 'center' }}>
        <T size={45} w={800} spacing={-2}>{value}<T size={16} w={800}>%</T></T>
        <T size={9} w={800} style={{ marginTop: 2 }}>{label}</T>
      </View>
    </View>
  );
}

/** .stepper — onboarding steps */
export function Stepper({ steps, current = 0 }: { steps: string[]; current?: number }) {
  const { c } = useTheme();
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: 6, marginBottom: 17 }}>
      <View style={{ position: 'absolute', top: 10, left: 47, right: 47, borderTopWidth: 1.5, borderStyle: 'dashed', borderColor: '#aeb8c9' }} />
      {steps.map((s, i) => (
        <View key={s} style={{ width: 78, alignItems: 'center' }}>
          <View style={{ width: 21, height: 21, borderRadius: 11, borderWidth: 1.2, borderColor: i <= current ? c.ink : '#aab4c5', backgroundColor: i < current ? c.green : i === current ? c.primary : c.bg, alignItems: 'center', justifyContent: 'center' }}>
            <T size={8} w={800} color={i === current ? '#fff' : c.text}>{i < current ? '✓' : i + 1}</T>
          </View>
          <T size={8} w={700} color={i === current ? c.text : c.faint} style={{ marginTop: 4 }}>{s}</T>
        </View>
      ))}
    </View>
  );
}

/** Animated count-up number (CountUp in the prototype) */
export function useCountUp(value: number, decimals = 0) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    let frame = 0;
    const frames = 24;
    const id = setInterval(() => {
      frame += 1;
      setShown(value * Math.min(frame / frames, 1));
      if (frame >= frames) clearInterval(id);
    }, 28);
    return () => clearInterval(id);
  }, [value]);
  return shown.toFixed(decimals);
}

/** Wound photo thumbnail (radial gradient) */
export function WoundThumb({ width = 54, height = 51, radius = 10, worse, dashed, border = true }: { width?: number; height?: number; radius?: number; worse?: boolean; dashed?: boolean; border?: boolean }) {
  const { c } = useTheme();
  const id = `w${width}${height}${worse ? 'x' : ''}`;
  return (
    <View style={{ width, height, borderRadius: radius, overflow: 'hidden', borderWidth: border ? 1 : 0, borderColor: c.ink }}>
      <Svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
        <Defs>
          <RadialGradient id={id} cx="50%" cy="50%" rx="50%" ry="50%">
            <Stop offset="0.08" stopColor={worse ? '#c3463d' : '#d36962'} />
            <Stop offset="0.09" stopColor={worse ? '#ee8b7a' : '#f4aa9b'} />
            <Stop offset="0.2" stopColor={worse ? '#ee8b7a' : '#f4aa9b'} />
            <Stop offset="0.21" stopColor={worse ? '#e9ab95' : '#ecc2ae'} />
            <Stop offset="0.48" stopColor={worse ? '#e9ab95' : '#ecc2ae'} />
            <Stop offset="0.49" stopColor="#dfb299" />
            <Stop offset="1" stopColor="#dfb299" />
          </RadialGradient>
        </Defs>
        <Rect width="100" height="100" fill={`url(#${id})`} />
        {dashed && <Path d="M22 52 L80 44" stroke="#7e3535" strokeWidth={3} strokeDasharray="5 4" />}
      </Svg>
    </View>
  );
}

/** Expected vs actual dual line chart (Reports + Twin) */
export function TrajectoryChart({ height = 120 }: { height?: number }) {
  const { c } = useTheme();
  return (
    <Svg width="100%" height={height} viewBox="0 0 160 65" preserveAspectRatio="none">
      <Defs>
        <LinearGradient id="trajArea" x1="0" y1="0" x2="0" y2="1"><Stop offset="0" stopColor={c.primary} stopOpacity={0.25} /><Stop offset="1" stopColor={c.primary} stopOpacity={0} /></LinearGradient>
      </Defs>
      <Path d="M3 56C30 50 55 40 80 30S130 14 157 8V65H3Z" fill="url(#trajArea)" />
      <Path d="M3 54C38 45 72 36 106 24S141 12 157 10" fill="none" stroke={c.muted} strokeWidth={2} strokeDasharray="5 4" />
      <Path d="M3 56C30 50 55 40 80 30S130 14 157 8" fill="none" stroke={c.primary} strokeWidth={2.6} strokeLinecap="round" />
      <Circle cx="157" cy="8" r="3" fill={c.primary} />
    </Svg>
  );
}
