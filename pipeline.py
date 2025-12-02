


# import streamlit as st
# import requests
# from bs4 import BeautifulSoup
# import csv
# import os
# import time
# import pandas as pd

# # --------------------
# # Scraping helpers
# # --------------------

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/123.0.0.0 Safari/537.36"
#     )
# }

# BASE_URL = "https://www.motorcyclestorehouse.com"


# def clean_url(url: str | None) -> str | None:
#     """Normalize relative URLs to absolute ones where possible."""
#     if not url:
#         return None
#     url = url.strip()
#     if url.startswith("//"):
#         return "https:" + url
#     if url.startswith("/"):
#         return BASE_URL + url
#     return url


# def extract_image_url(soup: BeautifulSoup, product_id: str | None = None) -> str | None:
#     """
#     Try multiple strategies to find the main product image.

#     Priority:
#     1) <meta property="og:image">
#     2) <meta name="twitter:image">
#     3) Heuristic selection over <img> tags
#     4) Fallback to the very first <img>
#     """
#     # 1) og:image
#     og = soup.find("meta", property="og:image")
#     if og and og.get("content"):
#         return clean_url(og["content"])

#     # 2) twitter:image
#     tw = soup.find("meta", attrs={"name": "twitter:image"})
#     if tw and tw.get("content"):
#         return clean_url(tw["content"])

#     # 3) Heuristic over <img> tags
#     imgs = soup.find_all("img")

#     def score_src(src: str) -> int:
#         """
#         Give a score to each image SRC so we can guess
#         which one is the real product photo.
#         """
#         s = src.lower()
#         score = 0
#         if "product" in s:
#             score += 5
#         if "public-assets" in s or "blob.core.windows.net" in s:
#             score += 3
#         if "category" in s:
#             score -= 4
#         if "logo" in s:
#             score -= 5
#         if product_id and product_id in s:
#             score += 6
#         return score

#     best_img = None
#     best_score = -999

#     for img in imgs:
#         src = img.get("src")
#         if not src:
#             continue
#         s = score_src(src)
#         if s > best_score:
#             best_score = s
#             best_img = src

#     if best_img and best_score > 0:
#         return clean_url(best_img)

#     # 4) Fallback: first <img>
#     if imgs:
#         return clean_url(imgs[0].get("src"))

#     return None


# def extract_catalog_links(soup: BeautifulSoup) -> list[str]:
#     """
#     Find catalog / PDF / catalog viewer links that look relevant.

#     Heuristics:
#     - HREF ending with .pdf
#     - URLs containing 'catalog', 'index.html', 'flipbook', 'viewer'
#     """
#     links = soup.find_all("a", href=True)
#     catalog_links: list[str] = []

#     for a in links:
#         href = a["href"]
#         href_lower = href.lower()

#         if href_lower.endswith(".pdf"):
#             catalog_links.append(href)
#         elif "catalog" in href_lower or "index.html" in href_lower:
#             catalog_links.append(href)
#         elif "flipbook" in href_lower or "viewer" in href_lower:
#             catalog_links.append(href)

#     # dedupe + normalize
#     normalized: list[str] = []
#     for h in catalog_links:
#         u = clean_url(h)
#         if u and u not in normalized:
#             normalized.append(u)
#     return normalized


# def extract_product_details(product_id: str) -> tuple[list[str], str | None]:
#     """
#     Download and parse details for a given product ID.

#     Returns:
#         (catalog_links, image_url)
#     """
#     url = f"{BASE_URL}/product/{product_id}"
#     try:
#         response = requests.get(url, headers=HEADERS, timeout=20)
#         if response.status_code != 200:
#             return [], None
#     except requests.RequestException:
#         return [], None

#     soup = BeautifulSoup(response.content, "html.parser")

#     image_url = extract_image_url(soup, product_id=product_id)
#     catalog_links = extract_catalog_links(soup)

#     return catalog_links, image_url


# # --------------------
# # Pipeline steps
# # --------------------


# def step1_extract_details(
#     input_path: str,
#     output_path: str,
#     max_products: int | None,
#     progress,
#     log_area,
# ) -> dict:
#     """
#     Step 1:
#     - Read raw CSV (supplier price list)
#     - For each product, scrape its page
#     - Add 'catalog_links' + 'image_url'
#     - Write intermediate CSV

#     Returns:
#         stats dict: {
#             "total_in_file": int,
#             "processed": int,
#             "with_images": int,
#             "with_catalogs": int,
#         }
#     """
#     with open(input_path, newline='', encoding='utf-8') as csvfile:
#         reader = csv.DictReader(csvfile, delimiter=';')
#         base_fieldnames = reader.fieldnames or []
#         fieldnames = list(base_fieldnames)

#         # Ensure our extra columns exist, but don't duplicate them
#         if 'catalog_links' not in fieldnames:
#             fieldnames.append('catalog_links')
#         if 'image_url' not in fieldnames:
#             fieldnames.append('image_url')

#         all_rows = list(reader)
#         total_in_file = len(all_rows)
#         total_to_process = total_in_file if max_products is None else min(total_in_file, max_products)

#         rows = []
#         processed = 0
#         with_images = 0
#         with_catalogs = 0

#         for idx, row in enumerate(all_rows):
#             if max_products is not None and idx >= max_products:
#                 break

#             product_id = row.get('PRODUCT')
#             if not product_id:
#                 continue

#             processed += 1
#             progress.progress(processed / total_to_process)
#             log_area.write(f"Step 1: [{processed}/{total_to_process}] Scraping product ID {product_id}")

#             catalog_links, image_url = extract_product_details(product_id)
#             if image_url:
#                 with_images += 1
#             if catalog_links:
#                 with_catalogs += 1

#             row['catalog_links'] = '; '.join(catalog_links)
#             row['image_url'] = image_url or ""
#             rows.append(row)

#             # Be gentle with the remote server
#             time.sleep(0.5)

#     # Write intermediate file
#     with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
#         writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
#         writer.writeheader()
#         writer.writerows(rows)

#     return {
#         "total_in_file": total_in_file,
#         "processed": processed,
#         "with_images": with_images,
#         "with_catalogs": with_catalogs,
#     }


# def step2_update_inventory(input_path: str, output_path: str) -> None:
#     """
#     Step 2:
#     - Read CSV with details
#     - Convert INVENTORY:
#         Y -> instock
#         N -> outofstock
#     - Write updated CSV
#     """
#     with open(input_path, newline='', encoding='utf-8') as csvfile:
#         reader = csv.DictReader(csvfile, delimiter=';')
#         fieldnames = reader.fieldnames
#         rows = []

#         for row in reader:
#             inv = row.get('INVENTORY')
#             if inv == 'Y':
#                 row['INVENTORY'] = 'instock'
#             elif inv == 'N':
#                 row['INVENTORY'] = 'outofstock'
#             rows.append(row)

#     with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
#         writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
#         writer.writeheader()
#         writer.writerows(rows)


# def step3_fix_image_urls(input_path: str, output_path: str) -> None:
#     """
#     Step 3:
#     - Ensure image_url has a proper protocol.
#       If an URL starts with //, prepend 'https:'.
#     - Write final CSV
#     """
#     with open(input_path, newline='', encoding='utf-8') as csvfile:
#         reader = csv.DictReader(csvfile, delimiter=';')
#         fieldnames = reader.fieldnames
#         rows = []

#         for row in reader:
#             img_url = row.get('image_url') or ''
#             if img_url.startswith('//'):
#                 row['image_url'] = 'https:' + img_url
#             rows.append(row)

#     with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
#         writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
#         writer.writeheader()
#         writer.writerows(rows)


# # --------------------
# # Streamlit UI
# # --------------------

# st.set_page_config(page_title="MCS Scraper", layout="wide")

# st.title("🏍️ Motorcycle Storehouse Scraper")
# st.caption("Upload price list → scrape product pages → normalize inventory → download a clean CSV")

# with st.expander("ℹ️ What does this tool do?", expanded=True):
#     st.markdown(
#         """
#         This app runs a **3-step pipeline** on your Motorcycle Storehouse price list:

#         1. **Scrape product pages**  
#            For each PRODUCT ID in your CSV, it loads the product page and extracts:
#            - A best-guess **product image URL**  
#            - Any **catalog / viewer links** related to that product  

#         2. **Normalize inventory values**  
#            Converts the `INVENTORY` column from:
#            - `Y` → `instock`  
#            - `N` → `outofstock`  

#         3. **Clean image URLs**  
#            Ensures `image_url` is always a valid, fully-qualified URL.
#         """
#     )

# # Sidebar controls
# with st.sidebar:
#     st.header("⚙️ Settings")

#     uploaded = st.file_uploader("Upload `motorcycle sh pricelist.csv`", type=["csv"])

#     max_products = st.number_input(
#         "Max products to process (0 = all)",
#         min_value=0, value=0, step=1,
#         help="Use a small number for testing. 0 = process the entire file.",
#     )

#     st.markdown("---")
#     run_button = st.button("🚀 Run full pipeline", use_container_width=True)

# # Main area placeholders
# log_area = st.empty()
# progress_bar = st.progress(0)
# result_placeholder = st.empty()

# # If a file is uploaded, show some quick info
# if uploaded is not None:
#     try:
#         df_preview = pd.read_csv(uploaded, delimiter=';')
#         st.subheader("📄 Input file preview")
#         st.write(f"Total rows in uploaded file: **{len(df_preview)}**")
#         st.dataframe(df_preview.head(20))
#     except Exception as e:
#         st.error(f"Could not read uploaded CSV: {e}")

# if run_button:
#     if not uploaded:
#         st.error("Please upload a CSV file in the sidebar first.")
#     else:
#         # Save uploaded file to disk
#         os.makedirs("data", exist_ok=True)
#         input_path = os.path.join("data", "input.csv")
#         with open(input_path, "wb") as f:
#             f.write(uploaded.getbuffer())

#         # Define intermediate & final outputs
#         step1_path = os.path.join("data", "with_details.csv")
#         step2_path = os.path.join("data", "with_inventory.csv")
#         final_path = os.path.join("data", "final_with_images_fixed.csv")

#         # Convert max_products=0 → None (meaning "all")
#         m = None if max_products == 0 else int(max_products)

#         with st.spinner("Running pipeline, this may take a while..."):
#             # STEP 1: Scrape product details
#             log_area.write("✅ Step 1/3: Scraping product details from website...")
#             progress_bar.progress(0)
#             stats_step1 = step1_extract_details(input_path, step1_path, m, progress_bar, log_area)

#             # STEP 2: Normalize inventory
#             log_area.write("✅ Step 2/3: Updating inventory values (Y/N → instock/outofstock)...")
#             progress_bar.progress(0)
#             step2_update_inventory(step1_path, step2_path)

#             # STEP 3: Clean image URLs
#             log_area.write("✅ Step 3/3: Fixing image URLs...")
#             progress_bar.progress(0)
#             step3_fix_image_urls(step2_path, final_path)

#         # Load final CSV into DataFrame
#         df_final = pd.read_csv(final_path, delimiter=';')

#         # Compute summary metrics
#         total_final = len(df_final)
#         images_final = (df_final['image_url'].astype(str).str.len() > 0).sum() if 'image_url' in df_final.columns else 0
#         catalogs_final = (
#             df_final['catalog_links'].astype(str).str.len() > 0
#         ).sum() if 'catalog_links' in df_final.columns else 0

#         st.success("🎉 Pipeline finished successfully!")

#         st.subheader("📊 Pipeline summary")
#         col1, col2, col3, col4 = st.columns(4)
#         col1.metric("Rows in input file", stats_step1["total_in_file"])
#         col2.metric("Products processed", stats_step1["processed"])
#         col3.metric("Products with image URL", stats_step1["with_images"])
#         col4.metric("Products with catalog links", stats_step1["with_catalogs"])

#         st.markdown(
#             f"""
#             **Final CSV contains:**  
#             • Total rows: **{total_final}**  
#             • Rows with a non-empty `image_url`: **{images_final}**  
#             • Rows with a non-empty `catalog_links`: **{catalogs_final}**
#             """
#         )

#         st.subheader("🔍 Preview of final CSV")
#         st.dataframe(df_final.head(50))

#         # Download button
#         with open(final_path, "rb") as f:
#             st.download_button(
#                 label="⬇️ Download final CSV",
#                 data=f,
#                 file_name="motorcycle_pricelist_final.csv",
#                 mime="text/csv",
#             )




import os
import time
import csv
import re
import json
from io import BytesIO
from typing import Optional, List, Tuple, Dict
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

# --------------------
# Scraping config
# --------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

BASE_URL = "https://www.motorcyclestorehouse.com"


def clean_url(url: Optional[str]) -> Optional[str]:
    """Normalize relative URLs to absolute ones where possible."""
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    return url


# --------------------
# Helpers for logging in Streamlit
# --------------------

def append_log(msg: str, log_area):
    """Append a line to the log area."""
    if "log_lines" not in st.session_state:
        st.session_state["log_lines"] = []
    st.session_state["log_lines"].append(msg)
    # show only last 200 lines
    log_area.text("\n".join(st.session_state["log_lines"][-200:]))


# --------------------
# HTML parsing helpers
# --------------------

def underlying_url(src: str) -> str:
    """
    If src is a Next.js proxy like '/_next/image?url=ENCODED',
    extract and decode the real 'url=' value; otherwise just return src.
    """
    if src.startswith("/_next/image"):
        parsed = urlparse(src)
        qs = parse_qs(parsed.query)
        if "url" in qs:
            return unquote(qs["url"][0])
    return src


def extract_image_urls(
    soup: BeautifulSoup, product_id: Optional[str] = None
) -> List[str]:
    """
    Return a list of product image URLs.

    Strategy:
    1. Prefer <img> tags whose alt contains 'thumbnail'
    2. Explicitly skip brand/logo images (alt='brand', 'brand_landscape', 'logo')
    3. As a fallback, score remaining imgs and keep good ones.
    """

    imgs = soup.find_all("img")

    product_imgs: List[str] = []
    fallback_candidates: List[Tuple[int, str]] = []

    def score_src(src: str) -> int:
        s = src.lower()
        score = 0
        # real product CDN
        if "images.cdn.europe-west1.gcp.commercetools.com" in s:
            score += 6
        # zoom/large versions are better
        if "zoom.jpg" in s or "large.jpg" in s:
            score += 4
        if "product" in s:
            score += 3
        if "category" in s:
            score -= 4
        # brand / logos we want to avoid
        if "logo" in s or "brand_landscape" in s:
            score -= 8
        if product_id and product_id in s:
            score += 5
        return score

    # 1) First pass: explicit thumbnails & skip brand
    for img in imgs:
        alt = (img.get("alt") or "").lower()
        src_raw = img.get("src")
        if not src_raw:
            continue

        real = underlying_url(src_raw)
        url = clean_url(real)
        if not url:
            continue

        # skip brand/logo images
        if alt == "brand" or "brand_landscape" in url.lower() or "logo" in url.lower():
            continue

        # explicit product thumbnails
        if "thumbnail" in alt:
            if url not in product_imgs:
                product_imgs.append(url)
            continue

        # collect as fallback candidate
        fallback_candidates.append((score_src(url), url))

    # 2) If we found any explicit thumbnail images, use those
    if product_imgs:
        return product_imgs

    # 3) Otherwise, use scored fallback candidates
    if fallback_candidates:
        fallback_candidates.sort(key=lambda x: x[0], reverse=True)
        all_urls: List[str] = []
        for score, url in fallback_candidates:
            if score <= 0:
                continue
            if url not in all_urls:
                all_urls.append(url)
        if not all_urls:
            # nothing scored positive, take very best
            all_urls.append(fallback_candidates[0][1])
        return all_urls

    # 4) Total fallback: no images at all
    return []


def extract_catalogs(
    soup: BeautifulSoup, product_id: Optional[str] = None
) -> List[str]:
    """
    Find product-specific catalog links (Azure blob URLs).

    Keep only links like:
      https://stmcsprod.blob.core.windows.net/public-assets/catalogs/XXX/index.html?search=PRODUCT
    """
    links = soup.find_all("a", href=True)
    urls: List[str] = []

    for a in links:
        href = a["href"]
        url = clean_url(href)
        if not url:
            continue

        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        href_lower = href.lower()

        # Only Azure blob 'public-assets/catalogs/...'
        if "stmcsprod.blob.core.windows.net" not in parsed.netloc:
            continue
        if "/public-assets/catalogs/" not in path_lower:
            continue

        # ensure link is tied to this product search if product_id given
        if product_id and product_id not in href_lower:
            continue

        if url in urls:
            continue

        urls.append(url)

    return urls


def extract_catalog_names(soup: BeautifulSoup) -> List[str]:
    """
    Extract human-readable catalog names shown near 'Catalog(s):'
    e.g. 'Workshop', 'V-Twin', 'Street'.

    We try:
      1. Find an element whose text is exactly 'Catalog(s):'
         and then collect <a> tags next to it.
      2. Fallback: any <a> where its parent text contains 'Catalog(s):'
    """
    names: List[str] = []

    # 1) direct label 'Catalog(s):'
    label_tag = soup.find(
        lambda tag: tag.get_text(strip=True) == "Catalog(s):"
        if hasattr(tag, "get_text") else False
    )

    if label_tag:
        # look through siblings after the label for <a> tags
        for sibling in label_tag.next_siblings:
            # direct <a>
            if getattr(sibling, "name", None) == "a":
                txt = sibling.get_text(" ", strip=True)
                if txt:
                    names.append(txt)
            # or deeper inside elements
            if hasattr(sibling, "find_all"):
                for a in sibling.find_all("a"):
                    txt = a.get_text(" ", strip=True)
                    if txt:
                        names.append(txt)

    # 2) fallback: any <a> inside a block that mentions 'Catalog(s):'
    if not names:
        for a in soup.find_all("a"):
            parent = a.find_parent()
            if parent and "Catalog(s):" in parent.get_text(" ", strip=True):
                txt = a.get_text(" ", strip=True)
                if txt and txt not in names:
                    names.append(txt)

    # dedupe, keep order
    unique: List[str] = []
    for n in names:
        if n not in unique:
            unique.append(n)
    return unique


def extract_section_text(soup: BeautifulSoup, heading_text: str) -> str:
    """
    Grab the text under a section heading like 'Description' or 'Fitment'.

    Looks for heading tags with matching text, then concatenates the
    following siblings until the next heading.
    """
    heading_text_lower = heading_text.lower()

    heading = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3", "h4"]
        and tag.get_text(strip=True).lower() == heading_text_lower
    )
    if not heading:
        return ""

    parts: List[str] = []
    for sib in heading.find_next_siblings():
        # stop when a new section heading starts
        if sib.name in ["h1", "h2", "h3", "h4"]:
            break
        txt = sib.get_text(" ", strip=True)
        if txt:
            parts.append(txt)

    return "\n".join(parts)


def extract_size(row: dict) -> str:
    """
    Extract size from a row.

    Priority:
    1. DESCR_TYPE like 'Size L', 'Size 2XL'
    2. Existing size_label (if present)
    3. 'Size X' pattern at end of DESCRIPTION2
    """
    descr_type = (row.get("DESCR_TYPE") or "").strip()
    size_label = (row.get("size_label") or "").strip()
    desc2 = (row.get("DESCRIPTION2") or "").strip()

    # 1) DESCR_TYPE: "Size L", "Size 2XL", etc.
    if descr_type.lower().startswith("size "):
        return descr_type[5:].strip()

    # 2) existing size_label if already filled
    if size_label:
        return size_label

    # 3) "Size X" at end of DESCRIPTION2
    m = re.search(r"Size\s+([A-Za-z0-9+./-]+)\s*$", desc2)
    if m:
        return m.group(1)

    return ""


def extract_product_details(product_id: str) -> Dict[str, object]:
    """
    Download and parse details for a given product ID.

    Returns a dict with:
      - image_urls (list)
      - catalog_urls (list)
      - catalog_names (list)
      - description_long
      - fitment
    """
    url = f"{BASE_URL}/product/{product_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        if response.status_code != 200:
            return {
                "image_urls": [],
                "catalog_urls": [],
                "catalog_names": [],
                "description_long": "",
                "fitment": "",
            }
    except requests.RequestException:
        return {
            "image_urls": [],
            "catalog_urls": [],
            "catalog_names": [],
            "description_long": "",
            "fitment": "",
        }

    soup = BeautifulSoup(response.content, "html.parser")

    image_urls = extract_image_urls(soup, product_id=product_id)
    catalog_urls = extract_catalogs(soup, product_id=product_id)
    catalog_names = extract_catalog_names(soup)
    description_long = extract_section_text(soup, "Description")
    fitment = extract_section_text(soup, "Fitment")

    return {
        "image_urls": image_urls,
        "catalog_urls": catalog_urls,
        "catalog_names": catalog_names,
        "description_long": description_long,
        "fitment": fitment,
    }


# --------------------
# Pipeline steps
# --------------------

def step1_extract_details(
    input_path: str,
    output_path: str,
    max_products: Optional[int],
    progress_bar,
    log_area,
) -> Dict[str, int]:
    """
    Step 1: read raw CSV, scrape each product page,
    and write a CSV with:
      - catalog_links (URLs)
      - catalog_names (human names like Workshop, V-Twin, Street)
      - image_url (primary)
      - image2 (second image if present)
      - image_gallery (all URLs joined)
      - description_long
      - fitment
      - size_label
      - availability_label (Yes/No from raw INVENTORY)
      - variants (JSON array of all sizes for this base product)
    """
    with open(input_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        base_fieldnames = reader.fieldnames or []
        fieldnames = list(base_fieldnames)

        # add our extra columns if not already present
        for extra_col in [
            "catalog_links",
            "catalog_names",
            "image_url",
            "image2",
            "image_gallery",
            "description_long",
            "fitment",
            "size_label",
            "availability_label",
            "variants",
        ]:
            if extra_col not in fieldnames:
                fieldnames.append(extra_col)

        rows: List[Dict[str, str]] = []
        all_rows = list(reader)
        total_rows = len(all_rows)
        total_to_process = total_rows if max_products is None else min(total_rows, max_products)

        processed = 0
        with_image = 0
        with_image2 = 0
        with_catalog = 0

        for idx, row in enumerate(all_rows):
            if max_products is not None and idx >= max_products:
                break

            product_id = row.get("PRODUCT")
            if not product_id:
                continue

            processed += 1
            if total_to_process:
                progress_bar.progress(processed / float(total_to_process))
            append_log(
                f"Step 1 → [{processed}/{total_to_process}] product {product_id}",
                log_area,
            )

            details = extract_product_details(product_id)

            all_images: List[str] = details["image_urls"] or []
            catalog_urls: List[str] = details["catalog_urls"] or []
            catalog_names: List[str] = details["catalog_names"] or []
            description_long: str = details["description_long"] or ""
            fitment: str = details["fitment"] or ""

            primary_image = all_images[0] if all_images else ""
            second_image = all_images[1] if len(all_images) > 1 else ""

            if primary_image:
                with_image += 1
            if second_image:
                with_image2 += 1
            if catalog_urls or catalog_names:
                with_catalog += 1

            row["catalog_links"] = "; ".join(catalog_urls)
            row["catalog_names"] = "; ".join(catalog_names)
            row["image_url"] = primary_image
            row["image2"] = second_image
            row["image_gallery"] = "; ".join(all_images)
            row["description_long"] = description_long
            row["fitment"] = fitment

            # size label (from DESCR_TYPE / DESCRIPTION2)
            row["size_label"] = extract_size(row)

            # availability label from raw INVENTORY
            inv_raw = row.get("INVENTORY")
            if inv_raw == "Y":
                row["availability_label"] = "Yes"
            elif inv_raw == "N":
                row["availability_label"] = "No"
            else:
                row["availability_label"] = ""

            rows.append(row)

            # be nice to the server
            time.sleep(0.5)

    # build variants (all sizes per base product)
    # group key: (DESCRIPTION, BRAND)
    group_sizes: Dict[Tuple[str, str], set] = {}
    for row in rows:
        desc = (row.get("DESCRIPTION") or "").strip()
        brand = (row.get("BRAND") or "").strip()
        if not desc:
            continue

        size = extract_size(row).strip()
        key = (desc, brand)

        if key not in group_sizes:
            group_sizes[key] = set()
        if size:
            group_sizes[key].add(size)

    # assign variants JSON to each row
    for row in rows:
        desc = (row.get("DESCRIPTION") or "").strip()
        brand = (row.get("BRAND") or "").strip()
        key = (desc, brand)
        sizes = sorted(group_sizes.get(key, set()))
        row["variants"] = json.dumps(sizes, ensure_ascii=False) if sizes else "[]"

    # write out CSV
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    return {
        "total_rows": total_rows,
        "processed": processed,
        "with_image": with_image,
        "with_image2": with_image2,
        "with_catalog": with_catalog,
    }


def step2_update_inventory(input_path: str, output_path: str) -> Dict[str, int]:
    """
    Step 2: change INVENTORY from Y/N to instock/outofstock.
    Returns stats.
    """
    with open(input_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        fieldnames = reader.fieldnames
        rows: List[Dict[str, str]] = []

        total = 0
        instock = 0
        outofstock = 0
        unchanged = 0

        for row in reader:
            total += 1
            inv = row.get("INVENTORY")
            if inv == "Y":
                row["INVENTORY"] = "instock"
                instock += 1
            elif inv == "N":
                row["INVENTORY"] = "outofstock"
                outofstock += 1
            else:
                unchanged += 1
            rows.append(row)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    return {
        "total": total,
        "instock": instock,
        "outofstock": outofstock,
        "unchanged": unchanged,
    }


def step3_fix_image_urls(input_path: str, output_path: str) -> Dict[str, int]:
    """
    Step 3: ensure image_url and image2 have https: prefix for // URLs.
    Returns stats.
    """
    with open(input_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        fieldnames = reader.fieldnames
        rows: List[Dict[str, str]] = []

        total = 0
        fixed = 0

        for row in reader:
            total += 1
            for col in ["image_url", "image2"]:
                img_url = row.get(col) or ""
                if img_url.startswith("//"):
                    row[col] = "https:" + img_url
                    fixed += 1
            rows.append(row)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    return {"total": total, "fixed": fixed}


# --------------------
# Streamlit UI
# --------------------

st.set_page_config(page_title="MCS Scraper", layout="wide")

st.title("🏍️ Motorcycle Storehouse Scraper")
st.caption(
    "Upload price list → scrape product pages (images, catalogs, catalog names, "
    "description, fitment, sizes) → normalize inventory → output clean CSV / JSON / Excel "
    "ready for WooCommerce."
)

# --- SIDEBAR ---

st.sidebar.header("⚙️ Configuration")

uploaded = st.sidebar.file_uploader(
    "Upload `motorcycle sh pricelist.csv`", type=["csv"]
)

total_rows: Optional[int] = None
df_preview: Optional[pd.DataFrame] = None

if uploaded is not None:
    uploaded.seek(0)
    df_preview = pd.read_csv(uploaded, delimiter=";")
    total_rows = len(df_preview)
    st.sidebar.success(f"Detected {total_rows} rows in uploaded CSV.")
    st.sidebar.caption("Preview of your file:")
    st.dataframe(df_preview.head(10))
    uploaded.seek(0)  # reset pointer so we can save it later

if total_rows:
    max_default = min(total_rows, 100)
    max_products = st.sidebar.number_input(
        "Max products to process (0 = all)",
        min_value=0,
        max_value=int(total_rows),
        value=int(max_default),
        step=10,
        help="Use a smaller number for testing; set to 0 to process all rows.",
    )
else:
    max_products = 0

run_button = st.sidebar.button("🚀 Run pipeline")

# --- MAIN LAYOUT ---

step_col1, step_col2, step_col3 = st.columns(3)
with step_col1:
    step1_status = st.empty()
with step_col2:
    step2_status = st.empty()
with step_col3:
    step3_status = st.empty()

progress_bar = st.progress(0)

log_container = st.expander("📜 Detailed log", expanded=False)
log_area = log_container.empty()

if run_button:
    if uploaded is None:
        st.error("Please upload a CSV first in the sidebar.")
    else:
        # save uploaded CSV to disk
        os.makedirs("data", exist_ok=True)
        input_path = os.path.join("data", "input.csv")
        with open(input_path, "wb") as f:
            f.write(uploaded.getbuffer())

        # intermediate + final paths
        step1_path = os.path.join("data", "with_details.csv")
        step2_path = os.path.join("data", "with_inventory.csv")
        final_path = os.path.join("data", "final_with_images_fixed.csv")

        # interpret max_products
        m: Optional[int] = None if max_products == 0 else int(max_products)

        # reset log
        st.session_state["log_lines"] = []
        append_log("🏁 Starting pipeline...", log_area)

        with st.spinner("Running pipeline, this may take a while..."):
            # STEP 1
            step1_status.markdown("⏳ **Step 1/3:** Scraping product details...")
            append_log(
                "Step 1: Scraping product pages for images, catalogs, catalog names, "
                "description, fitment, sizes & building variants.",
                log_area,
            )
            stats1 = step1_extract_details(
                input_path, step1_path, m, progress_bar, log_area
            )
            step1_status.markdown("✅ **Step 1/3 complete**")
            append_log(
                f"Step 1 done: processed {stats1['processed']} products "
                f"({stats1['with_image']} with image_url, "
                f"{stats1['with_image2']} with image2, "
                f"{stats1['with_catalog']} with catalog info).",
                log_area,
            )

            # STEP 2
            progress_bar.progress(0)
            step2_status.markdown("⏳ **Step 2/3:** Updating inventory values...")
            append_log(
                "Step 2: Converting INVENTORY Y/N → instock/outofstock.", log_area
            )
            stats2 = step2_update_inventory(step1_path, step2_path)
            step2_status.markdown("✅ **Step 2/3 complete**")
            append_log(
                f"Step 2 done: {stats2['instock']} instock, "
                f"{stats2['outofstock']} outofstock, "
                f"{stats2['unchanged']} unchanged.",
                log_area,
            )

            # STEP 3
            progress_bar.progress(0)
            step3_status.markdown("⏳ **Step 3/3:** Fixing image URLs...")
            append_log(
                "Step 3: Fixing any image_url/image2 that start with // to https://",
                log_area,
            )
            stats3 = step3_fix_image_urls(step2_path, final_path)
            step3_status.markdown("✅ **Step 3/3 complete**")
            append_log(
                f"Step 3 done: fixed {stats3['fixed']} image URLs "
                f"(out of {stats3['total']}).",
                log_area,
            )

        # load final CSV & show summary
        df_final = pd.read_csv(final_path, delimiter=";")

        st.success("🎉 Pipeline finished!")

        st.subheader("📊 Run summary")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Products processed", stats1["processed"])
            st.metric("Products with image_url", stats1["with_image"])
        with c2:
            st.metric("Products with image2", stats1["with_image2"])
            st.metric("Products with catalog info", stats1["with_catalog"])
        with c3:
            st.metric("Inventory: instock", stats2["instock"])
            st.metric("Inventory: outofstock", stats2["outofstock"])
            st.metric("Image URLs fixed", stats3["fixed"])

        st.subheader("Preview of final data")
        st.dataframe(df_final.head(50))

        # --------------------
        # Download options: CSV, JSON, XLSX
        # --------------------
        csv_data = df_final.to_csv(index=False, sep=";").encode("utf-8")
        json_data = df_final.to_json(
            orient="records", force_ascii=False, indent=2
        ).encode("utf-8")

        xls_buffer = BytesIO()
        with pd.ExcelWriter(xls_buffer, engine="xlsxwriter") as writer:
            df_final.to_excel(writer, index=False, sheet_name="Products")
        xls_buffer.seek(0)

        st.subheader("⬇️ Download")
        col_csv, col_json, col_xls = st.columns(3)
        with col_csv:
            st.download_button(
                label="📄 Download CSV",
                data=csv_data,
                file_name="motorcycle_pricelist_final.csv",
                mime="text/csv",
            )
        with col_json:
            st.download_button(
                label="🧾 Download JSON",
                data=json_data,
                file_name="motorcycle_pricelist_final.json",
                mime="application/json",
            )
        with col_xls:
            st.download_button(
                label="📊 Download Excel (.xlsx)",
                data=xls_buffer,
                file_name="motorcycle_pricelist_final.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        append_log("✅ Pipeline finished successfully.", log_area)
