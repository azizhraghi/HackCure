import React from 'react';
import { View } from 'react-native';

/** Camera framing corners (wound scan, QR join). */
export function Corners({ color = '#fff', size = 42, width = 270, height = 225 }: { color?: string; size?: number; width?: number; height?: number }) {
  const b = { position: 'absolute' as const, width: size, height: size, borderColor: color };
  return (
    <View pointerEvents="none" style={{ width, height }}>
      <View style={[b, { left: 0, top: 0, borderLeftWidth: 3, borderTopWidth: 3, borderTopLeftRadius: 13 }]} />
      <View style={[b, { right: 0, top: 0, borderRightWidth: 3, borderTopWidth: 3, borderTopRightRadius: 13 }]} />
      <View style={[b, { left: 0, bottom: 0, borderLeftWidth: 3, borderBottomWidth: 3, borderBottomLeftRadius: 13 }]} />
      <View style={[b, { right: 0, bottom: 0, borderRightWidth: 3, borderBottomWidth: 3, borderBottomRightRadius: 13 }]} />
    </View>
  );
}
