import streamlit as st
import random
import time

def render(db):
    """Renderiza o sorteador de jogador"""
    st.title("🎲 Sorteador de Primeiro Jogador")
    st.markdown("---")
    
    # Pega jogadores ativos
    jogadores_df = db.get_jogadores()
    
    if len(jogadores_df) == 0:
        st.warning("⚠️ Nenhum jogador cadastrado ainda!")
        return
    
    # Seleção de jogadores
    st.subheader("👥 Selecione os jogadores")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        jogadores_selecionados = st.multiselect(
            "Quem vai jogar?",
            options=jogadores_df['nome'].tolist(),
            default=jogadores_df['nome'].tolist()[:4] if len(jogadores_df) >= 4 else jogadores_df['nome'].tolist()
        )
    
    with col2:
        if st.button("⚡ Todos", use_container_width=True):
            st.session_state['jogadores_selecionados'] = jogadores_df['nome'].tolist()
            st.rerun()
    
    # Usa session_state se existir
    if 'jogadores_selecionados' in st.session_state:
        jogadores_selecionados = st.session_state['jogadores_selecionados']
    
    if len(jogadores_selecionados) < 2:
        st.info("💡 Selecione pelo menos 2 jogadores para sortear")
        return
    
    st.markdown("---")
    
    # Área da roleta
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        resultado_placeholder = st.empty()
        
        # Mostra placeholder inicial
        resultado_placeholder.markdown(
            "<h1 style='text-align: center; color: #7F8C8D; font-size: 50px;'>❓</h1>", 
            unsafe_allow_html=True
        )
        
        if st.button("🎰 SORTEAR!", use_container_width=True, type="primary"):
            # Animação da roleta (15 rodadas)
            velocidades = [0.08] * 8 + [0.12, 0.16, 0.20, 0.25, 0.30, 0.35, 0.4]
            
            for velocidade in velocidades:
                nome_temp = random.choice(jogadores_selecionados)
                resultado_placeholder.markdown(
                    f"<h1 style='text-align: center; color: #F4D03F; font-size: 60px;'>{nome_temp}</h1>", 
                    unsafe_allow_html=True
                )
                time.sleep(velocidade)
            
            # Resultado final
            vencedor = random.choice(jogadores_selecionados)
            resultado_placeholder.markdown(
                f"<h1 style='text-align: center; color: #2ECC71; font-size: 80px;'>🎉 {vencedor} 🎉</h1>", 
                unsafe_allow_html=True
            )
            st.balloons()
            
            # Guarda no session_state para mostrar depois
            if 'historico_sorteios' not in st.session_state:
                st.session_state['historico_sorteios'] = []
            st.session_state['historico_sorteios'].append(vencedor)
            
            st.success(f"✅ {vencedor} começa jogando!")
    
    # Histórico de sorteios (opcional)
    if 'historico_sorteios' in st.session_state and len(st.session_state['historico_sorteios']) > 0:
        st.markdown("---")
        with st.expander("📜 Últimos sorteios desta sessão"):
            for i, nome in enumerate(reversed(st.session_state['historico_sorteios'][-10:]), 1):
                st.write(f"{i}. {nome}")
