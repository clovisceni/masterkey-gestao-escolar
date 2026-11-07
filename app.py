from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash, send_from_directory
import sqlite3, os, io, csv, re, secrets
from datetime import date

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(APP_DIR, 'masterkey.db')
app = Flask(__name__)
SECRET_KEY_FILE = os.path.join(APP_DIR, '.flask_secret_key')
try:
    with open(SECRET_KEY_FILE, encoding='ascii') as key_file:
        app.secret_key = key_file.read().strip()
except FileNotFoundError:
    app.secret_key = secrets.token_hex(32)
    try:
        with open(SECRET_KEY_FILE, 'x', encoding='ascii') as key_file:
            key_file.write(app.secret_key)
    except FileExistsError:
        with open(SECRET_KEY_FILE, encoding='ascii') as key_file:
            app.secret_key = key_file.read().strip()
if not app.secret_key:
    raise ValueError(f'Chave de sessão vazia: {SECRET_KEY_FILE}')
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
PHOTO_DIR = os.path.join(APP_DIR, 'student_photos')
os.makedirs(PHOTO_DIR, exist_ok=True)

MODULES = [('Windows',2),('E-mail',1),('Word',6),('Segurança Digital',1),('PowerPoint',6),('Computação em Nuvem',1),('Inteligência Artificial',2),('Excel',8)]

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY, name TEXT NOT NULL, schedule TEXT DEFAULT '', teacher TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT DEFAULT '', notes TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY, student_id INTEGER REFERENCES students(id), class_id INTEGER REFERENCES classes(id), start_date TEXT NOT NULL, entry_module TEXT NOT NULL, UNIQUE(student_id,class_id));
    CREATE TABLE IF NOT EXISTS meetings(id INTEGER PRIMARY KEY, class_id INTEGER REFERENCES classes(id), meeting_date TEXT NOT NULL, module TEXT NOT NULL, lesson INTEGER NOT NULL, UNIQUE(class_id,meeting_date,module,lesson));
    CREATE TABLE IF NOT EXISTS attendance(meeting_id INTEGER REFERENCES meetings(id) ON DELETE CASCADE, student_id INTEGER REFERENCES students(id), mark TEXT NOT NULL, PRIMARY KEY(meeting_id,student_id));
    CREATE TABLE IF NOT EXISTS module_progress(enrollment_id INTEGER REFERENCES enrollments(id) ON DELETE CASCADE, module TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Concluído','Pendente')), source TEXT DEFAULT 'initial_import', PRIMARY KEY(enrollment_id,module));
    ''')
    if 'photo_filename' not in {r['name'] for r in c.execute('PRAGMA table_info(students)') }:
        c.execute("ALTER TABLE students ADD COLUMN photo_filename TEXT DEFAULT ''")
    c.commit(); c.close()
init()

def save_student_photo(file, student_id):
    if not file or not file.filename:
        return None
    os.makedirs(PHOTO_DIR, exist_ok=True)
    name=os.path.basename(file.filename).lower()
    ext=os.path.splitext(name)[1]
    data=file.read(3*1024*1024+1)
    valid=(ext=='.jpg' and data.startswith(b'\xff\xd8\xff')) or (ext=='.jpeg' and data.startswith(b'\xff\xd8\xff')) or (ext=='.png' and data.startswith(b'\x89PNG\r\n\x1a\n'))
    if not valid or len(data)>3*1024*1024:
        raise ValueError('Envie uma foto JPG ou PNG de até 3 MB.')
    filename=f'aluno_{student_id}{ext}'
    for oldext in ('.jpg','.jpeg','.png'):
        old=os.path.join(PHOTO_DIR,f'aluno_{student_id}{oldext}')
        if os.path.isfile(old): os.remove(old)
    with open(os.path.join(PHOTO_DIR,filename),'wb') as out: out.write(data)
    return filename

BASE='''<!doctype html><html lang="pt-br"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MasterKey Gestão Escolar</title>
<style>
:root{--blue:#17447f;--blue-deep:#102f60;--red:#ed1c35;--ink:#202a43;--muted:#68748d;--line:#e2e8f3;--paper:#f4f6fc}
*{box-sizing:border-box}body{font:16px/1.5 Arial,Helvetica,sans-serif;background:var(--paper);color:var(--ink);margin:0}
header{background:linear-gradient(115deg,#17447f,#0d2b58);color:white;padding:17px max(5%,calc((100% - 1160px)/2));display:flex;justify-content:space-between;align-items:center;gap:24px;border-bottom:5px solid var(--red);box-shadow:0 5px 18px #183a8b20}
header b{font-size:25px;display:flex;align-items:baseline;gap:10px;white-space:nowrap;letter-spacing:-.5px}.brand{font-weight:800}.brand-key{color:#ff5262}.brand-subtitle{font-size:12px;font-weight:500;letter-spacing:.7px;opacity:.86}
nav{display:flex;align-items:center;gap:5px;flex-wrap:wrap;justify-content:flex-end}nav a{color:white;margin:0;text-decoration:none;padding:9px 12px;border-radius:8px;font-size:14px;font-weight:600;transition:background .15s}nav a:hover,nav a:focus{background:#ffffff25}
main{max-width:1160px;margin:30px auto;padding:0 20px}.card{background:white;padding:22px;border:1px solid #e8edf6;border-radius:14px;margin:16px 0;box-shadow:0 5px 18px #183a8b0b}h2{margin:0 0 14px;color:var(--blue-deep);font-size:23px;letter-spacing:-.25px}h3{color:var(--ink)}p{margin:8px 0 14px}
a{color:var(--blue);font-weight:600}input,select,button,textarea{font:inherit;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;margin:4px;background:white;color:var(--ink)}input:focus,select:focus,textarea:focus{outline:3px solid #17447f26;border-color:var(--blue)}button,.btn{background:var(--blue);color:white;border:0;cursor:pointer;text-decoration:none;padding:10px 15px;border-radius:8px;display:inline-block;font-weight:700;transition:background .15s,transform .15s}button:hover,.btn:hover{background:var(--blue-deep);color:white;transform:translateY(-1px)}
table{border-collapse:collapse;width:100%;margin-top:12px;background:white;border-radius:8px;overflow:hidden}th,td{text-align:left;padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#edf2ff;color:#183a9c;font-size:13px;text-transform:uppercase;letter-spacing:.35px}tr:last-child td{border-bottom:0}tr:hover td{background:#f9faff}
.muted{color:var(--muted)}.ok{color:#13785f;font-weight:700}.bad{color:var(--red);font-weight:700}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.grid>.card{margin:0;padding:18px}.grid>.card h2{font-size:30px;margin:0 0 4px;color:var(--blue)}.msg{background:#e9efff;color:#16378e;border-left:4px solid var(--blue);padding:12px 14px;border-radius:8px;margin:10px 0}form.inline{display:inline}.wide{min-width:210px}.hero{background:linear-gradient(120deg,#17447f,#102f60);color:white;border:0;padding:28px}.hero h2{color:white;font-size:28px}.hero p{color:#eef2ff}.hero .card{color:var(--ink)}.hero .card h2{color:var(--blue)}
.quick-title{margin:24px 2px 10px;font-size:18px;color:var(--ink)}.quick-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin:0 0 22px}.action-card{display:flex;align-items:center;gap:14px;min-height:112px;padding:18px;background:white;border:1px solid var(--line);border-left:5px solid var(--blue);border-radius:13px;box-shadow:0 5px 18px #183a8b0b;color:var(--ink);text-decoration:none;transition:transform .15s,box-shadow .15s,border-color .15s}.action-card:hover,.action-card:focus{color:var(--ink);transform:translateY(-2px);box-shadow:0 9px 22px #183a8b18;border-color:#b7c9ea}.action-icon{display:grid;place-items:center;flex:none;width:48px;height:48px;border-radius:13px;background:#eaf0fb;color:var(--blue-deep);font-size:15px;font-weight:800}.action-copy strong{display:block;color:var(--blue-deep);font-size:17px;line-height:1.25}.action-copy small{display:block;margin-top:6px;color:var(--muted);font-size:13px;line-height:1.35}.action-arrow{margin-left:auto;color:var(--blue);font-size:25px;font-weight:400}.action-card.alert-action{border-left-color:var(--red)}.alert-action .action-icon{background:#fff0f2;color:var(--red)}.alert-action .action-copy strong,.alert-action .action-arrow{color:#c91d32}
.module-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:9px;margin:12px 0}.module-item{padding:11px 13px;border:1px solid var(--line);border-radius:10px;background:#fafbfe}.module-item b{display:block;color:var(--ink);font-size:14px}.module-item small{display:block;margin-top:3px;color:var(--muted)}.module-item.done{background:#f0faf5;border-color:#bfe5d1}.module-item.done small{color:#13785f;font-weight:700}.module-item.pending{background:#fffafb;border-color:#f0d7dc}
.student-thumb{width:42px;height:42px;object-fit:cover;border-radius:50%;border:2px solid #e2e8f3;vertical-align:middle}.student-thumb.initials{display:inline-grid;place-items:center;background:#eaf0fb;color:var(--blue);font-weight:700}.photo-input{display:inline-block;color:var(--muted);font-size:14px}
.report-list{display:grid;gap:10px;margin-top:18px}.report-card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:15px 17px;display:grid;grid-template-columns:minmax(150px,1.4fr) minmax(130px,1.2fr) repeat(4,minmax(95px,.8fr)) minmax(140px,1.2fr);gap:12px;align-items:center;box-shadow:0 3px 12px #183a8b08}.report-head{background:#edf2ff;color:#183a7a;border-radius:8px;padding:10px 17px;display:grid;grid-template-columns:minmax(150px,1.4fr) minmax(130px,1.2fr) repeat(4,minmax(95px,.8fr)) minmax(140px,1.2fr);gap:12px;font-size:11px;font-weight:800;letter-spacing:.3px;text-transform:uppercase}.report-head span:not(:first-child),.report-value{text-align:center}.report-name{font-weight:700;color:var(--blue-deep)}.report-class{color:var(--muted);font-size:13px}.report-value small{display:block;color:var(--muted);font-size:11px}.report-pill{display:inline-block;border-radius:999px;padding:5px 9px;background:#eef2f8;color:#4b5870;font-size:12px;font-weight:700;white-space:nowrap}.report-pill.good{background:#e9f7ef;color:#13785f}.report-pill.bad{background:#fff0f2;color:#cf2438}.report-alert{font-size:12px;color:#bd2436;font-weight:700;line-height:1.35}.report-actions{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.report-actions .btn{font-size:14px}
@media(max-width:760px){header{display:block;padding:16px 20px}header b{font-size:23px}nav{justify-content:flex-start;margin-top:12px;overflow-x:auto;flex-wrap:nowrap}nav a{white-space:nowrap;padding:8px 10px}main{margin:18px auto;padding:0 12px}.card{padding:17px;margin:12px 0}.hero{padding:22px 17px}h2{font-size:21px}table{font-size:14px}.scroll{overflow:auto}input,select{max-width:100%}.quick-title{margin-top:20px}.quick-actions{grid-template-columns:1fr;gap:10px}.action-card{min-height:90px;padding:16px}}
@media(max-width:1050px){.report-head{display:none}.report-card{grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.report-name-block{grid-column:span 3}.report-value{text-align:left}.report-alert-block{grid-column:span 2}}
@media(max-width:560px){.report-card{grid-template-columns:repeat(2,minmax(0,1fr));padding:13px}.report-name-block{grid-column:span 2}.report-alert-block{grid-column:span 2}}
</style>
<header><b><span class="brand">Master<span class="brand-key">Key</span></span><small class="brand-subtitle">GESTÃO ESCOLAR</small></b><nav><a href="/">Início</a><a href="/alunos">Alunos</a><a href="/turmas">Turmas</a><a href="/chamadas">Chamadas</a><a href="/alertas">Alertas</a><a href="/relatorios">Relatórios</a></nav></header><main>{% with msgs=get_flashed_messages() %}{% for m in msgs %}<div class="msg">{{m}}</div>{% endfor %}{% endwith %}{{body|safe}}</main></html>'''
def page(body, **ctx): return render_template_string(BASE,body=render_template_string(body,**ctx))
def progress(student_id,class_id,start_date,entry_module='Windows',enrollment_id=None):
    c=db(); rows=c.execute('''SELECT m.id,m.meeting_date,m.module,m.lesson,a.mark FROM meetings m LEFT JOIN attendance a ON a.meeting_id=m.id AND a.student_id=? WHERE m.class_id=? AND m.meeting_date>=? ORDER BY m.meeting_date,m.id''',(student_id,class_id,start_date)).fetchall(); c.close()
    total=len(rows); present=sum(r['mark']=='P' for r in rows); streak=0; failed=False
    for r in rows:
        if r['mark']=='F': streak+=1; failed=failed or streak>=3
        else: streak=0
    pct=round(100*present/total) if total else 0
    c=db()
    if enrollment_id is None:
        e=c.execute('SELECT id FROM enrollments WHERE student_id=? AND class_id=?',(student_id,class_id)).fetchone(); enrollment_id=e['id'] if e else None
    module_states={r['module']:r['status'] for r in c.execute('SELECT module,status FROM module_progress WHERE enrollment_id=?',(enrollment_id,)).fetchall()} if enrollment_id else {}
    c.close()
    if len(module_states)==len(MODULES): expected={(n,k) for n,q in MODULES for k in range(1,q+1)}
    else:
        start=next((i for i,(n,_) in enumerate(MODULES) if n==entry_module),0)
        expected={(n,k) for n,q in MODULES[start:] for k in range(1,q+1)}
    done={(r['module'],r['lesson']) for r in rows if r['mark']=='P' and (r['module'],r['lesson']) in expected}
    for module,status in module_states.items():
        if status=='Concluído': done.update((module,k) for k in range(1,dict(MODULES).get(module,0)+1))
    delivered={(r['module'],r['lesson']) for r in rows if (r['module'],r['lesson']) in expected}
    complete=expected.issubset(done)
    ready=expected.issubset(delivered) and all(r['mark'] for r in rows)
    status='Reprovado' if failed else ('Aprovado' if ready and pct>=70 else 'Em andamento')
    return total,present,pct,status,len(done),len(expected),complete,streak

def module_summary(enrollment_id,student_id,class_id,start_date):
    c=db(); saved={r['module']:r['status'] for r in c.execute('SELECT module,status FROM module_progress WHERE enrollment_id=?',(enrollment_id,)).fetchall()}
    marks=c.execute('SELECT m.module,m.lesson,a.mark FROM meetings m LEFT JOIN attendance a ON a.meeting_id=m.id AND a.student_id=? WHERE m.class_id=? AND m.meeting_date>=?',(student_id,class_id,start_date)).fetchall(); c.close()
    attended={(r['module'],r['lesson']) for r in marks if r['mark']=='P'}; out=[]
    for module,count in MODULES:
        done_count=sum(1 for n,k in attended if n==module)
        complete=saved.get(module)=='Concluído' or done_count>=count
        state='Concluído' if complete else (f'Em andamento ({done_count}/{count})' if done_count else 'Pendente')
        out.append(dict(name=module,status=state,complete=complete))
    return out

def alert_for(total,pct,status,streak):
    alerts=[]
    if status!='Aprovado' and total>=4:
        if pct<70: alerts.append('Abaixo do mínimo de 70%')
        elif pct<=75: alerts.append('Próximo do mínimo de 70%')
    if streak==2: alerts.append('Duas faltas seguidas')
    return ' · '.join(alerts)

@app.get('/')
def home():
    c=db(); students=c.execute('SELECT COUNT(*) n FROM students').fetchone()['n']; classes=c.execute('SELECT COUNT(*) n FROM classes').fetchone()['n']; meetings=c.execute('SELECT COUNT(*) n FROM meetings').fetchone()['n']; c.close()
    c=db(); enrollments=c.execute('SELECT e.id,e.student_id,e.class_id,e.start_date,e.entry_module,s.name student,cl.name class_name FROM enrollments e JOIN students s ON s.id=e.student_id JOIN classes cl ON cl.id=e.class_id ORDER BY s.name').fetchall(); c.close(); alerts=[]
    for e in enrollments:
        total,present,pct,status,done,target,complete,streak=progress(e['student_id'],e['class_id'],e['start_date'],e['entry_module'],e['id']); alert=alert_for(total,pct,status,streak)
        if alert: alerts.append((e['student_id'],e['student'],e['class_name'],alert,pct))
    return page('''<section class="card hero"><h2>Bem-vindo ao MasterKey</h2><p>Controle de Turmas MasterKey</p><div class="grid"><div class="card"><h2>{{students}}</h2>alunos cadastrados</div><div class="card"><h2>{{classes}}</h2>turmas</div><div class="card"><h2>{{meetings}}</h2>aulas chamadas</div><div class="card"><h2 class="{{'bad' if alerts else ''}}">{{alerts|length}}</h2>alertas de acompanhamento</div></div></section><h2 class="quick-title">Acesso rápido</h2><section class="quick-actions"><a class="action-card" href="/chamadas/nova"><span class="action-icon">01</span><span class="action-copy"><strong>Fazer chamada</strong><small>Registrar presenças e faltas da aula</small></span><span class="action-arrow">→</span></a><a class="action-card" href="/relatorios"><span class="action-icon">02</span><span class="action-copy"><strong>Situação dos alunos</strong><small>Consultar frequência e andamento do curso</small></span><span class="action-arrow">→</span></a><a class="action-card alert-action" href="/alertas"><span class="action-icon">03</span><span class="action-copy"><strong>Ver alertas</strong><small>Acompanhar frequência e faltas seguidas</small></span><span class="action-arrow">→</span></a></section>{% if alerts %}<section class="card"><h2>Alunos para acompanhar</h2><table><tr><th>Aluno</th><th>Turma</th><th>Alerta</th><th>Frequência</th></tr>{% for a in alerts %}<tr><td><a href="/aluno/{{a[0]}}">{{a[1]}}</a></td><td>{{a[2]}}</td><td class="bad">{{a[3]}}</td><td>{{a[4]}}%</td></tr>{% endfor %}</table></section>{% endif %}<section class="card"><h2>Curso</h2><p>{% for n,q in modules %}<span class="wide">{{n}}: {{q}} aula(s)</span><br>{% endfor %}</p><b>Total: 27 aulas</b></section>''',students=students,classes=classes,meetings=meetings,modules=MODULES,alerts=alerts)

@app.route('/turmas',methods=['GET','POST'])
def classes():
    c=db()
    if request.method=='POST':
        c.execute('INSERT INTO classes(name,schedule,teacher) VALUES(?,?,?)',(request.form['name'],request.form.get('schedule',''),request.form.get('teacher',''))); c.commit(); flash('Turma cadastrada.')
    q=request.args.get('q','').strip(); rows=c.execute('SELECT * FROM classes WHERE name LIKE ? ORDER BY name',('%'+q+'%',)).fetchall(); c.close()
    return page('''<section class="card"><h2>Turmas</h2><form method="post"><input name="name" placeholder="Nome da turma" required><input name="schedule" placeholder="Horário"><input name="teacher" placeholder="Professor"><button>Salvar turma</button></form></section><section class="card"><form method="get"><input name="q" value="{{q}}" placeholder="Buscar turma"><button>Buscar</button> <a href="/turmas">Limpar</a></form><table><tr><th>Turma</th><th>Horário</th><th>Professor</th><th></th></tr>{% for x in rows %}<tr><td>{{x.name}}</td><td>{{x.schedule}}</td><td>{{x.teacher}}</td><td><a href="/turmas/{{x.id}}">Alunos / matrículas</a> · <a href="/turmas/{{x.id}}/editar">Editar</a></td></tr>{% else %}<tr><td colspan="4">Nenhuma turma encontrada.</td></tr>{% endfor %}</table></section>''',rows=rows,q=q)

@app.route('/alunos',methods=['GET','POST'])
def students():
    c=db()
    if request.method=='POST':
        c.execute('INSERT INTO students(name,phone) VALUES(?,?)',(request.form['name'],request.form.get('phone',''))); sid=c.execute('SELECT last_insert_rowid()').fetchone()[0]
        try:
            photo=save_student_photo(request.files.get('photo'),sid)
            if photo: c.execute('UPDATE students SET photo_filename=? WHERE id=?',(photo,sid))
            c.commit(); flash('Aluno cadastrado.' if not photo else 'Aluno cadastrado com foto.')
        except ValueError as err:
            c.rollback(); c.execute('DELETE FROM students WHERE id=?',(sid,)); c.commit(); flash(str(err))
    q=request.args.get('q','').strip(); class_id=request.args.get('class_id','')
    sql='SELECT DISTINCT s.* FROM students s LEFT JOIN enrollments e ON e.student_id=s.id WHERE s.name LIKE ?'; args=['%'+q+'%']
    if class_id: sql+=' AND e.class_id=?'; args.append(class_id)
    sql+=' ORDER BY s.name'; rows=c.execute(sql,args).fetchall(); cls=c.execute('SELECT * FROM classes ORDER BY name').fetchall(); c.close()
    return page('''<section class="card"><h2>Alunos</h2><form method="post" enctype="multipart/form-data"><input name="name" placeholder="Nome completo" required><input name="phone" placeholder="Telefone (opcional)"><label class="photo-input">Foto pequena (opcional) <input name="photo" type="file" accept="image/jpeg,image/png"></label><button>Cadastrar aluno</button></form><p class="muted">JPG ou PNG, até 3 MB. Você também pode incluir a foto depois em Editar.</p></section><section class="card"><form method="get"><input name="q" value="{{q}}" placeholder="Buscar pelo nome"><select name="class_id"><option value="">Todas as turmas</option>{% for c in cls %}<option value="{{c.id}}" {% if class_id|string==c.id|string %}selected{% endif %}>{{c.name}}</option>{% endfor %}</select><button>Buscar</button> <a href="/alunos">Limpar</a></form><table><tr><th>Foto</th><th>Nome</th><th>Telefone</th><th></th></tr>{% for x in rows %}<tr><td>{% if x.photo_filename %}<img class="student-thumb" src="/foto/{{x.id}}" alt="Foto de {{x.name}}">{% else %}<span class="student-thumb initials">{{x.name[:1]}}</span>{% endif %}</td><td>{{x.name}}</td><td>{{x.phone}}</td><td><a href="/aluno/{{x.id}}">Histórico</a> · <a href="/aluno/{{x.id}}/editar">Editar</a></td></tr>{% else %}<tr><td colspan="4">Nenhum aluno encontrado.</td></tr>{% endfor %}</table></section>''',rows=rows,q=q,cls=cls,class_id=class_id)

@app.get('/foto/<int:sid>')
def student_photo(sid):
    c=db(); row=c.execute('SELECT photo_filename FROM students WHERE id=?',(sid,)).fetchone(); c.close()
    if not row or not row['photo_filename']: return '',404
    filename=row['photo_filename']
    if not re.fullmatch(r'aluno_%d\.(jpg|jpeg|png)' % sid,filename): return '',404
    return send_from_directory(PHOTO_DIR,filename,as_attachment=False)

@app.route('/aluno/<int:sid>/editar',methods=['GET','POST'])
def edit_student(sid):
    c=db(); s=c.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
    if not s: c.close(); return 'Aluno não encontrado',404
    if request.method=='POST':
        try:
            photo=save_student_photo(request.files.get('photo'),sid)
            c.execute('UPDATE students SET name=?,phone=?,notes=? WHERE id=?',(request.form['name'].strip(),request.form.get('phone','').strip(),request.form.get('notes','').strip(),sid))
            if photo: c.execute('UPDATE students SET photo_filename=? WHERE id=?',(photo,sid))
            c.commit(); c.close(); flash('Cadastro do aluno atualizado.'); return redirect(url_for('student_history',sid=sid))
        except ValueError as err:
            flash(str(err))
    c.close(); return page('''<section class="card"><h2>Editar aluno</h2>{% if s.photo_filename %}<p><img class="student-thumb" src="/foto/{{s.id}}" alt="Foto de {{s.name}}"></p>{% endif %}<form method="post" enctype="multipart/form-data"><p><input name="name" value="{{s.name}}" placeholder="Nome completo" required></p><p><input name="phone" value="{{s.phone}}" placeholder="Telefone"></p><p><label>Foto pequena (opcional) <input name="photo" type="file" accept="image/jpeg,image/png"></label></p><p><textarea name="notes" placeholder="Observações" rows="3">{{s.notes}}</textarea></p><button>Salvar alterações</button> <a class="btn" href="/aluno/{{s.id}}">Cancelar</a></form><p class="muted">JPG ou PNG, até 3 MB. Ao enviar uma nova foto, ela substitui a atual.</p></section>''',s=s)

@app.route('/turmas/<int:cid>',methods=['GET','POST'])
def class_detail(cid):
    c=db(); cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
    if not cl: c.close(); return 'Turma não encontrada',404
    if request.method=='POST':
        try: c.execute('INSERT INTO enrollments(student_id,class_id,start_date,entry_module) VALUES(?,?,?,?)',(request.form['student_id'],cid,request.form['start_date'],request.form['entry_module'])); c.commit(); flash('Matrícula realizada.')
        except sqlite3.IntegrityError: flash('Este aluno já está matriculado nesta turma.')
    students=c.execute('SELECT * FROM students WHERE id NOT IN (SELECT student_id FROM enrollments WHERE class_id=?) ORDER BY name',(cid,)).fetchall()
    roster=c.execute('SELECT s.id,s.name,e.start_date,e.entry_module FROM enrollments e JOIN students s ON s.id=e.student_id WHERE e.class_id=? ORDER BY s.name',(cid,)).fetchall(); c.close()
    return page('''<section class="card"><h2>{{cl.name}}</h2><p>{{cl.schedule}} · Professor: {{cl.teacher}}</p><a class="btn" href="/exportar/lista-frequencia?class_id={{cl.id}}">Baixar lista de frequência PDF</a><h3>Matricular aluno</h3><form method="post"><select name="student_id" required><option value="">Selecione aluno</option>{% for s in students %}<option value="{{s.id}}">{{s.name}}</option>{% endfor %}</select><input type="date" name="start_date" value="{{today}}" required><select name="entry_module">{% for n,q in modules %}<option>{{n}}</option>{% endfor %}</select><button>Matricular</button></form><p class="muted">A frequência passa a contar a partir da data da matrícula. O módulo de entrada é informativo; os módulos podem ser cursados fora de ordem.</p></section><section class="card"><h2>Alunos da turma</h2><table><tr><th>Aluno</th><th>Matrícula</th><th>Módulo de entrada</th><th>Histórico</th></tr>{% for s in roster %}<tr><td>{{s.name}}</td><td>{{s.start_date}}</td><td>{{s.entry_module}}</td><td><a href="/aluno/{{s.id}}">Abrir</a></td></tr>{% else %}<tr><td colspan="4">Ainda não há matrículas.</td></tr>{% endfor %}</table></section>''',cl=cl,students=students,roster=roster,today=date.today().isoformat(),modules=MODULES)

@app.route('/turmas/<int:cid>/editar',methods=['GET','POST'])
def edit_class(cid):
    c=db(); cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
    if not cl: c.close(); return 'Turma não encontrada',404
    if request.method=='POST':
        c.execute('UPDATE classes SET name=?,schedule=?,teacher=? WHERE id=?',(request.form['name'].strip(),request.form.get('schedule','').strip(),request.form.get('teacher','').strip(),cid)); c.commit(); c.close(); flash('Dados da turma atualizados.'); return redirect(url_for('class_detail',cid=cid))
    c.close(); return page('''<section class="card"><h2>Editar turma</h2><form method="post"><p><input name="name" value="{{cl.name}}" required></p><p><input name="schedule" value="{{cl.schedule}}" placeholder="Horário"></p><p><input name="teacher" value="{{cl.teacher}}" placeholder="Professor"></p><button>Salvar alterações</button> <a class="btn" href="/turmas/{{cl.id}}">Cancelar</a></form></section>''',cl=cl)

@app.route('/chamadas')
def calls():
    c=db(); cls=c.execute('SELECT * FROM classes ORDER BY name').fetchall(); q=request.args.get('q','').strip(); class_id=request.args.get('class_id',''); module=request.args.get('module',''); start=request.args.get('start',''); end=request.args.get('end','')
    sql='SELECT m.*,cl.name class_name FROM meetings m JOIN classes cl ON cl.id=m.class_id WHERE cl.name LIKE ?'; args=['%'+q+'%']
    if class_id: sql+=' AND m.class_id=?'; args.append(class_id)
    if module: sql+=' AND m.module=?'; args.append(module)
    if start: sql+=' AND m.meeting_date>=?'; args.append(start)
    if end: sql+=' AND m.meeting_date<=?'; args.append(end)
    sql+=' ORDER BY meeting_date DESC,m.id DESC'; rows=c.execute(sql,args).fetchall(); c.close()
    return page('''<section class="card"><h2>Chamadas</h2><a class="btn" href="/chamadas/nova">Nova chamada</a><form method="get"><input name="q" value="{{q}}" placeholder="Buscar turma"><select name="class_id"><option value="">Todas as turmas</option>{% for c in cls %}<option value="{{c.id}}" {% if class_id|string==c.id|string %}selected{% endif %}>{{c.name}}</option>{% endfor %}</select><select name="module"><option value="">Todos os módulos</option>{% for n,count in modules %}<option {% if module==n %}selected{% endif %}>{{n}}</option>{% endfor %}</select>De <input type="date" name="start" value="{{start}}"> até <input type="date" name="end" value="{{end}}"><button>Filtrar</button> <a href="/chamadas">Limpar</a></form><table><tr><th>Data</th><th>Turma</th><th>Módulo</th><th>Aula</th><th></th></tr>{% for m in rows %}<tr><td>{{m.meeting_date}}</td><td>{{m.class_name}}</td><td>{{m.module}}</td><td>{{m.lesson}}</td><td><a href="/chamada/{{m.id}}">Abrir / corrigir chamada</a></td></tr>{% else %}<tr><td colspan="5">Nenhuma aula encontrada.</td></tr>{% endfor %}</table></section>''',rows=rows,cls=cls,q=q,class_id=class_id,module=module,start=start,end=end,modules=MODULES)

@app.route('/chamadas/nova',methods=['GET','POST'])
def new_call():
    c=db(); cls=c.execute('SELECT * FROM classes ORDER BY name').fetchall()
    if request.method=='POST':
        try:
            c.execute('INSERT INTO meetings(class_id,meeting_date,module,lesson) VALUES(?,?,?,?)',(request.form['class_id'],request.form['meeting_date'],request.form['module'],request.form['lesson'])); mid=c.execute('SELECT last_insert_rowid()').fetchone()[0]; c.commit(); c.close(); return redirect(url_for('take_call',mid=mid))
        except sqlite3.IntegrityError:
            m=c.execute('SELECT id FROM meetings WHERE class_id=? AND meeting_date=? AND module=? AND lesson=?',(request.form['class_id'],request.form['meeting_date'],request.form['module'],request.form['lesson'])).fetchone(); c.close(); flash('Esta aula já tem chamada cadastrada. Você pode abri-la e corrigir os registros.'); return redirect(url_for('take_call',mid=m['id']))
    c.close(); return page('''<section class="card"><h2>Nova chamada</h2><form method="post"><p><select name="class_id" required><option value="">Turma</option>{% for c in cls %}<option value="{{c.id}}">{{c.name}}</option>{% endfor %}</select><input name="meeting_date" type="date" value="{{today}}" required></p><p><select name="module" id="module" onchange="setLessons()">{% for n,q in modules %}<option value="{{n}}" data-q="{{q}}">{{n}}</option>{% endfor %}</select><select name="lesson" id="lesson"></select><button>Continuar para chamada</button></p></form></section><script>function setLessons(){let s=document.querySelector('#module'),q=+s.options[s.selectedIndex].dataset.q,l=document.querySelector('#lesson');l.innerHTML='';for(let i=1;i<=q;i++)l.add(new Option('Aula '+i,i))}setLessons()</script>''',cls=cls,today=date.today().isoformat(),modules=MODULES)

@app.route('/chamada/<int:mid>',methods=['GET','POST'])
def take_call(mid):
    c=db(); m=c.execute('SELECT m.*,cl.name class_name FROM meetings m JOIN classes cl ON cl.id=m.class_id WHERE m.id=?',(mid,)).fetchone()
    if not m: c.close(); return 'Chamada não encontrada',404
    if request.method=='POST':
        for k,v in request.form.items():
            if k.startswith('s_') and v in ('P','F'):
                c.execute('INSERT INTO attendance(meeting_id,student_id,mark) VALUES(?,?,?) ON CONFLICT(meeting_id,student_id) DO UPDATE SET mark=excluded.mark',(mid,int(k[2:]),v))
            elif k.startswith('s_') and v=='X': c.execute('DELETE FROM attendance WHERE meeting_id=? AND student_id=?',(mid,int(k[2:])))
        c.commit(); flash('Chamada salva.'); c.close(); return redirect(url_for('calls'))
    roster=c.execute('SELECT s.id,s.name,a.mark FROM enrollments e JOIN students s ON s.id=e.student_id LEFT JOIN attendance a ON a.student_id=s.id AND a.meeting_id=? WHERE e.class_id=? AND e.start_date<=? ORDER BY s.name',(mid,m['class_id'],m['meeting_date'])).fetchall(); c.close()
    return page('''<section class="card"><h2>Chamada: {{m.class_name}}</h2><p>{{m.meeting_date}} · {{m.module}} · Aula {{m.lesson}} <a href="/chamada/{{m.id}}/editar">Corrigir data, módulo ou aula</a></p><form method="post"><div class="scroll"><table><tr><th>Aluno</th><th>Registro</th></tr>{% for s in roster %}<tr><td>{{s.name}}</td><td><label><input type="radio" name="s_{{s.id}}" value="P" {% if s.mark=='P' %}checked{% endif %}> Presente</label><label><input type="radio" name="s_{{s.id}}" value="F" {% if s.mark=='F' %}checked{% endif %}> Falta</label><label><input type="radio" name="s_{{s.id}}" value="X"> Limpar</label></td></tr>{% else %}<tr><td colspan="2">Não há alunos matriculados até esta data.</td></tr>{% endfor %}</table></div><button>Salvar chamada</button> <a class="btn" href="/chamadas">Voltar</a></form><p class="muted">Use “Limpar” para remover um registro lançado por engano.</p></section>''',m=m,roster=roster)

@app.route('/chamada/<int:mid>/editar',methods=['GET','POST'])
def edit_meeting(mid):
    c=db(); m=c.execute('SELECT * FROM meetings WHERE id=?',(mid,)).fetchone()
    if not m: c.close(); return 'Aula não encontrada',404
    if request.method=='POST':
        module=request.form['module']; lesson=int(request.form['lesson']); allowed=dict(MODULES).get(module,0)
        if not allowed or lesson<1 or lesson>allowed: c.close(); flash('Módulo ou número de aula inválido.'); return redirect(url_for('edit_meeting',mid=mid))
        try:
            c.execute('UPDATE meetings SET meeting_date=?,module=?,lesson=? WHERE id=?',(request.form['meeting_date'],module,lesson,mid)); c.commit()
        except sqlite3.IntegrityError: c.close(); flash('Já existe uma chamada igual para esta turma, data, módulo e aula.'); return redirect(url_for('edit_meeting',mid=mid))
        c.close(); flash('Dados da aula corrigidos.'); return redirect(url_for('take_call',mid=mid))
    cls=c.execute('SELECT name FROM classes WHERE id=?',(m['class_id'],)).fetchone(); c.close()
    return page('''<section class="card"><h2>Corrigir dados da aula</h2><form method="post"><p>Turma: {{class_name}}</p><p><label>Data <input type="date" name="meeting_date" value="{{m.meeting_date}}" required></label></p><p><label>Módulo <select name="module" id="module" onchange="setLessons()">{% for n,q in modules %}<option value="{{n}}" data-q="{{q}}" {% if m.module==n %}selected{% endif %}>{{n}}</option>{% endfor %}</select></label> <label>Aula <select name="lesson" id="lesson" data-current="{{m.lesson}}"></select></label></p><button>Salvar correção</button> <a class="btn" href="/chamada/{{m.id}}">Cancelar</a></form><p class="muted">A correção mantém os registros de presença e falta desta chamada.</p></section><script>function setLessons(){let s=document.querySelector('#module'),q=+s.options[s.selectedIndex].dataset.q,l=document.querySelector('#lesson'),cur=+l.dataset.current;l.innerHTML='';for(let i=1;i<=q;i++)l.add(new Option('Aula '+i,i,i===cur,i===cur))}setLessons()</script>''',m=m,class_name=cls['name'],modules=MODULES)

@app.route('/aluno/<int:sid>')
def student_history(sid):
    c=db(); s=c.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
    if not s: c.close(); return 'Aluno não encontrado',404
    enroll=c.execute('SELECT e.*,cl.name class_name FROM enrollments e JOIN classes cl ON cl.id=e.class_id WHERE e.student_id=? ORDER BY e.start_date',(sid,)).fetchall(); history=[]
    for e in enroll:
        total,present,pct,status,done,target,complete,streak=progress(sid,e['class_id'],e['start_date'],e['entry_module'],e['id']); history.append(dict(class_name=e['class_name'],start=e['start_date'],entry=e['entry_module'],total=total,present=present,pct=pct,status=status,done=done,target=target,complete=complete,alert=alert_for(total,pct,status,streak),modules=module_summary(e['id'],sid,e['class_id'],e['start_date'])))
    meetings=c.execute('SELECT m.meeting_date,m.module,m.lesson,a.mark,cl.name class_name FROM attendance a JOIN meetings m ON m.id=a.meeting_id JOIN classes cl ON cl.id=m.class_id WHERE a.student_id=? ORDER BY m.meeting_date DESC',(sid,)).fetchall(); c.close()
    return page('''<section class="card"><h2>{{s.name}}</h2><p>{{s.phone}} · <a href="/aluno/{{s.id}}/editar">Editar cadastro</a></p>{% for e in history %}<h3>Conteúdo por módulo · {{e.class_name}}</h3><div class="module-grid">{% for m in e.modules %}<div class="module-item {{'done' if m.complete else 'pending'}}"><b>{{m.name}}</b><small>{{m.status}}</small></div>{% endfor %}</div>{% endfor %}<h3>Resumo por turma</h3><table><tr><th>Turma</th><th>Matrícula</th><th>Entrada</th><th>Presenças</th><th>Frequência</th><th>Aulas concluídas</th><th>Situação</th><th>Alerta</th></tr>{% for e in history %}<tr><td>{{e.class_name}}</td><td>{{e.start}}</td><td>{{e.entry}}</td><td>{{e.present}} / {{e.total}}</td><td>{{e.pct}}%</td><td>{{e.done}} / {{e.target}}</td><td>{{e.status}}</td><td class="bad">{{e.alert}}</td></tr>{% else %}<tr><td colspan="8">Sem matrícula.</td></tr>{% endfor %}</table><p class="muted">Os módulos marcados como concluídos podem incluir um histórico informado manualmente; isso não altera o cálculo de frequência ou aprovação.</p></section><section class="card"><h3>Histórico de chamadas</h3><table><tr><th>Data</th><th>Turma</th><th>Módulo</th><th>Aula</th><th>Registro</th></tr>{% for x in meetings %}<tr><td>{{x.meeting_date}}</td><td>{{x.class_name}}</td><td>{{x.module}}</td><td>{{x.lesson}}</td><td>{{'Presente' if x.mark=='P' else 'Falta'}}</td></tr>{% else %}<tr><td colspan="5">Sem registros.</td></tr>{% endfor %}</table></section>''',s=s,history=history,meetings=meetings)

@app.get('/alertas')
def alerts_page():
    c=db(); enrollments=c.execute('SELECT e.id,e.student_id,e.class_id,e.start_date,e.entry_module,s.name student,cl.name class_name FROM enrollments e JOIN students s ON s.id=e.student_id JOIN classes cl ON cl.id=e.class_id ORDER BY s.name').fetchall(); c.close(); rows=[]
    for e in enrollments:
        total,present,pct,status,done,target,complete,streak=progress(e['student_id'],e['class_id'],e['start_date'],e['entry_module'],e['id']); alert=alert_for(total,pct,status,streak)
        if alert: rows.append(dict(id=e['student_id'],student=e['student'],class_name=e['class_name'],alert=alert,pct=pct,present=present,total=total))
    return page('''<section class="card"><h2>Alertas de acompanhamento</h2><p class="muted">O alerta de frequência aparece depois de quatro aulas registradas; duas faltas seguidas são sinalizadas imediatamente.</p><table><tr><th>Aluno</th><th>Turma</th><th>Alerta</th><th>Frequência</th><th></th></tr>{% for r in rows %}<tr><td>{{r.student}}</td><td>{{r.class_name}}</td><td class="bad">{{r.alert}}</td><td>{{r.present}}/{{r.total}} ({{r.pct}}%)</td><td><a href="/aluno/{{r.id}}">Histórico</a></td></tr>{% else %}<tr><td colspan="5">Nenhum alerta no momento.</td></tr>{% endfor %}</table></section>''',rows=rows)

def report_rows(q='',class_id=''):
    c=db(); sql='SELECT e.*,s.name student,cl.name class_name,cl.schedule,cl.teacher FROM enrollments e JOIN students s ON s.id=e.student_id JOIN classes cl ON cl.id=e.class_id WHERE s.name LIKE ?'; args=['%'+q+'%']
    if class_id: sql+=' AND cl.id=?'; args.append(class_id)
    sql+=' ORDER BY cl.name,s.name'; es=c.execute(sql,args).fetchall(); out=[]
    for e in es:
        total,present,pct,status,done,target,complete,streak=progress(e['student_id'],e['class_id'],e['start_date'],e['entry_module'],e['id']); alert=alert_for(total,pct,status,streak)
        out.append([e['student'],e['class_name'],e['schedule'],e['teacher'],e['start_date'],e['entry_module'],present,total,pct,done,target,status,alert,e['student_id']])
    classes=c.execute('SELECT * FROM classes ORDER BY name').fetchall(); c.close(); return out,classes
@app.get('/relatorios')
def reports():
    q=request.args.get('q','').strip(); class_id=request.args.get('class_id',''); rows,cls=report_rows(q,class_id)
    return page('''<section class="card"><h2>Relatório de frequência</h2><p>Acompanhe presença, avanço do conteúdo e situação do curso. A aprovação requer 70% de frequência; três faltas consecutivas reprovam. Conclusão das aulas e aprovação são acompanhadas separadamente.</p><form method="get"><input name="q" value="{{q}}" placeholder="Buscar aluno"><select name="class_id"><option value="">Todas as turmas</option>{% for c in cls %}<option value="{{c.id}}" {% if class_id|string==c.id|string %}selected{% endif %}>{{c.name}}</option>{% endfor %}</select><button>Filtrar</button> <a href="/relatorios">Limpar</a></form><div class="report-actions"><a class="btn" href="/exportar/xlsx?q={{q}}&class_id={{class_id}}">Baixar Excel</a><a class="btn" href="/exportar/pdf?q={{q}}&class_id={{class_id}}">Baixar resumo PDF</a>{% if class_id %}<a class="btn" href="/exportar/lista-frequencia?class_id={{class_id}}">Lista de chamada PDF</a>{% endif %}<a class="btn" href="/backup">Backup</a></div><div class="report-head"><span>Aluno</span><span>Turma</span><span>Presença</span><span>Frequência</span><span>Conteúdo</span><span>Situação</span><span>Alerta</span></div><div class="report-list">{% for r in rows %}<article class="report-card"><div class="report-name-block"><div class="report-name"><a href="/aluno/{{r[13]}}">{{r[0]}}</a></div><div class="report-class">Matrícula: {{r[4]}} · Entrada: {{r[5]}}</div></div><div><span class="report-class">Turma</span><br><b>{{r[1]}}</b></div><div class="report-value"><small>Presenças</small><b>{{r[6]}} / {{r[7]}}</b></div><div class="report-value"><small>Frequência</small><span class="report-pill {{'bad' if r[8]<70 else 'good' if r[8]>=70 and r[11]=='Aprovado' else ''}}">{{r[8]}}%</span></div><div class="report-value"><small>Conteúdo</small><b>{{r[9]}} / {{r[10]}} aulas</b></div><div class="report-value"><small>Situação</small><span class="report-pill {{'bad' if r[11]=='Reprovado' else 'good' if r[11]=='Aprovado' else ''}}">{{r[11]}}</span></div><div class="report-alert-block"><small class="report-class">Alerta</small><div class="report-alert">{{r[12] or '—'}}</div></div></article>{% else %}<p class="muted">Nenhuma matrícula encontrada.</p>{% endfor %}</div><p class="muted">O relatório mostra só os dados mais úteis para o acompanhamento diário. Horário, professor e demais informações continuam disponíveis no cadastro da turma e na exportação Excel.</p></section>''',rows=rows,cls=cls,q=q,class_id=class_id)

@app.get('/exportar/xlsx')
def export_xlsx():
    import xlsxwriter
    data,_=report_rows(request.args.get('q','').strip(),request.args.get('class_id','')); b=io.BytesIO(); book=xlsxwriter.Workbook(b,{'in_memory':True}); sh=book.add_worksheet('Frequência'); head=book.add_format({'bold':True,'bg_color':'#142b4a','font_color':'white'}); sh.write_row(0,0,['Aluno','Turma','Horário','Professor','Matrícula','Módulo de entrada','Presenças','Aulas chamadas','Frequência %','Aulas concluídas','Aulas previstas','Situação','Alerta'],head)
    for i,row in enumerate(data,1): sh.write_row(i,0,row[:13])
    sh.set_column('A:A',28); sh.set_column('B:D',22); sh.set_column('E:F',20); sh.set_column('G:M',18); book.close(); b.seek(0); return send_file(b,as_attachment=True,download_name='relatorio_masterkey.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.get('/exportar/csv')
def export_csv():
    data,_=report_rows(request.args.get('q','').strip(),request.args.get('class_id','')); buf=io.StringIO(); buf.write('\ufeff'); w=csv.writer(buf,delimiter=';'); w.writerow(['Aluno','Turma','Horário','Professor','Matrícula','Módulo de entrada','Presenças','Aulas registradas','Frequência %','Aulas concluídas','Aulas previstas','Situação','Alerta']); w.writerows([r[:13] for r in data]); out=io.BytesIO(buf.getvalue().encode('utf-8-sig')); return send_file(out,as_attachment=True,download_name='relatorio_masterkey.csv',mimetype='text/csv')

@app.get('/exportar/lista-frequencia')
def export_attendance_sheet():
    from reportlab.lib.pagesizes import landscape,A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    cid=request.args.get('class_id','',type=int)
    c=db(); cl=c.execute('SELECT * FROM classes WHERE id=?',(cid,)).fetchone()
    if not cl: c.close(); return 'Selecione uma turma válida.',404
    roster=c.execute('SELECT s.id,s.name,s.photo_filename,e.start_date FROM enrollments e JOIN students s ON s.id=e.student_id WHERE e.class_id=? ORDER BY s.name',(cid,)).fetchall()
    marks=c.execute('''SELECT e.student_id,m.module,m.lesson,a.mark FROM enrollments e JOIN meetings m ON m.class_id=e.class_id AND m.meeting_date>=e.start_date LEFT JOIN attendance a ON a.meeting_id=m.id AND a.student_id=e.student_id WHERE e.class_id=?''',(cid,)).fetchall(); c.close()
    grid={}
    for row in marks:
        if row['mark'] in ('P','F'): grid[(row['student_id'],row['module'],row['lesson'])]=row['mark']
    b=io.BytesIO(); width,height=landscape(A4); p=canvas.Canvas(b,pagesize=(width,height)); blue=colors.HexColor('#12396f'); red=colors.HexColor('#e72d43'); pale=colors.HexColor('#edf2fb'); ink=colors.HexColor('#233047')
    left=22; photo_w=27; name_w=105; start=left+photo_w+name_w; cell_w=(width-left*2-photo_w-name_w)/27; row_h=28; header_bottom=height-118
    positions=[]
    for mod,count in MODULES:
        positions.append((mod,count))
    def draw_heading(page_no):
        p.setFillColor(blue); p.rect(0,height-61,width,61,fill=1,stroke=0)
        p.setFillColor(colors.white); p.setFont('Helvetica-Bold',16); p.drawString(left,height-31,'MasterKey  |  Lista de frequência')
        p.setFont('Helvetica',8.5); p.drawRightString(width-left,height-29,'FOLHA DE CHAMADA  •  '+date.today().strftime('%d/%m/%Y'))
        p.setFillColor(ink); p.setFont('Helvetica-Bold',10); p.drawString(left,height-79,cl['name'])
        p.setFont('Helvetica',8.5); p.drawString(left,height-94,('Professor: '+(cl['teacher'] or '—')+'    •    Horário: '+(cl['schedule'] or '—'))[:95])
        p.drawRightString(width-left,height-94,'Marque P (presente) ou F (falta)')
        y=header_bottom
        p.setFillColor(blue); p.rect(left,y,photo_w+name_w,row_h,fill=1,stroke=0); p.setFillColor(colors.white); p.setFont('Helvetica-Bold',7.5); p.drawString(left+4,y+10,'ALUNO')
        x=start
        for mod,count in positions:
            w=count*cell_w; p.setFillColor(red if mod in ('Word','PowerPoint','Excel') else blue); p.roundRect(x,y+row_h-14,w,14,3,fill=1,stroke=0); p.setFillColor(colors.white); p.setFont('Helvetica-Bold',5.7)
            label={'Segurança Digital':'Seg.','Computação em Nuvem':'Nuvem','Inteligência Artificial':'IA','Windows':'Windows'}.get(mod,mod)
            p.setFont('Helvetica-Bold',4.8 if count==1 and len(label)>5 else 5.7)
            p.drawCentredString(x+w/2,y+row_h-10,label)
            for lesson in range(1,count+1):
                xx=x+(lesson-1)*cell_w; p.setFillColor(pale); p.rect(xx,y,cell_w,row_h-15,fill=1,stroke=0); p.setStrokeColor(colors.HexColor('#d2daea')); p.rect(xx,y,cell_w,row_h-15,fill=0,stroke=1); p.setFillColor(ink); p.setFont('Helvetica',7); p.drawCentredString(xx+cell_w/2,y+6,str(lesson))
            x+=w
        p.setStrokeColor(colors.HexColor('#d9dfeb')); p.line(left, y, width-left, y)
        return y-1
    y=draw_heading(1); rows_per_page=max(1,int((y-39)//row_h))
    for idx,s in enumerate(roster):
        if idx and idx%rows_per_page==0:
            p.setFillColor(colors.HexColor('#768198')); p.setFont('Helvetica',7); p.drawString(left,20,'Legenda: P presente  •  F falta  •  em branco sem registro')
            p.showPage(); y=draw_heading(idx//rows_per_page+1)
        y-=row_h
        if idx%2==0: p.setFillColor(colors.HexColor('#f7f9fd')); p.rect(left,y,width-left*2,row_h,fill=1,stroke=0)
        p.setStrokeColor(colors.HexColor('#e3e8f0')); p.line(left,y,width-left,y)
        fn=s['photo_filename']; photo_path=os.path.join(PHOTO_DIR,fn) if fn and os.path.basename(fn)==fn else ''
        if photo_path and os.path.isfile(photo_path):
            try: p.drawImage(ImageReader(photo_path),left+3,y+3,width=21,height=21,preserveAspectRatio=True,anchor='c',mask='auto')
            except Exception: pass
        else:
            p.setFillColor(pale); p.circle(left+13,y+14,9,fill=1,stroke=0); p.setFillColor(blue); p.setFont('Helvetica-Bold',8); p.drawCentredString(left+13,y+11,s['name'][:1].upper())
        p.setFillColor(ink); p.setFont('Helvetica-Bold',7.4); p.drawString(left+photo_w+3,y+10,s['name'][:27])
        x=start
        for mod,count in positions:
            for lesson in range(1,count+1):
                mark=grid.get((s['id'],mod,lesson))
                if mark:
                    p.setFillColor(colors.HexColor('#17845e') if mark=='P' else red); p.setFont('Helvetica-Bold',8); p.drawCentredString(x+cell_w/2,y+10,mark)
                x+=cell_w
    p.setFillColor(colors.HexColor('#768198')); p.setFont('Helvetica',7); p.drawString(left,20,'Legenda: P presente  •  F falta  •  em branco sem registro')
    p.drawRightString(width-left,20,'Página preparada para impressão em A4 paisagem')
    p.save(); b.seek(0)
    safe=re.sub(r'[^A-Za-z0-9_-]+','_',cl['name']).strip('_') or 'turma'
    return send_file(b,as_attachment=True,download_name=f'lista_frequencia_{safe}.pdf',mimetype='application/pdf')

@app.get('/exportar/pdf')
def export_pdf():
    from reportlab.lib.pagesizes import landscape,A4
    from reportlab.pdfgen import canvas
    data,_=report_rows(request.args.get('q','').strip(),request.args.get('class_id','')); b=io.BytesIO(); p=canvas.Canvas(b,pagesize=landscape(A4)); p.setFont('Helvetica-Bold',16); p.drawString(35,560,'MasterKey - Relatório de frequência'); p.setFont('Helvetica',8); y=540
    headers=['Aluno / turma / professor','Matrícula / horário','Entrada','Pres.','Aulas','Freq.','Concl.','Prev.','Situação','Alerta']; xs=[30,205,335,415,445,480,515,545,575,635]
    for i,h in enumerate(headers): p.drawString(xs[i],y,h)
    for row in data:
        y-=22
        if y<35: p.showPage(); y=560
        vals=[f'{row[0][:22]} / {row[1][:14]} / {row[3][:14]}',f'{row[4]} / {row[2][:12]}',row[5][:12],str(row[6]),str(row[7]),str(row[8])+'%',str(row[9]),str(row[10]),row[11],row[12][:18]]
        for i,v in enumerate(vals): p.drawString(xs[i],y,str(v)[:28])
    p.save(); b.seek(0); return send_file(b,as_attachment=True,download_name='relatorio_masterkey.pdf',mimetype='application/pdf')

@app.get('/backup')
def backup(): return send_file(DB,as_attachment=True,download_name='backup_masterkey.db')

if __name__=='__main__':
    app.run(host='127.0.0.1',port=5000,debug=False)
