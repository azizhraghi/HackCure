// Design tokens ported from the Figma Make prototype (SurgiGuard AI mobile app UI/src/index.css)

export const light = {
  bg: '#f9fbff',
  page: '#edf2fa',
  surface: '#ffffff',
  ink: '#1b2a4a', // borders + main text
  shadow: '#1b2a4a', // hard offset shadow under primary buttons
  title: '#111b31',
  text: '#1b2a4a',
  muted: '#64718a',
  faint: '#7d889c',
  primary: '#1e88e5',
  onPrimary: '#ffffff',
  blue: '#dcefff',
  sky: '#a9e3fa',
  task: '#72c9f2',
  green: '#bff3d9',
  pink: '#f4c7ea',
  yellow: '#fbe19b',
  lavender: '#cdbbf6',
  lilacBg: '#eee9ff',
  mint: '#e7f9ef',
  ice: '#eef9fe',
  iceBlue: '#e2f5fc',
  peach: '#fff0d6',
  amber: '#fff3cf',
  readonly: '#eef1f6',
  line: '#e1e5ed',
  lineSoft: '#d9e5ed',
  grey: '#e4e9f2',
  switchOff: '#dce1e9',
  track: '#5ED3A0',
  review: '#FFB347',
  urgent: '#FF6B6B',
  trackText: '#218d65',
  reviewText: '#a65f00',
  urgentText: '#c64e48',
  warnBorder: '#ef7168',
  warnBg: '#fff0ee',
  warnDot: '#ff8d81',
  navBg: 'rgba(255,255,255,0.97)',
  navLine: '#dde3ed',
  scrim: 'rgba(27,42,74,0.28)',
  glass: 'rgba(255,255,255,0.88)',
  quote: '#eef7ff',
  stageA: '#f9fdff',
  stageB: '#e4f2fb',
  stageC: '#e6def8',
};

export type Palette = typeof light;

export const dark: Palette = {
  bg: '#0e1628',
  page: '#0a1120',
  surface: '#16213a',
  ink: '#8fa3c9',
  shadow: '#03060d',
  title: '#f1f5ff',
  text: '#e6ecfa',
  muted: '#9aa8c2',
  faint: '#7f8daa',
  primary: '#2f93ea',
  onPrimary: '#ffffff',
  blue: '#1d3253',
  sky: '#1d4660',
  task: '#1b5b7c',
  green: '#1a4637',
  pink: '#4a2946',
  yellow: '#4f431f',
  lavender: '#372d5e',
  lilacBg: '#221d3d',
  mint: '#15302a',
  ice: '#13283a',
  iceBlue: '#163049',
  peach: '#3d2e17',
  amber: '#3a3218',
  readonly: '#1b2741',
  line: '#26324d',
  lineSoft: '#26324d',
  grey: '#22304d',
  switchOff: '#2a3754',
  track: '#5ED3A0',
  review: '#FFB347',
  urgent: '#FF6B6B',
  trackText: '#6fe0b0',
  reviewText: '#ffc070',
  urgentText: '#ff8a84',
  warnBorder: '#ef7168',
  warnBg: '#3a1c22',
  warnDot: '#ff8d81',
  navBg: 'rgba(14,22,40,0.97)',
  navLine: '#26324d',
  scrim: 'rgba(0,0,0,0.5)',
  glass: 'rgba(22,33,58,0.9)',
  quote: '#14263f',
  stageA: '#1a2a45',
  stageB: '#132238',
  stageC: '#211d3a',
};

export const fonts = {
  400: 'PlusJakartaSans-Regular',
  500: 'PlusJakartaSans-Medium',
  600: 'PlusJakartaSans-SemiBold',
  700: 'PlusJakartaSans-Bold',
  800: 'PlusJakartaSans-ExtraBold',
} as const;

export type Weight = keyof typeof fonts;

/**
 * The Figma frame uses tiny CSS sizes (5–9px) that are unreadable on a device.
 * Small sizes are lifted toward 11 while large sizes stay exact, so the
 * hierarchy of the design is preserved.
 */
export function fs(size: number): number {
  if (size >= 12) return size;
  return Math.round((size + (12 - size) * 0.42) * 10) / 10;
}

export const radius = { button: 15, card: 19, big: 22, pill: 99 };
export const BORDER = 1.5;
