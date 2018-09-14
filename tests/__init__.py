import sys
if sys.version_info[0] == 2: # only profile test on Python 2.7 (odd error locally with Python 3.7)
    pytest_plugins = ['pytest_profiling']

