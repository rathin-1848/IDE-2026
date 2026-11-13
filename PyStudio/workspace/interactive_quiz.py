"""Interactive Input Demo
Demonstrates PyStudio's interactive Terminal console for Python input().
"""


def main() -> None:
    print("=== PyStudio Interactive Console ===")
    name = input("Enter your name: ").strip() or "Developer"
    try:
        fav = int(input("Enter your favorite integer: "))
        print(f"\nHello, {name}! {fav} squared is {fav ** 2}.")
    except ValueError:
        print(f"\nHello, {name}! That wasn't a valid integer, try again next time.")


if __name__ == "__main__":
    main()
