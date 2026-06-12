"""Auto-migration: Fix order_index + section_name for Reading lessons R-01..R-32"""
import sqlite3, os, sys

ORDER_MAP = {
    "R-01": (1, "reading_cw_theory"),  "R-02": (2, "reading_cw_theory"),  "R-03": (3, "reading_cw_theory"),
    "R-04": (4, "reading_cw"),  "R-05": (5, "reading_cw"),  "R-06": (6, "reading_cw"),
    "R-07": (7, "reading_cw"),  "R-08": (8, "reading_cw"),  "R-09": (9, "reading_cw"),
    "R-10": (10, "reading_cw"), "R-11": (11, "reading_cw"), "R-12": (12, "reading_cw"),
    "R-13": (13, "reading_dl_theory"),
    "R-14": (14, "reading_dl"), "R-15": (15, "reading_dl"), "R-16": (16, "reading_dl"),
    "R-17": (17, "reading_dl"), "R-18": (18, "reading_dl"), "R-19": (19, "reading_dl"),
    "R-20": (20, "reading_dl"), "R-21": (21, "reading_dl"), "R-22": (22, "reading_dl"), "R-23": (23, "reading_dl"),
    "R-24": (24, "reading_ar_theory"),
    "R-25": (25, "reading_ar"), "R-26": (26, "reading_ar"), "R-27": (27, "reading_ar"), "R-28": (28, "reading_ar"),
    "R-29": (29, "reading_ar"), "R-30": (30, "reading_ar"), "R-31": (31, "reading_ar"), "R-32": (32, "reading_ar"),
}

def run(db_path=None):
    db_path = db_path or os.environ.get("DB_PATH") or "academy.db"
    if not os.path.exists(db_path):
        print(f"[fix_order] DB not found: {db_path}")
        return
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    updated = 0
    for code, (oi, sect) in ORDER_MAP.items():
        cur.execute("UPDATE lessons SET order_index=?, order_num=?, section_name=? WHERE lesson_code=?",
                    (float(oi), oi, sect, code))
        if cur.rowcount > 0:
            updated += 1
    con.commit()
    con.close()
    print(f"[fix_order] Reading R-01..R-32: updated={updated}")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
