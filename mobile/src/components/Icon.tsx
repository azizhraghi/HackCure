import React from 'react';
import Svg, { Circle, Path, Rect } from 'react-native-svg';
import { useTheme } from '../theme/ThemeContext';

// Same stroke icon set as the Figma prototype (App.tsx `paths`), plus a few for the new screens.
export type IconName =
  | 'arrow' | 'bell' | 'search' | 'camera' | 'upload' | 'image' | 'file' | 'check'
  | 'home' | 'checkin' | 'twin' | 'report' | 'profile' | 'close' | 'phone' | 'message'
  | 'thermo' | 'drop' | 'activity' | 'rotate' | 'scan' | 'sensor'
  | 'pill' | 'sparkle' | 'calendar' | 'globe' | 'moon' | 'gear' | 'send' | 'shield' | 'plus' | 'chevron' | 'heart';

function paths(name: IconName) {
  switch (name) {
    case 'arrow': return <Path d="m15 18-6-6 6-6" />;
    case 'chevron': return <Path d="m9 18 6-6-6-6" />;
    case 'bell': return <><Path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><Path d="M10 21h4" /></>;
    case 'search': return <><Circle cx="11" cy="11" r="7" /><Path d="m20 20-4-4" /></>;
    case 'camera': return <><Path d="M4 7h3l2-3h6l2 3h3v12H4z" /><Circle cx="12" cy="13" r="4" /></>;
    case 'upload': return <><Path d="M12 16V4m-5 5 5-5 5 5" /><Path d="M5 16v4h14v-4" /></>;
    case 'image': return <><Rect x="3" y="4" width="18" height="16" rx="2" /><Circle cx="9" cy="10" r="2" /><Path d="m3 17 5-5 4 4 3-3 6 6" /></>;
    case 'file': return <><Path d="M6 2h8l4 4v16H6z" /><Path d="M14 2v5h5M9 12h6M9 16h6" /></>;
    case 'check': return <Path d="m5 12 4 4L19 6" />;
    case 'home': return <><Path d="m3 11 9-8 9 8" /><Path d="M5 10v10h14V10M9 20v-6h6v6" /></>;
    case 'checkin': return <><Circle cx="12" cy="12" r="9" /><Path d="m8 12 3 3 5-6" /></>;
    case 'twin': return <><Circle cx="12" cy="5" r="3" /><Path d="M8 22v-6l-2-4 3-3h6l3 3-2 4v6M9 10l3 5 3-5" /></>;
    case 'report': return <><Path d="M5 20V10M12 20V4M19 20v-7" /><Path d="M3 20h18" /></>;
    case 'profile': return <><Circle cx="12" cy="8" r="4" /><Path d="M4 21a8 8 0 0 1 16 0" /></>;
    case 'close': return <Path d="m7 7 10 10M17 7 7 17" />;
    case 'phone': return <Path d="M7 3h3l2 5-2 2a15 15 0 0 0 4 4l2-2 5 2v3c0 2-2 4-4 4A14 14 0 0 1 3 7c0-2 2-4 4-4Z" />;
    case 'message': return <Path d="M4 4h16v13H8l-4 4z" />;
    case 'thermo': return <><Path d="M10 14.8V5a2 2 0 1 1 4 0v9.8a4 4 0 1 1-4 0Z" /><Path d="M12 9v8" /></>;
    case 'drop': return <Path d="M12 2s7 8 7 13a7 7 0 0 1-14 0c0-5 7-13 7-13Z" />;
    case 'activity': return <Path d="M2 12h4l2-7 4 14 3-10 2 3h5" />;
    case 'rotate': return <><Path d="M20 7a9 9 0 0 0-15-2L3 7" /><Path d="M3 3v4h4M4 17a9 9 0 0 0 15 2l2-2" /><Path d="M21 21v-4h-4" /></>;
    case 'scan': return <><Path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5" /><Circle cx="12" cy="12" r="4" /></>;
    case 'sensor': return <><Circle cx="12" cy="12" r="2" /><Path d="M7.8 7.8a6 6 0 0 0 0 8.4M16.2 7.8a6 6 0 0 1 0 8.4M4.9 4.9a10 10 0 0 0 0 14.2M19.1 4.9a10 10 0 0 1 0 14.2" /></>;
    case 'pill': return <><Rect x="2.5" y="8" width="19" height="8" rx="4" transform="rotate(-35 12 12)" /><Path d="m9.5 8.4 5 7.2" /></>;
    case 'sparkle': return <Path d="M12 3c.6 4.2 2.8 6.4 7 7-4.2.6-6.4 2.8-7 7-.6-4.2-2.8-6.4-7-7 4.2-.6 6.4-2.8 7-7ZM19 16c.3 1.6 1 2.3 2.6 2.6-1.6.3-2.3 1-2.6 2.6-.3-1.6-1-2.3-2.6-2.6 1.6-.3 2.3-1 2.6-2.6Z" />;
    case 'calendar': return <><Rect x="3" y="5" width="18" height="16" rx="3" /><Path d="M3 10h18M8 3v4M16 3v4" /></>;
    case 'globe': return <><Circle cx="12" cy="12" r="9" /><Path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" /></>;
    case 'moon': return <Path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z" />;
    case 'gear': return <><Circle cx="12" cy="12" r="3" /><Path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1" /></>;
    case 'send': return <Path d="M3 11 21 3l-8 18-2-8-8-2Z" />;
    case 'shield': return <Path d="M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5l8-3Z" />;
    case 'plus': return <Path d="M12 5v14M5 12h14" />;
    case 'heart': return <Path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z" />;
  }
}

export function Icon({ name, size = 20, color, strokeWidth = 1.8 }: { name: IconName; size?: number; color?: string; strokeWidth?: number }) {
  const { c } = useTheme();
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color ?? c.text} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
      {paths(name)}
    </Svg>
  );
}
