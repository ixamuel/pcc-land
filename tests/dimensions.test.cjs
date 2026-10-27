const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const core = html.split('/* BEGIN APPLICATION */')[1].split('/* DOM APPLICATION */')[0];
const api = vm.runInNewContext(core + '\n({newPattern, numbers, solvePattern, editDimension, setSameWidth, validatePattern, geometry, renderScene, reportSVG})');
let checks = 0;
function test(name, fn) { fn(); checks++; console.log('PASS ' + name); }
const base = () => api.newPattern({L:'3.4',P1:'2.7',P2:'8.4',W1:'2.85',W2:'2.85'});
test('manual editing preserves unrelated values', () => {
 const p=base();p.mode='manual';p.sameWidth=false;api.editDimension(p,'P2','9');
 assert.equal(p.values.P1,'2.7');assert.equal(p.values.W1,'2.85');assert.equal(api.validatePattern(p).ready,false);
});
test('auto resolves gap and hands off when the gap is edited', () => {
 const p=base();api.solvePattern(p);assert.equal(p.solved,'P1');api.editDimension(p,'P1','3.00');
 assert.equal(p.values.P1,'3.00');assert.equal(p.values.P2,'8.70');assert.equal(api.validatePattern(p).ready,true);
});
test('linked widths follow either input, including in manual mode', () => {
 const p=base();p.mode='manual';api.editDimension(p,'W2','1.23');assert.equal(p.values.W1,'1.23');assert.equal(p.values.P2,'8.4');
});
test('independent widths never imply symmetry', () => {
 const p=api.newPattern({L:'2',P1:'3',P2:'8'});p.sameWidth=false;api.solvePattern(p);
 assert.equal(p.values.W1,'');assert.equal(p.values.W2,'');api.editDimension(p,'W1','2');assert.equal(p.values.W2,'3.00');
});
test('explicit width linking enables symmetric solving', () => {
 const p=api.newPattern({L:'2',P1:'3',P2:'8'});api.solvePattern(p);assert.equal(p.values.W1,'2.50');assert.equal(p.values.W2,'2.50');
});
test('derived linked widths stay derived when the span changes', () => {
 const p=api.newPattern({L:'2',P1:'3',P2:'8'});api.solvePattern(p);api.editDimension(p,'P2','10');
 assert.equal(p.values.P1,'3');assert.equal(p.values.W1,'3.50');assert.equal(p.values.W2,'3.50');
});
test('enabling linked widths uses the most recently edited width', () => {
 const p=base();p.sameWidth=false;api.editDimension(p,'W2','1.3');api.setSameWidth(p,true);assert.equal(p.values.W1,'1.3');assert.equal(p.values.W2,'1.3');
});
test('empty edit is not replaced and negative gaps are not drawn', () => {
 const p=base();api.solvePattern(p);api.editDimension(p,'P1','');assert.equal(p.values.P1,'');
 api.editDimension(p,'P2','1');assert.equal(api.validatePattern(p).ready,false);assert.equal(api.validatePattern(p).error,true);
});
test('zero gap is valid; zero height and nonfinite values are invalid', () => {
 const p=api.newPattern({L:'2',P1:'0',P2:'4',W1:'2',W2:'2'});assert.equal(api.validatePattern(p).ready,true);
 p.values.L='0';assert.equal(api.validatePattern(p).ready,false);p.values.L='Infinity';assert.equal(api.validatePattern(p).ready,false);
});
test('unequal pad geometry shares the outer span centre', () => {
 const g=api.geometry({L:2,P1:3,P2:8,W1:2,W2:3});assert.equal(g.left,-4);assert.equal(g.right,4);assert.equal(g.innerLeft,-2);assert.equal(g.innerRight,1);assert.equal(g.innerRight-g.innerLeft,3);
});
test('rendering uses a single scale and includes every dimension', () => {
 const p=base();const result=api.renderScene({c:p,p:api.newPattern()},1000,700);
 const pad=result.markup.match(/data-pad="true"[^>]*width="([^"]+)" height="([^"]+)"/);
 assert.ok(Math.abs(Number(pad[1])/2.85-Number(pad[2])/3.4)<1e-8);
 for(const key of ['L','P1','P2','W1','W2'])assert.ok(result.markup.includes('data-label="'+key+'"'));
 assert.ok(result.markup.includes('stroke-width="0.55"'));assert.ok(result.markup.includes('X (mm)'));
});
test('report always retains dimension annotations, escapes text, and omits grid by default', () => {
 const p=base();p.label='<Bourns & part>';const report=api.reportSVG({c:p,p:api.newPattern()},'Test <title>','Comment & details');
 assert.ok(report.includes('&lt;Bourns &amp; part&gt;'));assert.ok(report.includes('Not to physical scale'));assert.ok(!report.includes('data-layer="grid"'));
 assert.ok(report.includes('data-label="W2"'));assert.ok(api.reportSVG({c:p,p:api.newPattern()},'T','',true).includes('data-layer="grid"'));
});
console.log(`${checks} checks passed.`);
