const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({document:{querySelector:()=>null}});
vm.runInContext(fs.readFileSync('site.js','utf8'),context);
const evaluate = code => vm.runInContext(code,context);
for (const input of ['""','"  "','null','undefined','"NaN"']) {
  assert.equal(evaluate(`formatNumber(${input})`),'N/A');
}
assert.equal(evaluate('formatNumber("0")'),'0.000');
assert.equal(evaluate('compactDate("20241112")'),'2024-11-12');
assert.match(evaluate('interpretation(1.001)'),/not evidence of statistical significance/);
assert.match(evaluate('interpretation("")'),/did not have enough/);
assert.equal(evaluate('parseCsv("a,b\\n1,\\\"hello, world\\\"\\n")[0].b'),'hello, world');
console.log('Website numeric, date, interpretation and CSV checks passed.');
