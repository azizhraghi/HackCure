/**
 * SurgiGuard AI — patient & caregiver mobile app
 * Smarter Recovery. Safer Care.
 *
 * @format
 */

import React from 'react';
import { StatusBar, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { ThemeToggle } from './src/components/ThemeToggle';
import './src/i18n';
import { AppStateProvider, useAppState } from './src/context/AppState';
import { RootNavigator } from './src/navigation/RootNavigator';
import { ThemeProvider, useTheme } from './src/theme/ThemeContext';

function Root() {
  const { c, isDark } = useTheme();
  const { ready } = useAppState();
  return (
    <>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      <SafeAreaView edges={['top']} style={{flex:1, backgroundColor:c.bg}}>
        <ThemeToggle />
        {ready ? <RootNavigator /> : <View style={{ flex: 1, backgroundColor: c.bg }} />}
      </SafeAreaView>
    </>
  );
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider>
          <AppStateProvider>
            <Root />
          </AppStateProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
