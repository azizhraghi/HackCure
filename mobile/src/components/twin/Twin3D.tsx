import React, { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { WebView as RNWebView, type WebViewMessageEvent, type WebViewProps } from 'react-native-webview';

// react-native-webview's class typings don't resolve against RN 0.87 types; re-type the component.
type WebViewHandle = { postMessage: (data: string) => void };
const WebView = RNWebView as unknown as React.ComponentType<WebViewProps & { ref?: React.Ref<WebViewHandle> }>;
import { GlassTwin } from '../figures';
import { T } from '../T';
import twinHtml from './twinHtml';

export type Twin3DHandle = { command: (cmd: 'rotate' | 'zoom' | 'reset') => void };

type Props = {
  day: number;
  layer: string;
  highlighted: string | null;
  onTapKnee?: () => void;
  loadingLabel: string;
  fallbackLabel: string;
};

/** WebGL (three.js) twin inside a WebView; falls back to the 2D glass SVG. */
export const Twin3D = forwardRef<Twin3DHandle, Props>(({ day, layer, highlighted, onTapKnee, loadingLabel, fallbackLabel }, ref) => {
  const web = useRef<WebViewHandle>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  const send = (msg: object) => web.current?.postMessage(JSON.stringify(msg));

  useImperativeHandle(ref, () => ({ command: cmd => send({ type: 'cmd', cmd }) }));

  useEffect(() => {
    if (ready) send({ type: 'state', day, layer, highlighted });
  }, [ready, day, layer, highlighted]);

  const onMessage = (e: WebViewMessageEvent) => {
    try {
      const msg = JSON.parse(e.nativeEvent.data);
      if (msg.type === 'ready') setReady(true);
      if (msg.type === 'error') setFailed(true);
      if (msg.type === 'tap' && msg.part === 'knee') onTapKnee?.();
    } catch {}
  };

  if (failed) {
    return (
      <View style={StyleSheet.absoluteFill}>
        <View style={{ position: 'absolute', left: 92, right: 92, top: 40, bottom: 79 }}>
          <GlassTwin day={day} layer={layer} />
        </View>
        <T size={6} w={700} color="#70809a" center style={{ position: 'absolute', bottom: 62, left: 0, right: 0 }}>{fallbackLabel}</T>
      </View>
    );
  }

  return (
    <View style={StyleSheet.absoluteFill}>
      <WebView
        ref={web}
        source={{ html: twinHtml, baseUrl: '' }}
        originWhitelist={['*']}
        onMessage={onMessage}
        javaScriptEnabled
        scrollEnabled={false}
        bounces={false}
        overScrollMode="never"
        style={{ backgroundColor: 'transparent' }}
        containerStyle={{ backgroundColor: 'transparent' }}
        androidLayerType="hardware"
        onError={() => setFailed(true)}
        onRenderProcessGone={() => setFailed(true)}
      />
      {!ready && (
        <View pointerEvents="none" style={[StyleSheet.absoluteFill, { alignItems: 'center', justifyContent: 'center', gap: 8 }]}>
          <ActivityIndicator color="#1e88e5" />
          <T size={8} w={700} color="#70809a">{loadingLabel}</T>
        </View>
      )}
    </View>
  );
});
