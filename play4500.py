#!/usr/bin/env python

# CS4500 Assignment 6
# Nate Bessa, Dan Brown, Kyle Oestreich, Tyler Rosini

import os
import sys
import getopt
import time
import json
import pipes
import tempfile
from subprocess import PIPE, Popen

# ----------------------------------------------------
#  Game Messages:
#	A. Referee to Player Messages
#		1. Invalid Board Setup
#		2. Invalid Board Move <moveErrorType>
#		3. <position 1> <position 2> <player> <movetype>
#		4. F <position>
# 		5. <winningPlayer> Victory
#	B. Player to Referee Messages
#		1. (<position> <position>)
#		2. (initial board setup...)
# ----------------------------------------------------

# expected command line arg format:
#		./play4500 --go <n> --time/move <t>
# sample format:
#		./play4500 --go 1 --time/move 1.2ms		

# global variables
nodes = {}
ourPlayer = 0

# syntax checking function
def syntaxChecker(arguments):
	
	# valid number of arguments?
	if len(arguments) != 4:
		print >> sys.stderr, "Invalid amount of arguments."
		sys.exit(1)
	
	# is first argument --go
	if arguments[0] != '--go':
		print >> sys.stderr, "The first argument should be --go."
		sys.exit(1)
	
	# is second argument 1 or 2
	if arguments[1] != '1' and arguments[1] != '2':
		print >> sys.stderr, "The second argument should be 1 or 2 for the player number."
		sys.exit(1)
	
	# is third argument --time/move
	if arguments[2] != '--time/move':
		print >> sys.stderr, "The third argument should be --time/move."
		sys.exit(1)
	
	# check for any char in fourth argument that is not '.', a number, 'm', or 's'
	periodCount = 0
	mCount = 0
	sCount = 0
	for char in arguments[3]:
		if char == '.':
			periodCount += 1
		elif char == 'm':
			mCount += 1
		elif char == 's':
			sCount += 1
		elif char.isdigit():
			pass
		else:
			print >> sys.stderr, "Unexpected character in the time argument."
			sys.exit(1)
	if periodCount > 1 or mCount > 1 or sCount == 0 or sCount > 1:
		print >> sys.stderr, "The fourth argument is not properly formatted."
		sys.exit(1)

# parse the time argument, convert to seconds
def getTimeLimit(timeString):
	
	# split the string into the time portion and the 'ms' or 's' string
	if 'm' in timeString:
		timeSplit = timeString.find('m')
		time = float(timeString[0:timeSplit])
		time = time / 1000
	elif 's' in timeString:
		timeSplit = timeString.find('s')
		time = float(timeString[0:timeSplit])
	
	# get just the time portion
	return time
	
# take a JSON initial configuration and convert to the specification's CFG
def jsonToCFG():

	# open our own initial configuration
	initConfig = open("initConfig.json")
	test = json.load(initConfig)
	initConfig.close()
	
	# convert to CFG format specified by the professor
	output = "( "
	for piece in test:
		 output += "( " + piece["position"] + " " + piece["piece"] + " ) "
	output += ")"
	
	return output
	
# updates the board using information parsed from the referree message
def updateBoard(movingFrom, movingTo, movingPlayer, moveType):
	
	global nodes
	
	
	if int(movingPlayer) == ourPlayer:
		# updating the board for a move type "move". Just take the piece in the
		#   MoveFrom position and put it in the moveTo position. Then empty the
		#	old position
		if moveType == "move":
			#move operation
			
			delNode = nodes[movingFrom]
			piece = delNode.getPiece()
			delNode.setPiece(None)
			
			setNode = nodes[movingTo]
			setNode.setPiece(piece)
							
		elif moveType == "win":
			#win operation
			#!!! For now the same as MOVE but will need to augment enemy piece tracking in the future
			
			delNode = nodes[movingFrom]
			piece = delNode.getPiece()
			delNode.setPiece(None)
			
			setNode = nodes[movingTo]
			setNode.setPiece(piece)
				
				
		elif moveType == "lose":
			#lose operation
			# Just set the moveFrom to empty, which should delete the piece
			delNode = nodes[movingFrom]
			piece = delNode.getPiece()
			delNode.setPiece(None)
								
		elif moveType == "tie":
			#tie operation
			# Just set the moveFrom to empty, which should delete the piece
			#in the future will need to Augment Enemy board and pieces as well.
			delNode = nodes[movingFrom]
			piece = delNode.getPiece()
			delNode.setPiece(None)
					
	else:
		#updated player 2 section of the board
		# we aren't tracking this yet so for now
		
		if moveType == "win":
			#lose operation
			# Just set the moveTo to empty, which should delete the piece
			
			delNode = nodes[movingTo]
			piece = delNode.getPiece()
			delNode.setPiece(None)
			
		elif moveType == "tie":
			#tie operation
			# Just set the moveTo to empty, which should delete the piece
			#in the future will need to Augment Enemy board and pieces as well.
			delNode = nodes[movingTo]
			piece = delNode.getPiece()
			delNode.setPiece(None)
			
#  places piece in the board
def injectPiece(piece, id):
	
	global nodes
	
	piecePos = piece["position"]
	pieceType = piece["piece"]
	
	node = nodes[piecePos]
	node.setPiece(FPiece(id, pieceType))
	nodes[piecePos] = node
	
class Node:
	def __init__(self, id, type, piece, connections):
		self.id = id
		self.type = type
		self.piece = piece
		self.connections = connections
	  
	def getId(self):
		return self.id
		
	def setId(self, id):
		self.id = id
		
	def getType(self):
		return self.type
		
	def setType(self, type):
		self.type = type
		
	def getPiece(self):
		return self.piece
	
	def setPiece(self, piece):
		self.piece = piece
	
	def getConnections(self):
		return self.connections  
		
	def setConnections(self, connections):
		self.connections = connections
		
	def __repr__(self):
		results = "Node(Id:" + str(self.id) + " Type:" + self.type + " Piece:" + str(self.piece) #+ " Connections:["
		
		#for conn in self.connections:
		#	results += str(conn) + " "
		
		results += ")"
		
		return results		
	
	def __str__(self):
		results = "Node(Id:" + str(self.id) + " Type:" + self.type + " Piece:" + str(self.piece) + " Connections:["
		
		for conn in self.connections:
			results += str(conn) + " "
		
		results += "])"
		
		return results	
		
class FPiece:
	def __init__(self, id, type):
		self.id = id
		self.type = type
		
	def getId(self):
		return self.id
		
	def getType(self):
		return self.type
	
	def setType(self, type):
		self.type = type

	def __str__(self):
		return "FPiece(Id:" + str(self.id) + " Type:" + self.type + ") "		

# Class which represents an Enemy Piece		
class EPiece:
	def __init__(self, id, typeProbs):
		self.id = id
		self.typeProbs = typeProbs
		
	def getId(self):
		return self.id
		
	def getTypeProbs(self):
		return self.typeProbs
		
	def setTypeProbs(self, typeProbs):
		self.typeProbs = typeProbs
		
	def __str__(self):
		return "EPiece(Id: " + str(self.id) + ") "

#Track what enemy pieces are left
#KO @30March
class EPieceCount:
	EPieces = {"FldMshl": 1, 
				"Gen" : 1,
				"LtGen": 2,
				"BrigGen": 2,
				"Col" : 2,
				"Maj": 2,
				"Capt" : 3,
				"PlCmdr" : 3,
				"Engr" : 3,
				"Gren" : 2,
				"LndMn": 2,
				"Flg" :1}
				
	def	__init__(self, epieces):
		self.epieces = EPieces
	
	def getAmtOfType(self, amt):
		return self.Epieces[amt]
	
	def setAmtOfTyp(self, typ, amt):
		self.EPieces[typ] = amt
	
	def setAmts(self, hshmp):
		self.EPieces = hshmp


'''

#Tracks probabilities of possible piece types.
# 	utilizes hasmap to map piece type to %
class typeProbs:

	# needs to add up to 1
	probDict = {"9" : .083, # field marshall 
							"8" : .083, # general
							"7" : .083, # lt. general
							"6" : .083, # brig. general
							"5" : .083, # colonel
							"4" : .083, # major
							"3" : .083, # captain
							"2" : .083, # pl commander
							"1" : .083, # engineer
							"B" : .083, # bomb
							"L" : .083, # land mine
							"F" : .083} # flag
					
	def	__init__(self, probDict):
		self.probDict = probDict
	
	def getTypeProb(self, typ):
		return self.probDict[typ]
	
	def setTypeProb(self, typ, prob):
		self.probDict[typ] = prob
	
	def setTypeProbs(self, hshmp):
		self.probDict = hshmp

	# update the probability of this piece
	def updateProb:
		return -1 # to-do
			
	#returns the type of highest probability
	def getMostProb:
		return max(self.probDict.iterkeys(), key=(lamda key: self.probDict[key]))
		
	#returns the type of lowest probab
	def getLeastProb:
		return min(self.probDict, key=self.probDict.get)

'''

class Connection:
	def __init__(self, connectedId, typ):
		self.connectedId = connectedId
		self.typ = typ
		
	def getConnectedId(self):
		return self.connectedId
		
	def setConnectedId(self, connectedId):
		self.connectedId = connectedId
		
	def getType(self):
		return self.typ
		
	def setType(self, typ):
		self.type = typ

	def __str__(self):
		return "Connection(To:" + str(self.connectedId) + " Type:" + self.typ + ") "

# calculate our next move
def calculateMove():
	bestMove = ""
	piecePositions = getPiecePositions()
	for pos in piecePositions:
		#for now pick any valid move, !!!!!!change to pick best move at a later date!!!!!!!!!
		bestMove = getBestMove(pos)
		
		if(bestMove):
			return bestMove	#!!!!!!!will be moved outside for statement later!!!!!!!!

# get the locations of all our pieces
def getPiecePositions():
	positions = []
	
	for key, node in nodes.iteritems():
		#check if a node contains a piece(!!!!!!!!!later make it only friendly pieces!!!!!!!!)
		if node.getPiece():
			#if (ourPlayer == 1):
			#	sys.stderr.write("Piece is: " + str(node.getPiece()) + " at: " + key + " adding to piece list.\n")
			positions.append(key)
			
	return positions

# grabs the best move for a given piece(!!!!!!!!for now just grabs the first valid move!!!!!!!)		
def getBestMove(pos):
	
	node = nodes[pos]
	
	piece = node.getPiece()
	if not piece.getType() == "L" and not piece.getType() == "F":
		for connection in node.getConnections():
			move = connection.getConnectedId()
			
			if isMoveValid(move):
				return "(" + pos + " " + move + ")"

# determine if a move is valid(!!!!!!!!!for now means we arn't moving onto a space occupied by our own piece!!!!!!!)
def isMoveValid(move):

	if nodes[move].getPiece():
		return False
	else:
		return True
		
		        
def main():
	
	global nodes
	global ourPlayer
	
	# parse command line options
	args = sys.argv[1:]
	
	# check for invalid syntax, pass only the arguments (not the file name)
	syntaxChecker(args)
	
	# convert the time argument to a float of seconds
	timeLimit = getTimeLimit(args[3])
	
	# create a CFG of the initial board configuration
	initialConfig = jsonToCFG()
	
	# which player are we
	ourPlayer = int(args[1])

	#A nodes	
	nodes["A1"] = Node("A1","standard", None, [Connection("B1", "standard"),Connection("A2", "standard")])
	nodes["A2"] = (Node("A2","standard", None, [Connection("A1", "standard"),Connection("B2", "rail"),Connection("B3","standard"),Connection("A3","rail")]))
	nodes["A3"] = (Node("A3","standard", None, [Connection("A2", "rail"),Connection("B3", "standard"),Connection("A4","rail")]))
	nodes["A4"] = (Node("A4","standard", None, [Connection("A3", "rail"),Connection("B3", "standard"),Connection("B4","standard"),Connection("B5","standard"),Connection("A5","rail")]))
	nodes["A5"] = (Node("A5","standard", None, [Connection("A4", "rail"),Connection("B5", "standard"),Connection("A6","rail")]))
	nodes["A6"] = (Node("A6","standard", None, [Connection("A5", "rail"),Connection("B5", "standard"),Connection("B6","rail"),Connection("A7","rail")]))
	nodes["A7"] = (Node("A7","standard", None, [Connection("A6", "rail"),Connection("B7", "rail"),Connection("B8","standard"),Connection("A8","rail")]))
	nodes["A8"] = (Node("A8","standard", None, [Connection("A7", "rail"),Connection("B8", "standard"),Connection("A9","rail")]))
	nodes["A9"] = (Node("A9","standard", None, [Connection("A8", "rail"),Connection("B8", "standard"),Connection("B9","standard"),Connection("B10","standard"),Connection("A10","rail")]))
	nodes["A10"] = (Node("A10","standard", None, [Connection("A9", "rail"),Connection("B10", "standard"),Connection("A11","rail")]))
	nodes["A11"] = (Node("A11","standard", None, [Connection("A10", "rail"),Connection("B10","standard"),Connection("B11","rail"),Connection("A12","standard")]))
	nodes["A12"] = (Node("A12","standard", None, [Connection("A11", "standard"),Connection("B12","standard")]))
			
	#B nodes
	nodes["B1"] = (Node("B1","HQ", None, [Connection("C1", "standard"),Connection("B2", "standard"),Connection("A1", "standard")]))
	nodes["B2"] = (Node("B2","standard", None, [Connection("B1", "standard"),Connection("C2", "rail"),Connection("B3","standard"),Connection("A2","rail")]))
	nodes["B3"] = (Node("B3","camp", None, [Connection("B2", "standard"),Connection("C2", "standard"),Connection("C3","standard"),Connection("C4", "standard"),Connection("B4", "standard"),Connection("A4","standard"),Connection("A3","standard"),Connection("A2","standard")]))
	nodes["B4"] = (Node("B4","standard", None, [Connection("B3", "standard"),Connection("C4", "standard"),Connection("B5","standard"),Connection("A4","standard")]))
	nodes["B5"] = (Node("B5","camp", None, [Connection("B4", "standard"),Connection("C4", "standard"),Connection("C5","standard"),Connection("C6", "standard"),Connection("B6", "standard"),Connection("A6","standard"),Connection("A5", "standard"),Connection("A4","standard")]))
	nodes["B6"] = (Node("B6","standard", None, [Connection("B5", "rail"),Connection("C6", "rail"),Connection("A6","rail")]))
	nodes["B7"] = (Node("B7","standard", None, [Connection("C7", "rail"),Connection("B8", "standard"),Connection("A7","rail")]))
	nodes["B8"] = (Node("B8","camp", None, [Connection("B7", "standard"),Connection("C7", "standard"),Connection("C8","standard"),Connection("C9", "standard"),Connection("B9", "standard"),Connection("A9","standard"),Connection("A8", "standard"),Connection("A7", "standard")]))
	nodes["B9"] = (Node("B9","standard", None, [Connection("B8", "standard"),Connection("C9", "standard"),Connection("B10","standard"),Connection("A9","standard")]))
	nodes["B10"] = (Node("B10","camp", None, [Connection("B9", "standard"),Connection("C9", "standard"),Connection("C10","standard"),Connection("C11", "standard"),Connection("B11", "standard"),Connection("A11","standard"),Connection("A10", "standard"),Connection("A9", "standard")]))
	nodes["B11"] = (Node("B11","standard", None, [Connection("B10", "standard"),Connection("C11","rail"),Connection("B12","standard"),Connection("A11","rail")]))
	nodes["B12"] = (Node("B12","HQ", None, [Connection("B11", "standard"),Connection("C12","standard"),Connection("A12","standard")]))
		
	#C nodes
	nodes["C1"] = (Node("C1","standard", None, [Connection("B1", "standard"),Connection("C2", "standard"),Connection("D1", "standard")]))
	nodes["C2"] = (Node("C2","standard", None, [Connection("C1", "standard"),Connection("D2", "rail"),Connection("D3","standard"),Connection("C3","standard"),Connection("B3","standard"),Connection("B2","rail")]))
	nodes["C3"] = (Node("C3","standard", None, [Connection("C2", "standard"),Connection("D3", "standard"),Connection("C4","standard"),Connection("B3", "standard")]))
	nodes["C4"] = (Node("C4","camp", None, [Connection("C3", "standard"),Connection("D3", "standard"),Connection("D4","standard"),Connection("D5","standard"),Connection("C5", "standard"),Connection("B5", "standard"),Connection("B4","standard"),Connection("B3","standard")]))
	nodes["C5"] = (Node("C5","standard", None, [Connection("C4", "standard"),Connection("D5", "standard"),Connection("C6","standard"),Connection("B5", "standard")]))
	nodes["C6"] = (Node("C6","standard", None, [Connection("C5", "standard"),Connection("D5", "standard"),Connection("D6","rail"),Connection("C7", "rail"),Connection("B6", "rail"),Connection("B5","standard")]))
	nodes["C7"] = (Node("C7","standard", None, [Connection("C6", "rail"),Connection("D7", "rail"),Connection("D8","standard"),Connection("C8","standard"),Connection("B8","standard"),Connection("B7","standard")]))
	nodes["C8"] = (Node("C8","standard", None, [Connection("C7", "standard"),Connection("D8", "standard"),Connection("C9","standard"),Connection("C8", "standard")]))
	nodes["C9"] = (Node("C9","camp", None, [Connection("C8", "standard"),Connection("D8", "standard"),Connection("D9","standard"),Connection("D10","standard"),Connection("C10", "standard"),Connection("B10", "standard"),Connection("B9","standard"),Connection("B8","standard")]))
	nodes["C10"] = (Node("C10","standard", None, [Connection("C9", "standard"),Connection("D10", "standard"),Connection("C11","standard"),Connection("B10", "standard")]))
	nodes["C11"] = (Node("C11","standard", None, [Connection("C10", "standard"),Connection("D10","standard"),Connection("D11","rail"),Connection("C12","standard"),Connection("B11","rail"),Connection("B10","standard")]))
	nodes["C12"] = (Node("C12","standard", None, [Connection("C11", "standard"),Connection("D12","standard"),Connection("B12","standard")]))

	#D nodes
	nodes["D1"] = (Node("D1","HQ", None, [Connection("E1", "standard"),Connection("D2", "standard"),Connection("C1", "standard")]))
	nodes["D2"] = (Node("D2","standard", None, [Connection("D1", "standard"),Connection("E2", "rail"),Connection("D3","standard"),Connection("C2","rail")]))
	nodes["D3"] = (Node("D3","camp", None, [Connection("D2", "standard"),Connection("E2", "standard"),Connection("E3","standard"),Connection("E4", "standard"),Connection("D4", "standard"),Connection("C4","standard"),Connection("C3","standard"),Connection("C2","standard")]))
	nodes["D4"] = (Node("D4","standard", None, [Connection("D3", "standard"),Connection("E4", "standard"),Connection("D5","standard"),Connection("C4","standard")]))
	nodes["D5"] = (Node("D5","camp", None, [Connection("D4", "standard"),Connection("E4", "standard"),Connection("E5","standard"),Connection("E6", "standard"),Connection("D6", "standard"),Connection("C6","standard"),Connection("C5", "standard"),Connection("C4","standard")]))
	nodes["D6"] = (Node("D6","standard", None, [Connection("D5", "rail"),Connection("E6", "rail"),Connection("C6","rail")]))
	nodes["D7"] = (Node("D7","standard", None, [Connection("E7", "rail"),Connection("D8", "standard"),Connection("C7","rail")]))
	nodes["D8"] = (Node("D8","camp", None, [Connection("D7", "standard"),Connection("E7", "standard"),Connection("E8","standard"),Connection("E9", "standard"),Connection("D9", "standard"),Connection("C9","standard"),Connection("C8", "standard"),Connection("C7", "standard")]))
	nodes["D9"] = (Node("D9","standard", None, [Connection("D8", "standard"),Connection("E9", "standard"),Connection("D10","standard"),Connection("C9","standard")]))
	nodes["D10"] = (Node("D10","camp", None, [Connection("D9", "standard"),Connection("E9", "standard"),Connection("E10","standard"),Connection("E11", "standard"),Connection("D11", "standard"),Connection("C11","standard"),Connection("C10", "standard"),Connection("C9", "standard")]))
	nodes["D11"] = (Node("D11","standard", None, [Connection("D10", "standard"),Connection("E11","rail"),Connection("D12","standard"),Connection("C11","rail")]))
	nodes["D12"] = (Node("D12","HQ", None, [Connection("D11", "standard"),Connection("E12","standard"),Connection("C12","standard")]))

	#E nodes	
	nodes["E1"] = (Node("E1","standard", None, [Connection("D1", "standard"),Connection("E2", "standard")]))
	nodes["E2"] = (Node("E2","standard", None, [Connection("E1", "standard"),Connection("E3", "rail"),Connection("D3","standard"),Connection("D2","rail")]))
	nodes["E3"] = (Node("E3","standard", None, [Connection("E2", "rail"),Connection("D3", "standard"),Connection("E4","rail")]))
	nodes["E4"] = (Node("E4","standard", None, [Connection("E3", "rail"),Connection("E5", "rail"),Connection("D5","standard"),Connection("D4","standard"),Connection("D3","standard")]))
	nodes["E5"] = (Node("E5","standard", None, [Connection("E4", "rail"),Connection("D5", "standard"),Connection("E6","rail")]))
	nodes["E6"] = (Node("E6","standard", None, [Connection("E5", "rail"),Connection("D5", "standard"),Connection("D6","rail"),Connection("E7","rail")]))
	nodes["E7"] = (Node("E7","standard", None, [Connection("E6", "rail"),Connection("D7", "rail"),Connection("D8","standard"),Connection("E8","rail")]))
	nodes["E8"] = (Node("E8","standard", None, [Connection("E7", "rail"),Connection("D8", "standard"),Connection("E9","rail")]))
	nodes["E9"] = (Node("E9","standard", None, [Connection("E8", "rail"),Connection("D8", "standard"),Connection("D9","standard"),Connection("D10","standard"),Connection("E10","rail")]))
	nodes["E10"] = (Node("E10","standard", None, [Connection("E9", "rail"),Connection("D10", "standard"),Connection("E11","rail")]))
	nodes["E11"] = (Node("E11","standard", None, [Connection("E10", "rail"),Connection("D10","standard"),Connection("D11","rail"),Connection("E12","standard")]))
	nodes["E12"] = (Node("E12","standard", None, [Connection("E11", "standard"),Connection("D12","standard")]))
	
	# open our json that has our initial configuration
	initConfig = open("initConfig.json")
	initConfigArray = json.load(initConfig)

	# place the pieces from the json configuration into our nodes
	i = 0
	for piece in initConfigArray:
		injectPiece(piece, i)
		i += 1

	initConfig.close()
	
	# send the referee our initial configuration
	sys.stdout.write(initialConfig)
	sys.stdout.flush()
		
	# if it is our turn first, send the referee our first move
	if ourPlayer == 1:
		sys.stdout.write("( A6 A7 )")
		sys.stdout.flush()
	
	while(True):
	
		# get the input from the ref
		message = raw_input()
				
		# start capturing the time duration of our move (not needed for prototype)
		# startTime = time.time() 
	
		if (message == "Invalid Board Setup"):
			sys.stderr.write("Board was not correctly set up. Exiting game.\n")
			sys.exit(0)
		
		# match just the first 18 characters which are always the same
		elif (message[:18] == "Invalid Board Move"):
			sys.stderr.write("We sent an invalid move. Exiting game.\n")
			sys.exit(0)
			
		elif ("Victory" in message):
			if ("1" in message):
				sys.stderr.write("Player 1 is the victor. Exiting game.\n")
				sys.exit(0)
			elif ("2" in message):
				sys.stderr.write("Player 2 is the victor. Exiting game.\n")
				sys.exit(0)
			else:
				sys.stderr.write("There was no victor. Exiting game.\n")
				sys.exit(0)
		
		elif (message[0] == "F"):
			# a field marshall has been captured and the flag is revealed
			# not needed for the prototype
			pass
		
		else:
			
			# make sure the referee's message is properly formatted
			if (message.count(' ') != 3):
				sys.stderr.write("Error: The referee provided an invalid message.\n")
				sys.exit(0)
			
			# parse the referee's input
			messageArgs = message.split(' ')
			movingFrom = messageArgs[0]
			movingTo = messageArgs[1]
			movingPlayer = messageArgs[2]
			moveType = messageArgs[3]
						
			# update our board (currently ignoring opponent's pieces and railroads)
			updateBoard(movingFrom, movingTo, movingPlayer, moveType)
				
				
			#We don't want to send our move, if the referee is simply reporting what we have done.
			if(ourPlayer == int(movingPlayer)):
				sys.stdout.flush()
				continue
					
					
			# select the next move (currently brute-force moving one piece till it dies)
			nextMove = calculateMove()
			
			# send the ref the move
			sys.stdout.write(nextMove)
			
			# check to make sure we haven't gone past our time limit (not needed for prototype)
			# timeLeft = timeLimit - (time.time() - startTime)
			# if (timeLeft <= 0):
			#	print "Error: We ran out of time to complete our move. Exiting game."
			#	sys.exit(0)
		
#		if (ourPlayer == 1):
#			sys.stderr.write(str(sorted(nodes.items())) + "\n")

		sys.stdout.flush()	
		
if __name__ == "__main__":
    main()

