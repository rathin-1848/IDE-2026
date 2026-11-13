"""Infinite Loop & Stop Button Demo
Run this file, watch live streaming output, and click Stop (Shift+F5)
to safely terminate the child Python process without freezing PyStudio.
"""

import time


def main() -> None:
    tick = 1
    print("Starting continuous counter. Click Stop to terminate safely.")
    while True:
        print(f"Heartbeat tick #{tick}")
        tick += 1
        time.sleep(0.8)


if __name__ == "__main__":
    main()
