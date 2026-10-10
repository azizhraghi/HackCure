import React from 'react';
import { Pressable, View } from 'react-native';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Icon, type IconName } from '../components/Icon';
import { T } from '../components/T';
import { haptic } from '../components/ui';
import { useTheme } from '../theme/ThemeContext';

/** .bottom-nav from the prototype — active tab gets a blue bordered circle */
export function BottomNav({ state, navigation, descriptors, icons }: BottomTabBarProps & { icons: Record<string, IconName> }) {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-around', alignItems: 'flex-start', paddingTop: 8, paddingBottom: Math.max(insets.bottom, 10), borderTopWidth: 1, borderTopColor: c.navLine, backgroundColor: c.navBg }}>
      {state.routes.map((route, index) => {
        const active = state.index === index;
        const label = descriptors[route.key].options.title ?? route.name;
        return (
          <Pressable key={route.key} accessibilityRole="tab" accessibilityState={{ selected: active }}
            onPress={() => {
              const e = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
              if (!active && !e.defaultPrevented) { haptic('selection'); navigation.navigate(route.name); }
            }}
            style={{ flex: 1, alignItems: 'center', gap: 2 }}>
            <View style={{ width: 34, height: 34, borderRadius: 17, alignItems: 'center', justifyContent: 'center', backgroundColor: active ? c.primary : 'transparent', borderWidth: active ? 1.2 : 0, borderColor: c.ink }}>
              <Icon name={icons[route.name]} size={19} color={active ? '#fff' : c.faint} />
            </View>
            <T size={7} w={active ? 800 : 500} color={active ? c.text : c.faint}>{label}</T>
          </Pressable>
        );
      })}
    </View>
  );
}
