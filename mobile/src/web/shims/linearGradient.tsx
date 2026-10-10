import React from 'react';
import { View, type ViewProps } from 'react-native';

type Props = ViewProps & { colors: string[]; start?: { x: number; y: number }; end?: { x: number; y: number }; locations?: number[] };

export default function LinearGradient({ colors, style, children, start: _start, end: _end, locations: _locations, ...props }: Props) {
  return <View {...props} style={[{ backgroundImage: `linear-gradient(135deg, ${colors.join(', ')})` }, style]}>{children}</View>;
}
