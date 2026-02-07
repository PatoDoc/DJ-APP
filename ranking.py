import pandas as pd
import itertools

class RankingCalculator:
    
    @staticmethod
    def calcular_aproveitamento(df_partidas, peso_jogo):
        """
        Calcula aproveitamento usando mini-partidas (todas as combinações)
        df_partidas: DataFrame com colunas [posicao, total_jogadores, peso]
        total_jogadores = MAX(posicao) da partida
        """
        if len(df_partidas) == 0:
            return 0.0
        
        total_vitorias_ponderadas = 0
        total_partidas_ponderadas = 0
        
        for _, partida in df_partidas.iterrows():
            posicao = partida['posicao']
            total = partida['total_jogadores']  # MAX(posicao)
            peso = partida['peso']
            
            # Quantos jogadores/times eu venci nessa partida?
            vitorias = total - posicao
            total_mini_partidas = total - 1  # total de confrontos
            
            # Pondera pelo peso ajustado (peso - 1)
            # Jogos de peso 1.0 (pura sorte) não contam no ranking
            peso_ajustado = peso - 1
            if peso_ajustado <= 0:
                continue
            
            total_vitorias_ponderadas += vitorias * peso_ajustado
            total_partidas_ponderadas += total_mini_partidas * peso_ajustado
        
        if total_partidas_ponderadas == 0:
            return 0.0
        
        aproveitamento = (total_vitorias_ponderadas / total_partidas_ponderadas) * 100
        return round(aproveitamento, 2)
    
    @staticmethod
    def calcular_ranking_aproveitamento(db, limite_partidas=40):
        """Calcula ranking de aproveitamento para todos jogadores"""
        jogadores = db.get_jogadores()
        
        ranking = []
        for _, jogador in jogadores.iterrows():
            partidas = db.get_todas_partidas_jogador(jogador['id'], limit=limite_partidas)
            
            if len(partidas) == 0:
                continue
            
            aproveitamento = RankingCalculator.calcular_aproveitamento(partidas, peso_jogo=True)
            
            ranking.append({
                'jogador': jogador['nome'],
                'aproveitamento': aproveitamento,
                'partidas': len(partidas)
            })
        
        df_ranking = pd.DataFrame(ranking)
        df_ranking = df_ranking.sort_values('aproveitamento', ascending=False).reset_index(drop=True)
        df_ranking.index = df_ranking.index + 1  # Começa do 1
        
        return df_ranking
    
    @staticmethod
    def get_k_factor(peso_jogo):
        """
        Calcula K-factor baseado no peso do jogo (escala linear)
        Peso 1.0 → K = 0 (jogos de pura sorte não contam)
        Peso 5.0 → K = 64 (jogos estratégicos contam muito)
        """
        k_val = 64 * ((peso_jogo - 1) / (5 - 1))
        if k_val < 0:
            k_val = 0
        if k_val > 64:
            k_val = 64
        return k_val
    
    @staticmethod
    def calcular_variacao_elo(elo_jogador, elo_oponente, resultado, peso_jogo, k_factor=None):
        """
        Calcula variação de Elo em uma mini-partida
        resultado: 1 = vitória, 0 = derrota, 0.5 = empate
        """
        # Usa K-factor variável baseado no peso
        if k_factor is None:
            k_factor = RankingCalculator.get_k_factor(peso_jogo)
        
        # Expectativa de vitória (divisor 350, não 400)
        expectativa = 1 / (1 + 10 ** ((elo_oponente - elo_jogador) / 350))
        
        # Variação (não multiplica pelo peso - já está no K)
        variacao = k_factor * (resultado - expectativa)
        
        return variacao
    
    @staticmethod
    def calcular_elos_partida(resultados_partida, elos_atuais, peso_jogo, eh_jogo_time='N'):
        """
        Calcula novos Elos após uma partida usando mini-partidas
        resultados_partida: lista de dicts [{jogador_id, posicao, time_id}, ...]
        elos_atuais: dict {jogador_id: elo}
        eh_jogo_time: 'S' ou 'N'
        """
        novos_elos = elos_atuais.copy()
        k_factor = RankingCalculator.get_k_factor(peso_jogo)
        
        if eh_jogo_time == 'S':
            # === JOGO DE TIME ===
            # Agrupa jogadores por posição (mesmo time = mesma posição)
            times = {}
            for r in resultados_partida:
                pos = r['posicao']
                if pos not in times:
                    times[pos] = []
                times[pos].append(r['jogador_id'])
            
            # Se só tem 1 time (todos empatados), pula
            if len(times) <= 1:
                return novos_elos
            
            # Calcula ELO médio de cada time
            team_elos = {}
            for pos, membros in times.items():
                team_elos[pos] = sum(elos_atuais[jid] for jid in membros) / len(membros)
            
            # Acumula variações por jogador
            rating_change = {r['jogador_id']: 0.0 for r in resultados_partida}
            
            # Mini-partidas entre times
            posicoes = sorted(times.keys())
            for i in range(len(posicoes)):
                for j in range(i + 1, len(posicoes)):
                    pos_i, pos_j = posicoes[i], posicoes[j]
                    
                    # Expectativa usando ELO médio do time
                    e_i = 1 / (1 + 10 ** ((team_elos[pos_j] - team_elos[pos_i]) / 350))
                    e_j = 1 / (1 + 10 ** ((team_elos[pos_i] - team_elos[pos_j]) / 350))
                    
                    # Resultado: posição menor = venceu
                    if pos_i < pos_j:
                        s_i, s_j = 1.0, 0.0
                    else:
                        s_i, s_j = 0.0, 1.0
                    
                    change_i = k_factor * (s_i - e_i)
                    change_j = k_factor * (s_j - e_j)
                    
                    # Mesma variação pra todos do time
                    for jid in times[pos_i]:
                        rating_change[jid] += change_i
                    for jid in times[pos_j]:
                        rating_change[jid] += change_j
            
            # Aplica variações
            for jid, change in rating_change.items():
                novos_elos[jid] += change
        
        else:
            # === JOGO INDIVIDUAL ===
            # Acumula variações usando ELO congelado (elos_atuais)
            rating_change = {r['jogador_id']: 0.0 for r in resultados_partida}
            
            for i in range(len(resultados_partida)):
                for j in range(i + 1, len(resultados_partida)):
                    p1 = resultados_partida[i]
                    p2 = resultados_partida[j]
                    
                    id_i = p1['jogador_id']
                    id_j = p2['jogador_id']
                    
                    # Expectativa
                    e_i = 1 / (1 + 10 ** ((elos_atuais[id_j] - elos_atuais[id_i]) / 350))
                    e_j = 1 / (1 + 10 ** ((elos_atuais[id_i] - elos_atuais[id_j]) / 350))
                    
                    # Resultado
                    if p1['posicao'] < p2['posicao']:
                        s_i, s_j = 1.0, 0.0
                    elif p1['posicao'] > p2['posicao']:
                        s_i, s_j = 0.0, 1.0
                    else:
                        s_i, s_j = 0.5, 0.5
                    
                    rating_change[id_i] += k_factor * (s_i - e_i)
                    rating_change[id_j] += k_factor * (s_j - e_j)
            
            # Aplica variações
            for jid, change in rating_change.items():
                novos_elos[jid] += change
        
        return novos_elos
    
    @staticmethod
    def recalcular_todos_elos(db, elo_inicial=1500):
        """Recalcula Elos de todos jogadores desde o início"""
        conn = db.get_connection()
        
        # Pega todas as partidas VÁLIDAS em ordem cronológica
        query = """
            SELECT 
                p.id as partida_id,
                p.data,
                p.eh_jogo_time,
                j.peso_bgg as peso,
                r.jogador_id,
                r.posicao,
                r.time_id
            FROM partidas p
            JOIN jogos j ON p.jogo_id = j.id
            JOIN resultados r ON p.id = r.partida_id
            WHERE p.valida_ranking = 'S'
            ORDER BY p.data ASC, p.id ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Inicializa Elos (TODOS jogadores, inclusive inativos, pois participaram de partidas)
        jogadores = db.get_jogadores(apenas_ativos=False)
        elos = {jog_id: elo_inicial for jog_id in jogadores['id'].tolist()}
        
        # Processa cada partida
        for partida_id in df['partida_id'].unique():
            partida_df = df[df['partida_id'] == partida_id]
            peso = partida_df['peso'].iloc[0]
            eh_jogo_time = partida_df['eh_jogo_time'].iloc[0]
            
            resultados = [
                {'jogador_id': row['jogador_id'], 'posicao': row['posicao'], 'time_id': row['time_id']}
                for _, row in partida_df.iterrows()
            ]
            
            # Calcula novos Elos (considera times se necessário)
            elos = RankingCalculator.calcular_elos_partida(resultados, elos, peso, eh_jogo_time)
        
        # Atualiza Elos no banco
        conn = db.get_connection()
        for jogador_id, elo in elos.items():
            conn.execute("UPDATE jogadores SET elo = ? WHERE id = ?", (round(elo, 1), jogador_id))
        conn.commit()
        conn.close()
        
        return elos
    
    @staticmethod
    def get_ranking_elo(db):
        """Retorna ranking por Elo"""
        jogadores = db.get_jogadores()
        ranking = jogadores[['nome', 'elo']].copy()
        ranking = ranking.sort_values('elo', ascending=False).reset_index(drop=True)
        ranking.index = ranking.index + 1
        ranking['elo'] = ranking['elo'].round(1)
        return ranking
