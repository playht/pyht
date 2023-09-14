import os
import subprocess


def run_make():
    # only run if Makefile exists
    if not os.path.exists("Makefile"):
        return
    try:
        subprocess.run(["make", "all"], check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'make all': {e}")
        print(e.output)
        exit(1)


if __name__ == "__main__":
    run_make()
