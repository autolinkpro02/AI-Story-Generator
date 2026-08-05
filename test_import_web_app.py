import importlib, sys
sys.path.insert(0, 'D:/New folder (3)')
app = importlib.import_module('web_app')
print('web_app import ok, app attr:', hasattr(app, 'app'))
