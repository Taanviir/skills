import argparse


def main():
    ap = argparse.ArgumentParser(prog="ledgerline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match")
    m.add_argument("bank")
    m.add_argument("invoices")
    m.add_argument("--out", default="report")
    ap.parse_args()
