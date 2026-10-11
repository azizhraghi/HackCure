/// <reference lib="dom" />
import React, { useEffect, useRef } from 'react';
import { View } from 'react-native';
import type { CaptureProps } from './MotionCapture';
import captureHtml from './captureHtml';

/** The browser asks for the camera itself when the capture page starts. */
export async function requestCameraPermission(): Promise<boolean> {
  return true;
}

/** Browser: the same capture page in an iframe (camera allowed). Needs https or localhost for the camera. */
export function MotionCapture({ test, seconds, kinds, labels, onFrames, onError }: CaptureProps) {
  const frame = useRef<HTMLIFrameElement | null>(null);
  const config = `<script>window.__CAPTURE=${JSON.stringify({ test, seconds, kinds, labels })}</script>`;
  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (e.source !== frame.current?.contentWindow || !e.data?.__motion) return;
      try {
        const msg = JSON.parse(e.data.__motion);
        if (msg.type === 'frames') onFrames(msg.frames);
        if (msg.type === 'error') onError(msg.reason);
      } catch {}
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [onFrames, onError]);
  return (
    <View style={{ height: 300, borderRadius: 18, overflow: 'hidden', backgroundColor: '#0b1626' }}>
      <iframe ref={frame} title="Movement test camera" allow="camera" srcDoc={captureHtml.replace('<body>', `<body>${config}`)}
        style={{ border: 0, width: '100%', height: '100%', display: 'block' }} />
    </View>
  );
}
