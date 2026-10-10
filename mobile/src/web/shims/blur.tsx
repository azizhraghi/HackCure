import React from 'react';
import { View, type ViewProps } from 'react-native';

export function BlurView({ style, children, ...props }: ViewProps & { blurType?: string; blurAmount?: number; reducedTransparencyFallbackColor?: string }) {
  return <View {...props} style={[{ backgroundColor: 'rgba(255,255,255,0.72)' }, style]}>{children}</View>;
}
