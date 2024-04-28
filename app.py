from flask import Flask, render_template, request, redirect, session, url_for
from flask import jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'rms'

# SQLite3 Database Initialization
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL,
            course_code TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            student_roll INTEGER NOT NULL,
            course_id INTEGER,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            marks INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (id,username, password, role) VALUES ((select max(id)+1 from users),?, ?, ?)', (username, password, role))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    return render_template('index.html')

@app.route('/manage_courses', methods=['GET', 'POST'])
def manage_courses():
    if request.method == 'POST':
        if request.form['action'] == 'add_course':
            course_name = request.form['course_name']
            course_code = request.form['course_code']
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO courses (course_name, course_code) VALUES (?, ?)', (course_name, course_code))
            conn.commit()
            conn.close()
        elif request.form['action'] == 'update_course':
            course_id = request.form['course_id']
            course_name = request.form['course_name']
            course_code = request.form['course_code']
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE courses SET course_name=?, course_code=? WHERE id=?', (course_name, course_code, course_id))
            conn.commit()
            conn.close()
        elif request.form['action'] == 'delete_course':
            course_id = request.form['course_id']
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM courses WHERE id=?', (course_id,))
            conn.commit()
            conn.close()

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM courses')
    courses = cursor.fetchall()
    conn.close()
    return render_template('manage_courses.html', courses=courses)

@app.route('/add_result')
def add_result():
    # Fetch courses to populate the dropdown menu
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, course_name, course_code FROM courses')
    courses = cursor.fetchall()
    conn.close()
    return render_template('add_result.html', courses=courses)

@app.route('/get_students')
def get_students():
    course_id = request.args.get('course_id')

    # Fetch students who have joined the selected course
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username
        FROM users 
        WHERE id in (select student_id from students a where course_id = ? 
        and not exists (select student_id from results b where a.course_id = b.course_id
        and a.student_id = b.student_id))
    ''', (course_id,))
    students = cursor.fetchall()
    conn.close()

    # Convert the result to JSON format and return it
    return jsonify(students)

@app.route('/submit_result', methods=['POST'])
def submit_result():
    if request.method == 'POST':
        student_id = request.form['student_id']
        marks = request.form['marks']
        course_id = request.form['course_id']

        # Validate the input if needed
        
        # Insert the result into the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO results (student_id, marks,course_id) VALUES (?, ?,?)', (student_id, marks,course_id))
        conn.commit()
        conn.close()

        # Redirect to a success page or to the student dashboard
        return redirect(url_for('dashboard'))

@app.route('/view_results')
def view_results():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.username, c.course_name, a.marks 
        FROM results a,users b,courses c
        where b.id = a.student_id and c.id = a.course_id
    ''')
    results = cursor.fetchall()
    conn.close()
    return render_template('view_results.html', results=results)

@app.route('/student_view_marks')
def student_view_marks():
    if 'user_id' in session:  # Check if the user is logged in
        student_id = session['user_id']
        
        # Fetch marks for the logged-in student from the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT courses.course_name, courses.course_code, results.marks
            FROM courses
            INNER JOIN results ON courses.id = results.course_id
            WHERE results.student_id = ?
        ''', (student_id,))
        student_marks = cursor.fetchall()
        conn.close()
        
        # Render the template with the student's marks
        return render_template('student_view_marks.html', student_marks=student_marks)
    else:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('login')) 

@app.route('/join_course', methods=['POST'])
def join_course():
    student_id = session['user_id']
    course_id = request.form['course_id']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO students (student_id, course_id) VALUES (?, ?)', (student_id, course_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/student_joined_courses')
def student_joined_courses():
    student_id = session['user_id']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT courses.course_name, courses.course_code
        FROM courses
        INNER JOIN students ON courses.id = students.course_id
        WHERE students.student_id = ?
    ''', (student_id,))
    joined_courses = cursor.fetchall()
    conn.close()
    return render_template('student_joined_courses.html', joined_courses=joined_courses)

@app.route('/student_available_courses')
def student_available_courses():
    student_id = session['user_id']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, course_name, course_code FROM courses where id not in (select course_id from students where student_id = ?)',(student_id,))
    available_courses = cursor.fetchall()
    conn.close()
    return render_template('student_available_courses.html', available_courses=available_courses)


@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        if session['role'] == 'teacher':
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM courses')
            total_courses = cursor.fetchall()
            cursor.execute('SELECT COUNT(*) FROM users where role = "student"')
            total_students = cursor.fetchall()
            cursor.execute('SELECT COUNT(*) FROM results')
            total_results = cursor.fetchall()
            return render_template('teacher_dashboard.html',total_courses=total_courses,total_students=total_students,total_results=total_results)
        elif session['role'] == 'student':
            student_id = session['user_id']
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM students where  student_id=?', (student_id,))
            total_courses_joined = cursor.fetchall()
            cursor.execute('SELECT COUNT(*) FROM courses where id not in (SELECT course_id FROM students where  student_id=?)', (student_id,))
            total_courses_avilable = cursor.fetchall()
            cursor.execute('SELECT COUNT(*) FROM results where  student_id=?', (student_id,))
            total_results_student = cursor.fetchall()
            return render_template('student_dashboard.html',total_courses_joined=total_courses_joined,total_courses_avilable=total_courses_avilable,total_results_student=total_results_student)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
