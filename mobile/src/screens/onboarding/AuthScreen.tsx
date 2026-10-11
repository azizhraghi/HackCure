import React, { useState } from 'react';
import { ActivityIndicator, Pressable, TextInput, View, type TextInputProps } from 'react-native';
import { Brand } from '../../components/Brand';
import { T } from '../../components/T';
import { Button, Card, haptic, Muted, PageTitle, Screen, TopBar } from '../../components/ui';
import { useAppState } from '../../context/AppState';
import { useT } from '../../i18n';
import { ApiError, createApi, toSession } from '../../services/backend';
import { useTheme } from '../../theme/ThemeContext';
import { fonts } from '../../theme/tokens';

function Field({ label, ...props }: { label: string } & TextInputProps) {
  const { c } = useTheme();
  return (
    <View style={{ marginTop: 9 }}>
      <T size={7} w={800} spacing={0.6} style={{ marginBottom: 4, marginHorizontal: 2 }}>{label}</T>
      <TextInput autoCapitalize="none" autoCorrect={false} placeholderTextColor={c.faint} {...props}
        style={{ height: 46, borderWidth: 1.2, borderColor: c.ink, borderRadius: 12, paddingHorizontal: 12, color: c.text, fontFamily: fonts[600], backgroundColor: c.surface }} />
    </View>
  );
}

/** Sign in / create an account on the backend, after picking a role. */
export function AuthScreen() {
  const { c } = useTheme();
  const { t } = useT();
  const { role, accountUrl, setAccountUrl, signIn, continueAsDemo, resetRole } = useAppState();
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', phone: '' });
  const [server, setServer] = useState(accountUrl);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof typeof form) => (value: string) => setForm(f => ({ ...f, [key]: value }));
  const isPatient = role !== 'family';

  const submit = async () => {
    const register = mode === 'register';
    if (!form.email || !form.password || (register && (!form.firstName || !form.lastName))) {
      setError(t('auth.required'));
      return;
    }
    setBusy(true);
    setError(null);
    const url = server.trim();
    if (url !== accountUrl) setAccountUrl(url);
    const api = createApi({ apiUrl: url });
    try {
      const res = register
        ? await api.register({
            email: form.email.trim(),
            password: form.password,
            role: isPatient ? 'PATIENT' : 'FAMILY_MEMBER',
            first_name: form.firstName.trim(),
            last_name: form.lastName.trim(),
            phone: form.phone.trim() || undefined,
          })
        : await api.login(form.email.trim(), form.password);
      const session = toSession(res);
      if (session.user.role !== 'PATIENT' && session.user.role !== 'FAMILY_MEMBER') {
        setError(t('auth.staff'));
        return;
      }
      // Existing patient → straight to the app; family → only once linked to a patient
      let onboarded = !register;
      if (session.user.role === 'FAMILY_MEMBER') {
        onboarded = (await createApi({ apiUrl: url, token: session.token }).followedPatients()).length > 0;
      }
      haptic('notificationSuccess');
      signIn(session, onboarded);
    } catch (e) {
      setError(e instanceof ApiError && e.status !== 0 ? e.message : t('auth.network'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <TopBar title={t('auth.top')} onBack={resetRole} />
      <Brand />
      <PageTitle style={{ marginTop: 14 }}>{mode === 'login' ? t('auth.titleLogin') : t('auth.titleRegister')}</PageTitle>
      <Muted>{isPatient ? t('auth.subPatient') : t('auth.subFamily')}</Muted>

      {mode === 'register' && (
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <View style={{ flex: 1 }}><Field label={t('auth.firstName')} value={form.firstName} onChangeText={set('firstName')} autoCapitalize="words" /></View>
          <View style={{ flex: 1 }}><Field label={t('auth.lastName')} value={form.lastName} onChangeText={set('lastName')} autoCapitalize="words" /></View>
        </View>
      )}
      <Field label={t('auth.email')} value={form.email} onChangeText={set('email')} keyboardType="email-address" />
      <Field label={t('auth.password')} value={form.password} onChangeText={set('password')} secureTextEntry />
      {mode === 'register' && <Field label={t('auth.phone')} value={form.phone} onChangeText={set('phone')} keyboardType="phone-pad" />}

      {error && <T size={8.5} w={700} color={c.urgentText} style={{ marginTop: 10 }}>{error}</T>}

      <Button style={{ marginTop: 16 }} onPress={busy ? undefined : submit}>
        {busy ? <ActivityIndicator color="#fff" /> : mode === 'login' ? t('auth.login') : t('auth.register')}
      </Button>
      <Pressable onPress={() => { setError(null); setMode(m => (m === 'login' ? 'register' : 'login')); }} style={{ marginTop: 14, alignSelf: 'center' }}>
        <T size={10} w={700} style={{ textDecorationLine: 'underline' }}>{mode === 'login' ? t('auth.toRegister') : t('auth.toLogin')}</T>
      </Pressable>
      <Pressable onPress={() => { haptic(); continueAsDemo(); }} style={{ marginTop: 12, alignSelf: 'center', padding: 6 }}>
        <T size={9} color={c.muted} style={{ textDecorationLine: 'underline' }}>{t('auth.demo')}</T>
      </Pressable>

      <Card radius={15} style={{ marginTop: 20, padding: 10 }}>
        <T size={6.5} w={800} spacing={0.8} style={{ marginBottom: 6 }}>{t('auth.server')}</T>
        <TextInput value={server} onChangeText={setServer} autoCapitalize="none" autoCorrect={false} keyboardType="url"
          style={{ height: 40, borderWidth: 1, borderColor: c.ink, borderRadius: 10, paddingHorizontal: 10, color: c.text, fontFamily: fonts[600], fontSize: 12, backgroundColor: c.bg }} />
      </Card>
    </Screen>
  );
}
