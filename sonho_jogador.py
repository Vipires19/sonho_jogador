import streamlit as st
from pymongo import MongoClient
import bcrypt
import pandas as pd
import urllib.parse
import streamlit_authenticator as stauth

MONGO_USER = urllib.parse.quote_plus(st.secrets['MONGO_USER'])
MONGO_PASS = urllib.parse.quote_plus(st.secrets['MONGO_PASS'])
MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASS}@cluster0.gjkin5a.mongodb.net/personalAI?retryWrites=true&w=majority&appName=Cluster0"

# Layout
layout = st.query_params.get("layout", "centered")
if layout not in ["wide", "centered"]:
    layout = "centered"

st.set_page_config(page_title="DOMINGOU FC", layout=layout)

with st.sidebar:
    st.write(f"Layout atual: **{layout.upper()}**")
    if layout == "centered":
        if st.button("🖥️ Versão Desktop"):
            st.markdown(
                '<meta http-equiv="refresh" content="0; URL=/?layout=wide">',
                unsafe_allow_html=True
            )
    else:
        if st.button("📱 Versão Mobile"):
            st.markdown(
                '<meta http-equiv="refresh" content="0; URL=/?layout=centered">',
                unsafe_allow_html=True
            )

# MongoDB Connection
client = MongoClient("mongodb+srv://%s:%s@cluster0.gjkin5a.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" % (MONGO_USER, MONGO_PASS))
db = client.campeonato_quadra
coll_users = db.usuarios
coll_jogadores = db.jogadores
coll_resultados = db.resultados
coll_champion = db.champion


# Autenticação Usuário
users = list(coll_users.find({}, {'_id': 0}))
credentials = {
    'usernames': {
        u['username']: {
            'name': u['name'],
            'password': u['password'][0]
        } for u in users
    }
}
authenticator = stauth.Authenticate(credentials, 'cookie', 'key123', cookie_expiry_days=1)
authenticator.login()


# Funções MongoDB
    
def adicionar_usuario(name, username, password, role="jogador"):
    hashed_passwords = stauth.Hasher([password]).generate()
    if coll_users.find_one({"username": username}):
        return False
    
    new_user = {
    "name": name,
    "username": username,
    "password":hashed_passwords,
    "role": role}

    coll_users.insert_one(new_user)
    return True

def listar_jogadores():
    jogadores = list(coll_jogadores.find({}, {"_id": 0}))
    return pd.DataFrame(jogadores)

def atualizar_resultado(jogador, vitorias, empates, derrotas, extras):
    pontos = vitorias * 3 + empates + extras
    coll_jogadores.update_one(
        {"nome": jogador},
        {"$set": {
            "vitorias": vitorias,
            "empates": empates,
            "derrotas": derrotas,
            "extra": extras,
            "pontos": pontos
        }}
    )

def criar_jogador(nome):
    if not coll_jogadores.find_one({"nome": nome}):
        coll_jogadores.insert_one({
            "nome": nome,
            "pontos": 0,
            "vitorias": 0,
            "empates": 0,
            "extra": 0,
            "derrotas": 0
        })
        return True
    return False

def show_admin_dashboard():
    # Inicializa o estado da página se não estiver presente
    if "pagina_atual" not in st.session_state:
        st.session_state["pagina_atual"] = "home"

    # Sidebar de navegação
    with st.sidebar:
        if authenticator.logout():
            st.session_state["authentication_status"] = None

        st.divider()

        if st.button("📖 Cadastro de jogadores"):
            st.session_state["pagina_atual"] = "cadastro"

        if st.button("👁️ Visualizar jogador"):
            st.session_state["pagina_atual"] = "visualiza"

        if st.button("📊 Placar"):
            st.session_state["pagina_atual"] = "placar"

        if st.button("📊 Atualizar Resultados"):
            st.session_state["pagina_atual"] = "resultados"

        if st.button("🏠 Voltar ao início"):
            st.session_state["pagina_atual"] = "home"

    # Conteúdo principal com base na seleção
    if st.session_state["pagina_atual"] == "home":
        st.title("🏆 DOMINGOU FC")
        st.header(f"Bem-vindo, {st.session_state['name']}")
        jogadores = listar_jogadores()
        total_jogadores = jogadores['nome'].value_counts().sum()
        st.metric('Jogadores', total_jogadores)
    
    if st.session_state["pagina_atual"] == "cadastro":
        st.title("📖 Cadastro de alunos")
        col1,col2 = st.columns(2)
        nome = col1.text_input('Nome do jogador')
        username = col2.text_input('Nome de usuário')
        password = col1.text_input('Senha', type='password')

        if st.button("Cadastrar jogador"):
            adicionar_usuario(nome, username, password)
            criar_jogador(nome)
            st.success("Jogador cadastrado com sucesso!")

        st.divider()
        champion = st.text_input('Nomear atual Campeão')
        if st.button("Atualizar campeão"):
            coll_champion.insert_one({'campeao': champion})
            st.success("Campeão atualizado com sucesso!")

    if st.session_state['pagina_atual'] == "visualiza":
        st.title("👁️ Visualizar jogadores")
        jogadores = listar_jogadores()
        jogadores.index = jogadores.index + 1
        jogadores.index.name = 'Posição'
        st.dataframe(jogadores)
        jogador = st.selectbox("Selecione o jogador", jogadores['nome'].tolist())
        col1,col2 = st.columns(2)
        col1.metric(label="Pontos", value=jogadores[jogadores['nome'] == jogador]['pontos'].values[0])
        col2.metric(label="Vitórias", value=jogadores[jogadores['nome'] == jogador]['vitorias'].values[0])
        col1.metric(label="Empates", value=jogadores[jogadores['nome'] == jogador]['empates'].values[0])
        col2.metric(label="Derrotas", value=jogadores[jogadores['nome'] == jogador]['derrotas'].values[0])
        col1.metric(label="Pts Extra", value=jogadores[jogadores['nome'] == jogador]['extra'].values[0])
        
    if st.session_state["pagina_atual"] == "placar":
        st.title("📊 Classificação")
        df = listar_jogadores()
        campeao = list(coll_champion.find({}, {"_id": 0}))
        campeoes = pd.DataFrame(campeao)
        # Ordena pelos pontos (decrescente)
        df = df.sort_values(by="pontos", ascending=False)

        # Ajusta o índice para começar de 1
        df.index = df.index + 1
        df.index.name = 'Posição'
        df.rename(columns={'nome': 'Jogador', 'pontos': 'Pontos', 'vitorias': 'Vitórias', 'empates': 'Empates', 'derrotas': 'Derrotas', 'extra': 'Extra'}, inplace=True)

        # Exibe a tabela
        st.dataframe(df)
        col1,col2,col3 = st.columns(3)
        col1.metric(label='🏆 Jogador com mais pontos', value=df['Jogador'].values[0], delta=f"{df['Pontos'].values[0]} pontos")
        if len(df[Jogador]) > 1:
            col2.metric(label='🏆 Segundo com mais pontos', value=df['Jogador'].values[1], delta=f"{df['Pontos'].values[1]} pontos",delta_color="inverse")
            col3.metric(label='🏆 Terceiro com mais pontos', value=df['Jogador'].values[2], delta=f"{df['Pontos'].values[2]} pontos",delta_color="inverse")
            st.metric("Último campeão:", campeoes['campeao'].values[0])
    
            st.divider()
            st.title("⚽ Resultado dos Jogos")
            jogos = list(coll_resultados.find({}, {"_id": 0}))
            jogo = pd.DataFrame(data= jogos, columns=['data', 'time1',  'resultado1', 'resultado2', 'time2'])
            jogo.rename(columns={'data':'Data do jogo', 'time1': 'Time A', 'time2': 'Time B', 'resultado1': 'Gols A', 'resultado2': 'Gols B'}, inplace=True)
            st.dataframe(jogo)

    if st.session_state["pagina_atual"] == "resultados":
        st.title("📝 Atualizar Resultados da Rodada")
        
        jogadores = listar_jogadores()

        # Cria dicionários para armazenar inputs temporários
        vitorias = {}
        empates = {}
        derrotas = {}
        extra = {}

        # Layout da tabela
        st.write("### 🏟️ Resultado da Rodada")
        cols = st.columns([3, 1, 1, 1,1])  # Ajusta largura das colunas
        cols[0].markdown("**Jogador**")
        cols[1].markdown("**Vitória (+3)**")
        cols[2].markdown("**Empate (+1)**")
        cols[3].markdown("**Derrota (+0)**")
        cols[4].markdown("**Extra (+1)**")

        for i, jogador in jogadores.iterrows():
            col_nome, col_vit, col_emp, col_der, col_extra = st.columns([3, 1, 1, 1, 1])

            col_nome.markdown(f"**{jogador['nome']}**")
            vitorias[jogador['nome']] = col_vit.number_input(
                label="Vitórias", value=jogador['vitorias'], step=1, key=f"vit_{jogador['nome']}"
            )
            empates[jogador['nome']] = col_emp.number_input(
                label="Empates", value=jogador['empates'], step=1, key=f"emp_{jogador['nome']}"
            )
            derrotas[jogador['nome']] = col_der.number_input(
                label="Derrotas", value=jogador['derrotas'], step=1, key=f"der_{jogador['nome']}"
            )
            extra[jogador['nome']] = col_extra.number_input(
                label="Pts extras", value=jogador['extra'], step=1, key=f"ex_{jogador['nome']}"
            )


        # Botão para atualizar todos os jogadores de uma vez
        if st.button("✅ Atualizar Resultados"):
            for nome in jogadores['nome']:
                v = vitorias[nome]
                e = empates[nome]
                d = derrotas[nome]
                ex = extra[nome]

                if v > 0 or e > 0 or d > 0:
                    atualizar_resultado(nome, v, e, d, ex)

            st.success("Resultados atualizados com sucesso!")

        st.divider()
        st.title("⚽ Jogos da Semana")

        # Inicializa os times na sessão se ainda não existem
        if 'time1' not in st.session_state:
            st.session_state.time1 = []
        if 'time2' not in st.session_state:
            st.session_state.time2 = []

        jogadores = listar_jogadores()  # Supondo que você já carregou os jogadores

        data = st.date_input("📅 Selecione a data do jogo")

        col1, col2 = st.columns(2)

        # Adicionar jogadores Time A
        jogador1 = col1.selectbox('👕 Jogador Time A', jogadores['nome'].tolist(), key='select_timeA')
        if col1.button("➕ Adicionar jogador ao Time A"):
            if jogador1 not in st.session_state.time1:
                st.session_state.time1.append(jogador1)

        # Adicionar jogadores Time B
        jogador2 = col2.selectbox('👕 Jogador Time B', jogadores['nome'].tolist(), key='select_timeB')
        if col2.button("➕ Adicionar jogador ao Time B"):
            if jogador2 not in st.session_state.time2:
                st.session_state.time2.append(jogador2)

        # Containers para mostrar os jogadores dos times
        container1 = col1.container()
        container2 = col2.container()

        container1.subheader('🟥 Time A')
        for player in st.session_state.time1:
            container1.write(player)

        container2.subheader('🟦 Time B')
        for player in st.session_state.time2:
            container2.write(player)

        # Inputs para os resultados
        resultado1 = col1.number_input('⚽ Gols Time A', min_value=0, step=1, key='resultadoA')
        resultado2 = col2.number_input('⚽ Gols Time B', min_value=0, step=1, key='resultadoB')

        # Botão para confirmar e salvar no MongoDB
        if st.button('✅ Confirmar e Salvar Jogo'):
            jogo = {
                'data': str(data),
                'time1': st.session_state.time1,
                'time2': st.session_state.time2,
                'resultado1': resultado1,
                'resultado2': resultado2
            }
            coll_resultados.insert_one(jogo)
            st.success('✅ Jogo cadastrado com sucesso!')

            # Limpa os times após salvar
            st.session_state.time1 = []
            st.session_state.time2 = []  

    elif st.session_state["pagina_atual"] == "home":
        st.info("Selecione uma opção no menu lateral para começar.")

def show_player_dashboard():
    # Inicializa o estado da página se não estiver presente
    if "pagina_atual" not in st.session_state:
        st.session_state["pagina_atual"] = "home"

    # Sidebar de navegação
    with st.sidebar:
        if authenticator.logout():
            st.session_state["authentication_status"] = None

        st.divider()

        if st.button("📊 Classificação"):
            st.session_state["pagina_atual"] = "placar"

        if st.button("🏠 Voltar ao início"):
            st.session_state["pagina_atual"] = "home"

    # Conteúdo principal com base na seleção
    if st.session_state["pagina_atual"] == "home":
        st.title("🏆 DOMINGOU FC")
        st.header(f"Bem-vindo, {st.session_state['name']}")
        jogadores = listar_jogadores()
        jogador = jogadores[jogadores['nome'] == st.session_state['name']]
        col1,col2 = st.columns(2)
        col1.metric(label="Pontos", value=jogador['pontos'].values[0])
        col2.metric(label="Vitórias", value=jogador['vitorias'].values[0])
        col1.metric(label="Empates", value=jogador['empates'].values[0])
        col2.metric(label="Derrotas", value=jogador['derrotas'].values[0])
        col1.metric(label="Pts Extra", value=jogador['extra'].values[0])
        col2.metric(label="Jogos", value=(jogador['derrotas'].values[0] + jogador['empates'].values[0] + jogador['vitorias'].values[0]))
            
    if st.session_state["pagina_atual"] == "placar":
        st.title("📊 Classificação")
        df = listar_jogadores()
        campeao = list(coll_champion.find({}, {"_id": 0}))
        campeoes = pd.DataFrame(campeao)
        # Ordena pelos pontos (decrescente)
        df = df.sort_values(by="pontos", ascending=False)

        # Ajusta o índice para começar de 1
        df.index = df.index + 1
        df.index.name = 'Posição'
        df.rename(columns={'nome': 'Jogador', 'pontos': 'Pontos', 'vitorias': 'Vitórias', 'empates': 'Empates', 'derrotas': 'Derrotas', 'extra': 'Extra'}, inplace=True)

        # Exibe a tabela
        st.dataframe(df)
        col1,col2,col3 = st.columns(3)
        col1.metric(label='🏆 Jogador com mais pontos', value=df['Jogador'].values[0], delta=f"{df['Pontos'].values[0]} pontos")
        col2.metric(label='🏆 Segundo com mais pontos', value=df['Jogador'].values[1], delta=f"{df['Pontos'].values[1]} pontos",delta_color="inverse")
        col3.metric(label='🏆 Terceiro com mais pontos', value=df['Jogador'].values[2], delta=f"{df['Pontos'].values[2]} pontos",delta_color="inverse")
        st.metric("Último campeão:", campeoes['campeao'].values[0])

        st.divider()
        st.title("⚽ Resultado dos Jogos")
        jogos = list(coll_resultados.find({}, {"_id": 0}))
        jogo = pd.DataFrame(data= jogos, columns=['data', 'time1',  'resultado1', 'resultado2', 'time2'])
        jogo.rename(columns={'data':'Data do jogo', 'time1': 'Time A', 'time2': 'Time B', 'resultado1': 'Gols A', 'resultado2': 'Gols B'}, inplace=True)
        st.dataframe(jogo)  

    elif st.session_state["pagina_atual"] == "home":
        st.info("Selecione uma opção no menu lateral para começar.")

if st.session_state["authentication_status"]:
    user_doc = coll_users.find_one({"username": st.session_state["username"]})
    if user_doc and "role" in user_doc:
        st.session_state["role"] = user_doc["role"]
    
    role = st.session_state["role"]

    if role == "admin":
        show_admin_dashboard()
    elif role == "jogador":
        show_player_dashboard()
        
elif st.session_state["authentication_status"] == False:
    st.error("Usuário/senha incorretos")

elif st.session_state["authentication_status"] is None:
    st.warning("Informe usuário e senha")
