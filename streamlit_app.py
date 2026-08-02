from datetime import datetime
import hashlib
import re
import pandas as pd
import psycopg2
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Painel de Gestão", layout="wide"
)

# E-mail principal definido como Administrador
EMAIL_ADMINISTRADOR = "brunorodriguesj26@gmail.com"

# Estilo CSS ajustado
st.markdown("""
    <style>
    /* Estilo para os cartões da página inicial (quando autenticado) */
    .st-key-card_home > div {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.05);
        height: 100%;
    }

    /* CAIXA DE LOGIN / REGISTO A ROXO COM FRISO BRANCO A ENVOLVER TUDO */
    .login-container-box {
        background-color: #4A2574;       
        border: 2px solid #ffffff;       
        border-radius: 12px;             
        padding: 30px;
        box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.2);
    }

    /* Remove fundos parasitas dentro das colunas */
    .login-container-box div[data-testid="stColumn"] {
        background-color: transparent !important;
    }
    
    /* Cor branca para todos os textos, labels e inputs dentro da caixa roxa */
    .login-container-box label, 
    .login-container-box p, 
    .login-container-box span,
    .login-container-box h2 {
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# Connection String do Supabase
DB_URL = "postgresql://postgres.pryqscahyzdbuhochvkh:Novembro2016@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"

# 1. Conexão à Base de Dados
def get_connection():
    return psycopg2.connect(DB_URL)

# 2. Criar Tabelas Automaticamente
def criar_tabelas():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Tabela de Encomendas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS encomendas (
            id SERIAL PRIMARY KEY,
            numero_pedido VARCHAR(50),
            nome_livro TEXT,
            requerente TEXT,
            data_pedido DATE,
            recebido BOOLEAN DEFAULT FALSE,
            data_recebimento VARCHAR(50),
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Tabela de Utilizadores
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilizadores (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            congregacao VARCHAR(100),
            idade INT,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            aprovado BOOLEAN DEFAULT FALSE,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Tabela de Territórios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS meusterritorios (
            id SERIAL PRIMARY KEY,
            numero_territorio VARCHAR(50) NOT NULL,
            nome_area VARCHAR(150) NOT NULL,
            observacoes TEXT,
            nome_ficheiro VARCHAR(255),
            tipo_ficheiro VARCHAR(50),
            ficheiro_bytes BYTEA,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS congregacao VARCHAR(100);")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS idade INT;")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS aprovado BOOLEAN DEFAULT FALSE;")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao ligar à base de dados: {e}")

criar_tabelas()

# --- Funções de Validação e Segurança ---
def validar_requisitos_password(password: str) -> tuple[bool, str]:
    if len(password) < 14:
        return False, "A palavra-passe tem de ter no mínimo 14 caracteres."
    if not re.search(r"[A-Z]", password):
        return False, "A palavra-passe tem de conter pelo menos uma letra maiúscula."
    if not re.search(r"[0-9]", password):
        return False, "A palavra-passe tem de conter pelo menos um número."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "A palavra-passe tem de conter pelo menos um símbolo especial (ex: @, #, $, %, !)."
    return True, "OK"

def gerar_hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_password(password: str, hashed_password: str) -> bool:
    return gerar_hash_password(password) == hashed_password

def registar_utilizador(nome, congregacao, idade, email, password):
    valido, mensagem_validacao = validar_requisitos_password(password)
    if not valido:
        return False, mensagem_validacao

    try:
        conn = get_connection()
        cursor = conn.cursor()
        hash_pw = gerar_hash_password(password)
        email_clean = email.lower().strip()
        
        is_admin = (email_clean == EMAIL_ADMINISTRADOR.lower())
        
        cursor.execute(
            """
            INSERT INTO utilizadores (nome, congregacao, idade, email, password_hash, aprovado) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (nome, congregacao, idade, email_clean, hash_pw, is_admin)
        )
        conn.commit()
        cursor.close()
        conn.close()
        if is_admin:
            return True, "Conta Administrador criada com sucesso! Pode entrar."
        return True, "Registo efetuado com sucesso! Aguarde a aprovação do administrador para conseguir entrar."
    except psycopg2.IntegrityError:
        return False, "Este e-mail já se encontra registado."
    except Exception as e:
        return False, f"Erro ao criar utilizador: {e}"

def autenticar_utilizador(email, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nome, password_hash, aprovado, email FROM utilizadores WHERE LOWER(email) = %s", 
            (email.lower().strip(),)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            user_id, nome, hash_pw, aprovado, user_email = user
            if verificar_password(password, hash_pw):
                if not aprovado and user_email.lower() != EMAIL_ADMINISTRADOR.lower():
                    return False, "PENDENTE", "A sua conta ainda aguarda aprovação pelo administrador."
                return True, "OK", {"id": user_id, "nome": nome, "email": user_email}
        return False, "ERRO", "E-mail ou palavra-passe incorretos."
    except Exception as e:
        return False, "ERRO", f"Erro na autenticação: {e}"

# --- Funções de Administração ---
def carregar_utilizadores_pendentes():
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT id, nome, congregacao, idade, email, data_registro FROM utilizadores WHERE aprovado = FALSE ORDER BY id DESC", 
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def alterar_status_utilizador(user_id, aprovar=True):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if aprovar:
            cursor.execute("UPDATE utilizadores SET aprovado = TRUE WHERE id = %s", (user_id,))
        else:
            cursor.execute("DELETE FROM utilizadores WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False

# --- Funções de Literatura ---
def carregar_dados_literatura():
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

# --- Funções de Territórios ---
def guardar_territorio(num, nome, obs, ficheiro):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        nome_fich = None
        tipo_fich = None
        bytes_fich = None
        
        if ficheiro is not None:
            nome_fich = ficheiro.name
            tipo_fich = ficheiro.type
            bytes_fich = ficheiro.read()

        cursor.execute(
            """
            INSERT INTO meusterritorios (numero_territorio, nome_area, observacoes, nome_ficheiro, tipo_ficheiro, ficheiro_bytes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (num, nome, obs, nome_fich, tipo_fich, bytes_fich)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Território guardado com sucesso!"
    except Exception as e:
        return False, f"Erro ao guardar território: {e}"

def carregar_territorios():
    try:
        conn = get_connection()
        query = "SELECT id, numero_territorio, nome_area, observacoes, nome_ficheiro, tipo_ficheiro, ficheiro_bytes FROM meusterritorios ORDER BY id DESC"
        cursor = conn.cursor()
        cursor.execute(query)
        dados = cursor.fetchall()
        cursor.close()
        conn.close()
        return dados
    except Exception as e:
        st.error(f"Erro ao carregar territórios: {e}")
        return []

# --- GESTÃO DA SESSÃO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "utilizador_nome" not in st.session_state:
    st.session_state.utilizador_nome = ""

if "utilizador_email" not in st.session_state:
    st.session_state.utilizador_email = ""

if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Página Inicial"

if "modo_autenticacao" not in st.session_state:
    st.session_state.modo_autenticacao = "login"


# ==============================================================================
# ECRÃ DE LOGIN E REGISTO (SE NÃO ESTIVER AUTENTICADO)
# ==============================================================================
if not st.session_state.autenticado:
    col_left, col_centered, col_right = st.columns([1, 2, 1])
    
    with col_centered:
        # A CAIXA COMEÇA AQUI EM CIMA DE TUDO
        st.markdown('<div class="login-container-box">', unsafe_allow_html=True)
        
        col_titulo, col_botao_top = st.columns([3, 1])
        with col_titulo:
            if st.session_state.modo_autenticacao == "login":
                st.markdown("<h2>Iniciar Sessão</h2>", unsafe_allow_html=True)
            else:
                st.markdown("<h2>Criar Conta</h2>", unsafe_allow_html=True)

        with col_botao_top:
            if st.session_state.modo_autenticacao == "login":
                if st.button("Registar", key="btn_ir_registo", use_container_width=True):
                    st.session_state.modo_autenticacao = "registo"
                    st.rerun()
            else:
                if st.button("Login", key="btn_ir_login", use_container_width=True):
                    st.session_state.modo_autenticacao = "login"
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        if st.session_state.modo_autenticacao == "login":
            with st.form("form_login"):
                email = st.text_input("E-mail")
                password = st.text_input("Palavra-passe", type="password")
                lembrar_login = st.checkbox("Memorizar Palavra Passe")
                
                btn_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)

                if btn_login:
                    if email and password:
                        sucesso, status, resultado = autenticar_utilizador(email, password)
                        if sucesso:
                            st.session_state.autenticado = True
                            st.session_state.utilizador_nome = resultado["nome"]
                            st.session_state.utilizador_email = resultado["email"]
                            st.session_state.lembrar_sessao = lembrar_login
                            st.success(f"Bem-vindo(a), {resultado['nome']}!")
                            st.rerun()
                        elif status == "PENDENTE":
                            st.warning(resultado)
                        else:
                            st.error(resultado)
                    else:
                        st.warning("Por favor preencha todos os campos.")

        else:
            with st.form("form_registar"):
                novo_nome = st.text_input("Nome Completo")
                nova_congregacao = st.text_input("Congregação")
                nova_idade = st.number_input("Idade", min_value=10, max_value=120, value=25, step=1)
                
                novo_email = st.text_input("E-mail (usado para entrar)")
                nova_password = st.text_input(
                    "Palavra-passe", 
                    type="password", 
                    help="Requisitos: mínimo 14 caracteres, 1 letra maiúscula, 1 número e 1 símbolo especial (@, #, $, %, !)."
                )
                
                st.caption("Requisitos da palavra-passe: Mínimo de 14 caracteres, pelo menos 1 letra maiúscula, 1 número e 1 símbolo especial.")
                
                btn_registar = st.form_submit_button("Submeter Registo", type="primary", use_container_width=True)

                if btn_registar:
                    if novo_nome and nova_congregacao and novo_email and nova_password:
                        sucesso, mensagem = registar_utilizador(novo_nome, nova_congregacao, int(nova_idade), novo_email, nova_password)
                        if sucesso:
                            st.info(mensagem)
                            st.session_state.modo_autenticacao = "login"
                        else:
                            st.error(mensagem)
                    else:
                        st.warning("Preencha todos os campos obrigatórios para submeter o registo.")
        
        # A CAIXA SÓ FECHA AQUI NO FIM DE TUDO
        st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# APLICAÇÃO PRINCIPAL (APÓS AUTENTICAÇÃO)
# ==============================================================================
else:
    df_literatura = carregar_dados_literatura()
    is_admin = st.session_state.utilizador_email.lower() == EMAIL_ADMINISTRADOR.lower()

    st.sidebar.title("Sessão Ativa")
    st.sidebar.caption(f"Utilizador: **{st.session_state.utilizador_nome}**")
    if is_admin:
        st.sidebar.caption("**Administrador**")
    
    if st.sidebar.button("Terminar Sessão", type="secondary"):
        st.session_state.autenticado = False
        st.session_state.utilizador_nome = ""
        st.session_state.utilizador_email = ""
        st.session_state.pagina_atual = "Página Inicial"
        st.session_state.modo_autenticacao = "login"
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.title("Navegação")
    
    opcoes_menu = ["Página Inicial", "Gestão de Literatura", "Territórios", "Limpeza do Salão", "Relatórios de Serviço de Campo"]
    if is_admin:
        opcoes_menu.append("Painel de Aprovações")

    if st.session_state.pagina_atual not in opcoes_menu:
        st.session_state.pagina_atual = "Página Inicial"

    menu_selecionado = st.sidebar.radio(
        "Ir para:",
        opcoes_menu,
        index=opcoes_menu.index(st.session_state.pagina_atual)
    )

    if menu_selecionado != st.session_state.pagina_atual:
        st.session_state.pagina_atual = menu_selecionado
        st.rerun()

    # --------------------------------------------------------------------------
    # 1. PÁGINA INICIAL
    # --------------------------------------------------------------------------
    if st.session_state.pagina_atual == "Página Inicial":
        st.title(f"Bem-vindo, {st.session_state.utilizador_nome}")
        st.caption("Clique no botão da secção correspondente para aceder ao respetivo módulo.")
        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown('<div class="card_home">', unsafe_allow_html=True)
            st.subheader("Gestão de Literatura")
            st.write("Encomendas de livros e controlo de receções.")
            pendentes_count = len(df_literatura[df_literatura["Recebido"] == False]) if not df_literatura.empty else 0
            st.caption(f"{pendentes_count} encomenda(s) pendente(s)")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Abrir Literatura", key="btn_lit", use_container_width=True, type="primary"):
                st.session_state.pagina_atual = "Gestão de Literatura"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="card_home">', unsafe_allow_html=True)
            st.subheader("Territórios")
            st.write("Gestão de mapas, fotos e ficheiros de territórios.")
            st.caption("Módulo ativo")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Abrir Territórios", key="btn_terr", use_container_width=True, type="primary"):
                st.session_state.pagina_atual = "Territórios"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col3:
            st.markdown('<div class="card_home">', unsafe_allow_html=True)
            st.subheader("Limpeza do Salão")
            st.write("Escalas de limpeza e registo de tarefas.")
            st.caption("Módulo ativo")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Abrir Limpeza", key="btn_limp", use_container_width=True, type="primary"):
                st.session_state.pagina_atual = "Limpeza do Salão"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col4:
            st.markdown('<div class="card_home">', unsafe_allow_html=True)
            st.subheader("Relatórios de Serviço")
            st.write("Registo mensal de relatórios de serviço de campo.")
            st.caption("Módulo ativo")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Abrir Relatórios", key="btn_rel", use_container_width=True, type="primary"):
                st.session_state.pagina_atual = "Relatórios de Serviço de Campo"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 2. TERRITÓRIOS
    # --------------------------------------------------------------------------
    elif st.session_state.pagina_atual == "Territórios":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()

        st.title("Gestão de Territórios")

        tab_ver_terr, tab_add_terr = st.tabs(["Consultar Territórios", "Adicionar / Carregar Ficheiro"])

        with tab_ver_terr:
            st.subheader("Mapas e Ficheiros de Territórios")
            lista_territorios = carregar_territorios()

            if lista_territorios:
                for terr in lista_territorios:
                    t_id, t_num, t_nome, t_obs, f_nome, f_tipo, f_bytes = terr
                    
                    with st.expander(f"Território Nº {t_num} - {t_nome}", expanded=False):
                        if t_obs:
                            st.write(f"**Observações:** {t_obs}")

                        if f_bytes:
                            st.markdown("---")
                            if f_tipo and "image" in f_tipo:
                                st.image(f_bytes, caption=f_nome, use_container_width=True)
                            
                            st.download_button(
                                label=f"Descarregar Ficheiro ({f_nome})",
                                data=bytes(f_bytes),
                                file_name=f_nome,
                                mime=f_tipo,
                                key=f"dl_{t_id}"
                            )
                        else:
                            st.caption("Sem ficheiro anexado.")
            else:
                st.info("Ainda não existem territórios registados.")

        with tab_add_terr:
            st.subheader("Adicionar Novo Território")
            
            with st.form("form_territorio", clear_on_submit=True):
                c_num, c_nome = st.columns([1, 2])
                num_terr = c_num.text_input("Nº do Território", placeholder="Ex: 05")
                nome_area = c_nome.text_input("Nome / Área", placeholder="Ex: Centro da Cidade / Bairro Sol")
                
                obs_terr = st.text_area("Notas / Observações", placeholder="Ex: Terreno inclinado, cães na rua principal...")
                
                ficheiro_terr = st.file_uploader(
                    "Carregar Foto ou Ficheiro (PNG, JPG, JPEG, PDF)", 
                    type=["png", "jpg", "jpeg", "pdf", "webp"]
                )

                btn_guardar_terr = st.form_submit_button("Guardar Território", type="primary", use_container_width=True)

                if btn_guardar_terr:
                    if num_terr and nome_area:
                        sucesso, msg = guardar_territorio(num_terr, nome_area, obs_terr, ficheiro_terr)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Por favor preencha o número do território e o nome da área.")

    # --------------------------------------------------------------------------
    # 3. PAINEL DE APROVAÇÕES (ADMINISTRADOR)
    # --------------------------------------------------------------------------
    elif st.session_state.pagina_atual == "Painel de Aprovações" and is_admin:
        st.title("Painel de Aprovação de Utilizadores")
        st.caption("Verifique os dados dos novos utilizadores e aprove ou recuse o acesso.")

        df_pendentes = carregar_utilizadores_pendentes()

        if not df_pendentes.empty:
            st.subheader(f"Pedidos Pendentes ({len(df_pendentes)})")
            
            for index, row in df_pendentes.iterrows():
                with st.container():
                    col_info, col_btn1, col_btn2 = st.columns([3, 1, 1])
                    
                    with col_info:
                        st.write(f"**{row['nome']}** ({row['idade']} anos)")
                        st.write(f"Congregação: **{row['congregacao']}** | E-mail: `{row['email']}`")
                        st.caption(f"Data do Registo: {row['data_registro']}")

                    with col_btn1:
                        if st.button("Aprovar", key=f"ap_btn_{row['id']}", use_container_width=True, type="primary"):
                            alterar_status_utilizador(row['id'], aprovar=True)
                            st.toast(f"Utilizador {row['nome']} aprovado!")
                            st.rerun()

                    with col_btn2:
                        if st.button("Recusar", key=f"rec_btn_{row['id']}", use_container_width=True):
                            alterar_status_utilizador(row['id'], aprovar=False)
                            st.toast(f"Pedido de {row['nome']} recusado.")
                            st.rerun()
                    st.markdown("---")
        else:
            st.success("Não há registos pendentes de aprovação neste momento.")

    # --------------------------------------------------------------------------
    # 4. GESTÃO DE LITERATURA
    # --------------------------------------------------------------------------
    elif st.session_state.pagina_atual == "Gestão de Literatura":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()

        st.title("Gestão de Literatura")

        aba1, aba2, aba3 = st.tabs([
            "Nova Encomenda", 
            "Tabela e Histórico", 
            "Gestão e Eliminação"
        ])

        with aba1:
            st.subheader("Registar Novo Pedido")
            st.caption("Preencha as informações da nova encomenda abaixo.")

            with st.form("form_encomenda", clear_on_submit=True):
                c1, c2 = st.columns([2, 1])
                nome_livro = c1.text_input("Nome do Livro", placeholder="Ex: O Principezinho")
                numero_pedido = c2.text_input("Nº do Pedido", placeholder="Ex: PED-2024-001")

                c3, c4 = st.columns([2, 1])
                requerente = c3.text_input("Requerente", placeholder="Ex: Maria Silva")
                data_pedido = c4.date_input("Data do Pedido", value=datetime.now())

                st.markdown("---")
                submetido = st.form_submit_button("Guardar Encomenda", type="primary", use_container_width=True)

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
                            st.toast(f"Encomenda '{nome_livro}' registada com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao guardar: {e}")
                    else:
                        st.warning("Por favor preencha todos os campos obrigatórios.")

        with aba2:
            st.subheader("Histórico Completo de Encomendas")

            if not df_literatura.empty:
                with st.expander("Marcar Encomenda como Recebida", expanded=True):
                    st.caption("Selecione uma encomenda pendente para atualizar o seu estado.")
                    
                    df_pendentes = df_literatura[df_literatura["Recebido"] == False].copy()
                    
                    if not df_pendentes.empty:
                        col_rec1, col_rec2 = st.columns([3, 1])
                        df_pendentes["label"] = df_pendentes["ID"].astype(str) + " - " + df_pendentes["Nome do Livro"].astype(str) + " (" + df_pendentes["Requerente"].astype(str) + ")"
                        
                        encomenda_sel = col_rec1.selectbox("Encomendas Pendentes:", options=df_pendentes["label"].tolist())
                        btn_marcar_recebido = col_rec2.button("Confirmar Recebimento", type="primary", use_container_width=True)
                        
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
                                st.success(f"Encomenda registada como recebida em {data_hora_atual}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar estado: {e}")
                    else:
                        st.info("Todas as encomendas registadas já foram recebidas.")

                st.markdown("---")

                col_f1, col_f2, col_f3 = st.columns(3)
                filtro_livro = col_f1.text_input("Filtrar por Livro:")
                filtro_requerente = col_f2.text_input("Filtrar por Requerente:")
                filtro_status = col_f3.selectbox("Estado:", ["Todos", "Recebidos", "Pendentes"])

                df_filtrado = df_literatura.copy()
                if filtro_livro:
                    df_filtrado = df_filtrado[df_filtrado["Nome do Livro"].astype(str).str.contains(filtro_livro, case=False, na=False)]
                if filtro_requerente:
                    df_filtrado = df_filtrado[df_filtrado["Requerente"].astype(str).str.contains(filtro_requerente, case=False, na=False)]
                if filtro_status == "Recebidos":
                    df_filtrado = df_filtrado[df_filtrado["Recebido"] == True]
                elif filtro_status == "Pendentes":
                    df_filtrado = df_filtrado[df_filtrado["Recebido"] == False]

                m1, m2, m3 = st.columns(3)
                m1.metric("Total Exibido", len(df_filtrado))
                m2.metric("Recebidos", len(df_filtrado[df_filtrado["Recebido"] == True]))
                m3.metric("Pendentes", len(df_filtrado[df_filtrado["Recebido"] == False]))

                st.markdown("---")
                df_filtrado["Data/Hora de Recebimento"] = df_filtrado["Data/Hora de Recebimento"].fillna("Pendente")

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

        with aba3:
            st.subheader("Eliminar Encomenda Registada")

            if not df_literatura.empty:
                st.caption("Selecione a encomenda que pretende remover permanentemente.")
                df_literatura["display_label"] = df_literatura["ID"].astype(str) + " - " + df_literatura["Nome do Livro"].astype(str) + " (" + df_literatura["Requerente"].astype(str) + ")"
                
                col_del1, col_del2 = st.columns([3, 1])
                opcao_selecionada = col_del1.selectbox("Selecionar encomenda:", options=df_literatura["display_label"].tolist())
                
                id_para_eliminar = int(opcao_selecionada.split(" - ")[0])
                btn_eliminar = col_del2.button("Eliminar Encomenda", type="primary", use_container_width=True)

                if btn_eliminar:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM encomendas WHERE id = %s", (id_para_eliminar,))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success("Encomenda removida com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao eliminar encomenda: {e}")
            else:
                st.info("Não há registos disponíveis para eliminar.")

    # --------------------------------------------------------------------------
    # 5. LIMPEZA DO SALÃO
    # --------------------------------------------------------------------------
    elif st.session_state.pagina_atual == "Limpeza do Salão":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()

        st.title("Limpeza do Salão")

        aba_limp1, aba_limp2 = st.tabs(["Escala de Limpeza", "Registo de Limpeza"])

        with aba_limp1:
            st.subheader("Escala de Limpeza")
            st.info("Consulte ou defina os grupos responsáveis pela limpeza do salão esta semana.")

        with aba_limp2:
            st.subheader("Registar Limpeza Concluída")
            with st.form("form_limpeza"):
                grupo = st.selectbox("Grupo Responsável:", ["Grupo 1", "Grupo 2", "Grupo 3", "Grupo 4"])
                data_limpeza = st.date_input("Data da Limpeza:", value=datetime.now())
                observacoes = st.text_area("Observações / Necessidades de Material:")
                btn_salvar_limpeza = st.form_submit_button("Guardar Registo", type="primary")

    # --------------------------------------------------------------------------
    # 6. RELATÓRIOS DE SERVIÇO DE CAMPO
    # --------------------------------------------------------------------------
    elif st.session_state.pagina_atual == "Relatórios de Serviço de Campo":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()

        st.title("Relatórios de Serviço de Campo")

        aba_rel1, aba_rel2 = st.tabs(["Entregar Relatório", "Resumo Mensal"])

        with aba_rel1:
            st.subheader("Novo Relatório Mensal")
            with st.form("form_relatorio", clear_on_submit=True):
                nome_publicador = st.text_input("Nome do Publicador", value=st.session_state.utilizador_nome)
                mes_ano = st.date_input("Mês de Referência", value=datetime.now())
                
                c1, c2, c3 = st.columns(3)
                publicacoes = c1.number_input("Publicações", min_value=0, step=1)
                videos = c2.number_input("Vídeos Mostrados", min_value=0, step=1)
                horas = c3.number_input("Horas", min_value=0, step=1)

                c4, c5 = st.columns(2)
                revisitas = c4.number_input("Revisitas", min_value=0, step=1)
                estudos = c5.number_input("Estudos Bíblicos", min_value=0, step=1)

                btn_relatorio = st.form_submit_button("Submeter Relatório", type="primary", use_container_width=True)

        with aba_rel2:
            st.subheader("Resumo do Mês")
            st.info("Aqui serão apresentados os totais acumulados de horas e publicações do mês.")