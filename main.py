import json
import re
from bs4 import BeautifulSoup

# Load HTML from file
with open("data.html", "r", encoding="utf-8") as file:
    html = file.read()

# Parse HTML using BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

# Find all product items
products = soup.find_all("div", class_="ProductList-item")

# List to store fragrance data
fragrances = []

# Loop through each product and extract data
for product in products:
    # Extract URL
    link_tag = product.find("a", class_="ProductList-item-link")
    url = link_tag["href"] if link_tag else "N/A"

    # Check if "Sold Out" div exists (if not present, it's in stock)
    sold_out_div = product.find("div", class_="sold-out")
    is_in_stock = False if sold_out_div else True

    # Extract fragrance name and clean it
    name_tag = product.find("h1", class_="ProductList-title")
    full_name = name_tag.text if name_tag else "N/A"

    # Remove newlines and extra spaces
    full_name = re.sub(r"\s+", " ", full_name).strip()

    # Split name using regex
    match = re.match(r"(.+?)\s+INSPIRED BY\s+(.+)", full_name, re.IGNORECASE)
    if match:
        name, clone_of = match.groups()
    else:
        name, clone_of = full_name, "Unknown"

    # Extract price
    price_tag = product.find("div", class_="product-price")
    price = price_tag.text if price_tag else "N/A"

    # Remove newlines and extra spaces from price
    price = re.sub(r"\s+", " ", price).strip()

    # Append data to list
    fragrances.append({
        "name": name,
        "clone_of": clone_of,
        "url": url,
        "is_in_stock": is_in_stock,
        "price": price
    })

# Save to JSON file
with open("fragrances.json", "w", encoding="utf-8") as json_file:
    json.dump(fragrances, json_file, indent=4, ensure_ascii=False)

print("Data has been saved to fragrances.json")
