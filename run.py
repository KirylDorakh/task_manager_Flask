import os
from datetime import datetime, date
from flask import Flask, session, render_template, redirect, request, url_for

# Session
from flask_session import Session

# DB Migrations
from flask_migrate import Migrate

# ENV
from dotenv import load_dotenv

# For DB errors
from sqlalchemy.exc import IntegrityError

# Email
from flask_mail import Mail, Message

# Import db from extensions
from extensions import db

# Import models
from models import User, Task, Project
from enums import TaskStatus

app = Flask(__name__)

# Load environment variables from .env
load_dotenv()

# Use environment variables
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# Configurate SQLAchemy database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

# initialize the database
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Email config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")

mail = Mail(app)


# Main page
@app.route("/")
def index():
    if session.get("username"):

        # Query database for user's information
        user = User.query.filter_by(username=session.get("username")).first()

        if user is None:
            # If the user is not found, clear the session and redirect to login
            session.clear()
            return redirect(url_for("login"))
        
        # For tasks
        project_id = request.args.get("project_id")
        
        # Filter for tasks
        query = Task.query.filter_by(user_id=user.id, completed=False)

        if project_id is None:
            query = query.filter(Task.project_id.is_(None))
        else:
            project_id = int(project_id) 
            query = query.filter_by(project_id=project_id)  
        tasks = query.all()      

        # today = date.today()
        # tasks = Task.query.filter(Task.due_date == today).all()

        # For sidebar
        projects = Project.query.filter_by(user_id=user.id).all()

        # print("Logged in user session:", dict(session))
        print(project_id, type(project_id))

        # To show completed tasks
        if "completed" in request.args:
            tasks = Task.query.filter_by(user_id=user.id, completed=True).all()
            project_id = "completed"

        return render_template("index.html", tasks=tasks, projects=projects, active_project_id=project_id)
    else:   
        return render_template("index.html")


# User
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Check the data from form
        username = request.form.get('username')
        password = request.form.get('password')

        print("Login POST received for user:", username)  # Debug log

        # Ensure username was submitted
        if not username:
            return render_template("login.html", apology="Please, write an username")

        # Ensure password was submitted
        elif not password:
            return render_template("login.html", apology="Please, write a password")

        # Query database for username
        user = User.query.filter_by(username=username).first()

        # Ensure username exists and password is correct
        if not user:
            return render_template("login.html", apology="Wrong username")
        elif not user.check_password(password):
            return render_template("login.html", apology="Wrong password")


        # Remember which user has logged in
        session["username"] = user.username
        session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        print("Index route called", session)
        return render_template("login.html")
    

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")   


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":

        # Validate submission
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return render_template("register.html", apology="Please, write an username")

        # Ensure password was submitted
        if not password or not confirmation:
            return render_template("register.html", apology="Please, write a password")
        
        # Validate submission
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template("register.html", apology="Username already taken")
        if password != confirmation:
            return render_template("register.html", apology="Passwords do not match")
        
        # Remember user
        else:
            try:
                new_user = User(username=username)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return render_template("register.html", apology="DB error")
            else:
                return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/change_password", methods=["GET", "POST"])
def change_password():

    # If method POST
    if request.method == "POST":

        # If user is not log in
        if not session.get("username"):
            username = request.form.get("username")

            # Ensure username was submitted
            if not username:
                return render_template("change_password.html",  apology="Please, write an username")

            # Query database for user's information
            user = User.query.filter_by(username=username).first()

            # Ensure username exists
            if not user:
                return render_template("change_password.html",  apology="Please, write a correct username")
        
        else:
            user = User.query.filter_by(username=session["username"]).first()

            # Ensure username exists
            if not user:
                return render_template("change_password.html",  apology="Invalid user")

        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")

        # Ensure old password was submitted
        if not old_password:
            return render_template("change_password.html", apology="must provide old password")

        # Ensure old password is correct
        elif not user.check_password(old_password):
            return render_template("change_password.html", apology="invalid old password")

        # Ensure mew password was submitted
        elif not new_password:
            return render_template("change_password.html", apology="must provide new password")

        # Ensure confirmation was submitted
        elif not confirmation:
            return render_template("change_password.html", apology="must provide confirmation of new password")

        # Ensure new password and confirmation match
        elif new_password != confirmation:
            return render_template("change_password.html", apology="new password and new password confirmation don't match")


        # Change password and commit the update
        try:
            user.set_password(new_password)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return render_template("change_password.html", apology="DB error: " + str(e))
        else:
            # Logout user
            session.clear()
            # Redirect to login page
            return render_template("login.html", success="Password was changed! Please log in with your new password")

    # If method GET and user is logged in
    elif session.get("username"):
        return render_template("change_password.html")

    # If method GET and user is not logged in
    return render_template("change_password.html")


# Tasks
@app.route("/create_task", methods=["GET", "POST"])
def create_task():
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect("/login")
    
    # user = User.query.filter_by(username=session.get("username")).first()
    projects = Project.query.filter_by(user_id=user.id).all()

    if request.method == "POST":
        # Data from form
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        # priority = request.form.get("priority")
        # status = request.form.get("status")
        project_id = request.form.get("project_id")  
        project_id = int(project_id) if project_id and project_id != "None" else None 

        user_id = user.id

        due_date = datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None

        # Prepare data and write to DB
        new_task = Task(title=title, 
                        description=description, 
                        user_id=user_id, 
                        due_date=due_date, 
                        project_id=project_id
                        )

        try:
            db.session.add(new_task)
            db.session.commit()
        except Exception as e:
            return render_template("task/create_task.html", apology=f'DB Error: {str(e)}')
        else:
            return redirect("/") 
    return render_template("/task/create_task.html", projects=projects)


@app.route("/edit_task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect("/login")
    
    projects = Project.query.filter_by(user_id=user.id).all()
    task = Task.query.get(task_id)

    if request.method=="POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        project_id = request.form.get("project_id") 
        project_id = int(project_id) if project_id and project_id != "None" else None  
        user_id = user.id
        due_date = datetime.strptime(due_date, "%Y-%m-%d").date() if due_date else None

        try:
            task.title = title 
            task.description = description 
            task.due_date = due_date
            task.project_id = project_id

            db.session.commit()
        except Exception as e:
            return render_template("task/edit_task.html", apology=f'DB Error: {str(e)}' )
        else:
            return redirect("/") 

    return render_template("task/edit_task.html", task=task, projects= projects)


@app.route("/mark_done/<int:task_id>", methods=["POST"])
def mark_done(task_id):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect("/login")
    
    task = Task.query.get(task_id)

    if task and task.user_id == user.id:
        try:
            task.completed = True
            db.session.commit()
        except Exception as e:
            return render_template("task/edit_task.html", apology=f'DB Error: {str(e)}' )

    return redirect("/")


@app.route("/mark_done_ajax/<int:task_id>", methods=["POST"])
def mark_done_ajax(task_id):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect("/login")

    task = Task.query.get(task_id)
    if not task or task.user_id != user.id:
        return {"error": "Task not found or forbidden"}, 403
    
    try:
        task.completed = True
        db.session.commit()
        return {"message": "Task marked as completed"}, 200
    except Exception as e:
        return {"error": str(e)}, 500
    

@app.route("/mark_undone_ajax/<int:task_id>", methods=["POST"])
def mark_undone_ajax(task_id):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect("/login")
    
    task = Task.query.get(task_id)
    if not task or task.user_id != user.id:
        return {"error": "Task not found or forbidden"}, 403
    
    try:
        task.completed = False
        db.session.commit()
        return {"message": "Task marked as not completed"}, 200
    except Exception as e:
        return {"error": str(e)}, 500



@app.route("/delete_task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect("/login")
    
    task = Task.query.get(task_id)

    if task and task.user_id == user.id:
        try:
            db.session.delete(task)
            db.session.commit()
        except Exception as e:
            return render_template("task/edit_task.html", task=task, apology=f"Error deleting task: {str(e)}")

    return redirect("/")    
    

# Projects
@app.route("/create_project", methods=["GET", "POST"])
def create_project():
    user = User.query.get(session.get("user_id"))
    if not user:
        return redirect("/login")

    user = User.query.filter_by(username=session.get("username")).first()

    if request.method=="POST":

        # Data from form
        name = request.form.get("name")
        description = request.form.get("description")

        user_id = user.id

        # Prepare data and write to DB
        new_project = Project(name=name, description=description, user_id=user_id)

        try:
            db.session.add(new_project)
            db.session.commit()
        except Exception as e:
            return render_template("create_project.html", apology=f'DB Error: {str(e)}')
        else:
            return redirect("/") 

    return render_template("create_project.html")


# Contatc
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        subject = request.form.get("subject")
        message = request.form.get("message")

        msg = Message(subject=f"Subject: {subject}",
                      sender=email,
                      recipients=[os.getenv("MAIL_USERNAME")],
                      body=f"User: {name}\nEmail: {email}\n{message}")
        
        try:
            mail.send(msg)
            return render_template("contact.html", success="Your message has been sent! Thank you!")
        except Exception as e:
            return render_template("contact.html", error="Error sending message" + str(e))

        
    
    return render_template("contact.html")


if __name__ == "__main__":
    app.run()
