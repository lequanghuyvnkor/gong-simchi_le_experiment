/* Python runs in a dedicated browser worker; the UI stays responsive. */
var pyodide = null;
var queue = Promise.resolve();
var files = ['model.py','hql.py','meta_hql.py','experiment.py','fql_model.py','fql.py','fql_experiment.py','mimic_ql.py','lab_api.py','stress_api.py'];
async function boot() {
  postMessage({type:'progress',message:'Đang tải Python…'});
  importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
  pyodide = await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'});
  postMessage({type:'progress',message:'Đang tải NumPy và mã mô hình…'});
  await pyodide.loadPackage('numpy');
  pyodide.FS.mkdirTree('/lab');
  await Promise.all(files.map(async function(name) {
    var response = await fetch('./assets/python/' + name);
    if (!response.ok) throw new Error('Không tải được mã mô hình: ' + name);
    pyodide.FS.writeFile('/lab/' + name, await response.text());
  }));
  pyodide.runPython("import sys\nsys.path.insert(0,'/lab')\nimport lab_api, stress_api");
  postMessage({type:'ready',version:pyodide.runPython("sys.version.split()[0]")});
}
var initialized = boot().catch(function(error){postMessage({type:'fatal',message:String(error.message||error)});throw error;});
self.onmessage = function(event) {
  var message = event.data;
  queue = queue.then(async function() {
    try {
      await initialized;
      pyodide.globals.set('_lab_request', JSON.stringify(message.payload));
      var raw = pyodide.runPython("stress_api.handle_json(_lab_request) if __import__('json').loads(_lab_request).get('op','').startswith('stress_') else lab_api.handle_json(_lab_request)");
      postMessage({type:'result',id:message.id,result:JSON.parse(raw)});
    } catch (error) {
      var text = String(error.message||error).split('\n');
      postMessage({type:'error',id:message.id,message:text[text.length-1]||'Không thực hiện được thao tác.'});
    }
  });
};
