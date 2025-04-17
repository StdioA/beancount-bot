import sqlite3
from pathlib import Path
from decimal import Decimal, InvalidOperation
import requests
from bottle import Bottle, request, static_file, response
from bots import controller
import conf
from bean_utils.bean import bean_manager
from conf.i18n import gettext as _

app = Bottle()

# Database setup
DATABASE = conf.config.bot.web.chat_db

def get_db():
    db = getattr(request, 'database', None)
    if db is None:
        db = request.database = sqlite3.connect(DATABASE)
    return db

@app.hook('before_request')
def db_connect():
    request.db = get_db()

@app.hook('after_request')
def db_close():
    if hasattr(request, 'db'):
        request.db.close()

def init_db():
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                transaction_text TEXT,
                status TINYINT default 0
            )
        ''')
        db.commit()
        try:
            cursor = db.cursor()
            cursor.execute('''
                ALTER TABLE messages ADD COLUMN favorite TINYINT default 0
            ''')
            db.commit()
        except sqlite3.OperationalError:
            pass


@app.route('/api/messages')
def list_messages():
    cursor = request.db.cursor()
    cursor.execute("SELECT id, message, transaction_text, status, favorite FROM messages ORDER BY id DESC limit 20")
    messages = []
    for (id_, message, trx, status, favorite) in reversed(cursor.fetchall()):
        messages.append({
            'id': id_,
            'message': message,
            'transaction_text': trx,
            'status': 'submitted' if status == 1 else 'pending',
            'favorite': bool(favorite),
        })

    collection_cursor = request.db.cursor()
    collection_cursor.execute("SELECT id, message, transaction_text, status, favorite FROM messages WHERE favorite = 1 ORDER BY id DESC")
    favorites = []
    for (id_, message, trx, status, favorite) in reversed(collection_cursor.fetchall()):
        favorites.append({
            'id': id_,
            'message': message,
            'transaction_text': trx,
            'status': 'submitted' if status == 1 else 'pending',
            'favorite': bool(favorite),
        })
    return {
        'messages': messages,
        'favorites': favorites,
    }


@app.route('/api/favorite', method='POST')
def collect():
    message_id = request.json.get('id')
    status = int(request.json.get('favorite'))
    if not message_id:
        response.status = 400
        return {'error': 'Message ID is required'}

    cursor = request.db.cursor()
    cursor.execute("UPDATE messages SET favorite = ? WHERE id = ?", (status, message_id))
    request.db.commit()
    return {'success': True}


@app.route('/api/delete', method='POST')
def delete_trx():
    message_id = request.json.get('id')
    if not message_id:
        response.status = 400
        return {'error': 'Message ID is required'}

    cursor = request.db.cursor()
    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id, ))
    request.db.commit()
    return {'success': True}


@app.route('/api/chat', method='POST')
def chat():
    message = request.json.get('message')
    if not message:
        response.status = 400
        return {'error': _('Message should not be empty.')}
    try:
        Decimal(message.split()[0])
    except InvalidOperation:
        response.status = 400
        return {'error': _('Message must start with a number.')}

    try:
        resp = controller.render_txs(message)
    except (ValueError, requests.exceptions.RequestException) as e:
        response.status = 500
        return {'error': repr(e)}
    if isinstance(resp, controller.ErrorMessage):
        response.status = 400
        return {'error': resp.content}
    
    transaction_text = resp[0].content
    cursor = request.db.cursor()
    cursor.execute("INSERT INTO messages (message, transaction_text) VALUES (?, ?)", (message, transaction_text))
    request.db.commit()
    last_id = cursor.lastrowid

    return {
        'message': message,
        'transaction_text': transaction_text,
        'id': last_id,
        'status': 'pending',
    }


@app.route('/api/submit', method='POST')
def submit():
    message_id = request.json.get('id')
    if not message_id:
        response.status = 400
        return {'error': 'Message ID is required'}

    cursor = request.db.cursor()
    cursor.execute("SELECT transaction_text FROM messages WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    if not row:
        response.status = 404
        return {'error': 'Message not found'}

    trx = row[0]
    bean_manager.commit_trx(trx.strip())
    cursor.execute("UPDATE messages SET status = 1 WHERE id = ?", (message_id,))
    request.db.commit()
    return {'success': True}


@app.route('/api/clone', method='POST')
def clone_txs():
    message_id = request.json.get('id')
    if not message_id:
        response.status = 400
        return {'error': 'Message ID is required'}

    cursor = request.db.cursor()
    cursor.execute("SELECT transaction_text FROM messages WHERE id = ?", (message_id,))
    row = cursor.fetchone()
    if not row:
        response.status = 404
        return {'error': 'Message not found'}

    trx = row[0]
    resp = controller.clone_txs(trx.strip())
    if isinstance(resp, controller.ErrorMessage):
        response.status = 500
        return {
            'success': False,
            'error': resp.content
        }
    bean_manager.commit_trx(resp.content)
    return {
        'success': True,
        'data': resp.content
    }

@app.route('/api/config')
def config_json():
    # Set language to invode i18n language detector
    lang = conf.config.get("language")
    if lang:
        response.set_cookie("i18next", lang, expires=30*24*60*60)
    return {
        "lang": lang,
    }

_root_path = Path(__file__).resolve().parent.parent

@app.route('/')
def serve_frontend():
    response = static_file('index.html', root=Path(_root_path) / 'frontend/dist')
    # Set language to invode i18n language detector
    lang = conf.config.get("language")
    if lang:
        response.set_cookie("i18next", lang, expires=30*24*60*60)
    return response

@app.route('/<filename:path>')
def serve_static(filename):
    response = static_file(filename, root=Path(_root_path) / 'frontend/dist')
    if filename == "index.html":
        # Set language to invode i18n language detector
        lang = conf.config.get("language")
        if lang:
            response.set_cookie("i18next", lang, expires=30*24*60*60)    
    return response

def run_bot():
    init_db()
    web_conf = conf.config.bot.web
    app.run(host=web_conf.host, port=web_conf.port,
            debug=web_conf.get("debug", False),
            reloader=web_conf.get("reloader", False))
