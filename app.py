import sqlite3
import calendar
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret_key_for_session" 

def init_db():
    conn = sqlite3.connect('database.db') 
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, name TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
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
            c.execute("INSERT INTO users (username, password, name) VALUES (?, ?, ?)", 
                      (username, password, name))
            conn.commit()
            conn.close()
            
            flash("회원가입이 완료되었습니다! 로그인해 주세요.")
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError: 
            flash("이미 존재하는 아이디입니다.")
            return redirect(url_for('signup'))

    return render_template('signup.html')
from flask import session 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[2] 
            return redirect(url_for('main'))
        else:
            flash("아이디 또는 비밀번호 정보가 틀렸습니다.")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/main')
def main():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    mode = request.args.get('mode', 'calendar')
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    first_weekday, last_day = calendar.monthrange(year, month)
    display_weekday = (first_weekday + 1) % 7
    empty_days = range(display_weekday)
    range_last_day = range(1, last_day + 1)

    year_range = range(year - 6, year + 7)
    
    return render_template('main.html', 
                           mode=mode, 
                           year=year, 
                           month=month, 
                           range_last_day=range_last_day,
                           empty_days=empty_days, 
                           year_range=year_range,
                           user_id=session['user_id'],
                           selected_date=selected_date)

if __name__ == '__main__':
    app.run(debug=True)
     