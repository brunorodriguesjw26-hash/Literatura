# Criar/Atualizar a tabela no Supabase automaticamente
def criar_tabela():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Cria a tabela base caso ainda não exista
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id SERIAL PRIMARY KEY
        );
        """)
        
        # 2. Garante que todas as colunas necessárias existem
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
            cursor.execute(f"""
            ALTER TABLE encomendas ADD COLUMN IF NOT EXISTS {nome_coluna} {tipo_coluna};
            """)

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao ligar à base de dados: {e}")