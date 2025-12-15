

# import os
# import time
# import csv
# import re
# import json
# from io import BytesIO
# from typing import Optional, List, Tuple, Dict
# from urllib.parse import urlparse, parse_qs, unquote

# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# import streamlit as st

# # --------------------
# # UNIVERSAL ENCODING HELPERS
# # --------------------
# def try_read_csv_from_filelike(
#     file_like,
#     delimiter=";",
#     encodings=("utf-8", "cp1252", "latin1"),
# ):
#     """
#     Try reading an uploaded CSV using multiple encodings.
#     Returns: (dataframe, detected_encoding)
#     Always succeeds (final fallback = latin1 with errors='replace').
#     """
#     for enc in encodings:
#         try:
#             file_like.seek(0)
#             return pd.read_csv(file_like, delimiter=delimiter, encoding=enc), enc
#         except Exception:
#             # catch broad exceptions (UnicodeDecodeError and others)
#             continue

#     # Final fallback (never crashes)
#     file_like.seek(0)
#     return (
#         pd.read_csv(file_like, delimiter=delimiter, encoding="latin1", errors="replace"),
#         "latin1",
#     )


# def detect_file_encoding(path, encodings=("utf-8", "cp1252", "latin1")) -> str:
#     """
#     Detect which encoding the saved CSV uses by trying to read a chunk.
#     Returns the first encoding that successfully reads the file.
#     If none succeed, returns 'latin1'.
#     """
#     for enc in encodings:
#         try:
#             with open(path, "r", encoding=enc) as f:
#                 f.read(4096)  # read a small chunk to test
#             return enc
#         except UnicodeDecodeError:
#             continue
#         except Exception:
#             # If some other IO error occurs, skip that encoding
#             continue
#     return "latin1"


# # --------------------
# # Scraping config
# # --------------------

# st.set_page_config(page_title="MCS Scraper uti", layout="wide")

# # 🔒 Hide GitHub link, footer, "made with Streamlit", and the menu
# hide_streamlit_style = """
# <style>
# /* Hide the GitHub icon/link in the top-right */
# [data-testid="stToolbar"] { 
#     display: none !important;
# }

# /* Hide Streamlit footer */
# footer {visibility: hidden;}
# footer:after {content:""; display:block;}

# /* Hide Streamlit hamburger menu */
# #MainMenu {visibility: hidden;}

# /* Hide any "View source", "Edit", or action icons */
# [data-testid="stActionButtonIcon"] {
#     display: none !important;
# }
# </style>
# """

# st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/123.0.0.0 Safari/537.36"
#     )
# }

# BASE_URL = "https://www.motorcyclestorehouse.com"


# def clean_url(url: Optional[str]) -> Optional[str]:
#     """Normalize relative URLs to absolute ones where possible."""
#     if not url:
#         return None
#     url = url.strip()
#     if url.startswith("//"):
#         return "https:" + url
#     if url.startswith("/"):
#         return BASE_URL + url
#     return url


# # --------------------
# # Helpers for logging in Streamlit
# # --------------------

# def append_log(msg: str, log_area):
#     """Append a line to the log area."""
#     if "log_lines" not in st.session_state:
#         st.session_state["log_lines"] = []
#     st.session_state["log_lines"].append(msg)
#     # show only last 200 lines
#     log_area.text("\n".join(st.session_state["log_lines"][-200:]))


# # --------------------
# # HTML parsing helpers
# # --------------------

# def underlying_url(src: str) -> str:
#     """
#     If src is a Next.js proxy like '/_next/image?url=ENCODED',
#     extract and decode the real 'url=' value; otherwise just return src.
#     """
#     if src.startswith("/_next/image"):
#         parsed = urlparse(src)
#         qs = parse_qs(parsed.query)
#         if "url" in qs:
#             return unquote(qs["url"][0])
#     return src


# def extract_image_urls(
#     soup: BeautifulSoup, product_id: Optional[str] = None
# ) -> List[str]:
#     """
#     Return a list of product image URLs.

#     Strategy:
#     1. Prefer <img> tags whose alt contains 'thumbnail'
#     2. Explicitly skip brand/logo images (alt='brand', 'brand_landscape', 'logo')
#     3. As a fallback, score remaining imgs and keep good ones.
#     """

#     imgs = soup.find_all("img")

#     product_imgs: List[str] = []
#     fallback_candidates: List[Tuple[int, str]] = []

#     def score_src(src: str) -> int:
#         s = src.lower()
#         score = 0
#         # real product CDN
#         if "images.cdn.europe-west1.gcp.commercetools.com" in s:
#             score += 6
#         # zoom/large versions are better
#         if "zoom.jpg" in s or "large.jpg" in s:
#             score += 4
#         if "product" in s:
#             score += 3
#         if "category" in s:
#             score -= 4
#         # brand / logos we want to avoid
#         if "logo" in s or "brand_landscape" in s:
#             score -= 8
#         if product_id and product_id in s:
#             score += 5
#         return score

#     # 1) First pass: explicit thumbnails & skip brand
#     for img in imgs:
#         alt = (img.get("alt") or "").lower()
#         src_raw = img.get("src")
#         if not src_raw:
#             continue

#         real = underlying_url(src_raw)
#         url = clean_url(real)
#         if not url:
#             continue

#         # skip brand/logo images
#         if alt == "brand" or "brand_landscape" in url.lower() or "logo" in url.lower():
#             continue

#         # explicit product thumbnails
#         if "thumbnail" in alt:
#             if url not in product_imgs:
#                 product_imgs.append(url)
#             continue

#         # collect as fallback candidate
#         fallback_candidates.append((score_src(url), url))

#     # 2) If we found any explicit thumbnail images, use those
#     if product_imgs:
#         return product_imgs

#     # 3) Otherwise, use scored fallback candidates
#     if fallback_candidates:
#         fallback_candidates.sort(key=lambda x: x[0], reverse=True)
#         all_urls: List[str] = []
#         for score, url in fallback_candidates:
#             if score <= 0:
#                 continue
#             if url not in all_urls:
#                 all_urls.append(url)
#         if not all_urls:
#             # nothing scored positive, take very best
#             all_urls.append(fallback_candidates[0][1])
#         return all_urls

#     # 4) Total fallback: no images at all
#     return []


# def extract_catalogs(
#     soup: BeautifulSoup, product_id: Optional[str] = None
# ) -> List[str]:
#     """
#     Find product-specific catalog links (Azure blob URLs).

#     Keep only links like:
#       https://stmcsprod.blob.core.windows.net/public-assets/catalogs/XXX/index.html?search=PRODUCT
#     """
#     links = soup.find_all("a", href=True)
#     urls: List[str] = []

#     for a in links:
#         href = a["href"]
#         url = clean_url(href)
#         if not url:
#             continue

#         parsed = urlparse(url)
#         path_lower = parsed.path.lower()
#         href_lower = href.lower()

#         # Only Azure blob 'public-assets/catalogs/...'
#         if "stmcsprod.blob.core.windows.net" not in parsed.netloc:
#             continue
#         if "/public-assets/catalogs/" not in path_lower:
#             continue

#         # ensure link is tied to this product search if product_id given
#         if product_id and product_id not in href_lower:
#             continue

#         if url in urls:
#             continue

#         urls.append(url)

#     return urls


# def extract_catalog_names(soup: BeautifulSoup) -> List[str]:
#     """
#     Extract human-readable catalog names shown near 'Catalog(s):'
#     e.g. 'Workshop', 'V-Twin', 'Street'.

#     We try:
#       1. Find an element whose text is exactly 'Catalog(s):'
#          and then collect <a> tags next to it.
#       2. Fallback: any <a> where its parent text contains 'Catalog(s):'
#     """
#     names: List[str] = []

#     # 1) direct label 'Catalog(s):'
#     label_tag = soup.find(
#         lambda tag: tag.get_text(strip=True) == "Catalog(s):"
#         if hasattr(tag, "get_text") else False
#     )

#     if label_tag:
#         # look through siblings after the label for <a> tags
#         for sibling in label_tag.next_siblings:
#             # direct <a>
#             if getattr(sibling, "name", None) == "a":
#                 txt = sibling.get_text(" ", strip=True)
#                 if txt:
#                     names.append(txt)
#             # or deeper inside elements
#             if hasattr(sibling, "find_all"):
#                 for a in sibling.find_all("a"):
#                     txt = a.get_text(" ", strip=True)
#                     if txt:
#                         names.append(txt)

#     # 2) fallback: any <a> inside a block that mentions 'Catalog(s):'
#     if not names:
#         for a in soup.find_all("a"):
#             parent = a.find_parent()
#             if parent and "Catalog(s):" in parent.get_text(" ", strip=True):
#                 txt = a.get_text(" ", strip=True)
#                 if txt and txt not in names:
#                     names.append(txt)

#     # dedupe, keep order
#     unique: List[str] = []
#     for n in names:
#         if n not in unique:
#             unique.append(n)
#     return unique


# def extract_section_text(soup: BeautifulSoup, heading_text: str) -> str:
#     """
#     Grab the text under a section heading like 'Description' or 'Fitment'.

#     Looks for heading tags with matching text, then concatenates the
#     following siblings until the next heading.
#     """
#     heading_text_lower = heading_text.lower()

#     heading = soup.find(
#         lambda tag: tag.name in ["h1", "h2", "h3", "h4"]
#         and tag.get_text(strip=True).lower() == heading_text_lower
#     )
#     if not heading:
#         return ""

#     parts: List[str] = []
#     for sib in heading.find_next_siblings():
#         # stop when a new section heading starts
#         if sib.name in ["h1", "h2", "h3", "h4"]:
#             break
#         txt = sib.get_text(" ", strip=True)
#         if txt:
#             parts.append(txt)

#     return "\n".join(parts)


# def extract_size(row: dict) -> str:
#     """
#     Extract size from a row.

#     Priority:
#     1. DESCR_TYPE like 'Size L', 'Size 2XL'
#     2. Existing size_label (if present)
#     3. 'Size X' pattern at end of DESCRIPTION2
#     """
#     descr_type = (row.get("DESCR_TYPE") or "").strip()
#     size_label = (row.get("size_label") or "").strip()
#     desc2 = (row.get("DESCRIPTION2") or "").strip()

#     # 1) DESCR_TYPE: "Size L", "Size 2XL", etc.
#     if descr_type.lower().startswith("size "):
#         return descr_type[5:].strip()

#     # 2) existing size_label if already filled
#     if size_label:
#         return size_label

#     # 3) "Size X" at end of DESCRIPTION2
#     m = re.search(r"Size\s+([A-Za-z0-9+./-]+)\s*$", desc2)
#     if m:
#         return m.group(1)

#     return ""


# def extract_product_details(product_id: str) -> Dict[str, object]:
#     """
#     Download and parse details for a given product ID.

#     Returns a dict with:
#       - image_urls (list)
#       - catalog_urls (list)
#       - catalog_names (list)
#       - description_long
#       - fitment
#     """
#     url = f"{BASE_URL}/product/{product_id}"
#     try:
#         response = requests.get(url, headers=HEADERS, timeout=20)
#         if response.status_code != 200:
#             return {
#                 "image_urls": [],
#                 "catalog_urls": [],
#                 "catalog_names": [],
#                 "description_long": "",
#                 "fitment": "",
#             }
#     except requests.RequestException:
#         return {
#             "image_urls": [],
#             "catalog_urls": [],
#             "catalog_names": [],
#             "description_long": "",
#             "fitment": "",
#         }

#     soup = BeautifulSoup(response.content, "html.parser")

#     image_urls = extract_image_urls(soup, product_id=product_id)
#     catalog_urls = extract_catalogs(soup, product_id=product_id)
#     catalog_names = extract_catalog_names(soup)
#     description_long = extract_section_text(soup, "Description")
#     fitment = extract_section_text(soup, "Fitment")

#     return {
#         "image_urls": image_urls,
#         "catalog_urls": catalog_urls,
#         "catalog_names": catalog_names,
#         "description_long": description_long,
#         "fitment": fitment,
#     }


# # --------------------
# # Pipeline steps (now accept input_encoding)
# # --------------------

# def step1_extract_details(
#     input_path: str,
#     output_path: str,
#     max_products: Optional[int],
#     progress_bar,
#     log_area,
#     input_encoding: str = "utf-8",
# ) -> Dict[str, int]:
#     """
#     Step 1: read raw CSV (using input_encoding), scrape each product page,
#     and write a UTF-8 CSV with additional detail columns.
#     """
#     rows: List[Dict[str, str]] = []
#     total_rows = 0
#     processed = 0
#     with_image = 0
#     with_image2 = 0
#     with_catalog = 0

#     try:
#         with open(input_path, newline="", encoding=input_encoding, errors="strict") as csvfile:
#             reader = csv.DictReader(csvfile, delimiter=";")
#             base_fieldnames = reader.fieldnames or []
#             fieldnames = list(base_fieldnames)

#             # add our extra columns if not already present
#             for extra_col in [
#                 "catalog_links",
#                 "catalog_names",
#                 "image_url",
#                 "image2",
#                 "image_gallery",
#                 "description_long",
#                 "fitment",
#                 "size_label",
#                 "availability_label",
#                 "variants",
#             ]:
#                 if extra_col not in fieldnames:
#                     fieldnames.append(extra_col)

#             all_rows = list(reader)
#             total_rows = len(all_rows)
#             total_to_process = total_rows if max_products is None else min(total_rows, max_products)

#             for idx, row in enumerate(all_rows):
#                 if max_products is not None and idx >= max_products:
#                     break

#                 product_id = row.get("PRODUCT")
#                 if not product_id:
#                     continue

#                 processed += 1
#                 if total_to_process:
#                     progress_bar.progress(processed / float(total_to_process))
#                 append_log(
#                     f"Step 1 → [{processed}/{total_to_process}] product {product_id}",
#                     log_area,
#                 )

#                 details = extract_product_details(product_id)

#                 all_images: List[str] = details["image_urls"] or []
#                 catalog_urls: List[str] = details["catalog_urls"] or []
#                 catalog_names: List[str] = details["catalog_names"] or []
#                 description_long: str = details["description_long"] or ""
#                 fitment: str = details["fitment"] or ""

#                 primary_image = all_images[0] if all_images else ""
#                 second_image = all_images[1] if len(all_images) > 1 else ""

#                 if primary_image:
#                     with_image += 1
#                 if second_image:
#                     with_image2 += 1
#                 if catalog_urls or catalog_names:
#                     with_catalog += 1

#                 row["catalog_links"] = "; ".join(catalog_urls)
#                 row["catalog_names"] = "; ".join(catalog_names)
#                 row["image_url"] = primary_image
#                 row["image2"] = second_image
#                 row["image_gallery"] = "; ".join(all_images)
#                 row["description_long"] = description_long
#                 row["fitment"] = fitment

#                 # size label (from DESCR_TYPE / DESCRIPTION2)
#                 row["size_label"] = extract_size(row)

#                 # availability label from raw INVENTORY
#                 inv_raw = row.get("INVENTORY")
#                 if inv_raw == "Y":
#                     row["availability_label"] = "Yes"
#                 elif inv_raw == "N":
#                     row["availability_label"] = "No"
#                 else:
#                     row["availability_label"] = ""

#                 rows.append(row)

#                 # be nice to the server
#                 time.sleep(0.5)

#     except UnicodeDecodeError as e:
#         # raise to caller to handle (so pipeline can present a friendly message)
#         raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, f"Step1 read failed: {e.reason}")
#     except Exception as e:
#         raise RuntimeError(f"Error in step1_extract_details reading input: {e}")

#     # build variants (all sizes per base product)
#     group_sizes: Dict[Tuple[str, str], set] = {}
#     for row in rows:
#         desc = (row.get("DESCRIPTION") or "").strip()
#         brand = (row.get("BRAND") or "").strip()
#         if not desc:
#             continue

#         size = extract_size(row).strip()
#         key = (desc, brand)

#         if key not in group_sizes:
#             group_sizes[key] = set()
#         if size:
#             group_sizes[key].add(size)

#     # assign variants JSON to each row
#     for row in rows:
#         desc = (row.get("DESCRIPTION") or "").strip()
#         brand = (row.get("BRAND") or "").strip()
#         key = (desc, brand)
#         sizes = sorted(group_sizes.get(key, set()))
#         row["variants"] = json.dumps(sizes, ensure_ascii=False) if sizes else "[]"

#     # write out CSV encoded as UTF-8 (consistent downstream)
#     try:
#         with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
#             writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
#             writer.writeheader()
#             writer.writerows(rows)
#     except Exception as e:
#         raise RuntimeError(f"Error in step1_extract_details writing output: {e}")

#     return {
#         "total_rows": total_rows,
#         "processed": processed,
#         "with_image": with_image,
#         "with_image2": with_image2,
#         "with_catalog": with_catalog,
#     }


# def step2_update_inventory(input_path: str, output_path: str, input_encoding: str = "utf-8") -> Dict[str, int]:
#     """
#     Step 2: change INVENTORY from Y/N to instock/outofstock.
#     Reads using input_encoding and writes UTF-8 output.
#     """
#     rows: List[Dict[str, str]] = []
#     total = 0
#     instock = 0
#     outofstock = 0
#     unchanged = 0

#     try:
#         with open(input_path, newline="", encoding=input_encoding, errors="strict") as csvfile:
#             reader = csv.DictReader(csvfile, delimiter=";")
#             fieldnames = reader.fieldnames or []

#             for row in reader:
#                 total += 1
#                 inv = row.get("INVENTORY")
#                 if inv == "Y":
#                     row["INVENTORY"] = "instock"
#                     instock += 1
#                 elif inv == "N":
#                     row["INVENTORY"] = "outofstock"
#                     outofstock += 1
#                 else:
#                     unchanged += 1
#                 rows.append(row)
#     except UnicodeDecodeError as e:
#         raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, f"Step2 read failed: {e.reason}")
#     except Exception as e:
#         raise RuntimeError(f"Error in step2_update_inventory reading input: {e}")

#     try:
#         with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
#             writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
#             writer.writeheader()
#             writer.writerows(rows)
#     except Exception as e:
#         raise RuntimeError(f"Error in step2_update_inventory writing output: {e}")

#     return {
#         "total": total,
#         "instock": instock,
#         "outofstock": outofstock,
#         "unchanged": unchanged,
#     }


# def step3_fix_image_urls(input_path: str, output_path: str, input_encoding: str = "utf-8") -> Dict[str, int]:
#     """
#     Step 3: ensure image_url and image2 have https: prefix for // URLs.
#     Reads using input_encoding and writes UTF-8 output.
#     """
#     rows: List[Dict[str, str]] = []
#     total = 0
#     fixed = 0

#     try:
#         with open(input_path, newline="", encoding=input_encoding, errors="strict") as csvfile:
#             reader = csv.DictReader(csvfile, delimiter=";")
#             fieldnames = reader.fieldnames or []

#             for row in reader:
#                 total += 1
#                 for col in ["image_url", "image2"]:
#                     img_url = row.get(col) or ""
#                     if img_url.startswith("//"):
#                         row[col] = "https:" + img_url
#                         fixed += 1
#                 rows.append(row)
#     except UnicodeDecodeError as e:
#         raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, f"Step3 read failed: {e.reason}")
#     except Exception as e:
#         raise RuntimeError(f"Error in step3_fix_image_urls reading input: {e}")

#     try:
#         with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
#             writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
#             writer.writeheader()
#             writer.writerows(rows)
#     except Exception as e:
#         raise RuntimeError(f"Error in step3_fix_image_urls writing output: {e}")

#     return {"total": total, "fixed": fixed}


# # --------------------
# # Streamlit UI
# # --------------------



# st.title("🏍️ Motorcycle Storehouse Scraper")
# st.caption(
#     "Upload price list → scrape product pages (images, catalogs, catalog names, "
#     "description, fitment, sizes) → normalize inventory → output clean CSV / JSON / Excel "
#     "ready for WooCommerce."
# )

# # --- SIDEBAR ---

# st.sidebar.header("⚙️ Configuration")

# uploaded = st.sidebar.file_uploader(
#     "Upload `motorcycle sh pricelist.csv`", type=["csv"]
# )

# total_rows: Optional[int] = None
# df_preview: Optional[pd.DataFrame] = None

# # track encodings
# PREVIEW_ENCODING: Optional[str] = None
# CSV_ENCODING: Optional[str] = None

# if uploaded is not None:
#     uploaded.seek(0)

#     # Read preview with try/ fallback
#     try:
#         df_preview, PREVIEW_ENCODING = try_read_csv_from_filelike(uploaded)
#     except Exception:
#         # ultimate fallback: latin1 with replace
#         uploaded.seek(0)
#         df_preview = pd.read_csv(uploaded, delimiter=";", encoding="latin1", errors="replace")
#         PREVIEW_ENCODING = "latin1"

#     total_rows = len(df_preview)
#     st.sidebar.success(f"Detected {total_rows} rows in uploaded CSV. (preview encoding: {PREVIEW_ENCODING})")
#     st.sidebar.caption("Preview of your file:")
#     st.dataframe(df_preview.head(10))
#     uploaded.seek(0)  # reset pointer so we can save it later

# if total_rows:
#     max_default = min(total_rows, 100)
#     max_products = st.sidebar.number_input(
#         "Max products to process (0 = all)",
#         min_value=0,
#         max_value=int(total_rows),
#         value=int(max_default),
#         step=10,
#         help="Use a smaller number for testing; set to 0 to process all rows.",
#     )
# else:
#     max_products = 0

# run_button = st.sidebar.button("🚀 Run pipeline")

# # --- MAIN LAYOUT ---

# step_col1, step_col2, step_col3 = st.columns(3)
# with step_col1:
#     step1_status = st.empty()
# with step_col2:
#     step2_status = st.empty()
# with step_col3:
#     step3_status = st.empty()

# progress_bar = st.progress(0)

# log_container = st.expander("📜 Detailed log", expanded=False)
# log_area = log_container.empty()

# if run_button:
#     if uploaded is None:
#         st.error("Please upload a CSV first in the sidebar.")
#     else:
#         # save uploaded CSV to disk
#         os.makedirs("data", exist_ok=True)
#         input_path = os.path.join("data", "input.csv")
#         with open(input_path, "wb") as f:
#             f.write(uploaded.getbuffer())

#         # detect encoding of saved file
#         try:
#             CSV_ENCODING = detect_file_encoding(input_path)
#         except Exception:
#             CSV_ENCODING = "latin1"
#         append_log(f"Detected CSV encoding: {CSV_ENCODING}", log_area)

#         # intermediate + final paths
#         step1_path = os.path.join("data", "with_details.csv")
#         step2_path = os.path.join("data", "with_inventory.csv")
#         final_path = os.path.join("data", "final_with_images_fixed.csv")

#         # interpret max_products
#         m: Optional[int] = None if max_products == 0 else int(max_products)

#         # reset log
#         st.session_state["log_lines"] = []
#         append_log("🏁 Starting pipeline...", log_area)

#         try:
#             with st.spinner("Running pipeline, this may take a while..."):
#                 # STEP 1
#                 step1_status.markdown("⏳ **Step 1/3:** Scraping product details...")
#                 append_log(
#                     "Step 1: Scraping product pages for images, catalogs, catalog names, "
#                     "description, fitment, sizes & building variants.",
#                     log_area,
#                 )
#                 # pass CSV_ENCODING into step1 (reading original uploaded file)
#                 stats1 = step1_extract_details(
#                     input_path, step1_path, m, progress_bar, log_area, input_encoding=CSV_ENCODING
#                 )
#                 step1_status.markdown("✅ **Step 1/3 complete**")
#                 append_log(
#                     f"Step 1 done: processed {stats1['processed']} products "
#                     f"({stats1['with_image']} with image_url, "
#                     f"{stats1['with_image2']} with image2, "
#                     f"{stats1['with_catalog']} with catalog info).",
#                     log_area,
#                 )

#                 # STEP 2
#                 progress_bar.progress(0)
#                 step2_status.markdown("⏳ **Step 2/3:** Updating inventory values...")
#                 append_log(
#                     "Step 2: Converting INVENTORY Y/N → instock/outofstock.", log_area
#                 )
#                 # step1 wrote UTF-8, so read step1_path using utf-8
#                 stats2 = step2_update_inventory(step1_path, step2_path, input_encoding="utf-8")
#                 step2_status.markdown("✅ **Step 2/3 complete**")
#                 append_log(
#                     f"Step 2 done: {stats2['instock']} instock, "
#                     f"{stats2['outofstock']} outofstock, "
#                     f"{stats2['unchanged']} unchanged.",
#                     log_area,
#                 )

#                 # STEP 3
#                 progress_bar.progress(0)
#                 step3_status.markdown("⏳ **Step 3/3:** Fixing image URLs...")
#                 append_log(
#                     "Step 3: Fixing any image_url/image2 that start with // to https://",
#                     log_area,
#                 )
#                 stats3 = step3_fix_image_urls(step2_path, final_path, input_encoding="utf-8")
#                 step3_status.markdown("✅ **Step 3/3 complete**")
#                 append_log(
#                     f"Step 3 done: fixed {stats3['fixed']} image URLs "
#                     f"(out of {stats3['total']}).",
#                     log_area,
#                 )

#             # load final CSV & show summary (final file written as UTF-8)
#             try:
#                 df_final = pd.read_csv(final_path, delimiter=";", encoding="utf-8")
#             except Exception:
#                 # if something unexpected happened, try latin1 fallback
#                 df_final = pd.read_csv(final_path, delimiter=";", encoding="latin1", errors="replace")

#             st.success("🎉 Pipeline finished!")

#             st.subheader("📊 Run summary")
#             c1, c2, c3 = st.columns(3)
#             with c1:
#                 st.metric("Products processed", stats1["processed"])
#                 st.metric("Products with image_url", stats1["with_image"])
#             with c2:
#                 st.metric("Products with image2", stats1["with_image2"])
#                 st.metric("Products with catalog info", stats1["with_catalog"])
#             with c3:
#                 st.metric("Inventory: instock", stats2["instock"])
#                 st.metric("Inventory: outofstock", stats2["outofstock"])
#                 st.metric("Image URLs fixed", stats3["fixed"])

#             st.subheader("Preview of final data")
#             st.dataframe(df_final.head(50))

#             # --------------------
#             # Download options: CSV, JSON, XLSX
#             # --------------------
#             csv_data = df_final.to_csv(index=False, sep=";").encode("utf-8")
#             json_data = df_final.to_json(
#                 orient="records", force_ascii=False, indent=2
#             ).encode("utf-8")

#             xls_buffer = BytesIO()
#             with pd.ExcelWriter(xls_buffer, engine="xlsxwriter") as writer:
#                 df_final.to_excel(writer, index=False, sheet_name="Products")
#             xls_buffer.seek(0)

#             st.subheader("⬇️ Download")
#             col_csv, col_json, col_xls = st.columns(3)
#             with col_csv:
#                 st.download_button(
#                     label="📄 Download CSV",
#                     data=csv_data,
#                     file_name="motorcycle_pricelist_final.csv",
#                     mime="text/csv",
#                 )
#             with col_json:
#                 st.download_button(
#                     label="🧾 Download JSON",
#                     data=json_data,
#                     file_name="motorcycle_pricelist_final.json",
#                     mime="application/json",
#                 )
#             with col_xls:
#                 st.download_button(
#                     label="📊 Download Excel (.xlsx)",
#                     data=xls_buffer,
#                     file_name="motorcycle_pricelist_final.xlsx",
#                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                 )

#             append_log("✅ Pipeline finished successfully.", log_area)

#         except UnicodeDecodeError as ude:
#             # Friendly error shown to user with suggestion to re-upload in a known encoding
#             err_msg = f"File encoding error: {ude}. Try re-saving your CSV as UTF-8 or Windows-1252."
#             append_log(err_msg, log_area)
#             st.error(err_msg)
#         except Exception as e:
#             append_log(f"Pipeline failed: {e}", log_area)
#             st.error(f"Pipeline failed: {e}")




import os
import time
import csv
import re
import json
import codecs
from io import BytesIO
from typing import Optional, List, Tuple, Dict
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st


# ============================
# UNIVERSAL ENCODING HELPERS
# ============================

# Wide coverage list (covers most real-world CSVs)
ENCODING_CANDIDATES = (
    "utf-8-sig", "utf-8",
    "utf-16", "utf-16le", "utf-16be",
    "utf-32", "utf-32le", "utf-32be",
    "cp1252", "windows-1252",
    "cp1250", "cp1251", "cp1254",
    "iso-8859-1", "iso-8859-2", "iso-8859-15",
    "latin1", "mac_roman",
    "cp437",
)

def detect_encoding_from_bytes(data: bytes) -> str:
    """Detect encoding using BOM + optional charset_normalizer + fallback decode tests."""
    # BOM checks
    if data.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return "utf-16"
    if data.startswith(codecs.BOM_UTF32_LE) or data.startswith(codecs.BOM_UTF32_BE):
        return "utf-32"

    # Optional best-effort detector (pip install charset-normalizer)
    try:
        from charset_normalizer import from_bytes  # type: ignore
        best = from_bytes(data).best()
        if best and best.encoding:
            return best.encoding
    except Exception:
        pass

    # Try decoding a sample with candidate encodings
    sample = data[:200_000]
    for enc in ENCODING_CANDIDATES:
        try:
            sample.decode(enc)
            return enc
        except Exception:
            continue

    return "latin1"


def read_csv_from_bytes(
    data: bytes,
    delimiter: str = ";",
    encoding: Optional[str] = None
) -> Tuple[pd.DataFrame, str]:
    """Read CSV bytes into DataFrame with robust encoding detection + replace on errors."""
    enc = encoding or detect_encoding_from_bytes(data)

    # Newer pandas uses encoding_errors; older pandas uses errors
    try:
        df = pd.read_csv(BytesIO(data), delimiter=delimiter, encoding=enc, encoding_errors="replace")
    except TypeError:
        df = pd.read_csv(BytesIO(data), delimiter=delimiter, encoding=enc, errors="replace")  # type: ignore

    return df, enc


def try_read_csv_from_uploaded(uploaded_file, delimiter: str = ";") -> Tuple[pd.DataFrame, str, bytes]:
    """Streamlit UploadedFile -> bytes -> robust read + returns (df, enc, bytes)."""
    data = uploaded_file.getvalue()
    df, enc = read_csv_from_bytes(data, delimiter=delimiter)
    return df, enc, data


# ============================
# STREAMLIT CONFIG
# ============================

st.set_page_config(page_title="MCS Scraper uti", layout="wide")

hide_streamlit_style = """
<style>
[data-testid="stToolbar"] { display: none !important; }
footer {visibility: hidden;}
footer:after {content:""; display:block;}
#MainMenu {visibility: hidden;}
[data-testid="stActionButtonIcon"] { display: none !important; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# ============================
# Scraping config
# ============================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}
BASE_URL = "https://www.motorcyclestorehouse.com"

# Reuse a session (faster + keeps connections)
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


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


# ============================
# Helpers for logging
# ============================

def append_log(msg: str, log_area):
    if "log_lines" not in st.session_state:
        st.session_state["log_lines"] = []
    st.session_state["log_lines"].append(msg)
    log_area.text("\n".join(st.session_state["log_lines"][-250:]))


# ============================
# HTML parsing helpers
# ============================

def underlying_url(src: str) -> str:
    """
    If src is a Next.js proxy like '/_next/image?url=ENCODED',
    extract and decode the real 'url=' value; otherwise return src.
    """
    if src.startswith("/_next/image"):
        parsed = urlparse(src)
        qs = parse_qs(parsed.query)
        if "url" in qs:
            return unquote(qs["url"][0])
    return src


def _is_brand_or_category_image(url: str, alt: str = "") -> bool:
    """Heuristic filters for non-product images (brand/logo/category nav items)."""
    u = (url or "").lower()
    a = (alt or "").lower()

    # obvious
    if a in ("brand", "logo", "nav item"):
        return True
    if "brand_landscape" in u or "logo" in u:
        return True

    # category / navigation images (your screenshot shows these)
    if "stmcsprod.blob.core.windows.net/public-assets/category_" in u:
        return True
    if "/public-assets/category_" in u:
        return True

    # shop categories thumbnails often have tiny sizes / nav patterns
    if "category_" in u and "public-assets" in u:
        return True

    return False


def extract_image_urls(soup: BeautifulSoup, product_id: Optional[str] = None) -> List[str]:
    """
    Return a list of product image URLs.

    IMPORTANT:
    - Prefer real product CDN images:
        images.cdn.europe-west1.gcp.commercetools.com
    - Strongly avoid category/brand images:
        stmcsprod.blob.core.windows.net/public-assets/category_...
    """
    imgs = soup.find_all("img")

    product_imgs: List[str] = []
    fallback_candidates: List[Tuple[int, str]] = []

    def score_src(src: str) -> int:
        s = src.lower()
        score = 0

        # product CDN (best)
        if "images.cdn.europe-west1.gcp.commercetools.com" in s:
            score += 20

        # high-res hints
        if "zoom.jpg" in s or "large.jpg" in s:
            score += 6

        # penalty for category images and other noise
        if "stmcsprod.blob.core.windows.net/public-assets/category_" in s:
            score -= 50
        if "public-assets/category_" in s:
            score -= 50
        if "category" in s:
            score -= 6
        if "logo" in s or "brand_landscape" in s:
            score -= 30

        # product id in url is a strong indicator
        if product_id and product_id in s:
            score += 10

        return score

    # Pass 1: collect all possible urls
    for img in imgs:
        alt = img.get("alt") or ""
        src_raw = img.get("src")
        if not src_raw:
            continue

        real = underlying_url(src_raw)
        url = clean_url(real)
        if not url:
            continue

        if _is_brand_or_category_image(url, alt=alt):
            continue

        # Keep explicit thumbnails (often the correct ones in product gallery)
        if "thumbnail" in alt.lower():
            product_imgs.append(url)
            continue

        fallback_candidates.append((score_src(url), url))

    # If we got explicit thumbnails, return those first (dedupe)
    if product_imgs:
        seen = set()
        out = []
        for u in product_imgs:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    # Otherwise, prefer ANY commercetools image first
    ct_imgs = []
    for _, u in fallback_candidates:
        if "images.cdn.europe-west1.gcp.commercetools.com" in u.lower():
            ct_imgs.append(u)
    if ct_imgs:
        seen = set()
        out = []
        for u in ct_imgs:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    # Fallback: use scored candidates
    if fallback_candidates:
        fallback_candidates.sort(key=lambda x: x[0], reverse=True)
        out: List[str] = []
        for score, u in fallback_candidates:
            if score <= 0:
                continue
            if u not in out:
                out.append(u)
        if not out:
            out.append(fallback_candidates[0][1])
        return out

    return []


def extract_catalogs(soup: BeautifulSoup, product_id: Optional[str] = None) -> List[str]:
    """
    Find product-specific catalog links (Azure blob URLs).
    Keep:
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

        if "stmcsprod.blob.core.windows.net" not in parsed.netloc:
            continue
        if "/public-assets/catalogs/" not in path_lower:
            continue
        if product_id and product_id not in href_lower:
            continue
        if url not in urls:
            urls.append(url)

    return urls


def extract_catalog_names(soup: BeautifulSoup) -> List[str]:
    """Extract catalog names shown near 'Catalog(s):'."""
    names: List[str] = []

    # 1) direct label 'Catalog(s):'
    label_tag = soup.find(
        lambda tag: hasattr(tag, "get_text") and tag.get_text(strip=True) == "Catalog(s):"
    )

    if label_tag:
        for sibling in label_tag.next_siblings:
            if getattr(sibling, "name", None) == "a":
                txt = sibling.get_text(" ", strip=True)
                if txt:
                    names.append(txt)
            if hasattr(sibling, "find_all"):
                for a in sibling.find_all("a"):
                    txt = a.get_text(" ", strip=True)
                    if txt:
                        names.append(txt)

    # 2) fallback
    if not names:
        for a in soup.find_all("a"):
            parent = a.find_parent()
            if parent and "Catalog(s):" in parent.get_text(" ", strip=True):
                txt = a.get_text(" ", strip=True)
                if txt and txt not in names:
                    names.append(txt)

    # dedupe, keep order
    out: List[str] = []
    for n in names:
        if n not in out:
            out.append(n)
    return out


def extract_section_text(soup: BeautifulSoup, heading_text: str) -> str:
    """Grab the text under a section heading like 'Description' or 'Fitment'."""
    heading_text_lower = heading_text.lower()

    heading = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3", "h4"]
        and tag.get_text(strip=True).lower() == heading_text_lower
    )
    if not heading:
        return ""

    parts: List[str] = []
    for sib in heading.find_next_siblings():
        if sib.name in ["h1", "h2", "h3", "h4"]:
            break
        txt = sib.get_text(" ", strip=True)
        if txt:
            parts.append(txt)

    return "\n".join(parts)


def extract_size(row: dict) -> str:
    """Extract size from a row."""
    descr_type = (row.get("DESCR_TYPE") or "").strip()
    size_label = (row.get("size_label") or "").strip()
    desc2 = (row.get("DESCRIPTION2") or "").strip()

    if descr_type.lower().startswith("size "):
        return descr_type[5:].strip()
    if size_label:
        return size_label

    m = re.search(r"Size\s+([A-Za-z0-9+./-]+)\s*$", desc2)
    if m:
        return m.group(1)

    return ""


def extract_breadcrumbs_and_title(soup: BeautifulSoup) -> Tuple[str, str, str]:
    """
    Extract:
      - breadcrumb_full: "Lifestyle > Merchandise > Stickers > Product Name"
      - breadcrumb_categories: "Lifestyle > Merchandise > Stickers"
      - product_title: "Product Name"
    """
    # product title: first h1 is usually correct on product pages
    h1 = soup.find("h1")
    product_title = h1.get_text(" ", strip=True) if h1 else ""

    # choose best breadcrumb <ol>
    best_ol = None
    best_score = -1

    for ol in soup.find_all("ol"):
        lis = ol.find_all("li")
        if len(lis) < 2:
            continue

        score = len(lis)

        # boost if it contains links (breadcrumbs usually do)
        if ol.find("a"):
            score += 2

        # boost if it contains a home link
        if ol.find("a", href="/"):
            score += 3

        # avoid mega-menu lists etc by preferring smaller text density
        text_len = len(ol.get_text(" ", strip=True))
        if text_len < 250:
            score += 2
        else:
            score -= 2

        if score > best_score:
            best_score = score
            best_ol = ol

    crumbs: List[str] = []
    if best_ol:
        for li in best_ol.find_all("li", recursive=True):
            t = li.get_text(" ", strip=True)
            if not t:
                continue
            # ignore noise
            if t.lower() in ("back",):
                continue
            # sometimes 'Home' is icon-only; keep only real text crumbs
            crumbs.append(t)

    # clean + dedupe while preserving order
    cleaned: List[str] = []
    for c in crumbs:
        c = re.sub(r"\s+", " ", c).strip()
        if not c:
            continue
        if c not in cleaned:
            cleaned.append(c)

    # if last crumb doesn't match title but title exists, append it
    if product_title:
        if not cleaned or cleaned[-1] != product_title:
            cleaned.append(product_title)

    breadcrumb_full = " > ".join(cleaned).strip()
    breadcrumb_categories = " > ".join(cleaned[:-1]).strip() if len(cleaned) >= 2 else ""
    return breadcrumb_full, breadcrumb_categories, product_title


def extract_product_details(product_id: str) -> Dict[str, object]:
    """Download and parse details for a given product ID."""
    url = f"{BASE_URL}/product/{product_id}"
    try:
        response = SESSION.get(url, timeout=25)
        if response.status_code != 200:
            return {
                "image_urls": [],
                "catalog_urls": [],
                "catalog_names": [],
                "description_long": "",
                "fitment": "",
                "breadcrumb_full": "",
                "breadcrumb_categories": "",
                "product_title": "",
            }
    except requests.RequestException:
        return {
            "image_urls": [],
            "catalog_urls": [],
            "catalog_names": [],
            "description_long": "",
            "fitment": "",
            "breadcrumb_full": "",
            "breadcrumb_categories": "",
            "product_title": "",
        }

    soup = BeautifulSoup(response.content, "html.parser")

    image_urls = extract_image_urls(soup, product_id=product_id)
    catalog_urls = extract_catalogs(soup, product_id=product_id)
    catalog_names = extract_catalog_names(soup)
    description_long = extract_section_text(soup, "Description")
    fitment = extract_section_text(soup, "Fitment")

    breadcrumb_full, breadcrumb_categories, product_title = extract_breadcrumbs_and_title(soup)

    return {
        "image_urls": image_urls,
        "catalog_urls": catalog_urls,
        "catalog_names": catalog_names,
        "description_long": description_long,
        "fitment": fitment,
        "breadcrumb_full": breadcrumb_full,
        "breadcrumb_categories": breadcrumb_categories,
        "product_title": product_title,
    }


# ============================
# Pipeline steps
# ============================

EXTRA_COLUMNS = [
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
    "breadcrumb_full",
    "breadcrumb_categories",
    "product_title",
]

def step1_extract_details(
    input_path: str,
    output_path: str,
    max_products: Optional[int],
    progress_bar,
    log_area,
    input_encoding: str = "utf-8",
    polite_delay_s: float = 0.35,
) -> Dict[str, int]:
    """
    Step 1:
      - read raw CSV using input_encoding (errors=replace so it NEVER crashes)
      - scrape product pages
      - write UTF-8 CSV with extra columns
    """
    rows: List[Dict[str, str]] = []
    processed = 0
    with_image = 0
    with_image2 = 0
    with_catalog = 0

    with open(input_path, newline="", encoding=input_encoding, errors="replace") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        base_fieldnames = reader.fieldnames or []
        fieldnames = list(base_fieldnames)

        for extra_col in EXTRA_COLUMNS:
            if extra_col not in fieldnames:
                fieldnames.append(extra_col)

        all_rows = list(reader)
        total_rows = len(all_rows)
        total_to_process = total_rows if max_products is None else min(total_rows, max_products)

        for idx, row in enumerate(all_rows):
            if max_products is not None and idx >= max_products:
                break

            product_id = (row.get("PRODUCT") or "").strip()
            if not product_id:
                continue

            processed += 1
            if total_to_process:
                progress_bar.progress(processed / float(total_to_process))
            append_log(f"Step 1 → [{processed}/{total_to_process}] product {product_id}", log_area)

            details = extract_product_details(product_id)

            all_images: List[str] = details.get("image_urls") or []
            catalog_urls: List[str] = details.get("catalog_urls") or []
            catalog_names: List[str] = details.get("catalog_names") or []
            description_long: str = details.get("description_long") or ""
            fitment: str = details.get("fitment") or ""

            row["breadcrumb_full"] = str(details.get("breadcrumb_full") or "")
            row["breadcrumb_categories"] = str(details.get("breadcrumb_categories") or "")
            row["product_title"] = str(details.get("product_title") or "")

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

            row["size_label"] = extract_size(row)

            inv_raw = row.get("INVENTORY")
            if inv_raw == "Y":
                row["availability_label"] = "Yes"
            elif inv_raw == "N":
                row["availability_label"] = "No"
            else:
                row["availability_label"] = ""

            rows.append(row)

            # be polite to the server
            time.sleep(polite_delay_s)

    # build variants (all sizes per base product)
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

    for row in rows:
        desc = (row.get("DESCRIPTION") or "").strip()
        brand = (row.get("BRAND") or "").strip()
        key = (desc, brand)
        sizes = sorted(group_sizes.get(key, set()))
        row["variants"] = json.dumps(sizes, ensure_ascii=False) if sizes else "[]"

    # write out UTF-8
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


def step2_update_inventory(input_path: str, output_path: str, input_encoding: str = "utf-8") -> Dict[str, int]:
    """Step 2: convert INVENTORY Y/N -> instock/outofstock. Read replace, write UTF-8."""
    rows: List[Dict[str, str]] = []
    total = 0
    instock = 0
    outofstock = 0
    unchanged = 0

    with open(input_path, newline="", encoding=input_encoding, errors="replace") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        fieldnames = reader.fieldnames or []

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


def step3_fix_image_urls(input_path: str, output_path: str, input_encoding: str = "utf-8") -> Dict[str, int]:
    """Step 3: ensure image_url and image2 have https: prefix for // URLs. Read replace, write UTF-8."""
    rows: List[Dict[str, str]] = []
    total = 0
    fixed = 0

    with open(input_path, newline="", encoding=input_encoding, errors="replace") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        fieldnames = reader.fieldnames or []

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


# ============================
# Streamlit UI
# ============================

st.title("🏍️ Motorcycle Storehouse Scraper")
st.caption(
    "Upload price list → scrape product pages (images, catalogs, breadcrumb path, "
    "description, fitment, sizes) → normalize inventory → output clean CSV / JSON / Excel "
    "ready for WooCommerce."
)

# --- SIDEBAR ---
st.sidebar.header("⚙️ Configuration")
uploaded = st.sidebar.file_uploader("Upload `motorcycle sh pricelist.csv`", type=["csv"])

preview_box = st.sidebar.empty()
preview_df_box = st.empty()  # main-area preview (bigger)
preview_info_box = st.sidebar.empty()

total_rows: Optional[int] = None
df_preview: Optional[pd.DataFrame] = None
PREVIEW_ENCODING: Optional[str] = None
UPLOADED_BYTES: Optional[bytes] = None

if uploaded is not None:
    preview_box.info("Reading CSV & building preview...")
    # NOTE: Streamlit DOES NOT have st.sidebar.spinner(); use st.spinner() normally.
    with st.spinner("Reading CSV & building preview..."):
        df_preview, PREVIEW_ENCODING, UPLOADED_BYTES = try_read_csv_from_uploaded(uploaded, delimiter=";")
        total_rows = len(df_preview)

    preview_box.success(f"Detected {total_rows} rows")
    preview_info_box.caption(f"Encoding used: {PREVIEW_ENCODING}")

    st.subheader("Preview of your file")
    preview_df_box.dataframe(df_preview.head(25), use_container_width=True)

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

st.sidebar.divider()
polite_delay_s = st.sidebar.slider(
    "Delay per product request (seconds)",
    min_value=0.0,
    max_value=2.0,
    value=0.35,
    step=0.05,
    help="Higher = safer for the server, lower = faster.",
)

run_button = st.sidebar.button("🚀 Run pipeline")

# --- MAIN STATUS AREA ---
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
        # reset log
        st.session_state["log_lines"] = []
        append_log("🏁 Starting pipeline...", log_area)

        # Save uploaded CSV to disk
        os.makedirs("data", exist_ok=True)
        input_path = os.path.join("data", "input.csv")

        file_bytes = UPLOADED_BYTES if UPLOADED_BYTES is not None else uploaded.getvalue()
        with open(input_path, "wb") as f:
            f.write(file_bytes)

        # Use preview encoding first (most reliable)
        input_encoding = PREVIEW_ENCODING or detect_encoding_from_bytes(file_bytes) or "latin1"
        append_log(f"Using input encoding: {input_encoding}", log_area)

        step1_path = os.path.join("data", "with_details.csv")
        step2_path = os.path.join("data", "with_inventory.csv")
        final_path = os.path.join("data", "final_with_images_fixed.csv")

        m: Optional[int] = None if int(max_products) == 0 else int(max_products)

        try:
            with st.spinner("Running pipeline..."):
                # STEP 1
                step1_status.markdown("⏳ **Step 1/3:** Scraping product details...")
                append_log(
                    "Step 1: Scraping product pages (images, catalogs, breadcrumb path, description, fitment, sizes).",
                    log_area,
                )
                stats1 = step1_extract_details(
                    input_path,
                    step1_path,
                    m,
                    progress_bar,
                    log_area,
                    input_encoding=input_encoding,
                    polite_delay_s=float(polite_delay_s),
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
                append_log("Step 2: Converting INVENTORY Y/N → instock/outofstock.", log_area)
                stats2 = step2_update_inventory(step1_path, step2_path, input_encoding="utf-8")
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
                append_log("Step 3: Fixing any image_url/image2 that start with // to https://", log_area)
                stats3 = step3_fix_image_urls(step2_path, final_path, input_encoding="utf-8")
                step3_status.markdown("✅ **Step 3/3 complete**")
                append_log(
                    f"Step 3 done: fixed {stats3['fixed']} image URLs "
                    f"(out of {stats3['total']}).",
                    log_area,
                )

            # Load final file
            with st.spinner("Loading final output preview..."):
                try:
                    df_final = pd.read_csv(final_path, delimiter=";", encoding="utf-8", encoding_errors="replace")
                except TypeError:
                    df_final = pd.read_csv(final_path, delimiter=";", encoding="utf-8", errors="replace")  # type: ignore

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
            st.dataframe(df_final.head(50), use_container_width=True)

            # Download outputs
            csv_data = df_final.to_csv(index=False, sep=";").encode("utf-8")
            json_data = df_final.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")

            xls_buffer = BytesIO()
            try:
                with pd.ExcelWriter(xls_buffer, engine="xlsxwriter") as writer:
                    df_final.to_excel(writer, index=False, sheet_name="Products")
            except Exception:
                with pd.ExcelWriter(xls_buffer, engine="openpyxl") as writer:
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

        except Exception as e:
            append_log(f"Pipeline failed: {e}", log_area)
            st.error(f"Pipeline failed: {e}")

