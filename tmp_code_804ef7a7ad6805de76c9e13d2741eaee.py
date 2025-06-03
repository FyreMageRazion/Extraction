```python
import pandas as pd
import matplotlib.pyplot as plt
import os

# Define the path to the CSV file and output directory
data_path = './code/processed_data.csv'
output_dir = './code'  # Same directory as the input CSV

# Load the dataset from the CSV file
try:
    df = pd.read_csv(data_path)
    print(f"Data loaded successfully from {data_path}")
except FileNotFoundError:
    print(f"Error: File not found at {data_path}")
    exit()
except Exception as e:
    print(f"Error loading data: {e}")
    exit()


# Generate statistical summaries
try:
    summary = df.describe()
    print("Statistical summary generated.")
except Exception as e:
    print(f"Error generating statistical summary: {e}")
    summary = None  # Ensure summary is None if an error occurred

# Save statistical summaries to a text file
if summary is not None:  # Only proceed if summary was successfully generated
    summary_file_path = os.path.join(output_dir, 'eda_summary.txt')
    try:
        with open(summary_file_path, 'w') as f:
            f.write(str(summary))
        print(f"Statistical summary saved to {summary_file_path}")
    except Exception as e:
        print(f"Error saving statistical summary: {e}")

# Create a scatter plot
try:
    # Identify numeric columns for the scatter plot
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if len(numeric_cols) >= 2:
        x_col = numeric_cols[0]
        y_col = numeric_cols[1]

        plt.figure(figsize=(8, 6))  # Adjust figure size for better readability
        plt.scatter(df[x_col], df[y_col])
        plt.xlabel(x_col)
        plt.ylabel(y_col)
        plt.title(f'Scatter Plot of {x_col} vs {y_col}')
        plt.grid(True)  # Add grid for better visual analysis

        scatter_plot_path = os.path.join(output_dir, 'scatter_plot.png')
        plt.savefig(scatter_plot_path)
        plt.close()  # Close the plot to free memory
        print(f"Scatter plot saved to {scatter_plot_path}")
    else:
        print("Not enough numeric columns to create a scatter plot.")

except Exception as e:
    print(f"Error creating scatter plot: {e}")