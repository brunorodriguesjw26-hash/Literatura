from datetime import datetime, date
import calendar
import hashlib
import re
import pandas as pd
import psycopg2
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Painel de Gestão", layout="wide"
)

# E-mail principal definido como Administrador Principal fixo
EMAIL_ADMINISTRADOR = "brunorodriguesj26@gmail.com"

# Estilo CSS ajustado
st.markdown("""
    <style>
    .st-key-card_home > div {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.05);
        height: 100%;
    }

    .login-container-box {
        background-color: #4A2574;       
        border: 2px solid #ffffff;       
        border-radius: 12px;             
        padding: 30px;
        box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.2);
    }

    .login-container-box div[data-testid="stColumn"] {
        background-color: transparent !important;
    }
    
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

def get_connection():
    return psycopg2.connect(DB_URL)

def criar_tabelas():
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
            data_recebimento VARCHAR(50),
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilizadores (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            congregacao VARCHAR(100),
            idade INT,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            aprovado BOOLEAN DEFAULT FALSE,
            is_admin BOOLEAN DEFAULT FALSE,
            acesso_literatura BOOLEAN DEFAULT FALSE,
            acesso_territorios BOOLEAN DEFAULT FALSE,
            acesso_limpeza BOOLEAN DEFAULT FALSE,
            acesso_relatorios BOOLEAN DEFAULT FALSE,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

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

        # Tabela de Relatórios Diários simplificada (com quem pregou, horas, estudos)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS relatorios_diarios (
            id SERIAL PRIMARY KEY,
            email_utilizador VARCHAR(100) NOT NULL,
            nome_publicador VARCHAR(100) NOT NULL,
            data_pregação DATE NOT NULL,
            com_quem TEXT,
            horas INT DEFAULT 0,
            estudos INT DEFAULT 0,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS congregacao VARCHAR(100);")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS idade INT;")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS aprovado BOOLEAN DEFAULT FALSE;")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS acesso_literatura BOOLEAN DEFAULT FALSE;")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS acesso_territorios BOOLEAN DEFAULT FALSE;")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS acesso_limpeza BOOLEAN DEFAULT FALSE;")
        cursor.execute("ALTER TABLE utilizadores ADD COLUMN IF NOT EXISTS acesso_relatorios BOOLEAN DEFAULT FALSE;")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao ligar à base de dados: {e}")

criar_tabelas()

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
        
        is_admin_principal = (email_clean == EMAIL_ADMINISTRADOR.lower())
        
        cursor.execute(
            """
            INSERT INTO utilizadores (nome, congregacao, idade, email, password_hash, aprovado, is_admin, acesso_literatura, acesso_territorios, acesso_limpeza, acesso_relatorios) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (nome, congregacao, idade, email_clean, hash_pw, is_admin_principal, is_admin_principal, is_admin_principal, is_admin_principal, is_admin_principal, is_admin_principal)
        )
        conn.commit()
        cursor.close()
        conn.close()
        if is_admin_principal:
            return True, "Conta Administrador principal criada com sucesso! Pode entrar."
        return True, "Registo efetuado com sucesso! Aguarde que o administrador aprove a sua conta e atribua acessos."
    except psycopg2.IntegrityError:
        return False, "Este e-mail já se encontra registado."
    except Exception as e:
        return False, f"Erro ao criar utilizador: {e}"

def autenticar_utilizador(email, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nome, password_hash, aprovado, email, is_admin, acesso_literatura, acesso_territorios, acesso_limpeza, acesso_relatorios FROM utilizadores WHERE LOWER(email) = %s", 
            (email.lower().strip(),)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            user_id, nome, hash_pw, aprovado, user_email, is_admin, lit, terr, limp, rel = user
            if verificar_password(password, hash_pw):
                if not aprovado and user_email.lower() != EMAIL_ADMINISTRADOR.lower():
                    return False, "PENDENTE", "A sua conta ainda aguarda aprovação pelo administrador."
                
                if user_email.lower() == EMAIL_ADMINISTRADOR.lower():
                    is_admin = True
                    lit = terr = limp = rel = True

                return True, "OK", {
                    "id": user_id, 
                    "nome": nome, 
                    "email": user_email, 
                    "is_admin": is_admin,
                    "acessos": {
                        "Literatura": lit,
                        "Territórios": terr,
                        "Limpeza do Salão": limp,
                        "Relatórios de Serviço de Campo": rel
                    }
                }
        return False, "ERRO", "E-mail ou palavra-passe incorretos."
    except Exception as e:
        return False, "ERRO", f"Erro na autenticação: {e}"

def carregar_utilizadores_sistema():
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT id, nome, congregacao, idade, email, aprovado, is_admin, acesso_literatura, acesso_territorios, acesso_limpeza, acesso_relatorios, data_registro FROM utilizadores ORDER BY id DESC", 
            conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def atualizar_permissoes_utilizador(user_id, aprovado, is_admin, lit, terr, limp, rel):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE utilizadores 
            SET aprovado = %s, is_admin = %s, acesso_literatura = %s, acesso_territorios = %s, acesso_limpeza = %s, acesso_relatorios = %s 
            WHERE id = %s
            """,
            (aprovado, is_admin, lit, terr, limp, rel, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception:
        return False

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
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "acessos" not in st.session_state:
    st.session_state.acessos = {}
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "Página Inicial"
if "modo_autenticacao" not in st.session_state:
    st.session_state.modo_autenticacao = "login"

# ECRÃ DE LOGIN E REGISTO
if not st.session_state.autenticado:
    col_left, col_centered, col_right = st.columns([1, 2, 1])
    
    with col_centered:
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
                btn_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)

                if btn_login:
                    if email and password:
                        sucesso, status, resultado = autenticar_utilizador(email, password)
                        if sucesso:
                            st.session_state.autenticado = True
                            st.session_state.utilizador_nome = resultado["nome"]
                            st.session_state.utilizador_email = resultado["email"]
                            st.session_state.is_admin = resultado["is_admin"]
                            st.session_state.acessos = resultado["acessos"]
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
                nova_password = st.text_input("Palavra-passe", type="password")
                
                st.caption("Requisitos: Mínimo 14 caracteres, 1 maiúscula, 1 número e 1 símbolo especial.")
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
                        st.warning("Preencha todos os campos obrigatórios.")
        
        st.markdown('</div>', unsafe_allow_html=True)

else:
    df_literatura = carregar_dados_literatura()
    is_admin = st.session_state.is_admin or (st.session_state.utilizador_email.lower() == EMAIL_ADMINISTRADOR.lower())

    st.sidebar.title("Sessão Ativa")
    st.sidebar.caption(f"Utilizador: **{st.session_state.utilizador_nome}**")
    if is_admin:
        st.sidebar.caption("**Administrador**")
    
    if st.sidebar.button("Terminar Sessão", type="secondary"):
        st.session_state.autenticado = False
        st.session_state.utilizador_nome = ""
        st.session_state.utilizador_email = ""
        st.session_state.is_admin = False
        st.session_state.acessos = {}
        st.session_state.pagina_atual = "Página Inicial"
        st.session_state.modo_autenticacao = "login"
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.title("Navegação")
    
    opcoes_menu = ["Página Inicial"]
    acessos = st.session_state.acessos
    if is_admin or acessos.get("Literatura", False):
        opcoes_menu.append("Gestão de Literatura")
    if is_admin or acessos.get("Territórios", False):
        opcoes_menu.append("Territórios")
    if is_admin or acessos.get("Limpeza do Salão", False):
        opcoes_menu.append("Limpeza do Salão")
    if is_admin or acessos.get("Relatórios de Serviço de Campo", False):
        opcoes_menu.append("Relatórios de Serviço de Campo")
    if is_admin:
        opcoes_menu.append("Painel de Administração e Acessos")

    if st.session_state.pagina_atual not in opcoes_menu:
        st.session_state.pagina_atual = "Página Inicial"

    menu_selecionado = st.sidebar.radio("Ir para:", opcoes_menu, index=opcoes_menu.index(st.session_state.pagina_atual))

    if menu_selecionado != st.session_state.pagina_atual:
        st.session_state.pagina_atual = menu_selecionado
        st.rerun()

    # PÁGINA INICIAL
    if st.session_state.pagina_atual == "Página Inicial":
        st.title(f"Bem-vindo, {st.session_state.utilizador_nome}")
        st.caption("Módulos disponíveis:")
        st.markdown("---")

        colunas = st.columns(4)
        todos_cartoes = [
            ("Literatura", "Gestão de Literatura", "btn_lit", is_admin or acessos.get("Literatura", False)),
            ("Territórios", "Territórios", "btn_terr", is_admin or acessos.get("Territórios", False)),
            ("Limpeza do Salão", "Limpeza do Salão", "btn_limp", is_admin or acessos.get("Limpeza do Salão", False)),
            ("Relatórios de Serviço", "Relatórios de Serviço de Campo", "btn_rel", is_admin or acessos.get("Relatórios de Serviço de Campo", False))
        ]

        for i, (titulo_cartao, destino, chave_btn, tem_acesso) in enumerate(todos_cartoes):
            with colunas[i]:
                st.markdown('<div class="card_home">', unsafe_allow_html=True)
                st.subheader(titulo_cartao)
                st.markdown("<br><br>", unsafe_allow_html=True)
                if tem_acesso:
                    if st.button(f"Abrir", key=chave_btn, use_container_width=True, type="primary"):
                        st.session_state.pagina_atual = destino
                        st.rerun()
                else:
                    st.caption("Acesso não atribuído")
                st.markdown('</div>', unsafe_allow_html=True)

    # TERRITÓRIOS
    elif st.session_state.pagina_atual == "Territórios":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()

        st.title("Gestão de Territórios")
        tab_ver_terr, tab_add_terr = st.tabs(["Consultar Territórios", "Adicionar / Carregar Ficheiro"])

        with tab_ver_terr:
            lista_territorios = carregar_territorios()
            if lista_territorios:
                for terr in lista_territorios:
                    t_id, t_num, t_nome, t_obs, f_nome, f_tipo, f_bytes = terr
                    with st.expander(f"Território Nº {t_num} - {t_nome}", expanded=False):
                        if t_obs: st.write(f"**Observações:** {t_obs}")
                        if f_bytes:
                            if f_tipo and "image" in f_tipo:
                                st.image(f_bytes, caption=f_nome, use_container_width=True)
                            st.download_button(label=f"Descarregar Ficheiro ({f_nome})", data=bytes(f_bytes), file_name=f_nome, mime=f_tipo, key=f"dl_{t_id}")
            else:
                st.info("Ainda não existem territórios registados.")

        with tab_add_terr:
            with st.form("form_territorio", clear_on_submit=True):
                c_num, c_nome = st.columns([1, 2])
                num_terr = c_num.text_input("Nº do Território")
                nome_area = c_nome.text_input("Nome / Área")
                obs_terr = st.text_area("Notas / Observações")
                ficheiro_terr = st.file_uploader("Carregar Foto ou Ficheiro", type=["png", "jpg", "jpeg", "pdf", "webp"])
                if st.form_submit_button("Guardar Território", type="primary", use_container_width=True):
                    if num_terr and nome_area:
                        sucesso, msg = guardar_territorio(num_terr, nome_area, obs_terr, ficheiro_terr)
                        if sucesso: st.success(msg); st.rerun()
                        else: st.error(msg)
                    else: st.warning("Preencha o número e nome da área.")

    # PAINEL DE ADMINISTRAÇÃO
    elif st.session_state.pagina_atual == "Painel de Administração e Acessos" and is_admin:
        st.title("Painel de Controlo de Utilizadores e Acessos")
        df_users = carregar_utilizadores_sistema()
        if not df_users.empty:
            for index, row in df_users.iterrows():
                with st.expander(f"{row['nome']} ({row['email']})", expanded=False):
                    with st.form(f"form_user_{row['id']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            novo_aprovado = st.checkbox("Conta Aprovada", value=bool(row['aprovado']), key=f"ap_{row['id']}")
                            novo_admin = st.checkbox("Administrador", value=bool(row['is_admin']), key=f"adm_{row['id']}")
                        with col2:
                            acc_lit = st.checkbox("Literatura", value=bool(row['acesso_literatura']), key=f"lit_{row['id']}")
                            acc_terr = st.checkbox("Territórios", value=bool(row['acesso_territorios']), key=f"terr_{row['id']}")
                            acc_limp = st.checkbox("Limpeza", value=bool(row['acesso_limpeza']), key=f"limp_{row['id']}")
                            acc_rel = st.checkbox("Relatórios", value=bool(row['acesso_relatorios']), key=f"rel_{row['id']}")
                        if st.form_submit_button("Guardar Alterações", type="primary"):
                            atualizar_permissoes_utilizador(row['id'], novo_aprovado, novo_admin, acc_lit, acc_terr, acc_limp, acc_rel)
                            st.success("Atualizado!")
                            st.rerun()

    # GESTÃO DE LITERATURA
    elif st.session_state.pagina_atual == "Gestão de Literatura":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()
        st.title("Gestão de Literatura")
        aba1, aba2, aba3 = st.tabs(["Nova Encomenda", "Tabela e Histórico", "Eliminar"])
        with aba1:
            with st.form("form_encomenda", clear_on_submit=True):
                c1, c2 = st.columns([2, 1])
                nome_livro = c1.text_input("Nome do Livro")
                numero_pedido = c2.text_input("Nº do Pedido")
                requerente = st.text_input("Requerente")
                data_pedido = st.date_input("Data do Pedido", value=datetime.now())
                if st.form_submit_button("Guardar Encomenda", type="primary", use_container_width=True):
                    if nome_livro and requerente:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO encomendas (numero_pedido, nome_livro, requerente, data_pedido, recebido) VALUES (%s, %s, %s, %s, FALSE)", (numero_pedido, nome_livro, requerente, data_pedido))
                        conn.commit(); cursor.close(); conn.close()
                        st.success("Guardado!")
        with aba2:
            if not df_literatura.empty:
                st.dataframe(df_literatura, use_container_width=True, hide_index=True)
            else:
                st.info("Sem encomendas.")
        with aba3:
            if not df_literatura.empty:
                df_literatura["label"] = df_literatura["ID"].astype(str) + " - " + df_literatura["Nome do Livro"]
                sel_enc = st.selectbox("Encomenda:", df_literatura["label"].tolist())
                if st.button("Eliminar", type="primary"):
                    id_del = int(sel_enc.split(" - ")[0])
                    conn = get_connection(); cursor = conn.cursor()
                    cursor.execute("DELETE FROM encomendas WHERE id = %s", (id_del,))
                    conn.commit(); cursor.close(); conn.close()
                    st.success("Eliminado!"); st.rerun()

    # LIMPEZA DO SALÃO
    elif st.session_state.pagina_atual == "Limpeza do Salão":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()
        st.title("Limpeza do Salão")
        st.info("Escala e registo de limpeza.")

    # RELATÓRIOS DE SERVIÇO DE CAMPO (CALENDÁRIO + RESUMO MENSAL + RESUMO ANUAL)
    elif st.session_state.pagina_atual == "Relatórios de Serviço de Campo":
        if st.button("Voltar ao Painel Principal"):
            st.session_state.pagina_atual = "Página Inicial"
            st.rerun()

        st.title("Relatórios de Serviço de Campo")

        aba_rel1, aba_rel2, aba_rel3 = st.tabs(["Calendário Diário", "Resumo Mensal", "Resumo Anual (Set - Ago)"])

        # ABAS 1: CALENDÁRIO DIÁRIO IMEDIATO DO MÊS ATUAL
        with aba_rel1:
            st.subheader(f"Calendário Diário — {datetime.now().strftime('%B de %Y').capitalize()}")
            st.caption("Selecione um dia do mês atual para adicionar ou atualizar os seus detalhes de pregação.")

            hoje = date.today()
            ano_atual = hoje.year
            mes_atual = hoje.month

            num_dias_mes = calendar.monthrange(ano_atual, mes_atual)[1]
            dias_opcoes = [date(ano_atual, mes_atual, d) for d in range(1, num_dias_mes + 1)]

            with st.form("form_calendario_diario"):
                dia_escolhido = st.selectbox(
                    "Escolha o Dia do Mês",
                    options=dias_opcoes,
                    format_func=lambda x: x.strftime("%d/%m/%Y (%A)")
                )

                com_quem = st.text_input("Com quem pregou?", placeholder="Ex: João Silva")
                
                col_h, col_e = st.columns(2)
                horas = col_h.number_input("Horas", min_value=0, value=0, step=1)
                estudos = col_e.number_input("Estudos Bíblicos", min_value=0, value=0, step=1)

                btn_guardar_apontamento = st.form_submit_button("Guardar / Atualizar Dia", type="primary", use_container_width=True)

                if btn_guardar_apontamento:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT id FROM relatorios_diarios WHERE LOWER(email_utilizador) = %s AND data_pregação = %s",
                            (st.session_state.utilizador_email.lower(), dia_escolhido)
                        )
                        registo_existente = cursor.fetchone()

                        if registo_existente:
                            cursor.execute(
                                """
                                UPDATE relatorios_diarios 
                                SET com_quem = %s, horas = %s, estudios = %s 
                                WHERE id = %s
                                """,
                                (com_quem, horas, estudos, registo_existente[0])
                            )
                            msg_ret = "Apontamento do dia atualizado com sucesso!"
                        else:
                            cursor.execute(
                                """
                                INSERT INTO relatorios_diarios (email_utilizador, nome_publicador, data_pregação, com_quem, horas, estudios)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                """,
                                (st.session_state.utilizador_email.lower(), st.session_state.utilizador_nome, dia_escolhido, com_quem, horas, estudos)
                            )
                            msg_ret = "Apontamento do dia guardado com sucesso!"

                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.success(msg_ret)
                    except Exception as e:
                        st.error(f"Erro ao guardar: {e}")

            st.markdown("---")
            st.subheader("Os seus registos deste mês")
            try:
                conn = get_connection()
                if is_admin:
                    q_mes = "SELECT id, nome_publicador, data_pregação, com_quem, horas, estudios FROM relatorios_diarios WHERE EXTRACT(MONTH FROM data_pregação) = %s AND EXTRACT(YEAR FROM data_pregação) = %s ORDER BY data_pregação DESC"
                    df_mes_atual = pd.read_sql_query(q_mes, conn, params=(mes_atual, ano_atual))
                else:
                    q_mes = "SELECT id, nome_publicador, data_pregação, com_quem, horas, estudios FROM relatorios_diarios WHERE LOWER(email_utilizador) = %s AND EXTRACT(MONTH FROM data_pregação) = %s AND EXTRACT(YEAR FROM data_pregação) = %s ORDER BY data_pregação DESC"
                    df_mes_atual = pd.read_sql_query(q_mes, conn, params=(st.session_state.utilizador_email.lower(), mes_atual, ano_atual))
                conn.close()

                if not df_mes_atual.empty:
                    st.dataframe(df_mes_atual, use_container_width=True, hide_index=True)
                else:
                    st.info("Ainda não tem apontamentos para este mês.")
            except Exception as e:
                st.error(f"Erro ao carregar dados do mês: {e}")

        # ABA 2: RESUMO MENSAL
        with aba_rel2:
            st.subheader("Resumo Mensal Consolidado")
            st.caption("Visão agregada de todos os meses em que foram submetidos relatórios.")

            try:
                conn = get_connection()
                if is_admin:
                    q_geral = "SELECT data_pregação, horas, estudios, nome_publicador FROM relatorios_diarios"
                    df_all = pd.read_sql_query(q_geral, conn)
                else:
                    q_geral = "SELECT data_pregação, horas, estudios, nome_publicador FROM relatorios_diarios WHERE LOWER(email_utilizador) = %s"
                    df_all = pd.read_sql_query(q_geral, conn, params=(st.session_state.utilizador_email.lower(),))
                conn.close()

                if not df_all.empty:
                    df_all["data_pregação"] = pd.to_datetime(df_all["data_pregação"])
                    df_all["Mes_Ano"] = df_all["data_pregação"].dt.to_period("M").astype(str)

                    df_resumo_mensal = df_all.groupby("Mes_Ano")[["horas", "estudos"]].sum().reset_index()
                    df_resumo_mensal = df_resumo_mensal.sort_values("Mes_Ano", ascending=False)

                    st.dataframe(df_resumo_mensal, use_container_width=True, hide_index=True)
                else:
                    st.info("Ainda não existem dados para gerar o resumo mensal.")
            except Exception as e:
                st.error(f"Erro ao gerar resumo mensal: {e}")

        # ABA 3: RESUMO ANUAL (Setembro a Agosto)
        with aba_rel3:
            st.subheader("Resumo Anual de Serviço (Setembro a Agosto)")
            st.caption("Ano de Serviço organizado oficialmente de Setembro do ano anterior até Agosto do ano corrente.")

            try:
                conn = get_connection()
                if is_admin:
                    df_anual = pd.read_sql_query("SELECT data_pregação, horas, estudios FROM relatorios_diarios", conn)
                else:
                    df_anual = pd.read_sql_query("SELECT data_pregação, horas, estudios FROM relatorios_diarios WHERE LOWER(email_utilizador) = %s", conn, params=(st.session_state.utilizador_email.lower(),))
                conn.close()

                if not df_anual.empty:
                    df_anual["data_pregação"] = pd.to_datetime(df_anual["data_pregação"])

                    def obter_ano_servico(dt):
                        if dt.month >= 9:
                            return f"{dt.year}/{dt.year + 1}"
                        else:
                            return f"{dt.year - 1}/{dt.year}"

                    df_anual["Ano_Serviço"] = df_anual["data_pregação"].apply(obter_ano_servico)
                    
                    df_agrupado_anual = df_anual.groupby("Ano_Serviço")[["horas", "estudos"]].sum().reset_index()
                    df_agrupado_anual = df_agrupado_anual.sort_values("Ano_Serviço")

                    st.markdown("### 1. Tabela e Gráfico de Horas por Ano de Serviço")
                    df_horas = df_agrupado_anual[["Ano_Serviço", "horas"]].set_index("Ano_Serviço")
                    st.dataframe(df_horas, use_container_width=True)
                    st.bar_chart(df_horas)

                    st.markdown("---")
                    st.markdown("### 2. Tabela e Gráfico de Estudos Bíblicos por Ano de Serviço")
                    df_estudos = df_agrupado_anual[["Ano_Serviço", "estudos"]].set_index("Ano_Serviço")
                    st.dataframe(df_estudos, use_container_width=True)
                    st.bar_chart(df_estudos)
                else:
                    st.info("Sem dados suficientes para o resumo anual.")
            except Exception as e:
                st.error(f"Erro ao gerar resumo anual: {e}")