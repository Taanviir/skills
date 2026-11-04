# ledgerline

<!-- Fictional project written for the project-presentation evals. -->

ledgerline reconciles a small business's bank export against its invoice spreadsheet and lists every payment that does not match an invoice. It is a command-line tool for bookkeepers who do this by hand every month.

## Features

- Reads CSV exports from four banks (Northbank, Harbor Credit, Fieldstone and Meridian) and invoice sheets as CSV or XLSX.
- Matches payments to invoices by amount, date within 5 days, and a fuzzy match on the payer name.
- Writes a report of unmatched payments and unpaid invoices as CSV and as a one-page HTML summary.

On a test month of 1,240 payments, ledgerline matched 1,198 automatically. A bookkeeper took 25 minutes to clear the other 42, down from about 6 hours by hand.

## Status

Version 0.9. Used monthly by three bookkeeping firms since August 2025.
Not yet built: multi-currency invoices and a Xero import.

## Usage

```sh
pip install -e .
ledgerline match bank.csv invoices.xlsx --out report/
```
