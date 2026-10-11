import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInUp } from 'react-native-reanimated';
import { Icon } from '../../components/Icon';
import { T } from '../../components/T';
import { Card, Chip, haptic, IconBadge, TopBar } from '../../components/ui';
import { useApi } from '../../context/AppState';
import { useT } from '../../i18n';
import type { RootScreen } from '../../navigation/types';
import type { ChatMessage } from '../../services/backend';
import { useTheme } from '../../theme/ThemeContext';
import { fonts, fs } from '../../theme/tokens';

type Bubble = ChatMessage & { error?: boolean; escalate?: boolean };

export function AIAssistantScreen({ navigation, route }: RootScreen<'AIAssistant'>) {
  const { c } = useTheme();
  const { t, list, lang } = useT();
  const api = useApi();
  const [messages, setMessages] = useState<Bubble[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const scroll = useRef<React.ComponentRef<typeof ScrollView>>(null);

  const ask = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    haptic();
    const history: Bubble[] = [...messages.filter(m => !m.error), { role: 'user', content: q }];
    setMessages(history);
    setInput('');
    setBusy(true);
    try {
      const res = await api.chat(history.map(({ role, content }) => ({ role, content })), lang);
      setMessages(m => [...m, { role: 'assistant', content: res.reply, escalate: res.escalate }]);
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: t('ai.error'), error: true }]);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (route.params?.question) ask(route.params.question);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const showEscalate = messages.some(m => m.escalate);

  return (
    <SafeAreaView edges={['top', 'bottom']} style={{ flex: 1, backgroundColor: c.bg }}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={{ paddingHorizontal: 16 }}>
          <TopBar title={t('ai.top')} />
        </View>
        <ScrollView ref={scroll} onContentSizeChange={() => scroll.current?.scrollToEnd({ animated: true })} contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 16 }} keyboardShouldPersistTaps="handled">
          <Chip tone="lavender" style={{ alignSelf: 'center', marginBottom: 12 }}><Icon name="sparkle" size={12} /><T size={8} w={800}>{t('ai.kicker')}</T></Chip>

          <AssistantBubble text={t('ai.hello')} />
          {messages.length === 0 && (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 6, marginLeft: 38 }}>
              {list('ai.suggestions').map(s => (
                <Pressable key={s} onPress={() => ask(s)} style={({ pressed }) => ({ paddingVertical: 8, paddingHorizontal: 11, borderRadius: 99, borderWidth: 1.2, borderColor: c.ink, backgroundColor: pressed ? c.blue : c.surface })}>
                  <T size={9} w={700}>{s}</T>
                </Pressable>
              ))}
            </View>
          )}
          {messages.map((m, i) => m.role === 'user'
            ? (
              <Animated.View key={i} entering={FadeInUp.duration(220)} style={{ alignSelf: 'flex-end', maxWidth: '82%', marginTop: 10, backgroundColor: c.primary, borderWidth: 1.2, borderColor: c.ink, borderRadius: 18, borderBottomRightRadius: 5, paddingVertical: 9, paddingHorizontal: 12 }}>
                <T size={11} w={600} color="#fff" lh={1.4}>{m.content}</T>
              </Animated.View>
            )
            : <AssistantBubble key={i} text={m.content} error={m.error} />)}
          {busy && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 10, marginLeft: 38 }}>
              <ActivityIndicator size="small" color={c.primary} /><T size={9} color={c.muted}>{t('ai.thinking')}</T>
            </View>
          )}
          {showEscalate && (
            <Animated.View entering={FadeInUp}>
              <Card bg={c.peach} radius={16} style={{ padding: 11, marginTop: 12, flexDirection: 'row', alignItems: 'center', gap: 10, borderColor: c.review }}>
                <IconBadge icon="phone" bg={c.surface} size={32} />
                <View style={{ flex: 1 }}><T size={9.5} w={800}>{t('ai.escalate')}</T><T size={7.5} color={c.muted} style={{ marginTop: 2 }}>{t('ai.escalateSub')}</T></View>
                <Pressable onPress={() => navigation.navigate('Escalation')} style={{ paddingVertical: 7, paddingHorizontal: 11, borderRadius: 99, borderWidth: 1, borderColor: c.ink, backgroundColor: c.primary }}>
                  <T size={8} w={800} color="#fff">{t('ai.contact')}</T>
                </Pressable>
              </Card>
            </Animated.View>
          )}
          <T size={7} color={c.muted} center style={{ marginTop: 16 }}>{t('ai.disclaimer')}</T>
        </ScrollView>

        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 16, paddingTop: 8, paddingBottom: 10, borderTopWidth: 1, borderTopColor: c.navLine, backgroundColor: c.navBg }}>
          <TextInput value={input} onChangeText={setInput} placeholder={t('ai.placeholder')} placeholderTextColor={c.faint} onSubmitEditing={() => ask(input)} returnKeyType="send" multiline
            style={{ flex: 1, minHeight: 46, maxHeight: 110, borderWidth: 1.5, borderColor: c.ink, borderRadius: 15, paddingHorizontal: 14, paddingTop: 12, paddingBottom: 12, color: c.text, fontFamily: fonts[500], fontSize: fs(12), backgroundColor: c.surface }} />
          <Pressable onPress={() => ask(input)} disabled={busy || !input.trim()} style={({ pressed }) => ({ width: 46, height: 46, borderRadius: 15, borderWidth: 1.5, borderColor: c.ink, backgroundColor: input.trim() ? c.primary : c.grey, alignItems: 'center', justifyContent: 'center', opacity: pressed ? 0.8 : 1 })}>
            <Icon name="send" size={20} color={input.trim() ? '#fff' : c.faint} />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function AssistantBubble({ text, error }: { text: string; error?: boolean }) {
  const { c } = useTheme();
  return (
    <Animated.View entering={FadeInUp.duration(260)} style={{ flexDirection: 'row', gap: 8, marginTop: 10, maxWidth: '92%' }}>
      <View style={{ width: 30, height: 30, borderRadius: 10, borderWidth: 1.2, borderColor: c.ink, backgroundColor: c.lavender, alignItems: 'center', justifyContent: 'center' }}>
        <Icon name="sparkle" size={16} />
      </View>
      <View style={{ flexShrink: 1, backgroundColor: error ? c.warnBg : c.surface, borderWidth: 1.2, borderColor: error ? c.warnBorder : c.ink, borderRadius: 18, borderTopLeftRadius: 5, paddingVertical: 9, paddingHorizontal: 12 }}>
        <T size={11} w={500} lh={1.45}>{text}</T>
      </View>
    </Animated.View>
  );
}
