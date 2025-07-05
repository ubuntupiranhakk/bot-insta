#!/usr/bin/env python3
"""
Instagram Bot Setup and Configuration Script
Configura e instala todas as dependências necessárias para o bot do Instagram
"""

import os
import sys
import subprocess
import platform
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

class InstagramBotSetup:
    """Classe para configuração inicial do bot"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.requirements_file = self.project_root / "requirements.txt"
        self.config_file = self.project_root / "config.json"
        self.templates_dir = self.project_root / "templates"
        self.logs_dir = self.project_root / "logs"
        self.exports_dir = self.project_root / "exports"
        
        # Detectar sistema operacional
        self.os_type = platform.system().lower()
        
    def print_header(self):
        """Imprime cabeçalho do setup"""
        print("=" * 60)
        print("🤖 INSTAGRAM AUTOMATION BOT - SETUP")
        print("=" * 60)
        print(f"Sistema operacional: {platform.system()}")
        print(f"Python: {sys.version}")
        print(f"Diretório do projeto: {self.project_root}")
        print("=" * 60)
    
    def check_python_version(self) -> bool:
        """Verifica se a versão do Python é compatível"""
        print("🐍 Verificando versão do Python...")
        
        if sys.version_info < (3, 8):
            print("❌ Python 3.8+ é necessário")
            print(f"   Versão atual: {sys.version}")
            return False
        
        print("✅ Versão do Python compatível")
        return True
    
    def check_adb_installation(self) -> bool:
        """Verifica se ADB está instalado"""
        print("📱 Verificando instalação do ADB...")
        
        try:
            result = subprocess.run(['adb', 'version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode == 0:
                print("✅ ADB encontrado")
                print(f"   Versão: {result.stdout.split()[4]}")
                return True
            else:
                print("❌ ADB não funciona corretamente")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ ADB não encontrado")
            self.show_adb_installation_instructions()
            return False
    
    def show_adb_installation_instructions(self):
        """Mostra instruções para instalar ADB"""
        print("\n📋 INSTRUÇÕES PARA INSTALAR ADB:")
        print("-" * 40)
        
        if self.os_type == "windows":
            print("Windows:")
            print("1. Baixe Android SDK Platform Tools:")
            print("   https://developer.android.com/studio/releases/platform-tools")
            print("2. Extraia em C:\\adb")
            print("3. Adicione C:\\adb ao PATH do sistema")
            print("4. Ou instale via Chocolatey: choco install adb")
            
        elif self.os_type == "darwin":  # macOS
            print("macOS:")
            print("1. Instale via Homebrew: brew install android-platform-tools")
            print("2. Ou baixe manualmente do link acima")
            
        elif self.os_type == "linux":
            print("Linux:")
            print("Ubuntu/Debian: sudo apt install android-tools-adb")
            print("Fedora: sudo dnf install android-tools")
            print("Arch: sudo pacman -S android-tools")
            
        print("\n⚠️  Depois de instalar, reinicie o terminal e execute o setup novamente")
    
    def create_requirements_file(self):
        """Cria arquivo requirements.txt"""
        print("📦 Criando arquivo requirements.txt...")
        
        requirements = [
            "streamlit>=1.25.0",
            "pandas>=1.5.0",
            "sqlite3",  # Parte da stdlib do Python
            "schedule>=1.2.0",
            "opencv-python>=4.8.0",
            "numpy>=1.24.0",
            "pillow>=10.0.0",
            "plotly>=5.15.0",
            "openpyxl>=3.1.0",
            "pytesseract>=0.3.10",  # Opcional para OCR
            "requests>=2.31.0",
            "python-dateutil>=2.8.0",
            "psutil>=5.9.0",  # Para monitoramento do sistema
        ]
        
        with open(self.requirements_file, 'w') as f:
            for req in requirements:
                f.write(f"{req}\n")
        
        print(f"✅ Arquivo criado: {self.requirements_file}")
    
    def install_dependencies(self) -> bool:
        """Instala dependências Python"""
        print("📦 Instalando dependências Python...")
        
        try:
            # Atualizar pip primeiro
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         check=True)
            
            # Instalar dependências
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(self.requirements_file)], 
                         check=True)
            
            print("✅ Dependências instaladas com sucesso")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao instalar dependências: {e}")
            return False
    
    def create_directory_structure(self):
        """Cria estrutura de diretórios"""
        print("📁 Criando estrutura de diretórios...")
        
        directories = [
            self.templates_dir,
            self.logs_dir,
            self.exports_dir,
            self.project_root / "screenshots",
            self.project_root / "data",
            self.project_root / "configs"
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True)
            print(f"   📁 {directory}")
        
        print("✅ Estrutura de diretórios criada")
    
    def create_config_file(self):
        """Cria arquivo de configuração"""
        print("⚙️ Criando arquivo de configuração...")
        
        config = {
            "bot_settings": {
                "follow_interval_minutes": 5,
                "follows_per_batch": 5,
                "follow_back_check_hours": 24,
                "max_daily_follows": 100,
                "max_daily_unfollows": 50,
                "min_delay_seconds": 30,
                "max_delay_seconds": 120
            },
            "device_settings": {
                "device_id": "",
                "instagram_package": "com.instagram.android",
                "screen_timeout": 30
            },
            "safety_settings": {
                "enable_human_simulation": True,
                "random_delays": True,
                "coordinate_variance": 5,
                "max_actions_per_hour": 20
            },
            "logging": {
                "level": "INFO",
                "max_log_files": 10,
                "max_log_size_mb": 50
            },
            "database": {
                "path": "instagram_automation.db",
                "backup_interval_hours": 24
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"✅ Arquivo criado: {self.config_file}")
    
    def create_template_images(self):
        """Cria templates de exemplo para detecção de botões"""
        print("🖼️ Criando templates de exemplo...")
        
        template_info = {
            "follow_button.png": "Botão 'Seguir' do Instagram",
            "following_button.png": "Botão 'Seguindo' do Instagram", 
            "search_icon.png": "Ícone de busca",
            "home_icon.png": "Ícone da tela inicial",
            "profile_icon.png": "Ícone do perfil"
        }
        
        readme_content = """# Templates para Detecção de Botões

Esta pasta deve conter screenshots dos botões do Instagram para detecção automática.

## Como criar templates:

1. Abra o Instagram no seu dispositivo
2. Navegue até o botão desejado
3. Tire um screenshot
4. Recorte apenas o botão (deve ter fundo transparente se possível)
5. Salve como PNG nesta pasta

## Templates necessários:

"""
        
        for template, description in template_info.items():
            readme_content += f"- `{template}`: {description}\n"
        
        readme_content += """
## Dicas:

- Use resolução do seu dispositivo
- Botões devem estar bem definidos
- Evite incluir texto que pode mudar
- Teste diferentes estados (claro/escuro)
"""
        
        with open(self.templates_dir / "README.md", 'w') as f:
            f.write(readme_content)
        
        print(f"✅ README criado em: {self.templates_dir}")
    
    def create_startup_scripts(self):
        """Cria scripts de inicialização"""
        print("🚀 Criando scripts de inicialização...")
        
        # Script para Windows
        if self.os_type == "windows":
            bat_content = """@echo off
echo Starting Instagram Bot...
python scheduler_system.py --mode cli
pause
"""
            with open(self.project_root / "start_bot.bat", 'w') as f:
                f.write(bat_content)
        
        # Script para Unix (Linux/macOS)
        sh_content = """#!/bin/bash
echo "Starting Instagram Bot..."
python3 scheduler_system.py --mode cli
"""
        with open(self.project_root / "start_bot.sh", 'w') as f:
            f.write(sh_content)
        
        # Tornar executável no Unix
        if self.os_type in ["linux", "darwin"]:
            os.chmod(self.project_root / "start_bot.sh", 0o755)
        
        print("✅ Scripts de inicialização criados")
    
    def create_example_files(self):
        """Cria arquivos de exemplo"""
        print("📄 Criando arquivos de exemplo...")
        
        # Exemplo de Excel
        example_excel_content = """# Exemplo de estrutura do arquivo Excel

O arquivo Excel deve ter:
- Nome da planilha: 'contacts'
- Colunas obrigatórias:
  - Username: nome de usuário no Instagram (sem @)
  - Profile link: link do perfil completo

Exemplo:
| Username | Profile link |
|----------|-------------|
| joaosilva | https://instagram.com/joaosilva |
| mariasantos | https://instagram.com/mariasantos |
"""
        
        with open(self.project_root / "exemplo_excel.md", 'w') as f:
            f.write(example_excel_content)
        
        print("✅ Arquivos de exemplo criados")
    
    def check_android_device(self) -> bool:
        """Verifica se há dispositivo Android conectado"""
        print("📱 Verificando dispositivos Android...")
        
        try:
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = [line for line in lines[1:] if line.strip() and 'device' in line]
                
                if devices:
                    print(f"✅ {len(devices)} dispositivo(s) encontrado(s):")
                    for device in devices:
                        device_id = device.split('\t')[0]
                        print(f"   📱 {device_id}")
                    return True
                else:
                    print("⚠️ Nenhum dispositivo encontrado")
                    self.show_device_connection_instructions()
                    return False
            else:
                print("❌ Erro ao listar dispositivos")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Não foi possível verificar dispositivos")
            return False
    
    def show_device_connection_instructions(self):
        """Mostra instruções para conectar dispositivo"""
        print("\n📋 INSTRUÇÕES PARA CONECTAR DISPOSITIVO:")
        print("-" * 45)
        print("1. Ative 'Opções do desenvolvedor' no Android:")
        print("   - Vá em Configurações > Sobre o telefone")
        print("   - Toque 7 vezes em 'Número da versão'")
        print("2. Ative 'Depuração USB' em Opções do desenvolvedor")
        print("3. Conecte o dispositivo via USB")
        print("4. Aceite a autorização de depuração USB")
        print("5. Execute 'adb devices' para verificar")
        print("\n📝 Para usar emulador:")
        print("1. Instale Android Studio ou Bluestacks")
        print("2. Inicie um emulador Android")
        print("3. O emulador deve aparecer automaticamente")
    
    def test_instagram_access(self) -> bool:
        """Testa acesso ao Instagram"""
        print("📱 Testando acesso ao Instagram...")
        
        try:
            # Verificar se Instagram está instalado
            result = subprocess.run([
                'adb', 'shell', 'pm', 'list', 'packages', 'com.instagram.android'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'com.instagram.android' in result.stdout:
                print("✅ Instagram encontrado no dispositivo")
                
                # Tentar iniciar Instagram
                result = subprocess.run([
                    'adb', 'shell', 'am', 'start', '-n', 
                    'com.instagram.android/com.instagram.android.activity.MainTabActivity'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print("✅ Instagram iniciado com sucesso")
                    return True
                else:
                    print("⚠️ Não foi possível iniciar o Instagram")
                    return False
            else:
                print("❌ Instagram não está instalado no dispositivo")
                print("   Instale o Instagram e faça login antes de continuar")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("❌ Erro ao testar acesso ao Instagram")
            return False
    
    def run_setup(self) -> bool:
        """Executa setup completo"""
        self.print_header()
        
        # Lista de verificações
        checks = [
            ("Versão do Python", self.check_python_version),
            ("Instalação do ADB", self.check_adb_installation),
        ]
        
        # Executar verificações obrigatórias
        for check_name, check_func in checks:
            if not check_func():
                print(f"\