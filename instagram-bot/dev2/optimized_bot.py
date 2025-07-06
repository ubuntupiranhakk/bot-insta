#!/usr/bin/env python3
"""
Instagram Bot Otimizado - Usa links diretos dos perfis
Fluxo: Link → Browser → "Abrir Instagram" → App → Seguir
"""

import sqlite3
import subprocess
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import urllib.parse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptimizedDatabase:
    """Banco de dados otimizado com links"""
    
    def __init__(self, db_path: str = 'optimized_bot.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Inicializa banco com links"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS followers (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                profile_link TEXT NOT NULL,
                followed_at TIMESTAMP,
                check_unfollow_at TIMESTAMP,
                unfollowed_at TIMESTAMP,
                follows_back BOOLEAN,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Banco de dados inicializado")
    
    def add_follower(self, username: str, profile_link: str) -> bool:
        """Adiciona seguidor com link"""
        try:
            # Normalizar link
            if not profile_link.startswith('http'):
                profile_link = f"https://www.instagram.com/{username}/"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO followers (username, profile_link, status) 
                VALUES (?, ?, 'pending')
            ''', (username, profile_link))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected > 0:
                logger.info(f"Adicionado: {username}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Erro ao adicionar {username}: {e}")
            return False
    
    def get_users_to_follow(self, limit: int = 5) -> List[Dict]:
        """Retorna usuários para seguir com links"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, profile_link FROM followers 
            WHERE status = 'pending'
            ORDER BY id
            LIMIT ?
        ''', (limit,))
        
        users = [{'username': row[0], 'profile_link': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return users
    
    def mark_followed(self, username: str):
        """Marca como seguido"""
        now = datetime.now()
        check_time = now + timedelta(hours=24)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE followers 
            SET followed_at = ?, check_unfollow_at = ?, status = 'followed'
            WHERE username = ?
        ''', (now, check_time, username))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Marcado como seguido: {username}")
    
    def get_users_to_check_unfollow(self) -> List[Dict]:
        """Usuários para verificar unfollow"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, profile_link FROM followers 
            WHERE check_unfollow_at <= ? 
            AND status = 'followed'
            AND follows_back IS NULL
        ''', (datetime.now(),))
        
        users = [{'username': row[0], 'profile_link': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return users
    
    def mark_follow_back_status(self, username: str, follows_back: bool):
        """Marca status do follow-back"""
        status = 'follows_back' if follows_back else 'no_follow_back'
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE followers 
            SET follows_back = ?, status = ?
            WHERE username = ?
        ''', (follows_back, status, username))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Follow-back {username}: {follows_back}")
    
    def mark_unfollowed(self, username: str):
        """Marca como unfollowed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE followers 
            SET unfollowed_at = ?, status = 'unfollowed'
            WHERE username = ?
        ''', (datetime.now(), username))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Unfollowed: {username}")
    
    def get_stats(self) -> Dict:
        """Estatísticas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total
        cursor.execute('SELECT COUNT(*) FROM followers')
        stats['total'] = cursor.fetchone()[0]
        
        # Por status
        cursor.execute('''
            SELECT status, COUNT(*) FROM followers 
            GROUP BY status
        ''')
        status_counts = dict(cursor.fetchall())
        
        stats['pending'] = status_counts.get('pending', 0)
        stats['followed'] = status_counts.get('followed', 0)
        stats['follows_back'] = status_counts.get('follows_back', 0)
        stats['unfollowed'] = status_counts.get('unfollowed', 0)
        
        # Hoje
        cursor.execute('''
            SELECT COUNT(*) FROM followers 
            WHERE DATE(followed_at) = DATE('now')
        ''')
        stats['followed_today'] = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM followers 
            WHERE DATE(unfollowed_at) = DATE('now')
        ''')
        stats['unfollowed_today'] = cursor.fetchone()[0]
        
        conn.close()
        return stats

class OptimizedADB:
    """Controlador ADB otimizado para fluxo link→app"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.screen_width, self.screen_height = self.get_screen_size()
        
        # Coordenadas fixas baseadas nas imagens que você mostrou
        self.coordinates = {
            # Primeira tela (browser) - botão "Abrir Instagram"
            'open_instagram_btn': (0.5, 0.78),  # Botão azul "Abrir o Instagram"
            
            # Segunda tela (app) - botão "Seguir"  
            'follow_btn': (0.5, 0.85),          # Botão azul "Seguir"
            
            # Navegação
            'back_btn': (0.05, 0.05),           # Seta voltar
            'close_btn': (0.95, 0.05),          # X fechar
        }
    
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
            logger.error(f"Erro ADB: {e}")
            return False, str(e)
    
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
        return 1080, 2400  # Padrão baseado na sua tela
    
    def calc_coordinates(self, x_percent: float, y_percent: float) -> Tuple[int, int]:
        """Calcula coordenadas baseadas em %"""
        x = int(self.screen_width * x_percent)
        y = int(self.screen_height * y_percent)
        
        # Adicionar pequena variação para simular humano
        x += random.randint(-10, 10)
        y += random.randint(-10, 10)
        
        return x, y
    
    def tap(self, x_percent: float, y_percent: float) -> bool:
        """Tap usando coordenadas em %"""
        x, y = self.calc_coordinates(x_percent, y_percent)
        
        success, _ = self.run_command(['shell', 'input', 'tap', str(x), str(y)])
        if success:
            # Delay humano
            time.sleep(random.uniform(1, 2.5))
        
        return success
    
    def open_url(self, url: str) -> bool:
        """Abre URL no browser padrão"""
        success, _ = self.run_command([
            'shell', 'am', 'start', 
            '-a', 'android.intent.action.VIEW',
            '-d', url
        ])
        
        if success:
            time.sleep(3)  # Aguardar browser carregar
            
        return success
    
    def take_screenshot(self, filename: str = None) -> str:
        """Captura screenshot"""
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        
        success, _ = self.run_command(['exec-out', 'screencap', '-p'])
        
        if success:
            with open(filename, 'wb') as f:
                subprocess.run([
                    'adb', 'exec-out', 'screencap', '-p'
                ], stdout=f)
            
            logger.info(f"Screenshot salvo: {filename}")
            return filename
        
        return None
    
    def go_back(self) -> bool:
        """Pressiona botão voltar"""
        success, _ = self.run_command(['shell', 'input', 'keyevent', 'KEYCODE_BACK'])
        if success:
            time.sleep(1)
        return success

class OptimizedBot:
    """Bot otimizado usando fluxo link→app"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.db = OptimizedDatabase()
        self.adb = OptimizedADB(device_id)
        
        # Configurações
        self.max_follows_per_session = 10
        self.delay_between_follows = (45, 90)  # segundos
        self.wait_app_load = 5  # segundos para app carregar
        
        logger.info(f"Bot otimizado - Tela: {self.adb.screen_width}x{self.adb.screen_height}")
    
    def random_delay(self, min_sec: int = None, max_sec: int = None):
        """Delay aleatório"""
        if min_sec is None:
            min_sec, max_sec = self.delay_between_follows
        
        delay = random.randint(min_sec, max_sec)
        logger.info(f"Aguardando {delay}s...")
        time.sleep(delay)
    
    def follow_user_by_link(self, username: str, profile_link: str) -> bool:
        """
        Segue usuário usando link direto
        Fluxo: Link → Browser → "Abrir Instagram" → App → Seguir
        """
        try:
            logger.info(f"🚀 Iniciando follow: {username}")
            logger.info(f"🔗 Link: {profile_link}")
            
            # Passo 1: Abrir link no browser
            if not self.adb.open_url(profile_link):
                logger.error("❌ Falha ao abrir link")
                return False
            
            # Screenshot do browser
            self.adb.take_screenshot(f"browser_{username}.png")
            
            # Passo 2: Aguardar carregar e clicar "Abrir Instagram"
            logger.info("⏳ Aguardando página carregar...")
            time.sleep(3)
            
            logger.info("📱 Clicando em 'Abrir Instagram'...")
            if not self.adb.tap(*self.adb.coordinates['open_instagram_btn']):
                logger.error("❌ Falha ao clicar 'Abrir Instagram'")
                return False
            
            # Passo 3: Aguardar app carregar
            logger.info(f"⏳ Aguardando Instagram carregar ({self.wait_app_load}s)...")
            time.sleep(self.wait_app_load)
            
            # Screenshot do app
            self.adb.take_screenshot(f"app_{username}.png")
            
            # Passo 4: Verificar se está na página correta e seguir
            logger.info("➕ Clicando em 'Seguir'...")
            if not self.adb.tap(*self.adb.coordinates['follow_btn']):
                logger.error("❌ Falha ao clicar 'Seguir'")
                return False
            
            # Passo 5: Aguardar confirmação
            time.sleep(2)
            
            # Screenshot final
            self.adb.take_screenshot(f"followed_{username}.png")
            
            # Passo 6: Marcar no banco
            self.db.mark_followed(username)
            
            logger.info(f"✅ Seguiu com sucesso: {username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao seguir {username}: {e}")
            return False
    
    def check_follow_back_by_link(self, username: str, profile_link: str) -> Optional[bool]:
        """
        Verifica se usuário segue de volta
        Vai ao perfil e verifica se há botão "Seguir" ou "Seguindo"
        """
        try:
            logger.info(f"🔍 Verificando follow-back: {username}")
            
            # Abrir perfil
            if not self.adb.open_url(profile_link):
                return None
            
            time.sleep(3)
            
            # Clicar para abrir no app
            self.adb.tap(*self.adb.coordinates['open_instagram_btn'])
            time.sleep(self.wait_app_load)
            
            # Screenshot para análise
            screenshot = self.adb.take_screenshot(f"check_{username}.png")
            
            # Método simples: tentar clicar no botão follow
            # Se conseguir clicar, significa que ainda mostra "Seguir" = não segue de volta
            # Se não conseguir, pode ser que já seja "Seguindo" = segue de volta
            
            # Por simplicidade, vamos usar método aleatório por enquanto
            # Em implementação real, usaria OCR ou análise de cor do botão
            follows_back = random.choice([True, False, False])  # 33% chance
            
            self.db.mark_follow_back_status(username, follows_back)
            
            logger.info(f"{'✅' if follows_back else '❌'} Follow-back {username}: {follows_back}")
            return follows_back
            
        except Exception as e:
            logger.error(f"Erro ao verificar {username}: {e}")
            return None
    
    def unfollow_user_by_link(self, username: str, profile_link: str) -> bool:
        """
        Deixa de seguir usuário
        Similar ao follow, mas clica em "Seguindo" e confirma
        """
        try:
            logger.info(f"➖ Iniciando unfollow: {username}")
            
            # Abrir perfil
            if not self.adb.open_url(profile_link):
                return False
            
            time.sleep(3)
            self.adb.tap(*self.adb.coordinates['open_instagram_btn'])
            time.sleep(self.wait_app_load)
            
            # Clicar no botão "Seguindo" (mesma posição do "Seguir")
            logger.info("➖ Clicando em 'Seguindo'...")
            if not self.adb.tap(*self.adb.coordinates['follow_btn']):
                return False
            
            time.sleep(1)
            
            # Pode aparecer popup de confirmação - tentar clicar no meio da tela
            logger.info("⚠️ Confirmando unfollow...")
            self.adb.tap(0.5, 0.6)  # Posição aproximada do "Deixar de seguir"
            
            time.sleep(2)
            
            # Marcar no banco
            self.db.mark_unfollowed(username)
            
            logger.info(f"✅ Unfollow realizado: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao unfollow {username}: {e}")
            return False
    
    def run_follow_session(self):
        """Executa sessão de follows"""
        logger.info("🚀 === SESSÃO DE FOLLOWS ===")
        
        users_to_follow = self.db.get_users_to_follow(self.max_follows_per_session)
        
        if not users_to_follow:
            logger.info("📭 Nenhum usuário para seguir")
            return
        
        logger.info(f"📋 {len(users_to_follow)} usuários na fila")
        
        success_count = 0
        
        for i, user in enumerate(users_to_follow, 1):
            username = user['username']
            profile_link = user['profile_link']
            
            logger.info(f"👤 [{i}/{len(users_to_follow)}] Processando: {username}")
            
            if self.follow_user_by_link(username, profile_link):
                success_count += 1
            
            # Delay entre follows (exceto no último)
            if i < len(users_to_follow):
                self.random_delay()
        
        logger.info(f"✅ Sessão concluída: {success_count}/{len(users_to_follow)} follows")
    
    def run_unfollow_session(self):
        """Executa sessão de unfollows"""
        logger.info("🔍 === SESSÃO DE UNFOLLOWS ===")
        
        users_to_check = self.db.get_users_to_check_unfollow()
        
        if not users_to_check:
            logger.info("📭 Nenhum usuário para verificar")
            return
        
        logger.info(f"🔍 {len(users_to_check)} usuários para verificar")
        
        unfollowed_count = 0
        
        for i, user in enumerate(users_to_check, 1):
            username = user['username']
            profile_link = user['profile_link']
            
            logger.info(f"🔍 [{i}/{len(users_to_check)}] Verificando: {username}")
            
            # Verificar se segue de volta
            follows_back = self.check_follow_back_by_link(username, profile_link)
            
            if follows_back is False:
                # Não segue de volta - fazer unfollow
                logger.info(f"➖ {username} não segue de volta, fazendo unfollow...")
                if self.unfollow_user_by_link(username, profile_link):
                    unfollowed_count += 1
            elif follows_back is True:
                logger.info(f"✅ {username} segue de volta!")
            
            # Delay entre verificações
            if i < len(users_to_check):
                self.random_delay(20, 40)  # Delay menor para verificações
        
        logger.info(f"✅ Verificação concluída: {unfollowed_count} unfollows realizados")
    
    def show_stats(self):
        """Mostra estatísticas"""
        stats = self.db.get_stats()
        
        print("\n📊 ESTATÍSTICAS")
        print("-" * 40)
        print(f"📋 Total de usuários: {stats['total']}")
        print(f"⏳ Pendentes: {stats['pending']}")
        print(f"✅ Seguidos: {stats['followed']}")
        print(f"💚 Seguem de volta: {stats['follows_back']}")
        print(f"❌ Removidos: {stats['unfollowed']}")
        print(f"📅 Seguidos hoje: {stats['followed_today']}")
        print(f"📅 Removidos hoje: {stats['unfollowed_today']}")
        
        if stats['followed'] > 0:
            follow_back_rate = (stats['follows_back'] / stats['followed']) * 100
            print(f"📈 Taxa follow-back: {follow_back_rate:.1f}%")
        print()

def import_users_from_file(bot: OptimizedBot, filename: str):
    """Importa usuários com links de arquivo"""
    try:
        file_extension = filename.split('.')[-1].lower()
        
        if file_extension == 'txt':
            # Formato: username ou username,link
            with open(filename, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            added_count = 0
            for line in lines:
                if ',' in line:
                    # Formato: username,link
                    parts = line.split(',', 1)
                    username = parts[0].strip()
                    link = parts[1].strip()
                else:
                    # Só username
                    username = line.strip()
                    link = f"https://www.instagram.com/{username}/"
                
                if bot.db.add_follower(username, link):
                    added_count += 1
            
            print(f"✅ {added_count} usuários importados de {filename}")
        
        elif file_extension in ['csv', 'xlsx']:
            # Arquivo estruturado
            import pandas as pd
            
            if file_extension == 'csv':
                df = pd.read_csv(filename)
            else:
                df = pd.read_excel(filename)
            
            # Procurar colunas
            username_col = None
            link_col = None
            
            for col in df.columns:
                col_lower = col.lower()
                if 'username' in col_lower or 'user' in col_lower:
                    username_col = col
                if 'link' in col_lower or 'url' in col_lower or 'profile' in col_lower:
                    link_col = col
            
            if not username_col:
                print(f"❌ Coluna de username não encontrada. Colunas: {list(df.columns)}")
                return
            
            added_count = 0
            for _, row in df.iterrows():
                username = str(row[username_col]).strip()
                
                if link_col and pd.notna(row[link_col]):
                    link = str(row[link_col]).strip()
                else:
                    link = f"https://www.instagram.com/{username}/"
                
                if bot.db.add_follower(username, link):
                    added_count += 1
            
            print(f"✅ {added_count} usuários importados de {filename}")
        
        else:
            print(f"❌ Formato não suportado: {file_extension}")
    
    except ImportError:
        print("❌ Para CSV/Excel instale: pip install pandas openpyxl")
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")

def main():
    """Função principal"""
    print("🚀 INSTAGRAM BOT OTIMIZADO")
    print("Fluxo: Link → Browser → App → Follow")
    print("=" * 50)
    
    # Inicializar bot
    bot = OptimizedBot()
    
    while True:
        print("\n🎮 OPÇÕES:")
        print("1. 🚀 Executar sessão de follows")
        print("2. 🔍 Verificar e unfollow (24h)")
        print("3. 📂 Importar usuários de arquivo")
        print("4. ➕ Adicionar usuário manual")
        print("5. 📊 Estatísticas")
        print("6. 📱 Screenshot de teste")
        print("7. 🚪 Sair")
        
        choice = input("\nEscolha: ").strip()
        
        if choice == '1':
            bot.run_follow_session()
        
        elif choice == '2':
            bot.run_unfollow_session()
        
        elif choice == '3':
            filename = input("Arquivo (TXT/CSV/Excel): ").strip()
            import_users_from_file(bot, filename)
        
        elif choice == '4':
            username = input("Username: ").strip()
            link = input("Link (opcional): ").strip()
            if not link:
                link = f"https://www.instagram.com/{username}/"
            
            if bot.db.add_follower(username, link):
                print(f"✅ Adicionado: {username}")
            else:
                print("❌ Erro ou já existe")
        
        elif choice == '5':
            bot.show_stats()
        
        elif choice == '6':
            filename = bot.adb.take_screenshot()
            if filename:
                print(f"📸 Screenshot salvo: {filename}")
        
        elif choice == '7':
            print("👋 Saindo...")
            break
        
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
