from __future__ import annotations

import argparse

from backend.server import run


def main() -> None:
    parser = argparse.ArgumentParser(description="启动多媒体隐写网页原型。")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8032)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
