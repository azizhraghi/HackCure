import React, { useEffect, useMemo, type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { useIsFocused } from '@react-navigation/native';
import { Camera, useCameraDevice, useCameraPermission, useObjectOutput, type ScannedObject } from 'react-native-vision-camera';
import { T } from './T';

type Props = {
  position?: 'back' | 'front';
  /** Rendered when no camera / permission (Figma mock look) */
  fallback: ReactNode;
  permissionLabel: string;
  torch?: boolean;
  onQr?: (value: string) => void;
};

/** Live camera (vision-camera v5) with permission handling and a design fallback. */
export function CameraPreview({ position = 'back', fallback, permissionLabel, torch, onQr }: Props) {
  const { hasPermission, canRequestPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice(position);
  const focused = useIsFocused();

  useEffect(() => {
    if (!hasPermission && canRequestPermission) requestPermission();
  }, [hasPermission, canRequestPermission, requestPermission]);

  if (!hasPermission || !device) {
    return (
      <View style={StyleSheet.absoluteFill}>
        {fallback}
        {!hasPermission && (
          <Pressable onPress={requestPermission} style={{ position: 'absolute', top: 10, alignSelf: 'center', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 99, backgroundColor: 'rgba(27,42,74,0.86)', borderWidth: 1, borderColor: '#fff' }}>
            <T size={8} w={800} color="#fff">{permissionLabel}</T>
          </Pressable>
        )}
      </View>
    );
  }

  return onQr
    ? <QrCamera device={device} active={focused} onQr={onQr} />
    : <Camera style={StyleSheet.absoluteFill} device={device} isActive={focused} torchMode={torch ? 'on' : 'off'} resizeMode="cover" />;
}

function QrCamera({ device, active, onQr }: { device: NonNullable<ReturnType<typeof useCameraDevice>>; active: boolean; onQr: (v: string) => void }) {
  const types = useMemo(() => ['qr' as const], []);
  const output = useObjectOutput({
    types,
    onObjectsScanned: (objects: ScannedObject[]) => {
      const code = objects.find(o => 'value' in o && (o as { value?: string }).value) as { value?: string } | undefined;
      if (code?.value) onQr(code.value);
    },
  });
  return <Camera style={StyleSheet.absoluteFill} device={device} isActive={active} outputs={[output]} resizeMode="cover" />;
}
