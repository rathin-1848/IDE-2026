"""Runtime Error & Traceback Demo
Run this script to inspect PyStudio's Runtime Errors panel and line jump.
"""


def calculate_average(values: list[float]) -> float:
    return sum(values) / len(values)


def main() -> None:
    scores = [92, 85, 78]
    print(f"Valid average: {calculate_average(scores):.2f}")

    empty_scores: list[float] = []
    print("Now triggering ZeroDivisionError...")
    print(calculate_average(empty_scores))


if __name__ == "__main__":
    main()
