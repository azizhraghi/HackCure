import React from 'react';
import { PermissionsAndroid, Platform, View } from 'react-native';
import { WebView as RNWebView, type WebViewMessageEvent, type WebViewProps } from 'react-native-webview';
import captureHtml from './captureHtml';

const WebView = RNWebView as unknown as React.ComponentType<WebViewProps & Record<string, unknown>>;

export type CaptureProps = {
  test: string;
  seconds: number;
  kinds: string[];
  labels: Record<string, string>;
  onFrames: (frames: object[]) => void;
  onError: (reason: string) => void;
};

/** Android asks for the camera before the WebView may use it. */
export async function requestCameraPermission(): Promise<boolean> {
  if (Platform.OS !== 'android') return true;
  return (await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA)) === PermissionsAndroid.RESULTS.GRANTED;
}

/** Phone: the capture page in a WebView on a secure local origin (needed for the camera); MediaPipe runs on the device. */
export function MotionCapture({ test, seconds, kinds, labels, onFrames, onError }: CaptureProps) {
  const config = `<script>window.__CAPTURE=${JSON.stringify({ test, seconds, kinds, labels })}</script>`;
  const onMessage = (e: WebViewMessageEvent) => {
    try {
      const msg = JSON.parse(e.nativeEvent.data);
      if (msg.type === 'frames') onFrames(msg.frames);
      if (msg.type === 'error') onError(msg.reason);
    } catch {}
  };
  return (
    <View style={{ height: 300, borderRadius: 18, overflow: 'hidden', backgroundColor: '#0b1626' }}>
      <WebView
        source={{ html: captureHtml.replace('<body>', `<body>${config}`), baseUrl: 'https://localhost' }}
        originWhitelist={['*']}
        onMessage={onMessage}
        javaScriptEnabled
        mediaPlaybackRequiresUserAction={false}
        allowsInlineMediaPlayback
        mediaCapturePermissionGrantType="grant"
        style={{ backgroundColor: '#0b1626' }}
        onError={() => onError('webview')}
      />
    </View>
  );
}
