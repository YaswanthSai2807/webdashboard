from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from config import DB_CONFIG, SECRET_KEY

app = Flask(__name__)
CORS(app)

app.secret_key = SECRET_KEY  # Needed for flash messages

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard", methods=['GET'])
def dashboard():
    # Access session data correctly
    username = session.get('username')
    user_id=session.get('user_id')  
    if not user_id:
        return redirect(url_for('home'))  # Redirect to login page if no username in session
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT dashboard_link,dashboard_name FROM dashboards WHERE user_id=%s", (user_id,))
    dashboard_data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("dashboard.html",username=username, user_id=user_id, dashboard_data=dashboard_data)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm-password")
        role = request.form.get("role")

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return render_template("register.html")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if the username already exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash("User already exists. Kindly login.", "danger")
                return redirect(url_for("register"))

            # Insert new user
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed_password, role),
            )
            conn.commit()
            flash("Registration successful!", "success")
            return redirect(url_for("home"))  # Redirect to login page after successful registration

        except pymysql.Error as err:
            flash(f"Error: {str(err)}", "danger")
            return redirect(url_for("register"))
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id, password, role FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    session['user_id']=user['id']
    if user and check_password_hash(user["password"], password):
        flash("Login successful!", "success") 
        session["username"] = username  # Store username in session
        return redirect(url_for('dashboard'))  # No need to pass username in URL
    
    flash("Invalid credentials!", "danger") 
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()  # Clear the session data
    return redirect(url_for('home'))  # Redirect to the home page (login page)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
