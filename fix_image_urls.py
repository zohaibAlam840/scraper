import csv

input_csv = 'motorcycle_sh_pricelist_with_updated_inventory.csv'
output_csv = 'motorcycle_sh_pricelist_with_images_fixed.csv'

# Read the input CSV file
with open(input_csv, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=';')
    fieldnames = reader.fieldnames
    rows = []

    for row in reader:
        image_url = row['image_url']
        if image_url.startswith('//'):
            row['image_url'] = 'https:' + image_url
        rows.append(row)

# Write the updated data to a new CSV file
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerows(rows)

print(f'Updated CSV file saved as {output_csv}')
