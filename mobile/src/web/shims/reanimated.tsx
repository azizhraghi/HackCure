import React, { useRef } from 'react';
import { Image, Text, View } from 'react-native';

type Entering = { delay: (ms: number) => Entering; duration: (ms: number) => Entering };
const entering: Entering = { delay: () => entering, duration: () => entering };
const Animated = {
  View, Text, Image,
  createAnimatedComponent: <T,>(component: T) => component,
};
const Easing = { linear: (value: number) => value, quad: (value: number) => value * value, out: (fn: (value: number) => number) => (value: number) => 1 - fn(1 - value) };
const FadeIn = entering, FadeInDown = entering, FadeInUp = entering, ZoomIn = entering, SlideInDown = entering;
function useSharedValue<T>(value: T) { return useRef({ value }).current; }
function useAnimatedStyle<T>(factory: () => T) { return factory(); }
function useAnimatedProps<T>(factory: () => T) { return factory(); }
const withTiming = <T,>(value: T) => value;
const withRepeat = <T,>(value: T) => value;

export { Easing, FadeIn, FadeInDown, FadeInUp, ZoomIn, SlideInDown, useSharedValue, useAnimatedStyle, useAnimatedProps, withRepeat, withTiming };
export default Animated;
