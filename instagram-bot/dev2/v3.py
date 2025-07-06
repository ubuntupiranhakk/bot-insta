#!/usr/bin/env python3
"""
Instagram Bot Otimizado com OCR
Usa Tesseract para detectar botões com precisão
"""

import sqlite3
import subprocess
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class Database:
    """Banco de dados simplificado"""
    
    def __init__(self, db_path: str = 'bot.db'):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                profile_link TEXT,
                followed_at TIMESTAMP,
                check_at TIMESTAMP,
                unfollowed_at TIMESTAMP,
                follows_back BOOLEAN,
                status TEXT DEFAULT 'pending'
            )
        ''')
        conn.commit()
        conn.close()
    
    def add_user(self, username: str, link: str = None) -> bool:
        if not link:
            link = f"https://www.instagram.com/{username}/"
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('INSERT OR IGNORE INTO users (username, profile_link) VALUES (?, ?)', 
                        (username, link))
            affected = conn.total_changes
            conn.commit()
            conn.close()
            return affected > 0
        except:
            return False
    
    def get_pending_users(self, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('SELECT username, profile_link FROM users WHERE status = "pending" LIMIT ?', (limit,))
        users = [{'username': row[0], 'link': row[1]} for row in cursor.fetchall()]
        conn.close()
        return users
    
    def mark_followed(self, username: str):
        now = datetime.now()
        check_time = now + timedelta(hours=24)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute('''UPDATE users SET followed_at = ?, check_at = ?, status = "followed" 
                       WHERE username = ?''', (now, check_time, username))
        conn.commit()
        conn.close()
    
    def get_users_to_check(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute('''SELECT username, profile_link FROM users 
                               WHERE check_at <= ? AND status = "followed"''', (datetime.now(),))
        users = [{'username': row[0], 'link': row[1]} for row in cursor.fetchall()]
        conn.close()
        return users
    
    def mark_follow_status(self, username: str, follows_back: bool):
        status = 'mutual' if follows_back else 'no_follow_back'
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE users SET follows_back = ?, status = ? WHERE username = ?', 
                    (follows_back, status, username))
        conn.commit()
        conn.close()
    
    def mark_unfollowed(self, username: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE users SET unfollowed_at = ?, status = "unfollowed" WHERE username = ?', 
                    (datetime.now(), username))
        conn.commit()
        conn.close()
    
    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Contadores por status
        cursor.execute('SELECT status, COUNT(*) FROM users GROUP BY status')
        status_counts = dict(cursor.fetchall())
        
        # Ações hoje
        cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(followed_at) = DATE("now")')
        followed_today = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(unfollowed_at) = DATE("now")')
        unfollowed_today = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': sum(status_counts.values()),
            'pending': status_counts.get('pending', 0),
            'followed': status_counts.get('followed', 0),
            'mutual': status_counts.get('mutual', 0),
            'unfollowed': status_counts.get('unfollowed', 0),
            'followed_today': followed_today,
            'unfollowed_today': unfollowed_today
        }

class OCRHelper:
    """Helper para OCR com Tesseract"""
    
    def __init__(self):
        # Configurar Tesseract automaticamente
        try:
            from config import get_tesseract_path, OCR_LANGUAGES, OCR_CONFIG
            pytesseract.pytesseract.tesseract_cmd = get_tesseract_path()
            self.languages = OCR_LANGUAGES
            self.config = OCR_CONFIG
        except ImportError:
            # Fallback se config.py não existir
            import platform
            system = platform.system().lower()
            if 'windows' in system:
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            else:
                pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
            self.languages = 'por+eng'
            self.config = '--psm 6'
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extrai texto de uma imagem"""
        try:
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Melhorar contraste
            gray = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
            
            # Usar Tesseract
            text = pytesseract.image_to_string(gray, lang=self.languages, config=self.config)
            return text.strip()
        except Exception as e:
            logger.error(f"Erro OCR: {e}")
            return ""
    
    def find_button_coordinates(self, image_path: str, button_texts: List[str]) -> Optional[Tuple[int, int]]:
        """Encontra coordenadas de botões usando OCR"""
        try:
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Usar Tesseract para obter coordenadas
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT, 
                                           lang=self.languages, config=self.config)
            
            for i, text in enumerate(data['text']):
                # Verificar se o texto corresponde a algum botão
                text_clean = text.strip().lower()
                for button_text in button_texts:
                    if button_text.lower() in text_clean and len(text_clean) <= len(button_text) + 5:
                        # Calcular centro do texto
                        x = data['left'][i] + data['width'][i] // 2
                        y = data['top'][i] + data['height'][i] // 2
                        
                        logger.info(f"Botão '{button_text}' encontrado em ({x}, {y})")
                        return x, y
            
            logger.warning(f"Nenhum botão encontrado: {button_texts}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao procurar botão: {e}")
            return None
    
    def detect_button_color(self, image_path: str, x: int, y: int, radius: int = 50) -> str:
        """Detecta cor dominante em uma região (para verificar status do botão)"""
        try:
            img = cv2.imread(image_path)
            h, w = img.shape[:2]
            
            # Limitar coordenadas
            x = max(radius, min(x, w - radius))
            y = max(radius, min(y, h - radius))
            
            # Extrair região
            region = img[y-radius:y+radius, x-radius:x+radius]
            
            # Calcular cor média
            mean_color = np.mean(region, axis=(0, 1))
            b, g, r = mean_color
            
            # Classificar cor
            if r > 150 and g > 150 and b > 200:
                return "azul"  # Botão seguir
            elif r > 200 and g > 200 and b > 200:
                return "branco"  # Botão seguindo
            else:
                return "outro"
                
        except Exception as e:
            logger.error(f"Erro ao detectar cor: {e}")
            return "erro"

class ADB:
    """Controlador ADB simplificado"""
    
    def __init__(self, device_id: str = None):
        self.device_id = device_id
        self.screen_width, self.screen_height = self._get_screen_size()
    
    def _run_cmd(self, cmd: List[str]) -> Tuple[bool, str]:
        """Executa comando ADB"""
        try:
            full_cmd = ['adb'] + (['-s', self.device_id] if self.device_id else []) + cmd
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout.strip()
        except Exception as e:
            logger.error(f"Erro ADB: {e}")
            return False, str(e)
    
    def _get_screen_size(self) -> Tuple[int, int]:
        """Obtém dimensões da tela"""
        success, output = self._run_cmd(['shell', 'wm', 'size'])
        if success and 'x' in output:
            try:
                size = output.split(':')[1].strip()
                w, h = map(int, size.split('x'))
                return w, h
            except:
                pass
        return 1080, 2400  # Padrão
    
    def tap(self, x: int, y: int) -> bool:
        """Tap com variação humana"""
        # Adicionar pequena variação
        x += random.randint(-5, 5)
        y += random.randint(-5, 5)
        
        # Limitar à tela
        x = max(0, min(x, self.screen_width))
        y = max(0, min(y, self.screen_height))
        
        success, _ = self._run_cmd(['shell', 'input', 'tap', str(x), str(y)])
        if success:
            time.sleep(random.uniform(1, 2))
        return success
    
    def open_url(self, url: str) -> bool:
        """Abre URL no navegador"""
        success, _ = self._run_cmd(['shell', 'am', 'start', '-a', 'android.intent.action.VIEW', '-d', url])
        if success:
            time.sleep(3)
        return success
    
    def screenshot(self, filename: str = None) -> str:
        """Captura screenshot"""
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
        
        success, _ = self._run_cmd(['exec-out', 'screencap', '-p'])
        if success:
            with open(filename, 'wb') as f:
                subprocess.run(['adb', 'exec-out', 'screencap', '-p'], stdout=f)
            return filename
        return None
    
    def back(self) -> bool:
        """Botão voltar"""
        success, _ = self._run_cmd(['shell', 'input', 'keyevent', 'KEYCODE_BACK'])
        if success:
            time.sleep(1)
        return success

class InstagramBot:
    """Bot principal otimizado"""
    
    def __init__(self, device_id: str = None):
        self.db = Database()
        self.adb = ADB(device_id)
        self.ocr = OCRHelper()
        
        # Carregar configurações
        try:
            from config import BUTTON_TEXTS, get_profile_config
            self.button_texts = BUTTON_TEXTS
            self.config = get_profile_config()
        except ImportError:
            # Fallback se config.py não existir
            self.button_texts = {
                'open_instagram': ['Abrir Instagram', 'Abrir o Instagram', 'Open Instagram'],
                'follow': ['Seguir', 'Follow'],
                'following': ['Seguindo', 'Following'],
                'unfollow': ['Deixar de seguir', 'Unfollow']
            }
            self.config = {
                'max_follows_per_session': 10,
                'delay_between_follows': (45, 90),
                'delay_between_unfollows': (30, 60)
            }
        
        logger.info(f"Bot iniciado - Tela: {self.adb.screen_width}x{self.adb.screen_height}")
        logger.info(f"Perfil: {self.config}")
    
    def _human_delay(self, action_type: str = 'follow'):
        """Delay humano entre ações"""
        if action_type == 'follow':
            min_sec, max_sec = self.config['delay_between_follows']
        else:
            min_sec, max_sec = self.config['delay_between_unfollows']
        
        delay = random.randint(min_sec, max_sec)
        logger.info(f"Aguardando {delay}s...")
        time.sleep(delay)
    
    def follow_user(self, username: str, profile_link: str) -> bool:
        """Segue usuário usando OCR para precisão"""
        try:
            logger.info(f"🚀 Seguindo: {username}")
            
            # 1. Abrir link no navegador
            if not self.adb.open_url(profile_link):
                logger.error("❌ Falha ao abrir link")
                return False
            
            # 2. Screenshot do navegador
            browser_screenshot = self.adb.screenshot(f"browser_{username}.png")
            if not browser_screenshot:
                logger.error("❌ Falha ao capturar screenshot")
                return False
            
            # 3. Encontrar botão "Abrir Instagram" usando OCR
            instagram_btn_coords = self.ocr.find_button_coordinates(
                browser_screenshot, self.button_texts['open_instagram']
            )
            
            if not instagram_btn_coords:
                logger.error("❌ Botão 'Abrir Instagram' não encontrado")
                return False
            
            # 4. Clicar no botão
            if not self.adb.tap(*instagram_btn_coords):
                logger.error("❌ Falha ao clicar 'Abrir Instagram'")
                return False
            
            # 5. Aguardar app carregar
            time.sleep(5)
            
            # 6. Screenshot do app
            app_screenshot = self.adb.screenshot(f"app_{username}.png")
            if not app_screenshot:
                logger.error("❌ Falha ao capturar screenshot do app")
                return False
            
            # 7. Encontrar botão "Seguir" usando OCR
            follow_btn_coords = self.ocr.find_button_coordinates(
                app_screenshot, self.button_texts['follow']
            )
            
            if not follow_btn_coords:
                logger.error("❌ Botão 'Seguir' não encontrado")
                return False
            
            # 8. Verificar se é realmente botão de seguir (cor azul)
            btn_color = self.ocr.detect_button_color(app_screenshot, *follow_btn_coords)
            if btn_color != "azul":
                logger.warning(f"⚠️ Cor do botão suspeita: {btn_color}")
            
            # 9. Clicar em seguir
            if not self.adb.tap(*follow_btn_coords):
                logger.error("❌ Falha ao clicar 'Seguir'")
                return False
            
            # 10. Aguardar confirmação
            time.sleep(2)
            
            # 11. Screenshot final
            self.adb.screenshot(f"followed_{username}.png")
            
            # 12. Marcar no banco
            self.db.mark_followed(username)
            
            logger.info(f"✅ Seguiu: {username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao seguir {username}: {e}")
            return False
    
    def check_follow_back(self, username: str, profile_link: str) -> Optional[bool]:
        """Verifica se usuário segue de volta usando OCR"""
        try:
            logger.info(f"🔍 Verificando: {username}")
            
            # Abrir perfil
            if not self.adb.open_url(profile_link):
                return None
            
            time.sleep(3)
            
            # Ir para o app
            screenshot = self.adb.screenshot(f"browser_check_{username}.png")
            btn_coords = self.ocr.find_button_coordinates(screenshot, self.button_texts['open_instagram'])
            
            if btn_coords:
                self.adb.tap(*btn_coords)
                time.sleep(5)
            
            # Screenshot do perfil
            profile_screenshot = self.adb.screenshot(f"profile_{username}.png")
            
            # Procurar botão "Seguir" ou "Seguindo"
            follow_coords = self.ocr.find_button_coordinates(profile_screenshot, self.button_texts['follow'])
            following_coords = self.ocr.find_button_coordinates(profile_screenshot, self.button_texts['following'])
            
            if following_coords:
                # Usuário segue de volta
                self.db.mark_follow_status(username, True)
                logger.info(f"✅ {username} segue de volta")
                return True
            elif follow_coords:
                # Usuário não segue de volta
                self.db.mark_follow_status(username, False)
                logger.info(f"❌ {username} não segue de volta")
                return False
            else:
                # Não conseguiu determinar
                logger.warning(f"⚠️ Status indefinido para {username}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao verificar {username}: {e}")
            return None
    
    def unfollow_user(self, username: str, profile_link: str) -> bool:
        """Remove seguidor usando OCR"""
        try:
            logger.info(f"➖ Removendo: {username}")
            
            # Abrir perfil
            if not self.adb.open_url(profile_link):
                return False
            
            time.sleep(3)
            
            # Ir para app
            screenshot = self.adb.screenshot(f"browser_unfollow_{username}.png")
            btn_coords = self.ocr.find_button_coordinates(screenshot, self.button_texts['open_instagram'])
            
            if btn_coords:
                self.adb.tap(*btn_coords)
                time.sleep(5)
            
            # Screenshot do perfil
            profile_screenshot = self.adb.screenshot(f"unfollow_{username}.png")
            
            # Procurar botão "Seguindo"
            following_coords = self.ocr.find_button_coordinates(profile_screenshot, self.button_texts['following'])
            
            if not following_coords:
                logger.error("❌ Botão 'Seguindo' não encontrado")
                return False
            
            # Clicar em "Seguindo"
            if not self.adb.tap(*following_coords):
                return False
            
            time.sleep(2)
            
            # Procurar opção "Deixar de seguir" no popup
            popup_screenshot = self.adb.screenshot(f"popup_{username}.png")
            unfollow_coords = self.ocr.find_button_coordinates(popup_screenshot, self.button_texts['unfollow'])
            
            if unfollow_coords:
                self.adb.tap(*unfollow_coords)
            else:
                # Fallback: clicar no centro da tela
                self.adb.tap(self.adb.screen_width // 2, self.adb.screen_height // 2)
            
            time.sleep(2)
            
            # Marcar no banco
            self.db.mark_unfollowed(username)
            
            logger.info(f"✅ Removido: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover {username}: {e}")
            return False
    
    def run_follow_session(self):
        """Executa sessão de follows"""
        logger.info("🚀 === SESSÃO DE FOLLOWS ===")
        
        max_follows = self.config['max_follows_per_session']
        users = self.db.get_pending_users(max_follows)
        if not users:
            logger.info("📭 Nenhum usuário pendente")
            return
        
        logger.info(f"📋 {len(users)} usuários na fila")
        
        success_count = 0
        for i, user in enumerate(users, 1):
            logger.info(f"👤 [{i}/{len(users)}] {user['username']}")
            
            if self.follow_user(user['username'], user['link']):
                success_count += 1
            
            # Delay entre follows
            if i < len(users):
                self._human_delay('follow')
        
        logger.info(f"✅ Sessão concluída: {success_count}/{len(users)} follows")
    
    def run_unfollow_session(self):
        """Executa sessão de unfollows"""
        logger.info("🔍 === SESSÃO DE UNFOLLOWS ===")
        
        users = self.db.get_users_to_check()
        if not users:
            logger.info("📭 Nenhum usuário para verificar")
            return
        
        logger.info(f"🔍 {len(users)} usuários para verificar")
        
        unfollowed_count = 0
        for user in users:
            follows_back = self.check_follow_back(user['username'], user['link'])
            
            if follows_back is False:
                if self.unfollow_user(user['username'], user['link']):
                    unfollowed_count += 1
            
            self._human_delay('unfollow')
        
        logger.info(f"✅ Verificação concluída: {unfollowed_count} unfollows")
    
    def show_stats(self):
        """Mostra estatísticas"""
        stats = self.db.get_stats()
        
        print("\n📊 ESTATÍSTICAS")
        print("-" * 30)
        print(f"📋 Total: {stats['total']}")
        print(f"⏳ Pendentes: {stats['pending']}")
        print(f"✅ Seguidos: {stats['followed']}")
        print(f"💚 Mútuos: {stats['mutual']}")
        print(f"❌ Removidos: {stats['unfollowed']}")
        print(f"📅 Hoje: {stats['followed_today']} follows, {stats['unfollowed_today']} unfollows")
        
        if stats['followed'] > 0:
            rate = (stats['mutual'] / stats['followed']) * 100
            print(f"📈 Taxa follow-back: {rate:.1f}%")

def analyze_excel_file(filename: str):
    """Analisa arquivo Excel para entender sua estrutura"""
    try:
        import pandas as pd
        
        print(f"🔍 Analisando arquivo: {filename}")
        
        # Ler arquivo
        df = pd.read_excel(filename)
        
        print(f"\n📊 INFORMAÇÕES GERAIS")
        print(f"📋 Total de linhas: {len(df)}")
        print(f"📋 Total de colunas: {len(df.columns)}")
        
        print(f"\n📋 COLUNAS ENCONTRADAS:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")
        
        print(f"\n📋 PRIMEIRAS 5 LINHAS:")
        print(df.head().to_string())
        
        print(f"\n🔍 ANÁLISE PARA INSTAGRAM:")
        username_candidates = []
        link_candidates = []
        
        for col in df.columns:
            col_lower = str(col).lower()
            # Buscar colunas que podem ser username
            if any(word in col_lower for word in ['username', 'user', 'nome', 'account', 'perfil', 'insta']):
                username_candidates.append(col)
            # Buscar colunas que podem ser links
            if any(word in col_lower for word in ['link', 'url', 'profile', 'perfil', 'instagram', 'ig']):
                link_candidates.append(col)
        
        print(f"✅ Possíveis colunas de username: {username_candidates if username_candidates else 'Nenhuma encontrada'}")
        print(f"✅ Possíveis colunas de link: {link_candidates if link_candidates else 'Nenhuma encontrada'}")
        
        # Sugestão de importação
        if username_candidates:
            suggested_username = username_candidates[0]
        else:
            suggested_username = df.columns[0]
        
        print(f"\n💡 SUGESTÃO:")
        print(f"   Coluna para username: {suggested_username}")
        if link_candidates:
            print(f"   Coluna para link: {link_candidates[0]}")
        
        # Mostrar exemplos dos dados
        print(f"\n📋 EXEMPLOS DE DADOS:")
        for i in range(min(3, len(df))):
            print(f"  Linha {i+1}: {df.iloc[i][suggested_username]}")
        
        return True
        
    except ImportError:
        print("❌ Para analisar Excel instale: pip install pandas openpyxl")
        return False
    except Exception as e:
        print(f"❌ Erro ao analisar arquivo: {e}")
        return False

def import_users(bot: InstagramBot, filename: str):
    """Importa usuários de arquivo (TXT, CSV, XLSX)"""
    try:
        file_extension = filename.split('.')[-1].lower()
        added = 0
        
        if file_extension == 'txt':
            # Arquivo texto
            with open(filename, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            for line in lines:
                if ',' in line:
                    username, link = line.split(',', 1)
                    username, link = username.strip(), link.strip()
                else:
                    username = line.strip()
                    link = None
                
                if bot.db.add_user(username, link):
                    added += 1
        
        elif file_extension in ['csv', 'xlsx', 'xls']:
            # Arquivo estruturado (CSV/Excel)
            try:
                import pandas as pd
            except ImportError:
                print("❌ Para CSV/Excel instale: pip install pandas openpyxl")
                return
            
            # Ler arquivo
            if file_extension == 'csv':
                df = pd.read_csv(filename, encoding='utf-8')
            else:
                df = pd.read_excel(filename)
            
            print(f"📊 Arquivo carregado: {len(df)} linhas, {len(df.columns)} colunas")
            print(f"📋 Colunas encontradas: {list(df.columns)}")
            
            # Procurar colunas relevantes
            username_col = None
            link_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(word in col_lower for word in ['username', 'user', 'nome', 'account', 'perfil']):
                    username_col = col
                    print(f"✅ Coluna de username: {col}")
                if any(word in col_lower for word in ['link', 'url', 'profile', 'perfil', 'instagram']):
                    link_col = col
                    print(f"✅ Coluna de link: {col}")
            
            # Se não encontrou coluna de username, usar primeira coluna
            if not username_col:
                username_col = df.columns[0]
                print(f"⚠️ Usando primeira coluna como username: {username_col}")
            
            # Processar dados
            for index, row in df.iterrows():
                try:
                    username = str(row[username_col]).strip()
                    
                    # Pular linhas vazias ou NaN
                    if pd.isna(row[username_col]) or username in ['', 'nan', 'None']:
                        continue
                    
                    # Limpar username (remover @ se houver)
                    if username.startswith('@'):
                        username = username[1:]
                    
                    # Obter link se disponível
                    link = None
                    if link_col and pd.notna(row[link_col]):
                        link = str(row[link_col]).strip()
                        if link and not link.startswith('http'):
                            link = f"https://www.instagram.com/{link}/"
                    
                    # Adicionar usuário
                    if bot.db.add_user(username, link):
                        added += 1
                        
                except Exception as e:
                    print(f"⚠️ Erro na linha {index + 1}: {e}")
                    continue
        
        else:
            print(f"❌ Formato não suportado: {file_extension}")
            print("📋 Formatos suportados: .txt, .csv, .xlsx, .xls")
            return
        
        print(f"✅ {added} usuários importados de {filename}")
        
        # Mostrar primeiros usuários adicionados
        if added > 0:
            print("\n📋 Primeiros usuários adicionados:")
            recent_users = bot.db.get_pending_users(5)
            for i, user in enumerate(recent_users[-5:], 1):
                print(f"  {i}. {user['username']}")
        
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {filename}")
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        print(f"💡 Dica: Verifique se o arquivo existe e está no formato correto")
    """Importa usuários de arquivo (TXT, CSV, XLSX)"""
    try:
        file_extension = filename.split('.')[-1].lower()
        added = 0
        
        if file_extension == 'txt':
            # Arquivo texto
            with open(filename, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            for line in lines:
                if ',' in line:
                    username, link = line.split(',', 1)
                    username, link = username.strip(), link.strip()
                else:
                    username = line.strip()
                    link = None
                
                if bot.db.add_user(username, link):
                    added += 1
        
        elif file_extension in ['csv', 'xlsx', 'xls']:
            # Arquivo estruturado (CSV/Excel)
            try:
                import pandas as pd
            except ImportError:
                print("❌ Para CSV/Excel instale: pip install pandas openpyxl")
                return
            
            # Ler arquivo
            if file_extension == 'csv':
                df = pd.read_csv(filename, encoding='utf-8')
            else:
                df = pd.read_excel(filename)
            
            print(f"📊 Arquivo carregado: {len(df)} linhas, {len(df.columns)} colunas")
            print(f"📋 Colunas encontradas: {list(df.columns)}")
            
            # Procurar colunas relevantes
            username_col = None
            link_col = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if any(word in col_lower for word in ['username', 'user', 'nome', 'account', 'perfil']):
                    username_col = col
                    print(f"✅ Coluna de username: {col}")
                if any(word in col_lower for word in ['link', 'url', 'profile', 'perfil', 'instagram']):
                    link_col = col
                    print(f"✅ Coluna de link: {col}")
            
            # Se não encontrou coluna de username, usar primeira coluna
            if not username_col:
                username_col = df.columns[0]
                print(f"⚠️ Usando primeira coluna como username: {username_col}")
            
            # Processar dados
            for index, row in df.iterrows():
                try:
                    username = str(row[username_col]).strip()
                    
                    # Pular linhas vazias ou NaN
                    if pd.isna(row[username_col]) or username in ['', 'nan', 'None']:
                        continue
                    
                    # Limpar username (remover @ se houver)
                    if username.startswith('@'):
                        username = username[1:]
                    
                    # Obter link se disponível
                    link = None
                    if link_col and pd.notna(row[link_col]):
                        link = str(row[link_col]).strip()
                        if link and not link.startswith('http'):
                            link = f"https://www.instagram.com/{link}/"
                    
                    # Adicionar usuário
                    if bot.db.add_user(username, link):
                        added += 1
                        
                except Exception as e:
                    print(f"⚠️ Erro na linha {index + 1}: {e}")
                    continue
        
        else:
            print(f"❌ Formato não suportado: {file_extension}")
            print("📋 Formatos suportados: .txt, .csv, .xlsx, .xls")
            return
        
        print(f"✅ {added} usuários importados de {filename}")
        
        # Mostrar primeiros usuários adicionados
        if added > 0:
            print("\n📋 Primeiros usuários adicionados:")
            recent_users = bot.db.get_pending_users(5)
            for i, user in enumerate(recent_users[-5:], 1):
                print(f"  {i}. {user['username']}")
        
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {filename}")
    except Exception as e:
        print(f"❌ Erro ao importar: {e}")
        print(f"💡 Dica: Verifique se o arquivo existe e está no formato correto")

def main():
    """Função principal"""
    print("🚀 INSTAGRAM BOT COM OCR")
    print("=" * 30)
    
    bot = InstagramBot()
    
    while True:
        print("\n🎮 MENU:")
        print("1. 🚀 Seguir usuários")
        print("2. 🔍 Verificar unfollows")
        print("3. 📂 Importar arquivo")
        print("4. 🔍 Analisar arquivo Excel")
        print("5. ➕ Adicionar usuário")
        print("6. 📊 Estatísticas")
        print("7. 📱 Screenshot")
        print("8. 🚪 Sair")
        
        choice = input("\nOpção: ").strip()
        
        if choice == '1':
            bot.run_follow_session()
        elif choice == '2':
            bot.run_unfollow_session()
        elif choice == '3':
            filename = input("Arquivo: ").strip()
            import_users(bot, filename)
        elif choice == '4':
            filename = input("Arquivo Excel para analisar: ").strip()
            analyze_excel_file(filename)
        elif choice == '5':
            username = input("Username: ").strip()
            link = input("Link (opcional): ").strip()
            if bot.db.add_user(username, link or None):
                print("✅ Adicionado")
            else:
                print("❌ Erro")
        elif choice == '6':
            bot.show_stats()
        elif choice == '7':
            filename = bot.adb.screenshot()
            if filename:
                print(f"📸 Screenshot: {filename}")
        elif choice == '8':
            break
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main()
