import sys
print(sys.version)
print(sys.executable)
print('pip installed packages...')

import pkg_resources
print([p.project_name for p in pkg_resources.working_set])
