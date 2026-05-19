import sqlite3
import random
from datetime import datetime, timedelta

DB_NAME = "ecommerce.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# ====================== SCHEMA ======================
cursor.executescript("""
    DROP TABLE IF EXISTS customers;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS order_items;
    DROP TABLE IF EXISTS reviews;

    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        city TEXT,
        country TEXT,
        signup_date TEXT
    );

    CREATE TABLE products (
        product_id INTEGER PRIMARY KEY,
        name TEXT,
        category TEXT,
        price REAL,
        stock INTEGER
    );

    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date TEXT,
        total_amount REAL,
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE order_items (
        item_id INTEGER PRIMARY KEY,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price_at_purchase REAL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );

    CREATE TABLE reviews (
        review_id INTEGER PRIMARY KEY,
        product_id INTEGER,
        customer_id INTEGER,
        rating INTEGER,
        comment TEXT,
        review_date TEXT,
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
""")

# ====================== SAMPLE DATA ======================
# Customers
customers = [
    (1, "Emma Thompson", "emma.t@email.com", "London", "UK", "2024-01-15"),
    (2, "Liam Chen", "liam.chen@email.com", "Manchester", "UK", "2024-03-22"),
    (3, "Olivia Patel", "olivia.p@email.com", "Birmingham", "UK", "2025-01-10"),
    (4, "Noah Garcia", "noah.g@email.com", "Edinburgh", "UK", "2024-11-05"),
    (5, "Ava Khan", "ava.k@email.com", "Glasgow", "UK", "2025-02-18"),
]
cursor.executemany("INSERT OR IGNORE INTO customers VALUES (?, ?, ?, ?, ?, ?)", customers)

# Products
products = [
    (1, "Wireless Headphones", "Electronics", 89.99, 150),
    (2, "Stainless Steel Water Bottle", "Home & Kitchen", 24.99, 300),
    (3, "Yoga Mat Premium", "Sports", 49.99, 80),
    (4, "Organic Coffee Beans", "Food & Drink", 15.99, 200),
    (5, "Smart Watch Series 8", "Electronics", 299.99, 45),
    (6, "Leather Laptop Bag", "Fashion", 79.99, 120),
    (7, "Mechanical Keyboard", "Electronics", 129.99, 65),
]
cursor.executemany("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?)", products)

# Orders + Order Items + Reviews (random but realistic)
random.seed(42)
for order_id in range(1, 51):
    customer_id = random.randint(1, 5)
    order_date = (datetime(2025, 1, 1) + timedelta(days=random.randint(0, 110))).strftime("%Y-%m-%d")
    num_items = random.randint(1, 5)
    total = 0.0

    cursor.execute("INSERT INTO orders (order_id, customer_id, order_date, total_amount, status) VALUES (?, ?, ?, ?, ?)",
                   (order_id, customer_id, order_date, 0.0, "Completed"))

    for _ in range(num_items):
        product_id = random.randint(1, 7)
        quantity = random.randint(1, 4)
        price = [89.99, 24.99, 49.99, 15.99, 299.99, 79.99, 129.99][product_id-1]
        line_total = quantity * price
        total += line_total
        cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) VALUES (?, ?, ?, ?)",
                       (order_id, product_id, quantity, price))

    cursor.execute("UPDATE orders SET total_amount = ? WHERE order_id = ?", (round(total, 2), order_id))

    # Random reviews
    if random.random() > 0.4:
        cursor.execute("INSERT INTO reviews (product_id, customer_id, rating, comment, review_date) VALUES (?, ?, ?, ?, ?)",
                       (random.randint(1,7), customer_id, random.randint(4,5), "Great product!", order_date))

print("✅ Populated with realistic sample data (50 orders, multiple categories)")

conn.commit()
conn.close()

print(f"\n🎉 Database created: {DB_NAME}")
print("You now have two databases in the folder:")
print("   • student_grades.db (university)")
print("   • ecommerce.db (sales / customers / products)")
print("\nYour agent can now intelligently switch between them using 'query_any_database'!")