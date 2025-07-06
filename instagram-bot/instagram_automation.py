import subprocess
import time
import random
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image
import io

@dataclass
class DeviceInfo:
    """Informações do dispositivo Android"""
    device_id: str
    screen_width: int
    screen_height: int
    density: float
    instagram_package: str = "com.instagram.android"

@dataclass
class ActionResult:
    """Resultado de uma ação executada"""
    success: bool
    message: str
    screenshot_path: Optional[str] = None
    execution_time: float = 0.0

class ADBController:
    """Controlador principal para interações via ADB"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.device_info = None
        self.logger = logging.getLogger(__name__)
        
    def _run_adb_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str]:
        """Executa comando ADB e retorna resultado"""
        try:
            if self.device_id:
                cmd = ['adb', '-s', self.device_id] + command
            else:
                cmd = ['adb'] + command
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                self.logger.error(f"ADB command failed: {result.stderr}")
                return False, result.stderr.strip()
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"ADB command timed out: {command}")
            return False, "Command timed out"
        except Exception as e:
            self.logger.error(f"Error executing ADB command: {e}")
            return False, str(e)
    
    def connect_device(self) -> bool:
        """Conecta ao dispositivo e obtém informações"""
        success, output = self._run_adb_command(['devices'])
        
        if not success:
            self.logger.error("Failed to list ADB devices")
            return False
        
        devices = []
        for line in output.split('\n')[1:]:  # Skip header
            if line.strip() and 'device' in line:
                device_id = line.split('\t')[0]
                devices.append(device_id)
        
        if not devices:
            self.logger.error("No Android devices found")
            return False
        
        if not self.device_id:
            self.device_id = devices[0]
            self.logger.info(f"Using device: {self.device_id}")
        
        # Obter informações do dispositivo
        return self._get_device_info()
    
    def _get_device_info(self) -> bool:
        """Obtém informações detalhadas do dispositivo"""
        try:
            # Dimensões da tela
            success, output = self._run_adb_command(['shell', 'wm', 'size'])
            if not success:
                return False
            
            size_match = re.search(r'(\d+)x(\d+)', output)
            if not size_match:
                return False
            
            width, height = map(int, size_match.groups())
            
            # Densidade da tela
            success, output = self._run_adb_command(['shell', 'wm', 'density'])
            if not success:
                return False
            
            density_match = re.search(r'(\d+)', output)
            density = int(density_match.group(1)) if density_match else 420
            
            self.device_info = DeviceInfo(
                device_id=self.device_id,
                screen_width=width,
                screen_height=height,
                density=density / 160.0  # Converter para fator de escala
            )
            
            self.logger.info(f"Device info: {width}x{height}, density: {density}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error getting device info: {e}")
            return False
    
    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[str]:
        """Captura screenshot do dispositivo"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not save_path:
                save_path = f"screenshot_{timestamp}.png"
            
            success, _ = self._run_adb_command([
                'exec-out', 'screencap', '-p'
            ])
            
            if success:
                # Salvar screenshot
                with open(save_path, 'wb') as f:
                    subprocess.run([
                        'adb', '-s', self.device_id, 'exec-out', 'screencap', '-p'
                    ], stdout=f)
                
                return save_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
            return None
    
    def tap(self, x: int, y: int, duration: int = 100) -> bool:
        """Executa tap na tela"""
        success, _ = self._run_adb_command([
            'shell', 'input', 'tap', str(x), str(y)
        ])
        
        if success:
            time.sleep(duration / 1000.0)  # Converter para segundos
        
        return success
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
        """Executa swipe na tela"""
        success, _ = self._run_adb_command([
            'shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)
        ])
        
        if success:
            time.sleep(duration / 1000.0 + 0.5)  # Aguardar animação
        
        return success
    
    def type_text(self, text: str) -> bool:
        """Digite texto (escapa caracteres especiais)"""
        # Escapar caracteres especiais para shell
        escaped_text = text.replace(' ', '%s').replace('&', '\\&')
        
        success, _ = self._run_adb_command([
            'shell', 'input', 'text', escaped_text
        ])
        
        return success
    
    def press_key(self, keycode: str) -> bool:
        """Pressiona uma tecla (KEYCODE_BACK, KEYCODE_HOME, etc.)"""
        success, _ = self._run_adb_command([
            'shell', 'input', 'keyevent', keycode
        ])
        
        return success
    
    def is_app_running(self, package_name: str) -> bool:
        """Verifica se o app está executando"""
        success, output = self._run_adb_command([
            'shell', 'pidof', package_name
        ])
        
        return success and output.strip() != ""
    
    def start_app(self, package_name: str, activity: Optional[str] = None) -> bool:
        """Inicia aplicativo"""
        if activity:
            intent = f"{package_name}/{activity}"
        else:
            intent = package_name
        
        success, _ = self._run_adb_command([
            'shell', 'am', 'start', '-n', intent
        ])
        
        if success:
            time.sleep(3)  # Aguardar app iniciar
        
        return success
    
    def stop_app(self, package_name: str) -> bool:
        """Para aplicativo"""
        success, _ = self._run_adb_command([
            'shell', 'am', 'force-stop', package_name
        ])
        
        return success

class InstagramAutomation:
    """Classe principal para automação do Instagram"""
    
    def __init__(self, adb_controller: ADBController, db_instance):
        self.adb = adb_controller
        self.db = db_instance
        self.logger = logging.getLogger(__name__)
        
        # Coordenadas baseadas em resolução padrão (serão ajustadas)
        self.coordinates = {
            'search_tab': (0.2, 0.9),      # Tab de busca
            'search_box': (0.5, 0.1),     # Caixa de busca
            'first_user': (0.5, 0.25),    # Primeiro usuário nos resultados
            'follow_button': (0.85, 0.3), # Botão seguir no perfil
            'back_button': (0.05, 0.05),  # Botão voltar
            'home_tab': (0.1, 0.9),       # Tab home
            'profile_tab': (0.9, 0.9),    # Tab perfil
            'following_list': (0.5, 0.4), # Lista de seguindo
            'unfollow_button': (0.85, 0.3) # Botão deixar de seguir
        }
    
    def _adjust_coordinates(self, relative_x: float, relative_y: float) -> Tuple[int, int]:
        """Converte coordenadas relativas para absolutas"""
        if not self.adb.device_info:
            raise Exception("Device info not available")
        
        x = int(relative_x * self.adb.device_info.screen_width)
        y = int(relative_y * self.adb.device_info.screen_height)
        
        return x, y
    
    def _random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Delay aleatório para simular comportamento humano"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def _add_human_variance(self, x: int, y: int, variance: int = 5) -> Tuple[int, int]:
        """Adiciona variação aleatória às coordenadas"""
        x_var = random.randint(-variance, variance)
        y_var = random.randint(-variance, variance)
        return x + x_var, y + y_var
    
    def start_instagram(self) -> ActionResult:
        """Inicia o Instagram"""
        start_time = time.time()
        
        try:
            # Verificar se já está rodando
            if self.adb.is_app_running(self.adb.device_info.instagram_package):
                self.logger.info("Instagram already running")
                return ActionResult(
                    success=True,
                    message="Instagram already running",
                    execution_time=time.time() - start_time
                )
            
            # Iniciar Instagram
            success = self.adb.start_app(self.adb.device_info.instagram_package)
            
            if not success:
                return ActionResult(
                    success=False,
                    message="Failed to start Instagram",
                    execution_time=time.time() - start_time
                )
            
            # Aguardar carregamento e tirar screenshot
            time.sleep(5)
            screenshot = self.adb.take_screenshot()
            
            return ActionResult(
                success=True,
                message="Instagram started successfully",
                screenshot_path=screenshot,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error starting Instagram: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def search_user(self, username: str) -> ActionResult:
        """Busca por um usuário no Instagram"""
        start_time = time.time()
        
        try:
            # Ir para aba de busca
            search_x, search_y = self._adjust_coordinates(*self.coordinates['search_tab'])
            search_x, search_y = self._add_human_variance(search_x, search_y)
            
            if not self.adb.tap(search_x, search_y):
                return ActionResult(
                    success=False,
                    message="Failed to tap search tab",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(1, 2)
            
            # Tocar na caixa de busca
            search_box_x, search_box_y = self._adjust_coordinates(*self.coordinates['search_box'])
            search_box_x, search_box_y = self._add_human_variance(search_box_x, search_box_y)
            
            if not self.adb.tap(search_box_x, search_box_y):
                return ActionResult(
                    success=False,
                    message="Failed to tap search box",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(1, 2)
            
            # Digitar username
            if not self.adb.type_text(username):
                return ActionResult(
                    success=False,
                    message=f"Failed to type username: {username}",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(2, 3)
            
            # Tocar no primeiro resultado
            first_user_x, first_user_y = self._adjust_coordinates(*self.coordinates['first_user'])
            first_user_x, first_user_y = self._add_human_variance(first_user_x, first_user_y)
            
            if not self.adb.tap(first_user_x, first_user_y):
                return ActionResult(
                    success=False,
                    message="Failed to tap first user result",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(2, 4)
            
            # Tirar screenshot do perfil
            screenshot = self.adb.take_screenshot()
            
            return ActionResult(
                success=True,
                message=f"Successfully navigated to {username}'s profile",
                screenshot_path=screenshot,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error searching user {username}: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def follow_user(self) -> ActionResult:
        """Segue o usuário atualmente na tela"""
        start_time = time.time()
        
        try:
            # Localizar e tocar no botão seguir
            follow_x, follow_y = self._adjust_coordinates(*self.coordinates['follow_button'])
            follow_x, follow_y = self._add_human_variance(follow_x, follow_y)
            
            if not self.adb.tap(follow_x, follow_y):
                return ActionResult(
                    success=False,
                    message="Failed to tap follow button",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(1, 2)
            
            # Tirar screenshot após seguir
            screenshot = self.adb.take_screenshot()
            
            return ActionResult(
                success=True,
                message="Successfully followed user",
                screenshot_path=screenshot,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error following user: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def check_if_following_back(self, username: str) -> ActionResult:
        """Verifica se o usuário está seguindo de volta"""
        start_time = time.time()
        
        try:
            # Ir para o perfil próprio
            profile_x, profile_y = self._adjust_coordinates(*self.coordinates['profile_tab'])
            if not self.adb.tap(profile_x, profile_y):
                return ActionResult(
                    success=False,
                    message="Failed to go to profile tab",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(2, 3)
            
            # Tocar em "seguindo"
            following_x, following_y = self._adjust_coordinates(*self.coordinates['following_list'])
            if not self.adb.tap(following_x, following_y):
                return ActionResult(
                    success=False,
                    message="Failed to tap following list",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(2, 3)
            
            # Buscar pelo username na lista
            if not self.adb.type_text(username):
                return ActionResult(
                    success=False,
                    message=f"Failed to search for {username}",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(2, 3)
            
            # Tirar screenshot para análise
            screenshot = self.adb.take_screenshot()
            
            # Aqui poderíamos implementar OCR para verificar se o usuário aparece
            # Por enquanto, retornamos sucesso com screenshot para análise manual
            
            return ActionResult(
                success=True,
                message=f"Screenshot taken for follow-back check of {username}",
                screenshot_path=screenshot,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error checking follow-back for {username}: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def unfollow_user(self, username: str) -> ActionResult:
        """Deixa de seguir um usuário"""
        start_time = time.time()
        
        try:
            # Primeiro buscar o usuário
            search_result = self.search_user(username)
            if not search_result.success:
                return ActionResult(
                    success=False,
                    message=f"Failed to find user {username}: {search_result.message}",
                    execution_time=time.time() - start_time
                )
            
            # Tocar no botão seguindo/unfollow
            unfollow_x, unfollow_y = self._adjust_coordinates(*self.coordinates['unfollow_button'])
            unfollow_x, unfollow_y = self._add_human_variance(unfollow_x, unfollow_y)
            
            if not self.adb.tap(unfollow_x, unfollow_y):
                return ActionResult(
                    success=False,
                    message="Failed to tap unfollow button",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(1, 2)
            
            # Confirmar unfollow se necessário (pode aparecer popup)
            # Tocar novamente para confirmar
            if not self.adb.tap(unfollow_x, unfollow_y):
                self.logger.warning("Failed to confirm unfollow, might not be needed")
            
            self._random_delay(1, 2)
            
            # Tirar screenshot
            screenshot = self.adb.take_screenshot()
            
            return ActionResult(
                success=True,
                message=f"Successfully unfollowed {username}",
                screenshot_path=screenshot,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error unfollowing {username}: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def go_back_to_home(self) -> ActionResult:
        """Volta para a tela inicial do Instagram"""
        start_time = time.time()
        
        try:
            # Tocar na aba home
            home_x, home_y = self._adjust_coordinates(*self.coordinates['home_tab'])
            
            if not self.adb.tap(home_x, home_y):
                return ActionResult(
                    success=False,
                    message="Failed to go back to home",
                    execution_time=time.time() - start_time
                )
            
            self._random_delay(1, 2)
            
            return ActionResult(
                success=True,
                message="Successfully returned to home",
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Error going back to home: {str(e)}",
                execution_time=time.time() - start_time
            )

class InstagramBot:
    """Bot principal que orquestra todas as operações"""
    
    def __init__(self, db_instance, device_id: Optional[str] = None):
        self.db = db_instance
        self.adb = ADBController(device_id)
        self.instagram = None
        self.logger = logging.getLogger(__name__)
        
        # Configurações
        self.max_follows_per_day = int(self.db.get_setting('max_daily_follows') or 100)
        self.max_unfollows_per_day = int(self.db.get_setting('max_daily_unfollows') or 50)
        self.follows_per_batch = int(self.db.get_setting('follows_per_batch') or 5)
        self.follow_interval_minutes = int(self.db.get_setting('follow_interval_minutes') or 5)
        self.min_delay = int(self.db.get_setting('min_delay_seconds') or 30)
        self.max_delay = int(self.db.get_setting('max_delay_seconds') or 120)
    
    def initialize(self) -> bool:
        """Inicializa o bot e conecta ao dispositivo"""
        try:
            if not self.adb.connect_device():
                self.logger.error("Failed to connect to Android device")
                return False
            
            self.instagram = InstagramAutomation(self.adb, self.db)
            
            # Iniciar Instagram
            result = self.instagram.start_instagram()
            if not result.success:
                self.logger.error(f"Failed to start Instagram: {result.message}")
                return False
            
            self.logger.info("Bot initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing bot: {e}")
            return False
    
    def execute_follow_batch(self) -> Dict[str, int]:
        """Executa um lote de follows"""
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        # Verificar limites diários
        daily_stats = self.db.get_statistics()
        if daily_stats['follows_today'] >= self.max_follows_per_day:
            self.logger.info(f"Daily follow limit reached: {self.max_follows_per_day}")
            return stats
        
        # Obter seguidores para seguir
        followers_to_follow = self.db.get_followers_to_follow(self.follows_per_batch)
        
        if not followers_to_follow:
            self.logger.info("No followers to follow")
            return stats
        
        for follower in followers_to_follow:
            try:
                follower_id = follower['id']
                username = follower['username']
                
                self.logger.info(f"Attempting to follow: {username}")
                
                # Registrar ação como pendente
                action_id = self.db.record_action(follower_id, 'follow', 'pending')
                
                # Buscar usuário
                search_result = self.instagram.search_user(username)
                if not search_result.success:
                    self.db.update_action_status(action_id, 'failed', search_result.message)
                    stats['failed'] += 1
                    continue
                
                # Seguir usuário
                follow_result = self.instagram.follow_user()
                if follow_result.success:
                    # Marcar como concluído
                    self.db.update_action_status(action_id, 'completed')
                    
                    # Agendar verificação de follow-back
                    self.db.schedule_follow_back_check(follower_id, datetime.now())
                    
                    stats['success'] += 1
                    self.logger.info(f"Successfully followed: {username}")
                else:
                    self.db.update_action_status(action_id, 'failed', follow_result.message)
                    stats['failed'] += 1
                    self.logger.error(f"Failed to follow {username}: {follow_result.message}")
                
                # Voltar ao home
                self.instagram.go_back_to_home()
                
                # Delay entre ações
                delay = random.randint(self.min_delay, self.max_delay)
                self.logger.info(f"Waiting {delay} seconds before next action")
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"Error processing follower {username}: {e}")
                stats['failed'] += 1
                continue
        
        return stats
    
    def check_follow_backs(self) -> Dict[str, int]:
        """Verifica follow-backs pendentes"""
        stats = {'checked': 0, 'following_back': 0, 'not_following_back': 0}
        
        # Obter follow-backs para verificar
        follow_backs_to_check = self.db.get_follow_backs_to_check()
        
        for follow_back in follow_backs_to_check:
            try:
                username = follow_back['username']
                follow_back_id = follow_back['id']
                
                self.logger.info(f"Checking follow-back for: {username}")
                
                # Verificar se está seguindo de volta
                check_result = self.instagram.check_if_following_back(username)
                
                if check_result.success:
                    # Aqui seria necessário implementar análise de imagem/OCR
                    # Por enquanto, marcaremos como verificado mas sem resultado
                    self.db.update_follow_back_status(follow_back_id, False)  # Assumir que não seguiu
                    stats['not_following_back'] += 1
                    stats['checked'] += 1
                    
                    self.logger.info(f"Follow-back check completed for: {username}")
                else:
                    self.logger.error(f"Failed to check follow-back for {username}: {check_result.message}")
                
                # Delay entre verificações
                time.sleep(random.randint(5, 10))
                
            except Exception as e:
                self.logger.error(f"Error checking follow-back for {username}: {e}")
                continue
        
        return stats
    
    def execute_unfollow_batch(self) -> Dict[str, int]:
        """Executa unfollows para quem não seguiu de volta"""
        stats = {'success': 0, 'failed': 0}
        
        # Verificar limite diário
        daily_stats = self.db.get_statistics()
        if daily_stats['unfollows_today'] >= self.max_unfollows_per_day:
            self.logger.info(f"Daily unfollow limit reached: {self.max_unfollows_per_day}")
            return stats
        
        # Obter usuários que não seguiram de volta
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fb.follower_id, f.username
            FROM follow_backs fb
            JOIN followers f ON fb.follower_id = f.id
            WHERE fb.followed_back = 0
            AND fb.unfollowed_at IS NULL
            LIMIT ?
        ''', (self.max_unfollows_per_day - daily_stats['unfollows_today'],))
        
        users_to_unfollow = cursor.fetchall()
        conn.close()
        
        for follower_id, username in users_to_unfollow:
            try:
                self.logger.info(f"Attempting to unfollow: {username}")
                
                # Registrar ação
                action_id = self.db.record_action(follower_id, 'unfollow', 'pending')
                
                # Executar unfollow
                unfollow_result = self.instagram.unfollow_user(username)
                
                if unfollow_result.success:
                    self.db.update_action_status(action_id, 'completed')
                    
                    # Marcar como unfollowed
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE follow_backs 
                        SET unfollowed_at = CURRENT_TIMESTAMP
                        WHERE follower_id = ?
                    ''', (follower_id,))
                    conn.commit()
                    conn.close()
                    
                    stats['success'] += 1
                    self.logger.info(f"Successfully unfollowed: {username}")
                else:
                    self.db.update_action_status(action_id, 'failed', unfollow_result.message)
                    stats['failed'] += 1
                    self.logger.error(f"Failed to unfollow {username}: {unfollow_result.message}")
                
                # Voltar ao home
                self.instagram.go_back_to_home()
                
                # Delay entre ações
                delay = random.randint(self.min_delay, self.max_delay)
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"Error unfollowing {username}: {e}")
                stats['failed'] += 1
                continue
        
        return stats
    
    def run_automation_cycle(self) -> Dict[str, any]:
        """Executa um ciclo completo de automação"""
        cycle_stats = {
            'started_at': datetime.now(),
            'follow_stats': {},
            'check_stats': {},
            'unfollow_stats': {},
            'completed_at': None,
            'total_execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            self.logger.info("Starting automation cycle")
            
            # 1. Executar follows
            self.logger.info("Executing follow batch")
            cycle_stats['completed_at'] = datetime.now()
            cycle_stats['total_execution_time'] = time.time() - start_time
            
            self.logger.info(f"Automation cycle completed in {cycle_stats['total_execution_time']:.2f} seconds")
            
            # Log das estatísticas
            self.db.log_message(
                'INFO',
                f"Automation cycle completed: {json.dumps(cycle_stats, default=str)}",
                'InstagramBot',
                'run_automation_cycle'
            )
            
        except Exception as e:
            self.logger.error(f"Error in automation cycle: {e}")
            cycle_stats['error'] = str(e)
            cycle_stats['completed_at'] = datetime.now()
            cycle_stats['total_execution_time'] = time.time() - start_time
            
            self.db.log_message(
                'ERROR',
                f"Automation cycle failed: {str(e)}",
                'InstagramBot',
                'run_automation_cycle'
            )
        
        return cycle_stats

# Classe para coordenadas adaptáveis baseadas em template matching
class CoordinateDetector:
    """Detector de coordenadas usando template matching e OCR"""
    
    def __init__(self, adb_controller: ADBController):
        self.adb = adb_controller
        self.templates_path = "templates/"  # Pasta com imagens de template
        
    def find_button(self, template_name: str, threshold: float = 0.8) -> Optional[Tuple[int, int]]:
        """Encontra um botão na tela usando template matching"""
        try:
            # Capturar screenshot atual
            screenshot_path = self.adb.take_screenshot()
            if not screenshot_path:
                return None
            
            # Carregar imagens
            screen = cv2.imread(screenshot_path)
            template = cv2.imread(f"{self.templates_path}{template_name}.png")
            
            if screen is None or template is None:
                return None
            
            # Template matching
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # Calcular centro do template
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return center_x, center_y
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in template matching: {e}")
            return None
    
    def find_text(self, text: str, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[int, int]]:
        """Encontra texto na tela usando OCR"""
        try:
            import pytesseract
            
            # Capturar screenshot
            screenshot_path = self.adb.take_screenshot()
            if not screenshot_path:
                return None
            
            # Carregar imagem
            image = cv2.imread(screenshot_path)
            
            if region:
                x, y, w, h = region
                image = image[y:y+h, x:x+w]
            
            # Converter para escala de cinza
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # OCR
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
            
            # Procurar pelo texto
            for i, word in enumerate(data['text']):
                if text.lower() in word.lower() and int(data['conf'][i]) > 50:
                    x = data['left'][i] + data['width'][i] // 2
                    y = data['top'][i] + data['height'][i] // 2
                    
                    # Ajustar coordenadas se foi usado region
                    if region:
                        x += region[0]
                        y += region[1]
                    
                    return x, y
            
            return None
            
        except ImportError:
            self.logger.warning("pytesseract not available, text detection disabled")
            return None
        except Exception as e:
            self.logger.error(f"Error in text detection: {e}")
            return None

class InstagramBot:
    """Bot principal que orquestra todas as operações"""
    
    def __init__(self, db_instance, device_id: Optional[str] = None):
        self.db = db_instance
        self.adb = ADBController(device_id)
        self.instagram = None
        self.logger = logging.getLogger(__name__)
        
        # Configurações básicas
        self.max_follows_per_day = 50
        self.max_unfollows_per_day = 25
        self.follows_per_batch = 5
        self.follow_interval_minutes = 5
        self.min_delay = 30
        self.max_delay = 120
    
    def initialize(self) -> bool:
        """Inicializa o bot e conecta ao dispositivo"""
        try:
            if not self.adb.connect_device():
                self.logger.error("Failed to connect to Android device")
                return False
            
            self.instagram = InstagramAutomation(self.adb, self.db)
            
            # Iniciar Instagram
            result = self.instagram.start_instagram()
            if not result.success:
                self.logger.error(f"Failed to start Instagram: {result.message}")
                return False
            
            self.logger.info("Bot initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing bot: {e}")
            return False
    
    def execute_follow_batch(self) -> Dict[str, int]:
        """Executa um lote de follows"""
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        # Obter seguidores para seguir
        followers_to_follow = self.db.get_followers_to_follow(self.follows_per_batch)
        
        if not followers_to_follow:
            self.logger.info("No followers to follow")
            return stats
        
        for follower in followers_to_follow:
            try:
                follower_id = follower['id']
                username = follower['username']
                
                self.logger.info(f"Attempting to follow: {username}")
                
                # Registrar ação como pendente
                action_id = self.db.record_action(follower_id, 'follow', 'pending')
                
                # Buscar usuário
                search_result = self.instagram.search_user(username)
                if not search_result.success:
                    self.db.update_action_status(action_id, 'failed', search_result.message)
                    stats['failed'] += 1
                    continue
                
                # Seguir usuário
                follow_result = self.instagram.follow_user()
                if follow_result.success:
                    self.db.update_action_status(action_id, 'completed')
                    self.db.schedule_follow_back_check(follower_id, datetime.now())
                    stats['success'] += 1
                    self.logger.info(f"Successfully followed: {username}")
                else:
                    self.db.update_action_status(action_id, 'failed', follow_result.message)
                    stats['failed'] += 1
                
                # Delay entre ações
                delay = random.randint(self.min_delay, self.max_delay)
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"Error processing follower {username}: {e}")
                stats['failed'] += 1
                continue
        
        return stats
    
    def check_follow_backs(self) -> Dict[str, int]:
        """Verifica follow-backs pendentes"""
        stats = {'checked': 0, 'following_back': 0, 'not_following_back': 0}
        
        follow_backs_to_check = self.db.get_follow_backs_to_check()
        
        for follow_back in follow_backs_to_check:
            try:
                username = follow_back['username']
                follow_back_id = follow_back['id']
                
                self.logger.info(f"Checking follow-back for: {username}")
                
                check_result = self.instagram.check_if_following_back(username)
                
                if check_result.success:
                    self.db.update_follow_back_status(follow_back_id, False)  # Assumir que não seguiu por enquanto
                    stats['not_following_back'] += 1
                    stats['checked'] += 1
                    
                time.sleep(random.randint(5, 10))
                
            except Exception as e:
                self.logger.error(f"Error checking follow-back for {username}: {e}")
                continue
        
        return stats
    
    def execute_unfollow_batch(self) -> Dict[str, int]:
        """Executa unfollows para quem não seguiu de volta"""
        stats = {'success': 0, 'failed': 0}
        
        # Obter usuários que não seguiram de volta
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fb.follower_id, f.username
            FROM follow_backs fb
            JOIN followers f ON fb.follower_id = f.id
            WHERE fb.followed_back = 0
            AND fb.unfollowed_at IS NULL
            LIMIT ?
        ''', (self.max_unfollows_per_day,))
        
        users_to_unfollow = cursor.fetchall()
        conn.close()
        
        for follower_id, username in users_to_unfollow:
            try:
                self.logger.info(f"Attempting to unfollow: {username}")
                
                action_id = self.db.record_action(follower_id, 'unfollow', 'pending')
                
                unfollow_result = self.instagram.unfollow_user(username)
                
                if unfollow_result.success:
                    self.db.update_action_status(action_id, 'completed')
                    
                    # Marcar como unfollowed
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE follow_backs 
                        SET unfollowed_at = CURRENT_TIMESTAMP
                        WHERE follower_id = ?
                    ''', (follower_id,))
                    conn.commit()
                    conn.close()
                    
                    stats['success'] += 1
                    self.logger.info(f"Successfully unfollowed: {username}")
                else:
                    self.db.update_action_status(action_id, 'failed', unfollow_result.message)
                    stats['failed'] += 1
                
                delay = random.randint(self.min_delay, self.max_delay)
                time.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"Error unfollowing {username}: {e}")
                stats['failed'] += 1
                continue
        
        return stats
    
    def run_automation_cycle(self) -> Dict[str, any]:
        """Executa um ciclo completo de automação"""
        cycle_stats = {
            'started_at': datetime.now(),
            'follow_stats': {},
            'check_stats': {},
            'unfollow_stats': {},
            'completed_at': None,
            'total_execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            self.logger.info("Starting automation cycle")
            
            # 1. Executar follows
            cycle_stats['follow_stats'] = self.execute_follow_batch()
            
            # 2. Verificar follow-backs
            cycle_stats['check_stats'] = self.check_follow_backs()
            
            # 3. Executar unfollows
            cycle_stats['unfollow_stats'] = self.execute_unfollow_batch()
            
            cycle_stats['completed_at'] = datetime.now()
            cycle_stats['total_execution_time'] = time.time() - start_time
            
            self.logger.info(f"Automation cycle completed in {cycle_stats['total_execution_time']:.2f} seconds")
            
            self.db.log_message(
                'INFO',
                f"Automation cycle completed: {json.dumps(cycle_stats, default=str)}",
                'InstagramBot',
                'run_automation_cycle'
            )
            
        except Exception as e:
            self.logger.error(f"Error in automation cycle: {e}")
            cycle_stats['error'] = str(e)
            cycle_stats['completed_at'] = datetime.now()
            cycle_stats['total_execution_time'] = time.time() - start_time
            
            self.db.log_message(
                'ERROR',
                f"Automation cycle failed: {str(e)}",
                'InstagramBot',
                'run_automation_cycle'
            )
        
        return cycle_stats

# Classe para análise de perfil
class ProfileAnalyzer:
    """Analisador de perfis do Instagram"""
    
    def __init__(self, adb_controller: ADBController):
        self.adb = adb_controller
        self.logger = logging.getLogger(__name__)
    
    def extract_profile_info(self, screenshot_path: str) -> Dict[str, any]:
        """Extrai informações do perfil a partir de screenshot"""
        try:
            profile_info = {
                'followers_count': None,
                'following_count': None,
                'posts_count': None,
                'is_verified': False,
                'is_private': False,
                'bio': None,
                'full_name': None
            }
            
            # Aqui implementaríamos OCR e análise de imagem
            # Por enquanto retorna estrutura básica
            
            return profile_info
            
        except Exception as e:
            self.logger.error(f"Error analyzing profile: {e}")
            return {}
    
    def is_worth_following(self, profile_info: Dict[str, any]) -> bool:
        """Determina se vale a pena seguir baseado no perfil"""
        try:
            # Regras de negócio para determinar se vale seguir
            
            # Não seguir contas privadas
            if profile_info.get('is_private', False):
                return False
            
            # Não seguir contas com muitos seguidores (famosos)
            followers = profile_info.get('followers_count', 0)
            if followers and followers > 100000:
                return False
            
            # Não seguir contas que seguem muito mais do que têm seguidores
            following = profile_info.get('following_count', 0)
            if followers and following and following > followers * 3:
                return False
            
            # Não seguir contas sem posts
            posts = profile_info.get('posts_count', 0)
            if posts == 0:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating profile: {e}")
            return False

# Classe para monitoramento e relatórios
class BotMonitor:
    """Monitor do bot com relatórios e alertas"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.logger = logging.getLogger(__name__)
    
    def generate_daily_report(self) -> Dict[str, any]:
        """Gera relatório diário de atividades"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'follows': {},
                'unfollows': {},
                'follow_backs': {},
                'errors': {},
                'efficiency': {}
            }
            
            # Follows hoje
            cursor.execute('''
                SELECT COUNT(*), AVG(julianday(performed_at) - julianday(scheduled_for)) * 24 * 60 as avg_delay_minutes
                FROM actions 
                WHERE action_type = 'follow' 
                AND status = 'completed'
                AND DATE(performed_at) = DATE('now')
            ''')
            follow_data = cursor.fetchone()
            report['follows']['completed'] = follow_data[0] if follow_data[0] else 0
            report['follows']['avg_delay_minutes'] = follow_data[1] if follow_data[1] else 0
            
            # Follows falharam hoje
            cursor.execute('''
                SELECT COUNT(*) FROM actions 
                WHERE action_type = 'follow' 
                AND status = 'failed'
                AND DATE(performed_at) = DATE('now')
            ''')
            report['follows']['failed'] = cursor.fetchone()[0]
            
            # Unfollows hoje
            cursor.execute('''
                SELECT COUNT(*) FROM actions 
                WHERE action_type = 'unfollow' 
                AND status = 'completed'
                AND DATE(performed_at) = DATE('now')
            ''')
            report['unfollows']['completed'] = cursor.fetchone()[0]
            
            # Follow-backs recebidos
            cursor.execute('''
                SELECT COUNT(*) FROM follow_backs 
                WHERE followed_back = 1
                AND DATE(checked_at) = DATE('now')
            ''')
            report['follow_backs']['received'] = cursor.fetchone()[0]
            
            # Taxa de follow-back
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_checked,
                    SUM(CASE WHEN followed_back = 1 THEN 1 ELSE 0 END) as followed_back
                FROM follow_backs 
                WHERE followed_back IS NOT NULL
                AND DATE(checked_at) = DATE('now')
            ''')
            fb_data = cursor.fetchone()
            if fb_data[0] > 0:
                report['follow_backs']['rate'] = (fb_data[1] / fb_data[0]) * 100
            else:
                report['follow_backs']['rate'] = 0
            
            # Erros por tipo
            cursor.execute('''
                SELECT error_message, COUNT(*) 
                FROM actions 
                WHERE status = 'failed'
                AND DATE(performed_at) = DATE('now')
                GROUP BY error_message
            ''')
            error_data = cursor.fetchall()
            report['errors'] = dict(error_data) if error_data else {}
            
            # Eficiência geral
            total_attempts = report['follows']['completed'] + report['follows']['failed']
            if total_attempts > 0:
                report['efficiency']['success_rate'] = (report['follows']['completed'] / total_attempts) * 100
            else:
                report['efficiency']['success_rate'] = 0
            
            conn.close()
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating daily report: {e}")
            return {}
    
    def check_bot_health(self) -> Dict[str, any]:
        """Verifica a saúde do bot"""
        health_report = {
            'status': 'healthy',
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Verificar taxa de erro
            stats = self.db.get_statistics()
            
            # Se mais de 50% das ações falharam hoje
            today_total = stats['follows_today'] + stats['unfollows_today']
            if today_total > 0:
                # Calcular falhas (seria necessário adicionar esse campo nas stats)
                # Por enquanto assumimos que está OK
                pass
            
            # Verificar se há ações pendentes há muito tempo
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM actions 
                WHERE status = 'pending'
                AND scheduled_for < datetime('now', '-1 hour')
            ''')
            old_pending = cursor.fetchone()[0]
            
            if old_pending > 10:
                health_report['status'] = 'warning'
                health_report['issues'].append(f"{old_pending} ações pendentes há mais de 1 hora")
                health_report['recommendations'].append("Verificar conectividade do dispositivo")
            
            # Verificar se o bot está seguindo muito rápido
            cursor.execute('''
                SELECT COUNT(*) FROM actions 
                WHERE action_type = 'follow'
                AND status = 'completed'
                AND performed_at > datetime('now', '-1 hour')
            ''')
            recent_follows = cursor.fetchone()[0]
            
            if recent_follows > 20:  # Mais de 20 follows por hora pode ser suspeito
                health_report['status'] = 'warning'
                health_report['issues'].append(f"{recent_follows} follows na última hora")
                health_report['recommendations'].append("Considerar aumentar delays entre ações")
            
            conn.close()
            
        except Exception as e:
            health_report['status'] = 'error'
            health_report['issues'].append(f"Erro ao verificar saúde: {str(e)}")
        
        return health_report
    
    def export_data(self, export_type: str = 'csv') -> Optional[str]:
        """Exporta dados do bot"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if export_type == 'csv':
                import pandas as pd
                import sqlite3
                
                conn = sqlite3.connect(self.db.db_path)
                
                # Exportar dados de followers e ações
                query = '''
                    SELECT 
                        f.username, f.profile_link, f.created_at,
                        a.action_type, a.status, a.performed_at,
                        fb.followed_back, fb.checked_at
                    FROM followers f
                    LEFT JOIN actions a ON f.id = a.follower_id
                    LEFT JOIN follow_backs fb ON f.id = fb.follower_id
                    ORDER BY f.created_at DESC
                '''
                
                df = pd.read_sql_query(query, conn)
                filename = f"instagram_bot_export_{timestamp}.csv"
                df.to_csv(filename, index=False)
                
                conn.close()
                return filename
                
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            return None_stats['follow_stats'] = self.execute_follow_batch()
            
            # 2. Verificar follow-backs
            self.logger.info("Checking follow-backs")
            cycle_stats['check_stats'] = self.check_follow_backs()
            
            # 3. Executar unfollows
            self.logger.info("Executing unfollow batch")
            cycle_stats['unfollow_stats'] = self.execute_unfollow_batch()
            
            cycle