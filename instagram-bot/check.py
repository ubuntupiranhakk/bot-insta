#!/usr/bin/env python3
"""
Verificação de Setup em Tempo Real
Mostra status de tudo que precisa estar funcionando
"""

import subprocess
import json
from pathlib import Path

def check_adb_connection():
    """Verifica conexão ADB"""
    print("📱 VERIFICANDO CONEXÃO ADB")
    print("-" * 30)
    
    try:
        # Verificar ADB
        result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ ADB funcionando")
        else:
            print("❌ ADB com problemas")
            return False
        
        # Listar dispositivos
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = [line for line in lines[1:] if line.strip() and 'device' in line]
            
            if devices:
                print(f"✅ {len(devices)} dispositivo(s) conectado(s):")
                for device in devices:
                    device_id = device.split('\t')[0]
                    status = device.split('\t')[1]
                    print(f"   📱 {device_id} ({status})")
                    
                    # Verificar Instagram
                    print(f"   🔍 Verificando Instagram...")
                    insta_result = subprocess.run([
                        'adb', '-s', device_id, 'shell', 'pm', 'list', 'packages', 'com.instagram.android'
                    ], capture_output=True, text=True, timeout=5)
                    
                    if 'com.instagram.android' in insta_result.stdout:
                        print(f"   ✅ Instagram instalado")
                        
                        # Verificar se Instagram pode ser aberto
                        print(f"   🧪 Testando abertura do Instagram...")
                        open_result = subprocess.run([
                            'adb', '-s', device_id, 'shell', 'am', 'start', '-n',
                            'com.instagram.android/com.instagram.android.activity.MainTabActivity'
                        ], capture_output=True, text=True, timeout=10)
                        
                        if open_result.returncode == 0:
                            print(f"   ✅ Instagram abre corretamente")
                            
                            # Obter resolução da tela
                            screen_result = subprocess.run([
                                'adb', '-s', device_id, 'shell', 'wm', 'size'
                            ], capture_output=True, text=True, timeout=5)
                            
                            if screen_result.returncode == 0:
                                print(f"   📐 Resolução: {screen_result.stdout.strip()}")
                            
                            return True
                        else:
                            print(f"   ❌ Erro ao abrir Instagram")
                    else:
                        print(f"   ❌ Instagram não instalado")
                
                return False
            else:
                print("❌ Nenhum dispositivo conectado")
                print("\n💡 SOLUÇÃO:")
                print("1. Conecte o celular via USB")
                print("2. Ative 'Depuração USB' no celular")
                print("3. Aceite a autorização quando aparecer")
                print("4. Execute: adb devices")
                return False
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def check_templates():
    """Verifica templates necessários"""
    print("\n🖼️ VERIFICANDO TEMPLATES")
    print("-" * 25)
    
    templates_dir = Path("templates")
    if not templates_dir.exists():
        print("❌ Pasta 'templates' não existe")
        print("\n💡 CRIANDO pasta templates...")
        templates_dir.mkdir()
        print("✅ Pasta criada")
    
    required_templates = [
        "follow_button.png",
        "following_button.png", 
        "search_icon.png",
        "home_icon.png"
    ]
    
    missing_templates = []
    for template in required_templates:
        template_path = templates_dir / template
        if template_path.exists():
            print(f"✅ {template}")
        else:
            print(f"❌ {template} - FALTANDO")
            missing_templates.append(template)
    
    if missing_templates:
        print(f"\n⚠️ ATENÇÃO: {len(missing_templates)} templates faltando!")
        print("\n📋 COMO CRIAR TEMPLATES:")
        print("1. Abra o Instagram no celular")
        print("2. Navegue até encontrar cada botão")
        print("3. Tire screenshot da tela")
        print("4. Recorte APENAS o botão (use editor de imagem)")
        print("5. Salve como PNG na pasta 'templates/'")
        print("\n📝 Templates necessários:")
        for template in missing_templates:
            desc = {
                "follow_button.png": "Botão 'Seguir' azul",
                "following_button.png": "Botão 'Seguindo' (quando já segue)",
                "search_icon.png": "Ícone de lupa da busca",
                "home_icon.png": "Ícone da casa/home"
            }
            print(f"   • {template}: {desc.get(template, 'Botão do Instagram')}")
        
        return False
    else:
        print("✅ Todos os templates encontrados!")
        return True

def check_database():
    """Verifica banco de dados"""
    print("\n🗄️ VERIFICANDO BANCO DE DADOS")
    print("-" * 30)
    
    db_path = Path("instagram_automation.db")
    if db_path.exists():
        print(f"✅ Banco existe ({db_path.stat().st_size:,} bytes)")
        
        # Verificar se tem seguidores
        try:
            from improved_db_schema import InstagramDatabase
            db = InstagramDatabase()
            stats = db.get_statistics()
            
            print(f"📊 Seguidores importados: {stats['total_followers']}")
            print(f"📊 Follows hoje: {stats['follows_today']}")
            print(f"📊 Unfollows hoje: {stats['unfollows_today']}")
            
            if stats['total_followers'] > 0:
                print("✅ Dados prontos para uso!")
                return True
            else:
                print("⚠️ Nenhum seguidor importado ainda")
                print("\n💡 IMPORTE DADOS:")
                print("1. Prepare arquivo Excel com planilha 'contacts'")
                print("2. Colunas: 'Username' e 'Profile link'")
                print("3. Use a aba 'Importar Dados' no Streamlit")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao acessar banco: {e}")
            return False
    else:
        print("❌ Banco de dados não existe")
        print("\n💡 SOLUÇÃO: Execute o Streamlit primeiro para criar o banco")
        return False

def show_next_steps():
    """Mostra próximos passos"""
    print("\n🚀 PRÓXIMOS PASSOS PARA COMEÇAR:")
    print("=" * 40)
    print("1. 📱 Certifique-se que o celular está conectado via USB")
    print("2. 🖼️ Crie os templates dos botões (MUITO IMPORTANTE)")
    print("3. 📊 Importe lista de seguidores via Streamlit") 
    print("4. ⚙️ Configure limites seguros no arquivo config.json")
    print("5. 🧪 Teste com poucos usuários primeiro")
    print("6. 🤖 Inicie o bot via CLI ou Streamlit")
    
    print(f"\n⚠️ IMPORTANTE - TEMPLATES:")
    print("• SEM os templates, o bot NÃO consegue encontrar os botões")
    print("• É OBRIGATÓRIO criar os arquivos PNG dos botões")
    print("• Use a resolução do SEU dispositivo")

def main():
    print("🔍 VERIFICAÇÃO DE SETUP COMPLETA")
    print("=" * 50)
    
    adb_ok = check_adb_connection()
    templates_ok = check_templates()
    db_ok = check_database()
    
    print(f"\n📊 RESUMO:")
    print(f"📱 ADB/Dispositivo: {'✅' if adb_ok else '❌'}")
    print(f"🖼️ Templates: {'✅' if templates_ok else '❌'}")
    print(f"🗄️ Banco/Dados: {'✅' if db_ok else '❌'}")
    
    if adb_ok and templates_ok and db_ok:
        print(f"\n🎉 TUDO PRONTO! Você pode iniciar o bot!")
        print(f"\n🚀 COMANDOS PARA INICIAR:")
        print("CLI: python scheduler_system.py --mode cli")
        print("Interface: já está rodando no Streamlit")
    else:
        show_next_steps()
        print(f"\n⚠️ Corrija os itens marcados com ❌ antes de continuar")

if __name__ == "__main__":
    main()
