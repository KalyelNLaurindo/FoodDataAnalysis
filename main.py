import sys
import logging
import pandas as pd
import os
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import io
import argparse
from fpdf import FPDF
from typing import Callable, List

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
matplotlib.use('Agg')

DATA_FILE_NAME = "trip advisor restaurents  10k - trip_rest_neywork_1.csv"
PREVIEW_FILE_NAME = "preview_data.csv"
OUTPUT_PDF = "relatorio_analise_restaurantes.pdf"


class DataProcessingError(Exception):
    pass


class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Relatório de Análise de Restaurantes - Trip Advisor NYC', align='C', ln=True)
        self.ln(10)

    def add_section(self, title: str, content: str):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, ln=True)
        self.ln(5)
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 10, content)
        self.ln(10)

    def add_image(self, img_path: str, title: str):
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
    if not os.path.exists(file_path):
        logging.error(f"File '{file_path}' does not exist.")
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.lower().endswith('.csv'):
        logging.error("The provided file is not a CSV.")
        raise DataProcessingError("The provided file does not have a '.csv' extension.")


def load_dataset(file_path: str) -> pd.DataFrame:
    try:
        validate_csv_file(file_path)
        df = pd.read_csv(file_path, low_memory=False)
        logging.info(f"Dataset loaded successfully! ({df.shape[0]} rows, {df.shape[1]} columns)")
        return df
    except FileNotFoundError:
        logging.error(f"Error: File '{file_path}' not found.")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"Error processing the file '{file_path}': {e}")
        raise DataProcessingError(f"Failed to parse the CSV: {e}")


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    try:
        if 'Reveiw Comment' in df.columns:
            df.rename(columns={'Reveiw Comment': 'Review Comment'}, inplace=True)
        if 'Number of review' in df.columns:
            df['Number of review'] = pd.to_numeric(df['Number of review'].str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        else:
            raise KeyError("'Number of review' column is missing.")
        if 'Online Order' in df.columns:
            df['Online Order'] = df['Online Order'].apply(lambda x: x.strip().lower() == "yes")
        else:
            raise KeyError("'Online Order' column is missing.")
        if 'Catagory' in df.columns:
            df['Catagory'] = df['Catagory'].str.strip()
        else:
            raise KeyError("'Catagory' column is missing.")
        logging.info("Data cleaned and standardized.")
        return df
    except KeyError as e:
        logging.error(f"Expected column not found in the DataFrame: {e}")
        raise DataProcessingError(f"Missing expected column in the dataset: {e}")
    except ValueError as e:
        logging.error(f"Error converting data types: {e}")
        raise DataProcessingError(f"Data conversion failed: {e}")


def show_dataset_summary(df: pd.DataFrame) -> None:
    logging.info("Showing the first rows of the dataset:")
    print(df.head(), "\n")
    logging.info("General dataset information:")
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    logging.info(info_str)
    missing_values = df.isnull().sum()
    logging.info("Missing values by column:")
    print(missing_values)
    df.head(100).to_csv(PREVIEW_FILE_NAME, index=False)
    logging.info(f"Preview saved as '{PREVIEW_FILE_NAME}'")


def analyze_categories(df: pd.DataFrame) -> None:
    logging.info("Running analysis: Categories with the most reviews")
    category_counts = df.groupby('Catagory')['Number of review'].sum().sort_values(ascending=False)
    plt.figure(figsize=(12, 8))
    bars = plt.bar(category_counts.index[:10], category_counts.values[:10], color='skyblue')
    plt.title("Categorias com Mais Avaliações", fontsize=16)
    plt.xlabel("Categoria", fontsize=12)
    plt.ylabel("Número de Avaliações", fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():,}", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("categorias_com_mais_avaliacoes_enhanced.png")
    plt.close()
    logging.info("Chart saved: categorias_com_mais_avaliacoes_enhanced.png")


def analyze_online_orders(df: pd.DataFrame) -> None:
    logging.info("Running analysis: Average reviews by online order availability")
    online_reviews = df.groupby('Online Order')['Number of review'].mean()
    labels = ["Sem Pedido Online", "Com Pedido Online"]
    plt.figure(figsize=(8, 6))
    bars = plt.bar(labels, online_reviews.values, color=['lightcoral', 'seagreen'])
    plt.title("Média de Avaliações por Pedido Online", fontsize=16)
    plt.xlabel("Pedido Online", fontsize=12)
    plt.ylabel("Número Médio de Avaliações", fontsize=12)
    for bar in bars:
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{bar.get_height():.2f}", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("media_avaliacoes_pedido_online_enhanced.png")
    plt.close()
    logging.info("Chart saved: media_avaliacoes_pedido_online_enhanced.png")


def popular_dishes_by_category(df: pd.DataFrame) -> None:
    logging.info("Running analysis: Most popular dishes by category")
    if 'Popular food' in df.columns:
        popular_dishes = df.groupby('Catagory')['Popular food'].apply(
            lambda x: x.mode().iloc[0] if not x.mode().empty else "Sem dado")
        print(popular_dishes)
    else:
        logging.warning("'Popular food' column is missing, cannot determine popular dishes.")


def top_reviewed_restaurant(df: pd.DataFrame) -> None:
    logging.info("Running analysis: Top reviewed restaurant")
    top_restaurant = df.loc[df['Number of review'].idxmax()]
    print(top_restaurant)


def review_distribution(df: pd.DataFrame) -> None:
    logging.info("Running analysis: Distribution of the number of reviews")
    plt.figure(figsize=(10, 6))
    plt.hist(df['Number of review'], bins=20, color='steelblue', edgecolor='black', alpha=0.7)
    plt.axvline(np.median(df['Number of review']), color='red', linestyle='dashed', linewidth=1.5, label='Mediana')
    plt.title("Distribuição do Número de Avaliações", fontsize=16)
    plt.xlabel("Número de Avaliações", fontsize=12)
    plt.ylabel("Frequência", fontsize=12)
    plt.legend()
    plt.tight_layout()
    plt.savefig("distribuicao_avaliacoes_enhanced.png")
    plt.close()
    logging.info("Chart saved: distribuicao_avaliacoes_enhanced.png")


def analyze_category_combinations(df: pd.DataFrame) -> None:
    logging.info("Running analysis: Impact of categories on total reviews volume")
    combined_reviews = df.groupby('Catagory')['Number of review'].sum().sort_values(ascending=False)
    total_reviews = combined_reviews.sum()
    percentages = (combined_reviews / total_reviews) * 100
    plt.figure(figsize=(12, 8))
    bars = plt.bar(combined_reviews.index[:10], combined_reviews.values[:10], color='orchid')
    plt.title("Impacto das Categorias no Volume de Avaliações", fontsize=16)
    plt.xlabel("Categoria", fontsize=12)
    plt.ylabel("Número de Avaliações", fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for bar, pct in zip(bars, percentages[:10]):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{pct:.1f}%", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("impacto_categorias_enhanced.png")
    plt.close()
    logging.info("Chart saved: impacto_categorias_enhanced.png")


def top_restaurants_by_category(df: pd.DataFrame, n: int = 5) -> None:
    logging.info(f"Running analysis: Top {n} restaurants by category")
    columns_of_interest = ['Title', 'Catagory', 'Number of review']
    grouped = (
        df.groupby('Catagory', group_keys=False)
          .apply(lambda x: x[columns_of_interest].nlargest(n, 'Number of review'))
    )
    print(grouped[['Title', 'Catagory', 'Number of review']])
    grouped.to_csv("top_restaurants_by_category.csv", index=False)
    logging.info("Data saved: top_restaurants_by_category.csv")

def generate_pdf_report():
    logging.info("Generating PDF report")
    pdf = PDFReport()
    pdf.add_page()
    pdf.add_section("Resumo dos Dados", "Este relatório apresenta uma análise detalhada dos dados de restaurantes de Nova York.")
    pdf.add_image("categorias_com_mais_avaliacoes_enhanced.png", "Categorias com Mais Avaliações")
    pdf.add_image("media_avaliacoes_pedido_online_enhanced.png", "Média de Avaliações por Pedido Online")
    pdf.add_image("distribuicao_avaliacoes_enhanced.png", "Distribuição do Número de Avaliações")
    pdf.add_image("impacto_categorias_enhanced.png", "Impacto das Categorias no Volume de Avaliações")
    pdf.add_section("Conclusões", "1. Categorias como Americana e Italiana dominam o número de avaliações.\n"
                                  "2. Restaurantes com pedidos online apresentam maior engajamento.")
    pdf.output(OUTPUT_PDF)
    logging.info(f"Report generated successfully: {OUTPUT_PDF}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Script para análise de dados de restaurantes.")
    parser.add_argument("--top-n", type=int, default=10, help="Número de restaurantes por categoria a exibir.")
    parser.add_argument("--generate-report", action="store_true", help="Gera um relatório consolidado em PDF.")
    args = parser.parse_args()
    return args


def execute_analyses(df: pd.DataFrame, top_n: int = 10) -> None:
    logging.info("Starting analysis executions")
    analysis_functions: List[Callable[[pd.DataFrame], None]] = [
        analyze_categories,
        analyze_online_orders,
        popular_dishes_by_category,
        top_reviewed_restaurant,
        review_distribution,
        analyze_category_combinations,
        lambda d: top_restaurants_by_category(d, n=top_n)
    ]
    for func in analysis_functions:
        try:
            func(df)
        except Exception as e:
            logging.error(f"Error during analysis execution: {e}")


def main() -> None:
    args = parse_arguments()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, DATA_FILE_NAME)

    if not os.path.exists(file_path):
        logging.error(f"File '{DATA_FILE_NAME}' not found in directory: {current_dir}")
        sys.exit(1)

    try:
        df = load_dataset(file_path)
        df = clean_data(df)
    except (FileNotFoundError, DataProcessingError) as e:
        logging.error(f"Error processing the dataset: {e}")
        sys.exit(1)

    show_dataset_summary(df)
    execute_analyses(df, top_n=args.top_n)

    if args.generate_report:
        generate_pdf_report()


if __name__ == "__main__":
    main()
