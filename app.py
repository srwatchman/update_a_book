# This file contains an example Flask-User application.
# To keep the example simple, we are applying some unusual techniques:
# - Placing everything in one file
# - Using class-based configuration (instead of file-based configuration)
# - Using string-based templates (instead of file-based templates)

import datetime
from enum import unique
from flask import Flask, request, render_template_string, render_template
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from flask_user import current_user, login_required, roles_required, UserManager, UserMixin
from werkzeug.utils import redirect


# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///basic_app.sqlite'    # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False    # Avoids SQLAlchemy warning

    # Flask-Mail SMTP server settings
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = 'swatchman_weber@gmail.com'
    MAIL_PASSWORD = 'Blue2015'
    MAIL_DEFAULT_SENDER = '"MyApp" <noreply@example.com>'

    # Flask-User settings
    USER_APP_NAME = "Flask-User Basic App"      # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = True        # Enable email authentication
    USER_ENABLE_USERNAME = False    # Disable username authentication
    USER_EMAIL_SENDER_NAME = USER_APP_NAME
    USER_EMAIL_SENDER_EMAIL = "noreply@example.com"


def create_app():
    """ Flask application factory """
    
    # Create Flask app load app.config
    app = Flask(__name__)
    app.config.from_object(__name__+'.ConfigClass')

    # Initialize Flask-BabelEx
    babel = Babel(app)

    # Initialize Flask-SQLAlchemy
    db = SQLAlchemy(app)

    # Define the User data-model.
    # NB: Make sure to add flask_user UserMixin !!!
    class User(db.Model, UserMixin):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')

        # User authentication information. The collation='NOCASE' is required
        # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
        email = db.Column(db.String(255, collation='NOCASE'), nullable=False, unique=True)
        email_confirmed_at = db.Column(db.DateTime())
        password = db.Column(db.String(255), nullable=False, server_default='')

        # User information
        first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
        last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')

        # Define the relationship to Role via UserRoles
        roles = db.relationship('Role', secondary='user_roles')

    # Define the Role data-model
    class Role(db.Model):
        __tablename__ = 'roles'
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(50), unique=True)

    # Define the UserRoles association table
    class UserRoles(db.Model):
        __tablename__ = 'user_roles'
        id = db.Column(db.Integer(), primary_key=True)
        user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
        role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

    # Setup Flask-User and specify the User data-model
    user_manager = UserManager(app, db, User)

    class Book_data(db.Model):
        __tablename__ = 'book_data'
        id = db.Column(db.Integer(), primary_key=True)
        author = db.Column(db.String(20), unique=True)
        title = db.Column(db.String(20), unique=True)
        description = db.Column(db.String(50), unique=True)

    # Create all database tables
    db.create_all()

    # Create 'member@example.com' user with no roles
    if not User.query.filter(User.email == 'member@example.com').first():
        user = User(
            email='member@example.com',
            email_confirmed_at=datetime.datetime.utcnow(),
            password=user_manager.hash_password('Password1'),
        )
        db.session.add(user)
        db.session.commit()

    # Create 'admin@example.com' user with 'Admin' and 'Agent' roles
    if not User.query.filter(User.email == 'admin@example.com').first():
        user = User(
            email='admin@example.com',
            email_confirmed_at=datetime.datetime.utcnow(),
            password=user_manager.hash_password('Password1'),
        )
        user.roles.append(Role(name='Admin'))
        user.roles.append(Role(name='Agent'))
        db.session.add(user)
        db.session.commit()

    # The Home page is accessible to anyone
    @app.route('/')
    def home_page():
        return render_template('index.html')

    # The Admin page requires an 'Admin' role.
    @app.route('/admin')
    @roles_required('Admin')    # Use of @roles_required decorator
    def admin_page():
        return render_template('admin.html')

    @app.route('/erase_DB')
    @roles_required('Admin') 
    def eraseDB():
        sqlQ = db.engine.execute('DELETE FROM Book',commit=True)
        return '<h1>Erased!</h1>'

    @app.route('/seedDB')
    @roles_required('Admin') 
    def seedDB():
        sqlQ = db.engine.execute('DROP TABLE IF EXISTS Book',commit=True)

        sqlQuery = db.engine.execute('CREATE TABLE Book (author TEXT,title TEXT, description TEXT)',commit=True)

        sqlQuery2 = db.engine.execute('INSERT INTO Book (author,title, description) VALUES ("Mary Shelly","Frankenstein", "A horror story written by a romantic.")',commit=True)
        sqlQuery2 = db.engine.execute('INSERT INTO Book (author,title, description) VALUES ("Henry James","The Turn of the Screw", "Another British horror story")',commit=True)
        sqlQuery2 = db.engine.execute('INSERT INTO Book (author,title, description) VALUES ("Max Weber","The Protestant Work Ethic and The Spirit", "A classic early 20th Century sociology text")',commit=True)
        sqlQuery2 = db.engine.execute('INSERT INTO Book (author,title, description) VALUES ("Robert Putnam","Bowling Alone", "A classic late 20th Century sociology text")',commit=True)

        booksQuery = db.engine.execute('SELECT rowid, * FROM Book')
        for book in booksQuery:
            print(book['rowid'])
            print(book['author'])

        return '<h1>DB Seeded!</h1>'

    @app.route('/contact')
    def contact_page():
        #return 'The contact page'
        return render_template('contacts.html')

    @app.route('/all_books')
    def all_books():
        books = db.engine.execute('SELECT * FROM Book')

        my_list_of_books = [row for row in books]
        return render_template('all_books.html', books=my_list_of_books)

    @app.route('/add_book/<book_id>', methods={'GET','POST'})
    @login_required
    def add_book(book_id):

        book = Book_data.query.filter(Book_data.id == book_id).first()

        if request.method == 'GET':
            request.form.author = book.author
            request.form.title = book.title
            request.form.description = book.description

        elif request.method == 'POST':
            book.author = request.form['author']
            book.title = request.form['title']
            book.description = request.form['description']

            db.session.add(book_id)
            db.session.commit()
            return redirect('home_page')


            #returnStatus = db.engine.execute('INSERT INTO Book (author, title, description) VALUES (?, ?, ?)', (author, title, description),commit=True)
            #return render_template('add_book.html', book_title=title)
        return render_template('add_book.html', author = book.author, title = book.title, description = book.description)


    return app


# Start development web server
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
