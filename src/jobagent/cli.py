"""Command-line entry point used to verify the project installation."""

BOOTSTRAP_MESSAGE = "JOBAGENT project bootstrap is ready."


def main() -> None:
    """Print a deterministic message that confirms the package is installed."""
    print(BOOTSTRAP_MESSAGE)


if __name__ == "__main__":
    main()
