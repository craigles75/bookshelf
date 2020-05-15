from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

app = Flask(__name__)
dburi = 'postgresql://postgres:postgres@localhost/bookshelf'
#dburi = 'postgres://nlqdivywrpomql:de868e8988b7872516ae01823ae3858468d1e400b2f0e47be17aa3dea613bc37@ec2-54-81-37-115.compute-1.amazonaws.com:5432/dca309g7qh6vf0?sslmode=require'
app.config['SQLALCHEMY_DATABASE_URI']=dburi

db = SQLAlchemy(app)

association_table = db.Table('association',  
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

def check_if_cat_exists(cat):
    existing_cat = Category.query.filter_by(id=cat).first()
    print (existing_cat)
    return None

class Book(db.Model):
    __tablename__="books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(300), nullable=False)
    year = db.Column(db.Integer)
    dewey = db.Column(db.String(20))
    goodreads_url = db.Column(db.String(512))
    categories = db.relationship("Category", secondary=association_table, lazy='subquery',
                        backref=db.backref('books', lazy=True))

    def __init__(self, title, author, year, dewey, goodreads_url):
        self.title = title
        self.author = author
        self.year = year
        self.dewey = dewey
        self.goodreads_url = goodreads_url

class Category(db.Model):
    __tablename__="categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), unique=True)
    
    def __init__(self, name):
        self.name = name

@app.route("/")
def index():
    books = Book.query.order_by(Book.id.desc()).limit(10).all()
    return render_template("index.html", len = len(books), books = books)

@app.route("/books")
def books():
    books = Book.query.all()

    return render_template("books.html", len = len(books), books = books)

@app.route("/add_book")
def add_book():
    categories = Category.query.all()

    return render_template("add.html", len = len(categories), categories = categories)

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

        data = Book(title, author, int(year), dewey, goodreads_url)
        for cat in categories:
            data.categories.append(Category.query.filter_by(id=cat).first())
        
        db.session.add(data)
        db.session.commit()

        return render_template("success.html")



if __name__ == '__main__':
    app.debug = True
    app.run()