// Fictional demo data (HackCure prototype). Measurements are SIMULATED.
// Translatable text lives in src/i18n; this file holds names, numbers and ids.

export const patient = {
  name: 'Sarah Miller',
  first: 'Sarah',
  initials: 'SM',
  day: 6,
  totalDays: 42,
  score: 87,
  inviteCode: '482916',
};

export const caregiver = { name: 'Ahmed Khan', first: 'Ahmed', initials: 'AK' };
export const surgeon = { name: 'Dr. Elena Ruiz', initials: 'ER' };

export const familyMembers = [
  { name: 'Ahmed Khan', initials: 'AK', relation: 'partner', badge: 'caregiver', tone: 'blue' },
  { name: 'Emma Lee', initials: 'EL', relation: 'sister', badge: 'family', tone: 'pink' },
  { name: 'David Miller', initials: 'DM', relation: 'father', badge: 'viewOnly', tone: 'yellow' },
] as const;

export const metrics = {
  woundTemp: 36.9,
  pain: 3,
  sleep: '8.5h',
  heartRate: 72,
  dressingTemp: 37.8,
  moisture: 42,
};

export type DoseState = 'pending' | 'taken' | 'skipped';
export const medications = [
  { id: 'm1', name: 'meds.m1', purpose: 'meds.m1p', times: ['08:00', '14:00', '20:00'], slot: 'morning', tone: 'pink' },
  { id: 'm4', name: 'meds.m4', purpose: 'meds.m4p', times: ['20:00'], slot: 'evening', tone: 'lavender' },
  { id: 'm2', name: 'meds.m2', purpose: 'meds.m2p', times: ['09:00'], slot: 'morning', tone: 'yellow' },
  { id: 'm3', name: 'meds.m3', purpose: 'meds.m3p', times: ['08:00'], slot: 'morning', tone: 'sky' },
] as const;

/** Simple 7-day series for the trends (simulated) */
export const series = {
  temp: [36.6, 36.8, 36.7, 36.9, 37.0, 36.9, 36.9],
  hr: [84, 80, 78, 75, 74, 73, 72],
  steps: [320, 610, 980, 1240, 1610, 1890, 2150],
};
