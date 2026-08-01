from datetime import datetime
import pandas as pd
import psycopg2
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Gestão de Encomendas", page_icon="📚", layout="wide"
)

# Connection String do Supabase
DB_URL = "postgresql://postgres.pryqscahyzdbuhochvkh:Novembro2016@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

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

# Criar as Abas Principais
aba1, aba2 = st.tabs(["➕ Nova Encomenda", "📊 Consulta e Gestão"])

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
                        "INSERT INTO encomendas (data, pedido, destinatario) VALUES (%s, %s, %s)",
                        (data_atual, pedido, destinatario)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"✅ Encomenda para '{destinatario}' guardada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao guardar: {e}")
            else:
                st.warning("⚠️ Por favor preenche todos os campos.")

# --- ABA 2: CONSULTA E GESTÃO (DIVIDIDA EM SUB-ABAS) ---
with aba2:
    try:
        conn = get_connection()
        query = 'SELECT id AS "ID", data AS "Data/Hora", pedido AS "Livro / Pedido", destinatario AS "Destinatário" FROM encomendas ORDER BY id DESC'
        df = pd.read_sql_query(query, conn)
        conn.close()

        if not df.empty:
            # Sub-abas dentro da Aba 2
            sub_aba_tabela, sub_aba_gestao = st.tabs(["📋 Tabela e Histórico", "🗑️ Anular / Eliminar"])

            # --- SUB-ABA 1: TABELA E FILTROS ---
            with sub_aba_tabela:
                st.subheader("Histórico de Encomendas")
                
                # Filtros de Pesquisa
                st.markdown("##### 🔍 Pesquisar / Filtrar")
                col_f1, col_f2 = st.columns(2)
                filtro_pedido = col_f1.text_input("Filtrar por Livro / Pedido:", "")
                filtro_destinatario = col_f2.text_input("Filtrar por Destinatário:", "")

                # Aplicar filtros
                df_filtrado = df.copy()
                if filtro_pedido:
                    df_filtrado = df_filtrado[df_filtrado["Livro / Pedido"].str.contains(filtro_pedido, case=False, na=False)]
                if filtro_destinatario:
                    df_filtrado = df_filtrado[df_filtrado["Destinatário"].str.contains(filtro_destinatario, case=False, na=False)]

                # Métricas em destaque
                col1, col2 = st.columns(2)
                col1.metric("Total de Encomendas Exibidas", len(df_filtrado))
                col2.metric("Última Encomenda Registada", str(df["Data/Hora"].iloc[0]))

                st.markdown("---")
                st.dataframe(df_filtrado, use_container_width=True)

            # --- SUB-ABA 2: ANULAR / ELIMINAR ---
            with sub_aba_gestao:
                st.subheader("Eliminar Encomenda Registada")
                st.caption("Seleciona o ID da encomenda que pretendes remover permanentemente da base de dados.")

                col_del1, col_del2 = st.columns([3, 1])
                
                id_para_eliminar = col_del1.selectbox(
                    "Seleciona o ID da encomenda:",
                    options=df["ID"].tolist()
                )
                
                btn_eliminar = col_del2.button("❌ Eliminar Encomenda", type="primary")

                if btn_eliminar:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM encomendas WHERE id = %s", (id_para_eliminar,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(f"✅ Encomenda ID {id_para_eliminar} eliminada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao eliminar encomenda: {e}")

        else:
            st.info("Ainda não existem encomendas registadas.")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")