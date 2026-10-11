import React from 'react';
import { View } from 'react-native';
import { useTheme } from '../theme/ThemeContext';
import { Icon } from './Icon';
import { T } from './T';

/** .brand — logo mark + "SurgiGuard AI" */
export function Brand({ family }: { family?: boolean }) {
  const { c } = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
      <View style={{ width: 31, height: 31, borderRadius: 10, borderWidth: 1.5, borderColor: c.ink, backgroundColor: family ? c.lavender : c.primary, alignItems: 'center', justifyContent: 'center' }}>
        <Icon name={family ? 'profile' : 'activity'} size={19} color={family ? c.text : '#fff'} />
      </View>
      <T size={18} w={700}>SurgiGuard <T size={18} w={700} color={c.primary}>AI</T></T>
      {family && (
        <View style={{ marginLeft: 2, paddingHorizontal: 7, paddingVertical: 3, borderWidth: 1, borderColor: c.ink, borderRadius: 99, backgroundColor: c.surface }}>
          <T size={7} w={800} spacing={0.8}>FAMILY</T>
        </View>
      )}
    </View>
  );
}
