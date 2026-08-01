from datetime import datetime
import pandas as pd
import psycopg2
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Gestão de Encomendas", page_icon="📚", layout="wide"
)

# Substitui pela tua Connection String do Supabase
DB_URL = "TEU_POSTGRESQL_CONNECTION_STRING_AQUI"


def get_connection():
    return psycopg2.connect(DB_URL)


# Criar a tabela no Supabase automaticamente caso ainda não exista
def criar_tabela():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id SERIAL PRIMARY KEY,
            data VARCHAR(50),
            pedido TEXT,
            destinatario TEXT
        );
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao ligar à base de dados: {e}")


criar_tabela()

# Título da App
st.title("📚 Gestão de Encomendas de Livros")

# Criar as Abas
aba1, aba2 = st.tabs(["➕ Nova Encomenda", "📊 Tabela e Histórico"])

# --- ABA 1: FORMULÁRIO DE INSERÇÃO ---
with aba1:
    st.subheader("Registar Novo Pedido")

    with st.form("form_encomenda", clear_on_submit=True):
        pedido = st.text_input("Qual foi o pedido (livro/literatura)?")
        destinatario = st.text_input("Para quem é (destinatário)?")
        submetido = st.form_submit_button("Guardar Encomenda")

        if submetido:
            if pedido and destinatario:
                data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO encomendas (data, pedido, destinatario)"
                        " VALUES (%s, %s, %s)",
                        (data_atual, pedido, destinatario),
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(
                        f"✅ Encomenda para '{destinatario}' guardada com"
                        " sucesso!"
                    )
                except Exception as e:
                    st.error(f"Erro ao guardar: {e}")
            else:
                st.warning("⚠️ Por favor preenche todos os campos.")

# --- ABA 2: TABELA DE CONSULTA ---
with aba2:
    st.subheader("Histórico Completo de Encomendas")

    try:
        conn = get_connection()
        query = (
            'SELECT id AS "ID", data AS "Data/Hora", pedido AS "Livro /'
            ' Pedido", destinatario AS "Destinatário" FROM encomendas ORDER BY'
            " id DESC"
        )
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty:
            col1, col2 = st.columns(2)
            col1.metric("Total de Encomendas", len(df))
            col2.metric("Última Encomenda", str(df["Data/Hora"].iloc[0]))

            st.markdown("---")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Ainda não existem encomendas registadas.")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")