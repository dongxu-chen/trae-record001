#!/usr/bin/env python3
import os
from log_archiver import LogArchiver

os.makedirs('logs', exist_ok=True)
os.makedirs('archive', exist_ok=True)

with open('logs/app-2026-05-06.log', 'w') as f:
    f.write('Log content for 10 days ago\n')

with open('logs/app-2026-05-08.log', 'w') as f:
    f.write('Log content for 8 days ago\n')

with open('logs/app-2026-05-16.log', 'w') as f:
    f.write('Log content for today\n')

print('Test files created. Now running archiver...')
print('=' * 50)

archiver = LogArchiver('logs', 'archive', 7)
archiver.run()

print('=' * 50)
print('\nLogs directory contents:')
for f in os.listdir('logs'):
    print(f'  - {f}')

print('\nArchive directory contents:')
for f in os.listdir('archive'):
    print(f'  - {f}')
