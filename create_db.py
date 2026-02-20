import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
connection = sqlite3.connect("student_grades.db")
cursor = connection.cursor()

# Create Departments table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        dept_id INTEGER PRIMARY KEY,
        dept_name TEXT UNIQUE,
        building TEXT
    )
""")

# Create Students table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY,
        name TEXT,
        dept_id INTEGER,
        enrollment_year INTEGER,
        email TEXT UNIQUE,
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
    )
""")

# Create Instructors table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS instructors (
        instructor_id INTEGER PRIMARY KEY,
        name TEXT,
        dept_id INTEGER,
        email TEXT UNIQUE,
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
    )
""")

# Create Courses table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        course_id INTEGER PRIMARY KEY,
        course_name TEXT,
        course_code TEXT UNIQUE,
        instructor_id INTEGER,
        dept_id INTEGER,
        credits INTEGER,
        FOREIGN KEY (instructor_id) REFERENCES instructors(instructor_id),
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id)
    )
""")

# Create Grades table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        grade_id INTEGER PRIMARY KEY,
        student_id INTEGER,
        course_id INTEGER,
        score INTEGER,
        letter_grade TEXT,
        semester TEXT,
        FOREIGN KEY (student_id) REFERENCES students(student_id),
        FOREIGN KEY (course_id) REFERENCES courses(course_id)
    )
""")

# Insert Departments
departments = [
    (1, "Computer Science", "Building A"),
    (2, "Mathematics", "Building B"),
    (3, "Physics", "Building C"),
    (4, "History", "Building D")
]
cursor.executemany("INSERT OR IGNORE INTO departments VALUES (?, ?, ?)", departments)

# Insert Students
students = [
    (1, "Aman Kumar", 1, 2022, "aman@university.edu"),
    (2, "Anshu Singh", 1, 2023, "anshu@university.edu"),
    (3, "Akshu Patel", 2, 2022, "akshu@university.edu"),
    (4, "Rahul Sharma", 3, 2023, "rahul@university.edu"),
    (5, "Divyansh Gupta", 1, 2021, "divyansh@university.edu"),
    (6, "Nandini Verma", 2, 2023, "nandini@university.edu"),
    (7, "Arjun Desai", 4, 2022, "arjun@university.edu"),
    (8, "Priya Reddy", 3, 2021, "priya@university.edu")
]
cursor.executemany("INSERT OR IGNORE INTO students VALUES (?, ?, ?, ?, ?)", students)

# Insert Instructors
instructors = [
    (101, "Dr. James Smith", 1, "james.smith@university.edu"),
    (102, "Dr. Maria Garcia", 2, "maria.garcia@university.edu"),
    (103, "Dr. Robert Johnson", 3, "robert.johnson@university.edu"),
    (104, "Dr. Sarah Williams", 4, "sarah.williams@university.edu")
]
cursor.executemany("INSERT OR IGNORE INTO instructors VALUES (?, ?, ?, ?)", instructors)

# Insert Courses
courses = [
    (1, "Data Structures", "CS101", 101, 1, 3),
    (2, "Algorithms", "CS201", 101, 1, 4),
    (3, "Calculus I", "MATH101", 102, 2, 4),
    (4, "Linear Algebra", "MATH201", 102, 2, 3),
    (5, "Physics I", "PHYS101", 103, 3, 4),
    (6, "Modern Physics", "PHYS301", 103, 3, 3),
    (7, "World History", "HIST101", 104, 4, 3),
    (8, "American History", "HIST201", 104, 4, 3)
]
cursor.executemany("INSERT OR IGNORE INTO courses VALUES (?, ?, ?, ?, ?, ?)", courses)

# Insert Grades
grades = [
    (1, 1, 1, 95, "A", "Fall 2023"),
    (2, 1, 2, 88, "B", "Spring 2024"),
    (3, 2, 1, 78, "C", "Fall 2023"),
    (4, 2, 3, 82, "B", "Spring 2024"),
    (5, 3, 3, 92, "A", "Fall 2023"),
    (6, 3, 4, 85, "B", "Spring 2024"),
    (7, 4, 5, 88, "B", "Fall 2023"),
    (8, 4, 6, 91, "A", "Spring 2024"),
    (9, 5, 1, 95, "A", "Fall 2023"),
    (10, 5, 2, 89, "B", "Spring 2024"),
    (11, 6, 3, 65, "D", "Fall 2023"),
    (12, 6, 4, 78, "C", "Spring 2024"),
    (13, 7, 7, 88, "B", "Fall 2023"),
    (14, 7, 8, 92, "A", "Spring 2024"),
    (15, 8, 5, 85, "B", "Fall 2023"),
    (16, 8, 6, 90, "A", "Spring 2024")
]
cursor.executemany("INSERT OR IGNORE INTO grades VALUES (?, ?, ?, ?, ?, ?)", grades)

connection.commit()
connection.close()

print("Database created and populated successfully with enhanced schema!")