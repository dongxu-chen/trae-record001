import sys
sys.path.insert(0, '.')

print("Starting test...")

import os
os.makedirs('logs', exist_ok=True)
os.makedirs('archive', exist_ok=True)

with open('logs/app-2026-05-06.log', 'w') as f:
    f.write('Log content for 10 days ago\n')

with open('logs/app-2026-05-08.log', 'w') as f:
    f.write('Log content for 8 days ago\n')

with open('logs/app-2026-05-16.log', 'w') as f:
    f.write('Log content for today\n')

print("Test files created in logs/")
print("Files in logs/:", os.listdir('logs'))

from log_archiver import LogArchiver
archiver = LogArchiver('logs', 'archive', 7)
print("\nRunning archiver...")
archiver.run()

print("\nFiles in logs/ after archiving:", os.listdir('logs'))
print("Files in archive/:", os.listdir('archive'))
print("\nTest complete!")
