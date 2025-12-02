import pandas as pd

# Load the CSV file
input_csv = 'categories-2024-04-29.csv'
df = pd.read_csv(input_csv)

# Inspect the first few rows of the dataframe
print(df.head())

# Extract categories and subcategories based on the 'path' column
categories = df[['categoryId', 'path', 'name_en']]

# Ensure all values are strings to prevent issues
categories['path'] = categories['path'].astype(str)
categories['name_en'] = categories['name_en'].astype(str)

# Split the 'path' column to understand the hierarchy
categories['path_split'] = categories['path'].apply(lambda x: x.split('/'))

# Create a new dataframe to store the hierarchical structure
hierarchical_categories = []

for _, row in categories.iterrows():
    path_parts = row['path_split']
    for i, part in enumerate(path_parts):
        if part:  # Ensure the part is not empty
            hierarchical_categories.append({
                'categoryId': row['categoryId'],
                'level': i,
                'category': part,
                'parent': path_parts[i-1] if i > 0 else None
            })

hierarchical_df = pd.DataFrame(hierarchical_categories)

# Display the hierarchical structure
print(hierarchical_df)

# Save the hierarchical structure to a new CSV file
output_csv = 'hierarchical_categories.csv'
hierarchical_df.to_csv(output_csv, index=False)

print(f"Hierarchical categories saved to {output_csv}")
