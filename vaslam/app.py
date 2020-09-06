import sys
from os import EX_OK, EX_TEMPFAIL
from argparse import ArgumentParser
from vaslam.conf import default_conf
from vaslam.diag import diagnose_network, issue_message
from vaslam import __summary__, __version__


def parse_args(args=None):
    parser = ArgumentParser(prog="vaslam", description=__summary__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s {}".format(__version__)
    )
    return parser.parse_args(args)


def main(args=None) -> int:
    opts = parse_args(args)
    conf = default_conf()
    result = diagnose_network(conf)
    issues = result.get_issues()
    if issues:
        for issue in issues:
            print(issue_message(issue) or 'Unknown issue')
        return EX_TEMPFAIL
    return EX_OK


if __name__ == "__main__":
    sys.exit(main())
