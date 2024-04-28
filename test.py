import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('SELECT id, course_name, course_code FROM courses')
available_courses = cursor.fetchall()
conn.close()
print(available_courses)