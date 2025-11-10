import sys
from dev.tail_utils import append
txt=' '.join(sys.argv[1:]).strip() or 'count my monitors and save a short note'
append('user', txt)
print('injected')
