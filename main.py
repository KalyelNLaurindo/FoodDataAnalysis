import sys
import logging
import pandas as pd
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)

def load_dataset(file_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path, low_memory=False)
        logging.info(f"Dataset carregado com sucesso! ({df.shape[0]} linhas, {df.shape[1]} colunas)")
        return df
    except FileNotFoundError:
        logging.error(f"Erro: Arquivo '{file_path}' não encontrado.")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"Erro ao processar o arquivo '{file_path}': {e}")
        raise

def show_dataset_summary(df: pd.DataFrame) -> None:
    logging.info("Visualizando as primeiras linhas do dataset:")
    print(df.head(), "\n")
    logging.info("Informações gerais do dataset:")
    import io
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    logging.info(info_str)
    missing_values = df.isnull().sum()
    logging.info("Valores ausentes por coluna:")
    print(missing_values)
    preview_file = "preview_data.csv"
    df.head(100).to_csv(preview_file, index=False)
    logging.info(f"Prévia do dataset salva como '{preview_file}'")

def main():
    file_name = "trip advisor restaurents  10k - trip_rest_neywork_1.csv"
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    if not os.path.exists(file_path):
        logging.error(f"O arquivo '{file_name}' não foi encontrado no diretório: {os.path.dirname(__file__)}")
        sys.exit(1)
    try:
        df = load_dataset(file_path)
    except (FileNotFoundError, pd.errors.ParserError):
        sys.exit(1)
    show_dataset_summary(df)

if __name__ == "__main__":
    main()
