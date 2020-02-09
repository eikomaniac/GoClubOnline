import sqlite3

class Record:
  #Fetches all records from a certain table
  def getAllRecords(self,table):
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("SELECT * FROM ?;",(table))
    queryResult = c.fetchall()
    conn.close()
    return queryResult
  #Fetches all records from a certain UserID in a table
  def getAllRecordsOfID(self,table,user_id):
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("SELECT * FROM ? WHERE UserID=?;",(table,user_id))
    queryResult = c.fetchall()
    conn.close()
    return queryResult

  #Fetch record data stored in the object of the User
  def getRecord(self):
    return self.record

  #Returns the amount of rows in a column by using an aggregate SQL function
  def getCount(self,table,user_id):
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM ? WHERE UserID = ?;",(table,user_id))
    count = c.fetchone()[0]
    conn.close()
    return count

#This class represents a row in the 'users' table and inherits from Record, gaining all of its methods
class User(Record):
  TABLE = "users"
  PRIMARY_KEY = "UserID"

  def __init__(self, user_id):
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE UserID=?",(user_id,))
    queryResult = c.fetchone()
    self.record = { #Stores, as a dictionary, the fields of each attribute of a certain record
      "UserID" : user_id,
      "IsAdmin" : queryResult[1],
      "Username" : queryResult[2],
      "Password" : queryResult[3],
      "ImageFile" : queryResult[4],
      "DateCreated" : queryResult[5],
      "IsActive" : queryResult[6]
      }
    conn.commit()
    conn.close()

#This class represents a row in the 'friendships' table and inherits from Record, gaining all of its methods
class Friendship(Record):
  TABLE = "friendships"
  PRIMARY_KEY = "UserID"

  def __init__(self, user_id):
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("SELECT FriendID FROM friendships WHERE UserID=?",(user_id,))
    queryResult = c.fetchone()
    self.record = {
      "UserID" : user_id,
      "FriendID" : queryResult[0]
      }
    conn.commit()
    conn.close()

  #Uses a cross-table parameterised SQL query to retrieve the IDs of any user that have a relationship in 'friendships' going both ways, i.e. are friends
  def getFriends(user):
    user_id = user.getRecord()["UserID"]
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("""SELECT f1.FriendID
             FROM friendships AS f1
             JOIN friendships AS f2 ON f1.UserID = f2.FriendID AND f1.FriendID = f2.UserID
             JOIN users ON f1.UserID = users.UserID
             WHERE users.UserID = ?""",(user_id,))
    queryResult = c.fetchall()
    conn.close()
    return queryResult

  #Returns the IDs of the users that have received a friend request from a specific user
  def getRequestFrom(user):
    user_id = user.getRecord()["UserID"]
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("""SELECT UserID FROM friendships WHERE FriendID = ?
           EXCEPT
           SELECT f1.FriendID
           FROM friendships AS f1
           JOIN friendships AS f2 ON f1.UserID = f2.FriendID AND f1.FriendID = f2.UserID
           JOIN users ON f1.UserID = users.UserID
           WHERE users.UserID = ?""",(user_id,user_id))
    queryResult = c.fetchall()
    conn.close()
    return queryResult

  #Returns the IDs of the users that have sent friend requests to a specific user
  def getRequestTo(user):
    user_id = user.getRecord()["UserID"]
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("""SELECT FriendID FROM friendships WHERE UserID = ?
           EXCEPT
           SELECT UserID FROM friendships WHERE FriendID = ?""",(user_id,user_id))
    queryResult = c.fetchall()
    conn.close()
    return queryResult

#This class represents a row in the 'gameRequests' table and inherits from Record, gaining all of its methods
class GameRequest(Record):
  TABLE = "gameRequests"
  PRIMARY_KEY = "UserID"

  def __init__(self, user_id):
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("SELECT RecipientID FROM gameRequests WHERE UserID={}".format(user_id))
    queryResult = c.fetchone()
    self.record = {
      "UserID" : user_id,
      "RecipientID" : queryResult[0]
      }
    conn.commit()
    conn.close()

  #Uses a cross-table parameterised SQL query to retrieve the IDs of any user that have a relationship in 'gameRequests' going both ways, i.e. are in a live game
  def getLiveGames(user):
    user_id = user.getRecord()["UserID"]
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("""SELECT p1.RecipientID
           FROM gameRequests AS p1
           JOIN gameRequests AS p2 ON p1.UserID = p2.RecipientID AND p1.RecipientID = p2.UserID
           JOIN users ON p1.UserID = users.UserID
           WHERE users.UserID = {}""".format(user_id))
    queryResult = c.fetchall()
    conn.close()
    return queryResult

  #Returns the IDs of the users that have received a game request from a specific user
  def getRequestFrom(user):
    user_id = user.getRecord()["UserID"]
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("""SELECT UserID FROM gameRequests WHERE RecipientID = {0}
           EXCEPT
           SELECT p1.RecipientID
           FROM gameRequests AS p1
           JOIN gameRequests AS p2 ON p1.UserID = p2.RecipientID AND p1.RecipientID = p2.UserID
           JOIN users ON p1.UserID = users.UserID
           WHERE users.UserID = {0}""".format(user_id))
    queryResult = c.fetchall()
    conn.close()
    return queryResult

  #Returns the IDs of the users that have sent game requests to a specific user
  def getRequestTo(user):
    user_id = user.getRecord()["UserID"]
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("""SELECT RecipientID FROM gameRequests WHERE UserID = {0}
           EXCEPT
           SELECT UserID FROM gameRequests WHERE RecipientID = {0}""".format(user_id))
    queryResult = c.fetchall()
    conn.close()
    return queryResult

#Object for the board used in the game of Go containing all necessary attributes and operations to perform on it
class Board:
  def __init__(self, game_id, state_no):
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    self.__game_id = game_id #ID of the game
    self.__state_no = state_no #State of the game (-1 if not viewing previous states)
    self.__board_array = [[] for i in range(9)] #Generates a two-dimensional array of 8 rows and 0 columns (as of yet)

    if state_no == -1: #If not viewing previous states
      c.execute("SELECT GameData FROM games WHERE GameID={}".format(game_id))
      self.__game_data = c.fetchone()[0] #Get the game data from the current state of the game (live)
    else: #Else if viewing a previous state of the game
      c.execute("SELECT GameData FROM gameStates WHERE GameID={} AND StateNo={}".format(game_id,state_no))
      self.__game_data = c.fetchone()[0] #Retrieve the game data from the state in the 'gameStates' table

    conn.close()
    self.__game_data_array = [] #
    self.__illegalMoves = [] #Stores positions of moves where the stone is not allowed to be placed on the board
    self.__pos_of_blacks = [] #Stores the positions of all black stones on the board (empty if none)
    self.__pos_of_whites = [] #Stores the positiosn of all white stones on the board (empty if none)

    #Convert the RLE into a two-dimensional array where
    self.parseGameData()
    self.convertGameDataToArray()
    self.createBoardData()

  #This subroutine turns RLE data such as “5U3BW2B3WU” into [“5U”,”3B”,”W”,”2B”,”3W”,”U”]
  def parseGameData(self):
    scan_index = 0 #value used when searching through the string
    cut_index = 0 #value used so that the program knows when to “cut” the string for the relevant details
    while scan_index < len(self.__game_data):
      if self.__game_data[scan_index] in ["B","W","U"]:
        self.__game_data_array.append(self.__game_data[cut_index:scan_index+1])
        cut_index = scan_index+1
      scan_index += 1

  #This subroutine converts the RLE array (created from before) into a two-dimensional array where each element is an individual stone that is represented by an object of the relevant class.
  def convertGameDataToArray(self):
    sum_of_spaces = 0 #Used to calculate which row of the board the stone should be on
    for i in self.__game_data_array:
      row = sum_of_spaces // 9
      if len(i) == 1: #If the length is 1, then it must be only be a character
        if i == "B":
          self.__board_array[row].append(Black())
        if i == "W":
          self.__board_array[row].append(White())
        if i == "U":
          self.__board_array[row].append(Unassigned())
        sum_of_spaces += 1
      else: #If the length is greater than 1, then it is a number showing the amount of occurrences in a row
        length = int(i[:-1]) #This gets the number of occurrences before the character
        for j in range(length):
          row = sum_of_spaces // 9
          if i[-1] == "B": #Checks to see what stone is being repeated occur_length many times
            self.__board_array[row].append(Black())
          if i[-1] == "W":
            self.__board_array[row].append(White())
          if i[-1] == "U":
            self.__board_array[row].append(Unassigned())
          sum_of_spaces+=1

  #This subroutine appends all the positions of illegal moves, black stones, and white stones in terms of pixel coordinates for the canvas used on the webpage with so that JavaScript can display it in the correct position
  def createBoardData(self):
    for row in range(len(self.__board_array)):
      for col in range(len(self.__board_array[row])):
        if self.__board_array[row][col].getRLEcode() != Unassigned().getRLEcode():
          self.__illegalMoves.append([35+65*row, 35+65*col])
          if self.__board_array[row][col].getRLEcode() == Black().getRLEcode():
            self.__pos_of_blacks.append([35+65*row, 35+65*col])
          elif self.__board_array[row][col].getRLEcode() == White().getRLEcode():
            self.__pos_of_whites.append([35+65*row, 35+65*col])

  def getBoardArray(self):
    return self.__board_array

  def getPosOfBlacks(self):
    return self.__pos_of_blacks

  def getPosOfWhites(self):
    return self.__pos_of_whites

  def getIllegalMoves(self):
    return self.__illegalMoves

  def getGameData(self):
    return self.__game_data

  def boardToRLE(self):
    tempRLE = ""
    RLEdata = ""
    #This for loop creates a string which contains ‘uncompressed’ RLE (i.e. WWWBBU instead of 3W2BU)
    for i in self.__board_array:
      for j in i:
        tempRLE += j.getRLEcode()
    tempRLE += "X" #A random character that is not U or X must be added onto the end of the string to signify EOL

    #This for loop converts uncompressed RLE into the compressed form (from WWWBBU to 3W2BU)
    RLEcount = 1
    for i in range(81):
      nextChar = tempRLE[i+1]
      if tempRLE[i] == nextChar: #If the next character is the same as the current character
        RLEcount += 1
      else:
        if RLEcount == 1: #If there is only one occurrence of the character, don't add the number before it
          RLEdata += tempRLE[i]
        else:
          RLEdata += str(RLEcount) + tempRLE[i]
        RLEcount = 1 #Reset count due to new character
    return RLEdata

  #Replaces the position on the board with the type of
  def placeStone(self,row,col,stone,game_id):
    self.__board_array[row][col] = stone
    RLEdata = self.boardToRLE()
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("UPDATE games SET GameData='{}' WHERE GameID={}".format(RLEdata,game_id))
    conn.commit()
    conn.close()

  #Replaces all stones in the positions given with the Unassigned() class but DOES NOT update the database as this is used for checking if a move is illegal
  def placeStoneForChecks(self,row,col,stone):
    self.__board_array[row][col] = stone
    self.__game_data = self.boardToRLE()
    return self

  #Replaces all stones in the positions given with the Unassigned() class and updates the database
  def removeStones(self,captured_stones,game_id):
    for row,col in captured_stones:
      self.__board_array[row][col] = Unassigned()
    RLEdata = self.boardToRLE()
    conn = sqlite3.connect("GoClubOnline.db")
    c = conn.cursor()
    c.execute("UPDATE games SET GameData='{}' WHERE GameID={}".format(RLEdata,game_id))
    conn.commit()
    conn.close()

  #Replaces all stones in the positions given with the Unassigned() class but DOES NOT update the database as this is used for checking if a move is illegal
  def removeStonesForChecks(self,captured_stones):
    for row,col in captured_stones:
      self.__board_array[row][col] = Unassigned()
    self.__game_data = self.boardToRLE()
    return self

#Class which is inherited by the specific stones (and empty space)
class Stone:
  #Returns the character which represents the stone/empty space used in RLE compression
  def getRLEcode(self):
    return self._RLEcode

class Black(Stone):
  def __init__(self):
    self._RLEcode = "B" #Code used for RLE

class White(Stone):
  def __init__(self):
    self._RLEcode = "W"

#Class for empty spaces on the board
class Unassigned(Stone):
  def __init__(self):
    self._RLEcode = "U"
