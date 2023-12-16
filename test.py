import sys
#https://docs.python.org/3/library/subprocess.html
#https://stackoverflow.com/questions/15899798/subprocess-popen-in-different-console
#https://stackoverflow.com/questions/1196074/start-a-background-process-in-python
#https://www.reddit.com/r/learnpython/comments/sl7bsn/how_do_you_keep_a_subprocess_running_after_the/


import subprocess
DETACHED_PROCESS = 0x00000008
pid = subprocess.Popen([sys.executable, "test2.py"],creationflags=subprocess.CREATE_NEW_CONSOLE|subprocess.CREATE_NEW_PROCESS_GROUP).pid