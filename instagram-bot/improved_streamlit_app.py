import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Any

# Importar nossa classe de banco melhorada
from improved_db_schema import InstagramDatabase

# Configuração da página
st.set_page_config(
    page_title="Instagram Automation Dashboard",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar banco de dados
@st.cache_resource
def init_database():
    return InstagramDatabase()

db = init_database()

# Função para carregar dados do Excel
def load_excel_data(uploaded_file):
    """Carrega e processa dados do arquivo Excel"""
    try:
        df = pd.read_excel(uploaded_file, sheet_name='contacts')
        
        # Verificar se as colunas necessárias existem
        required_columns = ['Username', 'Profile link']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Colunas obrigatórias não encontradas: {missing_columns}")
            return None
        
        # Limpar dados
        df = df.dropna(subset=required_columns)
        df['Username'] = df['Username'].str.strip()
        df['Profile link'] = df['Profile link'].str.strip()
        
        return df[required_columns]
    
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {str(e)}")
        return None

# Função para importar dados para o banco
def import_to_database(df):
    """Importa dados do DataFrame para o banco"""
    success_count = 0
    error_count = 0
    errors = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for index, row in df.iterrows():
        try:
            follower_id = db.add_follower(
                username=row['Username'],
                profile_link=row['Profile link']
            )
            
            if follower_id:
                success_count += 1
            else:
                error_count += 1
                errors.append(f"Erro ao adicionar {row['Username']}")
                
        except Exception as e:
            error_count += 1
            errors.append(f"Erro ao processar {row['Username']}: {str(e)}")
        
        # Atualizar barra de progresso
        progress = (index + 1) / len(df)
        progress_bar.progress(progress)
        status_text.text(f"Processando: {index + 1}/{len(df)} ({success_count} sucessos, {error_count} erros)")
    
    progress_bar.empty()
    status_text.empty()
    
    return success_count, error_count, errors

# Função para obter estatísticas
def get_dashboard_stats():
    """Retorna estatísticas para o dashboard"""
    stats = db.get_statistics()
    
    # Adicionar mais estatísticas personalizadas
    conn = db.db_path
    import sqlite3
    conn = sqlite3.connect(conn)
    cursor = conn.cursor()
    
    # Ações pendentes
    cursor.execute('''
        SELECT COUNT(*) FROM actions 
        WHERE status = 'pending'
    ''')
    stats['pending_actions'] = cursor.fetchone()[0]
    
    # Próximas verificações de follow-back
    cursor.execute('''
        SELECT COUNT(*) FROM follow_backs 
        WHERE check_scheduled_for <= datetime('now', '+1 hour')
        AND followed_back IS NULL
    ''')
    stats['upcoming_checks'] = cursor.fetchone()[0]
    
    conn.close()
    return stats

# Sidebar - Navegação
with st.sidebar:
    st.title("🤖 Instagram Bot")
    st.markdown("---")
    
    page = st.selectbox(
        "Navegação",
        ["Dashboard", "Importar Dados", "Gerenciar Seguidores", "Configurações", "Logs"]
    )
    
    st.markdown("---")
    
    # Status do sistema
    st.subheader("Status do Sistema")
    
    # Verificar se há ações pendentes
    stats = get_dashboard_stats()
    
    if stats['pending_actions'] > 0:
        st.warning(f"⏳ {stats['pending_actions']} ações pendentes")
    else:
        st.success("✅ Todas as ações processadas")
    
    if stats['upcoming_checks'] > 0:
        st.info(f"🔍 {stats['upcoming_checks']} verificações agendadas")

# Página principal baseada na seleção
if page == "Dashboard":
    st.title("📊 Dashboard de Automação")
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total de Seguidores",
            stats['total_followers'],
            help="Total de seguidores importados"
        )
    
    with col2:
        st.metric(
            "Follows Hoje",
            stats['follows_today'],
            help="Número de follows realizados hoje"
        )
    
    with col3:
        st.metric(
            "Unfollows Hoje",
            stats['unfollows_today'],
            help="Número de unfollows realizados hoje"
        )
    
    with col4:
        st.metric(
            "Taxa de Follow-back",
            f"{stats['follow_back_rate']:.1f}%",
            help="Porcentagem de pessoas que seguiram de volta"
        )
    
    # Gráficos
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Atividade Diária")
        
        # Simular dados de atividade (em produção, viria do banco)
        days = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='D')
        activity_data = pd.DataFrame({
            'Data': days,
            'Follows': [12, 15, 8, 20, 18, 25, stats['follows_today']],
            'Unfollows': [2, 5, 3, 8, 7, 12, stats['unfollows_today']]
        })
        
        fig = px.line(activity_data, x='Data', y=['Follows', 'Unfollows'], 
                     title="Atividade dos Últimos 7 Dias")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Status das Ações")
        
        # Dados do status das ações
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM actions
            GROUP BY status
        ''')
        
        status_data = cursor.fetchall()
        conn.close()
        
        if status_data:
            status_df = pd.DataFrame(status_data, columns=['Status', 'Count'])
            fig = px.pie(status_df, values='Count', names='Status', 
                        title="Distribuição de Status das Ações")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhuma ação registrada ainda")

elif page == "Importar Dados":
    st.title("📂 Importar Dados de Seguidores")
    
    st.markdown("""
    **Instruções:**
    1. Faça upload de um arquivo Excel (.xlsx)
    2. Certifique-se de que o arquivo tenha uma planilha chamada 'contacts'
    3. As colunas obrigatórias são: 'Username' e 'Profile link'
    """)
    
    uploaded_file = st.file_uploader(
        "Escolha um arquivo Excel",
        type=['xlsx'],
        help="Arquivo deve conter planilha 'contacts' com colunas 'Username' e 'Profile link'"
    )
    
    if uploaded_file is not None:
        df = load_excel_data(uploaded_file)
        
        if df is not None:
            st.success(f"✅ Arquivo carregado com sucesso! {len(df)} registros encontrados.")
            
            # Prévia dos dados
            st.subheader("Prévia dos Dados")
            st.dataframe(df.head(10))
            
            # Botão para importar
            if st.button("🚀 Importar para o Banco de Dados", type="primary"):
                with st.spinner("Importando dados..."):
                    success_count, error_count, errors = import_to_database(df)
                
                if success_count > 0:
                    st.success(f"✅ {success_count} registros importados com sucesso!")
                
                if error_count > 0:
                    st.error(f"❌ {error_count} registros com erro:")
                    for error in errors[:10]:  # Mostrar apenas os primeiros 10 erros
                        st.text(error)
                
                # Recarregar a página para atualizar estatísticas
                st.rerun()

elif page == "Gerenciar Seguidores":
    st.title("👥 Gerenciar Seguidores")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_status = st.selectbox(
            "Status",
            ["Todos", "Não seguidos", "Seguidos", "Follow-back confirmado"]
        )
    
    with col2:
        search_username = st.text_input("Buscar por Username")
    
    with col3:
        limit = st.number_input("Limite de registros", min_value=10, max_value=1000, value=50)
    
    # Buscar dados
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    
    query = '''
        SELECT 
            f.id, f.username, f.profile_link, f.created_at,
            CASE 
                WHEN fb.followed_back = 1 THEN 'Follow-back confirmado'
                WHEN a.status = 'completed' AND a.action_type = 'follow' THEN 'Seguido'
                WHEN a.status = 'pending' AND a.action_type = 'follow' THEN 'Pendente'
                ELSE 'Não seguido'
            END as status
        FROM followers f
        LEFT JOIN actions a ON f.id = a.follower_id AND a.action_type = 'follow'
        LEFT JOIN follow_backs fb ON f.id = fb.follower_id
        WHERE 1=1
    '''
    
    params = []
    
    if search_username:
        query += " AND f.username LIKE ?"
        params.append(f"%{search_username}%")
    
    if filter_status != "Todos":
        if filter_status == "Não seguidos":
            query += " AND a.id IS NULL"
        elif filter_status == "Seguidos":
            query += " AND a.status = 'completed' AND a.action_type = 'follow'"
        elif filter_status == "Follow-back confirmado":
            query += " AND fb.followed_back = 1"
    
    query += f" ORDER BY f.created_at DESC LIMIT {limit}"
    
    df_followers = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not df_followers.empty:
        st.dataframe(
            df_followers,
            use_container_width=True,
            column_config={
                "profile_link": st.column_config.LinkColumn("Profile Link"),
                "created_at": st.column_config.DatetimeColumn("Data de Criação"),
                "status": st.column_config.TextColumn("Status")
            }
        )
    else:
        st.info("Nenhum seguidor encontrado com os filtros aplicados.")

elif page == "Configurações":
    st.title("⚙️ Configurações")
    
    # Buscar configurações atuais
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT key, value, description FROM settings ORDER BY key')
    settings_data = cursor.fetchall()
    conn.close()
    
    st.subheader("Configurações de Automação")
    
    # Formulário para editar configurações
    with st.form("settings_form"):
        updated_settings = {}
        
        for key, value, description in settings_data:
            if key in ['follow_interval_minutes', 'follows_per_batch', 'follow_back_check_hours', 
                      'max_daily_follows', 'max_daily_unfollows', 'min_delay_seconds', 'max_delay_seconds']:
                updated_settings[key] = st.number_input(
                    description,
                    value=int(value) if value.isdigit() else 0,
                    min_value=0,
                    help=f"Chave: {key}"
                )
            else:
                updated_settings[key] = st.text_input(
                    description,
                    value=value,
                    help=f"Chave: {key}"
                )
        
        if st.form_submit_button("💾 Salvar Configurações", type="primary"):
            for key, value in updated_settings.items():
                db.update_setting(key, str(value))
            st.success("✅ Configurações salvas com sucesso!")
            st.rerun()

elif page == "Logs":
    st.title("📋 Logs do Sistema")
    
    # Filtros para logs
    col1, col2 = st.columns(2)
    
    with col1:
        log_level = st.selectbox(
            "Nível de Log",
            ["Todos", "DEBUG", "INFO", "WARNING", "ERROR"]
        )
    
    with col2:
        log_limit = st.number_input("Limite de registros", min_value=10, max_value=1000, value=100)
    
    # Buscar logs
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    
    if log_level != "Todos":
        query += " AND level = ?"
        params.append(log_level)
    
    query += f" ORDER BY timestamp DESC LIMIT {log_limit}"
    
    df_logs = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not df_logs.empty:
        # Colorir logs por nível
        def color_level(level):
            colors = {
                'DEBUG': 'gray',
                'INFO': 'blue',
                'WARNING': 'orange',
                'ERROR': 'red'
            }
            return f"color: {colors.get(level, 'black')}"
        
        st.dataframe(
            df_logs.style.applymap(color_level, subset=['level']),
            use_container_width=True,
            column_config={
                "timestamp": st.column_config.DatetimeColumn("Data/Hora"),
                "level": st.column_config.TextColumn("Nível"),
                "message": st.column_config.TextColumn("Mensagem"),
                "module": st.column_config.TextColumn("Módulo")
            }
        )
    else:
        st.info("Nenhum log encontrado.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    🤖 Instagram Automation Bot - Desenvolvido com Streamlit
    </div>
    """,
    unsafe_allow_html=True
)