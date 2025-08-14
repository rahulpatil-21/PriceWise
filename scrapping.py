from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re


def fetch_with_playwright(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(5000)
        html = page.content()
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        browser.close()
        return html


def parse_amazon(query):
    from bs4 import BeautifulSoup
    import re

    url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
    html = fetch_with_playwright(url)

    with open("amazon_debug.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("div.s-main-slot div[data-component-type='s-search-result']")
    if not product:
        return None

    title = product.select_one("h2 span").text.strip() if product.select_one("h2 span") else "N/A"
    price = product.select_one("span.a-offscreen").text.strip() if product.select_one("span.a-offscreen") else "N/A"
    image = product.select_one("img.s-image")["src"] if product.select_one("img.s-image") else "N/A"
    mrp_tag = product.select_one("span.a-text-price span.a-offscreen")
    mrp = mrp_tag.text.strip() if mrp_tag else "N/A"
    rating = product.select_one("span.a-icon-alt").text.strip() if product.select_one("span.a-icon-alt") else "N/A"
    link_tag = product.select_one("a.a-link-normal.s-no-outline")
    

    # Extract discount % via regex from product block text
    discount_match = re.search(r"\((\d+% off)\)", product.get_text())
    discount = discount_match.group(1) if discount_match else "N/A"

    return {
        "platform": "Amazon",
        "title": title,
        "price": price,
        "image_url": image,
        "mrp": mrp,
        "discount": discount,
        "rating": rating,
        "link": "https://www.amazon.in" + link_tag.get("href", "") if link_tag else "N/A"
    }



from bs4 import BeautifulSoup

def parse_flipkart(query):
    url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
    html = fetch_with_playwright(url)

    soup = BeautifulSoup(html, "html.parser")
    products = soup.select("a.CGtC98")

    query_keywords = query.lower().split()

    for product in products:
        title_tag = product.select_one("div.KzDlHZ, div.cPHDOP")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True).lower()
        if all(word in title for word in query_keywords):
            price = product.select_one("div.Nx9bqj, div._30jeq3")
            mrp = product.select_one("div.yRaY8j, div._3I9_wc")
            discount = product.select_one("div.UkUFwK span, div._3Ay6Sb span")
            image = product.select_one("img")
            rating = product.select_one("div.XQDdHH, div._3LWZlK")

            return {
                "platform": "Flipkart",
                "title": title_tag.text.strip(),
                "price": price.text.strip() if price else "N/A",
                "image_url": image["src"] if image else "N/A",
                "mrp": mrp.text.strip() if mrp else "N/A",
                "discount": discount.text.strip() if discount else "N/A",
                "rating": rating.text.strip() if rating else "N/A",
                "link": "https://www.flipkart.com" + product.get("href", "")
            }

    return None



def aggregate_basic(query):
    return [parse_amazon(query), parse_flipkart(query)]


# Example usage
if __name__ == "__main__":
    query = "redmi 14c 5g"
    results = aggregate_basic(query)

    for result in results:
        if result:
            print(f"\n=== {result['platform']} ===")
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            print("No result found.")
