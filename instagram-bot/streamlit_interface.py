#!/usr/bin/env python3
"""
Interface Streamlit Simples para Instagram Bot
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import time
import threading
import os

# Configurar página
st.set_page_config(
    page_title="Instagram Bot Simples",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado para deixar mais bonito
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .success-msg {
        background: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    .error-msg {
        background: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# Importar nossa classe do bot
try:
    from simple_instagram_bot import SimpleDatabase, SimpleBot
except ImportError:
    st.error("❌ Arquivo simple_instagram_bot.py não encontrado!")
    st.stop()

# Inicializar database
@st.cache_resource
def init_database():
    return SimpleDatabase()

@st.cache_resource
def init_bot():
    return SimpleBot()

db = init_database()
bot = init_bot()

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🤖 Instagram Bot Simples</h1>
    <p>Segue usuários e faz unfollow automático após 24h</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Controles
with st.sidebar:
    st.header("🎮 Controles")
    
    # Status do sistema
    st.subheader("📊 Status")
    stats = db.get_stats()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total", stats['total'])
        st.metric("Follows Hoje", stats['followed_today'])
    with col2:
        st.metric("Unfollows Hoje", stats['unfollowed_today'])
        st.metric("Follow-backs", stats['follow_backs'])
    
    # Taxa de follow-back
    if stats['followed_today'] > 0:
        rate = (stats['follow_backs'] / stats['followed_today']) * 100
        st.metric("Taxa Follow-back", f"{rate:.1f}%")
    
    st.markdown("---")
    
    # Configurações rápidas
    st.subheader("⚙️ Configurações")
    max_follows = st.slider("Máximo por sessão", 1, 20, 10)
    delay_min = st.slider("Delay mínimo (s)", 10, 60, 30)
    delay_max = st.slider("Delay máximo (s)", 30, 120, 60)
    
    # Atualizar configurações do bot
    bot.max_follows_per_session = max_follows
    bot.delay_between_actions = (delay_min, delay_max)

# Conteúdo principal - Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📂 Importar", "🚀 Executar", "📊 Dados", "📱 Monitoramento"])

# Tab 1 - Importar Dados
with tab1:
    st.header("📂 Importar Usuários")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Upload de arquivo
        uploaded_file = st.file_uploader(
            "Escolha um arquivo",
            type=['txt', 'csv', 'xlsx'],
            help="Formatos aceitos: TXT (um username por linha), CSV, Excel"
        )
        
        if uploaded_file is not None:
            try:
                # Determinar tipo de arquivo
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                if file_extension == 'txt':
                    # Arquivo de texto
                    content = str(uploaded_file.read(), "utf-8")
                    usernames = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                
                elif file_extension == 'csv':
                    # Arquivo CSV
                    df = pd.read_csv(uploaded_file)
                    # Tentar encontrar coluna com usernames
                    username_cols = ['username', 'user', 'Username', 'User', 'handle']
                    username_col = None
                    for col in username_cols:
                        if col in df.columns:
                            username_col = col
                            break
                    
                    if username_col:
                        usernames = df[username_col].dropna().astype(str).tolist()
                    else:
                        st.error("❌ Coluna de username não encontrada. Colunas disponíveis: " + ", ".join(df.columns))
                        usernames = []
                
                elif file_extension == 'xlsx':
                    # Arquivo Excel
                    df = pd.read_excel(uploaded_file)
                    # Mesma lógica do CSV
                    username_cols = ['username', 'user', 'Username', 'User', 'handle']
                    username_col = None
                    for col in username_cols:
                        if col in df.columns:
                            username_col = col
                            break
                    
                    if username_col:
                        usernames = df[username_col].dropna().astype(str).tolist()
                    else:
                        st.error("❌ Coluna de username não encontrada. Colunas disponíveis: " + ", ".join(df.columns))
                        usernames = []
                
                # Mostrar preview
                if usernames:
                    st.success(f"✅ {len(usernames)} usuários encontrados")
                    
                    # Preview dos primeiros 10
                    st.subheader("👀 Preview")
                    preview_df = pd.DataFrame(usernames[:10], columns=['Username'])
                    st.dataframe(preview_df, use_container_width=True)
                    
                    if len(usernames) > 10:
                        st.info(f"... e mais {len(usernames) - 10} usuários")
                    
                    # Botão para importar
                    if st.button("📥 Importar para Banco", type="primary"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        imported = 0
                        for i, username in enumerate(usernames):
                            if db.add_follower(username.strip()):
                                imported += 1
                            
                            # Atualizar progresso
                            progress = (i + 1) / len(usernames)
                            progress_bar.progress(progress)
                            status_text.text(f"Importando: {i + 1}/{len(usernames)} ({imported} novos)")
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.success(f"🎉 Importação concluída! {imported} usuários adicionados")
                        time.sleep(2)
                        st.rerun()
                
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")
    
    with col2:
        st.subheader("✍️ Adicionar Manual")
        
        # Campo para adicionar username individual
        new_username = st.text_input("Username", placeholder="usuario_exemplo")
        
        if st.button("➕ Adicionar"):
            if new_username.strip():
                if db.add_follower(new_username.strip()):
                    st.success(f"✅ Adicionado: {new_username}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("⚠️ Usuário já existe ou erro")
            else:
                st.error("❌ Digite um username")
        
        st.markdown("---")
        
        # Adicionar múltiplos
        st.subheader("📝 Lista Manual")
        manual_list = st.text_area(
            "Usernames (um por linha)",
            placeholder="usuario1\nusuario2\nusuario3",
            height=150
        )
        
        if st.button("📥 Adicionar Lista"):
            if manual_list.strip():
                usernames = [line.strip() for line in manual_list.split('\n') if line.strip()]
                imported = 0
                for username in usernames:
                    if db.add_follower(username):
                        imported += 1
                
                st.success(f"✅ {imported} usuários adicionados")
                time.sleep(1)
                st.rerun()

# Tab 2 - Executar Bot
with tab2:
    st.header("🚀 Executar Bot")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➕ Sessão de Follows")
        
        # Verificar quantos usuários há para seguir
        users_to_follow = db.get_users_to_follow(50)  # Verificar até 50
        
        if users_to_follow:
            st.info(f"📋 {len(users_to_follow)} usuários na fila para seguir")
            
            # Preview de quem será seguido
            if len(users_to_follow) > 0:
                preview_count = min(5, len(users_to_follow))
                st.write("**Próximos a serem seguidos:**")
                for i, username in enumerate(users_to_follow[:preview_count]):
                    st.write(f"{i+1}. {username}")
                if len(users_to_follow) > preview_count:
                    st.write(f"... e mais {len(users_to_follow) - preview_count}")
            
            # Botão para executar
            if st.button("🚀 Iniciar Sessão de Follows", type="primary"):
                with st.spinner("Executando sessão de follows..."):
                    # Aqui chamaria bot.run_follow_session() em uma thread
                    # Por simplicidade, vamos simular
                    st.info("⚡ Executando... (Esta é uma versão de demonstração)")
                    time.sleep(3)  # Simular execução
                    st.success("✅ Sessão de follows concluída!")
                    time.sleep(2)
                    st.rerun()
        else:
            st.warning("⚠️ Nenhum usuário na fila para seguir")
            st.info("💡 Importe usuários na aba 'Importar' primeiro")
    
    with col2:
        st.subheader("➖ Sessão de Unfollows")
        
        # Verificar quantos usuários há para unfollow
        users_to_unfollow = db.get_users_to_check_unfollow()
        
        if users_to_unfollow:
            st.info(f"🔍 {len(users_to_unfollow)} usuários para verificar (24h)")
            
            # Preview
            if len(users_to_unfollow) > 0:
                preview_count = min(5, len(users_to_unfollow))
                st.write("**Para verificar follow-back:**")
                for i, username in enumerate(users_to_unfollow[:preview_count]):
                    st.write(f"{i+1}. {username}")
                if len(users_to_unfollow) > preview_count:
                    st.write(f"... e mais {len(users_to_unfollow) - preview_count}")
            
            # Botão para executar
            if st.button("🔍 Iniciar Verificação + Unfollow", type="secondary"):
                with st.spinner("Verificando follow-backs e fazendo unfollows..."):
                    st.info("⚡ Executando... (Esta é uma versão de demonstração)")
                    time.sleep(3)  # Simular execução
                    st.success("✅ Sessão de unfollow concluída!")
                    time.sleep(2)
                    st.rerun()
        else:
            st.warning("⚠️ Nenhum usuário para verificar ainda")
            st.info("💡 Usuários aparecem aqui 24h após serem seguidos")

# Tab 3 - Visualizar Dados
with tab3:
    st.header("📊 Dados dos Usuários")
    
    # Carregar dados do banco
    conn = sqlite3.connect(db.db_path)
    
    # Query principal
    df = pd.read_sql_query('''
        SELECT 
            username,
            followed_at,
            check_unfollow_at,
            unfollowed_at,
            follows_back,
            CASE 
                WHEN unfollowed_at IS NOT NULL THEN 'Unfollowed'
                WHEN follows_back = 1 THEN 'Segue de volta'
                WHEN follows_back = 0 THEN 'Não segue'
                WHEN followed_at IS NOT NULL THEN 'Seguido'
                ELSE 'Na fila'
            END as status
        FROM followers
        ORDER BY 
            CASE 
                WHEN followed_at IS NULL THEN 0
                ELSE 1
            END,
            followed_at DESC
    ''', conn)
    
    conn.close()
    
    if not df.empty:
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Filtrar por Status",
                ['Todos'] + list(df['status'].unique())
            )
        
        with col2:
            search_user = st.text_input("Buscar Username")
        
        with col3:
            limit = st.number_input("Limite de registros", 10, 1000, 100)
        
        # Aplicar filtros
        filtered_df = df.copy()
        
        if status_filter != 'Todos':
            filtered_df = filtered_df[filtered_df['status'] == status_filter]
        
        if search_user:
            filtered_df = filtered_df[filtered_df['username'].str.contains(search_user, case=False, na=False)]
        
        filtered_df = filtered_df.head(limit)
        
        # Mostrar tabela
        st.subheader(f"📋 Usuários ({len(filtered_df)} registros)")
        
        # Configurar exibição das colunas
        column_config = {
            "username": st.column_config.TextColumn("Username", width="medium"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "followed_at": st.column_config.DatetimeColumn("Seguido em", width="medium"),
            "follows_back": st.column_config.CheckboxColumn("Segue de volta?"),
            "unfollowed_at": st.column_config.DatetimeColumn("Unfollowed em", width="medium")
        }
        
        st.dataframe(
            filtered_df[['username', 'status', 'followed_at', 'follows_back', 'unfollowed_at']],
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico simples de status
        if len(filtered_df) > 0:
            st.subheader("📈 Distribuição por Status")
            status_counts = filtered_df['status'].value_counts()
            st.bar_chart(status_counts)
    
    else:
        st.info("📭 Nenhum usuário no banco ainda")

# Tab 4 - Monitoramento
with tab4:
    st.header("📱 Monitoramento do Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔧 Status do ADB")
        
        if st.button("🔍 Verificar Dispositivos"):
            with st.spinner("Verificando dispositivos..."):
                import subprocess
                try:
                    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')[1:]
                        devices = [line.split('\t')[0] for line in lines if line.strip() and 'device' in line]
                        
                        if devices:
                            st.success(f"✅ {len(devices)} dispositivo(s) conectado(s)")
                            for device in devices:
                                st.info(f"📱 {device}")
                        else:
                            st.warning("⚠️ Nenhum dispositivo conectado")
                    else:
                        st.error("❌ Erro ao executar ADB")
                except Exception as e:
                    st.error(f"❌ ADB não encontrado: {e}")
        
        st.markdown("---")
        
        st.subheader("📊 Estatísticas Detalhadas")
        
        # Estatísticas por dia
        conn = sqlite3.connect(db.db_path)
        daily_stats = pd.read_sql_query('''
            SELECT 
                DATE(followed_at) as data,
                COUNT(*) as follows
            FROM followers 
            WHERE followed_at IS NOT NULL
            GROUP BY DATE(followed_at)
            ORDER BY data DESC
            LIMIT 7
        ''', conn)
        conn.close()
        
        if not daily_stats.empty:
            st.write("**Follows por dia (últimos 7 dias):**")
            st.bar_chart(daily_stats.set_index('data')['follows'])
        else:
            st.info("📊 Nenhuma atividade registrada ainda")
    
    with col2:
        st.subheader("⚙️ Configurações do Bot")
        
        # Mostrar configurações atuais
        st.write("**Configurações Atuais:**")
        st.write(f"• Máximo por sessão: {bot.max_follows_per_session}")
        st.write(f"• Delay: {bot.delay_between_actions[0]}-{bot.delay_between_actions[1]}s")
        st.write(f"• Resolução detectada: {bot.screen_width}x{bot.screen_height}")
        
        st.markdown("---")
        
        st.subheader("🗂️ Backup/Export")
        
        if st.button("💾 Exportar Dados"):
            # Exportar para CSV
            conn = sqlite3.connect(db.db_path)
            df_export = pd.read_sql_query('SELECT * FROM followers', conn)
            conn.close()
            
            if not df_export.empty:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"instagram_bot_backup_{timestamp}.csv"
                df_export.to_csv(filename, index=False)
                
                st.success(f"✅ Dados exportados para: {filename}")
                
                # Oferecer download
                with open(filename, 'rb') as f:
                    st.download_button(
                        "📥 Download Backup",
                        f.read(),
                        filename,
                        "text/csv"
                    )
            else:
                st.warning("⚠️ Nenhum dado para exportar")
        
        if st.button("🗑️ Limpar Banco"):
            if st.button("⚠️ Confirmar Limpeza", type="secondary"):
                conn = sqlite3.connect(db.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM followers')
                conn.commit()
                conn.close()
                
                st.success("✅ Banco limpo!")
                time.sleep(2)
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 1rem;'>
    🤖 Instagram Bot Simples v1.0 | 
    Desenvolvido para automação responsável | 
    Use com moderação
</div>
""", unsafe_allow_html=True)

# Auto-refresh opcional
if st.sidebar.checkbox("🔄 Auto-refresh (30s)"):
    time.sleep(30)
    st.rerun()
