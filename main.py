import argparse

from ftp_client.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FTP client application.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="run with mock protocol and logger services for integration checks",
    )
    args = parser.parse_args()

    app = create_app(use_mocks=args.mock)
    app.run()


if __name__ == "__main__":
    main()
