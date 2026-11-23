/* Run the exact browser Python distribution in Node, without automating a UI.
 * npm install --prefix /tmp/gong-pyodide --cache /tmp/gong-npm-cache pyodide@0.27.7 --no-audit --no-fund
 * node inventory_site/tools/check_pyodide.mjs /tmp/gong-pyodide/node_modules/pyodide/pyodide.mjs
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
process.on('uncaughtException', error => {console.error(String(error.message||error));process.exit(1);});
process.on('unhandledRejection', error => {console.error(String(error.message||error));process.exit(1);});
const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
if (!process.argv[2]) throw new Error('Pass the installed pyodide.mjs path.');
const {loadPyodide} = await import(pathToFileURL(path.resolve(process.argv[2])));
const py = await loadPyodide({indexURL:path.dirname(path.resolve(process.argv[2]))+path.sep});
await py.loadPackage('numpy');
py.FS.mkdirTree('/lab');
for (const name of await fs.readdir(path.join(site,'dist/assets/python'))) {
  if (name.endsWith('.py')) py.FS.writeFile('/lab/'+name, await fs.readFile(path.join(site,'dist/assets/python',name),'utf8'));
}
py.runPython("import sys\nsys.path.insert(0,'/lab')\nimport lab_api, stress_api");
const call = request => {
  py.globals.set('_request',JSON.stringify(request));
  return JSON.parse(py.runPython("stress_api.handle_json(_request) if __import__('json').loads(_request).get('op','').startswith('stress_') else lab_api.handle_json(_request)"));
};
const results = {};
for (const kind of ['hql','meta','fql','mimic']) {
  let s = call({op:'reset',kind});
  while (!s.finished) {
    s = call({op:'step',action:kind==='hql'||kind==='meta'?Math.max(10,s.manual_opening):[2,2]});
  }
  const q = call({op:'q',phase:1,action:0});
  if (!call({op:'export'}).csv.startsWith('\ufeff')) throw new Error('CSV encoding');
  results[kind] = {days:s.day,human_cost:s.sum_human,algorithm_cost:s.sum_algorithm,q_trace:Boolean(q.new_q!==undefined||q.available_actions)};
}
const stressResults={};
for (const kind of ['hql','meta','fql','mimic']) {
  let s=call({op:'stress_reset',config:{kind,scenario:'drift',seeds:2,cycles:2}});
  while(!s.finished)s=call({op:'stress_step'});
  if(s.failures.length||!s.summary.ci95)throw new Error('Stress invariants or CI');
  stressResults[kind]={steps:s.completed,summary:s.summary};
  if(!call({op:'stress_export'}).csv.startsWith('\ufeff'))throw new Error('Stress CSV');
}
console.log(JSON.stringify({status:'passed',scope:'Pyodide in Node; not browser UI QA',python:py.runPython('sys.version.split()[0]'),numpy:py.runPython('lab_api.np.__version__'),models:results,stress:stressResults},null,2));
