# 🤖 Instagram Automation Bot

Um sistema completo de automação para Instagram que permite seguir usuários automaticamente, verificar follow-backs e gerenciar unfollows de forma inteligente e segura.

## 📋 Índice

- [Características](#-características)
- [Arquitetura](#-arquitetura)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [Módulos](#-módulos)
- [Segurança](#-segurança)
- [Troubleshooting](#-troubleshooting)
- [Contribuição](#-contribuição)

## ✨ Características

### 🎯 Automação Inteligente
- **Follow automático**: Segue usuários de uma lista importada
- **Verificação de follow-back**: Checa se usuários seguiram de volta após 24h
- **Unfollow automático**: Remove usuários que não seguiram de volta
- **Delays humanizados**: Simula comportamento humano com delays aleatórios

### 📊 Interface e Monitoramento
- **Dashboard web**: Interface Streamlit com métricas em tempo real
- **CLI interativo**: Terminal com comandos para controle manual
- **Relatórios detalhados**: Estatísticas diárias e análises de performance
- **Sistema de logs**: Monitoramento completo de todas as ações

### 🔒 Segurança e Conformidade
- **Limites configuráveis**: Controle de ações por dia/hora
- **Comportamento humano**: Coordenadas variáveis e delays aleatórios
- **Verificação de saúde**: Monitoramento automático do status do bot
- **Backup automático**: Sistema de backup do banco de dados

### 🛠️ Tecnologias
- **Python 3.8+**: Linguagem principal
- **SQLite**: Banco de dados local robusto
- **ADB**: Controle de dispositivos Android
- **OpenCV**: Detecção de elementos visuais
- **Streamlit**: Interface web moderna
- **Schedule**: Sistema de agendamento

## 🏗️ Arquitetura

```
instagram-bot/
├── 📄 improved_db_schema.py      # Sistema de banco de dados
├── 🤖 instagram_automation.py    # Módulo de automação ADB
├── ⏰ scheduler_system.py        # Sistema de agendamento
├── 🌐 improved_streamlit_app.py  # Interface web
├── ⚙️ setup_and_config.py       # Script de configuração
├── 📊 data/                      # Dados e imports
├── 🖼️ templates/                # Templates para detecção
├── 📝 logs/                      # Arquivos de log
├── 📁 exports/                   # Exports e relatórios
├── 📸 screenshots/               # Screenshots automáticos
└── ⚙️ configs/                   # Arquivos de configuração
```

### Fluxo de Funcionamento

1. **Importação**: Usuários são importados via Excel para o banco SQLite
2. **Agendamento**: Sistema agenda execução de follows a cada 5 minutos
3. **Execução**: Bot usa ADB para controlar Instagram no Android
4. **Monitoramento**: Ações são registradas e monitoradas
5. **Verificação**: Após 24h, verifica se houve follow-back
6. **Unfollow**: Remove usuários que não seguiram de volta

## 🚀 Instalação

### Pré-requisitos

- **Python 3.8+**
- **Android Debug Bridge (ADB)**
- **Dispositivo Android** (físico ou emulador)
- **Instagram** instalado e logado no dispositivo

### Instalação Automática

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/instagram-bot.git
cd instagram-bot

# 2. Execute o setup automático
python setup_and_config.py

# 3. Siga as instruções na tela
```

### Instalação Manual

```bash
# 1. Instalar dependências Python
pip install -r requirements.txt

# 2. Instalar ADB (Ubuntu/Debian)
sudo apt install android-tools-adb

# 3. Configurar dispositivo Android
adb devices  # Verificar se dispositivo está conectado
```

## ⚙️ Configuração

### 1. Dispositivo Android

```bash
# Ativar opções do desenvolvedor
# Configurações > Sobre o telefone > Tocar 7x em "Número da versão"

# Ativar depuração USB
# Configurações > Opções do desenvolvedor > Depuração USB

# Conectar e autorizar
adb devices
```

### 2. Arquivo de Configuração

Edite `config.json` para ajustar comportamento:

```json
{
  "bot_settings": {
    "follow_interval_minutes": 5,
    "follows_per_batch": 5,
    "max_daily_follows": 100,
    "min_delay_seconds": 30,
    "max_delay_seconds": 120
  },
  "safety_settings": {
    "enable_human_simulation": true,
    "coordinate_variance": 5,
    "max_actions_per_hour": 20
  }
}
```

### 3. Templates de Detecção

Adicione screenshots dos botões do Instagram em `templates/`:
- `follow_button.png` - Botão "Seguir"
- `following_button.png` - Botão "Seguindo"
- `search_icon.png` - Ícone de busca
- `home_icon.png` - Ícone home

## 🎮 Uso

### Interface Web (Recomendado para iniciantes)

```bash
streamlit run improved_streamlit_app.py
```

Acesse http://localhost:8501 para:
- 📊 Ver dashboard com estatísticas
- 📂 Importar lista de usuários
- ⚙️ Configurar parâmetros
- 📝 Monitorar logs

### CLI Interativo (Recomendado para usuários avançados)

```bash
python scheduler_system.py --mode cli
```

Comandos disponíveis:
```
bot> help           # Ver todos os comandos
bot> start          # Iniciar scheduler
bot> status         # Ver status atual
bot> stats          # Ver estatísticas
bot> run follow_batch    # Executar follows manual
bot> health         # Verificar saúde do bot
```

### Modo Daemon (Para execução contínua)

```bash
python scheduler_system.py --mode scheduler
```

### Execução Única

```bash
python scheduler_system.py --mode once --task follow_batch
```

## 📋 Preparação dos Dados

### Formato do Excel

Crie um arquivo Excel com planilha nomeada `contacts`:

| Username | Profile link |
|----------|-------------|
| joaosilva | https://instagram.com/joaosilva |
| mariasantos | https://instagram.com/mariasantos |

### Importação

1. **Via Streamlit**: Use a interface web para upload
2. **Via CLI**: Coloque o arquivo em `data/` e importe

## 🔧 Módulos Detalhados

### 🗄️ improved_db_schema.py
- **InstagramDatabase**: Classe principal do banco
- **Tabelas**: followers, actions, follow_backs, settings, logs
- **Métodos**: CRUD completo + estatísticas

### 🤖 instagram_automation.py
- **ADBController**: Controle do dispositivo Android
- **InstagramAutomation**: Automação específica do Instagram
- **InstagramBot**: Orquestrador principal
- **Recursos**: Screenshot, tap, swipe, detecção de texto

### ⏰ scheduler_system.py
- **BotScheduler**: Sistema de agendamento principal
- **ScheduledTask**: Representação de tarefas
- **BotCLI**: Interface de linha de comando
- **Agendamentos**: Follows, verificações, unfollows, relatórios

### 🌐 improved_streamlit_app.py
- **Dashboard**: Métricas e gráficos em tempo real
- **Importação**: Interface para upload de dados
- **Gerenciamento**: CRUD de seguidores
- **Configurações**: Editor de configurações
- **Logs**: Visualizador de logs

## 🔒 Segurança e Boas Práticas

### Limites Recomendados
- **Follows diários**: Máximo 100-150
- **Unfollows diários**: Máximo 50-75
- **Interval entre ações**: 30-120 segundos
- **Ações por hora**: Máximo 20

### Simulação Humana
- ✅ Delays aleatórios entre ações
- ✅ Variação nas coordenadas de toque
- ✅ Pausa em horários noturnos
- ✅ Verificação de saúde automática

### Prevenção de Banimento
- 📊 Monitoramento de taxa de erro
- ⏱️ Respeito aos limites de API
- 🔄 Reinicialização automática
- 📝 Logs detalhados para auditoria

## 🆘 Troubleshooting

### Problemas Comuns

#### ADB não encontrado
```bash
# Verificar instalação
adb version

# Reinstalar (Ubuntu)
sudo apt remove android-tools-adb
sudo apt install android-tools-adb
```

#### Dispositivo não conecta
```bash
# Verificar dispositivos
adb devices

# Reiniciar servidor ADB
adb kill-server
adb start-server
```

#### Instagram não abre
```bash
# Verificar se está instalado
adb shell pm list packages | grep instagram

# Forçar parada e reiniciar
adb shell am force-stop com.instagram.android
adb shell am start -n com.instagram.android/.activity.MainTabActivity
```

#### Bot não encontra botões
1. Verifique templates em `templates/`
2. Tire novos screenshots dos botões
3. Ajuste coordenadas no código
4. Verifique resolução do dispositivo

### Logs e Diagnóstico

```bash
# Ver logs em tempo real
tail -f logs/instagram_bot.log

# Verificar saúde via CLI
python scheduler_system.py --mode cli
bot> health

# Exportar dados para análise
bot> export
```

## 📊 Monitoramento e Relatórios

### Métricas Disponíveis
- 📈 Taxa de follow-back
- ⚡ Velocidade de execução
- ❌ Taxa de erros
- 📅 Atividade por dia/hora
- 🎯 Eficiência por batch

### Relatórios Automáticos
- **Diário**: Gerado às 23:00
- **Semanal**: Resumo de performance
- **Mensal**: Análise de tendências
- **Exportação**: CSV para análise externa

## 🛡️ Considerações Legais

⚠️ **IMPORTANTE**: Este bot é para fins educacionais e de automação pessoal.

- ✅ Use apenas em suas próprias contas
- ✅ Respeite os termos de uso do Instagram
- ✅ Não use para spam ou atividades maliciosas
- ✅ Monitore e ajuste limites conforme necessário

## 🤝 Contribuição

### Como Contribuir

1. **Fork** o repositório
2. **Crie** uma branch para sua feature
3. **Commit** suas mudanças
4. **Push** para a branch
5. **Abra** um Pull Request

### Áreas para Melhoria

- 🎯 Detecção de botões mais robusta
- 🧠 IA para análise de perfis
- 📱 Suporte a múltiplos dispositivos
- 🌐 Interface web mais avançada
- 📊 Analytics mais detalhados

## 📝 Changelog

### v2.0.0 (Atual)
- ✨ Interface Streamlit completa
- 🗄️ Banco de dados robusto
- ⏰ Sistema de agendamento avançado
- 🔒 Recursos de segurança melhorados
- 📊 Dashboard com métricas em tempo real

### v1.0.0
- 🤖 Automação básica via ADB
- 📱 Controle simples do Instagram
- 📄 Import de dados via Excel

## 🆘 Suporte

Para dúvidas, problemas ou sugestões:

- 📧 **Email**: seu-email@exemplo.com
- 🐛 **Issues**: Use o GitHub Issues
- 💬 **Discussões**: GitHub Discussions
- 📚 **Wiki**: Documentação detalhada

## 📄 Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

⭐ **Se este projeto foi útil, considere dar uma estrela no GitHub!**

🤖 **Desenvolvido com ❤️ para automação responsável**