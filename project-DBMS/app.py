from flask import Flask, render_template, request, redirect, jsonify
import mysql.connector

app = Flask(__name__)

# ---------------- DATABASE CONNECTION ----------------

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="rootsql",
    database="smart_lost_found"
)

cursor = db.cursor(dictionary=True)


# ---------------- ACTIVITY LOGGER ----------------

def log_activity(email, action):

    cursor.execute(
        "INSERT INTO activities (user_email, action) VALUES (%s,%s)",
        (email, action)
    )

    db.commit()


# ---------------- NOTIFICATION LOGGER ----------------

def add_notification(message):

    cursor.execute(
        "INSERT INTO notifications (message) VALUES (%s)",
        (message,)
    )

    db.commit()


# ---------------- HOME ----------------

@app.route('/')
def home():
    return render_template("login.html")


# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():

    role = request.form['role']
    email = request.form['email']
    password = request.form['password']

    if role == "admin":

        if email == "admin@gmail.com" and password == "admin":

            log_activity(email, "Logged in as Admin")

            return redirect(f"/admin?email={email}")

        return "Invalid Admin Login"

    if role == "student":

        log_activity(email, "Logged in as Student")

        return redirect(f"/user?email={email}")


# ---------------- USER DASHBOARD ----------------

@app.route('/user')
def user_dashboard():

    email = request.args.get("email")

    log_activity(email, "Opened User Dashboard")

    return render_template("user_dashboard.html", email=email)


# ---------------- ADMIN DASHBOARD ----------------

@app.route('/admin')
def admin_dashboard():

    email = request.args.get("email")

    log_activity(email, "Opened Admin Dashboard")

    return render_template("admin_dashboard.html", email=email)


# ---------------- REPORT ITEM ----------------

@app.route('/report', methods=['GET','POST'])
def report():

    email = request.args.get("email")

    if request.method == "POST":

        item_name = request.form['item_name']
        description = request.form['description']
        category = request.form['category']
        location = request.form['location']

        cursor.execute(
            """
            INSERT INTO items
            (item_name, description, category, location, date_reported, status, user_email)
            VALUES (%s,%s,%s,%s,CURDATE(),'lost',%s)
            """,
            (item_name, description, category, location, email)
        )

        db.commit()

        log_activity(email, f"Reported item {item_name}")

        add_notification(f"{email} reported item {item_name}")

        return redirect(f"/user?email={email}")

    return render_template("report_item.html", email=email)


# ---------------- SEARCH ITEMS ----------------

@app.route('/search', methods=['GET','POST'])
def search():

    email = request.args.get("email")

    log_activity(email, "Opened Search Page")

    items = None
    message = None

    if request.method == "POST":

        keyword = request.form['keyword']

        cursor.execute(
            "SELECT * FROM items WHERE item_name LIKE %s",
            ('%' + keyword + '%',)
        )

        items = cursor.fetchall()

        if len(items) == 0:
            message = "Item is not Available"

    else:

        cursor.execute("SELECT * FROM items")

        items = cursor.fetchall()

    return render_template(
        "search_item.html",
        items=items,
        message=message,
        email=email
    )


# ---------------- CLAIM PAGE ----------------

@app.route('/claim')
def claim():

    email = request.args.get("email")

    log_activity(email, "Opened Claim Page")

    cursor.execute("SELECT * FROM items WHERE status='lost'")

    items = cursor.fetchall()

    return render_template("claim_item.html", items=items, email=email)


# ---------------- CLAIM REQUEST ----------------

@app.route('/claim_item/<int:item_id>')
def claim_item(item_id):

    email = request.args.get("email")

    cursor.execute(
        """
        INSERT INTO claims (item_id, user_email, claim_date, approval_status)
        VALUES (%s,%s,CURDATE(),'pending')
        """,
        (item_id,email)
    )

    db.commit()

    log_activity(email, f"Requested claim for item {item_id}")

    add_notification(f"{email} requested claim for item {item_id}")

    return redirect(f"/claim?email={email}")


# ---------------- ADMIN APPROVE CLAIM ----------------

@app.route('/approve_claim/<int:item_id>')
def approve_claim(item_id):

    cursor.execute(
        "UPDATE claims SET approval_status='approved' WHERE item_id=%s",
        (item_id,)
    )

    cursor.execute(
        "UPDATE items SET status='claimed' WHERE item_id=%s",
        (item_id,)
    )

    db.commit()

    return redirect("/claimed")


# ---------------- CLAIMED ITEMS ----------------

@app.route('/claimed')
def claimed():

    email = request.args.get("email")

    cursor.execute(
        """
        SELECT items.item_name, items.location, claims.claim_date, claims.approval_status
        FROM claims
        JOIN items ON claims.item_id = items.item_id
        """
    )

    data = cursor.fetchall()

    return render_template("claimed_items.html", data=data, email=email)


# ---------------- MY REPORTED ITEMS ----------------

@app.route('/my_reports')
def my_reports():

    email = request.args.get("email")

    cursor.execute(
        "SELECT * FROM items WHERE user_email=%s",
        (email,)
    )

    data = cursor.fetchall()

    return render_template("my_reports.html", items=data, email=email)


# ---------------- MY CLAIMS ----------------

@app.route('/my_claims')
def my_claims():

    email = request.args.get("email")

    cursor.execute(
        """
        SELECT items.item_name, claims.approval_status
        FROM claims
        JOIN items ON claims.item_id = items.item_id
        WHERE claims.user_email=%s
        """,
        (email,)
    )

    data = cursor.fetchall()

    return render_template("my_claims.html", claims=data, email=email)


# ---------------- ACTIVITY SUMMARY ----------------

@app.route('/activity_summary')
def activity_summary():

    email = request.args.get("email")

    cursor.execute(
        """
        SELECT action, activity_time
        FROM activities
        WHERE user_email=%s
        ORDER BY activity_time DESC
        """,
        (email,)
    )

    data = cursor.fetchall()

    return render_template("activity_summary.html", activities=data, email=email)


# ---------------- LIVE ACTIVITY ----------------

@app.route('/live_activity')
def live_activity():

    cursor.execute(
        """
        SELECT user_email, action, activity_time
        FROM activities
        ORDER BY activity_time DESC
        LIMIT 50
        """
    )

    activities = cursor.fetchall()

    return render_template("live_activity.html", activities=activities)


# ---------------- LIVE ACTIVITY API ----------------

@app.route('/api/live_activity')
def api_live_activity():

    cursor.execute(
        """
        SELECT user_email, action, activity_time
        FROM activities
        ORDER BY activity_time DESC
        LIMIT 20
        """
    )

    data = cursor.fetchall()

    return jsonify({"activities": data})


# ---------------- NOTIFICATIONS API ----------------

@app.route('/api/notifications')
def get_notifications():

    cursor.execute(
        """
        SELECT message, created_at
        FROM notifications
        ORDER BY created_at DESC
        LIMIT 5
        """
    )

    data = cursor.fetchall()

    return jsonify({"notifications": data})


# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    app.run(debug=True)