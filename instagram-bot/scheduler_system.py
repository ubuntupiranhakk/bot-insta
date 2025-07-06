import schedule
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
import json
import signal
import sys
from dataclasses import dataclass
from enum import Enum

# Importar nossas classes
from improved_db_schema import InstagramDatabase
from instagram_automation import InstagramBot

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ScheduledTask:
    """Representa uma tarefa agendada"""
    id: str
    name: str
    function: Callable
    args: tuple = ()
    kwargs: dict = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    error_message: str = None
    result: any = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.created_at is None:
            self.created_at = datetime.now()

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
            return None

class BotScheduler:
    """Agendador principal do bot do Instagram"""
    
    def __init__(self, db_instance: InstagramDatabase, device_id: Optional[str] = None):
        self.db = db_instance
        self.device_id = device_id
        self.bot = None
        self.monitor = BotMonitor(db_instance)
        self.logger = logging.getLogger(__name__)
        
        # Estado do scheduler
        self.is_running = False
        self.current_task = None
        self.task_history: List[ScheduledTask] = []
        
        # Thread para execução
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        
        # Configurações
        self.load_settings()
        
        # Registrar handlers para shutdown graceful
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def load_settings(self):
        """Carrega configurações do banco de dados"""
        self.follow_interval_minutes = int(self.db.get_setting('follow_interval_minutes') or 5)
        self.follow_back_check_hours = int(self.db.get_setting('follow_back_check_hours') or 24)
        self.max_daily_follows = int(self.db.get_setting('max_daily_follows') or 100)
        self.max_daily_unfollows = int(self.db.get_setting('max_daily_unfollows') or 50)
        
        self.logger.info(f"Scheduler settings loaded: follow_interval={self.follow_interval_minutes}min")
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de sistema (Ctrl+C, etc.)"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
    
    def initialize_bot(self) -> bool:
        """Inicializa o bot do Instagram"""
        try:
            self.bot = InstagramBot(self.db, self.device_id)
            success = self.bot.initialize()
            
            if success:
                self.logger.info("Bot initialized successfully")
                self.db.log_message('INFO', 'Bot initialized successfully', 'BotScheduler', 'initialize_bot')
            else:
                self.logger.error("Failed to initialize bot")
                self.db.log_message('ERROR', 'Failed to initialize bot', 'BotScheduler', 'initialize_bot')
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error initializing bot: {e}")
            self.db.log_message('ERROR', f'Error initializing bot: {str(e)}', 'BotScheduler', 'initialize_bot')
            return False
    
    def create_task(self, name: str, function: Callable, *args, **kwargs) -> ScheduledTask:
        """Cria uma nova tarefa agendada"""
        task_id = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            function=function,
            args=args,
            kwargs=kwargs
        )
        
        self.task_history.append(task)
        self.logger.info(f"Created task: {task_id}")
        
        return task
    
    def execute_task(self, task: ScheduledTask) -> bool:
        """Executa uma tarefa"""
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            self.current_task = task
            
            self.logger.info(f"Executing task: {task.name}")
            self.db.log_message('INFO', f'Started executing task: {task.name}', 'BotScheduler', 'execute_task')
            
            # Executar a função
            result = task.function(*task.args, **task.kwargs)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            execution_time = (task.completed_at - task.started_at).total_seconds()
            self.logger.info(f"Task {task.name} completed in {execution_time:.2f} seconds")
            
            self.db.log_message(
                'INFO', 
                f'Task {task.name} completed successfully in {execution_time:.2f}s',
                'BotScheduler', 
                'execute_task'
            )
            
            return True
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            
            self.logger.error(f"Task {task.name} failed: {e}")
            self.db.log_message('ERROR', f'Task {task.name} failed: {str(e)}', 'BotScheduler', 'execute_task')
            
            return False
        
        finally:
            self.current_task = None
    
    def schedule_follow_batch(self):
        """Agenda execução de lote de follows"""
        def follow_batch_wrapper():
            if not self.bot:
                self.logger.error("Bot not initialized")
                return {'error': 'Bot not initialized'}
            
            return self.bot.execute_follow_batch()
        
        task = self.create_task("follow_batch", follow_batch_wrapper)
        return self.execute_task(task)
    
    def schedule_follow_back_check(self):
        """Agenda verificação de follow-backs"""
        def check_wrapper():
            if not self.bot:
                self.logger.error("Bot not initialized")
                return {'error': 'Bot not initialized'}
            
            return self.bot.check_follow_backs()
        
        task = self.create_task("follow_back_check", check_wrapper)
        return self.execute_task(task)
    
    def schedule_unfollow_batch(self):
        """Agenda execução de lote de unfollows"""
        def unfollow_batch_wrapper():
            if not self.bot:
                self.logger.error("Bot not initialized")
                return {'error': 'Bot not initialized'}
            
            return self.bot.execute_unfollow_batch()
        
        task = self.create_task("unfollow_batch", unfollow_batch_wrapper)
        return self.execute_task(task)
    
    def schedule_full_cycle(self):
        """Agenda ciclo completo de automação"""
        def full_cycle_wrapper():
            if not self.bot:
                self.logger.error("Bot not initialized")
                return {'error': 'Bot not initialized'}
            
            return self.bot.run_automation_cycle()
        
        task = self.create_task("full_automation_cycle", full_cycle_wrapper)
        return self.execute_task(task)
    
    def schedule_health_check(self):
        """Agenda verificação de saúde do bot"""
        def health_check_wrapper():
            return self.monitor.check_bot_health()
        
        task = self.create_task("health_check", health_check_wrapper)
        return self.execute_task(task)
    
    def schedule_daily_report(self):
        """Agenda geração de relatório diário"""
        def daily_report_wrapper():
            return self.monitor.generate_daily_report()
        
        task = self.create_task("daily_report", daily_report_wrapper)
        return self.execute_task(task)
    
    def setup_schedules(self):
        """Configura todos os agendamentos"""
        # Limpar agendamentos anteriores
        schedule.clear()
        
        # Follows a cada X minutos
        schedule.every(self.follow_interval_minutes).minutes.do(self.schedule_follow_batch)
        
        # Verificação de follow-backs a cada hora
        schedule.every().hour.do(self.schedule_follow_back_check)
        
        # Unfollows a cada 2 horas
        schedule.every(2).hours.do(self.schedule_unfollow_batch)
        
        # Ciclo completo a cada 6 horas (backup/redundância)
        schedule.every(6).hours.do(self.schedule_full_cycle)
        
        # Verificação de saúde a cada 30 minutos
        schedule.every(30).minutes.do(self.schedule_health_check)
        
        # Relatório diário às 23:00
        schedule.every().day.at("23:00").do(self.schedule_daily_report)
        
        # Reinicialização do bot às 06:00 (para limpar estado)
        schedule.every().day.at("06:00").do(self.reinitialize_bot)
        
        self.logger.info("All schedules configured")
        self.db.log_message('INFO', 'Scheduler configured with all tasks', 'BotScheduler', 'setup_schedules')
    
    def reinitialize_bot(self):
        """Reinicializa o bot (útil para limpeza diária)"""
        def reinit_wrapper():
            self.logger.info("Reinitializing bot...")
            
            # Parar bot atual se existir
            if self.bot and hasattr(self.bot, 'adb'):
                try:
                    self.bot.adb.stop_app(self.bot.adb.device_info.instagram_package)
                except:
                    pass
            
            # Reinicializar
            success = self.initialize_bot()
            return {'success': success, 'message': 'Bot reinitialized' if success else 'Failed to reinitialize bot'}
        
        task = self.create_task("reinitialize_bot", reinit_wrapper)
        return self.execute_task(task)
    
    def run_scheduler(self):
        """Executa o loop principal do agendador"""
        self.logger.info("Starting scheduler loop")
        
        while not self.stop_event.is_set():
            try:
                # Verificar e executar tarefas agendadas
                schedule.run_pending()
                
                # Aguardar 1 minuto antes da próxima verificação
                if not self.stop_event.wait(60):
                    continue
                else:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                self.db.log_message('ERROR', f'Scheduler loop error: {str(e)}', 'BotScheduler', 'run_scheduler')
                
                # Aguardar antes de tentar novamente
                time.sleep(60)
        
        self.logger.info("Scheduler loop stopped")
    
    def start(self) -> bool:
        """Inicia o agendador"""
        if self.is_running:
            self.logger.warning("Scheduler is already running")
            return False
        
        self.logger.info("Starting Instagram bot scheduler...")
        
        # Inicializar bot
        if not self.initialize_bot():
            self.logger.error("Failed to initialize bot, cannot start scheduler")
            return False
        
        # Configurar agendamentos
        self.setup_schedules()
        
        # Iniciar thread do scheduler
        self.is_running = True
        self.stop_event.clear()
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("Scheduler started successfully")
        self.db.log_message('INFO', 'Instagram bot scheduler started', 'BotScheduler', 'start')
        
        return True
    
    def stop(self):
        """Para o agendador"""
        if not self.is_running:
            self.logger.warning("Scheduler is not running")
            return
        
        self.logger.info("Stopping scheduler...")
        
        # Sinalizar parada
        self.is_running = False
        self.stop_event.set()
        
        # Aguardar thread terminar
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=30)
        
        # Parar Instagram se estiver rodando
        if self.bot and hasattr(self.bot, 'adb') and self.bot.adb.device_info:
            try:
                self.bot.adb.stop_app(self.bot.adb.device_info.instagram_package)
            except:
                pass
        
        self.logger.info("Scheduler stopped")
        self.db.log_message('INFO', 'Instagram bot scheduler stopped', 'BotScheduler', 'stop')
    
    def get_status(self) -> Dict[str, any]:
        """Retorna status atual do agendador"""
        status = {
            'is_running': self.is_running,
            'current_task': None,
            'next_runs': {},
            'task_history_count': len(self.task_history),
            'recent_tasks': [],
            'bot_initialized': self.bot is not None
        }
        
        # Informações da tarefa atual
        if self.current_task:
            status['current_task'] = {
                'id': self.current_task.id,
                'name': self.current_task.name,
                'status': self.current_task.status.value,
                'started_at': self.current_task.started_at.isoformat() if self.current_task.started_at else None
            }
        
        # Próximas execuções
        for job in schedule.jobs:
            job_name = job.job_func.__name__ if hasattr(job.job_func, '__name__') else str(job.job_func)
            next_run = job.next_run
            status['next_runs'][job_name] = next_run.isoformat() if next_run else None
        
        # Tarefas recentes (últimas 10)
        recent_tasks = sorted(self.task_history, key=lambda x: x.created_at, reverse=True)[:10]
        status['recent_tasks'] = [
            {
                'id': task.id,
                'name': task.name,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error_message': task.error_message
            }
            for task in recent_tasks
        ]
        
        return status
    
    def execute_manual_task(self, task_name: str) -> Dict[str, any]:
        """Executa uma tarefa manualmente"""
        task_methods = {
            'follow_batch': self.schedule_follow_batch,
            'follow_back_check': self.schedule_follow_back_check,
            'unfollow_batch': self.schedule_unfollow_batch,
            'full_cycle': self.schedule_full_cycle,
            'health_check': self.schedule_health_check,
            'daily_report': self.schedule_daily_report,
            'reinitialize_bot': self.reinitialize_bot
        }
        
        if task_name not in task_methods:
            return {'success': False, 'message': f'Unknown task: {task_name}'}
        
        try:
            success = task_methods[task_name]()
            return {
                'success': success,
                'message': f'Task {task_name} executed successfully' if success else f'Task {task_name} failed'
            }
        except Exception as e:
            return {'success': False, 'message': f'Error executing task {task_name}: {str(e)}'}

# Classe para interface de linha de comando
class BotCLI:
    """Interface de linha de comando para o bot"""
    
    def __init__(self, scheduler: BotScheduler):
        self.scheduler = scheduler
        self.logger = logging.getLogger(__name__)
    
    def start_interactive_mode(self):
        """Inicia modo interativo do CLI"""
        print("🤖 Instagram Bot CLI")
        print("Digite 'help' para ver comandos disponíveis")
        print("Digite 'quit' para sair")
        print("-" * 50)
        
        while True:
            try:
                command = input("bot> ").strip().lower()
                
                if command == 'quit' or command == 'exit':
                    print("Saindo...")
                    break
                elif command == 'help':
                    self.show_help()
                elif command == 'status':
                    self.show_status()
                elif command == 'start':
                    self.start_scheduler()
                elif command == 'stop':
                    self.stop_scheduler()
                elif command == 'stats':
                    self.show_stats()
                elif command.startswith('run '):
                    task_name = command[4:]
                    self.run_manual_task(task_name)
                elif command == 'health':
                    self.show_health()
                elif command == 'report':
                    self.show_daily_report()
                elif command == 'export':
                    self.export_data()
                elif command == 'logs':
                    self.show_recent_logs()
                else:
                    print(f"Comando desconhecido: {command}")
                    print("Digite 'help' para ver comandos disponíveis")
                    
            except KeyboardInterrupt:
                print("\nSaindo...")
                break
            except Exception as e:
                print(f"Erro: {e}")
    
    def show_help(self):
        """Mostra ajuda dos comandos"""
        help_text = """
Comandos disponíveis:

📊 INFORMAÇÕES:
  status    - Mostra status do scheduler
  stats     - Mostra estatísticas gerais
  health    - Verifica saúde do bot
  report    - Gera relatório diário
  logs      - Mostra logs recentes

🎮 CONTROLE:
  start     - Inicia o scheduler
  stop      - Para o scheduler
  
🚀 EXECUÇÃO MANUAL:
  run follow_batch       - Executa lote de follows
  run follow_back_check  - Verifica follow-backs
  run unfollow_batch     - Executa lote de unfollows
  run full_cycle         - Executa ciclo completo
  run health_check       - Verifica saúde
  run daily_report       - Gera relatório
  run reinitialize_bot   - Reinicializa bot

📁 DADOS:
  export    - Exporta dados para CSV

❓ OUTROS:
  help      - Mostra esta ajuda
  quit/exit - Sai do programa
        """
        print(help_text)
    
    def show_status(self):
        """Mostra status do scheduler"""
        status = self.scheduler.get_status()
        
        print("\n📊 STATUS DO SCHEDULER")
        print("-" * 30)
        print(f"🔄 Running: {'✅ Sim' if status['is_running'] else '❌ Não'}")
        print(f"🤖 Bot: {'✅ Inicializado' if status['bot_initialized'] else '❌ Não inicializado'}")
        
        if status['current_task']:
            task = status['current_task']
            print(f"⚡ Tarefa atual: {task['name']} ({task['status']})")
        else:
            print("⚡ Tarefa atual: Nenhuma")
        
        print(f"📋 Total de tarefas: {status['task_history_count']}")
        
        if status['next_runs']:
            print("\n⏰ PRÓXIMAS EXECUÇÕES:")
            for job_name, next_run in status['next_runs'].items():
                if next_run:
                    next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                    print(f"  {job_name}: {next_run_dt.strftime('%H:%M:%S')}")
        
        if status['recent_tasks']:
            print("\n📝 TAREFAS RECENTES:")
            for task in status['recent_tasks'][:5]:
                status_emoji = {'completed': '✅', 'failed': '❌', 'running': '⚡', 'pending': '⏳'}.get(task['status'], '❓')
                print(f"  {status_emoji} {task['name']} - {task['status']}")
                if task['error_message']:
                    print(f"    Erro: {task['error_message']}")
        
        print()
    
    def start_scheduler(self):
        """Inicia o scheduler"""
        print("🚀 Iniciando scheduler...")
        success = self.scheduler.start()
        if success:
            print("✅ Scheduler iniciado com sucesso!")
        else:
            print("❌ Falha ao iniciar scheduler")
    
    def stop_scheduler(self):
        """Para o scheduler"""
        print("🛑 Parando scheduler...")
        self.scheduler.stop()
        print("✅ Scheduler parado")
    
    def show_stats(self):
        """Mostra estatísticas"""
        stats = self.scheduler.db.get_statistics()
        
        print("\n📊 ESTATÍSTICAS GERAIS")
        print("-" * 30)
        print(f"👥 Total de seguidores: {stats['total_followers']}")
        print(f"➕ Follows hoje: {stats['follows_today']}")
        print(f"➖ Unfollows hoje: {stats['unfollows_today']}")
        print(f"🔄 Follow-backs recebidos: {stats['follow_backs_received']}")
        print(f"📈 Taxa de follow-back: {stats['follow_back_rate']:.1f}%")
        
        # Verificar limites
        max_follows = int(self.scheduler.db.get_setting('max_daily_follows') or 100)
        max_unfollows = int(self.scheduler.db.get_setting('max_daily_unfollows') or 50)
        
        print(f"\n⚖️ LIMITES DIÁRIOS:")
        print(f"➕ Follows: {stats['follows_today']}/{max_follows} ({(stats['follows_today']/max_follows)*100:.1f}%)")
        print(f"➖ Unfollows: {stats['unfollows_today']}/{max_unfollows} ({(stats['unfollows_today']/max_unfollows)*100:.1f}%)")
        print()
    
    def run_manual_task(self, task_name: str):
        """Executa tarefa manual"""
        print(f"🚀 Executando tarefa: {task_name}")
        result = self.scheduler.execute_manual_task(task_name)
        
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")
    
    def show_health(self):
        """Mostra verificação de saúde"""
        health = self.scheduler.monitor.check_bot_health()
        
        print(f"\n🏥 SAÚDE DO BOT")
        print("-" * 20)
        
        status_emoji = {'healthy': '✅', 'warning': '⚠️', 'error': '❌'}
        print(f"Status: {status_emoji.get(health['status'], '❓')} {health['status'].upper()}")
        
        if health['issues']:
            print("\n⚠️ PROBLEMAS ENCONTRADOS:")
            for issue in health['issues']:
                print(f"  • {issue}")
        
        if health['recommendations']:
            print("\n💡 RECOMENDAÇÕES:")
            for rec in health['recommendations']:
                print(f"  • {rec}")
        
        print()
    
    def show_daily_report(self):
        """Mostra relatório diário"""
        report = self.scheduler.monitor.generate_daily_report()
        
        if not report:
            print("❌ Erro ao gerar relatório")
            return
        
        print(f"\n📋 RELATÓRIO DIÁRIO - {report['date']}")
        print("-" * 40)
        
        print(f"➕ FOLLOWS:")
        print(f"  Completados: {report['follows']['completed']}")
        print(f"  Falharam: {report['follows']['failed']}")
        if report['follows']['avg_delay_minutes']:
            print(f"  Delay médio: {report['follows']['avg_delay_minutes']:.1f} min")
        
        print(f"\n➖ UNFOLLOWS:")
        print(f"  Completados: {report['unfollows']['completed']}")
        
        print(f"\n🔄 FOLLOW-BACKS:")
        print(f"  Recebidos: {report['follow_backs']['received']}")
        print(f"  Taxa: {report['follow_backs']['rate']:.1f}%")
        
        print(f"\n📊 EFICIÊNCIA:")
        print(f"  Taxa de sucesso: {report['efficiency']['success_rate']:.1f}%")
        
        if report['errors']:
            print(f"\n❌ ERROS:")
            for error, count in report['errors'].items():
                print(f"  {error}: {count}x")
        
        print()
    
    def export_data(self):
        """Exporta dados"""
        print("📁 Exportando dados...")
        filename = self.scheduler.monitor.export_data('csv')
        
        if filename:
            print(f"✅ Dados exportados para: {filename}")
        else:
            print("❌ Erro ao exportar dados")
    
    def show_recent_logs(self):
        """Mostra logs recentes"""
        import sqlite3
        
        conn = sqlite3.connect(self.scheduler.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT level, message, timestamp, module
            FROM logs 
            ORDER BY timestamp DESC 
            LIMIT 20
        ''')
        
        logs = cursor.fetchall()
        conn.close()
        
        if not logs:
            print("📝 Nenhum log encontrado")
            return
        
        print("\n📝 LOGS RECENTES (últimos 20)")
        print("-" * 50)
        
        level_colors = {
            'DEBUG': '🔍',
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌'
        }
        
        for level, message, timestamp, module in logs:
            emoji = level_colors.get(level, '📝')
            time_str = datetime.fromisoformat(timestamp).strftime('%H:%M:%S')
            module_str = f"[{module}]" if module else ""
            print(f"{emoji} {time_str} {module_str} {message}")
        
        print()

# Função principal para executar o bot
def main():
    """Função principal do bot"""
    import argparse
    import sys
    import os
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('instagram_bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Parser de argumentos
    parser = argparse.ArgumentParser(description='Instagram Automation Bot')
    parser.add_argument('--device-id', help='ID do dispositivo Android')
    parser.add_argument('--db-path', default='instagram_automation.db', help='Caminho do banco de dados')
    parser.add_argument('--mode', choices=['scheduler', 'cli', 'once'], default='cli', 
                       help='Modo de execução: scheduler (daemon), cli (interativo), once (execução única)')
    parser.add_argument('--task', help='Tarefa para executar no modo "once"')
    
    args = parser.parse_args()
    
    # Inicializar banco de dados
    db = InstagramDatabase(args.db_path)
    
    # Inicializar scheduler
    scheduler = BotScheduler(db, args.device_id)
    
    try:
        if args.mode == 'scheduler':
            # Modo daemon
            print("🤖 Iniciando bot em modo scheduler (daemon)")
            if scheduler.start():
                print("✅ Scheduler iniciado. Pressione Ctrl+C para parar.")
                try:
                    # Manter vivo
                    while scheduler.is_running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n🛑 Parando scheduler...")
                    scheduler.stop()
            else:
                print("❌ Falha ao iniciar scheduler")
                sys.exit(1)
        
        elif args.mode == 'cli':
            # Modo interativo
            cli = BotCLI(scheduler)
            cli.start_interactive_mode()
        
        elif args.mode == 'once':
            # Execução única
            if not args.task:
                print("❌ Especifique uma tarefa com --task")
                sys.exit(1)
            
            print(f"🚀 Executando tarefa única: {args.task}")
            
            # Inicializar bot
            if not scheduler.initialize_bot():
                print("❌ Falha ao inicializar bot")
                sys.exit(1)
            
            # Executar tarefa
            result = scheduler.execute_manual_task(args.task)
            
            if result['success']:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")
                sys.exit(1)
    
    except Exception as e:
        logging.error(f"Erro fatal: {e}")
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)
    
    finally:
        # Cleanup
        if scheduler.is_running:
            scheduler.stop()

if __name__ == "__main__":
    main()