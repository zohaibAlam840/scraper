import csv

input_csv = 'motorcycle_sh_pricelist_with_details.csv'
output_csv = 'motorcycle_sh_pricelist_with_updated_inventory.csv'

# Read the input CSV file
with open(input_csv, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile, delimiter=';')
    fieldnames = reader.fieldnames
    rows = []

    for row in reader:
        inventory_value = row['INVENTORY']
        if inventory_value == 'Y':
            row['INVENTORY'] = 'instock'
        elif inventory_value == 'N':
            row['INVENTORY'] = 'outofstock'
        rows.append(row)

# Write the updated data to a new CSV file
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
    writer.writeheader()
    writer.writerows(rows)

print(f'Updated CSV file saved as {output_csv}')
