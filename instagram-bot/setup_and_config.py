#!/usr/bin/env python3
"""
Instagram Bot - Installation Verification
Verifica se tudo está instalado e configurado corretamente
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path
import json

class InstallationVerifier:
    """Verificador de instalação do bot"""
    
    def __init__(self):
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.BLUE = '\033[94m'
        self.ENDC = '\033[0m'
        self.BOLD = '\033[1m'
        
        self.results = {
            'python': False,
            'dependencies': {},
            'files': {},
            'adb': False,
            'devices': [],
            'instagram': False,
            'overall_score': 0
        }
    
    def print_header(self):
        """Imprime cabeçalho"""
        print("=" * 70)
        print(f"{self.BOLD}🔍 VERIFICAÇÃO DE INSTALAÇÃO - INSTAGRAM BOT{self.ENDC}")
        print("=" * 70)
        print(f"Python: {sys.version}")
        print(f"Sistema: {sys.platform}")
        print("=" * 70)
    
    def check_python_version(self):
        """Verifica versão do Python"""
        print(f"\n{self.BLUE}🐍 VERIFICANDO PYTHON{self.ENDC}")
        print("-" * 30)
        
        version = sys.version_info
        if version >= (3, 8):
            print(f"{self.GREEN}✅ Python {version.major}.{version.minor}.{version.micro} - OK{self.ENDC}")
            self.results['python'] = True
            return True
        else:
            print(f"{self.RED}❌ Python {version.major}.{version.minor}.{version.micro} - Versão muito antiga{self.ENDC}")
            print(f"   Requerido: Python 3.8+")
            return False
    
    def check_dependencies(self):
        """Verifica dependências Python"""
        print(f"\n{self.BLUE}📦 VERIFICANDO DEPENDÊNCIAS{self.ENDC}")
        print("-" * 40)
        
        # Dependências obrigatórias
        required_deps = {
            'streamlit': 'Interface web',
            'pandas': 'Manipulação de dados', 
            'numpy': 'Computação numérica',
            'schedule': 'Agendamento de tarefas',
            'requests': 'Requisições HTTP',
            'openpyxl': 'Leitura de Excel',
            'plotly': 'Gráficos interativos'
        }
        
        # Dependências de visão computacional
        cv_deps = {
            'cv2': 'OpenCV - Visão computacional',
            'PIL': 'Pillow - Processamento de imagens'
        }
        
        # Dependências opcionais
        optional_deps = {
            'pytesseract': 'OCR - Reconhecimento de texto',
            'psutil': 'Monitoramento do sistema',
            'colorlog': 'Logs coloridos'
        }
        
        all_deps = {**required_deps, **cv_deps, **optional_deps}
        installed_count = 0
        
        for module, description in all_deps.items():
            try:
                if module == 'cv2':
                    import cv2
                    version = cv2.__version__
                elif module == 'PIL':
                    from PIL import Image
                    version = Image.__version__ if hasattr(Image, '__version__') else 'N/A'
                else:
                    mod = importlib.import_module(module)
                    version = getattr(mod, '__version__', 'N/A')
                
                print(f"{self.GREEN}✅ {module:15} {version:10} - {description}{self.ENDC}")
                self.results['dependencies'][module] = True
                installed_count += 1
                
            except ImportError:
                is_optional = module in optional_deps
                color = self.YELLOW if is_optional else self.RED
                status = "⚠️ Opcional" if is_optional else "❌ Obrigatório"
                print(f"{color}{status:12} {module:15} {'':10} - {description}{self.ENDC}")
                self.results['dependencies'][module] = False
        
        success_rate = (installed_count / len(all_deps)) * 100
        print(f"\n📊 Taxa de instalação: {success_rate:.1f}% ({installed_count}/{len(all_deps)})")
        
        return success_rate >= 70  # 70% das dependências instaladas
    
    def check_project_files(self):
        """Verifica arquivos do projeto"""
        print(f"\n{self.BLUE}📁 VERIFICANDO ARQUIVOS DO PROJETO{self.ENDC}")
        print("-" * 45)
        
        required_files = {
            'improved_db_schema.py': 'Módulo de banco de dados',
            'instagram_automation.py': 'Módulo de automação',
            'scheduler_system.py': 'Sistema de agendamento', 
            'improved_streamlit_app.py': 'Interface web',
            'requirements.txt': 'Lista de dependências'
        }
        
        optional_files = {
            'setup_and_config.py': 'Script de configuração',
            'test_all_modules.py': 'Suite de testes',
            'quick_start.py': 'Script de início rápido',
            'config.json': 'Arquivo de configuração'
        }
        
        all_files = {**required_files, **optional_files}
        found_count = 0
        
        for filename, description in all_files.items():
            path = Path(filename)
            if path.exists():
                size = path.stat().st_size
                size_str = f"({size:,} bytes)"
                print(f"{self.GREEN}✅ {filename:25} {size_str:15} - {description}{self.ENDC}")
                self.results['files'][filename] = True
                found_count += 1
            else:
                is_optional = filename in optional_files
                color = self.YELLOW if is_optional else self.RED
                status = "⚠️ Opcional" if is_optional else "❌ Obrigatório"
                print(f"{color}{status:12} {filename:25} {'':15} - {description}{self.ENDC}")
                self.results['files'][filename] = False
        
        # Verificar diretórios
        print(f"\n📂 Diretórios:")
        directories = ['templates', 'logs', 'exports', 'data', 'screenshots']
        
        for dirname in directories:
            path = Path(dirname)
            if path.exists() and path.is_dir():
                file_count = len(list(path.iterdir()))
                print(f"{self.GREEN}✅ {dirname:15} ({file_count} arquivos){self.ENDC}")
            else:
                print(f"{self.YELLOW}⚠️ {dirname:15} (será criado automaticamente){self.ENDC}")
        
        success_rate = (found_count / len(all_files)) * 100
        print(f"\n📊 Arquivos encontrados: {success_rate:.1f}% ({found_count}/{len(all_files)})")
        
        return len([f for f in required_files if self.results['files'].get(f, False)]) == len(required_files)
    
    def check_adb(self):
        """Verifica ADB"""
        print(f"\n{self.BLUE}📱 VERIFICANDO ADB{self.ENDC}")
        print("-" * 25)
        
        try:
            result = subprocess.run(['adb', 'version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"{self.GREEN}✅ ADB instalado: {version_line}{self.ENDC}")
                self.results['adb'] = True
                return True
            else:
                print(f"{self.RED}❌ ADB não funciona corretamente{self.ENDC}")
                print(f"   Erro: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"{self.RED}❌ ADB timeout{self.ENDC}")
            return False
        except FileNotFoundError:
            print(f"{self.RED}❌ ADB não encontrado{self.ENDC}")
            print(f"   Instale ADB primeiro")
            return False
    
    def check_android_devices(self):
        """Verifica dispositivos Android"""
        print(f"\n{self.BLUE}📱 VERIFICANDO DISPOSITIVOS ANDROID{self.ENDC}")
        print("-" * 40)
        
        if not self.results['adb']:
            print(f"{self.YELLOW}⚠️ ADB não disponível, pulando verificação de dispositivos{self.ENDC}")
            return False
        
        try:
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                devices = []
                
                for line in lines[1:]:  # Pular cabeçalho
                    if line.strip() and '\t' in line:
                        device_id, status = line.split('\t')
                        devices.append((device_id, status))
                
                if devices:
                    print(f"{self.GREEN}✅ {len(devices)} dispositivo(s) encontrado(s):{self.ENDC}")
                    for device_id, status in devices:
                        status_color = self.GREEN if status == 'device' else self.YELLOW
                        print(f"   {status_color}📱 {device_id} ({status}){self.ENDC}")
                        self.results['devices'].append(device_id)
                    return True
                else:
                    print(f"{self.YELLOW}⚠️ Nenhum dispositivo conectado{self.ENDC}")
                    return False
            else:
                print(f"{self.RED}❌ Erro ao listar dispositivos{self.ENDC}")
                return False
                
        except Exception as e:
            print(f"{self.RED}❌ Erro na verificação: {e}{self.ENDC}")
            return False
    
    def check_instagram(self):
        """Verifica Instagram nos dispositivos"""
        print(f"\n{self.BLUE}📱 VERIFICANDO INSTAGRAM{self.ENDC}")
        print("-" * 30)
        
        if not self.results['devices']:
            print(f"{self.YELLOW}⚠️ Nenhum dispositivo para verificar{self.ENDC}")
            return False
        
        instagram_found = False
        
        for device_id in self.results['devices']:
            try:
                print(f"🔍 Verificando {device_id}...")
                
                result = subprocess.run([
                    'adb', '-s', device_id, 'shell', 'pm', 'list', 'packages', 
                    'com.instagram.android'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and 'com.instagram.android' in result.stdout:
                    print(f"{self.GREEN}   ✅ Instagram instalado{self.ENDC}")
                    
                    # Tentar obter versão
                    version_result = subprocess.run([
                        'adb', '-s', device_id, 'shell', 'dumpsys', 'package', 
                        'com.instagram.android', '|', 'grep', 'versionName'
                    ], capture_output=True, text=True, timeout=5)
                    
                    instagram_found = True
                else:
                    print(f"{self.RED}   ❌ Instagram não instalado{self.ENDC}")
                    
            except Exception as e:
                print(f"{self.YELLOW}   ⚠️ Erro na verificação: {e}{self.ENDC}")
        
        self.results['instagram'] = instagram_found
        return instagram_found
    
    def calculate_overall_score(self):
        """Calcula pontuação geral"""
        score = 0
        max_score = 100
        
        # Python (20 pontos)
        if self.results['python']:
            score += 20
        
        # Dependências (30 pontos)
        deps_installed = sum(1 for installed in self.results['dependencies'].values() if installed)
        deps_total = len(self.results['dependencies'])
        if deps_total > 0:
            score += int((deps_installed / deps_total) * 30)
        
        # Arquivos (25 pontos)
        files_found = sum(1 for found in self.results['files'].values() if found)
        files_total = len(self.results['files'])
        if files_total > 0:
            score += int((files_found / files_total) * 25)
        
        # ADB (15 pontos)
        if self.results['adb']:
            score += 15
        
        # Instagram (10 pontos)
        if self.results['instagram']:
            score += 10
        
        self.results['overall_score'] = score
        return score
    
    def print_summary(self):
        """Imprime resumo final"""
        score = self.calculate_overall_score()
        
        print(f"\n{self.BOLD}📊 RESUMO FINAL{self.ENDC}")
        print("=" * 50)
        
        # Determinar cor da pontuação
        if score >= 80:
            score_color = self.GREEN
            status = "EXCELENTE 🎉"
        elif score >= 60:
            score_color = self.YELLOW  
            status = "BOM ⚠️"
        else:
            score_color = self.RED
            status = "PRECISA MELHORAR ❌"
        
        print(f"🎯 Pontuação geral: {score_color}{score}/100 - {status}{self.ENDC}")
        
        print(f"\n📋 Detalhes:")
        print(f"   🐍 Python: {'✅' if self.results['python'] else '❌'}")
        print(f"   📦 Dependências: {sum(1 for x in self.results['dependencies'].values() if x)}/{len(self.results['dependencies'])}")
        print(f"   📁 Arquivos: {sum(1 for x in self.results['files'].values() if x)}/{len(self.results['files'])}")
        print(f"   📱 ADB: {'✅' if self.results['adb'] else '❌'}")
        print(f"   📱 Dispositivos: {len(self.results['devices'])}")
        print(f"   📱 Instagram: {'✅' if self.results['instagram'] else '❌'}")
        
        # Recomendações
        print(f"\n{self.BLUE}💡 RECOMENDAÇÕES:{self.ENDC}")
        
        if score >= 80:
            print("🎯 Tudo pronto! Você pode iniciar o bot.")
            print("   Execute: python quick_start.py")
        else:
            if not self.results['python']:
                print("🐍 Atualize o Python para versão 3.8+")
            
            missing_deps = [dep for dep, installed in self.results['dependencies'].items() if not installed]
            if missing_deps:
                print(f"📦 Instale dependências: pip install {' '.join(missing_deps)}")
            
            missing_files = [file for file, found in self.results['files'].items() if not found]
            if missing_files:
                print(f"📁 Baixe arquivos faltando: {', '.join(missing_files)}")
            
            if not self.results['adb']:
                print("📱 Instale ADB para controlar dispositivos Android")
            
            if not self.results['instagram']:
                print("📱 Instale Instagram no dispositivo Android")
        
        # Salvar relatório
        report_file = f"verification_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Relatório salvo em: {report_file}")
    
    def run_verification(self):
        """Executa verificação completa"""
        self.print_header()
        
        # Executar todas as verificações
        self.check_python_version()
        self.check_dependencies() 
        self.check_project_files()
        self.check_adb()
        self.check_android_devices()
        self.check_instagram()
        
        # Mostrar resumo
        self.print_summary()
        
        return self.results['overall_score'] >= 60

def main():
    """Função principal"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='Instagram Bot Installation Verifier')
    parser.add_argument('--json', action='store_true', 
                       help='Output em formato JSON')
    parser.add_argument('--quiet', action='store_true',
                       help='Modo silencioso')
    
    args = parser.parse_args()
    
    verifier = InstallationVerifier()
    
    if args.quiet:
        # Modo silencioso - apenas verificar e retornar código de saída
        verifier.check_python_version()
        verifier.check_dependencies()
        verifier.check_project_files()
        verifier.check_adb()
        verifier.check_android_devices() 
        verifier.check_instagram()
        
        score = verifier.calculate_overall_score()
        
        if args.json:
            print(json.dumps(verifier.results, indent=2))
        
        sys.exit(0 if score >= 60 else 1)
    
    else:
        # Modo completo
        success = verifier.run_verification()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()