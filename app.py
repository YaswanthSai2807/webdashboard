from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from config import users_db
from datetime import datetime
from html.parser import HTMLParser

app = Flask(__name__)
CORS(app)

app.secret_key = "SECRET_KEY"

def get_db_connection():
    return pymysql.connect(**users_db )

def html_to_text(html_string):
    text = ""
    class TextExtractor(HTMLParser):
        def handle_data(self, data):
            nonlocal text  # Access the outer scope 'text' variable
            text += data
    parser = TextExtractor()
    parser.feed(html_string)
    return text

@app.route("/")
def home():
    return render_template("index.html")

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
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash("User already exists. Kindly login.", "danger")
                return redirect(url_for("register"))

            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed_password, role))
            conn.commit()
            flash("Registration successful!", "success")
            return redirect(url_for("login"))

        except pymysql.Error as err:
            flash(f"Error: {str(err)}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    
    if not username or not password:
        flash("Enter the username and password", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id, password, role, is_temporary_password FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["username"] = username
        session["password"] = password

        if user["is_temporary_password"]:
            flash("You must update your password before accessing the portal.", "warning")
            return redirect(url_for("change_password"))  

        flash("Login successful!", "success")
        return redirect(url_for("dashboard"))

    flash("Invalid credentials!", "danger")
    return redirect(url_for("home"))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("home"))

    username = session["username"]
    temp_password = session["password"]

    if request.method == "POST":
        current_password = request.form.get("current-password")
        new_password = request.form.get("new-password")
        confirm_password = request.form.get("confirm-new-password")
        role = request.form.get("role")

        if current_password != temp_password:
            flash("Entered Current Password is Invalid", "danger")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        hashed_password = generate_password_hash(new_password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET password=%s, is_temporary_password=%s, role=%s WHERE id=%s", (hashed_password, False, role, session["user_id"]))
            conn.commit()
            flash("Password updated successfully, Kindly Login", "success")
            return redirect(url_for("home"))

        except pymysql.Error as err:
            flash(f"Error updating password: {str(err)}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("change_password.html", username=username)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')

        if not username:
            flash("Please enter a username.", "danger")
            return redirect(url_for('forgot_password'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT id, username FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                user_id = user["id"]  # Extract user_id from the database
                
                subject = f"Password Reset Request for {username}"
                message_body = "Hi Support Team, I forgot my password. Kindly update my password."

                # Insert into support_emails table
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO support_emails (user_id, username, subject, message) VALUES (%s, %s, %s, %s)",
                        (user_id, username, subject, message_body)
                    )
                    conn.commit()
                    flash("Your request has been sent to the support team.", "success")

                    # Uncomment the following lines to enable email sending in the future
                    """
                    support_email = "saiyaswanthabbaraju@gmail.com"
                    if forgot_email(support_email, subject, message_body):
                        flash("Your request has been sent to the support team.", "success")
                    else:
                        flash("Failed to send email. Please try again later.", "danger")
                    """

                except pymysql.Error as err:
                    flash(f"Database Error: {str(err)}", "danger")
                finally:
                    cursor.close()
                    conn.close()
            else:
                flash("No username found.", "danger")

        except Exception as e:
            flash("An error occurred. Please try again later.", "danger")
            print(f"Error: {str(e)}")

        return redirect(url_for('forgot_password'))

    return render_template('forgot.html')

@app.route("/profile")
def profile():
    username = session.get('username', 'Guest')  # Handling case where user is not logged in
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
    return render_template("profile.html", username=username, timestamp=timestamp)

@app.route("/dashboard", methods=['GET'])
def dashboard():
    username = session.get('username')
    user_id = session.get('user_id')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
    
    if not user_id:
        return redirect(url_for('home'))  # Redirect if not logged in
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch all projects assigned to the user
    cursor.execute("SELECT project_id, project_name FROM projects WHERE user_id=%s", (user_id,))
    projects = cursor.fetchall()

    # Fetch dashboards based on project association
    cursor.execute("SELECT dashboard_name, dashboard_link, project_id FROM dashboards WHERE user_id=%s", (user_id,))
    dashboards = cursor.fetchall()

    # Count unread emails
    cursor.execute("SELECT count(*) AS unread FROM user_emails WHERE is_read=0 AND user_id=%s", (user_id,))
    mails = cursor.fetchone()["unread"]

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        username=username,
        user_id=user_id,
        projects=projects,
        dashboards=dashboards,
        mails=mails,
        timestamp=timestamp
    )

@app.route('/dashboard_view')
def dashboard_view():
    username = session.get('username')
    user_id = session.get('user_id')  
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp

    if not user_id:
        return redirect(url_for('home'))  # Redirect to login page if not logged in

    dashboard_name = request.args.get('dashboard_name')  # Get selected dashboard name
    project_id = request.args.get('project_id')  # Get selected project ID (if any)

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch dashboards based on project or all non-project dashboards
    if project_id:
        cursor.execute("SELECT dashboard_link, dashboard_name FROM dashboards WHERE user_id=%s AND project_id=%s", 
                       (user_id, project_id))
    else:
        cursor.execute("SELECT dashboard_link, dashboard_name FROM dashboards WHERE user_id=%s AND (project_id IS NULL OR project_id=0)", 
                       (user_id,))

    dashboard_data = cursor.fetchall()

    cursor.close()
    conn.close()

    if not dashboard_data:
        return "No dashboards found", 404  # No dashboards exist for this user

    # Find the selected dashboard if specified
    selected_dashboard = next((d for d in dashboard_data if d["dashboard_name"] == dashboard_name), None)

    # If a `dashboard_name` was given but not found, return an error instead of defaulting
    if dashboard_name and not selected_dashboard:
        return "Dashboard not found", 404

    # If no dashboard is selected, use the first available one
    if not selected_dashboard:
        selected_dashboard = dashboard_data[0]

    return render_template("dashboard_view.html", 
                           username=username, 
                           dashboard_data=dashboard_data, 
                           selected_dashboard=selected_dashboard, timestamp=timestamp)


@app.route('/support')
def support():
    username = session.get('username')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
    return render_template("support.html",username=username, timestamp=timestamp)

@app.route('/send-email', methods=['POST'])
def handle_email():
    """Handle email storing request without sending."""
    if 'username' not in session:
        flash("Please log in to send emails.", "danger")
        return redirect(url_for("login"))
    
    user_id = session['user_id']
    username = session['username']
    to_email = "saiabbaraju2807@gmail.com"  # Example recipient email
    subject = request.form['subject']
    body = request.form['message']

    # Store email in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message_body = html_to_text(body)  # Convert HTML to plain text if necessary
        cursor.execute(
            "INSERT INTO support_emails (user_id, username, subject, message) VALUES (%s, %s, %s, %s)",
            (user_id, username, subject, message_body)
        )
        conn.commit()
        flash("E-Mail sent successfully!", "success")

        # Uncomment the following lines to enable email sending in the future
        """
        if send_email(to_email, f"{username}: {subject}", body):
            flash("Email sent successfully!", "success")
        else:
            flash("Failed to send email. Please authenticate first.", "danger")
        """

    except pymysql.Error as err:
        flash(f"Error: {str(err)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("dashboard"))

@app.route('/sent')
def sent():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
    user_id = session.get('user_id')  

    if not user_id:
        return redirect(url_for('sent'))
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch all dashboards for sidebar
    cursor.execute("SELECT subject, message,sent_at FROM support_emails WHERE user_id=%s ORDER BY sent_at DESC", (user_id,))
    sent_data = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("sent.html", sent_data=sent_data, timestamp=timestamp)

@app.route('/inbox')
def inbox():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
    user_id = session.get('user_id')  
    conn=get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM user_emails WHERE user_id=%s ORDER BY sent_at DESC",(user_id,))
    inbox = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("inbox.html", inbox=inbox, timestamp=timestamp)

@app.route('/inbox/<int:email_id>')
def view_email(email_id):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Formatting timestamp
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch email details
    cursor.execute("SELECT * FROM user_emails WHERE id = %s", (email_id,))
    email = cursor.fetchone()

    # Mark email as read
    if email and not email['is_read']:
        cursor.execute("UPDATE user_emails SET is_read = 1 WHERE id = %s", (email_id,))
        conn.commit()

    cursor.close()
    conn.close()

    if email:
        return render_template("email_detail.html", email=email, timestamp=timestamp)
    else:
        return "Email not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 