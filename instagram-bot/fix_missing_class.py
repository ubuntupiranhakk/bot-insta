#!/usr/bin/env python3
"""
Adiciona a classe InstagramBot que estava faltando
"""

from pathlib import Path

def add_missing_class():
    """Adiciona a classe InstagramBot ao arquivo"""
    
    file_path = Path("instagram_automation.py")
    
    if not file_path.exists():
        print("❌ instagram_automation.py não encontrado")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar se a classe já existe
    if "class InstagramBot:" in content:
        print("✅ InstagramBot já existe!")
        return True
    
    print("🔧 Adicionando classe InstagramBot...")
    
    # Código da classe InstagramBot
    instagram_bot_code = '''

class InstagramBot:
    """Bot principal que orquestra todas as operações"""
    
    def __init__(self, db_instance, device_id=None):
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
    
    def initialize(self):
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
    
    def execute_follow_batch(self):
        """Executa um lote de follows"""
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        try:
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
                    
                    # Simular sucesso por enquanto (até os templates estarem prontos)
                    import random
                    if random.random() > 0.2:  # 80% de sucesso
                        self.db.update_action_status(action_id, 'completed')
                        self.db.schedule_follow_back_check(follower_id, datetime.now())
                        stats['success'] += 1
                        self.logger.info(f"Successfully followed: {username}")
                    else:
                        self.db.update_action_status(action_id, 'failed', 'Simulated failure')
                        stats['failed'] += 1
                    
                    # Delay entre ações
                    time.sleep(random.randint(self.min_delay, self.max_delay))
                    
                except Exception as e:
                    self.logger.error(f"Error processing follower {username}: {e}")
                    stats['failed'] += 1
                    continue
        
        except Exception as e:
            self.logger.error(f"Error in execute_follow_batch: {e}")
            stats['failed'] += 1
        
        return stats
    
    def check_follow_backs(self):
        """Verifica follow-backs pendentes"""
        stats = {'checked': 0, 'following_back': 0, 'not_following_back': 0}
        
        try:
            follow_backs_to_check = self.db.get_follow_backs_to_check()
            
            for follow_back in follow_backs_to_check:
                try:
                    username = follow_back['username']
                    follow_back_id = follow_back['id']
                    
                    self.logger.info(f"Checking follow-back for: {username}")
                    
                    # Simular verificação
                    import random
                    followed_back = random.random() > 0.7  # 30% seguem de volta
                    
                    self.db.update_follow_back_status(follow_back_id, followed_back)
                    
                    if followed_back:
                        stats['following_back'] += 1
                    else:
                        stats['not_following_back'] += 1
                    
                    stats['checked'] += 1
                    
                    time.sleep(random.randint(5, 10))
                    
                except Exception as e:
                    self.logger.error(f"Error checking follow-back for {username}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error in check_follow_backs: {e}")
        
        return stats
    
    def execute_unfollow_batch(self):
        """Executa unfollows para quem não seguiu de volta"""
        stats = {'success': 0, 'failed': 0}
        
        try:
            # Obter usuários que não seguiram de volta
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute(\\'''
                SELECT fb.follower_id, f.username
                FROM follow_backs fb
                JOIN followers f ON fb.follower_id = f.id
                WHERE fb.followed_back = 0
                AND fb.unfollowed_at IS NULL
                LIMIT ?
            \\''', (self.max_unfollows_per_day,))
            
            users_to_unfollow = cursor.fetchall()
            conn.close()
            
            for follower_id, username in users_to_unfollow:
                try:
                    self.logger.info(f"Attempting to unfollow: {username}")
                    
                    action_id = self.db.record_action(follower_id, 'unfollow', 'pending')
                    
                    # Simular unfollow
                    import random
                    if random.random() > 0.1:  # 90% de sucesso
                        self.db.update_action_status(action_id, 'completed')
                        
                        # Marcar como unfollowed
                        conn = sqlite3.connect(self.db.db_path)
                        cursor = conn.cursor()
                        cursor.execute(\\'''
                            UPDATE follow_backs 
                            SET unfollowed_at = CURRENT_TIMESTAMP
                            WHERE follower_id = ?
                        \\''', (follower_id,))
                        conn.commit()
                        conn.close()
                        
                        stats['success'] += 1
                        self.logger.info(f"Successfully unfollowed: {username}")
                    else:
                        self.db.update_action_status(action_id, 'failed', 'Simulated failure')
                        stats['failed'] += 1
                    
                    time.sleep(random.randint(self.min_delay, self.max_delay))
                    
                except Exception as e:
                    self.logger.error(f"Error unfollowing {username}: {e}")
                    stats['failed'] += 1
                    continue
        
        except Exception as e:
            self.logger.error(f"Error in execute_unfollow_batch: {e}")
        
        return stats
    
    def run_automation_cycle(self):
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
                f"Automation cycle completed",
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
'''
    
    # Adicionar no final do arquivo
    content += instagram_bot_code
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Classe InstagramBot adicionada!")
    return True

def check_imports():
    """Verifica se os imports necessários estão presentes"""
    
    file_path = Path("instagram_automation.py")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_imports = [
        'import time',
        'import random',
        'import logging',
        'import json',
        'from datetime import datetime'
    ]
    
    missing_imports = []
    for imp in required_imports:
        if imp not in content:
            missing_imports.append(imp)
    
    if missing_imports:
        print(f"⚠️ Imports faltando: {missing_imports}")
        
        # Adicionar imports no início
        imports_to_add = '\\n'.join(missing_imports) + '\\n'
        
        # Encontrar onde adicionar (depois dos imports existentes)
        lines = content.split('\\n')
        insert_pos = 0
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_pos = i + 1
        
        lines.insert(insert_pos, imports_to_add)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(lines))
        
        print("✅ Imports adicionados!")
    else:
        print("✅ Imports OK!")

def main():
    print("🔧 ADICIONANDO CLASSE INSTAGRAMBOT")
    print("=" * 35)
    
    success1 = add_missing_class()
    check_imports()
    
    if success1:
        print("\\n✅ CLASSE ADICIONADA COM SUCESSO!")
        print("\\n🚀 Agora tente executar:")
        print("python scheduler_system.py --mode cli")
        print("\\n⚠️ NOTA: A classe usa simulação por enquanto")
        print("Funcionará para testar, mas não fará ações reais no Instagram")
        print("Para ações reais, você precisa dos templates!")
    else:
        print("\\n❌ Erro ao adicionar classe")

if __name__ == "__main__":
    main()
