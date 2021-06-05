"""Write image.

This module contains some trickery enabling a restart with sudo.
"""

import os
import pathlib
import subprocess
import sys

# The super user has a different environment. The following code adds the
# calling user's local site packages path. This is necessary if the package
# was installed with the --user argument.
path = pathlib.Path(__file__)
module_path = str(path.parents[1])
if not module_path in sys.path:
    sys.path.insert(0, module_path)

# The following must be imported after the corrected sys.path
from tqdm.auto import tqdm

def write(src, dest, become=False):
    if become:
        subprocess.run(['sudo', sys.executable, __file__, 
            pathlib.Path(src).absolute(), pathlib.Path(dest).absolute()])
    else:
        with open(src, 'rb') as fin, tqdm.wrapattr(open(dest, 'wb'), 'write',
            unit='B', unit_scale=True, unit_divisor=1024, miniters=1,
            desc="Writing image", total=pathlib.Path(src).stat().st_size
            ) as fout:
            chunk = fin.read(1024*1024)
            while chunk:
                fout.write(chunk)
                fout.flush()
                os.fsync(fout.fileno())
                chunk = fin.read(1024*1024)
        os.sync()

if __name__ == '__main__':
    write(sys.argv[1], sys.argv[2])
