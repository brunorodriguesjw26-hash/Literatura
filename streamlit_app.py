import streamlit as st
from psycopg2 import sql

# Criar/Atualizar a tabela no Supabase automaticamente
def criar_tabela():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id SERIAL PRIMARY KEY
        );
        """)

        colunas = [
            ("numero_pedido", "VARCHAR(50)"),
            ("nome_livro", "TEXT"),
            ("requerente", "TEXT"),
            ("data_pedido", "DATE"),
            ("recebido", "BOOLEAN DEFAULT FALSE"),
            ("data_recebimento", "VARCHAR(50)"),
            ("data_registro", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]

        for nome_coluna, tipo_coluna in colunas:
            cursor.execute(
                sql.SQL("ALTER TABLE encomendas ADD COLUMN IF NOT EXISTS {} {}")
                   .format(sql.Identifier(nome_coluna), sql.SQL(tipo_coluna))
            )

        conn.commit()
    except Exception as e:
        st.error(f"Erro ao ligar à base de dados: {e}")
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()