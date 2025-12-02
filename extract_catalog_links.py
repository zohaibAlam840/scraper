# import requests
# from bs4 import BeautifulSoup
# import csv
# import os
# import time

# # Function to extract product details
# def extract_product_details(product_url):
#     try:
#         print(f"Fetching details for: {product_url}")
#         response = requests.get(product_url, timeout=10)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.content, 'html.parser')

#         # Extract catalog links
#         catalog_links = []
#         link_tags = soup.select('td a[target="_blank"]')
#         for link_tag in link_tags:
#             catalog_links.append(link_tag['href'])

#         # Extract product image URL
#         image_tag = soup.find('a', {'rel': 'gallery'})
#         image_url = image_tag['href'] if image_tag else None
#         print(f"Image URL: {image_url}")
#         print(f"Catalog Links: {catalog_links}")

#         return catalog_links, image_url
#     except requests.RequestException as e:
#         print(f"Error fetching {product_url}: {e}")
#         return [], None

# # CSV file paths
# input_csv = 'motorcycle sh pricelist.csv'
# output_csv = 'motorcycle_sh_pricelist_with_details.csv'

# # Check if input CSV exists
# if not os.path.exists(input_csv):
#     print(f"Error: The file '{input_csv}' does not exist in the directory.")
#     exit(1)

# # Read the input CSV file and extract details
# with open(input_csv, newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile, delimiter=';')
#     fieldnames = reader.fieldnames + ['catalog_links', 'image_url']
#     print(f"Fieldnames in CSV: {fieldnames}")  # Print out field names for debugging
#     rows = []

#     for row in reader:
#         product_id = row['PRODUCT']
#         print(f"Processing product ID: {product_id}")  # Debug: Check which product is being processed
#         product_url = f'https://www.motorcyclestorehouse.com/product/{product_id}'
#         catalog_links, image_url = extract_product_details(product_url)
#         row['catalog_links'] = '; '.join(catalog_links)
#         row['image_url'] = image_url
#         rows.append(row)
#         print(f"Processed product ID {product_id}")  # Print each processed product ID
#         time.sleep(0.5)  # Delay to prevent overwhelming the server

# # Write the updated data to the output CSV file
# with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
#     writer.writeheader()  # Write header 
#     writer.writerows(rows)

# print(f'Updated CSV file saved as {output_csv}')


import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import re

# -------- CONFIG --------
INPUT_CSV = 'motorcycle sh pricelist.csv'
OUTPUT_CSV = 'motorcycle_sh_pricelist_with_details.csv'
SLEEP_SECONDS = 0.7          # delay between product requests
MAX_PRODUCTS = 10         # set e.g. 50 while testing, or None for all
# ------------------------


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}


def clean_url(url: str | None) -> str | None:
    """Normalize relative URLs to absolute ones where possible."""
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        # base domain
        return "https://www.motorcyclestorehouse.com" + url
    return url


def extract_image_url(soup: BeautifulSoup, product_id: str | None = None) -> str | None:
    """Try multiple strategies to find the main product image URL."""

    # 1) Try OpenGraph image: <meta property="og:image" content="...">
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        img = clean_url(og["content"])
        print(f"  ✅ og:image found: {img}")
        return img

    # 2) Try Twitter image: <meta name="twitter:image" content="...">
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        img = clean_url(tw["content"])
        print(f"  ✅ twitter:image found: {img}")
        return img

    # 3) Try <img> tags & pick a likely product image
    imgs = soup.find_all("img")
    print(f"  ℹ️ Found {len(imgs)} <img> tags, scanning for a product-looking one...")

    # helper to rank how "product-like" an image src is
    def score_src(src: str) -> int:
        s = src.lower()
        score = 0
        if "product" in s:
            score += 5
        if "public-assets" in s or "blob.core.windows.net" in s:
            score += 3
        if "category" in s:
            score -= 4
        if "logo" in s:
            score -= 5
        if product_id and product_id in s:
            score += 6
        return score

    best_img = None
    best_score = -999

    for img in imgs:
        src = img.get("src")
        if not src:
            continue
        s = score_src(src)
        if s > best_score:
            best_score = s
            best_img = src

    if best_img and best_score > 0:
        img_url = clean_url(best_img)
        print(f"  ✅ Chosen product image src={img_url} (score={best_score})")
        return img_url

    # 4) last resort: just return the first img src
    if imgs:
        fallback = clean_url(imgs[0].get("src"))
        print(f"  ⚠️ Using first <img> as fallback: {fallback}")
        return fallback

    print("  ⚠️ No image candidate found at all.")
    return None


def extract_catalog_links(soup: BeautifulSoup) -> list[str]:
    """Try to find catalog / PDF / external links that look relevant."""
    links = soup.find_all("a", href=True)
    print(f"  ℹ️ Found {len(links)} <a> tags, scanning for PDFs / catalog links...")

    catalog_links: list[str] = []
    for a in links:
        href = a["href"]
        href_lower = href.lower()

        # Heuristics: adapt these if you see patterns in debug HTML
        if href_lower.endswith(".pdf"):
            catalog_links.append(href)
        elif "catalog" in href_lower or "page" in href_lower:
            catalog_links.append(href)
        elif "flipbook" in href_lower or "viewer" in href_lower:
            catalog_links.append(href)

    # deduplicate & normalize
    normalized = []
    for h in catalog_links:
        u = clean_url(h)
        if u and u not in normalized:
            normalized.append(u)

    print(f"  ✅ Found {len(normalized)} catalog-like links")
    for u in normalized[:5]:
        print(f"     - {u}")
    if len(normalized) > 5:
        print(f"     ... and {len(normalized) - 5} more")

    return normalized


def extract_product_details(product_id: str) -> tuple[list[str], str | None]:
    """Download and parse details for a given product ID."""
    url = f"https://www.motorcyclestorehouse.com/product/{product_id}"
    print("\n" + "=" * 80)
    print(f"PRODUCT: {product_id}")
    print(f"URL:     {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        print(f"❌ Request error for {url}: {e}")
        return [], None

    print(f"Status: {response.status_code} | Final URL: {response.url}")

    if response.status_code != 200:
        print("❌ Non-200 status code, skipping this product.")
        return [], None

    soup = BeautifulSoup(response.content, "html.parser")

    # Extract image URL
    image_url = extract_image_url(soup, product_id=product_id)

    # Extract catalog links
    catalog_links = extract_catalog_links(soup)

    return catalog_links, image_url


def main():
    # Check input CSV
    if not os.path.exists(INPUT_CSV):
        print(f"Error: The file '{INPUT_CSV}' does not exist in this directory.")
        return

    # Read input CSV
    with open(INPUT_CSV, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        # make sure we don't duplicate columns if script is re-run
        base_fieldnames = reader.fieldnames or []
        fieldnames = list(base_fieldnames)
        if 'catalog_links' not in fieldnames:
            fieldnames.append('catalog_links')
        if 'image_url' not in fieldnames:
            fieldnames.append('image_url')

        print(f"Fieldnames in CSV: {fieldnames}")
        rows = []

        for idx, row in enumerate(reader):
            product_id = row.get('PRODUCT')
            if not product_id:
                print("⚠️ Row without PRODUCT, skipping:", row)
                continue

            # limit for testing
            if MAX_PRODUCTS is not None and idx >= MAX_PRODUCTS:
                print(f"\nReached MAX_PRODUCTS ({MAX_PRODUCTS}), stopping.")
                break

            print(f"\n--- Processing product {idx+1}: ID={product_id} ---")
            catalog_links, image_url = extract_product_details(product_id)

            row['catalog_links'] = '; '.join(catalog_links)
            row['image_url'] = image_url or ""

            rows.append(row)

            print(f"✅ Finished product ID {product_id}")
            time.sleep(SLEEP_SECONDS)

    # Write output CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n🎉 Updated CSV file saved as {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
