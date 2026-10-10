import React from 'react';
import { Text, type TextProps, type TextStyle } from 'react-native';
import { useTheme } from '../theme/ThemeContext';
import { fonts, fs, type Weight } from '../theme/tokens';

type Props = TextProps & {
  /** CSS font size from the Figma file; scaled with fs() */
  size?: number;
  w?: Weight;
  color?: string;
  center?: boolean;
  upper?: boolean;
  spacing?: number;
  lh?: number;
};

/** Text with Plus Jakarta Sans and the Figma size scale. */
export function T({ size = 13, w = 400, color, center, upper, spacing, lh, style, ...rest }: Props) {
  const { c } = useTheme();
  const s = fs(size);
  const base: TextStyle = {
    fontFamily: fonts[w],
    fontSize: s,
    color: color ?? c.text,
    includeFontPadding: false,
    ...(center ? { textAlign: 'center' } : null),
    ...(upper ? { textTransform: 'uppercase' } : null),
    ...(spacing !== undefined ? { letterSpacing: spacing } : null),
    ...(lh ? { lineHeight: s * lh } : null),
  };
  return <Text {...rest} style={[base, style]} />;
}

/** Small uppercase label ("TODAY'S TASK", "AI COMPARISON"…) */
export function Kicker({ children, color, size = 7.5, style }: { children: React.ReactNode; color?: string; size?: number; style?: TextProps['style'] }) {
  return <T size={size} w={800} spacing={0.9} upper color={color} style={style}>{children}</T>;
}
