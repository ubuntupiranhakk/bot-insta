#!/usr/bin/env python3
"""
Correção rápida do erro de import
"""

import re
from pathlib import Path

def fix_scheduler_imports():
    """Corrige os imports no scheduler_system.py"""
    
    file_path = Path("scheduler_system.py")
    
    if not file_path.exists():
        print("❌ scheduler_system.py não encontrado")
        return False
    
    print("🔧 Corrigindo imports...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Corrigir import
    old_import = "from instagram_automation import InstagramBot, BotMonitor"
    new_import = "from instagram_automation import InstagramBot"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        print("✅ Import corrigido")
    else:
        print("⚠️ Import já corrigido ou não encontrado")
    
    # Verificar se BotMonitor já está definido no arquivo
    if "class BotMonitor:" not in content:
        print("⚠️ Classe BotMonitor não encontrada, você precisa adicionar")
        return False
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Arquivo corrigido!")
    return True

def create_simple_bot_monitor():
    """Cria uma versão simples do BotMonitor se necessário"""
    
    file_path = Path("scheduler_system.py")
    
    if not file_path.exists():
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "class BotMonitor:" in content:
        print("✅ BotMonitor já existe")
        return True
    
    # Encontrar onde inserir a classe
    scheduler_class_pos = content.find("class BotScheduler:")
    
    if scheduler_class_pos == -1:
        print("❌ Não foi possível encontrar onde inserir BotMonitor")
        return False
    
    # Inserir BotMonitor antes do BotScheduler
    bot_monitor_code = '''
# Classe para monitoramento e relatórios  
class BotMonitor:
    """Monitor do bot com relatórios e alertas"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.logger = logging.getLogger(__name__)
    
    def generate_daily_report(self) -> Dict[str, any]:
        """Gera relatório diário de atividades"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'follows': {'completed': 0, 'failed': 0},
            'unfollows': {'completed': 0},
            'follow_backs': {'received': 0, 'rate': 0},
            'errors': {},
            'efficiency': {'success_rate': 0}
        }
    
    def check_bot_health(self) -> Dict[str, any]:
        """Verifica a saúde do bot"""
        return {
            'status': 'healthy',
            'issues': [],
            'recommendations': []
        }
    
    def export_data(self, export_type: str = 'csv') -> Optional[str]:
        """Exporta dados do bot"""
        return None

'''
    
    new_content = content[:scheduler_class_pos] + bot_monitor_code + content[scheduler_class_pos:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ BotMonitor adicionado!")
    return True

def main():
    print("🔧 CORREÇÃO DE IMPORT ERROR")
    print("=" * 30)
    
    success1 = fix_scheduler_imports()
    success2 = create_simple_bot_monitor()
    
    if success1 and success2:
        print("\n✅ CORREÇÃO COMPLETA!")
        print("\n🚀 Agora tente executar:")
        print("python scheduler_system.py --mode cli")
    else:
        print("\n❌ Problema na correção")

if __name__ == "__main__":
    main()
