#Imports the Flask microframework and the routes (necessary back-end code) for all pages on the website  
from flask import Flask  
  
app = Flask(__name__) #Creates the app  
  
#Configuration constants used throughout the app  
app.config['SECRET_KEY'] = 'ee6fdb88d9f2813a09c4239deb0fe2a7' #Used for encrypting cookies, must not be shown to anyone! (Will be changed before given to client)
app.config['UPLOAD_FOLDER'] = './gco/static/img/avi/'  

from gco import routes  
