"""
screen的替代方案，方便批量部署与运行服务器
"""
import os.path
import subprocess
import time
import atexit

progress_dict = {}


@atexit.register
def server_console_exit():
    print("exiting... ")

    for progress_to_exit in progress_dict.values():
        progress_to_exit.terminate()

    should_wait = True
    while should_wait:
        should_exit = True
        for progress_to_exit in progress_dict.values():
            if progress_to_exit.poll() is None:
                should_exit = False
            if should_exit:
                should_wait = False
    print("goodbye.")


if __name__ == '__main__':
    server_path = os.path.join(r'D:\TestArea')
    java_path = os.path.join(server_path, r"PythonSubprogressTest.jar")

    for test_code in range(5):
        progress = subprocess.Popen(fr"java -jar {java_path} {test_code}", stdout=subprocess.PIPE)
        progress_dict[test_code] = progress

    print(progress_dict)

    while True:
        for line in iter(progress_dict[3].stdout.readline, b''):
            print(line)
        time.sleep(1)
