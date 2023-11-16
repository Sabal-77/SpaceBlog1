from flask import Flask, render_template, request, session, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime, timedelta
import math

with open('config.json', 'r') as f:
    data = json.load(f)

app = Flask(__name__)
if data["config"]["local_server"]:
    app.config['SQLALCHEMY_DATABASE_URI']=data["config"]["local_db"]
else:
    app.config['SQLALCHEMY_DATABASE_URI']=data["config"]["production_db"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.secret_key=data["config"]["secret_key"]
app.permanent_session_lifetime = timedelta(days=7)
db = SQLAlchemy(app)

class Signup(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    pw = db.Column(db.String(100), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    tagline = db.Column(db.String(200), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    date = db.Column(db.DateTime(), default=datetime.utcnow())

class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(1000), nullable=False)

with app.app_context():
    db.create_all() 

@app.route('/', methods=['GET','POST'])
def home():
    if request.method=='POST':
        email = request.form['email']
        pw = request.form['pw']
        userData =  Signup.query.filter_by(email=email).first()
        if not userData:
            flash("You haven't registered that account, please sign up.", "danger")
            return redirect('/signup')
        elif email=="" or pw=="":
            flash("Fields can't be empty", "danger")
            return redirect('/')
        elif email==userData.email and pw==userData.pw:
            session.permanent=True
            session['user']=email
            return redirect('/blog')
        else:
            flash("Invalid email or password, please try again.", "danger")
            return redirect('/')
    return render_template('home.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        email = request.form['email']
        pw = request.form['pw']
        cpw = request.form['cpw']
        if email=="" or pw=="" or cpw=="":
            flash("Fields can't be empty", "danger")
            return redirect('/signup')
        elif pw!=cpw:
            flash("Password did not match.", "danger")
            return redirect('/signup')
        userData =  Signup.query.filter_by(email=email).first()
        if not userData:
            data = Signup(email=email, pw=pw)
            db.session.add(data)
            db.session.commit()
            flash('Registered Account, please login', "success")
            return redirect('/')
        else:
            flash("You have already signed up through that account, please login.", "danger")
            return redirect('/')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/reset-password', methods=['GET','POST'])
def reset_pw():
    pass

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    datas = Signup.query.all()
    posts = Posts.query.all()
    if 'admin' in session and session['admin']==data['config']['admin_user']:
        return render_template('dashboard.html', datas=datas, posts=posts)
    if request.method=='POST':
        username = request.form['uname']
        pw = request.form['pw']
        if username==data['config']['admin_user'] and pw==data['config']['admin_pw']:
            session.permanent=True
            session['admin'] = username
            return render_template('dashboard.html', datas=datas, posts=posts)
        else:
            return render_template('dash_login.html')
    return render_template('dash_login.html')

@app.route('/dashlogout')
def dashlogout():
    session.pop('admin')
    return render_template('dash_login.html')

@app.route('/dashboard/post/<int:sno>', methods=['GET','POST'])
def post(sno):
    if 'admin' in session and session['admin']==data['config']['admin_user']:
        if request.method=='POST':
            slug = request.form['slug']
            title = request.form['title']
            tagline = request.form['tagline']
            content = request.form['content']
            if sno==0:
                post = Posts(slug=slug, title=title, tagline=tagline, content=content)
                db.session.add(post)
                db.session.commit()

                # Updating json file
                nextSlug = data['posts']['slug'].split('-')
                nextSlug[1] = f"{data['posts']['id']+1}"
                nextID=data['posts']['id']+1
                total_posts = data['posts']['total_posts']+1
                with open('config.json', 'w') as f:
                    data['posts']={}
                    data['posts']['id'] = nextID
                    data['posts']['slug'] = '-'.join(nextSlug)
                    data['posts']['total_posts'] = total_posts
                    json.dump(data, f, indent=4)

            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.slug = slug
                post.title = title
                post.tagline = tagline
                post.content= content
                db.session.add(post)
                db.session.commit()
                return redirect('/dashboard')
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('post.html', post=post, sno=sno, data=data)
    else:
        return render_template('dash_login.html')
    
@app.route('/dashboard/delete/acc/<int:sno>')
def delete_acc(sno):
    data = Signup.query.filter_by(sno=sno).first()
    db.session.delete(data)
    db.session.commit()
    return redirect('/dashboard')

@app.route('/dashboard/delete/post/<int:sno>')
def delete_post(sno):
    post = Posts.query.filter_by(sno=sno).first()
    db.session.delete(post)
    db.session.commit()
    total_posts = data["posts"]["total_posts"]-1
    data["posts"]["total_posts"] = total_posts
    with open('config.json', 'w') as f:
        json.dump(data, f, indent=4)
    return redirect('/dashboard')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if 'user' in session:
        if request.method=='POST':
            email = request.form['email']
            subject = request.form['subject']
            message = request.form['msg']
            msgToSend = Contact(email=email, subject=subject, message=message)
            db.session.add(msgToSend)
            db.session.commit()
            flash('Message sent successfully.', 'success')
            return redirect('/contact')
    else:
        flash("You need to login first.", "danger")
        return redirect('/')
    return render_template('contact.html', email=session['user'])

@app.route('/blog')
def blog():
    if 'user' in session:
        page = request.args.get('page')
        posts = Posts.query.all()
        last = math.ceil(len(posts)/data['config']['posts_to_show'])
        if not str(page).isnumeric():
            page = 1

        page = int(page)
        posts = posts[(page-1)*data['config']['posts_to_show']:(page-1)*data['config']['posts_to_show']+data['config']['posts_to_show']]
        if page==1:
            prev = '#'
            next = f'?page={page+1}'
        elif page==last:
            prev = f'?page={page-1}'
            next = '#'
        else:
            prev = f'?page={page-1}'
            next = f'?page={page+1}'
        
        return render_template('blog.html', posts=posts, prev=prev, next=next)
    else:
        flash("You need to login first.", "danger")
        return redirect('/')

@app.route('/blog/<string:slug>')
def blogpost(slug):
    post = Posts.query.filter_by(slug=slug).first()
    return render_template('blogpost.html', post=post)

if __name__=='__main__':
    app.run(debug=True)