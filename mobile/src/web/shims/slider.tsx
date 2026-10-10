import React, { createElement } from 'react';
import { View, type ViewStyle } from 'react-native';

type Props = {
  minimumValue?: number; maximumValue?: number; step?: number; value?: number;
  onValueChange?: (value: number) => void; style?: ViewStyle;
};

export default function Slider({ minimumValue = 0, maximumValue = 1, step = 0.01, value = minimumValue, onValueChange, style }: Props) {
  return <View style={[{ justifyContent: 'center', minHeight: 28 }, style]}>{createElement('input', {
    type: 'range', min: minimumValue, max: maximumValue, step, value,
    onChange: (event: React.ChangeEvent<HTMLInputElement>) => onValueChange?.(Number(event.target.value)),
    style: { width: '100%', accentColor: '#2089e8', cursor: 'pointer' },
  })}</View>;
}
