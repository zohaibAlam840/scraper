import requests
from bs4 import BeautifulSoup
import pandas as pd

base_url = "https://www.motorcyclestorehouse.com"

def get_soup(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return BeautifulSoup(response.content, "html.parser")

def parse_categories():
    url = f"{base_url}/category/017"
    soup = get_soup(url)
    categories = []
    for category in soup.select(".catalog_navigation_item > a"):
        name = category.text.strip()
        link = base_url + category["href"]
        categories.append({"category_name": name, "category_link": link})
    return categories

def parse_subcategories(category):
    soup = get_soup(category["category_link"])
    subcategories = []
    for subcategory in soup.select(".catalog_navigation_item > a"):
        name = subcategory.text.strip()
        link = base_url + subcategory["href"]
        subcategories.append({"subcategory_name": name, "subcategory_link": link, "parent_category": category["category_name"]})
    return subcategories

def main():
    categories = parse_categories()
    all_subcategories = []
    for category in categories:
        subcategories = parse_subcategories(category)
        all_subcategories.extend(subcategories)
    
    df = pd.DataFrame(all_subcategories)
    df.to_csv("categories_with_subcategories.csv", index=False)
    print("Categories with subcategories saved to categories_with_subcategories.csv")

if __name__ == "__main__":
    main()
