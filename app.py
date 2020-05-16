from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

app = Flask(__name__)
dburi = 'postgresql://postgres:postgres@localhost/bookshelf'
dburi = 'postgres://clikrrdctqcuis:049f4ccfd236f228dfd29ca261ad4967476f92acdecdecd87ed7ebe964f378d9@ec2-35-169-254-43.compute-1.amazonaws.com:5432/de21dpoptggcfe?sslmode=require'
app.config['SQLALCHEMY_DATABASE_URI']=dburi

db = SQLAlchemy(app)

association_table = db.Table('association',  
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

class Book(db.Model):
    __tablename__="books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(400), nullable=False)
    author = db.Column(db.String(400), nullable=False)
    year = db.Column(db.Integer)
    dewey = db.Column(db.String(20))
    goodreads_url = db.Column(db.String(512))
    series = db.Column(db.String(300))
    status = db.Column(db.String(300))
    categories = db.relationship("Category", secondary=association_table, lazy='subquery',
                        backref=db.backref('books', lazy=True))

    def __init__(self, title, author, year, dewey, goodreads_url, series, status):
        self.title = title
        self.author = author
        self.year = year
        self.dewey = dewey
        self.goodreads_url = goodreads_url
        self.series = series
        self.status = status

class Category(db.Model):
    __tablename__="categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), unique=True)
    
    def __init__(self, name):
        self.name = name

@app.route("/")
@app.route("/home")
@app.route("/index")
def index():
    books = Book.query.order_by(Book.id.desc()).limit(10).all()
    return render_template("index.html", len = len(books), books = books)

@app.route("/books", methods=['POST','GET'])
def books():
    category = None
    if request.method == "POST" and request.form["category"] != "_all_":
        category = request.form["category"]
        books = Book.query.join(Category, Book.categories).filter(Category.name == category).all()
    else:
        books = Book.query.limit(50).all()

    categories = Category.query.order_by(Category.name).all()
    count = Book.query.count()

    return render_template("books.html", count = count, books = books, categories = categories, category = category)

@app.route("/book/<int:id>")
def book(id):
    try:
        book = Book.query.filter(Book.id == id).first()
        return render_template("book.html", book = book)
    except NoResultFound:
        books = Book.query.order_by(Book.id.desc()).limit(10).all()
        return render_template("index.html", len = len(books), books = books)

@app.route("/add_book")
def add_book():
    categories = Category.query.order_by(Category.name).all()

    return render_template("add.html", len = len(categories), categories = categories)

@app.route("/search")
def search():

    return render_template("search.html")


@app.route("/category")
def category():
    categories = Category.query.order_by(Category.name).all()

    return render_template("category.html", len = len(categories), categories = categories)

@app.route("/category_success", methods=['POST'])
def category_success():
    if request.method == "POST":
        category_name = request.form["category_name"]

        category = Category(category_name)
        db.session.add(category)
        db.session.commit()

        categories = Category.query.all()
        return render_template("category.html", len = len(categories), categories = categories)

@app.route("/success", methods=['POST'])
def success():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        year = request.form["year"]
        
        if year == "":
            year = 0

        dewey = request.form["dewey"]
        goodreads_url = request.form["goodreads_url"]
        categories = request.form.getlist("categories")
        series = request.form["series"]
        status = request.form["status"]

        data = Book(title, author, int(year), dewey, goodreads_url, series, "In Bookshelf")
        for cat in categories:
            data.categories.append(Category.query.filter_by(id=cat).first())
        
        db.session.add(data)
        db.session.commit()

        return render_template("success.html")



if __name__ == '__main__':
    app.debug = True
    app.run()