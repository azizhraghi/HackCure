/// <reference lib="dom" />
import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { GlassTwin } from '../figures';
import { T } from '../T';
import type { Twin3DHandle } from './Twin3D';
import twinHtml from './twinHtml';

type Props = { day: number; layer: string; highlighted: string | null; hr?: number; onTapKnee?: () => void; loadingLabel: string; fallbackLabel: string };

// The scene posts through window.ReactNativeWebView on the phone; in the browser it is an iframe talking to this page.
const BRIDGE = "<script>window.ReactNativeWebView={postMessage:function(d){parent.postMessage({__twin:d},'*')}}</script>";
const srcDoc = twinHtml.replace('<body>', `<body>${BRIDGE}`);

/** Browser build: the same three.js hologram as the phone, in an iframe (2D illustration if WebGL is missing). */
export const Twin3D = forwardRef<Twin3DHandle, Props>(({ day, layer, highlighted, hr = 72, onTapKnee, loadingLabel, fallbackLabel }, ref) => {
  const frame = useRef<HTMLIFrameElement | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const send = (msg: object) => frame.current?.contentWindow?.postMessage(JSON.stringify(msg), '*');

  useImperativeHandle(ref, () => ({ command: cmd => send({ type: 'cmd', cmd }) }));

  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (e.source !== frame.current?.contentWindow || !e.data?.__twin) return;
      try {
        const msg = JSON.parse(e.data.__twin);
        if (msg.type === 'ready') setReady(true);
        if (msg.type === 'error') setFailed(true);
        if (msg.type === 'tap' && msg.part === 'knee') onTapKnee?.();
      } catch {}
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [onTapKnee]);

  useEffect(() => {
    if (ready) send({ type: 'state', day, layer, highlighted, hr });
  }, [ready, day, layer, highlighted, hr]);

  if (failed) {
    return <View style={StyleSheet.absoluteFill}>
      <View style={{ position: 'absolute', left: 92, right: 92, top: 35, bottom: 68 }}><GlassTwin day={day} layer={layer} /></View>
      <T size={6} w={700} color="#8fb3c9" center style={{ position: 'absolute', bottom: 50, left: 0, right: 0 }}>{fallbackLabel}</T>
    </View>;
  }
  return <View style={StyleSheet.absoluteFill}>
    <iframe ref={frame} title="3D recovery twin" srcDoc={srcDoc}
      style={{ border: 0, width: '100%', height: '100%', background: 'transparent', display: 'block' }} />
    {!ready && (
      <View pointerEvents="none" style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center', gap: 8 }]}>
        <ActivityIndicator color="#5fd8ff" />
        <T size={8} w={700} color="#8fb3c9">{loadingLabel}</T>
      </View>
    )}
  </View>;
});
