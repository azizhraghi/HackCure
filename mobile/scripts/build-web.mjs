import { build } from 'esbuild';
import { cp, mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const out = path.join(root, 'dist-web');
const shim = (name) => path.join(root, 'src', 'web', 'shims', name);

await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
await cp(path.join(root, 'web', 'index.html'), path.join(out, 'index.html'));
await cp(path.join(root, 'web', 'theme.js'), path.join(out, 'theme.js'));

await build({
  absWorkingDir: root,
  entryPoints: ['src/web.tsx'],
  outfile: path.join(out, 'app.js'),
  bundle: true,
  minify: false,
  sourcemap: true,
  platform: 'browser',
  format: 'iife',
  target: ['es2022'],
  jsx: 'automatic',
  resolveExtensions: ['.web.tsx', '.web.ts', '.web.jsx', '.web.js', '.tsx', '.ts', '.jsx', '.js', '.json'],
  mainFields: ['browser', 'module', 'main'],
  conditions: ['browser', 'default'],
  loader: { '.png': 'dataurl', '.jpg': 'dataurl', '.jpeg': 'dataurl', '.webp': 'dataurl' },
  define: { 'process.env.NODE_ENV': '"development"', __DEV__: 'true' },
  alias: {
    'react-native': 'react-native-web',
    'react-native-reanimated': shim('reanimated.tsx'),
    'react-native-haptic-feedback': shim('haptics.ts'),
    'react-native-localize': shim('localize.ts'),
    '@react-native-async-storage/async-storage': shim('asyncStorage.ts'),
    '@react-native-community/blur': shim('blur.tsx'),
    '@react-native-community/slider': shim('slider.tsx'),
    'react-native-linear-gradient': shim('linearGradient.tsx'),
    '@react-native/assets-registry/registry': shim('assetRegistry.ts'),
  },
  logLevel: 'info',
});

console.log(`Browser app built to ${path.relative(root, out)}`);
