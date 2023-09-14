import subprocess


def run_make():
    try:
        subprocess.run(["make", "all"], check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing 'make all': {e}")
        print(e.output)
        exit(1)


if __name__ == "__main__":
    run_make()
