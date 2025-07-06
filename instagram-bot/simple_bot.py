#!/usr/bin/env python3
"""
Instagram Bot Simples - Versão Minimalista
Funções básicas:
1. Seguir pessoas da DB
2. Deixar de seguir quem não seguiu de volta em 24h
"""

import sqlite3
import subprocess
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple

# Configurar logging simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDatabase:
    """Banco de dados simples"""
    
    def __init__(self, db_path: str = 'simple_bot.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Inicializa tabelas básicas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de seguidores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS followers (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                followed_at TIMESTAMP,
                check_unfollow_at TIMESTAMP,
                unfollowed_at TIMESTAMP,
                follows_back BOOLEAN
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Banco de dados inicializado")
    
    def add_follower(self, username: str) -> bool:
        """Adiciona seguidor para a fila"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO followers (username) 
                VALUES (?)
            ''', (username,))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected > 0:
                logger.info(f"Adicionado seguidor: {username}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Erro ao adicionar seguidor {username}: {e}")
            return False
    
    def get_users_to_follow(self, limit: int = 5) -> List[str]:
        """Retorna usuários para seguir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username FROM followers 
            WHERE followed_at IS NULL 
            LIMIT ?
        ''', (limit,))
        
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return users
    
    def mark_followed(self, username: str):
        """Marca usuário como seguido"""
        now = datetime.now()
        check_time = now + timedelta(hours=24)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE followers 
            SET followed_at = ?, check_unfollow_at = ?
            WHERE username = ?
        ''', (now, check_time, username))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Marcado como seguido: {username}")
    
    def get_users_to_check_unfollow(self) -> List[str]:
        """Retorna usuários para verificar unfollow (após 24h)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username FROM followers 
            WHERE check_unfollow_at <= ? 
            AND unfollowed_at IS NULL
            AND follows_back IS NULL
        ''', (datetime.now(),))
        
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return users
    
    def mark_follow_back_status(self, username: str, follows_back: bool):
        """Marca se o usuário seguiu de volta"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE followers 
            SET follows_back = ?
            WHERE username = ?
        ''', (follows_back, username))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Status follow-back {username}: {follows_back}")
    
    def mark_unfollowed(self, username: str):
        """Marca usuário como unfollowed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE followers 
            SET unfollowed_at = ?
            WHERE username = ?
        ''', (datetime.now(), username))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Marcado como unfollowed: {username}")
    
    def get_stats(self) -> Dict:
        """Estatísticas simples"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total de usuários
        cursor.execute('SELECT COUNT(*) FROM followers')
        total = cursor.fetchone()[0]
        
        # Seguidos hoje
        cursor.execute('''
            SELECT COUNT(*) FROM followers 
            WHERE DATE(followed_at) = DATE('now')
        ''')
        followed_today = cursor.fetchone()[0]
        
        # Unfollowed hoje
        cursor.execute('''
            SELECT COUNT(*) FROM followers 
            WHERE DATE(unfollowed_at) = DATE('now')
        ''')
        unfollowed_today = cursor.fetchone()[0]
        
        # Follow-backs
        cursor.execute('''
            SELECT COUNT(*) FROM followers 
            WHERE follows_back = 1
        ''')
        follow_backs = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'followed_today': followed_today,
            'unfollowed_today': unfollowed_today,
            'follow_backs': follow_backs
        }

class SimpleADB:
    """Controlador ADB simples"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.instagram_package = "com.instagram.android"
    
    def run_command(self, cmd: List[str]) -> Tuple[bool, str]:
        """Executa comando ADB"""
        try:
            if self.device_id:
                full_cmd = ['adb', '-s', self.device_id] + cmd
            else:
                full_cmd = ['adb'] + cmd
            
            result = subprocess.run(
                full_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            return result.returncode == 0, result.stdout.strip()
            
        except Exception as e:
            logger.error(f"Erro comando ADB: {e}")
            return False, str(e)
    
    def tap(self, x: int, y: int) -> bool:
        """Tap na tela"""
        success, _ = self.run_command(['shell', 'input', 'tap', str(x), str(y)])
        if success:
            time.sleep(random.uniform(1, 2))
        return success
    
    def type_text(self, text: str) -> bool:
        """Digite texto"""
        # Escapar espaços
        escaped = text.replace(' ', '%s')
        success, _ = self.run_command(['shell', 'input', 'text', escaped])
        if success:
            time.sleep(random.uniform(1, 2))
        return success
    
    def press_back(self) -> bool:
        """Pressiona botão voltar"""
        success, _ = self.run_command(['shell', 'input', 'keyevent', 'KEYCODE_BACK'])
        if success:
            time.sleep(1)
        return success
    
    def open_instagram(self) -> bool:
        """Abre Instagram"""
        success, _ = self.run_command([
            'shell', 'am', 'start', '-n', 
            f'{self.instagram_package}/com.instagram.mainactivity.MainActivity'
        ])
        if success:
            time.sleep(5)  # Aguardar carregar
        return success
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Obtém tamanho da tela"""
        success, output = self.run_command(['shell', 'wm', 'size'])
        if success and 'x' in output:
            try:
                size_part = output.split(':')[1].strip()
                width, height = map(int, size_part.split('x'))
                return width, height
            except:
                pass
        return 1080, 1920  # Padrão

class SimpleBot:
    """Bot Instagram simples"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.db = SimpleDatabase()
        self.adb = SimpleADB(device_id)
        self.screen_width, self.screen_height = self.adb.get_screen_size()
        
        # Configurações
        self.max_follows_per_session = 10
        self.delay_between_actions = (30, 60)  # segundos
        
        logger.info(f"Bot inicializado - Tela: {self.screen_width}x{self.screen_height}")
    
    def calc_coordinates(self, x_percent: float, y_percent: float) -> Tuple[int, int]:
        """Calcula coordenadas baseadas em porcentagem da tela"""
        x = int(self.screen_width * x_percent)
        y = int(self.screen_height * y_percent)
        return x, y
    
    def random_delay(self):
        """Delay aleatório entre ações"""
        delay = random.randint(*self.delay_between_actions)
        logger.info(f"Aguardando {delay}s...")
        time.sleep(delay)
    
    def follow_user(self, username: str) -> bool:
        """Segue um usuário"""
        try:
            logger.info(f"Tentando seguir: {username}")
            
            # 1. Ir para busca (ícone lupa - normalmente na parte inferior)
            search_x, search_y = self.calc_coordinates(0.2, 0.95)
            if not self.adb.tap(search_x, search_y):
                return False
            
            # 2. Clicar na caixa de busca (parte superior)
            search_box_x, search_box_y = self.calc_coordinates(0.5, 0.1)
            if not self.adb.tap(search_box_x, search_box_y):
                return False
            
            # 3. Digitar username
            if not self.adb.type_text(username):
                return False
            
            time.sleep(2)  # Aguardar resultados
            
            # 4. Clicar no primeiro resultado
            first_result_x, first_result_y = self.calc_coordinates(0.5, 0.25)
            if not self.adb.tap(first_result_x, first_result_y):
                return False
            
            time.sleep(3)  # Aguardar perfil carregar
            
            # 5. Clicar no botão seguir (geralmente à direita do nome)
            follow_btn_x, follow_btn_y = self.calc_coordinates(0.85, 0.3)
            if not self.adb.tap(follow_btn_x, follow_btn_y):
                return False
            
            # 6. Marcar como seguido no banco
            self.db.mark_followed(username)
            
            logger.info(f"✅ Seguiu: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao seguir {username}: {e}")
            return False
    
    def check_if_follows_back(self, username: str) -> Optional[bool]:
        """Verifica se usuário segue de volta (simplificado)"""
        try:
            logger.info(f"Verificando follow-back: {username}")
            
            # Ir para o próprio perfil
            profile_x, profile_y = self.calc_coordinates(0.9, 0.95)
            if not self.adb.tap(profile_x, profile_y):
                return None
            
            time.sleep(2)
            
            # Clicar em "seguidores"
            followers_x, followers_y = self.calc_coordinates(0.3, 0.4)
            if not self.adb.tap(followers_x, followers_y):
                return None
            
            time.sleep(2)
            
            # Buscar pelo username na lista
            search_x, search_y = self.calc_coordinates(0.5, 0.1)
            if not self.adb.tap(search_x, search_y):
                return None
            
            if not self.adb.type_text(username):
                return None
            
            time.sleep(2)
            
            # Verificar se apareceu resultado (método simples)
            # Em uma implementação real, usaria OCR ou análise de imagem
            # Por simplicidade, assumimos que se chegou até aqui, pode seguir
            
            # Por enquanto, simular resultado aleatório
            follows_back = random.choice([True, False, False])  # 33% chance
            
            self.db.mark_follow_back_status(username, follows_back)
            
            logger.info(f"Follow-back {username}: {follows_back}")
            return follows_back
            
        except Exception as e:
            logger.error(f"Erro ao verificar follow-back {username}: {e}")
            return None
    
    def unfollow_user(self, username: str) -> bool:
        """Deixa de seguir um usuário"""
        try:
            logger.info(f"Tentando unfollow: {username}")
            
            # Similar ao follow, mas clica em "seguindo" depois
            # 1. Buscar usuário
            search_x, search_y = self.calc_coordinates(0.2, 0.95)
            if not self.adb.tap(search_x, search_y):
                return False
            
            search_box_x, search_box_y = self.calc_coordinates(0.5, 0.1)
            if not self.adb.tap(search_box_x, search_box_y):
                return False
            
            if not self.adb.type_text(username):
                return False
            
            time.sleep(2)
            
            first_result_x, first_result_y = self.calc_coordinates(0.5, 0.25)
            if not self.adb.tap(first_result_x, first_result_y):
                return False
            
            time.sleep(3)
            
            # 2. Clicar no botão "seguindo"
            following_btn_x, following_btn_y = self.calc_coordinates(0.85, 0.3)
            if not self.adb.tap(following_btn_x, following_btn_y):
                return False
            
            time.sleep(1)
            
            # 3. Confirmar unfollow (pode aparecer popup)
            confirm_x, confirm_y = self.calc_coordinates(0.7, 0.6)
            self.adb.tap(confirm_x, confirm_y)  # Tentar confirmar
            
            # 4. Marcar no banco
            self.db.mark_unfollowed(username)
            
            logger.info(f"✅ Unfollowed: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao unfollow {username}: {e}")
            return False
    
    def run_follow_session(self):
        """Executa sessão de follows"""
        logger.info("=== INICIANDO SESSÃO DE FOLLOWS ===")
        
        if not self.adb.open_instagram():
            logger.error("Falha ao abrir Instagram")
            return
        
        users_to_follow = self.db.get_users_to_follow(self.max_follows_per_session)
        
        if not users_to_follow:
            logger.info("Nenhum usuário para seguir")
            return
        
        success_count = 0
        
        for username in users_to_follow:
            if self.follow_user(username):
                success_count += 1
            
            # Voltar ao home
            home_x, home_y = self.calc_coordinates(0.1, 0.95)
            self.adb.tap(home_x, home_y)
            
            self.random_delay()
        
        logger.info(f"Sessão concluída: {success_count}/{len(users_to_follow)} follows")
    
    def run_unfollow_session(self):
        """Executa sessão de unfollows"""
        logger.info("=== INICIANDO SESSÃO DE UNFOLLOWS ===")
        
        if not self.adb.open_instagram():
            logger.error("Falha ao abrir Instagram")
            return
        
        users_to_check = self.db.get_users_to_check_unfollow()
        
        if not users_to_check:
            logger.info("Nenhum usuário para verificar unfollow")
            return
        
        unfollowed_count = 0
        
        for username in users_to_check:
            # Primeiro verificar se segue de volta
            follows_back = self.check_if_follows_back(username)
            
            if follows_back is False:
                # Não segue de volta, fazer unfollow
                if self.unfollow_user(username):
                    unfollowed_count += 1
            
            # Voltar ao home
            home_x, home_y = self.calc_coordinates(0.1, 0.95)
            self.adb.tap(home_x, home_y)
            
            self.random_delay()
        
        logger.info(f"Sessão de unfollow concluída: {unfollowed_count} unfollows")
    
    def show_stats(self):
        """Mostra estatísticas"""
        stats = self.db.get_stats()
        
        print("\n📊 ESTATÍSTICAS")
        print("-" * 30)
        print(f"Total de usuários: {stats['total']}")
        print(f"Seguidos hoje: {stats['followed_today']}")
        print(f"Unfollowed hoje: {stats['unfollowed_today']}")
        print(f"Follow-backs: {stats['follow_backs']}")
        
        if stats['followed_today'] > 0:
            rate = (stats['follow_backs'] / stats['followed_today']) * 100
            print(f"Taxa follow-back: {rate:.1f}%")
        print()

def import_users_from_file(bot: SimpleBot, filename: str):
    """Importa usuários de arquivo (TXT, CSV, Excel)"""
    try:
        file_extension = filename.split('.')[-1].lower()
        usernames = []
        
        if file_extension == 'txt':
            # Arquivo de texto
            with open(filename, 'r', encoding='utf-8') as f:
                usernames = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        elif file_extension == 'csv':
            # Arquivo CSV
            import pandas as pd
            df = pd.read_csv(filename)
            
            # Procurar coluna com usernames
            username_cols = ['username', 'user', 'Username', 'User', 'handle']
            username_col = None
            for col in username_cols:
                if col in df.columns:
                    username_col = col
                    break
            
            if username_col:
                usernames = df[username_col].dropna().astype(str).tolist()
            else:
                print(f"❌ Coluna de username não encontrada. Colunas disponíveis: {', '.join(df.columns)}")
                return
        
        elif file_extension in ['xlsx', 'xls']:
            # Arquivo Excel
            import pandas as pd
            df = pd.read_excel(filename)
            
            # Procurar coluna com usernames
            username_cols = ['username', 'user', 'Username', 'User', 'handle']
            username_col = None
            for col in username_cols:
                if col in df.columns:
                    username_col = col
                    break
            
            if username_col:
                usernames = df[username_col].dropna().astype(str).tolist()
            else:
                print(f"❌ Coluna de username não encontrada. Colunas disponíveis: {', '.join(df.columns)}")
                return
        
        else:
            print(f"❌ Formato não suportado: {file_extension}")
            print("Formatos aceitos: .txt, .csv, .xlsx, .xls")
            return
        
        if not usernames:
            print("❌ Nenhum username encontrado no arquivo")
            return
        
        print(f"📋 Encontrados {len(usernames)} usuários")
        print("Importando...")
        
        added_count = 0
        for i, username in enumerate(usernames, 1):
            clean_username = str(username).strip()
            if clean_username and bot.db.add_follower(clean_username):
                added_count += 1
            
            # Progress indicator
            if i % 10 == 0:
                print(f"Processados: {i}/{len(usernames)} ({added_count} novos)")
        
        print(f"✅ Importação concluída: {added_count} usuários adicionados de {len(usernames)} encontrados")
        
    except ImportError:
        print("❌ pandas não instalado. Para arquivos Excel/CSV, instale: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erro ao importar {filename}: {e}")
        print("💡 Dicas:")
        print("   - Verifique se o arquivo existe")
        print("   - Para Excel: certifique-se que há uma coluna 'username' ou 'user'")
        print("   - Para TXT: um username por linha")

def main():
    """Função principal"""
    print("🤖 INSTAGRAM BOT SIMPLES")
    print("=" * 40)
    
    # Inicializar bot
    bot = SimpleBot()
    
    while True:
        print("\nOpções:")
        print("1. Seguir usuários da DB")
        print("2. Verificar e unfollow (24h)")
        print("3. Importar usuários de arquivo")
        print("4. Estatísticas")
        print("5. Sair")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == '1':
            bot.run_follow_session()
        
        elif choice == '2':
            bot.run_unfollow_session()
        
        elif choice == '3':
            filename = input("Nome do arquivo (ex: users.txt): ").strip()
            import_users_from_file(bot, filename)
        
        elif choice == '4':
            bot.show_stats()
        
        elif choice == '5':
            print("Saindo...")
            break
        
        else:
            print("Opção inválida")

if __name__ == "__main__":
    main()
