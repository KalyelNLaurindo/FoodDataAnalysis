import sys
import logging
import pandas as pd
import os
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend for matplotlib
import matplotlib.pyplot as plt
import numpy as np
import io
import argparse
from fpdf import FPDF
from typing import Callable, List
import streamlit as st

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Default filenames
PREVIEW_FILE_NAME = "preview_data.csv"
OUTPUT_PDF = "report_analysis_restaurants.pdf"

class DataProcessingError(Exception):
    """Exception for data processing errors."""
    pass


class PDFReport(FPDF):
    """Class for generating a PDF report using FPDF."""
    def header(self):
        """Defines the header for each page in the PDF."""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Restaurants Analysis Report - Trip Advisor NYC', align='C', ln=True)
        self.ln(10)

    def add_section(self, title: str, content: str):
        """Add a textual section to the PDF report.

        Args:
            title (str): Section title.
            content (str): Section content as text.
        """
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, ln=True)
        self.ln(5)
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 10, content)
        self.ln(10)

    def add_image(self, img_path: str, title: str):
        """Add an image to the PDF report.

        Args:
            img_path (str): Path to the image.
            title (str): Title for the image section.
        """
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, ln=True)
        self.ln(5)
        if os.path.exists(img_path):
            self.image(img_path, w=180)
        else:
            logging.warning(f"Image not found: {img_path}")
            self.set_font('Arial', 'I', 10)
            self.multi_cell(0, 10, f"Image not found: {img_path}")
        self.ln(10)


def validate_csv_file(file_path: str) -> None:
    """Check if the given path points to a valid CSV file.

    Args:
        file_path (str): Path to the CSV file.

    Raises:
        FileNotFoundError: If the file does not exist.
        DataProcessingError: If the file extension is not CSV.
    """
    if not os.path.exists(file_path):
        logging.error(f"File '{file_path}' does not exist.")
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.lower().endswith('.csv'):
        logging.error("Provided file is not a CSV.")
        raise DataProcessingError("Provided file does not have '.csv' extension.")


def load_dataset(file_path: str) -> pd.DataFrame:
    """Load dataset from a CSV file into a DataFrame.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded DataFrame.

    Raises:
        FileNotFoundError: If the file is not found.
        DataProcessingError: If there is a parsing error in the CSV.
    """
    try:
        validate_csv_file(file_path)
        df = pd.read_csv(file_path, low_memory=False)
        logging.info(f"Dataset loaded successfully! ({df.shape[0]} rows, {df.shape[1]} columns)")
        return df
    except FileNotFoundError as e:
        logging.error(str(e))
        raise
    except pd.errors.ParserError as e:
        logging.error(f"Error parsing file '{file_path}': {e}")
        raise DataProcessingError(f"Failed to parse CSV: {e}")


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize the dataset.

    - Rename columns if necessary.
    - Convert 'Number of review' to int.
    - Normalize 'Online Order' to boolean.
    - Strip whitespace from 'Catagory'.

    Args:
        df (pd.DataFrame): The raw DataFrame.

    Returns:
        pd.DataFrame: Cleaned DataFrame.

    Raises:
        DataProcessingError: If expected columns are missing.
    """
    try:
        if 'Reveiw Comment' in df.columns:
            df.rename(columns={'Reveiw Comment': 'Review Comment'}, inplace=True)

        if 'Number of review' in df.columns:
            df['Number of review'] = pd.to_numeric(df['Number of review'].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        else:
            raise DataProcessingError("Missing required column: 'Number of review'.")

        if 'Online Order' in df.columns:
            df['Online Order'] = df['Online Order'].fillna("No").apply(lambda x: x.strip().lower() == "yes")
        else:
            logging.warning("Column 'Online Order' missing. Creating default False values.")
            df['Online Order'] = False

        if 'Catagory' in df.columns:
            df['Catagory'] = df['Catagory'].astype(str).str.strip()
        else:
            raise DataProcessingError("Missing required column: 'Catagory'.")

        logging.info("Data cleaned and standardized.")
        return df
    except KeyError as e:
        logging.error(f"Expected column not found: {e}")
        raise DataProcessingError(f"Missing expected column: {e}")
    except ValueError as e:
        logging.error(f"Data type conversion error: {e}")
        raise DataProcessingError(f"Data conversion failure: {e}")


def validate_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the data types of critical columns.

    Ensures 'Number of review' is int, 'Catagory' is string, and 'Online Order' is bool.

    Args:
        df (pd.DataFrame): DataFrame after cleaning.

    Returns:
        pd.DataFrame: DataFrame with validated data types.
    """
    if not pd.api.types.is_numeric_dtype(df['Number of review']):
        df['Number of review'] = pd.to_numeric(df['Number of review'], errors='coerce').fillna(0).astype(int)

    if not pd.api.types.is_string_dtype(df['Catagory']):
        df['Catagory'] = df['Catagory'].astype(str)

    if 'Online Order' in df.columns:
        # Convert to boolean explicitly (already done, but ensuring correctness)
        df['Online Order'] = df['Online Order'].astype(bool)

    logging.info("Data types validated and cleaned.")
    return df


def ensure_required_columns(df: pd.DataFrame, required_cols: List[str]) -> None:
    """Ensure that all required columns are present in the DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to check.
        required_cols (List[str]): List of required column names.

    Raises:
        DataProcessingError: If any required column is missing.
    """
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise DataProcessingError(f"Missing required columns: {missing}")


def show_dataset_summary(df: pd.DataFrame) -> None:
    """Show a summary of the dataset including head and info.

    Args:
        df (pd.DataFrame): The DataFrame to summarize.
    """
    logging.info("Displaying first rows of the dataset:")
    print(df.head(), "\n")
    logging.info("General dataset info:")
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    logging.info(info_str)

    missing_values = df.isnull().sum()
    logging.info("Missing values per column:")
    print(missing_values)

    df.head(100).to_csv(PREVIEW_FILE_NAME, index=False)
    logging.info(f"Preview saved as '{PREVIEW_FILE_NAME}'")


def analyze_categories(df: pd.DataFrame) -> None:
    """Analyze top categories by total number of reviews and create a bar chart.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
    """
    category_counts = df.groupby('Catagory')['Number of review'].sum().sort_values(ascending=False)
    plt.figure(figsize=(12, 8))
    bars = plt.bar(category_counts.index[:10], category_counts.values[:10], color='skyblue')
    plt.title("Top Categories by Number of Reviews", fontsize=16)
    plt.xlabel("Category", fontsize=12)
    plt.ylabel("Number of Reviews", fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():,}", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("top_categories_reviews.png")
    plt.close()
    logging.info("Chart saved: top_categories_reviews.png")


def analyze_online_orders(df: pd.DataFrame) -> None:
    """Analyze average reviews depending on the availability of online orders.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
    """
    online_reviews = df.groupby('Online Order')['Number of review'].mean()
    labels = ["No Online Order", "Has Online Order"]
    plt.figure(figsize=(8, 6))
    bars = plt.bar(labels, online_reviews.values, color=['lightcoral', 'seagreen'])
    plt.title("Average Number of Reviews by Online Order Availability", fontsize=16)
    plt.xlabel("Online Order", fontsize=12)
    plt.ylabel("Average Number of Reviews", fontsize=12)
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.2f}", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("avg_reviews_online_order.png")
    plt.close()
    logging.info("Chart saved: avg_reviews_online_order.png")


def popular_dishes_by_category(df: pd.DataFrame) -> None:
    """Find the most popular dishes by category if 'Popular food' column exists.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
    """
    if 'Popular food' in df.columns:
        popular_dishes = df.groupby('Catagory')['Popular food'].apply(
            lambda x: x.mode().iloc[0] if not x.mode().empty else "No data")
        popular_dishes.to_csv("popular_dishes_by_category.csv")
        logging.info("Data saved: popular_dishes_by_category.csv")
    else:
        logging.warning("Column 'Popular food' missing, cannot determine popular dishes.")


def top_reviewed_restaurant(df: pd.DataFrame) -> None:
    """Identify the restaurant with the highest number of reviews.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
    """
    if 'Number of review' in df.columns:
        top_restaurant = df.loc[df['Number of review'].idxmax()]
        top_restaurant.to_frame().transpose().to_csv("top_reviewed_restaurant.csv", index=False)
        logging.info("Data saved: top_reviewed_restaurant.csv")
    else:
        logging.warning("Column 'Number of review' missing, cannot determine top reviewed restaurant.")


def review_distribution(df: pd.DataFrame) -> None:
    """Plot the distribution of the number of reviews as a histogram.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
    """
    plt.figure(figsize=(10, 6))
    plt.hist(df['Number of review'], bins=20, color='steelblue', edgecolor='black', alpha=0.7)
    plt.axvline(np.median(df['Number of review']), color='red', linestyle='dashed', linewidth=1.5, label='Median')
    plt.title("Distribution of Number of Reviews", fontsize=16)
    plt.xlabel("Number of Reviews", fontsize=12)
    plt.ylabel("Frequency", fontsize=12)
    plt.legend()
    plt.tight_layout()
    plt.savefig("review_distribution.png")
    plt.close()
    logging.info("Chart saved: review_distribution.png")


def analyze_category_combinations(df: pd.DataFrame) -> None:
    """Analyze the impact of categories on the total volume of reviews.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
    """
    combined_reviews = df.groupby('Catagory')['Number of review'].sum().sort_values(ascending=False)
    total_reviews = combined_reviews.sum()
    percentages = (combined_reviews / total_reviews) * 100
    plt.figure(figsize=(12, 8))
    bars = plt.bar(combined_reviews.index[:10], combined_reviews.values[:10], color='orchid')
    plt.title("Impact of Categories on Total Number of Reviews", fontsize=16)
    plt.xlabel("Category", fontsize=12)
    plt.ylabel("Number of Reviews", fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for bar, pct in zip(bars, percentages[:10]):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{pct:.1f}%", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("category_impact.png")
    plt.close()
    logging.info("Chart saved: category_impact.png")


def top_restaurants_by_category(df: pd.DataFrame, n: int = 5) -> None:
    """List the top N restaurants by category based on the number of reviews.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
        n (int): Number of top restaurants per category.
    """
    columns_of_interest = ['Title', 'Catagory', 'Number of review']
    grouped = (
        df.groupby('Catagory', group_keys=False)[columns_of_interest]
        .apply(lambda x: x.nlargest(n, 'Number of review'))
    )

    grouped.to_csv("top_restaurants_by_category.csv", index=False)
    logging.info("Data saved: top_restaurants_by_category.csv")


def generate_pdf_report():
    """Generate a consolidated PDF report with results and charts."""
    logging.info("Generating PDF report")
    pdf = PDFReport()
    pdf.add_page()
    pdf.add_section("Data Summary",
                    "This report provides a detailed analysis of New York City restaurants from Trip Advisor.")
    pdf.add_image("top_categories_reviews.png", "Top Categories by Number of Reviews")
    pdf.add_image("avg_reviews_online_order.png", "Average Reviews by Online Order Availability")
    pdf.add_image("review_distribution.png", "Distribution of the Number of Reviews")
    pdf.add_image("category_impact.png", "Impact of Categories on the Total Number of Reviews")
    pdf.add_section("Conclusions",
                    "1. Certain categories like American and Italian dominate total reviews.\n"
                    "2. Restaurants offering online ordering show higher engagement in reviews.")
    pdf.output(OUTPUT_PDF)
    logging.info(f"Report generated successfully: {OUTPUT_PDF}")


def execute_analyses_sequential(df: pd.DataFrame, top_n: int = 10) -> None:
    """Execute all analysis functions sequentially to avoid thread issues.

    Args:
        df (pd.DataFrame): The DataFrame containing cleaned and validated data.
        top_n (int): Number of top restaurants per category to show.
    """
    logging.info("Starting sequential analyses execution")
    analysis_functions: List[Callable[[pd.DataFrame], None]] = [
        analyze_categories,
        analyze_online_orders,
        review_distribution,
        popular_dishes_by_category,
        top_reviewed_restaurant,
        analyze_category_combinations,
        lambda d: top_restaurants_by_category(d, n=top_n)
    ]
    for func in analysis_functions:
        try:
            func(df)
        except Exception as e:
            logging.error(f"Error during analysis execution: {e}")


def create_streamlit_dashboard(df: pd.DataFrame):
    """Create an interactive Streamlit dashboard for exploring the dataset and analyses.

    Args:
        df (pd.DataFrame): The DataFrame containing restaurant data.
    """
    st.title("Restaurants Analysis - Trip Advisor NYC")

    st.sidebar.title("Settings")
    show_summary = st.sidebar.checkbox("Show Dataset Summary", value=True)

    if show_summary:
        st.subheader("Dataset Summary")
        st.write(df.head())

    st.sidebar.subheader("Analyses")
    if st.sidebar.button("Top Categories by Number of Reviews"):
        analyze_categories(df)
        st.image("top_categories_reviews.png")

    if st.sidebar.button("Average Reviews by Online Order Availability"):
        analyze_online_orders(df)
        st.image("avg_reviews_online_order.png")

    if st.sidebar.button("Distribution of the Number of Reviews"):
        review_distribution(df)
        st.image("review_distribution.png")

    if st.sidebar.button("Popular Dishes by Category"):
        popular_dishes_by_category(df)
        st.write("Popular dishes by category saved to 'popular_dishes_by_category.csv'")

    if st.sidebar.button("Top Reviewed Restaurant"):
        top_reviewed_restaurant(df)
        st.write("Top reviewed restaurant saved to 'top_reviewed_restaurant.csv'")

    if st.sidebar.button("Impact of Categories"):
        analyze_category_combinations(df)
        st.image("category_impact.png")

    st.sidebar.subheader("PDF Report")
    if st.sidebar.button("Generate PDF Report"):
        generate_pdf_report()
        with open(OUTPUT_PDF, "rb") as pdf_file:
            st.download_button(label="Download PDF Report", data=pdf_file, file_name=OUTPUT_PDF, mime="application/pdf")


def parse_arguments():
    """Parse command line arguments for the script.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Script for NYC restaurants data analysis.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of restaurants per category to display.")
    parser.add_argument("--generate-report", action="store_true", help="Generate a consolidated PDF report.")
    parser.add_argument("--data-file", type=str, default="trip advisor restaurents  10k - trip_rest_neywork_1.csv",
                        help="Path to the input CSV data file.")
    args = parser.parse_args()
    return args


def main() -> None:
    """Main function to orchestrate data loading, cleaning, analysis, and optional reporting."""
    args = parse_arguments()
    file_path = args.data_file

    if not os.path.exists(file_path):
        logging.error(f"File '{file_path}' not found in the directory.")
        sys.exit(1)

    try:
        df = load_dataset(file_path)
        df = clean_data(df)
        df = validate_data_types(df)
        # Ensure required columns for analyses:
        required_cols = ['Catagory', 'Number of review', 'Online Order']
        ensure_required_columns(df, required_cols)
    except (FileNotFoundError, DataProcessingError) as e:
        logging.error(f"Error processing the dataset: {e}")
        sys.exit(1)

    # If "streamlit" in sys.argv, run the Streamlit dashboard
    if "streamlit" in sys.argv:
        create_streamlit_dashboard(df)
    else:
        show_dataset_summary(df)
        execute_analyses_sequential(df, top_n=args.top_n)

        if args.generate_report:
            generate_pdf_report()


if __name__ == "__main__":
    main()