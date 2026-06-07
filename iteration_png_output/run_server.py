from __future__ import annotations

import argparse

from backend.server import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PNG-output image steganography prototype.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
