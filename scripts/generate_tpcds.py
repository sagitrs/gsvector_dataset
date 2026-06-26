#!/usr/bin/env python3
"""Generate TPC-DS schema data with deterministic random values (seed=42).

Usage: python3 generate_tpcds.py --scale 0.1 --out-dir /tmp/tpcds_data
"""
import argparse, csv, os, random, sys

random.seed(42)

SCHEMAS = {
    "store_sales": [
        ("ss_sold_date_sk", "int"), ("ss_sold_time_sk", "int"),
        ("ss_item_sk", "int"), ("ss_customer_sk", "int"),
        ("ss_cdemo_sk", "int"), ("ss_hdemo_sk", "int"),
        ("ss_addr_sk", "int"), ("ss_store_sk", "int"),
        ("ss_promo_sk", "int"), ("ss_ticket_number", "int"),
        ("ss_quantity", "int"), ("ss_wholesale_cost", "decimal"),
        ("ss_list_price", "decimal"), ("ss_sales_price", "decimal"),
        ("ss_ext_discount_amt", "decimal"), ("ss_ext_sales_price", "decimal"),
        ("ss_ext_wholesale_cost", "decimal"), ("ss_ext_list_price", "decimal"),
        ("ss_ext_tax", "decimal"), ("ss_coupon_amt", "decimal"),
        ("ss_net_paid", "decimal"), ("ss_net_paid_inc_tax", "decimal"),
        ("ss_net_profit", "decimal"),
    ],
    "date_dim": [
        ("d_date_sk", "int"), ("d_date_id", "text"), ("d_date", "text"),
        ("d_month_seq", "int"), ("d_week_seq", "int"),
        ("d_quarter_seq", "int"), ("d_year", "int"), ("d_dow", "int"),
        ("d_moy", "int"), ("d_dom", "int"), ("d_qoy", "int"),
        ("d_fy_year", "int"), ("d_fy_quarter_seq", "int"),
        ("d_fy_week_seq", "int"), ("d_day_name", "text"),
        ("d_quarter_name", "text"), ("d_holiday", "text"),
        ("d_weekend", "text"), ("d_following_holiday", "text"),
        ("d_first_dom", "int"), ("d_last_dom", "int"),
        ("d_same_day_ly", "int"), ("d_same_day_lq", "int"),
        ("d_current_day", "text"), ("d_current_week", "text"),
        ("d_current_month", "text"), ("d_current_quarter", "text"),
        ("d_current_year", "text"),
    ],
    "item": [
        ("i_item_sk", "int"), ("i_item_id", "text"),
        ("i_rec_start_date", "text"), ("i_rec_end_date", "text"),
        ("i_item_desc", "text"), ("i_current_price", "decimal"),
        ("i_wholesale_cost", "decimal"), ("i_brand_id", "int"),
        ("i_brand", "text"), ("i_class_id", "int"), ("i_class", "text"),
        ("i_category_id", "int"), ("i_category", "text"),
        ("i_manufact_id", "int"), ("i_manufact", "text"),
        ("i_size", "text"), ("i_formulation", "text"),
        ("i_color", "text"), ("i_units", "text"),
        ("i_container", "text"), ("i_manager_id", "int"),
        ("i_product_name", "text"),
    ],
    "customer": [
        ("c_customer_sk", "int"), ("c_customer_id", "text"),
        ("c_current_cdemo_sk", "int"), ("c_current_hdemo_sk", "int"),
        ("c_current_addr_sk", "int"), ("c_first_shipto_date_sk", "int"),
        ("c_first_sales_date_sk", "int"), ("c_salutation", "text"),
        ("c_first_name", "text"), ("c_last_name", "text"),
        ("c_preferred_cust_flag", "text"), ("c_birth_day", "int"),
        ("c_birth_month", "int"), ("c_birth_year", "int"),
        ("c_birth_country", "text"), ("c_login", "text"),
        ("c_email_address", "text"), ("c_last_review_date", "text"),
    ],
    "store": [
        ("s_store_sk", "int"), ("s_store_id", "text"),
        ("s_rec_start_date", "text"), ("s_rec_end_date", "text"),
        ("s_closed_date_sk", "int"), ("s_store_name", "text"),
        ("s_number_employees", "int"), ("s_floor_space", "int"),
        ("s_hours", "text"), ("s_manager", "text"),
        ("s_market_id", "int"), ("s_geography_class", "text"),
        ("s_market_desc", "text"), ("s_market_manager", "text"),
        ("s_division_id", "int"), ("s_division_name", "text"),
        ("s_company_id", "int"), ("s_company_name", "text"),
        ("s_street_number", "text"), ("s_street_name", "text"),
        ("s_street_type", "text"), ("s_suite_number", "text"),
        ("s_city", "text"), ("s_county", "text"), ("s_state", "text"),
        ("s_zip", "text"), ("s_country", "text"),
        ("s_gmt_offset", "decimal"), ("s_tax_percentage", "decimal"),
    ],
}

ROW_COUNTS = {
    0.1: {"store_sales": 288000, "date_dim": 2556, "item": 18000,
           "customer": 10000, "store": 12},
    1:   {"store_sales": 2880000, "date_dim": 73049, "item": 18000,
           "customer": 100000, "store": 12},
}


def gen_value(field_type):
    if field_type == "int":
        return str(random.randint(1, 100000))
    elif field_type == "decimal":
        return f"{random.uniform(0, 500):.2f}"
    elif field_type == "text":
        return f"val_{random.randint(1, 99999)}"
    return ""


def main():
    parser = argparse.ArgumentParser(description="Generate TPC-DS data")
    parser.add_argument("--scale", type=float, default=0.1)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--tables", nargs="*",
                        default=["store_sales", "date_dim", "item", "customer", "store"])
    args = parser.parse_args()

    counts = ROW_COUNTS.get(args.scale, ROW_COUNTS[1])
    os.makedirs(args.out_dir, exist_ok=True)

    for table in args.tables:
        cols = SCHEMAS[table]
        n = counts[table]
        path = os.path.join(args.out_dir, f"{table}.csv")
        print(f"  {table}: {n} rows → {path}")
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in cols])
            for _ in range(n):
                w.writerow([gen_value(c[1]) for c in cols])
            f.flush()
        size = os.path.getsize(path)
        print(f"    {size:,} bytes")


if __name__ == "__main__":
    main()
