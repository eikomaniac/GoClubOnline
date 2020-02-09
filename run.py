#Imports required modules from db.py and app.py
from gco import app
from gco.db import *

#Required code to run Flask microframework
if __name__ == '__main__':
    db_setup() #Runs the DDL statements in db.py
    app.run(debug=True)
