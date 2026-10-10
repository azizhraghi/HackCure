import React, { type ReactNode } from 'react';
import { View } from 'react-native';
import { T } from './T';

type Props = { fallback: ReactNode };

/** Browser preview keeps the existing camera mock art; live camera capture remains a mobile feature. */
export function CameraPreview({ fallback }: Props) {
  return <View style={{ flex: 1, position: 'relative' }}>
    {fallback}
    <View style={{ position: 'absolute', top: 10, left: 12, borderRadius: 99, backgroundColor: 'rgba(27,42,74,0.86)', borderWidth: 1, borderColor: '#fff', paddingHorizontal: 9, paddingVertical: 5 }}>
      <T size={7} w={800} color="#fff">Camera preview · mobile device only</T>
    </View>
  </View>;
}
