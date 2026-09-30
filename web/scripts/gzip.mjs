// Comprime ogni file di ../firmware/data in .gz e cancella l'originale (ESPAsyncWebServer serve la .gz).
import { readdirSync, readFileSync, writeFileSync, unlinkSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync, constants } from 'node:zlib';

const dir = new URL('../../firmware/data/', import.meta.url).pathname;
let total = 0, stl = 0;
const walk = (d) => readdirSync(d).forEach((f) => {
  const p = join(d, f);
  if (statSync(p).isDirectory()) return walk(p);
  if (!f.endsWith('.gz')) {
    writeFileSync(p + '.gz', gzipSync(readFileSync(p), { level: constants.Z_BEST_COMPRESSION }));
    unlinkSync(p);
  }
  const s = statSync(p.endsWith('.gz') ? p : p + '.gz').size;
  total += s;
  if (/\.stl\.gz$/i.test(p)) stl += s;
  console.log(`${(s / 1024).toFixed(1).padStart(8)} KB  ${p.slice(dir.length)}${p.endsWith('.gz') ? '' : '.gz'}`);
});
walk(dir);
console.log(`totale data/: ${(total / 1024).toFixed(1)} KB (STL: ${(stl / 1024).toFixed(1)} KB, senza STL: ${((total - stl) / 1024).toFixed(1)} KB)`);
if (total - stl > 1.8 * 1024 * 1024) { console.error('ERRORE: data/ senza STL supera 1.8 MB'); process.exit(1); }
