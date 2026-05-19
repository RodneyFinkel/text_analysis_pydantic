import sqlite3
import random
import numpy as np
from datetime import datetime, timedelta

DB_NAME = "stocks.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# ====================== SCHEMA ======================
cursor.executescript("""
    DROP TABLE IF EXISTS companies;
    DROP TABLE IF EXISTS stock_prices;
    DROP TABLE IF EXISTS financials;
    DROP TABLE IF EXISTS analyst_ratings;

    CREATE TABLE companies (
        ticker TEXT PRIMARY KEY,
        company_name TEXT,
        sector TEXT,
        industry TEXT,
        market_cap REAL,
        employees INTEGER,
        founded_year INTEGER
    );

    CREATE TABLE stock_prices (
        price_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT,
        date TEXT,
        open_price REAL,
        high_price REAL,
        low_price REAL,
        close_price REAL,
        volume INTEGER,
        FOREIGN KEY (ticker) REFERENCES companies(ticker)
    );

    CREATE TABLE financials (
        financial_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT,
        quarter TEXT,                    -- e.g., "2025-Q1"
        revenue REAL,
        net_income REAL,
        eps REAL,
        pe_ratio REAL,
        debt_to_equity REAL,
        FOREIGN KEY (ticker) REFERENCES companies(ticker)
    );

    CREATE TABLE analyst_ratings (
        rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT,
        analyst TEXT,
        rating TEXT,                     -- Buy, Hold, Sell
        target_price REAL,
        date TEXT,
        FOREIGN KEY (ticker) REFERENCES companies(ticker)
    );
""")

print("✅ Schema created for stocks.db\n")

# ====================== SAMPLE COMPANIES ======================
companies = [
    ("AAPL", "Apple Inc.", "Technology", "Consumer Electronics", 3200000000000, 164000, 1976),
    ("MSFT", "Microsoft Corporation", "Technology", "Software", 3100000000000, 228000, 1975),
    ("GOOGL", "Alphabet Inc.", "Technology", "Internet Services", 2100000000000, 182000, 1998),
    ("AMZN", "Amazon.com, Inc.", "Consumer Cyclical", "E-commerce", 1950000000000, 1520000, 1994),
    ("NVDA", "NVIDIA Corporation", "Technology", "Semiconductors", 2800000000000, 29600, 1993),
    ("TSLA", "Tesla, Inc.", "Consumer Cyclical", "Automotive", 980000000000, 140000, 2003),
    ("JPM", "JPMorgan Chase & Co.", "Financial Services", "Banking", 620000000000, 310000, 1799),
    ("V", "Visa Inc.", "Financial Services", "Payments", 580000000000, 28500, 1958),
]

cursor.executemany("INSERT OR IGNORE INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)", companies)

# ====================== STOCK PRICES (Daily data - ~120 days) ======================
print("Generating daily stock price data...")

tickers = [c[0] for c in companies]
start_date = datetime(2025, 1, 1)

for ticker in tickers:
    base_price = random.uniform(80, 450)
    price = base_price
    
    for i in range(120):  # ~4 months of data
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        
        # Simulate realistic price movement
        change = np.random.normal(0.001, 0.015)
        price = price * (1 + change)
        
        open_p = round(price * random.uniform(0.98, 1.02), 2)
        high_p = round(max(open_p, price) * random.uniform(1.00, 1.03), 2)
        low_p = round(min(open_p, price) * random.uniform(0.97, 1.00), 2)
        close_p = round(price, 2)
        volume = random.randint(8000000, 120000000)
        
        cursor.execute("""
            INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticker, date, open_p, high_p, low_p, close_p, volume))

print(f"✅ Generated ~960 stock price records (120 days × 8 companies)")

# ====================== QUARTERLY FINANCIALS ======================
quarters = ["2024-Q4", "2025-Q1", "2025-Q2"]
for ticker in tickers:
    for q in quarters:
        revenue = random.uniform(8000, 95000) * 1000000
        net_income = revenue * random.uniform(0.12, 0.35)
        eps = round(net_income / random.randint(800000000, 16000000000), 2)
        pe = round(random.uniform(18, 65), 1)
        dte = round(random.uniform(0.3, 1.8), 2)
        
        cursor.execute("""
            INSERT INTO financials (ticker, quarter, revenue, net_income, eps, pe_ratio, debt_to_equity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticker, q, round(revenue, 2), round(net_income, 2), eps, pe, dte))

# ====================== ANALYST RATINGS ======================
ratings = ["Buy", "Strong Buy", "Hold", "Sell"]
analysts = ["Goldman Sachs", "Morgan Stanley", "JPMorgan", "Citigroup", "Barclays", "UBS"]

for ticker in tickers:
    for i in range(random.randint(3, 6)):
        rating = random.choice(ratings)
        target = random.uniform(80, 550)
        date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 100))).strftime("%Y-%m-%d")
        
        cursor.execute("""
            INSERT INTO analyst_ratings (ticker, analyst, rating, target_price, date)
            VALUES (?, ?, ?, ?, ?)
        """, (ticker, random.choice(analysts), rating, round(target, 2), date))

conn.commit()
conn.close()

print(f"\n🎉 Financial Database created: {DB_NAME}")
print("This database contains:")
print("   • 8 major companies (AAPL, MSFT, NVDA, TSLA, etc.)")
print("   • ~960 daily stock price records")
print("   • Quarterly financials (revenue, EPS, etc.)")
print("   • Analyst ratings and target prices")
print("\nNow you have **three** interesting databases:")
print("   1. student_grades.db     → Education")
print("   2. ecommerce.db          → Sales / Customers")
print("   3. stocks.db             → Financial Markets")