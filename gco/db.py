import sqlite3 #Imports sqlite3 module which is required for database operations

#This function sets up all tables in the database if they did not exist
def db_setup():
    #The connection to the database is established
    conn = sqlite3.connect("GoClubOnline.db")
    #The command that will create the table is set to use the provider and filepath passed as a parameter to connect with
    c = conn.cursor()

    #The following DDL statements are achieved through the execute() module in sqlite3
    c.execute("""CREATE TABLE IF NOT EXISTS 'users' (
    	'UserID'      INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        'IsAdmin'     BOOLEAN NOT NULL,
    	'Username'    VARCHAR(20) NOT NULL UNIQUE,
    	'Password'    VARCHAR(255) NOT NULL,
        'ImageFile'   VARCHAR(20) NOT NULL,
        'DateCreated' DATE NOT NULL,
        'IsActive'    BOOLEAN NOT NULL
    );""")

    c.execute("""CREATE TABLE IF NOT EXISTS 'adminEmails' (
    	'UserID'        INTEGER PRIMARY KEY UNIQUE,
        'Email'         VARCHAR(255) NOT NULL UNIQUE,
        FOREIGN KEY(UserID) REFERENCES users(UserID)
    );""")

    c.execute("""CREATE TABLE IF NOT EXISTS 'friendships' (
        'UserID'    INTEGER NOT NULL,
        'FriendID'  INTEGER NOT NULL,
        PRIMARY KEY(UserID, FriendID),
        FOREIGN KEY(UserID) REFERENCES users(UserID)
        FOREIGN KEY(FriendID) REFERENCES users(UserID)
    );""")

    c.execute("""CREATE TABLE IF NOT EXISTS 'games' (
    	'GameID'	        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    	'PlayerOneID'	    INTEGER NOT NULL,
    	'PlayerTwoID'       INTEGER NOT NULL,
    	'WinnerID'	        INTEGER,
    	'GameData'	        TEXT NOT NULL,
    	'PlayerToMove'      INTEGER NOT NULL,
    	'PassRequest'	    BOOLEAN NOT NULL,
        'DeadStones'        TEXT,
    	FOREIGN KEY(PlayerOneID) REFERENCES users(UserID),
    	FOREIGN KEY(PlayerTwoID) REFERENCES users(UserID),
    	FOREIGN KEY(WinnerID) REFERENCES users(UserID)
    );""")

    c.execute("""CREATE TABLE IF NOT EXISTS 'stats' (
    	'UserID'	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    	'Rating'	FLOAT NOT NULL,
    	'MovesMade'	INTEGER NOT NULL,
    	'Prisoners'	INTEGER NOT NULL,
        'RatingsDeviation' FLOAT NOT NULL,
	FOREIGN KEY(UserID) REFERENCES users(UserID)
    );""")

    c.execute("""CREATE TABLE IF NOT EXISTS 'gameRequests' (
        'UserID'    INTEGER NOT NULL,
        'RecipientID'  INTEGER NOT NULL,
        PRIMARY KEY(UserID, RecipientID),
        FOREIGN KEY(UserID) REFERENCES users(UserID)
        FOREIGN KEY(RecipientID) REFERENCES users(UserID)
    );""")

    c.execute("""CREATE TABLE IF NOT EXISTS 'gameStates' (
        'GameID'    INTEGER NOT NULL,
        'StateNo'    INTEGER NOT NULL,
        'GameData'    TEXT NOT NULL,
        PRIMARY KEY(GameID, StateNo),
        FOREIGN KEY(GameID) REFERENCES games(GameID)
    );""")

    #All changes are written to the database (i.e. saved)
    conn.commit()
    #The connection to the database is closed
    conn.close()
