from flask import flash, redirect, url_for
from gco.classes import *
from math import sqrt, pi, log

#http://www.glicko.net/glicko/glicko.pdf, let t=1
#RD = Current Ratings Deviation, r = Current Rating, ri = Current Rating of Opponent, si = Outcome of the game (1 = Win, 0.5 = Draw (not possible in Go), 0 = Loss)
def determineNewRating(RD,r,ri,si):
    #Step 1: Determine Ratings Deviation - measures the accuracy of a player's rating. One RD = One standard deviation.
    c2 = (350**2-50**2)/30
    RD = min(sqrt(RD**2+c2),350)

    #Step 2: Determine New Rating
    q=log(10)/400
    g = 1/sqrt(1+(3*q**2*RD**2)/pi**2)
    E = 1/(1+10**((g*(r-ri))/-400))
    d2 = 1/(q**2*g**2*E*(1-E))

    r += (q/(1/RD**2 + 1/d2))*g*(si-E)

    #Step 3: Determine New Ratings Deviation
    RD = sqrt((1/RD**2 + 1/d2)**-1)

    return r, RD

#First function that is called to determine the amount of territory a certain colour has. NOT the floodfill algorithm! (yet)
def getTerritory(board,colour,opposite_colour):
    #These variables are global as they are to be accessed by two functions yet cannot be passed as a parameter to the other function
    global visited
    global territory
    global potential_territory
    global is_territory
    potential_territory = []

    #Potential territory would be any positions on the board that are empty
    for row in range(9):
        for col in range(9):
            if board[row][col].getRLEcode() == "U":
                potential_territory.append([row,col])

    visited = [] #Stores each position from potential_territory that has already been visited
    territory = [] #Stores each potential "group" of territory
    is_territory = [] #For each group in territory, stores a boolean value that states whether it actually is territory or not

    #This loop runs the floodfill algorithm on positions that have not yet been visited by the algorithm and could potentially be territory
    for row,col in potential_territory:
        if [row,col] not in visited:
            territory.append([])
            is_territory.append(True)
            index = len(territory)-1
            territoryFloodfill(board,colour,row,col,opposite_colour,index)

    colour_territory_array = []
    #This for loop appends all positions in the groups in potential_territory that are actually territory, determined by is_territory.
    for i in range(len(is_territory)):
        if is_territory[i]:
            for j in territory[i]:
                colour_territory_array.append(j)

    return colour_territory_array

def territoryFloodfill(board,colour,row,col,opposite_colour,index):
    global visited #Array where each element is [row,column] of positions on the board already visited
    global territory #Array where each element is [row,column] of positions of territory
    global potential_territory
    global is_territory

    #Check if the position has not already been visited
    if not is_territory[index]:
        return

    visited.append([row,col])

    #Check if there is no stone in the current position
    if board[row][col].getRLEcode() == "U": #board is a two-dimensional array which represents the Go board
        territory[index].append([row,col])

    elif board[row][col].getRLEcode() == opposite_colour:
        is_territory[index] = False #This is because the territory of a player must be surrounded only by its own colour
        return

    elif board[row][col].getRLEcode() == colour:
        return #This position is no longer relevant so we don’t need to floodfill on it

    surrounding = [[row-1,col],[row,col+1],[row+1,col],[row,col-1]] #North, East, South, West

    for new_row,new_col in surrounding:
        if 0 <= new_row <= 8 and 0 <= new_col <= 8 and [new_row,new_col] not in visited:
            territoryFloodfill(board,colour,new_row,new_col,opposite_colour,index) #Floodfill recursion

def deadStonesToRLE(dead_stones_pos):
    tempRLE = ""
    RLEdata = ""
    board = [["U" for j in range(9)] for i in range(9)]

    #Replaces all positions on the board that should be dead with X to represent dead stones
    for row,col in dead_stones_pos:
        board[row][col] = "X"

    #This for loop creates a string which contains ‘uncompressed’ RLE (i.e. WWWBBU instead of 3W2BU)
    for i in board:
        for j in i:
            tempRLE += j
    tempRLE += "Z" #A random character that is not U or X must be added onto the end of the string to signify EOL

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

#This function turns RLE data such as “5U3BW2B3WU” into [“5U”,”3B”,”W”,”2B”,”3W”,”U”]
def parseGameDataOfState(RLEdata):
    game_data_array = []
    scan_index = 0 #value used when searching through the string
    cut_index = 0 #value used so that the program knows when to “cut” the string for the relevant details
    while scan_index < len(RLEdata):
        if RLEdata[scan_index] in ["B","W","U","X"]:
            game_data_array.append(RLEdata[cut_index:scan_index+1])
            cut_index = scan_index+1
        scan_index += 1
    return game_data_array

#This function convers the RLE array (created from before) into a two-dimensional array where each element is an individual stone that is represented by an object of the relevant class.
def convertGameDataOfStateToArray(game_data):
    board_array = [[] for i in range(9)] #Generates a two-dimensional array of 8 rows and 0 columns (as of yet)
    sum_of_spaces = 0 #Used to calculate which row of the board the stone should be on
    for i in game_data:
        row = sum_of_spaces // 9
        if len(i) == 1: #If the length is 1, then it must be only be a character
            if i == "B":
                board_array[row].append("B")
            if i == "W":
                board_array[row].append("W")
            if i == "U":
                board_array[row].append("U")
            if i == "X":
                board_array[row].append("X")
            sum_of_spaces += 1
        else: #If the length is greater than 1, then it is a number showing the amount of occurrences in a row
            length = int(i[:-1]) #This gets the number of occurrences before the character
            for j in range(length):
                row = sum_of_spaces // 9
                if i[-1] == "B": #Checks to see what stone is being repeated occur_length many times.
                    board_array[row].append("B")
                if i[-1] == "W":
                    board_array[row].append("W")
                if i[-1] == "U":
                    board_array[row].append("U")
                if i[-1] == "X":
                    board_array[row].append("X")
                sum_of_spaces+=1
    return board_array

#First function that is called to determine the captured stones after a move has been made and if the move is suicidal. NOT the floodfill algorithm! (yet)
def getCapturedStonesAndIsSuicidal(board,colour,row,col,opposite_colour):
    #These variables are global as they are to be accessed by two functions yet cannot be passed as a parameter to the other function
    global visited
    global possible_stones
    global is_capturable
    visited = [[],[],[],[]] #Stores each position that has already been visited by each of the four floodfills (for each direction from where the stone was originally placed)
    possible_stones = [[],[],[],[]] #Stores each "group" of possibly capturable stones
    is_capturable = [True,True,True,True] #For each group in possible_stones, stores a boolean value that states whether it is actually capturable
    surrounding = [[row-1,col],[row,col+1],[row+1,col],[row,col-1]]

    #This loop runs the floodfill algorithm on stones that have not yet been visited by the algorithm and could possibly be capturable
    for new_row,new_col in surrounding:
        if 0 <= new_row <= 8 and 0 <= new_col <= 8:
            index = surrounding.index([new_row,new_col])
            floodfill(colour,board,new_row,new_col,opposite_colour,index)

    captured_stones = []
    #This for loop appends all positions in the groups in possible_stones that are actually capturable, determined by each boolean value in is_capturable
    for index in range(4):
        if is_capturable[index]:
            for stone in possible_stones[index]:
                captured_stones.append((stone[0],stone[1]))

    #This function is also used to check if a move is suicidal (i.e. placing the stones kills itself).
    suicidal = True
    for i in is_capturable:
        if not i:
            suicidal = False

    return list(set(captured_stones)), suicidal

def floodfill(colour, board, row, col, opposite_colour, index):
    global visited #Array where each element is [row,column] of positions on the board already visited
    global possible_stones #Array where each element is [row,column] of positions of captured stones
    global is_capturable

    #If the set of stones is found to not be capturable, stop performing floodfill on it as it is unnecessary
    if not is_capturable[index]:
        return

    if board[row][col].getRLEcode() == opposite_colour: #board is a two-dimensional array which represents the Go board
        possible_stones[index].append([row,col])

    visited[index].append([row,col])

    #Check if there is no stone in the current position
    if board[row][col].getRLEcode() == "U":
        is_capturable[index] = False #This is because if there is an empty space in the chain of stones, then the group of stones, by definitino, cannot be captured
        return
    elif board[row][col].getRLEcode() == colour:
        return #This stone is no longer relevant so we don't need to floodfill on it

    surrounding = [[row-1,col],[row,col+1],[row+1,col],[row,col-1]] #North, East, South, West

    for new_row,new_col in surrounding:
        if 0 <= new_row <= 8 and 0 <= new_col <= 8 and [new_row,new_col] not in visited[index]:
            floodfill(colour,board,new_row,new_col,opposite_colour,index) #Floodfill recursion

#Converts positions into Go board coordinate notation (such as [2,1] -> C2)
def PosToCoords(pos):
    letters = "ABCDEFGHI"
    row = 9-int(pos[1])
    col = int(letters.index(pos[0]))
    return row,col

#Returns all the notifications a user has
def getNotifs(user_id):
    #Create instance of User class
    current_user = User(user_id)

    notif_list = []

    #Store message templates for types of notifications
    NotifTypes = {
        "GameInvite" : "has challenged you to a game of Go!",
        "FriendRequest" : "has sent you a friend request!"
        }

    #Get all friend requests sent to the user
    friendNotifs = Friendship.getRequestFrom(current_user)
    for i in friendNotifs:
        notif_list.append([i[0],NotifTypes["FriendRequest"],User(i[0]).record["Username"],User(i[0]).record["ImageFile"]])

    #Get all game requests sent to the user
    gameNotifs = GameRequest.getRequestFrom(current_user)
    for i in gameNotifs:
        notif_list.append([i[0],NotifTypes["GameInvite"],User(i[0]).record["Username"],User(i[0]).record["ImageFile"]])

    return notif_list

def mergeSort(unsorted_list, index):
    if len(unsorted_list)>1: #Base case. By definition, a list of zero or one elements is sorted
        #Recursive case. First, the array is divided into equal-sized sub-arrays consisting of the first half and second half of the list
        mid = len(unsorted_list)//2
        left_half = unsorted_list[:mid]
        right_half = unsorted_list[mid:]
        #Recursively sort both sub-arrays
        mergeSort(left_half,index)
        mergeSort(right_half,index)
        #Now merge the sorted sub-arrays
        i=0
        j=0
        k=0
        while i < len(left_half) and j < len(right_half):
            if left_half[i][index] < right_half[j][index]:
                unsorted_list[k]=left_half[i]
                i=i+1
            else:
                unsorted_list[k]=right_half[j]
                j=j+1
            k=k+1
        while i < len(left_half):
            unsorted_list[k]=left_half[i]
            i=i+1
            k=k+1
        while j < len(right_half):
            unsorted_list[k]=right_half[j]
            j=j+1
            k=k+1
    return unsorted_list

#Returns the amount of notifications a user has
def getNotifNo(user_id):
    return len(getNotifs(user_id))

#Returns the amount of games a user is currently in by using an aggregate SQL function
def getGameNo(user_id):
    conn = sqlite3.connect("GoClubOnline.db") #The connection to the database is established
    c = conn.cursor()
    #COUNT(*) function on an SQL query which returns all games where a user is either Player One or Player Two and a WinnerID has not yet been set (i.e. the game is on-going)
    c.execute("SELECT COUNT(*) FROM games WHERE (PlayerOneID = ? OR PlayerTwoID = ?) AND (WinnerID = 0 OR WinnerID IS NULL);",(user_id,user_id))
    count = c.fetchone()[0]
    conn.close() #The connection to the database is closed
    return count
