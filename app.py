from __future__ import annotations

import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "store.db"
CSS_PATH = BASE_DIR / "static" / "style.css"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        cursor = connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                price REAL NOT NULL,
                rating REAL NOT NULL,
                learners INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            );

            CREATE TABLE IF NOT EXISTS user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )

        if cursor.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO categories (name, icon) VALUES (?, ?)",
                [
                    ("Data Science", "📊"),
                    ("Programming", "💻"),
                    ("Cloud & DevOps", "☁️"),
                    ("Business", "📈"),
                    ("Design", "🎨"),
                ],
            )

        if cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            cursor.executemany(
                """
                INSERT INTO products
                    (title, description, category_id, price, rating, learners, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "Machine Learning Pro Bootcamp",
                        "Build production-grade recommendation engines with Python and SQL.",
                        1,
                        1499,
                        4.8,
                        15320,
                        "https://images.unsplash.com/photo-1526379095098-d400fd0bf935?auto=format&fit=crop&w=800&q=80",
                    ),
                    (
                        "Full-Stack Python Commerce",
                        "Create scalable e-commerce apps with backend APIs and SQL design.",
                        2,
                        1299,
                        4.7,
                        10450,
                        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=800&q=80",
                    ),
                    (
                        "SQL Analytics Mastery",
                        "Hands-on SQL projects for customer behavior and business insights.",
                        1,
                        999,
                        4.9,
                        18700,
                        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?auto=format&fit=crop&w=800&q=80",
                    ),
                    (
                        "AWS for Education Platforms",
                        "Deploy modern learning applications with robust cloud infrastructure.",
                        3,
                        1399,
                        4.6,
                        7820,
                        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=800&q=80",
                    ),
                    (
                        "Product Strategy for E-Commerce",
                        "Improve retention and conversion through personalization strategy.",
                        4,
                        1199,
                        4.5,
                        6320,
                        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80",
                    ),
                    (
                        "UI/UX for Learning Marketplaces",
                        "Design clean interfaces inspired by Flipkart and Amazon style layouts.",
                        5,
                        899,
                        4.7,
                        9210,
                        "https://images.unsplash.com/photo-1558655146-9f40138edfeb?auto=format&fit=crop&w=800&q=80",
                    ),
                ],
            )

        if cursor.execute("SELECT COUNT(*) FROM user_events").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO user_events (user_name, product_id, event_type, score) VALUES (?, ?, ?, ?)",
                [
                    ("Aarav", 1, "enroll", 5),
                    ("Aarav", 3, "wishlist", 4),
                    ("Mira", 2, "enroll", 5),
                    ("Mira", 6, "view", 3),
                    ("Riya", 3, "enroll", 5),
                    ("Riya", 1, "view", 4),
                    ("Karan", 4, "enroll", 5),
                    ("Karan", 2, "view", 4),
                ],
            )

        connection.commit()


def query_categories() -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute("SELECT * FROM categories ORDER BY name").fetchall()


def query_products(category: str | None) -> list[sqlite3.Row]:
    sql = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON c.id = p.category_id
    """
    params: tuple[str, ...] = ()
    if category:
        sql += " WHERE c.name = ?"
        params = (category,)
    sql += " ORDER BY p.rating DESC, p.learners DESC"

    with get_connection() as connection:
        return connection.execute(sql, params).fetchall()


def query_recommendations() -> list[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT p.title, c.name AS category_name,
                   ROUND(AVG(ue.score), 2) AS recommendation_score,
                   COUNT(ue.id) AS interactions,
                   p.price
            FROM products p
            JOIN categories c ON c.id = p.category_id
            LEFT JOIN user_events ue ON ue.product_id = p.id
            GROUP BY p.id
            ORDER BY recommendation_score DESC, interactions DESC, p.rating DESC
            LIMIT 4
            """
        ).fetchall()


def render_home(category: str | None) -> str:
    categories = query_categories()
    products = query_products(category)
    recommendations = query_recommendations()

    category_html = "".join(
        f'<a class="category-card" href="/?category={c["name"]}#courses"><span class="icon">{c["icon"]}</span><span>{c["name"]}</span></a>'
        for c in categories
    )

    product_html = "".join(
        f"""
        <article class=\"product-card\">
          <img src=\"{p['image_url']}\" alt=\"{p['title']}\">
          <div class=\"content\">
            <span class=\"chip\">{p['category_name']}</span>
            <h3>{p['title']}</h3>
            <p>{p['description']}</p>
            <div class=\"meta\"><span>⭐ {p['rating']}</span><span>{p['learners']} learners</span></div>
            <div class=\"bottom-row\"><strong>₹ {int(p['price'])}</strong><button>Enroll Now</button></div>
          </div>
        </article>
        """
        for p in products
    ) or "<p>No courses found for this category.</p>"

    recommendation_html = "".join(
        f"<tr><td>{r['title']}</td><td>{r['category_name']}</td><td>{r['recommendation_score'] or 0}</td><td>{r['interactions']}</td><td>₹ {int(r['price'])}</td></tr>"
        for r in recommendations
    )

    selected_label = (
        f"Showing results for <strong>{category}</strong>." if category else "Curated by quality, ratings, and learner engagement."
    )

    return f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>EduCart Pro</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap\" rel=\"stylesheet\">
  <link rel=\"stylesheet\" href=\"/static/style.css\">
</head>
<body>
<header class=\"top-nav\">
  <div class=\"brand\">EduCart<span>Pro</span></div>
  <form class=\"search-bar\" action=\"/\" method=\"get\">
    <input type=\"text\" name=\"category\" placeholder=\"Search by category\" value=\"{category or ''}\">
    <button type=\"submit\">Search</button>
  </form>
  <nav class=\"menu\"><a href=\"#categories\">Categories</a><a href=\"#courses\">Courses</a><a href=\"#recommendations\">Recommended</a></nav>
</header>
<main>
  <section class=\"hero\">
    <div>
      <p class=\"eyebrow\">Professional Educational Marketplace</p>
      <h1>AI-Powered Learning & Commerce Platform</h1>
      <p class=\"subtitle\">Inspired by Flipkart/Amazon interfaces with educational e-commerce structure powered by Python and SQL.</p>
      <div class=\"hero-actions\"><a href=\"#courses\" class=\"btn primary\">Explore Courses</a><a href=\"#recommendations\" class=\"btn secondary\">View Recommendations</a></div>
    </div>
    <div class=\"hero-card\">
      <h3>Project Spotlight</h3>
      <table>
        <tr><th>Title</th><td>Product Recommendation System for E-Commerce</td></tr>
        <tr><th>Task</th><td>Build recommendation system based on customer behavior</td></tr>
        <tr><th>Parameters</th><td>Analyze purchase history and ratings data</td></tr>
        <tr><th>Methods</th><td>Collaborative Filtering, Content-Based Filtering</td></tr>
      </table>
    </div>
  </section>
  <section id=\"categories\" class=\"section\"><div class=\"section-head\"><h2>Top Categories</h2><p>Browse popular educational domains.</p></div><div class=\"category-grid\">{category_html}</div></section>
  <section id=\"courses\" class=\"section\"><div class=\"section-head\"><h2>Featured Courses</h2><p>{selected_label}</p></div><div class=\"product-grid\">{product_html}</div></section>
  <section id=\"recommendations\" class=\"section\">
    <div class=\"section-head\"><h2>Recommendation Engine Output</h2><p>SQL-calculated ranking from user interactions.</p></div>
    <div class=\"recommendation-panel\">
      <table><thead><tr><th>Course</th><th>Category</th><th>Score</th><th>Interactions</th><th>Price</th></tr></thead><tbody>{recommendation_html}</tbody></table>
    </div>
  </section>
</main>
<footer class=\"footer\"><p>© 2026 EduCart Pro • Built with HTML, CSS, Python & SQL</p></footer>
</body>
</html>
    """


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/static/style.css":
            self.serve_css()
            return

        if parsed.path == "/":
            params = parse_qs(parsed.query)
            category = params.get("category", [None])[0]
            html = render_home(category)
            encoded = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        self.send_response(404)
        self.end_headers()

    def serve_css(self) -> None:
        css = CSS_PATH.read_text(encoding="utf-8").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(css)))
        self.end_headers()
        self.wfile.write(css)


def run() -> None:
    init_db()
    server = HTTPServer(("0.0.0.0", 5000), AppHandler)
    print("Server running on http://localhost:5000")
    server.serve_forever()


if __name__ == "__main__":
    run()
