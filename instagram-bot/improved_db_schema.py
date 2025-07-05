import sqlite3
import datetime
from typing import Optional, List, Dict, Any
import logging

class InstagramDatabase:
    def __init__(self, db_path: str = 'instagram_automation.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com todas as tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de seguidores (dados base)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS followers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                profile_link TEXT NOT NULL,
                full_name TEXT,
                bio TEXT,
                followers_count INTEGER,
                following_count INTEGER,
                posts_count INTEGER,
                is_verified BOOLEAN DEFAULT 0,
                is_private BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de ações realizadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER,
                action_type TEXT NOT NULL, -- 'follow', 'unfollow', 'like', 'comment'
                status TEXT NOT NULL, -- 'pending', 'completed', 'failed', 'skipped'
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scheduled_for TIMESTAMP,
                error_message TEXT,
                attempts INTEGER DEFAULT 0,
                FOREIGN KEY (follower_id) REFERENCES followers (id)
            )
        ''')
        
        # Tabela de follow-backs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS follow_backs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                follower_id INTEGER,
                followed_at TIMESTAMP NOT NULL,
                check_scheduled_for TIMESTAMP NOT NULL,
                followed_back BOOLEAN DEFAULT NULL,
                checked_at TIMESTAMP,
                unfollowed_at TIMESTAMP,
                FOREIGN KEY (follower_id) REFERENCES followers (id)
            )
        ''')
        
        # Tabela de configurações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL, -- 'INFO', 'WARNING', 'ERROR', 'DEBUG'
                message TEXT NOT NULL,
                module TEXT,
                function_name TEXT,
                line_number INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT -- JSON string para dados adicionais
            )
        ''')
        
        # Inserir configurações padrão
        default_settings = [
            ('follow_interval_minutes', '5', 'Intervalo entre follows em minutos'),
            ('follows_per_batch', '5', 'Número de follows por lote'),
            ('follow_back_check_hours', '24', 'Horas para verificar follow-back'),
            ('max_daily_follows', '100', 'Máximo de follows por dia'),
            ('max_daily_unfollows', '50', 'Máximo de unfollows por dia'),
            ('min_delay_seconds', '30', 'Delay mínimo entre ações em segundos'),
            ('max_delay_seconds', '120', 'Delay máximo entre ações em segundos'),
            ('instagram_username', '', 'Username do Instagram da conta'),
            ('device_id', '', 'ID do dispositivo Android')
        ]
        
        for key, value, desc in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            ''', (key, value, desc))
        
        conn.commit()
        conn.close()
    
    def add_follower(self, username: str, profile_link: str, **kwargs) -> int:
        """Adiciona um seguidor ao banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO followers 
                (username, profile_link, full_name, bio, followers_count, 
                 following_count, posts_count, is_verified, is_private, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username, profile_link, kwargs.get('full_name'),
                kwargs.get('bio'), kwargs.get('followers_count'),
                kwargs.get('following_count'), kwargs.get('posts_count'),
                kwargs.get('is_verified', 0), kwargs.get('is_private', 0),
                datetime.datetime.now()
            ))
            
            follower_id = cursor.lastrowid
            conn.commit()
            return follower_id
            
        except sqlite3.Error as e:
            logging.error(f"Erro ao adicionar seguidor {username}: {e}")
            return None
        finally:
            conn.close()
    
    def get_followers_to_follow(self, limit: int = 5) -> List[Dict]:
        """Retorna seguidores que ainda não foram seguidos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.* FROM followers f
            LEFT JOIN actions a ON f.id = a.follower_id 
                AND a.action_type = 'follow' 
                AND a.status = 'completed'
            WHERE a.id IS NULL
            ORDER BY f.created_at ASC
            LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def record_action(self, follower_id: int, action_type: str, 
                     status: str = 'pending', **kwargs) -> int:
        """Registra uma ação realizada"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO actions 
            (follower_id, action_type, status, scheduled_for, error_message, attempts)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            follower_id, action_type, status,
            kwargs.get('scheduled_for'), kwargs.get('error_message'),
            kwargs.get('attempts', 0)
        ))
        
        action_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return action_id
    
    def update_action_status(self, action_id: int, status: str, 
                           error_message: Optional[str] = None):
        """Atualiza o status de uma ação"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE actions 
            SET status = ?, error_message = ?, performed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, error_message, action_id))
        
        conn.commit()
        conn.close()
    
    def schedule_follow_back_check(self, follower_id: int, followed_at: datetime.datetime):
        """Agenda verificação de follow-back"""
        check_time = followed_at + datetime.timedelta(hours=24)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO follow_backs 
            (follower_id, followed_at, check_scheduled_for)
            VALUES (?, ?, ?)
        ''', (follower_id, followed_at, check_time))
        
        conn.commit()
        conn.close()
    
    def get_follow_backs_to_check(self) -> List[Dict]:
        """Retorna follow-backs que precisam ser verificados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fb.*, f.username, f.profile_link
            FROM follow_backs fb
            JOIN followers f ON fb.follower_id = f.id
            WHERE fb.check_scheduled_for <= CURRENT_TIMESTAMP
            AND fb.followed_back IS NULL
            ORDER BY fb.check_scheduled_for ASC
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def update_follow_back_status(self, follow_back_id: int, followed_back: bool):
        """Atualiza o status de follow-back"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE follow_backs 
            SET followed_back = ?, checked_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (followed_back, follow_back_id))
        
        conn.commit()
        conn.close()
    
    def get_setting(self, key: str) -> Optional[str]:
        """Retorna uma configuração"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    
    def update_setting(self, key: str, value: str):
        """Atualiza uma configuração"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE settings 
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE key = ?
        ''', (value, key))
        
        conn.commit()
        conn.close()
    
    def log_message(self, level: str, message: str, module: str = None, 
                   function_name: str = None, line_number: int = None, 
                   extra_data: str = None):
        """Registra uma mensagem de log"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO logs 
            (level, message, module, function_name, line_number, extra_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (level, message, module, function_name, line_number, extra_data))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total de seguidores
        cursor.execute('SELECT COUNT(*) FROM followers')
        stats['total_followers'] = cursor.fetchone()[0]
        
        # Follows realizados hoje
        cursor.execute('''
            SELECT COUNT(*) FROM actions 
            WHERE action_type = 'follow' 
            AND status = 'completed'
            AND DATE(performed_at) = DATE('now')
        ''')
        stats['follows_today'] = cursor.fetchone()[0]
        
        # Unfollows realizados hoje
        cursor.execute('''
            SELECT COUNT(*) FROM actions 
            WHERE action_type = 'unfollow' 
            AND status = 'completed'
            AND DATE(performed_at) = DATE('now')
        ''')
        stats['unfollows_today'] = cursor.fetchone()[0]
        
        # Follow-backs recebidos
        cursor.execute('''
            SELECT COUNT(*) FROM follow_backs 
            WHERE followed_back = 1
        ''')
        stats['follow_backs_received'] = cursor.fetchone()[0]
        
        # Taxa de follow-back
        cursor.execute('''
            SELECT COUNT(*) FROM follow_backs 
            WHERE followed_back IS NOT NULL
        ''')
        total_checked = cursor.fetchone()[0]
        
        if total_checked > 0:
            stats['follow_back_rate'] = (stats['follow_backs_received'] / total_checked) * 100
        else:
            stats['follow_back_rate'] = 0
        
        conn.close()
        return stats