const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const core = html.split('/* BEGIN APPLICATION */')[1].split('/* DOM APPLICATION */')[0];
const api = vm.runInNewContext(core + '\n({newPattern, numbers, solvePattern, editDimension, setSameWidth, validatePattern, geometry, edgeDistances, renderScene, reportSVG, automaticComment})');
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
test('report always retains dimension annotations, escapes text, and includes grid by default', () => {
 const p=base();p.label='<Bourns & part>';const report=api.reportSVG({c:p,p:api.newPattern()},'Test <title>','Comment & details');
 assert.ok(report.includes('&lt;Bourns &amp; part&gt;'));assert.ok(report.includes('Not to physical scale'));assert.ok(report.includes('data-layer="grid"'));
 assert.ok(report.includes('data-label="W2"'));assert.ok(!api.reportSVG({c:p,p:api.newPattern()},'T','',false).includes('data-layer="grid"'));
});
test('automatic comment uses committed component identities and sensible fallbacks', () => {
 const patterns={c:base(),p:api.newPattern()};patterns.c.label='Bourns SRP';patterns.p.label='ETQP3M4R7KVN';
 assert.equal(api.automaticComment(patterns),'Panasonic ETQP3M4R7KVN solder terminals on Bourns SRP recommended land pattern.');
 patterns.c.label='';patterns.p.label='';
 assert.equal(api.automaticComment(patterns),'Panasonic solder terminals on the competitor recommended land pattern.');
});
test('long report comments wrap above the table without the old footer', () => {
 const report=api.reportSVG({c:base(),p:api.newPattern()},'A long document title '.repeat(4),'Long comment text '.repeat(15));
 const titleY=[...report.matchAll(/y="([^"]+)"[^>]*data-report-title="true"/g)].map(m=>Number(m[1]));
 const commentY=[...report.matchAll(/y="([^"]+)"[^>]*data-report-comment="true"/g)].map(m=>Number(m[1]));
 const tableY=Number(report.match(/data-report-table="true" x="40" y="([^"]+)"/)[1]);
 assert.ok(commentY.length>1);assert.ok(Math.min(...commentY)>Math.max(...titleY));assert.ok(Math.max(...commentY)<tableY);
 assert.ok(!report.includes('COMMENT'));assert.ok(!report.includes('Competitor: land pattern (red)'));
});
const terminal = () => api.newPattern({L:'3',P1:'3.5',P2:'6.5',W1:'1.5',W2:'1.5'});
test('equal distances use D on both sides and remain opt-in', () => {
 const patterns={c:base(),p:terminal()},d=api.edgeDistances(patterns);
 assert.ok(Math.abs(d.left-.4)<1e-8);assert.ok(Math.abs(d.right-.4)<1e-8);assert.equal(d.equal,true);
 assert.ok(!api.renderScene(patterns,900,600).markup.includes('data-layer="distances"'));
 const scene=api.renderScene(patterns,900,600,{distances:true}).markup;
 assert.equal((scene.match(/data-distance-label="D"/g)||[]).length,2);
 assert.ok(scene.includes('left P1 to P1 distance 0.40 mm'));assert.ok(scene.includes('right P1 to P1 distance 0.40 mm'));
});
test('asymmetric distances use actual inner edges and separate labels', () => {
 const c=api.newPattern({L:'2',P1:'3',P2:'8',W1:'2',W2:'3'}),p=terminal();
 const d=api.edgeDistances({c,p});assert.equal(d.left,-.25);assert.equal(d.right,.75);assert.equal(d.equal,false);
 const scene=api.renderScene({c,p},900,600,{distances:true}).markup;
 assert.ok(scene.includes('data-distance-label="DL"'));assert.ok(scene.includes('data-distance-label="DR"'));
});
test('P1 distances ignore outer span changes that preserve the inner edges', () => {
 const patterns={c:base(),p:terminal()};
 patterns.p.values.P2='5.5';patterns.p.values.W1='1';patterns.p.values.W2='1';
 const d=api.edgeDistances(patterns);assert.equal(d.leftText,'0.40');assert.equal(d.rightText,'0.40');
 const scene=api.renderScene(patterns,900,600,{distances:true});
 for(const [side,innerEdges] of [['left',[-1.75,-1.35]],['right',[1.35,1.75]]]){
   const group=scene.markup.split('data-distance-side="'+side+'"')[1].split('</g>')[0];
   const extensions=[...group.matchAll(/<line x1="([^"]+)"[^>]*data-extension="true"/g)];
   innerEdges.forEach((x,i)=>assert.ok(Math.abs(Number(extensions[i][1])-(450+x*scene.scale))<1e-8));
 }
});
test('signed and zero distances are retained without false zero arrowheads', () => {
 const p=api.newPattern({L:'2',P1:'1',P2:'2',W1:'.5',W2:'.5'});
 const c=api.newPattern({L:'2',P1:'4',P2:'6',W1:'1',W2:'1'});
 assert.equal(api.edgeDistances({c,p}).leftText,'-1.50');assert.equal(api.edgeDistances({c,p}).rightText,'-1.50');
 c.values.P1='1';c.values.P2='3';
 const scene=api.renderScene({c,p},900,600,{distances:true}).markup.split('<g data-layer="distances">')[1];
 assert.ok(scene.includes('distance 0.00 mm'));assert.ok(!scene.includes('<path'));
 c.values.W1='0.999';c.values.W2='1.001';
 const d=api.edgeDistances({c,p});assert.equal(d.leftText,'0.00');assert.equal(d.rightText,'0.00');assert.equal(d.equal,true);
});
test('distance visibility is independent of component dimensions and requires valid patterns', () => {
 const patterns={c:base(),p:terminal()};
 const scene=api.renderScene(patterns,900,600,{dimensions:false,distances:true}).markup;
 assert.ok(scene.includes('data-layer="distances"'));assert.ok(!scene.includes('data-label="L"'));
 patterns.p.values.L='';assert.equal(api.edgeDistances(patterns),null);
 assert.ok(!api.renderScene(patterns,900,600,{distances:true}).markup.includes('data-layer="distances"'));
});
test('overlapping distance intervals are staggered', () => {
 const c=api.newPattern({L:'2',P1:'0',P2:'8',W1:'7',W2:'1'});
 const p=api.newPattern({L:'2',P1:'1',P2:'2',W1:'.5',W2:'.5'});
 assert.equal(api.edgeDistances({c,p}).overlap,true);
 const scene=api.renderScene({c,p},900,600,{distances:true}).markup;
 const ys=[...scene.matchAll(/<text x="[^"]+" y="([^"]+)"[^>]*data-distance-label=/g)].map(m=>Number(m[1]));
 assert.equal(ys[1]-ys[0],40);
});
test('L labels face the terminals and export distances only appear inside the drawing', () => {
 const patterns={c:base(),p:terminal()},scene=api.renderScene(patterns,900,600).markup;
 assert.match(scene,/data-label="L" transform="rotate\(-90 /);assert.match(scene,/data-label="L" transform="rotate\(90 /);
 const off=api.reportSVG(patterns,'Title','Comment'),on=api.reportSVG(patterns,'Title','Comment',true,true);
 assert.ok(!off.includes('data-distance-label'));
 const drawingStart=on.indexOf('<svg x="40"');assert.ok(drawingStart>0);
 assert.ok(!on.slice(0,drawingStart).includes('data-distance-label'));assert.ok(on.slice(drawingStart).includes('data-distance-label'));
 assert.equal(off.slice(0,off.indexOf('<svg x="40"')),on.slice(0,drawingStart));
});
console.log(`${checks} checks passed.`);
