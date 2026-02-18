try:
    from uvloop import run  # type: ignore[unresolved-import]
except ImportError:
    from asyncio import run

from instancer.core.consumer import consume


def main() -> None:
    run(consume())


if __name__ == '__main__':
    main()
