import sys
import logging
import pandas as pd
import os
import matplotlib
import matplotlib.pyplot as plt
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)

matplotlib.use('Agg')

DATA_FILE_NAME = "trip advisor restaurents  10k - trip_rest_neywork_1.csv"
PREVIEW_FILE_NAME = "preview_data.csv"

class DataProcessingError(Exception):
    pass

def validate_csv_file(file_path: str) -> None:
    if not os.path.exists(file_path):
        logging.error(f"O arquivo '{file_path}' não existe no diretório especificado.")
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    if not file_path.lower().endswith('.csv'):
        logging.error("O arquivo fornecido não é do tipo CSV.")
        raise DataProcessingError("O arquivo fornecido não possui extensão '.csv'.")

def load_dataset(file_path: str) -> pd.DataFrame:
    try:
        validate_csv_file(file_path)
        df = pd.read_csv(file_path, low_memory=False)
        logging.info(f"Dataset carregado com sucesso! ({df.shape[0]} linhas, {df.shape[1]} colunas)")
        return df
    except FileNotFoundError:
        logging.error(f"Erro: Arquivo '{file_path}' não encontrado.")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"Erro ao processar o arquivo '{file_path}': {e}")
        raise DataProcessingError(f"Falha ao interpretar o CSV: {e}")

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df.rename(columns={'Reveiw Comment': 'Review Comment'}, inplace=True)
        df['Number of review'] = pd.to_numeric(df['Number of review'].str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        df['Online Order'] = df['Online Order'].apply(lambda x: True if x == "Yes" else False)
        df['Catagory'] = df['Catagory'].str.strip()
        logging.info("Dados limpos e padronizados.")
        return df
    except KeyError as e:
        logging.error(f"Coluna esperada não encontrada no DataFrame: {e}")
        raise DataProcessingError(f"Falta coluna esperada no dataset: {e}")
    except ValueError as e:
        logging.error(f"Erro ao converter tipos de dados: {e}")
        raise DataProcessingError(f"Falha na conversão de dados: {e}")

def show_dataset_summary(df: pd.DataFrame) -> None:
    logging.info("Visualizando as primeiras linhas do dataset:")
    print(df.head(), "\n")
    logging.info("Informações gerais do dataset:")
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    logging.info(info_str)
    missing_values = df.isnull().sum()
    logging.info("Valores ausentes por coluna:")
    print(missing_values)
    df.head(100).to_csv(PREVIEW_FILE_NAME, index=False)
    logging.info(f"Prévia do dataset salva como '{PREVIEW_FILE_NAME}'")


def analyze_categories(df: pd.DataFrame) -> None:
    category_counts = df.groupby('Catagory')['Number of review'].sum().sort_values(ascending=False)
    logging.info("Categorias com mais avaliações:")
    print(category_counts.head(10))
    category_counts.head(10).plot(kind='bar', figsize=(10, 6), title='Categorias com mais avaliações', xlabel='Categoria', ylabel='Número de Avaliações')
    plt.tight_layout()
    plt.savefig("categorias_com_mais_avaliacoes.png")
    plt.close()
    logging.info("Gráfico salvo: categorias_com_mais_avaliacoes.png")

def analyze_online_orders(df: pd.DataFrame) -> None:
    online_reviews = df.groupby('Online Order')['Number of review'].mean()
    logging.info("Média de avaliações por opção de pedido online:")
    print(online_reviews)
    online_reviews.plot(kind='bar', figsize=(8, 6), title='Média de Avaliações por Pedido Online', xlabel='Pedido Online', ylabel='Número Médio de Avaliações')
    plt.xticks([0, 1], labels=["Sem Pedido Online", "Com Pedido Online"], rotation=0)
    plt.tight_layout()
    plt.savefig("media_avaliacoes_pedido_online.png")
    plt.close()
    logging.info("Gráfico salvo: media_avaliacoes_pedido_online.png")

def popular_dishes_by_category(df: pd.DataFrame) -> None:
    popular_dishes = df.groupby('Catagory')['Popular food'].apply(lambda x: x.mode().iloc[0] if not x.mode().empty else "Sem dado")
    logging.info("Pratos mais populares por categoria:")
    print(popular_dishes)

def top_reviewed_restaurant(df: pd.DataFrame) -> None:
    top_restaurant = df.loc[df['Number of review'].idxmax()]
    logging.info("Restaurante com maior número de avaliações:")
    print(top_restaurant)

def review_distribution(df: pd.DataFrame) -> None:
    df['Number of review'].plot(kind='hist', bins=20, figsize=(10, 6), title='Distribuição do Número de Avaliações', xlabel='Número de Avaliações', ylabel='Frequência')
    plt.tight_layout()
    plt.savefig("distribuicao_avaliacoes.png")
    plt.close()
    logging.info("Gráfico salvo: distribuicao_avaliacoes.png")

def analyze_category_combinations(df: pd.DataFrame) -> None:
    combined_reviews = df.groupby('Catagory')['Number of review'].sum().sort_values(ascending=False)
    logging.info("Impacto das categorias no volume de avaliações:")
    print(combined_reviews.head(10))
    combined_reviews.head(10).plot(kind='bar', figsize=(10, 6), title='Impacto das Categorias no Volume de Avaliações', xlabel='Categoria', ylabel='Número de Avaliações')
    plt.tight_layout()
    plt.savefig("impacto_categorias.png")
    plt.close()
    logging.info("Gráfico salvo: impacto_categorias.png")

def execute_analyses(df: pd.DataFrame) -> None:
    analysis_functions = [
        analyze_categories,
        analyze_online_orders,
        popular_dishes_by_category,
        top_reviewed_restaurant,
        review_distribution,
        analyze_category_combinations
    ]
    for func in analysis_functions:
        try:
            func(df)
        except Exception as e:
            logging.error(f"Erro durante a execução de uma análise: {e}")

def main() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, DATA_FILE_NAME)
    if not os.path.exists(file_path):
        logging.error(f"O arquivo '{DATA_FILE_NAME}' não foi encontrado no diretório: {current_dir}")
        sys.exit(1)
    try:
        df = load_dataset(file_path)
        df = clean_data(df)
    except (FileNotFoundError, DataProcessingError) as e:
        logging.error(f"Erro no processamento do dataset: {e}")
        sys.exit(1)
    show_dataset_summary(df)
    execute_analyses(df)

if __name__ == "__main__":
    main()
