import React, { forwardRef, useImperativeHandle } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { GlassTwin } from '../figures';
import { T } from '../T';
import type { Twin3DHandle } from './Twin3D';

type Props = { day: number; layer: string; highlighted: string | null; onTapKnee?: () => void; loadingLabel: string; fallbackLabel: string };

/** Browser renders the same recovery twin illustration; native WebView interactions remain on mobile. */
export const Twin3D = forwardRef<Twin3DHandle, Props>(({ day, layer, highlighted, onTapKnee, fallbackLabel }, ref) => {
  useImperativeHandle(ref, () => ({ command: () => {} }));
  return <View style={StyleSheet.absoluteFill}>
    <Pressable accessibilityRole="button" accessibilityLabel="Open knee detail" onPress={onTapKnee} style={{ position: 'absolute', left: 92, right: 92, top: 35, bottom: 68 }}>
      <GlassTwin day={day} layer={layer} />
    </Pressable>
    <T size={6} w={700} color="#70809a" center style={{ position: 'absolute', bottom: 50, left: 0, right: 0 }}>{fallbackLabel}</T>
  </View>;
});
