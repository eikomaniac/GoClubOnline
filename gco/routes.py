#Flask and package imports
from flask import Flask, render_template, session, redirect, url_for, flash, request
from gco.classes import *
from gco.funcs import *
from gco import app

from passlib.hash import pbkdf2_sha256 #Hashing algorithm for password hashing
import re #Regular expressions
import sqlite3 #Database connections
from datetime import date,datetime #Retrieving system date and time
import os #Handles operating system commands such as deleting files
from shutil import copy2 #Copying files exactly and separating memory locations
import smtplib #Library for sending emails through Python
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string

PW_PAT = r'^[a-zA-Z0-9.]*$' #Regex for password - Any length of alphanumeric characters and full-stops
USER_PAT = r'^[a-zA-Z0-9]*$' #Regex for username - Any length of alphanumeric characters
EMAIL_PAT = r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)' #Regex for email
ADMIN_KEY = "cssgco2019" #Must be changed when given to the client

@app.route("/index")
@app.route("/")
def index():
  if 'logged_in' not in session: #If the user is not logged in
    return render_template('index.html')
  #If the user is logged in, then home.html should be rendered and the notifications and games data should be passed as a parameter
  return render_template('home.html', notifications=getNotifs(session['user_id']),notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))

@app.route("/leaderboard", methods=['GET']) #GET request access is required as there may be a parameter in the URL
def leaderboard():
  conn = sqlite3.connect("GoClubOnline.db")
  c = conn.cursor()
  errors = [] #Array where each element is a string containing information about any errors which will be displayed to the user as a 'danger-alert' class div

  params = ["rating","games","moves","prisoners"] #All possible parameters that are allowed to be passed
  if request.args.get('sb') not in params: #If parameter is changed by the user to in the URL then don't use it
    return redirect(url_for('leaderboard') + "?sb=rating") #Redirect to the default, working leaderboard page

  c.execute("SELECT Username, Rating, (SELECT COUNT(*) FROM games WHERE (PlayerOneID=users.UserID OR PlayerTwoID=users.UserID) AND WinnerID > 0), MovesMade, Prisoners FROM users, stats WHERE users.UserID = stats.UserID AND users.IsActive = 1")
  users = mergeSort(c.fetchall(),params.index(request.args.get('sb'))+1) #Merge sorts the users list by the argument set by the user
  users.reverse()

  #Small algorithm used to determine what rank to display next to a user
  rank_count = 0
  ranks = []
  for i in users:
    rank_count += 1
    if int(users[users.index(i)-1][params.index(request.args.get('sb'))+1]) == int(users[users.index(i)][params.index(request.args.get('sb'))+1]):
      ranks.append("-")
    else:
      ranks.append(str(rank_count))
  conn.close()

  if 'logged_in' in session: #Login check, passing different parameters depending on if they're logged in or not
    return render_template('leaderboard.html', title="Leaderboard", ranks=ranks, errors=errors, users=users, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))
  else:
    return render_template('leaderboard.html', title="Leaderboard", ranks=ranks, errors=errors, users=users)

@app.route("/register", methods=['GET','POST']) #Post request required as data will be sent to the server
def register_teacher():
  if 'logged_in' not in session: #Login check as the user must not be logged in to access this page
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    errors = [] #Array which holds the error messages to be displayed to the user, if any

    if request.method == 'POST': #If the user has submitted a post request (i.e. presses the 'Register' button)
      #Setting cookies and variables for use at a later date
      session['username'] = request.form['username']
      session['email'] = request.form['email']
      session['password'] = request.form['password']
      confirm_password = request.form['confirm_password']
      input_admin_key = request.form['admin_key']

      if input_admin_key != ADMIN_KEY: #If the admin key the user is input is not the same as the actual admin key set in this python file
        errors.append("The admin key you have input is invalid. Please try again")
      #Check to see if a username is already taken
      c.execute("SELECT * FROM users WHERE username=?",(session['username'],))
      if c.fetchone():
        errors.append('That username is already taken')
      elif session['username'] == "default":
        errors.append('That username is not available')
      else:
        if not re.match(USER_PAT, session['username']): #Regex check to see if the username follows the regex rules set above
           errors.append('Your username must only contain letters and numbers')
        if len(session['username']) < 3 or len(session['username']) > 20: #Length check to confirm the username is between 3-20 characters inclusive
           errors.append('Your username must be between 3 and 20 characters long')
      c.execute("SELECT * FROM adminEmails WHERE Email=\'{}\'".format(session['email']))
      if c.fetchone(): #Check to see if the email is taken
        errors.append('That email address is already taken')
      if not re.match(EMAIL_PAT, session['email']): #Regex check to see if the email follows the regex rules set above
        errors.append("Please input a valid email address")
      if not re.match(PW_PAT, session['password']): #Regex check to see if the password follows the regex rules set above
         errors.append('Your password must only contain letters, numbers, and a full stop')
      if len(session['password']) < 8: #The password must be at least 8 characters long
         errors.append('Your password must be at least 8 characters long')
      if confirm_password != session['password']: #If the passwords don't match
         errors.append('Your password does not match')
      if not errors: #If every field has valid input, send an email with the verification code
        msg = MIMEMultipart()
        msg['From'] = "goclubonline@gmail.com" #Email address for the account
        msg['To'] = session['email']
        msg['Subject'] = "Go Club Online Account Verification"
        session['verification_code'] = "".join([random.choice(string.ascii_uppercase + string.digits) for i in range(5)]) #Verification code is generated and stored as a cookie which will be used to check when the user inputs the code on the verification page
        session['verification_time'] = datetime.now() #Used to check if the code has expired
        msg.attach(MIMEText("""Hello {},
  Here is the code you need to verify your email account:

  {}

  If you are not trying to create an account on GoClubOnline, please ignore this email. It is possible that another user entered their login information incorrectly.
  This code will be active for 10 minutes. If you do not wish to create an account, please disregard this notice. """.format(msg['To'],session['verification_code'])))
        text = msg.as_string()
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
          server.starttls()
          server.login(msg['From'], "Hehexd3.1415") #Password for the email account
          server.sendmail(msg['From'], msg['To'], text) #Function to send the email
        flash("A verification code has been sent to your email address.", "success")
        return redirect(url_for('verification')) #Redirect to the verification page where they can input their code
    conn.close()
    return render_template('register.html', title='Register', errors=errors) #If errors found, refresh the page and display the errors
  flash("You must be logged out to do that.", 'warning')
  return redirect(url_for('index'))

@app.route("/login", methods=['GET','POST'])
def login():
  if 'logged_in' not in session: #Login check as the user must not be logged in to access this page
    errors = [] #Array which holds the error messages to be displayed to the user, if any
    if request.method == 'POST': #If the user has submitted a post request (i.e. presses the 'Login' button)
      conn = sqlite3.connect("GoClubOnline.db")
      c = conn.cursor()
      c.execute("SELECT * FROM users WHERE username=?",(request.form['username'],))
      record = c.fetchone()

      if not record: #If the username is not in the database, then no login attempt can be successful
        errors.append('Login unsuccessful. Please check your username or password.')
      else:
        if pbkdf2_sha256.verify(request.form["password"], record[3]): #Hash the password input by the user and check with the hashed password in the database
          if record[1] == True: #If the user is an admin, set the is_admin cookie to be True
            session['is_admin'] = True
          session['username'] = request.form['username']
          c.execute("SELECT UserID,IsActive FROM users WHERE Username=?",(session['username'],))
          session['user_id'], is_active = c.fetchone()
          if is_active == False: #If the user has been deleted by an admin then don't allow the user to log in
            session.clear() #and clear the cookies so the website does not think they are still logged in
            flash("This account no longer exists.", 'warning')
            return redirect(url_for('login'))
          #If all goes correctly, set the logged_in cookie to be True so the website can recognise that the user is logged in
          session['logged_in'] = True
          flash('You are now logged in.', 'success')
          return redirect(url_for('index'))
        else:
          errors.append('Login unsuccessful. Please check your username or password.')
    return render_template('login.html', title='Login', errors=errors)
  flash("You must be logged out to do that.", 'warning')
  return redirect(url_for('index'))

@app.route("/logout")
def logout():
  if 'logged_in' in session: #If the user is logged in
    session.clear() #Clear the cookies so the website does not think they are still logged in
    flash("You have now been logged out.", 'success')
    return redirect(url_for('index')) #And redirect to the home page
  flash("You must be logged in to do that.", 'warning') #Logout page should not be accessible if they are already logged out
  return redirect(url_for('login'))

@app.route("/account", methods=['GET','POST'])
def account():
  if 'logged_in' not in session: #Login check as the user must be logged in to access this page
    flash("You must be logged in to do that.", 'warning')
    return redirect(url_for('login'))
  errors = [] #Array which holds the error messages to be displayed to the user, if any
  conn = sqlite3.connect("GoClubOnline.db")
  c = conn.cursor()
  admins = [] #List of all admins' usernames
  c.execute("SELECT Username FROM users WHERE IsAdmin=?",(True,))
  admin = c.fetchall()
  for i in admin:
    admins.append(i[0])
  #Get data of the user to display onto the Account page
  c.execute("SELECT ImageFile,DateCreated,Password FROM users WHERE username=?",(session['username'],))
  record = c.fetchone()
  image_file = record[0]
  date = record[1]
  password = record[2]
  file_name = session['username']+image_file

  #Get total amount of wins the user has
  c.execute("SELECT COUNT(*) FROM games WHERE WinnerID={}".format(session['user_id']))
  wins = c.fetchone()[0]
  #Get total amount of games played - can be used to calculate winrate and amount of losses
  c.execute("SELECT COUNT(*) FROM games WHERE (PlayerOneID={0} OR PlayerTwoID={0}) AND WinnerID > 0".format(session['user_id']))
  total_games = c.fetchone()[0]
  #Get the other stats which are stored in the stats table that cannot be calculated through queries
  c.execute("SELECT Rating,MovesMade,Prisoners FROM stats WHERE UserID={}".format(session['user_id']))
  rating,moves_made,prisoners = c.fetchone()

  if request.method == 'POST': #If the user has submitted a post request (i.e. presses the 'Update' button)
    if pbkdf2_sha256.verify(request.form['current_password'],password):
      password_up = request.form['password']
      if password_up:
        if not re.match(PW_PAT, password_up): #Regex check to see if the password follows the regex rules set above
           errors.append('Your password must only contain letters, and numbers')
        if len(password_up) < 8: #The password must be at least 8 characters long
           errors.append('Your password must be at least 8 characters long')
        password_up = pbkdf2_sha256.hash(password_up, salt=bytes(session['username'],encoding="ascii")) #Hashes the password that will be uploaded and salts it with the user's username
      else:
        password_up = password
      if 'file' in request.files: #If the user has uploaded a file
        file = request.files['file']
        if file:
          file_name, file_type = os.path.splitext(app.config['UPLOAD_FOLDER']+file.filename)
          if file_type == ".png" or file_type == ".jpg" or file_type ==  ".gif" or file_type == ".jpeg": #Check to see if the file type is valid (so no harmful files can be uploaded to the server)
            os.remove(app.config['UPLOAD_FOLDER']+session['username']+image_file) #Deletes the old profile picture
            random_string = "".join([random.choice(string.ascii_letters + string.digits) for i in range(15)]) #New file name must be random so the browser recognises that the file is different and does not use the cached version which has not been updated
            file.save(os.path.join(os.path.dirname(__file__), "static/img/avi/", session['username']+random_string+file_type)) #Saves the file in the avi directory (for profile pictures)
            image_file = random_string + file_type
            file_name = session['username'] + image_file
          else:
            errors.append("Invalid file type: \'{}\'. Please choose a JPG, JPEG, PNG, or GIF file.".format(file_type))
            file_name = image_file
      if not errors:
        c.execute("UPDATE users SET Password=?,ImageFile=? WHERE Username=?;",(password_up,image_file,session['username'])) #Updates database with new password and image file name
        conn.commit()
        conn.close()
        flash('Profile details for ' + session['username'] + ' have been updated', 'success')
    else:
      errors.append("The password you have input is invalid. Please try again")
  return render_template('account.html', title='Account', date=date, moves_made=moves_made, prisoners=prisoners, wins=wins, total_games=total_games, rating=rating, file_name=file_name, admins=admins, errors=errors, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))

@app.route("/register_student", methods=['GET','POST'])
def register_student():
  if 'is_admin' in session: #Check to see if the user is an admin as only admins should be able to access this page
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    errors = [] #Array where each element is a string containing information about any errors which will be displayed to the user as a 'danger-alert' class div

    if request.method == 'POST': #If the user has submitted a post request (i.e. presses the 'Register' button)
      username = request.form['username']
      password = request.form['password']
      confirm_password = request.form['confirm_password']
      current_password = request.form['current_password']
      #Fetches the hashed password of the admin registering the student account
      c.execute("SELECT Password FROM users WHERE username=?",(session['username'],))
      admin_password = c.fetchone()[0]

      #Hash and check if the admin password the user inputs matches the admin's actual hashed password in the database
      if pbkdf2_sha256.verify("current_password",admin_password):
        errors.append("Your password (for verification) that you have input is invalid. Please try again")
      c.execute("SELECT * FROM users WHERE username=?",(username,))
      if c.fetchone(): #Check to see if the username
        errors.append('That username is already taken')
      if username == "default": #default is used as the file name for the default profile picture that
        errors.append('That username is not available')
      else:
        if not re.match(USER_PAT, username): #Regex check to see if the username follows the regex rules set above
           errors.append('Your username must only contain letters and numbers')
        if len(username) < 3 or len(username) > 20: #Length check to confirm the username is between 3-20 characters inclusive
           errors.append('Your username must be between 3 and 20 characters long')
      if not re.match(PW_PAT, password): #Regex check to see if the password follows the regex rules set above
         errors.append('Your password must only contain letters, numbers, and a full stop')
      if len(password) < 8: #Passwords must be at least 8 characters long to ensure strong and secure password
         errors.append('Your password must be at least 8 characters long')
      if not confirm_password == password: #Check to see if the passwords match
         errors.append('Your password does not match')
      if not errors: #If all fields are valid
        copy2(os.path.join("./gco/static/img/", "default.jpg"), os.path.join(app.config['UPLOAD_FOLDER'], username+".jpg")) #Generate a new profile picture for the user by copying the default picture under their name
        hashed_password = pbkdf2_sha256.hash(password, salt=bytes(username,encoding="ascii")) #Hash their password
        c.execute("INSERT INTO users VALUES (NULL,?,?,?,?,?,?);",(False,username,hashed_password,".jpg",date.today(),True,)) #SQL statement to insert new user into the 'users' table with all of the relevant information
        c.execute("SELECT UserID FROM users WHERE Username=?",(username,))
        user_id = c.fetchone()[0] #UserID fetched so it can be used to insert a new row into the 'stats' table
        c.execute("INSERT INTO stats VALUES ({},1000,0,0,350);".format(user_id))
        conn.commit()
        conn.close()
        flash('An account for ' + username + ' has been created. They may now log in.', 'success')
        return redirect(url_for('index'))
    conn.close()
    return render_template('register_student.html', title='Register Student', errors=errors, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))
  flash("You must be a teacher to do that.", 'warning')
  return redirect(url_for('login'))

@app.route("/users", methods=['GET','POST'])
def users():
  if 'logged_in' not in session: #Login check as the user must be logged in to access this page
    flash("You must be logged in to do that.", 'warning')
    return redirect(url_for('login'))
  conn = sqlite3.connect("GoClubOnline.db")
  c = conn.cursor()
  #Fetch the necessary data to display each user on the page
  c.execute("SELECT ImageFile, Username, UserID FROM users")
  queryRequest = c.fetchall()
  users = mergeSort(queryRequest,1) #Merge sort the users to display in alphabetical order from username

  admins = [] #List of all admins' usernames
  c.execute("SELECT Username FROM users WHERE IsAdmin=?",(True,))
  admin = c.fetchall()
  for i in admin:
    admins.append(i[0])

  deactivated_id_list = [] #List of UserIDs of all users that are deactivated (i.e. deleted by an admin)
  c.execute("SELECT UserID FROM users WHERE IsActive=0")
  deactivated_ids = c.fetchall()
  for i in deactivated_ids:
    deactivated_id_list.append(int(str(i)[1:-2]))

  if request.method == 'POST':
    if request.form.get('recover_button'): #If an admin presses the recover button
      #Update the IsActive column to be true of that user in the 'users' table so they can now log into their account
      c.execute("UPDATE users SET IsActive=1 WHERE UserID=?",(request.form.get('recover_button'),))
      conn.commit()
      deactivated_id_list.remove(int(request.form.get('recover_button'))) #The user with that UserID is no longer deactivated so it can be removed from this list
    elif request.form.get('search') != "": #If the user searches and the search field is not left blank
      #The same query will be done as above except there will be a WHERE Username LIKE condition to search for users only with those characters in that order in their username
      c.execute("SELECT ImageFile, Username, UserID FROM users WHERE Username LIKE ?",("%"+request.form['search']+"%",))
      queryResult = c.fetchall()
      users = mergeSort(queryResult,1) #Merge sort the users to display in alphabetical order from username
      conn.close()
    else:
      return redirect(url_for('users'))
  conn.close()
  return render_template('users.html', title="Users", users=users, admins=admins, deactivated_id_list=deactivated_id_list, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))

@app.route("/friends", methods=['GET','POST'])
def friends():
  if 'logged_in' not in session: #Login check as the user must be logged in to access this page
    flash("You must be logged in to do that.", 'warning')
    return redirect(url_for('login'))
  conn = sqlite3.connect("GoClubOnline.db")
  c = conn.cursor()
  #Get the UserID of the user currently logged in
  c.execute("SELECT UserID FROM users WHERE Username=?",(session['username'],))
  current_user_id = c.fetchone()[0]
  current_user = User(current_user_id) #Creating an instance of the User class of the user that is logged in right now

  friend_id_list = [] #List of UserIDs containing all mutual friends
  friend_ids = Friendship.getFriends(current_user)
  for i in friend_ids:
    friend_id_list.append(int(str(i)[1:-2]))

  request_from_list = [] #List of UserIDs of the people that the user with UserID as the user logged in has sent a friend request to
  request_from_ids = Friendship.getRequestFrom(current_user)
  for i in request_from_ids:
    request_from_list.append(int(str(i)[1:-2]))

  request_to_list = [] #List of UserIDs of the people that have sent a friend request to the user logged in
  request_to_ids = Friendship.getRequestTo(current_user)
  for i in request_to_ids:
    request_to_list.append(int(str(i)[1:-2]))

  c.execute("SELECT users.UserID, users.Username, users.ImageFile\
        FROM (SELECT UserID FROM friendships WHERE FriendID = ?\
        UNION\
        SELECT FriendID FROM friendships WHERE UserID = ?) AS relationships\
        JOIN users ON relationships.UserID = users.UserID",(current_user_id,current_user_id,))
  users = c.fetchall() #List of data for each friend that will be displayed on the page

  if request.method == 'POST':
    if request.form.get("goto_users"): #If the user presses the button to go to the Users page
      return redirect(url_for('users')) #they will be redirected there
    if request.form.get("friend_button"): #If the user presses one of buttons related to friendship functions
      #A small one-time algorithm to get the name of the button that has been pressed
      button_data = request.form.get("friend_button")[1:-2]
      eol_index = 0
      for i in range(len(button_data)):
        if button_data[i] == ",":
          eol_index = i
      user_id = int(button_data[:eol_index])
      event = button_data[len(str(user_id))+3:]
      if event == "Cancel Pending Request": #If the button's function is to cancel a pending request
        #Remove the one-way relationship in the friendships database to cancel the request
        c.execute("DELETE FROM friendships WHERE UserID=? AND FriendID=?;",(current_user_id,user_id,))
        conn.commit()
        request_to_list.remove(user_id)
      elif event == "Accept Friend Request": #If the button's function is to accept the friend request
        #Complete the one-way relationship by making it a two-way relationship, thus confirming them as friends
        c.execute("INSERT INTO friendships VALUES (?,?);",(current_user_id,user_id,))
        conn.commit()
        friend_id_list.append(user_id)
        request_from_list.remove(user_id)
      elif event == "Decline Friend Request": #If the button's function is to decline a friend request
        #Delete the existing one-way relationship so no relationship between the users exists
        c.execute("DELETE FROM friendships WHERE UserID=? AND FriendID=?;",(user_id,current_user_id,))
        conn.commit()
        request_from_list.remove(user_id)
      c.execute("SELECT users.UserID, users.Username, users.ImageFile\
            FROM (SELECT UserID FROM friendships WHERE FriendID = ?\
            UNION\
            SELECT FriendID FROM friendships WHERE UserID = ?) AS relationships\
            JOIN users ON relationships.UserID = users.UserID",(current_user_id,current_user_id,))
      users = c.fetchall() #New list of data for each friend that will be displayed on the page
    if request.form.get('search'):
      if request.form.get('search') != "": #If the user searches and the search field is not left blank
        #The same query will be done as above except there will be a WHERE Username LIKE condition to search for users only with those characters in that order in their username
        c.execute("SELECT users.UserID, users.Username, users.ImageFile\
              FROM (SELECT UserID FROM friendships WHERE FriendID = ?\
              UNION\
              SELECT FriendID FROM friendships WHERE UserID = ?) AS relationships\
              JOIN users ON relationships.UserID = users.UserID\
              WHERE users.Username LIKE ?",(current_user_id,current_user_id,"%"+request.form.get('search')+"%"),)
        users = c.fetchall() #New list of data for each friend that will be displayed on the page
        conn.close()
      else:
        return redirect(url_for('friends'))
  conn.close()
  return render_template('friends.html', title="Friends", users=users, friend_id_list=friend_id_list, request_to_list=request_to_list, request_from_list=request_from_list, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))

@app.route("/users/<int:user_id>", methods=['GET','POST'])
def user_profile(user_id):
  if 'logged_in' not in session:
    flash("You must be logged in to do that.", 'warning')
    return redirect(url_for('login'))
  errors = [] #Array where each element is a string containing information about any errors which will be displayed to the user as a 'danger-alert' class div
  #Variables initialised to be modified later
  friends = False
  liveGame = False
  game_id = ""
  friend_request_to_user = False
  game_request_to_user = False
  friend_request_from_user = False
  game_request_from_user = False
  conn = sqlite3.connect("GoClubOnline.db")
  c = conn.cursor()

  c.execute("SELECT Password FROM users WHERE Username=?",(session['username'],))
  my_password = c.fetchone()[0]

  admins = [] #List of all the admins' usernames
  c.execute("SELECT Username FROM users WHERE IsAdmin=?",(True,))
  admin = c.fetchall()
  for i in admin:
    admins.append(str(i)[2:-3])
  current_user_id = session['user_id']
  current_user = User(current_user_id) #Creating an instance of the User class of the user that is logged in right now

  c.execute("SELECT GameID from games WHERE PlayerOneID = {} AND PlayerTwoID = {}".format(user_id,current_user_id))
  queryResult = c.fetchone()
  if queryResult != None:
    game_id = str(queryResult[0])
  c.execute("SELECT GameID from games WHERE PlayerOneID = {} AND PlayerTwoID = {}".format(current_user_id,user_id))
  queryResult = c.fetchone()
  if queryResult != None:
    game_id = str(queryResult[0])

  user = User(user_id) #Creating an instance of the User class of the user whose page is being viewed right now

  username = user.record['Username']
  password = user.record['Password']
  image_file = user.record['ImageFile']
  datecreated = user.record['DateCreated']
  is_active = user.record['IsActive']
  if is_active == False: #If the user is not active due to an admin deleting it, deny access to view the page
    flash("This account no longer exists.", 'warning')
    return redirect(url_for('users'))

  #Get total amount of wins the user has
  c.execute("SELECT COUNT(*) FROM games WHERE WinnerID={}".format(user_id))
  wins = c.fetchone()[0]
  #Get total amount of games played - can be used to calculate winrate and amount of losses
  c.execute("SELECT COUNT(*) FROM games WHERE (PlayerOneID={0} OR PlayerTwoID={0}) AND WinnerID > 0".format(user_id))
  total_games = c.fetchone()[0]
  #Get the other stats which are stored in the stats table that cannot be calculated through queries
  c.execute("SELECT Rating,MovesMade,Prisoners FROM stats WHERE UserID={}".format(user_id))
  rating,moves_made,prisoners = c.fetchone()

  #Check to see if the users are friends
  friend_id_list = []
  friend_ids = Friendship.getFriends(current_user)
  for i in friend_ids:
    friend_id_list.append(i[0])
  if user_id in friend_id_list:
    friends = True

  #Check to see if the users are already in a live game
  game_id_list = []
  game_ids = GameRequest.getLiveGames(current_user)
  for i in game_ids:
    game_id_list.append(int(i[0]))
  if user_id in game_id_list:
    liveGame = True

  #Check to see if a friend request has been sent to the user by the current user
  friend_request_from_list = []
  friend_request_from_ids = Friendship.getRequestFrom(current_user)
  for i in friend_request_from_ids:
    friend_request_from_list.append(i[0])
  if user_id in friend_request_from_list:
    friend_request_from_user = True

  #Checks to see if a game request has been sent to the user by the current user
  game_request_from_list = []
  game_request_from_ids = GameRequest.getRequestFrom(current_user)
  for i in game_request_from_ids:
    game_request_from_list.append(i[0])
  if user_id in game_request_from_list:
    game_request_from_user = True

  #Checks to see if a friend request has been sent to the current user by the user whose page is being viewed
  friend_request_to_list = []
  friend_request_to_ids = Friendship.getRequestTo(current_user)
  for i in friend_request_to_ids:
    friend_request_to_list.append(i[0])
  if user_id in friend_request_to_list:
    friend_request_to_user = True

  #Checks to see if a game request has been sent to the current user by the user whose page is being viewed
  game_request_to_list = []
  game_request_to_ids = GameRequest.getRequestTo(current_user)
  for i in game_request_to_ids:
    game_request_to_list.append(i[0])
  if user_id in game_request_to_list:
    game_request_to_user = True

  file_name = image_file
  if request.method == 'POST':
    if request.form.get('friend_button') == "Send Friend Request":
      #Creates a one-way relationship in the 'friendships' table
      c.execute("INSERT INTO friendships VALUES (?,?);",(current_user_id,user_id,))
      conn.commit()
      friend_request_to_user = True
    elif request.form.get('friend_button') == "Cancel Pending Request":
      #Removes the one-way relationship that existed before
      c.execute("DELETE FROM friendships WHERE UserID=? AND FriendID=?;",(current_user_id,user_id,))
      conn.commit()
      friend_request_to_user = False
    elif request.form.get('friend_button') == "Unfriend":
      #Removes the two-way relationship that made both users be 'Friends' in the system and thus are no longer friends
      c.execute("DELETE FROM friendships WHERE UserID=? AND FriendID=?;",(current_user_id,user_id,))
      conn.commit()
      c.execute("DELETE FROM friendships WHERE UserID=? AND FriendID=?;",(user_id,current_user_id,))
      conn.commit()
      friends = False
    elif request.form.get('friend_button') == "Accept Friend Request":
      #Complete the two-way relationship by inserting the other one-way relationship in the 'friendships' table
      c.execute("INSERT INTO friendships VALUES (?,?);",(current_user_id,user_id,))
      conn.commit()
      friends, friend_request_from_user = True, False
    elif request.form.get('friend_button') == "Decline Friend Request":
      #Removes the one-way relationship that existed before
      c.execute("DELETE FROM friendships WHERE UserID=? AND FriendID=?;",(user_id,current_user_id,))
      conn.commit()
      friend_request_from_user = False
    elif request.form.get('delete_button') == "Delete account": #If an admin presses the 'Delete account' button on the user's page
      #Update the IsActive column for that user to be False so they can no longer log in
      c.execute("UPDATE users SET IsActive=0 WHERE UserID=?",(user_id,))
      conn.commit()
      is_active = False
      flash("This account no longer exists.", 'warning')
      return redirect(url_for('users'))
    elif request.form.get('challenge_button') == ("Challenge " + username + "!"):
      #Creates a one-way relationship in the 'gameRequests' table
      c.execute("INSERT INTO gameRequests VALUES({},{})".format(current_user_id,user_id))
      conn.commit()
      game_request_to_user = True
    elif request.form.get('challenge_button') == "Cancel Challenge Request":
      #Removes the one-way relationship that existed before
      c.execute("DELETE FROM gameRequests WHERE UserID={} AND RecipientID={}".format(current_user_id,user_id))
      conn.commit()
      game_request_to_user = False
    elif request.form.get('challenge_button') == "Accept Challenge":
      #Complete the two-way relationship by inserting the other one-way relationship in the 'gameRequests' table
      c.execute("INSERT INTO gameRequests VALUES ({},{});".format(current_user_id,user_id))
      #As the challenge has been accepted, a game must be created and initialised in the 'games' table
      c.execute("INSERT INTO games VALUES (?,?,?,?,?,?,?,?);",(None,user_id,current_user_id,None,'81U',user_id,0,None))
      conn.commit()
      liveGame, game_request_from_user = True, False
      c.execute("SELECT GameID from games WHERE PlayerOneID = {} AND PlayerTwoID = {}".format(user_id,current_user_id))
      queryResult = c.fetchone()
      game_id = str(queryResult[0])
      return redirect(url_for('games') + "/" + game_id) #The user is redirected to their live game
    elif request.form.get('challenge_button') == "Decline Challenge":
      #Removes the one-way relationship that existed before
      c.execute("DELETE FROM gameRequests WHERE UserID={} AND RecipientID={};".format(user_id,current_user_id))
      conn.commit()
      friend_request_from_user, game_request_from_user = False, False
    elif pbkdf2_sha256.verify(request.form.get('current_password'),my_password): #If an admin presses the 'Update' button to change some details, first the admin password is checked to verify that the person changing the details is actually the admin
      password_up = request.form['password']
      if password_up:
        if not re.match(PW_PAT, password_up):
           errors.append('Your password must only contain letters, numbers') #Regex check to see if the password follows the regex rules set above
        if len(password_up) < 8:
           errors.append('Your password must be at least 8 characters long') #Password must be at least 8 characters to ensure a strong and secure password
        password_up = pbkdf2_sha256.hash(password_up, salt=bytes(username,encoding="ascii")) #The password that will be uploaded is hashed and salted using the username
      else:
        password_up = password
      if 'file' in request.files: #If a file has been uploaded to the server
        file = request.files['file']
        if file:
          file_name, file_type = os.path.splitext(app.config['UPLOAD_FOLDER']+file.filename)
          if file_type == ".png" or file_type == ".jpg" or file_type ==  ".gif" or file_type == ".jpeg": #Check to see if the file type is valid (so no harmful files can be uploaded to the server)
            os.remove(app.config['UPLOAD_FOLDER']+username+image_file) #Deletes the old profile picture
            random_string = "".join([random.choice(string.ascii_letters + string.digits) for i in range(15)]) #New file name must be random so the browser recognises that the file is different and does not use the cached version which has not been updated
            file.save(os.path.join(os.path.dirname(__file__), "static/img/avi/", username+random_string+file_type)) #Saves the file in the avi directory (for profile pictures)
            file_name = random_string + file_type
          else:
            errors.append("Invalid file type: \'{}\'. Please choose a JPG, JPEG, PNG, or GIF file.".format(file_type))
            file_name = image_file
      if not errors:
        c.execute("UPDATE users SET Password=?,ImageFile=? WHERE Username=?;",(password_up,file_name,username,)) #Updates database with new password and image file name
        conn.commit()
        conn.close()
        flash('Profile details for ' + username + ' have been updated', 'success')
    else:
      errors.append("The password you have input is invalid. Please try again")
  return render_template('user_profile.html', title=username, moves_made=moves_made, prisoners=prisoners, wins=wins, total_games=total_games, rating=rating, datecreated=datecreated, file_name=file_name, admins=admins, is_active=is_active, liveGame=liveGame, game_id=game_id, game_request_to_user=game_request_to_user, game_request_from_user=game_request_from_user, friend_request_to_user=friend_request_to_user, friends=friends, friend_request_from_user=friend_request_from_user, errors=errors, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))


@app.route("/forgotten_password", methods=['GET','POST'])
def forgotten_password():
  if 'logged_in' not in session:
    errors = [] #Array where each element is a string containing information about any errors which will be displayed to the user as a 'danger-alert' class div
    if request.method == 'POST':
      conn = sqlite3.connect("GoClubOnline.db")
      c = conn.cursor()
      email = request.form['email']
      c.execute("SELECT COUNT(*) FROM adminEmails WHERE Email=\'{}\'".format(email))
      if c.fetchone()[0] == 0: #If there is no email in the database with what the user has input into the email form
        flash("Error: There is no email associated with this account","danger")
        return redirect(url_for("forgotten_password"))
      try:
        session['email'] = email
        code = "".join([random.choice(string.ascii_uppercase + string.digits) for i in range(5)]) #Randomly generated 5 character alphanumeric code which will be stored as a cookie and hashed and used in the link so that only the person who is meant to receive the link should have access to the 'Change Password' page
        session['code'] = pbkdf2_sha256.hash(code, salt=bytes(session['email'],encoding="ascii"))
        msg = MIMEMultipart()
        msg['From'] = "goclubonline@gmail.com"
        msg['To'] = session['email']
        msg['Subject'] = "Go Club Online Password Reset"
        link = url_for('change_password', code=session['code'], _external=True)
        msg.attach(MIMEText("""We have received a request to reset the password for your GCO account: {}
  If you submitted this request, please click the link below to proceed.

  {}

  If you do not wish to reset your password, please disregard this notice.""".format(msg['To'],link)))
        text = msg.as_string()
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
          server.starttls()
          server.login(msg['From'], "Hehexd3.1415") #Password for the email account
          server.sendmail(msg['From'], msg['To'], text) #Function to send the email to the email address
        flash("A link to reset your password has been sent to your email address", "success")
      except:
        #If the email could not be sent then the user will be notified with an error message
        errors.append("There was a problem sending the email. Please try again later")
      c.close()
    return render_template('forgotten_password.html', title="Forgotten Password?", errors = errors)
  flash("You must be logged out to do that", "warning")
  return redirect(url_for('index'))

@app.route("/change_password", methods=['GET','POST'])
def change_password():
  if 'logged_in' not in session and 'email' in session: #This page should only be accessible if the user is not logged in and an email has been sent to them, which is determinable through the 'email' cookie
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    errors = [] #Array where each element is a string containing information about any errors which will be displayed to the user as a 'danger-alert' class div
    if request.method == 'GET':
      if session['code'] != request.args.get('code'): #If the code cookie does not exist or it is not the same as the parameter in the URl, then the user should not have access to this page
        flash("You do not have sufficient permissions to access this page", "danger")
        return redirect(url_for("index"))
    if request.method == 'POST':
      password = request.form['password']
      confirm_password = request.form['confirm_password']
      if not re.match(PW_PAT, password): #Regex check to see if the password follows the regex rules set above
         errors.append('Your password must only contain letters, numbers, and a full stop')
      if len(password) < 8: #Passwords must be at least 8 characters long to ensure strong and secure password
         errors.append('Your password must be at least 8 characters long')
      if not confirm_password == password: #Check to see if the passwords match
         errors.append('Your password does not match')
      if not errors:
        #Find the UserID of the user whose email we are performing account operations on
        c.execute("SELECT UserID from adminEmails WHERE Email=\'{}\'".format(session['email']))
        user_id = c.fetchone()[0]
        #Find the Username of the user with that UserID in order to use it for hashing
        c.execute("SELECT Username from Users WHERE UserID={}".format(user_id))
        username = c.fetchone()[0]
        hashed_password = pbkdf2_sha256.hash(password, salt=bytes(username,encoding="ascii")) #Hashes the password that will be uploaded and salts it with the user's username
        #Update the password in the database
        c.execute("UPDATE users SET Password=? WHERE UserID=?;",(hashed_password,user_id))
        conn.commit()
        conn.close()
        flash('Your password has been reset. You may now log in', 'success')
        return redirect(url_for('login'))
    return render_template('change_password.html', title="Change Password", errors=errors)
  return redirect(url_for('forgotten_password'))

@app.route("/verification", methods=['GET','POST'])
def verification():
  if 'logged_in' not in session: #Login check as the user must not be logged in to access this page
    errors = [] #Array where each element is a string containing information about any errors which will be displayed to the user as a 'danger-alert' class div
    if request.method == 'POST':
      conn = sqlite3.connect("GoClubOnline.db")
      c = conn.cursor()
      username = session['username']
      password = session['password']
      if request.form['verification_code'] == session['verification_code']: #If the code that the user has input is equal to the code stored in the cookie (which was generated when the email was sent)
        if (datetime.now()-session['verification_time']).total_seconds() <= 600: #If the time since the time stored in the 'verification_time' cookie is less than 600 seconds (10 minutes) then the code has not yet expired
          copy2(os.path.join("./gco/static/img/", "default.jpg"), os.path.join(app.config['UPLOAD_FOLDER'], username+".jpg")) #Generate the new profile picture for the user by copying the default profile picture image under the user's username
          hashed_password = pbkdf2_sha256.hash(password, salt=bytes(username,encoding="ascii")) #Hashes the password that will be uploaded and salts it with the user's username
          c.execute("INSERT INTO users VALUES (NULL,?,?,?,?,?,?);",(True,username,hashed_password,".jpg",date.today(),True)) #SQL statement to insert new admin user into the 'users' table with all of the relevant information (IsAdmin = True)
          c.execute("SELECT UserID FROM users WHERE Username='{}'".format(session['username']))
          user_id = c.fetchone()[0]
          #Insert the email into the table of admin emails which will be used to check if the email is taken in the future and whose email belongs to which account
          c.execute("INSERT INTO adminEmails VALUES (?,?);",(user_id,session['email']))
          conn.commit()
          conn.close()
          flash('An account for ' + username + ' has been created. You can now log in.', 'success')
          return redirect(url_for('login'))
        else:
          errors.append("Your verification code has expired. Please register again")
    return render_template('verification.html', title='Verification', errors=errors)
  flash("You must be logged out to do that", "warning")
  return redirect(url_for('index'))

@app.route("/games", methods=['GET','POST'])
def games():
  if 'logged_in' not in session: #Login check to make sure that the user is logged in
    flash("You must be logged in to do that.", 'warning')
    return redirect(url_for('login'))
  conn = sqlite3.connect("GoClubOnline.db")
  c = conn.cursor()

  my_live_games = [] #Stores the relevant info (to be displayed to the user) of all live games the user is in
  c.execute("SELECT GameID, PlayerTwoID, PlayerToMove FROM games WHERE PlayerOneID={} AND (WinnerID = 0 OR WinnerID IS NULL)".format(session['user_id']))
  for i in c.fetchall():
    opponent_id = i[1]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[1]))
    username = c.fetchone()[0]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[2]))
    player_to_move = c.fetchone()[0]
    my_live_games.append([i[0],username,player_to_move,opponent_id])
  c.execute("SELECT GameID, PlayerOneID, PlayerToMove FROM games WHERE PlayerTwoID={} AND (WinnerID = 0 OR WinnerID IS NULL)".format(session['user_id']))
  #The query must be done twice as it is possible they could be player one in some games and player two in others
  for i in c.fetchall():
    opponent_id = i[1]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[1]))
    username = c.fetchone()[0]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[2]))
    player_to_move = c.fetchone()[0]
    my_live_games.append([i[0],username,player_to_move,opponent_id])

  my_friends_live_games = [] #Stores the relevant info (to be displayed to the user) of all live games that the user's friends are in
  friends = Friendship.getFriends(User(session['user_id']))
  if len(friends) != 0: #If they have friends on this account
    for friend_id in friends:
      c.execute("SELECT GameID, PlayerOneID, PlayerTwoID FROM games WHERE PlayerOneID={} AND (WinnerID = 0 OR WinnerID IS NULL)".format(friend_id[0]))
      for i in c.fetchall():
        c.execute("SELECT Username FROM users WHERE UserID={}".format(i[1]))
        player_one = c.fetchone()[0]
        c.execute("SELECT Username FROM users WHERE UserID={}".format(i[2]))
        player_two = c.fetchone()[0]
        my_friends_live_games.append([i[0],player_one,player_two])
      #The query must be done twice as it is possible they could be player one in some games and player two in others
      c.execute("SELECT GameID, PlayerOneID, PlayerTwoID FROM games WHERE PlayerTwoID={} AND (WinnerID = 0 OR WinnerID IS NULL)".format(friend_id[0]))
      for i in c.fetchall():
        c.execute("SELECT Username FROM users WHERE UserID={}".format(i[1]))
        player_one = c.fetchone()[0]
        c.execute("SELECT Username FROM users WHERE UserID={}".format(i[2]))
        player_two = c.fetchone()[0]
        my_friends_live_games.append([i[0],player_one,player_two])

  my_past_games = [] #Stores the relevant info (to be displayed to the user) of all games the user has been in that is complete (a winner has been declared)
  c.execute("SELECT GameID, PlayerTwoID, WinnerID FROM games WHERE PlayerOneID={} AND WinnerID > 0".format(session['user_id']))
  for i in c.fetchall():
    opponent_id = i[1]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[1]))
    username = c.fetchone()[0]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[2]))
    player_to_move = c.fetchone()[0]
    my_past_games.append([i[0],username,player_to_move,opponent_id])
  c.execute("SELECT GameID, PlayerOneID, WinnerID FROM games WHERE PlayerTwoID={} AND WinnerID > 0".format(session['user_id']))
  for i in c.fetchall():
    opponent_id = i[1]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[1]))
    username = c.fetchone()[0]
    c.execute("SELECT Username FROM users WHERE UserID={}".format(i[2]))
    player_to_move = c.fetchone()[0]
    my_past_games.append([i[0],username,player_to_move,opponent_id])

  conn.commit()
  conn.close()
  return render_template('games.html', title="Games", my_live_games=my_live_games, my_friends_live_games=my_friends_live_games, my_past_games=my_past_games, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))


@app.route("/games/<int:game_id>", methods=['GET','POST'])
def game_page(game_id):
  if 'logged_in' not in session:
    flash("You must be logged in to do that.", 'warning')
    return redirect(url_for('login'))
  conn = sqlite3.connect("GoClubOnline.db") #The connection to the database is established
  c = conn.cursor() #The command that will create the table is set to use the provider and filepath passed as a parameter to connect with

  c.execute("SELECT COUNT(*) FROM games WHERE GameID={}".format(game_id))
  if c.fetchone()[0] == 0: #game_id is a parameter in the URL, if the user manually inputs a game_id of a game that does not exist then they must be redirected to another page
    flash("This game does not exist","warning")
    return redirect(url_for('games'))

  #state is a parameter in the URL which is used to determine which state of the board to show to the user. If there is no parameter in the URL or it is not matched as being a numeric-only string, then it is set to -1 to signify the latest state. 0 is the beginning state
  state_no = int(request.args.get('state')) if re.match(r'[0-9]+',str(request.args.get('state'))) else -1

  #Variables initialised to be modified later
  colou,error="",""
  prev_placed_stone = []
  pass_request = False
  winner_id = 0
  dead_stones = []
  players = [[],[]]

  #Get statistics for each user to be displayed on the page
  c.execute("SELECT PlayerOneID, PlayerTwoID FROM games WHERE GameID = {}".format(game_id))
  player_ids = c.fetchone()
  for i in range(2):
    #Get username
    c.execute("SELECT Username FROM users WHERE UserID={}".format(player_ids[i]))
    players[i].append(c.fetchone()[0])
    #Get amount of wins
    c.execute("SELECT COUNT(*) FROM games WHERE WinnerID={}".format(player_ids[i]))
    players[i].append(c.fetchone()[0])
    #Get total amount of games played (not including live games)
    c.execute("SELECT COUNT(*) FROM games WHERE (PlayerOneID={0} OR PlayerTwoID={0}) AND WinnerID > 0".format(player_ids[i]))
    players[i].append(c.fetchone()[0])
    #Get rating from the 'stats' table
    c.execute("SELECT Rating FROM stats WHERE UserID={}".format(player_ids[i]))
    players[i].append(c.fetchone()[0])

  #Get the profile pictures of both users
  c.execute("SELECT ImageFile FROM users WHERE UserID={}".format(player_ids[0]))
  p1image = c.fetchone()[0]
  c.execute("SELECT ImageFile FROM users WHERE UserID={}".format(player_ids[1]))
  p2image = c.fetchone()[0]

  #Get the dead stones RLE stored with the game in case dead stones have been submitted
  c.execute("SELECT DeadStones FROM games WHERE GameID={}".format(game_id))
  dead_stones_query = c.fetchone()[0]
  if dead_stones_query == None: #If the DeadStones field is blank
    dead_stones = [] #There are no positions where a dead stone exists
  else: #Else, if there is an RLE for the dead stones
    dead_stones_temp = convertGameDataOfStateToArray(parseGameDataOfState(dead_stones_query)) #Convert the RLE into a 2D array of "X"s (dead stones) and "U"s (non-dead stones)
    for row in range(9):
      for col in range(9):
        if dead_stones_temp[row][col] == "X": #If there is an "X" in the 2D array
          dead_stones.append([row*65+35,col*65+35]) #Append its position to the dead_stones array (to pass to the page) and convert into pixel coordinates so the page knows where to place it on the canvas tag on the HTML page by using Javascript

  #Get the WinnerID and PassRequest boolean value for the current game that is being viewed
  c.execute("SELECT PassRequest,WinnerID FROM games WHERE GameID={}".format(game_id))
  queryResult = c.fetchone()
  if queryResult[0] == True:
    pass_request = True
  winner_id = queryResult[1]

  #Get the spectators of the game (i.e. people who are allowed to view the board - admins and one of either of the players' friends)
  c.execute("SELECT PlayerOneID, PlayerTwoID FROM games WHERE GameID={}".format(game_id))
  queryResult = c.fetchone()
  playerOne = User(queryResult[0]) #Creating an instance of the User class of Player One in the game
  playerTwo = User(queryResult[1]) #Creating an instance of the User class of Player TWo in the game
  spectator_ids = [] #List of UserIDs of users that are allowed to view the game
  playerOne_friends = Friendship.getFriends(playerOne) #Get UserIDs of friends of playerOne
  playerTwo_friends = Friendship.getFriends(playerTwo) #Get UserIDs of friends of playerTwo
  for i in (playerOne_friends + playerTwo_friends):
    spectator_ids.append(i[0])
  spectator_ids = list(set(spectator_ids) - {playerOne.record['UserID'], playerTwo.record['UserID']})

  #If the user is not admin and is not a spectator or a player who is part of the game then they should not be allowed to access this page
  if 'is_admin' not in session:
    if session['user_id'] not in spectator_ids and session['user_id'] != playerOne.record['UserID'] and session['user_id'] != playerTwo.record['UserID']:
      flash("You do not have sufficient permissions to access this page", "danger")
      return redirect(url_for("index"))

  #Get the UserID of the player whose turn it is to move
  c.execute("SELECT PlayerToMove FROM games WHERE GameID={}".format(game_id))
  player_to_move = c.fetchone()[0]

  board = Board(game_id,state_no) #Create an instance of the Board class of the board in the game
  board_array = board.getBoardArray() #Generate the 2D array of the board so that algorithms can be performed on it rather than having the data as RLE

  #Determine the colour of the stone of the PlayerToMove, which is done through the amount of states there are for the game. Even number of states = black's turn to move and vice versa
  c.execute("SELECT GameData FROM gameStates WHERE GameID = {}".format(game_id))
  all_game_data = c.fetchall()
  game_state = len(all_game_data)
  if (game_state) % 2 == 0:
    colour="black"
  else:
    colour="white"

  #Determine the position of the stone that was previously placed so that it can be displayed on the board to improve the overall look and gameplay
  if game_state > 1: #If the state_no is bigger than 1, then either there are no stones placed or only one placed
    if state_no >= 2 or state_no == -1:
      if state_no == -1: #If the state being viewed is the live game state
        c.execute("SELECT GameData FROM games WHERE GameID = {}".format(game_id))
        current_game_data = (game_state,c.fetchone()[0])
        c.execute("SELECT StateNo, GameData FROM gameStates WHERE GameID = {} AND StateNo = {}".format(game_id,game_state-1))
        prev_game_data = c.fetchone()
        queryResult = (prev_game_data, current_game_data)
      else: #If the board state is neither live, the beginning state, nor the first-stone-placed state
        c.execute("SELECT StateNo, GameData FROM gameStates WHERE GameID = {} AND (StateNo = {} OR StateNo = {})".format(game_id,state_no,state_no-1))
        queryResult = c.fetchall()
      #queryResult is a tuple containing two board states. However, it is not possible to know which is the previous board state
      prev_state = queryResult[0][1] if queryResult[1][0] > queryResult[0][0] else queryResult[1][1]
      current_state =  queryResult[1][1] if queryResult[1][0] > queryResult[0][0] else queryResult[0][1]
      #Now that both are clarified, we can convert the RLE of the board state into 2D board arrays to compare between them
      current_state_array = convertGameDataOfStateToArray(parseGameDataOfState(current_state))
      prev_state_array = convertGameDataOfStateToArray(parseGameDataOfState(prev_state))
      for state_row in range(9):
        for state_col in range(9):
          if (current_state_array[state_row][state_col] == "B" or current_state_array[state_row][state_col] == "W") and prev_state_array[state_row][state_col] == "U": #The previously placed stone would be where in the previous state, there was an empty (unassigned) position, and in the current state there is a stone, so we do a check on each position that follows these exact conditions
            prev_placed_stone = [state_row,state_col] #If the conditions are met, then we have found the previously placed stone and can pass this onto the page as a parameter
    elif state_no == 1: #If the state_no is 1, then that means the previously placed stone must be the first stone that is placed on the board as the empty board state is the 0th state
      c.execute("SELECT GameData FROM gameStates WHERE GameID={} AND StateNo=1".format(game_id))
      queryResult = c.fetchone()[0]
      current_state_array = convertGameDataOfStateToArray(parseGameDataOfState(queryResult)) #Convert the RLE into a 2D array
      for state_row in range(9):
        for state_col in range(9):
          if current_state_array[state_row][state_col] != "U": #Check each position until one where it is not empty is found
            prev_placed_stone = [state_row,state_col] #That position is the position of the previously placed stone, so we have found it and can pass this onto the page as a parameter

  if request.method == 'POST': #If the user submits a post request (i.e. wants to perform an action on the page)
    #First, find out who the new player to move is after this turn has been taken
    new_player_to_move = [playerOne.record['UserID'],playerTwo.record['UserID']]
    new_player_to_move.remove(player_to_move)
    if request.form.get('forfeit_game') == "Forfeit Game": #If the user confirms their choice to forfeit the game
      #Set the winner to be the player that wasn't the one who pressed forfeit
      c.execute("UPDATE games SET WinnerID={} WHERE GameID={}".format(new_player_to_move[0],game_id))
      conn.commit()
      #Removes the two-way relationship that made both users be in a live game in the system and thus are no longer in a live game
      c.execute("DELETE FROM gameRequests WHERE UserID={} AND RecipientID={}".format(playerOne.record['UserID'],playerTwo.record['UserID']))
      c.execute("DELETE FROM gameRequests WHERE UserID={} AND RecipientID={}".format(playerTwo.record['UserID'],playerOne.record['UserID']))
      conn.commit()
      #Change the ratings of the winner and loser accordingly
      c.execute("SELECT Rating, RatingsDeviation FROM stats WHERE UserID={}".format(session['user_id']))
      RatingOfLost, RDofLost = c.fetchone()
      c.execute("SELECT Rating, RatingsDeviation FROM stats WHERE UserID={}".format(session['user_id']))
      RatingOfWon, RDofWon = c.fetchone()
      new_RatingOfLost, new_RDofLost = determineNewRating(RDofLost,RatingOfLost,RatingOfWon,0)
      new_RatingOfWon, new_RDofWon = determineNewRating(RDofWon,RatingOfWon,RatingOfLost,1)
      #Update new ratings and RatingsDeviation (used for calculating rating) in the database for the winner and loser
      c.execute("UPDATE stats SET Rating={},RatingsDeviation={} WHERE UserID={}".format(new_RatingOfLost, new_RDofLost, session['user_id']))
      conn.commit()
      c.execute("UPDATE stats SET Rating={},RatingsDeviation={} WHERE UserID={}".format(new_RatingOfWon, new_RDofWon, new_player_to_move[0]))
    elif request.form.get('pass_move') == "Pass": #If the user confirms their choice to pass
      if not pass_request: #If the other user has not already passed
        #Update the PassRequest to be True and the new player-to-move
        c.execute("UPDATE games SET PassRequest=1,PlayerToMove={} WHERE GameID = {}".format(new_player_to_move[0],game_id))
        conn.commit()
        #Insert a new state as a 'move' has been made so there is a new state of the board now
        c.execute("INSERT INTO gameStates VALUES ({},{},'{}')".format(game_id,game_state,board.getGameData()))
      else: #If the user has passed then transition to the 'Submit Dead Stones' stage of the game, signified by setting WinnerID to 0 instead of blank or any other integer
        c.execute("UPDATE games SET PlayerToMove={},WinnerID=0 WHERE GameID={}".format(new_player_to_move[0],game_id))
      conn.commit()
      return redirect(url_for('games')+"/"+str(game_id))
    elif request.form.get('submit_dead') == "Submit Dead Stones": #If the option to Submit Dead Stones comes up (when both users pass) and the user clicks it
      dead_stones_temp = request.form.get('submit_dead_value').split(',') #'submit_dead_value' is a hidden form field which stores the positions of the dead stones - this line splits it so that each element is an array of x and y coordinates of the dead stones
      if dead_stones_temp != ['']: #If dead stones have been submitted
        for i in range(0,len(dead_stones_temp),2): #For each pair of coordinates stored in the hidden field,
          dead_stones.append([int((int(dead_stones_temp[i])-35)/65),int((int(dead_stones_temp[i+1])-35)/65)]) #Converts the coordinates of each dead stone into row and column positions of the 2D array
        c.execute("UPDATE games SET PlayerToMove={},DeadStones=\'{}\' WHERE GameID = {}".format(new_player_to_move[0],deadStonesToRLE(dead_stones),game_id)) #Converts the board from a 2D array into RLE so that it can be stored in the database for the other user to retrieve
      else: #If no dead stones have been submitted
        c.execute("UPDATE games SET PlayerToMove={}, DeadStones=\'{}\' WHERE GameID = {}".format(new_player_to_move[0],"81U",game_id))
      conn.commit()
      return redirect(url_for('games')+"/"+str(game_id))
    elif request.form.get('accept_dead'): #If the user accepts the dead stones submitted by the other user
      opposite_colour = "white" if colour == "black" else "black"
      dead_stones_pos = []
      for i in dead_stones:
        dead_stones_pos.append([int((i[0]-35)/65),int((i[1]-35)/65)]) #Converts the coordinates of each dead stone into row and column positions of the 2D array
      #Prisoners = captured stones, so all relevant dead stones must be added onto each user's stats
      whitePrisoners = 0
      blackPrisoners = 0
      for row, col in dead_stones_pos:
        if board.getBoardArray()[row][col].getRLEcode() == "B":
          blackPrisoners += 1
        elif board.getBoardArray()[row][col].getRLEcode() == "W":
          whitePrisoners += 1
      board.removeStones(dead_stones_pos,game_id) #Removes the dead stones from the board so that they won't be included when counting territory

      #Prisoners statistic for each user must be updated because of the dead stones being removed from the board, so they are 'captured'
      c.execute("SELECT Prisoners FROM stats WHERE UserID={}".format(playerOne.record['UserID']))
      oldWhitePrisoners = c.fetchone()[0]
      c.execute("SELECT Prisoners FROM stats WHERE UserID={}".format(playerTwo.record['UserID']))
      oldBlackPrisoners = c.fetchone()[0]
      c.execute("UPDATE stats SET Prisoners={} WHERE UserID={}".format(oldWhitePrisoners+whitePrisoners,playerOne.record['UserID']))
      c.execute("UPDATE stats SET Prisoners={} WHERE UserID={}".format(oldBlackPrisoners+blackPrisoners,playerTwo.record['UserID']))
      conn.commit()

      black_territory = getTerritory(board.getBoardArray(),"B","W") #Returns black's territory as an integer
      white_territory = getTerritory(board.getBoardArray(),"W","B") #Returns white's territory as an integer
      winner_id = playerOne.record['UserID'] if len(black_territory) > (6.5+len(white_territory)) else playerTwo.record['UserID'] #White gets a 6.5 komi (meaning they automatically get +6.5 territory), therefore a draw is not possible in Go
      #End the game by declaring a winner depending on winner_id which is set by whoever has more territory
      c.execute("UPDATE games SET WinnerID={} WHERE GameID={}".format(winner_id,game_id))
      conn.commit()
      c.execute("DELETE FROM gameRequests WHERE UserID={} AND RecipientID={}".format(playerOne.record['UserID'],playerTwo.record['UserID']))
      c.execute("DELETE FROM gameRequests WHERE UserID={} AND RecipientID={}".format(playerTwo.record['UserID'],playerOne.record['UserID']))

      loser_id = playerOne.record['UserID'] if winner_id == playerTwo.record['UserID'] else playerTwo.record['UserID']

      #Update ratings of the winner and loser accordingly and store in the database
      c.execute("SELECT Rating, RatingsDeviation FROM stats WHERE UserID={}".format(session['user_id']))
      RatingOfLost, RDofLost = c.fetchone()
      c.execute("SELECT Rating, RatingsDeviation FROM stats WHERE UserID={}".format(session['user_id']))
      RatingOfWon, RDofWon = c.fetchone()
      new_RatingOfLost, new_RDofLost = determineNewRating(RDofLost,RatingOfLost,RatingOfWon,0)
      new_RatingOfWon, new_RDofWon = determineNewRating(RDofWon,RatingOfWon,RatingOfLost,1)
      c.execute("UPDATE stats SET Rating={},RatingsDeviation={} WHERE UserID={}".format(new_RatingOfLost, new_RDofLost, session['user_id']))
      conn.commit()
      c.execute("UPDATE stats SET Rating={},RatingsDeviation={} WHERE UserID={}".format(new_RatingOfWon, new_RDofWon, new_player_to_move[0]))
    elif request.form.get('reject_dead'): #If the user rejects the dead stones submitted by the other user
      #Set PassRequest and DeadStones and WinnerID to 0, meaning the game continues on as usual
      c.execute("UPDATE games SET PlayerToMove={}, WinnerID=null, DeadStones=null, PassRequest=0 WHERE GameID = {}".format(new_player_to_move[0],game_id))
      conn.commit()
      return redirect(url_for('games')+"/"+str(game_id))
    elif request.form.get('submit_move')[:13] == "Submit Move: ": #If the user submits a move
      if re.match(r'[ABCDEFGHI][123456789]',request.form.get('submit_move')[-2:]): #Regex check to see if a valid move has been made, see Data Dictionary in Design of the documentation
        #Convert the Go position of the stone that will be placed into coordinates that can be used in a 2D array, i.e. a row and column value
        row,col = PosToCoords(request.form.get('submit_move')[-2:])

        #test_board is an instance of the Board class that is used to make checks on certain rules such as no-suicidal-moves and Ko without updating the actual board that will be uploaded to the database after the move has been complete
        test_board = Board(game_id,state_no)

        if colour=="black":
          test_board = test_board.placeStoneForChecks(row,col,Black())
        else:
          test_board = test_board.placeStoneForChecks(row,col,White())
        opposite_colour = "white" if colour == "black" else "black"

        #Get a list of all the positions of the captured stones in the 2D array and a boolean value that states whether the move is suicidal or not
        captured_stones, suicidal = getCapturedStonesAndIsSuicidal(test_board.getBoardArray(),colour.capitalize()[0],row,col,opposite_colour.capitalize()[0])

        #Remove the captured stones on the test board
        test_board = test_board.removeStonesForChecks(captured_stones)

        #Ko is when a stone is captured such that the resultant board is the exact same as the board from two moves before it, and is considered illegal in the rules of Go
        if game_state > 0: #Ko can only be checked if there are more than 0 states in the game already
          c.execute("SELECT GameData FROM gameStates WHERE GameID={} AND StateNo={}".format(game_id,game_state-1)) #Return board data from two moves ago
          queryResult = c.fetchone()[0]
          if queryResult == test_board.getGameData(): #If the board data from two moves ago is the same as the resultant board
            flash("Illegal Ko Move", "game_error")
            return redirect(url_for('games')+"/"+str(game_id))

        #A suicidal move is, by definition, a move that does not capture any other stones in the process and is actually one that would kill itself if placed in that position
        if captured_stones == [] and suicidal: #If the move does not capture any stones and is suicidal
          flash("Move is suicidal", "game_error")
          return redirect(url_for('games')+"/"+str(game_id))

        #If the code has not yet returned a web page to the user, then that means the move must be legal and so the real operations may begin
        #Place the stone depending on the user's stone colour onto the 2D board array
        if colour=="black":
          board.placeStone(row,col,Black(),game_id)
        else:
          board.placeStone(row,col,White(),game_id)

        #Remove the captured stones (determined above) on the board
        board.removeStones(captured_stones,game_id)

        #Insert a new game state as a move has been made
        c.execute("INSERT INTO gameStates VALUES ({},{},'{}')".format(game_id,game_state,board.getGameData()))
        conn.commit()

        #Update the user's stats by increasing the moves made by 1 and prisoners by the amount of prisoners captured
        c.execute("SELECT MovesMade,Prisoners FROM stats WHERE UserID={}".format(session['user_id']))
        queryResult = c.fetchone()
        c.execute("UPDATE stats SET MovesMade={},Prisoners={} WHERE UserID={}".format(queryResult[0]+1,queryResult[1]+len(captured_stones),session['user_id']))
        #Update the game data by setting a new player to move (i.e. passing on your turn)
        c.execute("UPDATE games SET PlayerToMove={}, PassRequest=0 WHERE GameID={}".format(new_player_to_move[0],game_id))
        conn.commit()
        return redirect(url_for('games') + "/" + str(game_id))
      else:
        flash("Please place a stone before submitting a move","game_error")

  conn.commit()
  conn.close()
  return render_template('game_page.html', title="Game", p1image=p1image, p2image=p2image, players=players, dead_stones_query = dead_stones_query,dead_stones=dead_stones, game_id=str(game_id), pass_request=pass_request, winner_id=winner_id, prev_placed_stone = prev_placed_stone, max_state_no = game_state-1, colour=colour, illegalMoves=board.getIllegalMoves(), pos_of_whites=board.getPosOfWhites(), pos_of_blacks=board.getPosOfBlacks(), player_to_move=player_to_move, playerOne_username=playerOne.record['Username'],playerTwo_username=playerTwo.record['Username'], p1_id = playerOne.record['UserID'], spectator_ids = spectator_ids, notifications=getNotifs(session['user_id']), notificationsNo=getNotifNo(session['user_id']), gamesNo=getGameNo(session['user_id']))
