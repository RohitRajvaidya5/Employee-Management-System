from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
import bcrypt
from flask import Flask, render_template
from dash import Dash, dcc, html, dash_table as dt
import pandas as pd
import mysql.connector
import plotly.graph_objects as go
import dash
from dash.dependencies import Input, Output
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

def create_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')  # This will get the password from the environment
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None

# Queries to fetch data
queries = {
    "avg_salary_by_department": """
        SELECT department, ROUND(AVG(salary), 2) AS avg_salary
        FROM employees
        GROUP BY department;
    """,
    "employee_count_by_department": """
        SELECT department, COUNT(department) AS employee_count
        FROM employees
        GROUP BY department;
    """,
    "avg_salary_by_role": """
        SELECT role, ROUND(AVG(salary), 2) AS avg_salary
        FROM employees
        GROUP BY role;
    """,
    "employee_hiring_trend": """
        SELECT YEAR(hire_date) AS year, COUNT(first_name) AS employee_count
        FROM employees
        WHERE YEAR(hire_date) <= YEAR(CURDATE())
        GROUP BY year
        ORDER BY year;
    """,
}



# Access environment variables
DB_CONFIG = {
    "host": os.getenv('DB_HOST'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME')
}



def fetch_data(query):
    """Execute a query and fetch results."""
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    return results

# Fetch data for figures
avg_salary_data = fetch_data(queries["avg_salary_by_department"])
departments = [row[0] for row in avg_salary_data]
avg_salaries = [row[1] for row in avg_salary_data]

employee_count_data = fetch_data(queries["employee_count_by_department"])
employee_counts = [row[1] for row in employee_count_data]

avg_salary_by_role_data = fetch_data(queries["avg_salary_by_role"])
roles = [row[0] for row in avg_salary_by_role_data]
avg_salaries_by_role = [row[1] for row in avg_salary_by_role_data]

hiring_trend_data = fetch_data(queries["employee_hiring_trend"])
years = [row[0] for row in hiring_trend_data]
employee_counts_by_year = [row[1] for row in hiring_trend_data]

# Create figures
fig_avg_salary = go.Figure(data=[go.Bar(x=departments, y=avg_salaries, marker_color='purple')])
fig_avg_salary.update_layout(
    title='Salary Distribution Across Departments',
    xaxis_title='Department',
    yaxis_title='Average Salary',
    xaxis_tickangle=-45,
    bargap=0.5
)

fig_employee_count = go.Figure(data=[go.Bar(x=departments, y=employee_counts, marker_color='blue')])
fig_employee_count.update_layout(
    title='Employees Per Department',
    xaxis_title='Department',
    yaxis_title='Employee Count',
    xaxis_tickangle=-45,
    bargap=0.6
)

fig_avg_salary_by_role = go.Figure(data=[go.Bar(x=roles, y=avg_salaries_by_role, marker_color='red')])
fig_avg_salary_by_role.update_layout(
    title='Average Salary Per Role',
    xaxis_title='Role',
    yaxis_title='Avg Salary',
    xaxis_tickangle=-45,
    bargap=0.5
)

fig_employee_hiring_trend = go.Figure(data=[go.Bar(x=years, y=employee_counts_by_year, marker_color='purple')])
fig_employee_hiring_trend.update_layout(
    title='Employee Hiring Trend',
    xaxis_title='Year',
    yaxis_title='Employee Count',
    xaxis_tickangle=-45,
    bargap=0.5
)

# Initialize Flask and Dash apps
# app = Flask(__name__)
dash_app = Dash(__name__, server=app, url_base_pathname='/dash/')


# Dash layout
dash_app.layout = html.Div(
    className="dashboard-container",
    children=[
        html.H1("Employee Dashboard", className="heading-class"),
        html.Div(
            className="graph-grid",
            children=[
                dcc.Graph(id='avg-salary-graph', figure=fig_avg_salary, className='graph-class'),
                dcc.Graph(id='employee-count-graph', figure=fig_employee_count, className='graph-class'),
                dcc.Graph(id='avg-salary-per-role-graph', figure=fig_avg_salary_by_role, className='graph-class'),
                dcc.Graph(id='employee-hiring-trend-graph', figure=fig_employee_hiring_trend, className='graph-class'),
                html.H1("Employee Data", className="heading-class"),
                html.Div(
                    dt.DataTable(
                        id='datatable',
                        columns=[],  # Empty for now, will be filled dynamically
                        data=[],  # Will be filled later
                        page_size=10,  # Show 10 rows per page
                        style_table={'overflowX': 'auto'},  # Horizontal scrolling
                        style_cell={'textAlign': 'left', 'padding': '5px'}
                    ),
                    className='div-class-2'  # Adding class here
                )
            ]
        ),
    ],
)

@dash_app.callback(
    [Output('datatable', 'data'),
     Output('datatable', 'columns')],
    [Input('avg-salary-graph', 'id')]  # A more reliable input component that loads on page render
)
def load_data_on_load(_):
    df = fetch_data_from_db()
    data = df.to_dict('records')
    columns = [{'name': col, 'id': col} for col in df.columns]
    return data, columns

def authenticate(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    query = "SELECT password, role FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        stored_password, role = result
        if check_password(stored_password.encode('utf-8'), password):
            return {"status": "success", "role": role}
        else:
            return {"status": "failed", "message": "Incorrect password"}
    return {"status": "failed", "message": "User not found"}

def check_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)

def fetch_data_from_db():
    """Fetch employee data from the database."""
    connection = mysql.connector.connect(**DB_CONFIG)
    query = "SELECT * FROM employees;"
    df = pd.read_sql(query, connection)
    connection.close()
    return df

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:  # Check if the user is already logged in
        if session['role'] == 'admin':
            return redirect(url_for('index'))
        elif session['role'] == 'employee':
            return redirect(url_for('employee_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_info = authenticate(username, password)

        if user_info['status'] == 'success':
            session['logged_in'] = True  # Set the logged-in session
            session['role'] = user_info['role']  # Store user role

            if user_info['role'] == 'admin':
                return redirect(url_for('home'))
            elif user_info['role'] == 'employee':
                return redirect(url_for('employee_dashboard'))
        else:
            return render_template('login.html', error=user_info['message'])

    return render_template('login.html')

@app.route('/index')
def index():
    if 'logged_in' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))  # Redirect to login if not logged in or not admin

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', employees=employees, active_data = 'employee_data')

@app.route('/home')
def home():

    return render_template('SimpleUI.html', active_page='home')


@app.route('/dashboard')
def dash_route():
   return render_template('dashboard.html')  # Serve Dash's app directly


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))
    return render_template('index.html', active_page='logout')


@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        first_name = request.form['first_name'].capitalize()
        last_name = request.form['last_name'].capitalize()
        department = request.form['department'].capitalize()
        role = request.form['role'].capitalize()
        salary = request.form['salary']
        hire_date = request.form['hire_date']
        status = request.form['status'].capitalize()

        conn = create_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO employees (first_name, last_name, department, role, salary, hire_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        data = (first_name, last_name, department, role, salary, hire_date, status)
        cursor.execute(query, data)
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('index'))

    return render_template('add_employee.html')

@app.route('/update_employee/<int:employee_id>', methods=['GET', 'POST'])
def update_employee(employee_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
    employee = cursor.fetchone()

    if request.method == 'POST':
        column_name = request.form['column_name']
        changed_value = request.form['changed_value']

        query = f"UPDATE employees SET {column_name} = %s WHERE employee_id = %s"
        cursor.execute(query, (changed_value, employee_id))
        conn.commit()

        return redirect(url_for('index'))

    cursor.close()
    conn.close()
    return render_template('update_employee.html', employee=employee)

@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    conn = create_connection()
    cursor = conn.cursor()
    query = "DELETE FROM employees WHERE employee_id = %s"
    cursor.execute(query, (employee_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('index'))

@app.route('/register_user', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role').lower()  # Ensure role is lowercase

        # Check if username or password is not provided
        if not username or not password:
            flash("Username and password are required!", "error")
            return render_template('register.html')

        # Hash the password before storing
        hashed_password = hash_password(password)

        # Database connection
        db = create_connection()
        cursor = db.cursor()

        query = "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)"
        try:
            cursor.execute(query, (username, hashed_password, role))
            db.commit()

            flash("User registered successfully!", "success")
            return redirect(url_for('login'))  # Redirect to login page after successful registration

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash(f"Database error: {err}", "error")
        finally:
            cursor.close()
            db.close()

    return render_template('register.html')



def hash_password(password):
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

if __name__ == '__main__':
    app.run(debug=True)


    
