// Lists t('...') strings used in src/ that have no Arabic entry in src/i18n.ts. Usage: node scripts/check-i18n.mjs
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : [p] })
const files = walk('src').filter((f) => /\.(tsx?)$/.test(f) && !/i18n\.ts$|mock\.ts$|DevDrawer/.test(f))
const dict = readFileSync('src/i18n.ts', 'utf8')
const used = new Set()
const re = /\bt\(\s*(['"])((?:\\.|(?!\1).)*)\1/g
for (const f of files) { const s = readFileSync(f, 'utf8'); for (const m of s.matchAll(re)) used.add(m[2].replace(/\\'/g, "'")) }
const missing = [...used].filter((k) => !dict.includes(JSON.stringify(k)) && !dict.includes(`'${k.replace(/'/g, "\\'")}'`) && !dict.includes(`"${k}"`) && !dict.includes('`' + k + '`'))
console.log(`${used.size} strings used, ${missing.length} missing Arabic`)
missing.forEach((k) => console.log(' -', k))
process.exit(missing.length ? 1 : 0)
