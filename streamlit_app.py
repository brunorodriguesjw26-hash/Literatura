from datetime import datetime
import pandas as pd
import psycopg2
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Gestão de Encomendas", page_icon="📚", layout="wide"
)

# Connection String do Supabase 
# Recomendado em produção: usar st.secrets["postgres"]["url"]
DB_URL = "postgresql://postgres.pryqscahyzdbuhochvkh:Novembro2016@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

def get_connection():
    return psycopg2.connect(DB_URL)

# Criar/Atualizar a tabela no Supabase automaticamente
def criar_tabela():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id SERIAL PRIMARY KEY,
            numero_pedido VARCHAR(50),
            nome_livro TEXT,
            requerente TEXT,
            data_pedido DATE,
            recebido BOOLEAN DEFAULT FALSE,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao ligar à base de dados: {e}")

criar_tabela()

# --- TÍTULO PRINCIPAL ---
st.title("📚 Gestão de Encomendas de Livros")

# Criar as 3 Abas Principais
aba1, aba2, aba3 = st.tabs([
    "➕ Nova Encomenda", 
    "📊 Tabela e Histórico", 
    "🗑️ Gestão e Eliminação"
])

# --- ABA 1: FORMULÁRIO DE INSERÇÃO CLEAN ---
with aba1:
    st.subheader("Registar Novo Pedido")
    st.caption("Preencha as informações do livro encomendado abaixo.")

    with st.form("form_encomenda", clear_on_submit=True):
        # Linha 1: Dados do Livro e Pedido
        col1, col2 = st.columns([2, 1])
        nome_livro = col1.text_input("📖 Nome do Livro", placeholder="Ex: O Principezinho")
        numero_pedido = col2.text_input("🔢 Nº do Pedido", placeholder="Ex: PED-2024-001")

        # Linha 2: Requerente, Data e Seleção Sim/Não
        col3, col4, col5 = st.columns([2, 1, 1])
        requerente = col3.text_input("👤 Requerente", placeholder="Ex: Maria Silva")
        data_pedido = col4.date_input("📅 Data do Pedido", value=datetime.now())
        
        # Opção de escolha direta "Sim" ou "Não"
        opcao_recebido = col5.radio(
            "📦 Já foi recebido?",
            options=["Não", "Sim"],
            horizontal=True
        )

        st.markdown("---")
        submetido = st.form_submit_button("💾 Guardar Encomenda", type="primary", use_container_width=True)

        if submetido:
            if nome_livro and requerente and numero_pedido:
                # Converte "Sim" para True e "Não" para False para a base de dados
                recebido_bool = True if opcao_recebido == "Sim" else False

                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO encomendas (numero_pedido, nome_livro, requerente, data_pedido, recebido) 
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (numero_pedido, nome_livro, requerente, data_pedido, recebido_bool)
                    )
                    conn.commit()
                    st.success(f"✅ Encomenda '{nome_livro}' guardada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao guardar: {e}")
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
            else:
                st.warning("⚠️ Por favor preencha todos os campos obrigatórios (Livro, Nº Pedido e Requerente).")

# --- Carregar Dados Globais ---
try:
    conn = get_connection()
    query = """
    SELECT 
        id AS "ID", 
        numero_pedido AS "Nº Pedido", 
        nome_livro AS "Nome do Livro", 
        requerente AS "Requerente", 
        data_pedido AS "Data do Pedido",
        recebido AS "Recebido"
    FROM encomendas 
    ORDER BY id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
except Exception as e:
    df = pd.DataFrame()
    st.error(f"Erro ao carregar dados: {e}")

# --- ABA 2: CONSULTA E FILTROS ---
with aba2:
    st.subheader("Histórico Completo de Encomendas")

    if not df.empty:
        # Filtros organizados
        with st.expander("🔍 Filtros de Pesquisa", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            filtro_livro = col_f1.text_input("Filtrar por Livro:")
            filtro_requerente = col_f2.text_input("Filtrar por Requerente:")
            filtro_status = col_f3.selectbox("Estado:", ["Todos", "Recebidos", "Pendentes"])

        # Aplicação dos filtros
        df_filtrado = df.copy()
        if filtro_livro:
            df_filtrado = df_filtrado[df_filtrado["Nome do Livro"].str.contains(filtro_livro, case=False, na=False)]
        if filtro_requerente:
            df_filtrado = df_filtrado[df_filtrado["Requerente"].str.contains(filtro_requerente, case=False, na=False)]
        if filtro_status == "Recebidos":
            df_filtrado = df_filtrado[df_filtrado["Recebido"] == True]
        elif filtro_status == "Pendentes":
            df_filtrado = df_filtrado[df_filtrado["Recebido"] == False]

        # Métricas visuais
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Exibido", len(df_filtrado))
        m2.metric("Recebidos", len(df_filtrado[df_filtrado["Recebido"] == True]))
        m3.metric("Pendentes", len(df_filtrado[df_filtrado["Recebido"] == False]))

        st.markdown("---")
        
        # Tabela Formatada de Forma Apresentável
        st.dataframe(
            df_filtrado, 
            use_container_width=True,
            column_config={
                "Recebido": st.column_config.CheckboxColumn("Recebido?", default=False),
                "Data do Pedido": st.column_config.DateColumn("Data do Pedido", format="DD/MM/YYYY")
            },
            hide_index=True
        )
    else:
        st.info("Ainda não existem encomendas registadas.")

# --- ABA 3: ELIMINAÇÃO ---
with aba3:
    st.subheader("Eliminar Encomenda Registada")

    if not df.empty:
        st.caption("Selecione a encomenda que pretende remover permanentemente.")

        # Opção amigável visualmente com Nome do Livro + ID no Selectbox
        df["display_label"] = df["ID"].astype(str) + " - " + df["Nome do Livro"] + " (" + df["Requerente"] + ")"
        
        col_del1, col_del2 = st.columns([3, 1])
        
        opcao_selecionada = col_del1.selectbox(
            "Selecionar encomenda:",
            options=df["display_label"].tolist()
        )
        
        id_para_eliminar = int(opcao_selecionada.split(" - ")[0])
        btn_eliminar = col_del2.button("❌ Eliminar", type="primary", use_container_width=True)

        if btn_eliminar:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM encomendas WHERE id = %s", (id_para_eliminar,))
                conn.commit()
                cursor.close()
                conn.close()
                st.success(f"✅ Encomenda removida com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao eliminar encomenda: {e}")
    else:
        st.info("Não há registos disponíveis para eliminar.")