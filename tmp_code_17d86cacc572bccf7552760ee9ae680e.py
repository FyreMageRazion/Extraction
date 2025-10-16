import pandas as pd
import numpy as np
import os

# Define the path to the raw data and the output directory
raw_data_path = 'Projects/AutoGen/raw_data.csv'
output_dir = 'code'
output_path = os.path.join(output_dir, 'processed_data.csv')

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Load the data
try:
    df = pd.read_csv(raw_data_path)
except FileNotFoundError:
    print(f"Error: File not found at {raw_data_path}")
    exit()

# Data Cleaning and Preprocessing

# 1. Handle missing values: Fill numerical columns with the mean and categorical columns with the mode
for col in df.columns:
    if df[col].dtype in ['int64', 'float64']:
        df[col] = df[col].fillna(df[col].mean())
    else:
        df[col] = df[col].fillna(df[col].mode()[0])

# 2. Convert data types (if needed - add specific conversions here based on data understanding)
# Example: Convert a column to datetime if it represents dates
# df['date_column'] = pd.to_datetime(df['date_column'])

# 3. Remove duplicates
df = df.drop_duplicates()

# 4. Standardize text data (lowercase, remove leading/trailing spaces)
for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].str.lower().str.strip()

# Save the processed data to a new CSV file
df.to_csv(output_path, index=False)

print(f"Processed data saved to {output_path}")