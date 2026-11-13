"""Welcome to PyStudio!
Click Run (F5) to execute this Python script in an isolated subprocess.
"""

import math
import platform


def fibonacci(count: int) -> list[int]:
    sequence = [0, 1]
    while len(sequence) < count:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence[:count]


def main() -> None:
    print("PyStudio Execution Engine Ready")
    print(f"Python Runtime: {platform.python_version()} ({platform.system()})")
    numbers = fibonacci(10)
    print(f"First 10 Fibonacci numbers: {numbers}")
    print(f"Golden ratio approximation: {numbers[-1] / numbers[-2]:.6f}")
    print(f"Pi constant: {math.pi:.5f}")


if __name__ == "__main__":
    main()
