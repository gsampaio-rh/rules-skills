"""Nightly sales summary pipeline.

Seed code for a harness eval scenario. Reads data/orders.csv, sums revenue
per region, writes output/summary.csv. Runs fine until it hits real-world
data — one malformed row in the seed CSV crashes the whole run.
"""
import csv

INPUT_PATH = "data/orders.csv"
OUTPUT_PATH = "output/summary.csv"


def load_orders(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def summarize(orders):
    totals = {}
    for order in orders:
        region = order["region"]
        # No error handling: a non-numeric quantity blows up the whole run.
        revenue = int(order["quantity"]) * float(order["unit_price"])
        totals[region] = totals.get(region, 0) + revenue
    return totals


def write_summary(totals, path):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["region", "total_revenue"])
        for region, total in totals.items():
            writer.writerow([region, round(total, 2)])


def main():
    print("Loading orders...")
    orders = load_orders(INPUT_PATH)
    print(f"Loaded {len(orders)} orders")

    totals = summarize(orders)

    print("Writing summary...")
    write_summary(totals, OUTPUT_PATH)
    print("Done.")


if __name__ == "__main__":
    main()
