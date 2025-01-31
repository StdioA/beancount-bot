import sqlite3
from pathlib import Path
from decimal import Decimal, InvalidOperation
from bottle import Bottle, request, static_file, response
from bots import controller
import conf
from bean_utils.bean import bean_manager
from conf.i18n import gettext as _

app = Bottle()

# Database setup
DATABASE = conf.config.bot.web.chat_db

def get_db():
    db = getattr(request, '_database', None)
    if db is None:
        db = request._database = sqlite3.connect(DATABASE)
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


@app.route('/api/messages')
def list_messages():
    cursor = request.db.cursor()
    cursor.execute("SELECT id, message, transaction_text, status FROM messages ORDER BY id DESC limit 20")
    messages = []

    for (id_, message, trx, status) in reversed(cursor.fetchall()):
        messages.append({
            'id': id_,
            'message': message,
            'transaction_text': trx,
            'status': 'submitted' if status == 1 else 'pending',
        })
    return {'messages': messages}


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
    except Exception as e:
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


_root_path = Path(__file__).resolve().parent.parent

@app.route('/')
def serve_frontend():
    return static_file('index.html', root=Path(_root_path) / 'frontend/dist')

@app.route('/<filename:path>')
def serve_static(filename):
    return static_file(filename, root=Path(_root_path) / 'frontend/dist')

def run_bot():
    init_db()
    web_conf = conf.config.bot.web
    app.run(host=web_conf.host, port=web_conf.port,
            debug=web_conf.get("debug", False),
            reloader=web_conf.get("reloader", False))
