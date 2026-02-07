import streamlit as st
from database import Database
from ranking import RankingCalculator
from datetime import datetime
import pandas as pd
import time
from ferramentas import sorteador_jogador

# FORÇA ATUALIZAÇÃO - Limpa cache na primeira execução
# Resolve problema: jogadores/jogos desativados ainda aparecem
if 'cache_limpo' not in st.session_state:
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.cache_limpo = True

# Configuração da página
st.set_page_config(
    page_title="Diretoria da Jogatina",
    page_icon="🎲",
    layout="wide"
)

# Função para obter Database (sempre retorna nova instância)
def get_db():
    """Retorna nova instância de Database para evitar cache"""
    return Database()

# Inicializa database
db = get_db()

# Header com logo
col1, col2 = st.columns([1, 4])
with col1:
    try:
        st.image("logo.jpg", width=150)
    except:
        st.write("🎲")  # fallback se não achar o logo

with col2:
    st.title("Diretoria da Jogatina")
    st.caption("Sistema de Rankings e Estatísticas")

st.markdown("---")

# CSS customizado para melhorar visual
st.markdown("""
    <style>
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    
    /* Cores da Diretoria da Jogatina */
    .stButton>button {
        border-color: #F4D03F;
    }
    
    .stButton>button:hover {
        background-color: #F4D03F;
        color: #2C3E50;
        border-color: #F4D03F;
    }
    
    /* Header customizado */
    h1 {
        color: #F4D03F;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #34495E;
    }
    </style>
    """, unsafe_allow_html=True)

# ====================
# MENU LATERAL
# ====================
st.sidebar.title("🎲 Diretoria da Jogatina")
st.sidebar.markdown("---")

# Botão para forçar atualização de dados
if st.sidebar.button("🔄 Atualizar Dados", help="Clique se jogadores/jogos desativados ainda aparecem"):
    st.cache_data.clear()
    st.cache_resource.clear()
    # Força recriação do Database
    if 'db_recreate' not in st.session_state:
        st.session_state.db_recreate = 0
    st.session_state.db_recreate += 1
    st.rerun()

# Recria Database se necessário (ou sempre após atualizar dados)
if 'db_recreate' in st.session_state and st.session_state.db_recreate > 0:
    db = get_db()
else:
    # Primeira vez ou sem atualização - recria de qualquer forma
    db = get_db()

menu = st.sidebar.radio(
    "Menu Principal",
    ["🏠 Início", "➕ Registrar Partida", "🏆 Rankings", "👥 Jogadores", "🎮 Jogos",
    "📊 Histórico", "🛠️ Ferramentas", "✏️ Editar"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Backup")

if st.sidebar.button("Gerar backup do banco"):
    backup_data, backup_name = db.backup_bytes()
    st.session_state["backup_data"] = backup_data
    st.session_state["backup_name"] = backup_name

if "backup_data" in st.session_state:
    st.sidebar.download_button(
        label="⬇️ Baixar backup (.db)",
        data=st.session_state["backup_data"],
        file_name=st.session_state["backup_name"],
        mime="application/octet-stream",
    )

st.sidebar.markdown("---")
st.sidebar.caption("Diretoria da Jogatina © 2025")
st.sidebar.caption("Sistema de Rankings v2.0")

# ====================
# PÁGINA: INÍCIO
# ====================
if menu == "🏠 Início":
    st.title("🏠 Dashboard")
    st.write("Bem-vindo à **Diretoria da Jogatina**!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_jogadores = len(db.get_jogadores())
        st.metric("👥 Jogadores Ativos", total_jogadores)
    
    with col2:
        total_jogos = len(db.get_jogos())
        st.metric("🎮 Jogos Cadastrados", total_jogos)
    
    with col3:
        total_partidas = len(db.get_partidas())
        st.metric("🎯 Partidas Registradas", total_partidas)
    
    st.markdown("---")
    
    st.subheader("📊 Últimas Partidas")
    ultimas = db.get_partidas(limit=10)
    if len(ultimas) > 0:
        st.dataframe(ultimas[['data', 'jogo', 'jogadores']], width="stretch", hide_index=True)
    else:
        st.info("Nenhuma partida registrada ainda. Vá em 'Registrar Partida' para começar!")

# ====================
# PÁGINA: REGISTRAR PARTIDA
# ====================
elif menu == "➕ Registrar Partida":
    st.title("➕ Registrar Nova Partida")
    
    jogos_df = db.get_jogos()
    jogadores_df = db.get_jogadores()
    
    if len(jogos_df) == 0:
        st.warning("⚠️ Você precisa cadastrar pelo menos um jogo primeiro!")
        st.info("Vá no menu 'Jogos' para cadastrar.")
        st.stop()
    
    if len(jogadores_df) == 0:
        st.warning("⚠️ Você precisa cadastrar pelo menos um jogador primeiro!")
        st.info("Vá no menu 'Jogadores' para cadastrar.")
        st.stop()
    
    # Número de jogadores FORA do formulário (para atualizar campos dinamicamente)
    st.subheader("👥 Jogadores")
    num_jogadores = st.number_input(
        "Quantos jogadores participaram?", 
        min_value=2, 
        max_value=10, 
        value=3,
        help="💡 Mude este número ANTES de preencher o formulário abaixo"
    )
    
    st.markdown("---")
    
    with st.form("form_partida"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Seleção do jogo
            jogo_selecionado = st.selectbox(
                "🎮 Jogo",
                options=jogos_df['nome'].tolist()
            )
            jogo_id = jogos_df[jogos_df['nome'] == jogo_selecionado]['id'].iloc[0]
            peso = jogos_df[jogos_df['nome'] == jogo_selecionado]['peso_bgg'].iloc[0]
            st.caption(f"Peso BGG: {peso}")
        
        with col2:
            # Data da partida
            data_partida = st.date_input(
                "📅 Data",
                value=datetime.now()
            )
        
        # Checkboxes
        col1, col2 = st.columns(2)
        with col1:
            valida_ranking = st.checkbox("✅ Válida para ranking", value=True)
        with col2:
            eh_jogo_time = st.checkbox("👥 Jogo de times", value=False)
        
        st.markdown("---")
        st.subheader("Jogadores e Resultados")
        
        # Cria inputs para cada jogador
        jogadores_posicoes = []
        
        for i in range(num_jogadores):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                jogador = st.selectbox(
                    f"Jogador {i+1}",
                    options=jogadores_df['nome'].tolist(),
                    key=f"jogador_{i}"
                )
            
            with col2:
                posicao = st.number_input(
                    f"Posição",
                    min_value=1,
                    max_value=num_jogadores,
                    value=i+1,
                    key=f"posicao_{i}"
                )
            
            with col3:
                pontuacao = st.number_input(
                    f"Pontos",
                    min_value=0,
                    value=0,
                    key=f"pontuacao_{i}"
                )
            
            jogador_id = jogadores_df[jogadores_df['nome'] == jogador]['id'].iloc[0]
            jogadores_posicoes.append((jogador_id, posicao, pontuacao))
        
        observacoes = st.text_area("Observações (opcional)")
        
        submit = st.form_submit_button("💾 Salvar Partida", width="stretch")
        
        if submit:
            # Valida posições únicas
            posicoes = [x[1] for x in jogadores_posicoes]
            if len(posicoes) != len(set(posicoes)):
                st.error("❌ Não pode ter posições repetidas!")
            else:
                valida_str = 'S' if valida_ranking else 'N'
                time_str = 'S' if eh_jogo_time else 'N'
                
                sucesso = db.add_partida(
                    jogo_id, 
                    data_partida, 
                    jogadores_posicoes, 
                    observacoes,
                    valida_ranking=valida_str,
                    eh_jogo_time=time_str
                )
                
                if sucesso:
                    st.success("✅ Partida registrada com sucesso!")
                    
                    # Recalcula Elos
                    with st.spinner("Recalculando Elos..."):
                        RankingCalculator.recalcular_todos_elos(db)
                    
                    st.info("✨ Elos atualizados!")
                    st.balloons()
                else:
                    st.error("❌ Erro ao salvar partida!")

# ====================
# PÁGINA: RANKINGS
# ====================
elif menu == "🏆 Rankings":
    st.title("🏆 Rankings")
    
    tab1, tab2 = st.tabs(["📊 Aproveitamento", "🎯 ELO"])
    
    with tab1:
        st.subheader("Ranking por Aproveitamento (últimas 40 partidas)")
        
        limite = st.slider("Quantas partidas considerar?", min_value=10, max_value=100, value=40, step=10)
        
        with st.spinner("Calculando ranking..."):
            ranking_aprov = RankingCalculator.calcular_ranking_aproveitamento(db, limite_partidas=limite)
        
        if len(ranking_aprov) > 0:
            # Formata para exibição
            ranking_aprov['aproveitamento'] = ranking_aprov['aproveitamento'].apply(lambda x: f"{x:.2f}%")
            
            st.dataframe(
                ranking_aprov,
                width="stretch",
                column_config={
                    "jogador": "Jogador",
                    "aproveitamento": "Aproveitamento",
                    "partidas": "Partidas"
                }
            )

        else:
            st.info("Nenhum jogador com partidas registradas ainda.")
    
    with tab2:
        st.subheader("Ranking ELO")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🔄 Recalcular Todos Elos"):
                with st.spinner("Recalculando..."):
                    RankingCalculator.recalcular_todos_elos(db)
                st.success("✅ Elos recalculados!")
                st.rerun()
        
        ranking_elo = RankingCalculator.get_ranking_elo(db)
        
        if len(ranking_elo) > 0:
            st.dataframe(
                ranking_elo,
                width="stretch",
                column_config={
                    "nome": "Jogador",
                    "elo": "ELO"
                }
            )

        else:
            st.info("Nenhum jogador cadastrado ainda.")

# ====================
# PÁGINA: JOGADORES
# ====================
elif menu == "👥 Jogadores":
    st.title("👥 Gerenciar Jogadores")
    
    tab1, tab2 = st.tabs(["📋 Lista", "➕ Adicionar"])
    
    with tab1:
        st.subheader("Jogadores Cadastrados")
        jogadores = db.get_jogadores()
        
        if len(jogadores) > 0:
            st.dataframe(
                jogadores[['nome', 'elo']],
                width="stretch",
                hide_index=True,
                column_config={
                    "nome": "Nome",
                    "elo": "ELO Atual"
                }
            )
        else:
            st.info("Nenhum jogador cadastrado ainda.")
    
    with tab2:
        st.subheader("Adicionar Novo Jogador")
        
        with st.form("form_jogador"):
            nome = st.text_input("Nome do Jogador")
            elo_inicial = st.number_input("ELO Inicial", min_value=0, value=1500, step=50)
            
            submit = st.form_submit_button("💾 Salvar Jogador")
            
            if submit:
                if nome.strip() == "":
                    st.error("❌ Nome não pode ser vazio!")
                else:
                    sucesso = db.add_jogador(nome.strip(), elo_inicial)
                    if sucesso:
                        st.success(f"✅ Jogador '{nome}' adicionado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Jogador já existe!")

# ====================
# PÁGINA: JOGOS
# ====================
elif menu == "🎮 Jogos":
    st.title("🎮 Gerenciar Jogos")
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista", "➕ Adicionar", "🔄 Atualizar do BGG"])
    
    with tab1:
        st.subheader("Jogos Cadastrados")
        jogos = db.get_jogos()
        
        if len(jogos) > 0:
            # Seleciona colunas relevantes para exibição
            colunas_exibir = ['nome', 'peso_bgg', 'min_jogadores', 'max_jogadores', 
                            'tempo_min', 'tempo_max', 'categoria']
            
            # Filtra apenas colunas que existem
            colunas_disponiveis = [col for col in colunas_exibir if col in jogos.columns]
            
            st.dataframe(
                jogos[colunas_disponiveis],
                width="stretch",
                hide_index=True,
                column_config={
                    "nome": "Nome",
                    "peso_bgg": "Peso BGG",
                    "min_jogadores": "Min Jog.",
                    "max_jogadores": "Max Jog.",
                    "tempo_min": "Tempo Min",
                    "tempo_max": "Tempo Max",
                    "categoria": "Categoria"
                }
            )
            
            # Detalhes expandíveis
            with st.expander("🔍 Ver Detalhes Completos"):
                jogo_selecionado = st.selectbox(
                    "Selecione um jogo",
                    jogos['nome'].tolist()
                )
                
                jogo_info = jogos[jogos['nome'] == jogo_selecionado].iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Nome:** {jogo_info['nome']}")
                    if 'ano_publicacao' in jogo_info and pd.notna(jogo_info['ano_publicacao']):
                        st.write(f"**Ano:** {int(jogo_info['ano_publicacao'])}")
                    st.write(f"**Peso BGG:** {jogo_info['peso_bgg']}")
                    if 'min_jogadores' in jogo_info and pd.notna(jogo_info['min_jogadores']):
                        st.write(f"**Jogadores:** {int(jogo_info['min_jogadores'])} - {int(jogo_info['max_jogadores'])}")
                    if 'tempo_min' in jogo_info and pd.notna(jogo_info['tempo_min']):
                        st.write(f"**Tempo:** {int(jogo_info['tempo_min'])} - {int(jogo_info['tempo_max'])} min")
                
                with col2:
                    if 'tipo' in jogo_info and pd.notna(jogo_info['tipo']):
                        st.write(f"**Tipo:** {jogo_info['tipo']}")
                    if 'categoria' in jogo_info and pd.notna(jogo_info['categoria']):
                        st.write(f"**Categoria:** {jogo_info['categoria']}")
                    if 'mecanicas' in jogo_info and pd.notna(jogo_info['mecanicas']):
                        st.write(f"**Mecânicas:** {jogo_info['mecanicas']}")
                    if 'link_bgg' in jogo_info and pd.notna(jogo_info['link_bgg']):
                        st.write(f"**Link:** [{jogo_info['link_bgg']}]({jogo_info['link_bgg']})")
                
                if 'ultima_atualizacao' in jogo_info and pd.notna(jogo_info['ultima_atualizacao']):
                    st.caption(f"Última atualização: {jogo_info['ultima_atualizacao']}")
        else:
            st.info("Nenhum jogo cadastrado ainda.")
    
    with tab2:
        st.subheader("Adicionar Novo Jogo")
        
        modo = st.radio("Como deseja adicionar?", ["🔍 Buscar no BGG", "✏️ Manual"])
        
        if modo == "🔍 Buscar no BGG":
            with st.form("form_jogo_bgg"):
                nome_busca = st.text_input("Nome do jogo para buscar no BGG")
                
                submit = st.form_submit_button("🔍 Buscar e Adicionar")
                
                if submit:
                    if nome_busca.strip() == "":
                        st.error("❌ Nome não pode ser vazio!")
                    else:
                        with st.spinner(f"Buscando '{nome_busca}' no BGG..."):
                            from bgg_sync import adicionar_jogo_com_bgg
                            sucesso, dados = adicionar_jogo_com_bgg(db, nome_busca)
                        
                        if sucesso:
                            st.success(f"✅ Jogo '{dados['nome']}' adicionado com sucesso!")
                            st.info(f"Peso: {dados['peso']} | Jogadores: {dados['min_jogadores']}-{dados['max_jogadores']}")
                            st.rerun()
                        elif dados is None:
                            st.error("❌ Jogo não encontrado no BGG! Tente buscar com outro nome ou adicione manualmente.")
                        else:
                            st.error("❌ Jogo já existe no banco!")
        
        else:  # Manual
            with st.form("form_jogo_manual"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("Nome do Jogo")
                    peso = st.number_input("Peso BGG", min_value=1.0, max_value=5.0, value=2.5, step=0.1)
                    min_jog = st.number_input("Min Jogadores", min_value=1, value=2)
                    max_jog = st.number_input("Max Jogadores", min_value=1, value=4)
                
                with col2:
                    tempo_min = st.number_input("Tempo Mínimo (min)", min_value=0, value=30)
                    tempo_max = st.number_input("Tempo Máximo (min)", min_value=0, value=60)
                    link = st.text_input("Link BGG (opcional)")
                
                submit = st.form_submit_button("💾 Salvar Jogo")
                
                if submit:
                    if nome.strip() == "":
                        st.error("❌ Nome não pode ser vazio!")
                    else:
                        sucesso = db.add_jogo(
                            nome=nome.strip(),
                            peso_bgg=peso,
                            min_jogadores=min_jog,
                            max_jogadores=max_jog,
                            tempo_min=tempo_min,
                            tempo_max=tempo_max,
                            link_bgg=link if link else None
                        )
                        if sucesso:
                            st.success(f"✅ Jogo '{nome}' adicionado com sucesso!")
                            st.rerun()
                        else:
                            st.error("❌ Jogo já existe!")
    
    with tab3:
        st.subheader("🔄 Atualizar Jogos do BGG")
        st.write("Busca e atualiza informações dos jogos cadastrados usando o BGG.")
        
        jogos = db.get_jogos()
        
        if len(jogos) > 0:
            jogo_atualizar = st.selectbox(
                "Selecione um jogo para atualizar",
                jogos['nome'].tolist()
            )
            
            if st.button("🔄 Atualizar este jogo"):
                jogo_info = jogos[jogos['nome'] == jogo_atualizar].iloc[0]
                jogo_id = jogo_info['id']
                
                with st.spinner(f"Buscando dados de '{jogo_atualizar}' no BGG..."):
                    from bgg_sync import atualizar_jogo_do_bgg
                    sucesso, dados = atualizar_jogo_do_bgg(db, jogo_id, jogo_atualizar)
                
                if sucesso:
                    st.success(f"✅ Jogo '{dados['nome']}' atualizado!")
                    st.info(f"Peso: {dados['peso']} | Jogadores: {dados['min_jogadores']}-{dados['max_jogadores']}")
                    st.rerun()
                else:
                    st.error("❌ Não foi possível encontrar o jogo no BGG!")
            
            st.markdown("---")
            
            if st.button("🔄 Atualizar TODOS os jogos"):
                from bgg_sync import atualizar_jogo_do_bgg
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total = len(jogos)
                sucessos = 0
                
                for idx, (_, jogo) in enumerate(jogos.iterrows()):
                    status_text.text(f"Atualizando {idx+1}/{total}: {jogo['nome']}")
                    
                    sucesso, _ = atualizar_jogo_do_bgg(db, jogo['id'], jogo['nome'])
                    if sucesso:
                        sucessos += 1
                    
                    progress_bar.progress((idx + 1) / total)
                    time.sleep(0.5)  # Rate limit da API
                
                status_text.text(f"✅ Concluído! {sucessos}/{total} jogos atualizados.")
                st.balloons()
                st.rerun()
        else:
            st.info("Nenhum jogo cadastrado ainda.")

# ====================
# PÁGINA: HISTÓRICO
# ====================
elif menu == "📊 Histórico":
    st.title("📊 Histórico de Partidas")
    
    partidas = db.get_partidas()
    
    if len(partidas) > 0:
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            jogos_unicos = db.get_jogos()['nome'].tolist()
            jogo_filtro = st.selectbox("Filtrar por jogo", ["Todos"] + jogos_unicos)
        
        with col2:
            ordenacao = st.selectbox("Ordenar por", ["Mais recentes", "Mais antigas"])
        
        # Aplica filtros (simplificado - pode melhorar)
        df_exibir = partidas
        
        st.dataframe(
            df_exibir[['data', 'jogo', 'peso_bgg', 'jogadores']],
            width="stretch",
            hide_index=True,
            column_config={
                "data": "Data",
                "jogo": "Jogo",
                "peso_bgg": "Peso",
                "jogadores": "Jogadores (Posição)"
            }
        )
        
        st.metric("Total de Partidas", len(df_exibir))
    else:
        st.info("Nenhuma partida registrada ainda.")

# ====================
# PÁGINA: FERRAMENTAS
# ====================
elif menu == "🛠️ Ferramentas":
    st.title("🛠️ Ferramentas")
    
    # Abas para cada ferramenta
    tab1 = st.tabs(["🎲 Sorteador de Jogador"])[0]
    
    with tab1:
        sorteador_jogador.render(db)

# ====================
# PÁGINA: EDITAR
# ====================
elif menu == "✏️ Editar":
    st.title("✏️ Editar Registros")
    
    tab1, tab2, tab3 = st.tabs(["👥 Jogadores", "🎮 Jogos", "🎯 Partidas"])
    
    with tab1:
        st.subheader("Editar Jogadores")
        
        # Mostra TODOS jogadores (ativos e inativos)
        jogadores = db.get_jogadores(apenas_ativos=False)
        
        if len(jogadores) > 0:
            # Adiciona indicador de status
            jogadores['display_nome'] = jogadores.apply(
                lambda x: f"{'✅' if x['ativo'] else '🚫'} {x['nome']}", 
                axis=1
            )
            
            jogador_selecionado = st.selectbox(
                "Selecione um jogador",
                jogadores['display_nome'].tolist(),
                help="✅ = Ativo | 🚫 = Desativado"
            )
            
            jogador_info = jogadores[jogadores['display_nome'] == jogador_selecionado].iloc[0]
            
            # Mostra status
            if jogador_info['ativo'] == 0:
                st.warning("⚠️ Este jogador está DESATIVADO (não aparece em registros novos)")
            
            with st.form("form_editar_jogador"):
                nome = st.text_input("Nome", value=jogador_info['nome'])
                
                # ELO apenas para visualização (calculado automaticamente)
                st.info(f"🎯 **ELO Atual:** {jogador_info['elo']:.1f} (calculado automaticamente baseado nas partidas)")
                st.caption("💡 O ELO é recalculado automaticamente. Para atualizar, vá em Rankings → ELO → Recalcular.")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    salvar = st.form_submit_button("💾 Salvar Nome", width="stretch")
                
                with col2:
                    if jogador_info['ativo'] == 1:
                        desativar = st.form_submit_button("🗑️ Desativar", width="stretch")
                        reativar = False  # Garante que existe
                    else:
                        reativar = st.form_submit_button("✅ Reativar", width="stretch", type="primary")
                        desativar = False  # Garante que existe
            
            # Processa ações FORA do form
            if salvar:
                sucesso = db.update_jogador(jogador_info['id'], nome)
                if sucesso:
                    st.success("✅ Jogador atualizado!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao atualizar (nome pode já existir)")
            
            if desativar:
                st.write("🔍 DEBUG: Botão desativar clicado!")  # DEBUG
                st.write(f"🔍 DEBUG: jogador_info['id'] = {jogador_info['id']}")  # DEBUG
                db.desativar_jogador(jogador_info['id'])
                st.success(f"🗑️ Jogador '{jogador_info['nome']}' desativado!")
                st.info("💡 Jogador não aparecerá mais em novos registros, mas histórico está preservado.")
                st.balloons()
                st.rerun()
            
            if reativar:
                st.write("🔍 DEBUG: Botão reativar clicado!")  # DEBUG
                db.reativar_jogador(jogador_info['id'])
                st.success(f"✅ Jogador '{jogador_info['nome']}' reativado!")
                st.balloons()
                st.rerun()
        else:
            st.info("Nenhum jogador cadastrado.")
    
    with tab2:
        st.subheader("Editar Jogos")
        
        # Mostra TODOS jogos (ativos e inativos)
        jogos = db.get_jogos(apenas_ativos=False)
        
        if len(jogos) > 0:
            # Adiciona indicador de status
            jogos['display_nome'] = jogos.apply(
                lambda x: f"{'✅' if x['ativo'] else '🚫'} {x['nome']}", 
                axis=1
            )
            
            jogo_selecionado = st.selectbox(
                "Selecione um jogo",
                jogos['display_nome'].tolist(),
                help="✅ = Ativo | 🚫 = Desativado"
            )
            
            jogo_info = jogos[jogos['display_nome'] == jogo_selecionado].iloc[0]
            
            # Mostra status
            if jogo_info['ativo'] == 0:
                st.warning("⚠️ Este jogo está DESATIVADO (não aparece em registros novos)")
            
            with st.form("form_editar_jogo"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("Nome", value=jogo_info['nome'])
                    peso = st.number_input("Peso BGG", min_value=1.0, max_value=5.0, 
                                          value=float(jogo_info['peso_bgg']), step=0.1)
                    min_jog = st.number_input("Min Jogadores", min_value=1, 
                                             value=int(jogo_info['min_jogadores']) if pd.notna(jogo_info['min_jogadores']) else 2)
                    max_jog = st.number_input("Max Jogadores", min_value=1, 
                                             value=int(jogo_info['max_jogadores']) if pd.notna(jogo_info['max_jogadores']) else 4)
                
                with col2:
                    tempo_min = st.number_input("Tempo Min (min)", min_value=0, 
                                               value=int(jogo_info['tempo_min']) if pd.notna(jogo_info['tempo_min']) else 30)
                    tempo_max = st.number_input("Tempo Max (min)", min_value=0, 
                                               value=int(jogo_info['tempo_max']) if pd.notna(jogo_info['tempo_max']) else 60)
                    tipo = st.text_input("Tipo", value=str(jogo_info['tipo']) if pd.notna(jogo_info['tipo']) else "")
                    link = st.text_input("Link BGG", value=str(jogo_info['link_bgg']) if pd.notna(jogo_info['link_bgg']) else "")
                
                categoria = st.text_input("Categoria", value=str(jogo_info['categoria']) if pd.notna(jogo_info['categoria']) else "")
                mecanicas = st.text_area("Mecânicas", value=str(jogo_info['mecanicas']) if pd.notna(jogo_info['mecanicas']) else "")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    salvar = st.form_submit_button("💾 Salvar Alterações", width="stretch")
                
                with col2:
                    if jogo_info['ativo'] == 1:
                        desativar_jogo = st.form_submit_button("🗑️ Desativar", width="stretch")
                        reativar_jogo = False  # Garante que existe
                    else:
                        reativar_jogo = st.form_submit_button("✅ Reativar", width="stretch", type="primary")
                        desativar_jogo = False  # Garante que existe
            
            # Processa ações FORA do form
            if salvar:
                dados = {
                    'nome': nome,
                    'peso_bgg': peso,
                    'min_jogadores': min_jog,
                    'max_jogadores': max_jog,
                    'tempo_min': tempo_min,
                    'tempo_max': tempo_max,
                    'tipo': tipo if tipo else None,
                    'categoria': categoria if categoria else None,
                    'mecanicas': mecanicas if mecanicas else None,
                    'link_bgg': link if link else None
                }
                sucesso = db.update_jogo(jogo_info['id'], dados)
                if sucesso:
                    st.success("✅ Jogo atualizado!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao atualizar")
            
            if desativar_jogo:
                st.write("🔍 DEBUG: Botão desativar jogo clicado!")  # DEBUG
                db.desativar_jogo(jogo_info['id'])
                st.success(f"🗑️ Jogo '{jogo_info['nome']}' desativado!")
                st.info("💡 Jogo não aparecerá mais em novos registros.")
                st.balloons()
                st.rerun()
            
            if reativar_jogo:
                st.write("🔍 DEBUG: Botão reativar jogo clicado!")  # DEBUG
                db.reativar_jogo(jogo_info['id'])
                st.success(f"✅ Jogo '{jogo_info['nome']}' reativado!")
                st.balloons()
                st.rerun()
        else:
            st.info("Nenhum jogo cadastrado.")
    
    with tab3:
        st.subheader("Editar/Excluir Partidas")
        
        partidas = db.get_partidas(limit=50)
        
        if len(partidas) > 0:
            # Cria identificador visual (tratando None em jogadores)
            partidas['display'] = partidas.apply(
                lambda x: f"{x['data']} - {x['jogo']} ({x['jogadores'][:50] if x['jogadores'] else 'Sem jogadores'}...)", 
                axis=1
            )
            
            partida_selecionada = st.selectbox(
                "Selecione uma partida",
                partidas['display'].tolist(),
                key="select_partida_edit"
            )
            
            idx = partidas[partidas['display'] == partida_selecionada].index[0]
            partida_id = int(partidas.loc[idx, 'id'])  # Força int nativo
            
            # Busca detalhes
            partida_info, resultados = db.get_partida_detalhes(partida_id)
            
            if partida_info is None:
                st.error("❌ Erro ao carregar detalhes da partida")
            else:
                st.write(f"**Jogo:** {partida_info['jogo_nome']}")
                st.write(f"**Data:** {partida_info['data']}")
                st.write(f"**Válida para ranking:** {partida_info['valida_ranking']}")
                st.write(f"**Jogo de times:** {partida_info['eh_jogo_time']}")
                
                st.markdown("**Resultados:**")
                st.dataframe(
                    resultados[['jogador_nome', 'posicao', 'pontuacao']],
                    hide_index=True,
                    column_config={
                        "jogador_nome": "Jogador",
                        "posicao": "Posição",
                        "pontuacao": "Pontuação"
                    }
                )
                
                st.markdown("---")
                
                # Opções de edição
                col1, col2 = st.columns(2)
                
                with col1:
                    editar_mode = st.checkbox("✏️ Habilitar edição", key=f"edit_{partida_id}")
                
                with col2:
                    confirmar_delete = st.checkbox("⚠️ Confirmar exclusão", key=f"del_{partida_id}")
                
                if editar_mode:
                    st.warning("🚧 Edição completa em desenvolvimento. Por enquanto, exclua e registre novamente.")
                
                if confirmar_delete:
                    if st.button("🗑️ EXCLUIR PARTIDA PERMANENTEMENTE", width="stretch", type="primary"):
                        if db.delete_partida(partida_id):
                            st.success("✅ Partida excluída!")
                            # Recalcula Elos
                            with st.spinner("Recalculando Elos..."):
                                RankingCalculator.recalcular_todos_elos(db)
                            st.rerun()
                        else:
                            st.error("❌ Erro ao excluir partida")
        else:
            st.info("Nenhuma partida registrada.")
