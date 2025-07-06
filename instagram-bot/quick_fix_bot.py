#!/usr/bin/env python3
"""
Correção rápida - adiciona InstagramBot simples
"""

import os

def add_simple_bot():
    """Adiciona uma versão simples do InstagramBot"""
    
    # Verificar se arquivo existe
    if not os.path.exists("instagram_automation.py"):
        print("❌ instagram_automation.py não encontrado")
        return False
    
    # Ler arquivo atual
    with open("instagram_automation.py", "r") as f:
        content = f.read()
    
    # Verificar se já tem a classe
    if "class InstagramBot:" in content:
        print("✅ InstagramBot já existe!")
        return True
    
    print("🔧 Adicionando InstagramBot simples...")
    
    # Classe simples
    bot_class = '''

class InstagramBot:
    """Bot principal - versão simples para testes"""
    
    def __init__(self, db_instance, device_id=None):
        self.db = db_instance
        self.device_id = device_id
        self.logger = __import__('logging').getLogger(__name__)
        
        # Configurações
        self.max_follows_per_day = 50
        self.follows_per_batch = 5
        self.min_delay = 30
        self.max_delay = 120
    
    def initialize(self):
        """Inicializa o bot"""
        self.logger.info("Bot inicializado (modo simulação)")
        return True
    
    def execute_follow_batch(self):
        """Executa lote de follows (simulação)"""
        import random
        import time
        
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        try:
            followers = self.db.get_followers_to_follow(self.follows_per_batch)
            
            if not followers:
                self.logger.info("Nenhum seguidor para seguir")
                return stats
            
            for follower in followers:
                username = follower['username']
                follower_id = follower['id']
                
                self.logger.info(f"Simulando follow: {username}")
                
                # Registrar ação
                action_id = self.db.record_action(follower_id, 'follow', 'pending')
                
                # Simular sucesso/falha
                if random.random() > 0.2:  # 80% sucesso
                    self.db.update_action_status(action_id, 'completed')
                    
                    # Agendar verificação de follow-back
                    from datetime import datetime
                    self.db.schedule_follow_back_check(follower_id, datetime.now())
                    
                    stats['success'] += 1
                    self.logger.info(f"✅ Follow simulado: {username}")
                else:
                    self.db.update_action_status(action_id, 'failed', 'Falha simulada')
                    stats['failed'] += 1
                    self.logger.warning(f"❌ Follow falhou: {username}")
                
                # Delay
                delay = random.randint(self.min_delay, self.max_delay)
                self.logger.info(f"Aguardando {delay}s...")
                time.sleep(delay)
        
        except Exception as e:
            self.logger.error(f"Erro no batch: {e}")
            stats['failed'] += self.follows_per_batch
        
        return stats
    
    def check_follow_backs(self):
        """Verifica follow-backs (simulação)"""
        import random
        
        stats = {'checked': 0, 'following_back': 0, 'not_following_back': 0}
        
        try:
            follow_backs = self.db.get_follow_backs_to_check()
            
            for fb in follow_backs:
                username = fb['username']
                fb_id = fb['id']
                
                self.logger.info(f"Verificando follow-back: {username}")
                
                # Simular resultado (30% seguem de volta)
                followed_back = random.random() < 0.3
                
                self.db.update_follow_back_status(fb_id, followed_back)
                
                if followed_back:
                    stats['following_back'] += 1
                    self.logger.info(f"✅ {username} seguiu de volta!")
                else:
                    stats['not_following_back'] += 1
                    self.logger.info(f"❌ {username} não seguiu de volta")
                
                stats['checked'] += 1
        
        except Exception as e:
            self.logger.error(f"Erro verificando follow-backs: {e}")
        
        return stats
    
    def execute_unfollow_batch(self):
        """Executa unfollows (simulação)"""
        import random
        import sqlite3
        
        stats = {'success': 0, 'failed': 0}
        
        try:
            # Buscar quem não seguiu de volta
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT fb.follower_id, f.username
                FROM follow_backs fb
                JOIN followers f ON fb.follower_id = f.id
                WHERE fb.followed_back = 0
                AND fb.unfollowed_at IS NULL
                LIMIT 10
            """)
            
            users_to_unfollow = cursor.fetchall()
            conn.close()
            
            for follower_id, username in users_to_unfollow:
                self.logger.info(f"Simulando unfollow: {username}")
                
                action_id = self.db.record_action(follower_id, 'unfollow', 'pending')
                
                # Simular unfollow (90% sucesso)
                if random.random() > 0.1:
                    self.db.update_action_status(action_id, 'completed')
                    
                    # Marcar como unfollowed
                    conn = sqlite3.connect(self.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE follow_backs 
                        SET unfollowed_at = CURRENT_TIMESTAMP
                        WHERE follower_id = ?
                    """, (follower_id,))
                    conn.commit()
                    conn.close()
                    
                    stats['success'] += 1
                    self.logger.info(f"✅ Unfollow simulado: {username}")
                else:
                    self.db.update_action_status(action_id, 'failed', 'Falha simulada')
                    stats['failed'] += 1
        
        except Exception as e:
            self.logger.error(f"Erro no unfollow: {e}")
        
        return stats
    
    def run_automation_cycle(self):
        """Executa ciclo completo"""
        from datetime import datetime
        import time
        
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
            self.logger.info("🚀 Iniciando ciclo de automação")
            
            # 1. Follows
            self.logger.info("📤 Executando follows...")
            cycle_stats['follow_stats'] = self.execute_follow_batch()
            
            # 2. Verificar follow-backs
            self.logger.info("🔍 Verificando follow-backs...")
            cycle_stats['check_stats'] = self.check_follow_backs()
            
            # 3. Unfollows
            self.logger.info("📥 Executando unfollows...")
            cycle_stats['unfollow_stats'] = self.execute_unfollow_batch()
            
            cycle_stats['completed_at'] = datetime.now()
            cycle_stats['total_execution_time'] = time.time() - start_time
            
            self.logger.info(f"✅ Ciclo concluído em {cycle_stats['total_execution_time']:.1f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Erro no ciclo: {e}")
            cycle_stats['error'] = str(e)
            cycle_stats['completed_at'] = datetime.now()
            cycle_stats['total_execution_time'] = time.time() - start_time
        
        return cycle_stats
'''
    
    # Adicionar ao final do arquivo
    with open("instagram_automation.py", "a") as f:
        f.write(bot_class)
    
    print("✅ InstagramBot adicionado!")
    return True

def main():
    print("🔧 CORREÇÃO RÁPIDA - INSTAGRAMBOT")
    print("=" * 35)
    
    if add_simple_bot():
        print("\n✅ SUCESSO!")
        print("\n🚀 Agora teste:")
        print("python scheduler_system.py --mode cli")
        print("\n💡 Esta versão usa SIMULAÇÃO")
        print("- Registra ações no banco")
        print("- Não faz ações reais no Instagram")
        print("- Perfeito para testar o sistema!")
    else:
        print("\n❌ Falha na correção")

if __name__ == "__main__":
    main()
