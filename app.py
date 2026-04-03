import sqlite3
import calendar #달력
from flask import Flask, render_template, request, redirect, url_for, flash , session
from datetime import datetime #기본날짜 ,시간

app = Flask(__name__)
app.secret_key = "secret_key_for_session" #세션 유지를 위한 암호화 키

@app.route('/main')
def main():
    if 'user_id' not in session: # 세션에 id 없으면 로그인 페이지로 강제 이동
        return redirect(url_for('login'))

    today = datetime.now()
    now_year = today.year
    now_month = today.month
    now_day = today.day

    mode = request.args.get('mode', 'calendar') #연도선택,월 선택, 달력 화면
    year = request.args.get('year', datetime.now().year, type=int) 
    month = request.args.get('month', datetime.now().month, type=int)
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d')) #다른 날짜 클릭 시 해당 날짜의 ToDo를 보여줌

    first_weekday, last_day = calendar.monthrange(year, month)
    display_weekday = (first_weekday + 1) % 7
    empty_days = range(display_weekday) # 달력 1일 시작 전 공백
    range_last_day = range(1, last_day + 1) # 1일부터 마지막 날 리스트

    year_range = range(year - 6, year + 7) # 해당 연도 +- 6년
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""SELECT date, COUNT(*) FROM todos  
                 WHERE user_id=? AND date LIKE ? AND is_completed=0
                 GROUP BY date""", (session['user_id'], f"{year}-{month:02d}-%"))
    todo_counts = {row[0]: row[1] for row in c.fetchall()} # 달력 도트점 

    c.execute("SELECT id, content, is_completed FROM todos WHERE user_id=? AND date=?", 
              (session['user_id'], selected_date))
    todo_list = c.fetchall()
    conn.close()

    return render_template('main.html', # 렌더링한 데이터 Jinja2로 전달
                           now_year=now_year,    # Today 표시
                           now_month=now_month, # Today 표시
                           now_day=now_day, # Today 표시
                           mode=mode, 
                           year=year, 
                           month=month, 
                           range_last_day=range_last_day,
                           empty_days=empty_days, 
                           year_range=year_range,
                           user_name=session.get('user_name'), 
                           todo_counts=todo_counts, 
                           todo_list=todo_list,
                           selected_date=selected_date)

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 유저테이블
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, pw TEXT, name TEXT)''')
    # 할 일 테이블
    # AUTOINCREMENT : 숫자를 자동으로 올려줌 1,2,3....
    c.execute('''CREATE TABLE IF NOT EXISTS todos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id TEXT, 
                  date TEXT, 
                  content TEXT,
                  is_completed INTEGER DEFAULT 0, 
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # POST 사용자가 폼을 보냄
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        name = request.form['name']

        if password != confirm_password:
            flash("비밀번호가 일치하지 않습니다. 다시 확인해 주세요!")
            return redirect(url_for('signup'))

        try:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            # Values에 ? ? ? 넣은 이유 : 보안을 위해서 직접 안넣고 ? 방식을 사용함 : SQL Injection방지
            c.execute("INSERT INTO users (id, pw, name) VALUES (?, ?, ?)", 
                      (username, password, name))
            
            conn.commit()
            conn.close()
            
            flash("회원가입이 완료되었습니다! 로그인해 주세요.")
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError: # 아이디 중복 > 예외처리
            flash("이미 존재하는 아이디입니다.")
            return redirect(url_for('signup'))
        # GET 가입 페이지를 처음 열었을 때
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        # 입력된 아이디/비번이 일치하는 행이 있는지 조회
        c.execute("SELECT * FROM users WHERE id=? AND pw=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            # 인증 성공하면 세션에 유저 정보를 저장하여 로그인 상태 유지
            session['user_id'] = user[0]
            session['user_name'] = user[2] 
            return redirect(url_for('main'))
        else:
            flash("아이디 또는 비밀번호 정보가 틀렸습니다.")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/add_todo', methods=['POST'])
def add_todo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    date = request.form.get('date')
    content = request.form.get('content')
    
    if content:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO todos (user_id, date, content) VALUES (?, ?, ?)", 
                  (user_id, date, content))
        conn.commit()
        conn.close()
        # 작업 후 날짜 정보를 유지하며 메인 페이지로 복귀
    return redirect(url_for('main', date=date, year=date.split('-')[0], month=date.split('-')[1]))

@app.route('/delete_todo/<int:todo_id>')
def delete_todo(todo_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    date = request.args.get('date')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 보안상 작성자와 로그인한 유저가 같은지 한 번 더 체크 한다.(AND user_id=?)
    c.execute("DELETE FROM todos WHERE id=? AND user_id=?", (todo_id, session['user_id']))
    conn.commit()
    conn.close()
    
    return redirect(url_for('main', date=date, year=date.split('-')[0], month=date.split('-')[1]))

@app.route('/edit_todo/<int:todo_id>', methods=['POST'])
def edit_todo(todo_id):
    new_content = request.form.get('new_content')
    date = request.form.get('date')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE todos SET content = ? WHERE id = ?", (new_content, todo_id))
    conn.commit()
    conn.close()
    return redirect(url_for('main', date=date))

@app.route('/check_todo/<int:todo_id>')
def check_todo(todo_id):
    date = request.args.get('date')
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 데이터 수정
    # is_completed : 할 일 완료? O , X [체크박스 표시]
    # O = 1(완료) , X = 0(미완료)
    c.execute("UPDATE todos SET is_completed = 1 - is_completed WHERE id=?", (todo_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('main', date=date, year=date.split('-')[0], month=date.split('-')[1]))

@app.route('/logout')
def logout():
    session.clear() # 모든세션 데이터 삭제 (로그아웃)
    return redirect(url_for('login'))


if __name__ == '__main__':
    init_db() # 시작 시 디비 테이블 점검 < 없으면 디비 실행 안됨
    app.run(debug=True)
     