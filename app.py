from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
app=Flask(__name__); app.secret_key='student-academic-portal-secret-key'
DB_PATH=Path(__file__).resolve().parent/'data.db'
ADMIN_USERNAME='admin'; ADMIN_PASSWORD='admin123'
def db():
 c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init_db():
 c=db(); c.execute('CREATE TABLE IF NOT EXISTS student_data(id INTEGER PRIMARY KEY,name TEXT,branch TEXT,semester INTEGER,total_marks REAL)'); c.commit(); c.close()
def grade(m): return 'A+' if m>=90 else 'A' if m>=80 else 'B+' if m>=70 else 'B' if m>=60 else 'C' if m>=50 else 'F'
def formdata(f):
 try:
  x=(int(f['id']),f['name'].strip(),f['branch'].strip(),int(f['semester']),float(f['total_marks']))
  if not x[1] or not x[2]: return None,'Name and branch are required.'
  if not 1<=x[3]<=12: return None,'Semester must be between 1 and 12.'
  if not 0<=x[4]<=100: return None,'Marks must be between 0 and 100.'
  return x,None
 except: return None,'Please enter valid values.'
@app.route('/',methods=['GET','POST'])
def login():
 err=None
 if request.method=='POST':
  sid=request.form.get('student_id','').strip(); pw=request.form.get('password','').strip(); c=db(); s=c.execute('SELECT * FROM student_data WHERE id=?',(sid,)).fetchone(); c.close()
  if s and pw==f'{sid}@123': session.clear(); session['student_id']=int(sid); return redirect(url_for('dashboard'))
  err='Invalid Student ID or Password.'
 return render_template('login.html',error=err)
@app.route('/dashboard')
def dashboard():
 sid=session.get('student_id')
 if not sid:return redirect(url_for('login'))
 c=db(); s=c.execute('SELECT * FROM student_data WHERE id=?',(sid,)).fetchone(); r=c.execute('SELECT COUNT(*)+1 rank FROM student_data WHERE total_marks>(SELECT total_marks FROM student_data WHERE id=?)',(sid,)).fetchone(); c.close()
 if not s: session.clear(); return redirect(url_for('login'))
 m=float(s['total_marks']); return render_template('dashboard.html',student=s,percentage=m,grade=grade(m),rank=r['rank'])
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
 err=None
 if request.method=='POST':
  if request.form.get('username')==ADMIN_USERNAME and request.form.get('password')==ADMIN_PASSWORD: session.clear(); session['admin']=True; return redirect(url_for('admin'))
  err='Invalid admin username or password.'
 return render_template('admin_login.html',error=err)
@app.route('/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('admin_login'))
@app.route('/admin')
def admin():
 if not session.get('admin'): return redirect(url_for('admin_login'))
 c=db(); students=c.execute('SELECT * FROM student_data ORDER BY id').fetchall(); c.close(); return render_template('admin.html',students=students)
@app.route('/admin/add',methods=['POST'])
def add():
 if not session.get('admin'): return redirect(url_for('admin_login'))
 x,e=formdata(request.form)
 if e: flash(e,'error'); return redirect(url_for('admin'))
 c=db()
 if c.execute('SELECT 1 FROM student_data WHERE id=?',(x[0],)).fetchone(): c.close(); flash('Student ID already exists.','error'); return redirect(url_for('admin'))
 c.execute('INSERT INTO student_data VALUES(?,?,?,?,?)',x); c.commit(); c.close(); flash(f'Student {x[0]} added successfully.','success'); return redirect(url_for('admin'))
@app.route('/admin/update/<int:sid>',methods=['POST'])
def update(sid):
 if not session.get('admin'): return redirect(url_for('admin_login'))
 x,e=formdata(request.form)
 if e: flash(e,'error'); return redirect(url_for('admin'))
 c=db()
 if x[0]!=sid and c.execute('SELECT 1 FROM student_data WHERE id=?',(x[0],)).fetchone(): c.close(); flash('New Student ID already exists.','error'); return redirect(url_for('admin'))
 c.execute('UPDATE student_data SET id=?,name=?,branch=?,semester=?,total_marks=? WHERE id=?',(*x,sid)); c.commit(); c.close(); flash('Student record updated successfully.','success'); return redirect(url_for('admin'))
@app.route('/admin/delete/<int:sid>',methods=['POST'])
def delete(sid):
 if not session.get('admin'): return redirect(url_for('admin_login'))
 c=db(); c.execute('DELETE FROM student_data WHERE id=?',(sid,)); c.commit(); c.close(); flash(f'Student {sid} deleted.','success'); return redirect(url_for('admin'))
if __name__=='__main__': init_db(); app.run(debug=True)
