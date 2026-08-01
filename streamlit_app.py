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

# 1. Conexão à Base de Dados
def get_connection():
    return psycopg2.connect(DB_URL)

# 2. Criar ou Atualizar a tabela no Supabase automaticamente
def criar_tabela():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Cria a tabela base caso ainda não exista
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id SERIAL PRIMARY KEY
        );
        """)
        
        # Adiciona dinamicamente as colunas necessárias caso não existam
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

# Executa a verificação da tabela ao iniciar
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
    st.caption("Preencha as informações da nova encomenda abaixo.")

    with st.form("form_encomenda", clear_on_submit=True):
        # Linha 1: Dados do Livro e Pedido
        col1, col2 = st.columns([2, 1])
        nome_livro = col1.text_input("📖 Nome do Livro", placeholder="Ex: O Principezinho")
        numero_pedido = col2.text_input("🔢 Nº do Pedido", placeholder="Ex: PED-2024-001")

        # Linha 2: Requerente e Data do Pedido
        col3, col4 = st.columns([2, 1])
        requerente = col3.text_input("👤 Requerente", placeholder="Ex: Maria Silva")
        data_pedido = col4.date_input("📅 Data do Pedido", value=datetime.now())

        st.markdown("---")
        submetido = st.form_submit_button("💾 Guardar Encomenda", type="primary", use_container_width=True)

        if submetido:
            if nome_livro and requerente and numero_pedido:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO encomendas (numero_pedido, nome_livro, requerente, data_pedido, recebido, data_recebimento) 
                        VALUES (%s, %s, %s, %s, FALSE, NULL)
                        """,
                        (numero_pedido, nome_livro, requerente, data_pedido)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.toast(f"✅ Encomenda '{nome_livro}' registada com sucesso!", icon="🎉")
                except Exception as e:
                    st.error(f"Erro ao guardar: {e}")
            else:
                st.warning("⚠️ Por favor preencha todos os campos obrigatórios (Livro, Nº Pedido e Requerente).")

# --- Função de Carregamento dos Dados ---
def carregar_dados():
    try:
        conn = get_connection()
        query = """
        SELECT 
            id AS "ID", 
            numero_pedido AS "Nº Pedido", 
            nome_livro AS "Nome do Livro", 
            requerente AS "Requerente", 
            data_pedido AS "Data do Pedido",
            recebido AS "Recebido",
            data_recebimento AS "Data/Hora de Recebimento"
        FROM encomendas 
        ORDER BY id DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df = carregar_dados()

# --- ABA 2: CONSULTA, FILTROS E RECEBIMENTO ---
with aba2:
    st.subheader("Histórico Completo de Encomendas")

    if not df.empty:
        # Seção para marcar encomendas como recebidas com carimbo de data/hora
        with st.expander("📦 Marcar Encomenda como Recebida", expanded=True):
            st.caption("Selecione uma encomenda pendente para atualizar o seu estado (grava a data e hora atuais).")
            
            df_pendentes = df[df["Recebido"] == False].copy()
            
            if not df_pendentes.empty:
                col_rec1, col_rec2 = st.columns([3, 1])
                
                df_pendentes["label"] = df_pendentes["ID"].astype(str) + " - " + df_pendentes["Nome do Livro"].astype(str) + " (" + df_pendentes["Requerente"].astype(str) + ")"
                
                encomenda_sel = col_rec1.selectbox(
                    "Encomendas Pendentes:",
                    options=df_pendentes["label"].tolist()
                )
                
                btn_marcar_recebido = col_rec2.button("✅ Confirmar Recebimento", type="primary", use_container_width=True)
                
                if btn_marcar_recebido:
                    id_atualizar = int(encomenda_sel.split(" - ")[0])
                    data_hora_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            UPDATE encomendas 
                            SET recebido = TRUE, data_recebimento = %s 
                            WHERE id = %s
                            """,
                            (data_hora_atual, id_atualizar)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(f"✅ Encomenda registada como recebida em {data_hora_atual}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar estado: {e}")
            else:
                st.info("🎉 Todas as encomendas registadas já foram recebidas!")

        st.markdown("---")

        # Filtros
        col_f1, col_f2, col_f3 = st.columns(3)
        filtro_livro = col_f1.text_input("Filtrar por Livro:")
        filtro_requerente = col_f2.text_input("Filtrar por Requerente:")
        filtro_status = col_f3.selectbox("Estado:", ["Todos", "Recebidos", "Pendentes"])

        df_filtrado = df.copy()
        if filtro_livro:
            df_filtrado = df_filtrado[df_filtrado["Nome do Livro"].astype(str).str.contains(filtro_livro, case=False, na=False)]
        if filtro_requerente:
            df_filtrado = df_filtrado[df_filtrado["Requerente"].astype(str).str.contains(filtro_requerente, case=False, na=False)]
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
        
        # Substituir os valores nulos para visualização limpa
        df_filtrado["Data/Hora de Recebimento"] = df_filtrado["Data/Hora de Recebimento"].fillna("⏳ Pendente")

        # Exibição da tabela formatada
        st.dataframe(
            df_filtrado, 
            use_container_width=True,
            column_config={
                "Recebido": st.column_config.CheckboxColumn("Recebido?", default=False),
                "Data do Pedido": st.column_config.DateColumn("Data do Pedido", format="DD/MM/YYYY"),
                "Data/Hora de Recebimento": st.column_config.TextColumn("Data/Hora de Recebimento")
            },
            hide_index=True
        )
    else:
        st.info("Ainda não existem encomendas registadas.")

# --- ABA 3: GESTÃO E ELIMINAÇÃO ---
with aba3:
    st.subheader("Eliminar Encomenda Registada")

    if not df.empty:
        st.caption("Selecione a encomenda que pretende remover permanentemente.")

        df["display_label"] = df["ID"].astype(str) + " - " + df["Nome do Livro"].astype(str) + " (" + df["Requerente"].astype(str) + ")"
        
        col_del1, col_del2 = st.columns([3, 1])
        
        opcao_selecionada = col_del1.selectbox(
            "Selecionar encomenda:",
            options=df["display_label"].tolist()
        )
        
        id_para_eliminar = int(opcao_selecionada.split(" - ")[0])
        btn_eliminar = col_del2.button("❌ Eliminar Encomenda", type="primary", use_container_width=True)

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