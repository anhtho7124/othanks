from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

DATABASE = 'database.db'

def init_db():
    """Khởi tạo database"""
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Bảng từ vựng
        c.execute('''CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY,
            chinese TEXT NOT NULL,
            pinyin TEXT NOT NULL,
            english TEXT NOT NULL,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            last_reviewed TEXT
        )''')
        
        # Bảng bài tập
        c.execute('''CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY,
            vocab_id INTEGER,
            type TEXT,
            completed BOOLEAN DEFAULT 0,
            date_completed TEXT,
            FOREIGN KEY(vocab_id) REFERENCES vocabulary(id)
        )''')
        
        # Thêm dữ liệu mẫu
        sample_vocab = [
            ('你好', 'nǐ hǎo', 'Hello'),
            ('谢谢', 'xièxiè', 'Thank you'),
            ('对不起', 'duìbùqǐ', 'Sorry'),
            ('再见', 'zàijiàn', 'Goodbye'),
            ('中文', 'zhōngwén', 'Chinese language'),
            ('学习', 'xuéxí', 'To study'),
            ('朋友', 'péngyou', 'Friend'),
            ('家', 'jiā', 'Home'),
        ]
        
        c.executemany('INSERT INTO vocabulary (chinese, pinyin, english) VALUES (?, ?, ?)', 
                     sample_vocab)
        
        conn.commit()
        conn.close()

def get_db():
    """Kết nối database"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/flashcard')
def flashcard():
    """Trang flashcard"""
    return render_template('flashcard.html')

@app.route('/practice')
def practice():
    """Trang bài tập"""
    return render_template('practice.html')

@app.route('/progress')
def progress():
    """Trang theo dõi tiến độ"""
    return render_template('progress.html')

# ========== API ENDPOINTS ==========

@app.route('/api/vocabulary', methods=['GET'])
def get_vocabulary():
    """Lấy tất cả từ vựng"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM vocabulary ORDER BY id')
    vocabs = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(vocabs)

@app.route('/api/vocabulary/<int:vocab_id>', methods=['PUT'])
def update_vocabulary(vocab_id):
    """Cập nhật từ vựng (đánh dấu đúng/sai)"""
    data = request.json
    is_correct = data.get('correct', False)
    
    conn = get_db()
    c = conn.cursor()
    
    if is_correct:
        c.execute('UPDATE vocabulary SET correct_count = correct_count + 1 WHERE id = ?', (vocab_id,))
    else:
        c.execute('UPDATE vocabulary SET wrong_count = wrong_count + 1 WHERE id = ?', (vocab_id,))
    
    c.execute('UPDATE vocabulary SET last_reviewed = ? WHERE id = ?', 
             (datetime.now().isoformat(), vocab_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/exercises', methods=['POST'])
def log_exercise():
    """Ghi nhận bài tập đã hoàn thành"""
    data = request.json
    vocab_id = data.get('vocab_id')
    exercise_type = data.get('type')  # 'recognition', 'writing', 'matching', 'speaking'
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO exercises (vocab_id, type, completed, date_completed) 
                VALUES (?, ?, 1, ?)''',
             (vocab_id, exercise_type, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Lấy thống kê học tập"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as total FROM vocabulary')
    total_vocab = c.fetchone()['total']
    
    c.execute('SELECT COUNT(*) as learned FROM vocabulary WHERE correct_count >= 3')
    learned = c.fetchone()['learned']
    
    c.execute('SELECT COUNT(*) as total_exercises FROM exercises WHERE completed = 1')
    total_exercises = c.fetchone()['total_exercises']
    
    c.execute('''SELECT COUNT(*) as today_exercises FROM exercises 
                WHERE completed = 1 AND date_completed LIKE ?''',
             (datetime.now().strftime('%Y-%m-%d') + '%',))
    today_exercises = c.fetchone()['today_exercises']
    
    conn.close()
    
    return jsonify({
        'total_vocabulary': total_vocab,
        'learned': learned,
        'learning': total_vocab - learned,
        'total_exercises': total_exercises,
        'today_exercises': today_exercises,
        'progress_percentage': round((learned / total_vocab * 100) if total_vocab > 0 else 0, 1)
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
