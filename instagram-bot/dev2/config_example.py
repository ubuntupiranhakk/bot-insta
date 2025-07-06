#!/usr/bin/env python3
"""
Configurações do Instagram Bot
Personalize aqui os parâmetros do bot
"""

# ==================== CONFIGURAÇÕES GERAIS ====================

# Máximo de usuários para seguir por sessão
MAX_FOLLOWS_PER_SESSION = 10

# Máximo de unfollows por sessão  
MAX_UNFOLLOWS_PER_SESSION = 20

# Tempo para verificar unfollow (em horas)
UNFOLLOW_CHECK_DELAY_HOURS = 24

# ==================== DELAYS (em segundos) ====================

# Delay entre follows (min, max)
DELAY_BETWEEN_FOLLOWS = (45, 90)

# Delay entre unfollows (min, max)
DELAY_BETWEEN_UNFOLLOWS = (30, 60)

# Tempo para aguardar app carregar
APP_LOAD_WAIT_TIME = 5

# Tempo para aguardar navegador carregar
BROWSER_LOAD_WAIT_TIME = 3

# ==================== CONFIGURAÇÕES DO OCR ====================

# Caminho do Tesseract (ajustar conforme sistema)
TESSERACT_PATH = {
    'windows': r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    'linux': '/usr/bin/tesseract',
    'mac': '/usr/local/bin/tesseract'
}

# Idiomas para OCR
OCR_LANGUAGES = 'por+eng'  # Português + Inglês

# Configurações do Tesseract
OCR_CONFIG = '--psm 6'

# ==================== TEXTOS DOS BOTÕES ====================

BUTTON_TEXTS = {
    'open_instagram': [
        'Abrir Instagram', 
        'Abrir o Instagram', 
        'Open Instagram',
        'Abrir',
        'Open'
    ],
    'follow': [
        'Seguir', 
        'Follow'
    ],
    'following': [
        'Seguindo', 
        'Following'
    ],
    'unfollow': [
        'Deixar de seguir', 
        'Unfollow',
        'Deixar'
    ],
    'confirm_unfollow': [
        'Deixar de seguir',
        'Unfollow',
        'Sim',
        'Yes'
    ]
}

# ==================== CONFIGURAÇÕES DE SEGURANÇA ====================

# Variação de pixels para simular toque humano
TAP_VARIATION = 5

# Tempo mínimo entre ações (segundos)
MIN_ACTION_DELAY = 1

# Tempo máximo entre ações (segundos) 
MAX_ACTION_DELAY = 3

# ==================== CONFIGURAÇÕES DO BANCO ====================

# Nome do arquivo do banco de dados
DATABASE_NAME = 'instagram_bot.db'

# ==================== CONFIGURAÇÕES DE LOG ====================

# Nível de log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = 'INFO'

# Formato do log
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# Salvar logs em arquivo
SAVE_LOGS_TO_FILE = True
LOG_FILENAME = 'bot.log'

# ==================== CONFIGURAÇÕES DE SCREENSHOT ====================

# Salvar screenshots automaticamente
AUTO_SCREENSHOT = True

# Pasta para salvar screenshots
SCREENSHOT_FOLDER = 'screenshots'

# Manter screenshots por quantos dias
KEEP_SCREENSHOTS_DAYS = 7

# ==================== CONFIGURAÇÕES AVANÇADAS ====================

# Tentar novamente em caso de erro
MAX_RETRIES = 2

# Timeout para comandos ADB (segundos)
ADB_TIMEOUT = 30

# Verificar status da internet antes de executar
CHECK_INTERNET = True

# URL para testar internet
INTERNET_CHECK_URL = 'https://www.google.com'

# ==================== PERFIS DE USO ====================

# Perfil conservador (para evitar bloqueios)
CONSERVATIVE_PROFILE = {
    'max_follows_per_session': 5,
    'max_unfollows_per_session': 10,
    'delay_between_follows': (60, 120),
    'delay_between_unfollows': (45, 90),
    'unfollow_check_delay_hours': 48
}

# Perfil agressivo (mais rápido, mais risco)
AGGRESSIVE_PROFILE = {
    'max_follows_per_session': 20,
    'max_unfollows_per_session': 40,
    'delay_between_follows': (30, 60),
    'delay_between_unfollows': (20, 40),
    'unfollow_check_delay_hours': 12
}

# Perfil atual (pode ser 'default', 'conservative', 'aggressive')
CURRENT_PROFILE = 'default'

# ==================== FUNÇÕES AUXILIARES ====================

def get_profile_config():
    """Retorna configurações do perfil atual"""
    if CURRENT_PROFILE == 'conservative':
        return CONSERVATIVE_PROFILE
    elif CURRENT_PROFILE == 'aggressive':
        return AGGRESSIVE_PROFILE
    else:
        return {
            'max_follows_per_session': MAX_FOLLOWS_PER_SESSION,
            'max_unfollows_per_session': MAX_UNFOLLOWS_PER_SESSION,
            'delay_between_follows': DELAY_BETWEEN_FOLLOWS,
            'delay_between_unfollows': DELAY_BETWEEN_UNFOLLOWS,
            'unfollow_check_delay_hours': UNFOLLOW_CHECK_DELAY_HOURS
        }

def get_tesseract_path():
    """Retorna caminho do Tesseract baseado no SO"""
    import platform
    
    system = platform.system().lower()
    if 'windows' in system:
        return TESSERACT_PATH['windows']
    elif 'linux' in system:
        return TESSERACT_PATH['linux']
    elif 'darwin' in system:  # macOS
        return TESSERACT_PATH['mac']
    else:
        return '/usr/bin/tesseract'  # Padrão

# ==================== VALIDAÇÕES ====================

def validate_config():
    """Valida configurações"""
    errors = []
    
    # Verificar delays
    if DELAY_BETWEEN_FOLLOWS[0] < 30:
        errors.append("Delay mínimo entre follows deve ser >= 30s")
    
    if MAX_FOLLOWS_PER_SESSION > 50:
        errors.append("Máximo de follows por sessão não deve exceder 50")
    
    # Verificar Tesseract
    import os
    tesseract_path = get_tesseract_path()
    if not os.path.exists(tesseract_path):
        errors.append(f"Tesseract não encontrado em: {tesseract_path}")
    
    return errors

if __name__ == "__main__":
    # Testar configurações
    print("🔧 Testando configurações...")
    
    errors = validate_config()
    if errors:
        print("❌ Erros encontrados:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Configurações válidas!")
    
    print(f"\n📋 Perfil atual: {CURRENT_PROFILE}")
    profile = get_profile_config()
    for key, value in profile.items():
        print(f"  {key}: {value}")
    
    print(f"\n🔧 Tesseract: {get_tesseract_path()}")
