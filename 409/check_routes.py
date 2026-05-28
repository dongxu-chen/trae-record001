import sys
sys.path.insert(0, '.')
from web import create_app

app = create_app()
print('App created successfully')
print('\nAvailable routes:')
for rule in app.url_map.iter_rules():
    methods = ', '.join(sorted(rule.methods - {'OPTIONS', 'HEAD'}))
    print(f'  {rule.rule:40s} [{methods}]')
