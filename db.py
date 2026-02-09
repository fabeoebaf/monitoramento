import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carrega variáveis locais
load_dotenv()

def get_db_engine():
    # Pega a URL
    db_url = os.getenv("DATABASE_URL", "sqlite:///monitoramento.db")
    
    # Se for SQLite, retorna direto
    if "sqlite" in db_url:
        return create_engine(db_url)

    # Corrige protocolo se necessário
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Cria a conexão (Pooler do Supabase exige SSL)
    return create_engine(db_url, connect_args={'sslmode': 'require'})

def ler_dados(query, params=None):
    try:
        engine = get_db_engine()
        return pd.read_sql(query, engine, params=params)
    except Exception as e:
        print(f"🔴 Erro Leitura DB: {e}")
        return pd.DataFrame()

def salvar_dados(df, nome_tabela, if_exists='append'):
    try:
        engine = get_db_engine()
        df.to_sql(nome_tabela, engine, if_exists=if_exists, index=False)
        print(f"🟢 Dados salvos com sucesso na tabela '{nome_tabela}'")
    except Exception as e:
        # Mostra o erro real
        print(f"🔴 Erro Salvar DB: {e}")
        raise e
