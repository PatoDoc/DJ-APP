import sqlite3
from datetime import datetime
import pandas as pd
import tempfile
from pathlib import Path

class Database:
    def __init__(self, db_name='jogos.db'):
        self.db_name = db_name
        self.create_tables()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn
    
    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabela de jogatinas (sessões de jogos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jogatinas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data DATE NOT NULL,
                local TEXT,
                observacoes TEXT
            )
        """)
        
        # Tabela de jogadores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jogadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                elo REAL DEFAULT 1500,
                ativo INTEGER DEFAULT 1
            )
        """)
        
        # Tabela de jogos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jogos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                bgg_id INTEGER,
                link_bgg TEXT,
                peso_bgg REAL DEFAULT 2.0,
                min_jogadores INTEGER,
                max_jogadores INTEGER,
                tempo_min INTEGER,
                tempo_max INTEGER,
                tipo TEXT,
                categoria TEXT,
                mecanicas TEXT,
                ano_publicacao INTEGER,
                ultima_atualizacao DATE,
                ativo INTEGER DEFAULT 1
            )
        """)
        
        # Tabela de partidas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jogo_id INTEGER NOT NULL,
                jogatina_id INTEGER,
                data DATE NOT NULL,
                valida_ranking TEXT DEFAULT 'S',
                eh_jogo_time TEXT DEFAULT 'N',
                observacoes TEXT,
                FOREIGN KEY (jogo_id) REFERENCES jogos(id),
                FOREIGN KEY (jogatina_id) REFERENCES jogatinas(id)
            )
        """)
        
        # Tabela de resultados (posições em cada partida)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partida_id INTEGER NOT NULL,
                jogador_id INTEGER NOT NULL,
                posicao INTEGER NOT NULL,
                pontuacao REAL,
                time_id INTEGER,
                FOREIGN KEY (partida_id) REFERENCES partidas(id),
                FOREIGN KEY (jogador_id) REFERENCES jogadores(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # === JOGADORES ===
    def add_jogador(self, nome, elo=1500):
        conn = self.get_connection()
        try:
            conn.execute("INSERT INTO jogadores (nome, elo) VALUES (?, ?)", (nome, elo))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_jogadores(self, apenas_ativos=True):
        conn = self.get_connection()
        if apenas_ativos:
            query = "SELECT * FROM jogadores WHERE ativo = 1 ORDER BY nome"
        else:
            query = "SELECT * FROM jogadores ORDER BY nome"
        df = pd.read_sql_query(query, conn)
        conn.close()
        # Retorna cópia para evitar cache do Streamlit
        return df.copy()
    
    def desativar_jogador(self, jogador_id):
        jogador_id = int(jogador_id)
        conn = self.get_connection()
        conn.execute("UPDATE jogadores SET ativo = 0 WHERE id = ?", (jogador_id,))
        conn.commit()
        conn.close()
    
    def reativar_jogador(self, jogador_id):
        """Reativa um jogador desativado"""
        jogador_id = int(jogador_id)
        conn = self.get_connection()
        conn.execute("UPDATE jogadores SET ativo = 1 WHERE id = ?", (jogador_id,))
        conn.commit()
        conn.close()
    
    def update_jogador(self, jogador_id, nome):
        """Atualiza dados de um jogador (apenas nome - ELO é calculado)"""
        jogador_id = int(jogador_id)
        conn = self.get_connection()
        try:
            conn.execute("UPDATE jogadores SET nome = ? WHERE id = ?", (nome, jogador_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    # === JOGATINAS ===
    def add_jogatina(self, data, local=None, observacoes=None):
        """Adiciona uma nova jogatina (sessão de jogos)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jogatinas (data, local, observacoes) VALUES (?, ?, ?)",
            (data, local, observacoes)
        )
        jogatina_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jogatina_id
    
    def get_jogatinas(self, limit=None):
        conn = self.get_connection()
        query = "SELECT * FROM jogatinas ORDER BY data DESC"
        if limit:
            query += f" LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_jogatina_by_id(self, jogatina_id):
        conn = self.get_connection()
        query = "SELECT * FROM jogatinas WHERE id = ?"
        df = pd.read_sql_query(query, conn, params=(jogatina_id,))
        conn.close()
        return df.iloc[0] if len(df) > 0 else None
    
    def get_or_create_jogatina(self, data, local=None):
        """Pega jogatina da data ou cria se não existir"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tenta achar
        result = cursor.execute("SELECT id FROM jogatinas WHERE data = ?", (data,)).fetchone()
        
        if result:
            jogatina_id = int(result[0])  # Força int
            conn.close()
            return jogatina_id
        else:
            # Cria nova
            cursor.execute("INSERT INTO jogatinas (data, local) VALUES (?, ?)", (data, local))
            jogatina_id = int(cursor.lastrowid)  # Força int
            conn.commit()
            conn.close()
            return jogatina_id
    
    # === JOGOS ===
    def add_jogo(self, nome, peso_bgg=2.0, bgg_id=None, link_bgg=None, 
                 min_jogadores=None, max_jogadores=None, tempo_min=None, 
                 tempo_max=None, tipo=None, categoria=None, mecanicas=None,
                 ano_publicacao=None):
        conn = self.get_connection()
        try:
            conn.execute("""
                INSERT INTO jogos 
                (nome, peso_bgg, bgg_id, link_bgg, min_jogadores, max_jogadores, 
                 tempo_min, tempo_max, tipo, categoria, mecanicas, ano_publicacao, ultima_atualizacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATE('now'))
            """, (nome, peso_bgg, bgg_id, link_bgg, min_jogadores, max_jogadores,
                  tempo_min, tempo_max, tipo, categoria, mecanicas, ano_publicacao))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def update_jogo_bgg(self, jogo_id, bgg_data):
        """Atualiza dados de um jogo com informações do BGG"""
        jogo_id = int(jogo_id)
        conn = self.get_connection()
        conn.execute("""
            UPDATE jogos 
            SET peso_bgg = ?, min_jogadores = ?, max_jogadores = ?,
                tempo_min = ?, tempo_max = ?, tipo = ?, categoria = ?,
                mecanicas = ?, ano_publicacao = ?, link_bgg = ?, bgg_id = ?,
                ultima_atualizacao = DATE('now')
            WHERE id = ?
        """, (
            bgg_data.get('peso'),
            bgg_data.get('min_jogadores'),
            bgg_data.get('max_jogadores'),
            bgg_data.get('tempo_min'),
            bgg_data.get('tempo_max'),
            bgg_data.get('tipo'),
            bgg_data.get('categoria'),
            bgg_data.get('mecanicas'),
            bgg_data.get('ano_publicacao'),
            bgg_data.get('link_bgg'),
            bgg_data.get('bgg_id'),
            jogo_id
        ))
        conn.commit()
        conn.close()
    
    def get_jogos(self, apenas_ativos=True):
        conn = self.get_connection()
        if apenas_ativos:
            query = "SELECT * FROM jogos WHERE ativo = 1 ORDER BY nome"
        else:
            query = "SELECT * FROM jogos ORDER BY nome"
        df = pd.read_sql_query(query, conn)
        conn.close()
        # Retorna cópia para evitar cache do Streamlit
        return df.copy()
    
    def update_jogo(self, jogo_id, dados):
        """Atualiza informações de um jogo"""
        jogo_id = int(jogo_id)
        conn = self.get_connection()
        try:
            conn.execute("""
                UPDATE jogos 
                SET nome = ?, peso_bgg = ?, min_jogadores = ?, max_jogadores = ?,
                    tempo_min = ?, tempo_max = ?, tipo = ?, categoria = ?,
                    mecanicas = ?, link_bgg = ?
                WHERE id = ?
            """, (
                dados.get('nome'),
                dados.get('peso_bgg'),
                dados.get('min_jogadores'),
                dados.get('max_jogadores'),
                dados.get('tempo_min'),
                dados.get('tempo_max'),
                dados.get('tipo'),
                dados.get('categoria'),
                dados.get('mecanicas'),
                dados.get('link_bgg'),
                jogo_id
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar jogo: {e}")
            return False
        finally:
            conn.close()
    
    def desativar_jogo(self, jogo_id):
        jogo_id = int(jogo_id)
        conn = self.get_connection()
        conn.execute("UPDATE jogos SET ativo = 0 WHERE id = ?", (jogo_id,))
        conn.commit()
        conn.close()
    
    def reativar_jogo(self, jogo_id):
        """Reativa um jogo desativado"""
        jogo_id = int(jogo_id)
        conn = self.get_connection()
        conn.execute("UPDATE jogos SET ativo = 1 WHERE id = ?", (jogo_id,))
        conn.commit()
        conn.close()
    
    # === PARTIDAS ===
    def add_partida(self, jogo_id, data, jogadores_posicoes, observacoes="", 
                    jogatina_id=None, valida_ranking='S', eh_jogo_time='N'):
        """
        jogadores_posicoes: lista de tuplas [(jogador_id, posicao, pontuacao, time_id), ...]
        time_id é opcional, só usado se eh_jogo_time='S'
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Converte IDs para int nativo (evita BLOB)
            jogo_id = int(jogo_id)
            if jogatina_id is not None:
                jogatina_id = int(jogatina_id)
            
            # Cria jogatina se não existir
            if jogatina_id is None:
                jogatina_id = self.get_or_create_jogatina(data)
            
            # Insere partida
            cursor.execute(
                """INSERT INTO partidas 
                   (jogo_id, data, observacoes, jogatina_id, valida_ranking, eh_jogo_time) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (jogo_id, data, observacoes, jogatina_id, valida_ranking, eh_jogo_time)
            )
            partida_id = cursor.lastrowid
            
            # Insere resultados
            for item in jogadores_posicoes:
                if len(item) == 3:
                    jogador_id, posicao, pontuacao = item
                    time_id = None
                else:
                    jogador_id, posicao, pontuacao, time_id = item
                
                # Converte todos os IDs para int nativo
                jogador_id = int(jogador_id)
                posicao = int(posicao)
                if time_id is not None:
                    time_id = int(time_id)
                
                cursor.execute(
                    """INSERT INTO resultados 
                       (partida_id, jogador_id, posicao, pontuacao, time_id) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (partida_id, jogador_id, posicao, pontuacao, time_id)
                )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Erro ao adicionar partida: {e}")
            return False
        finally:
            conn.close()
    
    def get_partidas(self, limit=None):
        conn = self.get_connection()
        query = """
            SELECT 
                p.id,
                p.data,
                j.nome as jogo,
                j.peso_bgg,
                p.valida_ranking,
                p.eh_jogo_time,
                GROUP_CONCAT(jog.nome || ' (' || r.posicao || '°)') as jogadores
            FROM partidas p
            JOIN jogos j ON p.jogo_id = j.id
            JOIN resultados r ON p.id = r.partida_id
            JOIN jogadores jog ON r.jogador_id = jog.id
            GROUP BY p.id
            ORDER BY p.id DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        # Retorna cópia para evitar cache do Streamlit
        return df.copy()
    
    def get_partida_detalhes(self, partida_id):
        """Retorna detalhes completos de uma partida"""
        # Força int nativo (evita problemas com numpy.int64)
        partida_id = int(partida_id)
        
        conn = self.get_connection()
        
        # Dados da partida
        partida_query = """
            SELECT p.*, j.nome as jogo_nome
            FROM partidas p
            JOIN jogos j ON p.jogo_id = j.id
            WHERE p.id = ?
        """
        partida = pd.read_sql_query(partida_query, conn, params=(partida_id,))
        
        # Resultados
        resultados_query = """
            SELECT r.*, jog.nome as jogador_nome
            FROM resultados r
            JOIN jogadores jog ON r.jogador_id = jog.id
            WHERE r.partida_id = ?
            ORDER BY r.posicao
        """
        resultados = pd.read_sql_query(resultados_query, conn, params=(partida_id,))
        
        conn.close()
        return partida.iloc[0] if len(partida) > 0 else None, resultados
    
    def delete_partida(self, partida_id):
        """Exclui uma partida e seus resultados"""
        partida_id = int(partida_id)
        conn = self.get_connection()
        try:
            # Deleta resultados primeiro (FK constraint)
            conn.execute("DELETE FROM resultados WHERE partida_id = ?", (partida_id,))
            # Deleta partida
            conn.execute("DELETE FROM partidas WHERE id = ?", (partida_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Erro ao deletar partida: {e}")
            return False
        finally:
            conn.close()
    
    def update_partida(self, partida_id, jogo_id, data, jogadores_posicoes, 
                      observacoes="", valida_ranking='S', eh_jogo_time='N'):
        """Atualiza uma partida existente"""
        partida_id = int(partida_id)
        jogo_id = int(jogo_id)
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Atualiza partida
            cursor.execute("""
                UPDATE partidas 
                SET jogo_id = ?, data = ?, observacoes = ?, 
                    valida_ranking = ?, eh_jogo_time = ?
                WHERE id = ?
            """, (jogo_id, data, observacoes, valida_ranking, eh_jogo_time, partida_id))
            
            # Deleta resultados antigos
            cursor.execute("DELETE FROM resultados WHERE partida_id = ?", (partida_id,))
            
            # Insere novos resultados
            for item in jogadores_posicoes:
                if len(item) == 3:
                    jogador_id, posicao, pontuacao = item
                    time_id = None
                else:
                    jogador_id, posicao, pontuacao, time_id = item
                
                cursor.execute(
                    """INSERT INTO resultados 
                       (partida_id, jogador_id, posicao, pontuacao, time_id) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (partida_id, jogador_id, posicao, pontuacao, time_id)
                )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Erro ao atualizar partida: {e}")
            return False
        finally:
            conn.close()
    
    def get_todas_partidas_jogador(self, jogador_id, limit=40, apenas_validas=True):
        """Retorna as últimas N partidas de um jogador para cálculo de ranking"""
        jogador_id = int(jogador_id)
        conn = self.get_connection()
        
        filtro_valida = "AND p.valida_ranking = 'S'" if apenas_validas else ""
        
        query = f"""
            SELECT 
                p.id as partida_id,
                p.data,
                p.eh_jogo_time,
                j.nome as jogo,
                j.peso_bgg as peso,
                r.posicao,
                r.pontuacao,
                r.time_id,
                (SELECT MAX(posicao) FROM resultados WHERE partida_id = p.id) as total_jogadores
            FROM resultados r
            JOIN partidas p ON r.partida_id = p.id
            JOIN jogos j ON p.jogo_id = j.id
            WHERE r.jogador_id = ?
            {filtro_valida}
            ORDER BY p.id DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(jogador_id, limit))
        conn.close()
        return df
    
    def backup_bytes(self) -> tuple[bytes, str]:
        """
        Gera um backup consistente do SQLite e devolve:
        - bytes do arquivo .db
        - nome sugerido do arquivo
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"jogos_backup_{ts}.db"

        # cria backup num arquivo temporário, depois lê como bytes
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_path = Path(tmpdir) / filename

            src = sqlite3.connect(self.db_name, timeout=30)
            try:
                dst = sqlite3.connect(str(backup_path))
                try:
                    src.backup(dst)   # backup consistente
                    dst.commit()
                finally:
                    dst.close()
            finally:
                src.close()

            data = backup_path.read_bytes()

        return data, filename
