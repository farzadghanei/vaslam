import sys
from os import EX_OK, EX_TEMPFAIL
from logging import (
    INFO,
    DEBUG,
    ERROR,
    getLogger,
    Formatter,
    StreamHandler,
    NullHandler,
    FileHandler,
)
from argparse import ArgumentParser
from vaslam.conf import default_conf
from vaslam.diag import diagnose_network, issue_message
from vaslam import __summary__, __version__


logger = getLogger("vaslam")


def parse_args(args=None):
    parser = ArgumentParser(prog="vaslam", description=__summary__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__)
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="no output, just exit code"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="log debug information"
    )
    parser.add_argument("-l", "--log", help="log to file")
    return parser.parse_args(args)


def _diag_prog(total: int, step: int) -> None:
    pct = int(step * 100.0 / total)
    dots = "." * int(pct / 20)
    print(
        "\r\bdiagnosing Internet connection {:d}/{:d} {:d}% {}".format(
            step, total, pct, dots
        ),
        end="",
    )
    sys.stdout.flush()
    if step == total:
        print("")  # print new line


def main(args=None) -> int:
    opts = parse_args(args)
    logger.setLevel(DEBUG)  # level is set per handler
    log_level = DEBUG if opts.debug else INFO
    out_handler = NullHandler() if opts.quiet else StreamHandler(sys.stdout)
    out_handler.setLevel(ERROR)  # details are logged, not printed
    out_handler.setFormatter(Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(out_handler)
    if opts.log:
        file_handler = FileHandler(opts.log)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
    observer = None if opts.quiet else _diag_prog
    conf = default_conf()
    result = diagnose_network(conf, observer)
    issues = result.get_issues()
    if issues:
        for issue in issues:
            print(issue_message(issue) or "Unknown issue")
        return EX_TEMPFAIL
    return EX_OK


if __name__ == "__main__":
    sys.exit(main())
