import React, { type ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { trigger } from 'react-native-haptic-feedback';
import { useNavigation } from '@react-navigation/native';
import { useTheme } from '../theme/ThemeContext';
import { BORDER, type Palette } from '../theme/tokens';
import { Icon, type IconName } from './Icon';
import { T } from './T';

export const haptic = (kind: 'impactLight' | 'impactMedium' | 'selection' | 'notificationSuccess' = 'impactLight') => {
  try { trigger(kind, { enableVibrateFallback: false, ignoreAndroidSystemSettings: false }); } catch {}
};

/** Card with the signature 1.5px navy border */
export function Card({ children, style, bg, radius = 19, dashed }: { children?: ReactNode; style?: StyleProp<ViewStyle>; bg?: string; radius?: number; dashed?: boolean }) {
  const { c } = useTheme();
  return <View style={[{ borderWidth: BORDER, borderColor: c.ink, borderRadius: radius, backgroundColor: bg ?? c.surface, borderStyle: dashed ? 'dashed' : 'solid' }, style]}>{children}</View>;
}

/** .primary-button — blue, navy border and 3px hard offset shadow */
export function Button({ children, secondary, icon, onPress, flat, height = 51, style, color, textColor, size = 13 }: {
  children: ReactNode; secondary?: boolean; icon?: IconName; onPress?: () => void; flat?: boolean; height?: number;
  style?: StyleProp<ViewStyle>; color?: string; textColor?: string; size?: number;
}) {
  const { c } = useTheme();
  const bg = color ?? (secondary ? c.surface : c.primary);
  const fg = textColor ?? (secondary ? c.text : c.onPrimary);
  return (
    <Pressable onPress={() => { haptic(); onPress?.(); }} style={[{ height: height + (flat ? 0 : 3) }, style]}>
      {({ pressed }) => (
        <>
          {!flat && <View style={[StyleSheet.absoluteFill, { top: 3, borderRadius: 15, backgroundColor: c.shadow }]} />}
          <View style={{
            height, borderRadius: 15, borderWidth: BORDER, borderColor: c.ink, backgroundColor: bg,
            flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 9,
            transform: [{ translateY: pressed && !flat ? 2 : 0 }], opacity: pressed && flat ? 0.85 : 1,
          }}>
            {icon && <Icon name={icon} size={18} color={fg} />}
            {typeof children === 'string' || Array.isArray(children)
              ? <T size={size} w={800} color={fg}>{children}</T>
              : children}
          </View>
        </>
      )}
    </Pressable>
  );
}

export function RoundButton({ icon, onPress, size = 38, bg }: { icon: IconName; onPress?: () => void; size?: number; bg?: string }) {
  const { c } = useTheme();
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={icon} onPress={() => { haptic('selection'); onPress?.(); }}
      style={({ pressed }) => ({ width: size, height: size, borderRadius: size / 2, borderWidth: BORDER, borderColor: c.ink, backgroundColor: bg ?? c.surface, alignItems: 'center', justifyContent: 'center', opacity: pressed ? 0.7 : 1 })}>
      <Icon name={icon} size={20} />
    </Pressable>
  );
}

/** .top-bar — back button, centered title, optional action */
export function TopBar({ title, back = true, action, onBack }: { title: string; back?: boolean; action?: ReactNode; onBack?: () => void }) {
  const nav = useNavigation();
  return (
    <View style={{ height: 48, flexDirection: 'row', alignItems: 'center', marginBottom: 7 }}>
      <View style={{ width: 80 }}>{back && <RoundButton icon="arrow" onPress={onBack ?? (() => nav.canGoBack() && nav.goBack())} />}</View>
      <T size={15} w={800} center numberOfLines={1} style={{ flex: 1 }}>{title}</T>
      <View style={{ width: 80, alignItems: 'flex-end' }}>{action}</View>
    </View>
  );
}

export type Tone = 'white' | 'blue' | 'green' | 'pink' | 'yellow' | 'lavender' | 'dark' | 'sky';

export function toneColor(c: Palette, tone: Tone | string): string {
  switch (tone) {
    case 'blue': return c.blue;
    case 'green': case 'mint': return c.green;
    case 'pink': return c.pink;
    case 'yellow': return c.yellow;
    case 'lavender': return c.lavender;
    case 'sky': return c.sky;
    case 'dark': return 'rgba(27,42,74,0.86)';
    default: return c.surface;
  }
}

export function Chip({ children, tone = 'white', style, size = 9 }: { children: ReactNode; tone?: Tone; style?: StyleProp<ViewStyle>; size?: number }) {
  const { c } = useTheme();
  const isDark = tone === 'dark';
  return (
    <View style={[{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, borderWidth: 1.2, borderColor: isDark ? '#fff' : c.ink, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 99, backgroundColor: toneColor(c, tone), alignSelf: 'flex-start' }, style]}>
      {typeof children === 'string' ? <T size={size} w={800} color={isDark ? '#fff' : c.text}>{children}</T> : children}
    </View>
  );
}

/** .toggle — Day / Week segmented pill */
export function Toggle({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  const { c } = useTheme();
  return (
    <View style={{ height: 31, backgroundColor: c.grey, borderWidth: 1.2, borderColor: c.ink, borderRadius: 99, padding: 2, flexDirection: 'row' }}>
      {options.map(o => (
        <Pressable key={o} onPress={() => { haptic('selection'); onChange(o); }} style={{ borderRadius: 99, paddingHorizontal: 9, justifyContent: 'center', backgroundColor: value === o ? c.primary : 'transparent' }}>
          <T size={8} w={800} color={value === o ? '#fff' : c.text}>{o}</T>
        </Pressable>
      ))}
    </View>
  );
}

/** .switch */
export function Switch({ on, onToggle, scale = 1 }: { on: boolean; onToggle: () => void; scale?: number }) {
  const { c } = useTheme();
  return (
    <Pressable accessibilityRole="switch" accessibilityState={{ checked: on }} onPress={() => { haptic('selection'); onToggle(); }}
      style={{ width: 38 * scale, height: 22 * scale, borderWidth: 1, borderColor: c.ink, borderRadius: 99, padding: 2, backgroundColor: on ? c.primary : c.switchOff, justifyContent: 'center' }}>
      <View style={{ width: 16 * scale, height: 16 * scale, borderRadius: 99, backgroundColor: '#fff', borderWidth: 1, borderColor: c.ink, transform: [{ translateX: on ? 15 * scale : 0 }] }} />
    </Pressable>
  );
}

export function SectionRow({ title, kicker, right, style }: { title: string; kicker?: string; right?: ReactNode; style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  return (
    <View style={[{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 12, marginBottom: 9, marginHorizontal: 1 }, style]}>
      <View style={{ flexShrink: 1 }}>
        {kicker && <T size={6.5} w={700} spacing={0.9} upper color={c.muted}>{kicker}</T>}
        <T size={13} w={800} style={{ marginTop: kicker ? 2 : 0 }}>{title}</T>
      </View>
      {typeof right === 'string' ? <T size={9} color={c.muted}>{right}</T> : right}
    </View>
  );
}

export function PageTitle({ children, center, size = 29, style }: { children: ReactNode; center?: boolean; size?: number; style?: StyleProp<any> }) {
  const { c } = useTheme();
  return <T size={size} w={800} color={c.title} center={center} spacing={-1.1} style={[{ lineHeight: size * 1.17, marginTop: 13, marginBottom: 9 }, style]}>{children}</T>;
}

export function Muted({ children, center, style }: { children: ReactNode; center?: boolean; style?: StyleProp<any> }) {
  const { c } = useTheme();
  return <T size={12.5} color={c.muted} center={center} lh={1.55} style={[{ marginBottom: 13 }, style]}>{children}</T>;
}

export function Avatar({ initials, size = 41, bg, online, portrait }: { initials: string; size?: number; bg?: string; online?: boolean; portrait?: boolean }) {
  const { c } = useTheme();
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, borderWidth: BORDER, borderColor: c.ink, backgroundColor: bg ?? (portrait ? '#d5c3f7' : c.pink), alignItems: 'center', justifyContent: 'center' }}>
      {portrait && <View style={{ position: 'absolute', left: 0, right: 0, top: 0, height: size * 0.42, borderTopLeftRadius: size / 2, borderTopRightRadius: size / 2, backgroundColor: '#f3c5aa' }} />}
      <T size={size > 45 ? 13 : size < 34 ? 7 : 10.5} w={800} color="#1b2a4a">{initials}</T>
      {online && <View style={{ position: 'absolute', width: 11, height: 11, borderRadius: 6, backgroundColor: '#53d397', borderWidth: 2, borderColor: '#fff', right: -1, bottom: 0 }} />}
    </View>
  );
}

/** Small circular icon badge used in lists */
export function IconBadge({ icon, bg, size = 27, radius = 9, border = true, iconSize = 15, color }: { icon: IconName; bg?: string; size?: number; radius?: number; border?: boolean; iconSize?: number; color?: string }) {
  const { c } = useTheme();
  return (
    <View style={{ width: size, height: size, borderRadius: radius, backgroundColor: bg ?? c.blue, borderWidth: border ? 1 : 0, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
      <Icon name={icon} size={iconSize} color={color} />
    </View>
  );
}

/** "SIMULATED" tag — the prompt requires simulated measurements to be labeled */
export function SimulatedTag({ style }: { style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  return (
    <View style={[{ alignSelf: 'flex-start', paddingHorizontal: 6, paddingVertical: 3, borderRadius: 99, borderWidth: 1, borderColor: c.ink, backgroundColor: c.lavender }, style]}>
      <T size={5.5} w={800} spacing={0.5}>SIMULATED</T>
    </View>
  );
}

/** Standard screen: safe area + scroll + 16px gutter */
export function Screen({ children, scroll = true, style, bg, padded = true, edges = ['top'] }: {
  children: ReactNode; scroll?: boolean; style?: StyleProp<ViewStyle>; bg?: string; padded?: boolean; edges?: ('top' | 'bottom')[];
}) {
  const { c } = useTheme();
  const pad: ViewStyle = padded ? { paddingHorizontal: 16, paddingTop: 4, paddingBottom: 28 } : {};
  return (
    <SafeAreaView edges={edges} style={{ flex: 1, backgroundColor: bg ?? c.bg }}>
      {scroll
        ? <ScrollView contentContainerStyle={[pad, style]} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">{children}</ScrollView>
        : <View style={[{ flex: 1 }, pad, style]}>{children}</View>}
    </SafeAreaView>
  );
}

/** Row in a bordered list (profile links, settings…) */
export function ListRow({ left, title, sub, right, onPress, last }: { left?: ReactNode; title: string; sub?: string; right?: ReactNode; onPress?: () => void; last?: boolean }) {
  const { c } = useTheme();
  return (
    <Pressable onPress={onPress} disabled={!onPress} style={({ pressed }) => ({ minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 10, paddingVertical: 6, borderBottomWidth: last ? 0 : 1, borderBottomColor: c.line, opacity: pressed ? 0.7 : 1 })}>
      {left}
      <View style={{ flex: 1 }}>
        <T size={8.5} w={800}>{title}</T>
        {sub && <T size={6.5} color={c.muted} style={{ marginTop: 2 }}>{sub}</T>}
      </View>
      {right ?? (onPress ? <T size={13} w={800}>›</T> : null)}
    </Pressable>
  );
}
