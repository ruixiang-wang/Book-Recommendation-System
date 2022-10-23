from utils import load_config
from logger import setup_log
from flask import Flask, request, render_template, session, redirect, url_for
from utils import mysql
import uuid
import math
import time

config = load_config()
logger = setup_log(__name__)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'This is secret key'
mysql = mysql(config['mysql'])


@app.route("/")
def root():
    """
    主页
    :return: home.html
    """
    login, userid = False, ''
    if 'userid' in session:
        login, userid = True, session['userid']
    # 热门书籍
    hot_books = []
    # sql: SELECT BookID,sum(Rating) as score FROM Book.Bookrating group by BookID order by score desc limit 10;
    # 从数据库中查询出评分最高的10本书的BookTitle, BookAuthor ,BookID, ImageM等信息
    sql = "SELECT BookTitle, BookAuthor ,BookID, ImageM FROM Books where BookID = '" + \
          "' or BookID = '".join(config['bookid']) + "'"

    try:
        hot_books = mysql.fetchall_db(sql)
        hot_books = [[v for k, v in row.items()] for row in hot_books]

    except Exception as e:
        print(e)
        # 日志
        # logger.exception("select hot books error: {}".format(e))
    # 15171556176
    return render_template('Index.html',
                           login=login,
                           books=hot_books,
                           useid=userid,
                           name="index")


@app.route("/guess")
def guess():
    """
    实时推荐模块,猜你喜欢
    :return: Index.html
    """
    login, userid, error = False, '', False
    if 'userid' in session:
        login, userid = True, session['userid']
    # 推荐书籍
    guess_books = []
    if login:
        # - 首先查该用户的浏览记录
        # - 通过浏览过的书籍，找到也看过这本书的人
        # - 在也看过这本书的人中，找评分较高的书推荐给用户

        # 1.从Booktuijian中查询出当前userID对应的所有BookID，设为b
        # 2.从Bookrating中查询出Rating不为0的5000条数据的UserID和BookID，设为a
        # 3.查询出a和b中BookID相等的UserID，设为d
        # 4.从Bookrating查询出Rating不为0的5000条数据的UserID,BookID,Rating，设为c
        # 5.查询出c和d中 c.UserID=d.UserID，然后按BookID分组，按score排序，取前十个，设为f
        # 6.将Books表设为e，从e和f中查询BookTitle,BookAuthor,BookID,ImageM
        sql = """select e.BookTitle,
                       e.BookAuthor,
                       e.BookID,
                       e.ImageM
                       from Books e
                inner join (select  c.BookID,
                                    sum(c.Rating) as score  
                            from (select UserID,BookID,Rating from Bookrating where Rating != 0
                                limit {0}) c 
                            inner join (select UserID 
                                        from (select UserID,BookID from Bookrating where Rating != 0
                                        limit {0}) a 
                                        inner join (select BookID from Booktuijian where UserID='{1}') b
                                        on a.BookID=b.BookID ) d
                            on c.UserID=d.UserID
                            group by c.BookID 
                            order by score desc 
                            limit 10) f
                on e.BookID = f.BookID""".format(config['limit'], session['userid'])
        try:
            guess_books = mysql.fetchall_db(sql)
            guess_books = [[v for k, v in row.items()] for row in guess_books]

        except Exception as e:
            print(e)
            # logger.exception("select guess books error: {}".format(e))
    return render_template('Index.html',
                           login=login,
                           books=guess_books,
                           useid=userid,
                           name = "guess")


@app.route("/recommend")
def recommend():
    """
    协同过滤计算---推荐书籍页面
    :return: Index.html
    """
    login, userid, error = False, '', False
    if 'userid' in session:
        login, userid = True, session['userid']
    # 推荐书籍
    recommend_books = []
 
    if login:
        sql = """select BookTitle,
                        BookAuthor,
                        a.BookID,
                        a.ImageM ,
                        score
                        from (SELECT * from Books ) a  
                        LEFT  JOIN Booktuijian as b on a.BookID = b.BookID where b.UserID = "{}"
                        order by score desc
                        """.format(userid)
        try:
            recommend_books = mysql.fetchall_db(sql)
            recommend_books = [[v for k, v in row.items()] for row in recommend_books]

        except Exception as e:
            print(e)

    return render_template('Index.html',
                           login=login,
                           books=recommend_books,
                           useid=userid,
                           name = "recommend")


@app.route("/loginForm")
def loginForm():
    """
    跳转登录页
    :return: Login.html
    """
    if 'userid' in session:
        return redirect(url_for('root'))
    else:
        return render_template('Login.html', error='')


@app.route("/registerationForm")
def registrationForm():
    """
    跳转注册页
    :return: Register.html
    """
    return render_template("Register.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    注册
    :return: Register.html
    """
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            age = request.form['age']

            try:
                sql = "insert into User (UserID,Location,Age) values ('{}','{}','{}')".format(username, password, age)
                # 执行sql
                mysql.exe(sql)
                print("username:{},password:{},age:{} register success".format(username, password, age))
                # logger.info("username:{},password:{},age:{} register success".format(username, password, age))
            except Exception as e:
                # 发生异常，回滚
                mysql.rollback()
                print("username:{},password:{},age:{} register filed".format(username, password, age))
                # logger.exception("username:{},password:{},age:{} register filed".format(username, password, age))
            return render_template('Login.html')
    except Exception as e:
        print("register function error: {}".format(e))

        return render_template('Register.html', error='注册出错')


def is_valid(username, password):
    """
    登录验证
    :param username: 用户名
    :param password: 密码
    :return: True/False
    """
    try:
        sql = "SELECT UserID, Location as Username FROM User where UserID='{}' and Location ='{}'".format(username, password)
        # 若按条件查询到结果，则表示用户名、密码正确
        result = mysql.fetchone_db(sql)

        if result:
            print('username:{},password:{}: has login success'.format(username, password))

            return True
        else:
            print('username:{},password:{}: has login filed'.format(username, password))

            return False
    except Exception as e:
        print('username:{},password:{}: has login error'.format(username, password))

        return False


@app.route("/login", methods=['POST', 'GET'])
def login():
    """
    登录页提交
    :return: Login.html
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and username == password:
            session['userid'] = username
            return render_template('Admin.html',userid= 'admin')
        if is_valid(username, password):
            session['userid'] = username
            return redirect(url_for('root'))
        else:
            error = '账号密码输入错误'
            return render_template('Login.html', error=error)


@app.route("/logout")
def logout():
    """
    退出登录，注销
    :return: root
    """
    session.pop('userid', None)
    return redirect(url_for('root'))


def update_recommend_book(UserID, BookID):
    """
    更新推荐数据
    更新策略为：若score存在，则判断(score+0.5)是否大于10，大于则将score赋值为10，否则，score+=0.5
                若score不存在，则score=0.5
    """
    sql = '''SELECT score FROM Booktuijian WHERE UserID="{0}" and BookID="{1}"'''.format(UserID, BookID)
    score = mysql.fetchone_db(sql)
    if score:
        print(score)
        score = float(score['score'])
    
        if score + 0.5 > 10:
            score = 10
        else:
            score += 0.5
        print(score)
        sql = '''UPDATE Booktuijian SET score='{2}' WHERE UserID="{0}" and BookID="{1}" '''.format(UserID, BookID,
                                                                                                   str(score))
        mysql.exe(sql)
    else:
        score = 0.5
        sql = ''' insert into Booktuijian (UserID,BookID,score) values ('{0}','{1}','{2}') '''.format(UserID, BookID,
                                                                                                      str(score))
        # logger.info("update_recommend_book, sql:{}".format(sql))
        mysql.exe(sql)


@app.route("/bookinfo", methods=['POST', 'GET'])
def bookinfo():
    """
    书籍详情
    :return: BookInfo.html
    """
    # 获取用户ID
    score = 0
    if 'userid' not in session:
        userid = None
        login = False
    else:
        userid = session['userid']
        login = True
    try:
        if request.method == 'GET':
            bookid = request.args.get('bookid')
            sql = """SELECT BookTitle,
                            BookID,
                            PubilcationYear,
                            BookAuthor,
                            ImageM from Books where BookID="{}" """.format(bookid)
            book_info = mysql.fetchall_db(sql)
            book_info = [v for k, v in book_info[0].items()]
            # 在Booktuijian表中插入信息
            update_recommend_book(userid, bookid)
        if userid:
            sql = '''SELECT Rating FROM Bookrating 
                            where UserID="{}" and BookID="{}"'''.format(userid, bookid)
            score = mysql.fetchone_db(sql)
            if score:
                score = int(score['Rating'])
                # 对浮点数向上取整
                score = math.ceil(score / 2)
                if score>10:score=10

    except Exception as e:
        print(e)
        # logger.exception("select book info error: {}".format(e))
    return render_template('BookInfo.html',
                           book_info=book_info,
                           login=login,
                           useid=userid,
                           score=score)


@app.route("/user", methods=['POST', 'GET'])
def user():
    """
    个人信息
    :return: UserInfo.html
    """
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('loginForm'))
    else:
        login, userid = True, session['userid']
    userinfo = []
    orderinfo = []
    try:
        sql = "select UserID,Location,Age from User where UserID='{}'".format(userid)
        userinfo = mysql.fetchone_db(sql)
        userinfo = [v for k, v in userinfo.items()]

        sql = "select OrderID,BookID,BookNames,price,status,time from `order` where UserID='{}'".format(userid)
        orderinfo = mysql.fetchall_db(sql)
    except Exception as e:
        print(e)
    return render_template("UserInfo.html",
                           login=login,
                           useid=userid,
                           userinfo=userinfo,
                           is_order=False,
                           orderinfo=orderinfo)


@app.route("/search", methods=['POST', 'GET'])
def search():
    """
    书籍检索
    :return: Search.html
    """
    login, userid = False, None
    if 'userid' in session:
        login, userid = True, session['userid']
    keyword, search_books = "", []
    try:
        if request.method == 'GET':
            keyword = request.values.get('keyword')
            # 移除字符串头尾指定的空格
            keyword = keyword.strip()
            sql = "SELECT BookTitle, BookAuthor ,BookID, ImageM from Books where BookTitle like '%{}%' limit 20".\
                format(keyword)
            search_books = mysql.fetchall_db(sql)
            search_books = [[v for k, v in row.items()] for row in search_books]
    except Exception as e:
        print(e)
        # logger.exception("select search books error: {}".format(e))
    return render_template("Search.html",
                           key=keyword,
                           books=search_books,
                           login=login,
                           useid=userid)


@app.route("/rating", methods=['POST', 'GET'])
def rating():
    """
    书籍评分
    :return: update
    """
    userid = session['userid']
    try:
        if request.method == 'POST':
            # 评分等级
            rank = request.values.get('rank')
            bookid = request.values.get('book_id')
            # 通过查询，判断当前用户是否对当前书籍评分过
            sql = '''SELECT COUNT(1) as count FROM Bookrating WHERE UserID="{0}" and BookID="{1}" '''.format(userid,
                                                                                                             bookid)
            count = mysql.fetchone_db(sql)
            if count['count']:
                # 评分只有5颗星，所有此处乘2
                sql = '''UPDATE Bookrating SET Rating='{2}' WHERE UserID="{0}" and BookID="{1}"  '''.format(userid,
                                                                                                bookid, int(rank) * 2)
            else:
                sql = '''INSERT INTO Bookrating (UserID,BookID,Rating) values ('{0}','{1}','{2}') '''.format(userid,
                                                                                                 bookid, int(rank) * 2)
            mysql.exe(sql)
            print("update book rating success,sql:{}".format(sql))
            # logger.info("update book rating success,sql:{}".format(sql))
    except Exception as e:
        print("rating books error: {}".format(e))
        # logger.exception("rating books error: {}".format(e))
    return redirect(url_for('root'))


@app.route("/historical", methods=['POST', 'GET'])
def historical():
    """
    历史评分
    :return: Historicalscore.html"
    """
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('loginForm'))
    else:
        login, userid = True, session['userid']
    historicals = []
    try:
        # 查询出Bookrating表中的历史评分
        sql = '''SELECT 
                        BookTitle,
                        BookAuthor,
                        PubilcationYear,
                        a.BookID,
                        Rating,
                        ImageM 
                        FROM (SELECT * from Bookrating ) a   
                        LEFT  JOIN  Books as b on a.BookID = b.BookID where a.UserID = '{}'
                        '''.format(userid)
        historicals = mysql.fetchall_db(sql)
        historicals = [[v for k, v in row.items()] for row in historicals]
    except Exception as e:
        print("historical rating books error: {}".format(e))
        # logger.exception("historical rating books error: {}".format(e))
    return render_template("Historicalscore.html",
                           books=historicals,
                           login=login,
                           useid=userid)


@app.route("/order", methods=['POST', 'GET'])
def order():
    """
    查看购物车
    :return: Order.html
    """
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('loginForm'))
    else:
        login, userid = True, session['userid']
    cats = []
    try:
        # floor()函数用于取整
        sql = '''SELECT b.BookID,
                        b.BookTitle,
                        b.BookAuthor,
                        (b.PubilcationYear)/100 price FROM (SELECT * from Cart ) a  
                        LEFT  JOIN  Books as b on a.BookID = b.BookID where a.UserID = "{}"
                        '''.format(userid)
        cats = mysql.fetchall_db(sql)
        cats = [[v for k, v in row.items()] for row in cats]
        # 将书单存入session
        session['cats'] = cats

    except Exception as e:
        print("historical rating books error: {}".format(e))
    return render_template("Order.html",
                           books=cats,
                           login=login,
                           useid=userid)


@app.route("/addcart", methods=['POST', 'GET'])
def add():
    """
    添加到购物车
    :return:
    """
    login, userid = False, None
    if 'userid' not in session:
        return redirect(url_for('loginForm'))
    else:
        login, userid = True, session['userid']
    try:
        if request.method == 'GET':
            bookid = request.values.get('bookid')
            # 判断有无记录
            sql = '''SELECT COUNT(1) as count FROM Cart WHERE UserID="{0}" and BookID="{1}" '''.format(userid,
                                                                                                       bookid)
            count = mysql.fetchone_db(sql)
            if not count['count']:
                sql = '''INSERT INTO Cart (UserID,BookID ) values ('{0}','{1}') '''.format(userid, bookid)
                mysql.exe(sql)
    except Exception as e:
        print(e)
    return redirect(url_for('order'))


@app.route("/delete", methods=['POST', 'GET'])
def delete():
    """
    删除购物车
    :return:
    """
    userid = session['userid']
    try:
        if request.method == 'GET':
            bookid = request.values.get('bookid')
            sql = '''DELETE  FROM Cart WHERE UserID="{0}" and BookID="{1}" '''.format(userid,bookid)
            mysql.exe(sql)
            print("delete Cart  success,sql:{}".format(sql))
    except Exception as e:
        print("delete Cart  books error: {}".format(e))
    return redirect(url_for('order'))


@app.route("/editinfo", methods=["GET", "POST"])
def editinfo():
    """
    修改个人信息
    :return: Userinfo.html
    """
    userid = session['userid']
    try:
        if request.method == 'POST':
            password = request.form['password']
            age = request.form['age']
            try:
                sql = "UPDATE User SET Location='{}',Age= '{}' WHERE UserID='{}'".format(password, age, userid)
                mysql.exe(sql)
                # logger.info("UPDATE userinfo --> username:{},password:{},age:{} ".format(userid, password, age))
            except Exception as e:
                mysql.rollback()
                # logger.exception("username:{},password:{},age:{} UPDATE filed".format(userid, password, age))
            return redirect(url_for('user'))
    except Exception as e:
        # logger.exception("add user info  error: {}".format(e))
        return redirect(url_for('user'))


@app.route("/editpassword", methods=["GET", "POST"])
def editpassword():
    """
    修改账号密码
    :return: Userinfo.html
    """
    userid = session['userid']
    try:
        if request.method == 'POST':
            password1 = request.form['password1']
            password2 = request.form['password2']
            if password1==password2:
                try:
                    sql = "UPDATE User SET Location='{}' WHERE UserID='{}'".format(password1, userid)
                    mysql.exe(sql)
                    # logger.info("UPDATE password --> username:{},password:{} ".format(userid, password1))
                except Exception as e:
                    mysql.rollback()
                    # logger.exception("username:{},password:{} UPDATE password filed".format(userid, password1))
                return redirect(url_for('user'))
    except Exception as e:
        print(e)
        # logger.exception("add user info  error: {}".format(e))
        return redirect(url_for('user'))


@app.route("/admin")
def admin():
    """
    后台管理页面的主页面
    :return:
    """
    return render_template('Admin.html', userid="admin")


@app.route("/adminuser", methods=["GET", "POST"])
def adminuser():
    """
    管理用户页面
    """
    userid = session['userid']
    users = []
    next_page = 0
    previous_page = 0
    try:
        # 总页数
        total_user = mysql.fetchone_db("select count(*) from User")
        total_page = math.ceil(total_user["count(*)"] / 10)
        # 每页的大小
        page_size = 10
        # 查询的是否是下一页
        try:
            flag = int(request.args.get("flag"))
        except:
            flag = 1
        # 当前页
        try:
            crruent_page = int(request.args.get("crruent_page"))
        except:
            crruent_page = 0
        # 当前得到的是第几条数据
        if flag:
            previous_page = crruent_page - 1
            next_page = crruent_page + 1
            # 如果查询的值大于总页数，则将其置为总页数
            if crruent_page > total_page:
                crruent_page = total_page
        else:
            crruent_page = crruent_page - 2
            next_page = crruent_page + 1
            previous_page = crruent_page - 1
        crruent_page = page_size * crruent_page
        sql = "select * from User where Age != 'nan' limit {},{}".format(crruent_page,page_size)
        users = mysql.fetchall_db(sql)
        users = [[v for k, v in row.items()] for row in users]
        return render_template('AdminUser.html',users = users, error=False, userid=userid, next_page = next_page, previous_page = previous_page, search = False)
    except Exception as e:
        print(e)
        # logger.exception("Admin User info error: {}".format(e))
        return render_template('AdminUser.html', search = False)


@app.route("/keyword", methods=["GET", "POST"])
def keyword():
    """
    Location关键字查询用户
    """
    users = []
    try:
        userid = session['userid']
        if request.method == 'POST':
            keyword = request.form['keyword']
            if keyword:
                sql = "select UserID,Location,Age from User where UserID like '%{}%' limit 20 ".format(keyword)
                users = mysql.fetchall_db(sql)
                users = [[v for k, v in row.items()] for row in users]
            return render_template('AdminUser.html',users = users, userid=userid, search = True)
    except Exception as e:
        print(e)
        # logger.exception("keyword info  error: {}".format(e))
        return render_template('AdminUser.html',users = users, userid="admin", search = True)


@app.route("/delete_user", methods=['POST', 'GET'])
def delete_user():
    """
    删除用户
    """
    userid = session['userid']
    try:
        if request.method == 'GET':
            userid = request.values.get('userid')
            sql = '''DELETE  FROM User WHERE UserID="{0}" '''.format(userid)
            mysql.exe(sql)
            # logger.info("delete User  success,sql:{}".format(sql))
    except Exception as e:
        print(e)
        # logger.exception("delete User books error: {}".format(e))
    return redirect(url_for('adminuser', search = False))


@app.route("/adminbook", methods=["GET", "POST"])
def adminbook():
    """
    管理书籍页面
    """
    userid = session['userid']
    books = []
    next_page = 0
    previous_page = 0
    try:
        # 总页数
        total_book = mysql.fetchone_db("select count(*) from Books")
        total_page = math.ceil(total_book["count(*)"]/10)
        # 每页的大小
        page_size = 10
        # 查询的是否是下一页
        try:
            flag = int(request.args.get("flag"))
        except:
            flag = 1
        # 当前页
        try:
            crruent_page = int(request.args.get("crruent_page"))
        except:
            crruent_page = 0
        # 当前得到的是第几条数据
        if flag:
            previous_page = crruent_page - 1
            next_page = crruent_page + 1
            # 如果查询的值大于总页数，则将其置为总页数
            if crruent_page > total_page:
                crruent_page = total_page
        else:
            crruent_page = crruent_page - 2
            next_page = crruent_page + 1
            previous_page = crruent_page - 1
        crruent_page = page_size * crruent_page
        sql = "select * from Books limit {},{}".format(crruent_page, page_size)
        books = mysql.fetchall_db(sql)
        books = [[v for k, v in row.items()] for row in books]
    except Exception as e:
        print(e)
        # logger.exception("Admin Book info error: {}".format(e))
    return render_template('AdminBook.html',books = books, userid=userid, next_page = next_page, previous_page = previous_page,search = False)


@app.route("/keyword_book", methods=["GET", "POST"])
def keyword_book():
    """
    关键字查询书籍
    """
    books = []
    userid = session['userid']
    try:
        if request.method == 'POST':
            keyword = request.form['keyword']
            if keyword:
                sql = "select * from Books where BookTitle like '%{}%' limit 20 ".format(keyword)
                books = mysql.fetchall_db(sql)
                books = [[v for k, v in row.items()] for row in books]
    except Exception as e:
        print(e)
    return render_template('AdminBook.html',books = books, userid=userid,search = True)


@app.route("/delete_book", methods=['POST', 'GET'])
def delete_book():
    """
    删除书籍
    """
    userid = session['userid']
    try:
        if request.method == 'GET':
            bookid = request.values.get('bookid')
            sql = '''DELETE  FROM Books WHERE BookID="{0}" '''.format(bookid)
            mysql.exe(sql)
    except Exception as e:
        print(e)
    return redirect(url_for('adminbook', search = False))


@app.route("/addbook", methods=['POST', 'GET'])
def addbook():
    """
    添加书籍
    """
    userid = session['userid']
    try:
        if request.method == 'POST':
            bookid = request.form['bookid']
            title = request.form['title']
            author = request.form['author']
            public = request.form['public']
            Image = "http://photocdn.sohu.com/20140424/Img398717878.jpg"
            sql = '''INSERT INTO Books (BookID,BookTitle,BookAuthor,PubilcationYear,Publisher,ImageS,ImageM,ImageL) 
                     values  ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}')'''.format(bookid,title,author,"2018",
                                                                                        public,Image,Image,Image)
            mysql.exe(sql)
            return redirect(url_for('adminbook', search = False))
    except Exception as e:
        print(e)
    return render_template('AdminAddBook.html', search = False)


@app.route("/addorder", methods=['POST', 'GET'])
def add_order():
    """
    付款成功，创建订单。
    0.清除cart表中相关数据
    1.生成订单唯一id
    2.将数据加入order表
    :return:
    """
    userid = session['userid']
    books = session.pop('cats')
    userinfo = []
    orderinfo = []
    if books:
        # 生成唯一订单信息,将数据加入order表
        orderId = uuid.uuid4()
        booksId = []
        booksName = []
        order_price = 0
        for book in books:
            booksId.append(book[0])
            booksName.append(book[1].replace("'", "/"))
            order_price = order_price + book[3]
        booksIds = ",".join(booksId)
        booksNames = ",".join(booksName)
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        try:
            # status 0 -- 已下单（付款），等待发货  1 -- 已发货
            sql = "insert into `order` values ('{}','{}','{}','{}',{},'0','{}')"\
                .format(orderId, userid, booksIds, booksNames, order_price, time_now)
            print(sql)
            mysql.exe(sql)
            print(sql)
            # 删除cart（购物车）中的信息
            sql = "delete from cart where UserId='{}'".format(userid)
            mysql.exe(sql)
        except Exception as e:
            print(e)
    try:
        # 查询用户信息
        sql = "select UserID,Location,Age from User where UserID='{}'".format(userid)
        userinfo = mysql.fetchone_db(sql)
        userinfo = [v for k, v in userinfo.items()]

        sql = "select OrderID,BookID,BookNames,price,status,time from `order` where UserID='{}'".format(userid)
        orderinfo = mysql.fetchall_db(sql)
    except Exception as e:
        print(e)
    return render_template("UserInfo.html",
                           login=True,
                           useid=userid,
                           userinfo=userinfo,
                           is_order=True,
                           orderinfo=orderinfo)


@app.route("/adminorder", methods=['POST', 'GET'])
def admin_order():
    sql = "select OrderID,UserID,BookID,BookNames,price,status,time from `order`"
    orderinfo = mysql.fetchall_db(sql)
    return render_template("AdminOrder.html",
                           orderinfo=orderinfo)


@app.route("/deleteOrder", methods=['POST', 'GET'])
def delete_order():
    try:
        if request.method == 'GET':
            orderid = request.values.get('orderID')
            sql = '''DELETE FROM `order` WHERE OrderID="{0}"'''.format(orderid)
            mysql.exe(sql)
    except Exception as e:
        print(e)
    return redirect(url_for('admin_order'))


@app.route("/sendOrder", methods=['POST', 'GET'])
def send_order():
    try:
        if request.method == 'GET':
            orderid = request.values.get('orderID')
            sql = '''UPDATE `order` SET status="1" WHERE OrderID="{0}"'''.format(orderid)
            mysql.exe(sql)
    except Exception as e:
        print(e)
    return redirect(url_for('admin_order'))


if __name__ == '__main__':
    app.run(debug=True, port=8080)
