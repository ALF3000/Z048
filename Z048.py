#!/usr/bin/python

import os,sys
import pygame
from pygame.locals import *
from math import floor,log,fabs
import random
import argparse

history_file='history.csv'

def read_csv():
    scores={}
    with open(history_file,'r') as fi:
        for line in fi:
            toks = line.split(',')
            scores[int(toks[0])]=int(toks[1][:-1])
    return scores

def write_csv(scores):
    with open(history_file,'w') as fi:
        for k,v in scores.items():
            fi.write("{},{}\n".format(k,v))


class Column():
	''' Slave to a Grid '''
	def __init__(self,cells):	
		self.cells=cells
		self.merge_score=0

	def __getitem__(self,index):
		return self.cells[index]

	def __setitem__(self,index,value):
		self.cells[index]=value

	def __len__(self):
		return len(self.cells)

	def __repr__(self):
		return str(self.cells)

	def nextCell(self,i):
		j=i+1
		while j<len(self.cells) and self.cells[j].isEmpty():
			j+=1
		return j

	def prevCell(self,i):
		'''Return j>=-1 '''
		if i<0:
			raise Exception
		j=i-1
		while j>=0 and self.cells[j].isEmpty():
			j-=1
		return j

	def update(self):
		'''
		Collapse column towards the first entry
		If at least one cell has moved :
			return True to master
		Otherwise, the game might be frozen : 
			return False to master
			(ominous jingle)
		'''
		i=self.nextCell(-1)
		hasMoved=False
		self.merge_score=0
		while i<len(self.cells):
			i0=self.prevCell(i)
			val=self.cells[i].val
			x=self.cells[i].x
			y=self.cells[i].y

			if i0>-1 and self.cells[i0].val==val and not(self.cells[i0].hasGrown): #merge
				self.cells[i0].val*=2
				self.merge_score+=self.cells[i0].val
				self.cells[i0].hasGrown=True # for display to update
				self.cells[i].dead=True
				self.cells[i]=EmptyCell(x,y)
				hasMoved1=True
			else:
				# i0 is an obstacle : it is either out of Bounds,
				# or it is in bounds but it does not have the same value
				# we have i0+1<=i, by construction, 
				# so i0+1 is either an EmptyCell, or i0==i
				if i0+1<i:
					# note that i0+1>=0 because i0>=-1
					self.cells[i].moveTo(self.cells[i0+1])
					self.cells[i0+1]=self.cells[i]
					self.cells[i]=EmptyCell(x,y)
					hasMoved1=True
				else:
					hasMoved1=False
			hasMoved=hasMoved or hasMoved1
			i=self.nextCell(i)
		return hasMoved

class EmptyCell():
	def __init__(self,x,y):
		self.val=0
		self.x=x
		self.y=y

	def __repr__(self):
		return str(self.val)

	def isEmpty(self):
		return True

class Cell(pygame.sprite.Sprite):

	def __init__(self,x,y,val=2):
		pygame.sprite.Sprite.__init__(self) # call Sprite initializer
		self.val=val
		self.x=x
		self.y=y
		self.dead=False
		self.hasGrown=False
		self.move=[0,0]

	def init(self):
		self.image=pygame.image.load('digits/'+str(self.val)+'.gif').convert()
		self.rect=self.image.get_rect()
		self.rect.top=self.x*128
		self.rect.left=self.y*128

	def __repr__(self):
		return str(self.val)

	def isEmpty(self):
		return False

	def moveTo(self,cell):
		self.x=cell.x
		self.y=cell.y
		self.move=[cell.x-self.x,cell.y-self.y]

	def update(self):
		self.init()
		#### is this necessary ?
		self.rect.top=self.x*128
		self.rect.left=self.y*128
		##### 
		if self.hasGrown:
			self.image=pygame.image.load('digits/'+str(self.val)+'.gif').convert()
			newpos=self.image.get_rect()
			newpos.left=self.rect.left
			newpos.top=self.rect.top
			self.rect=newpos
			self.hasGrown=False

class Grid:
	'''Cells are stored in the grid both as a Group for rendering, and as a table, for faster access to columns'''

	def __init__(self,nx=4,ny=4,p=.8):
		self.tab=[[EmptyCell(i,j) for j in range(ny)] for i in range(nx)]
		self.p=p # proba of drawing a 2*1
		self.merge_score=0

	def __repr__(self):
		""" tabs and newline will print a neat square
		since cell.val is bounded above 
		(... is it not ?)"""
		s=''
		for row in self.tab:
			for cell in row:
				s+=str(cell.val)+'\t'
			s+='\n'
		return s

	def copy(orig):
		x=Grid(len(orig.tab),len(orig.tab[0]))
		x.p=orig.p
		for nr,row in enumerate(orig.tab):
			for nc,cell in enumerate(row):
				if cell.isEmpty():
					x.tab[nr][nc]=EmptyCell(nr,nc)
				else:
					x.tab[nr][nc]=Cell(nr,nc,val=orig.tab[nr][nc].val)
		return x

	def colsToGrid(self,cols,direction):
		''' TODO : proofread
		Turn columns back into grid
		'''
		for nr in range(len(self.tab)):
			for nc in range(len(self.tab[0])):
				if direction==K_UP:
					self.tab[nr][nc]=cols[nc][nr]
				elif direction==K_DOWN:
					self.tab[nr][nc]=cols[nc][len(self.tab)-1-nr]
				elif direction==K_LEFT:
					self.tab[nr][nc]=cols[nr][nc]
				elif direction==K_RIGHT:
					self.tab[nr][nc]=cols[nr][len(self.tab[0])-1-nc]
		
	def freeCells(self):
		cells=[]
		for nrow,row in enumerate(self.tab):
			for ncol,col in enumerate(row):
				if col.isEmpty():
					cells.append((nrow,ncol))
		return cells

	def gridToCols(self,direction):
		'''
		Return a list of columns, so that each column has its gravity upwards.
		A column = a list of Cells
		'''
		if direction==K_UP:
			cols=[Column( [self.tab[nrow][ncol] for nrow in range(len(self.tab))]) for ncol in range(len(self.tab[0]))]
		elif direction==K_DOWN:
			cols=[Column( [self.tab[nrow][ncol] for nrow in range(len(self.tab)-1,-1,-1)]) for ncol in range(len(self.tab[0]))]
		elif direction==K_LEFT:
			cols=[Column(row) for row in self.tab]
		elif direction==K_RIGHT:
			cols=[Column( [row[ncol] for ncol in range(len(row)-1,-1,-1)]) for row in self.tab]
		return cols

	def initState(self):
		'''TODO: suppress calls to freeCells '''
		for i in range(2):
			self.newTile(2)

		

	def isOver(self):
		cells=self.freeCells()
		if len(cells)==0:
			mergePair=False
			#horizontal pairs
			for row in self.tab:
				for nc in range(len(row)-1):
					mergePair= mergePair or row[nc].val==row[nc+1].val
			for nc in range(len(self.tab[0])):
				for nr in range(len(self.tab)-1):
					mergePair=mergePair or self.tab[nr][nc].val==self.tab[nr+1][nc].val
		return len(cells)==0 and not(mergePair)

	def score(self):
	    return max([max([c.val for c in r]) for r in self.tab])

	def legal_moves(self):
		
		mvs=set()
		for nr in range(len(self.tab)):
			for nc in range(len(self.tab[nr])-1):
				if self.tab[nr][nc].val==0 and self.tab[nr][nc+1].val>0:
					mvs.add(K_LEFT)
				if self.tab[nr][nc+1].val==0 and self.tab[nr][nc].val>0:
					mvs.add(K_RIGHT)

				if self.tab[nr][nc].val==self.tab[nr][nc+1].val and self.tab[nr][nc].val>0:
					mvs.add(K_LEFT)
					mvs.add(K_RIGHT)

		for nr in range(len(self.tab)-1):
			for nc in range(len(self.tab[nr])):
				if self.tab[nr][nc].val==self.tab[nr+1][nc].val and self.tab[nr][nc].val>0:
					mvs.add(K_UP)
					mvs.add(K_DOWN)

				if self.tab[nr][nc].val==0 and self.tab[nr+1][nc].val>0:
					mvs.add(K_UP)
				if self.tab[nr+1][nc].val==0 and self.tab[nr][nc].val>0:
					mvs.add(K_DOWN)

		return list(mvs)

	def move(self,direction):
		
		cols=self.gridToCols(direction)
		hasMoved=False
		for col in cols:
			b=col.update()
			self.merge_score+=col.merge_score
			hasMoved=hasMoved or b
		self.colsToGrid(cols,direction)
		return hasMoved
		

	def newTile(self,val=0):
		cells=self.freeCells()
		j=int(floor(random.random()*len(cells)))
		nrow,ncol=cells[j]
		if val==0:
			if random.random()<self.p:
				val=2
			else:
				val=4
		self.tab[nrow][ncol]=Cell(nrow,ncol,val)
	
	def insert_tile(self,nrow,ncol,val):
		""" For testing purposes"""
		self.tab[nrow][ncol]=Cell(nrow,ncol,val)

	def cells(self):
		""" Return only non empty cells, for rendering"""
		cells=[]
		for i in range(len(self.tab)):
			for j in range(len(self.tab[0])):
				if not(self.tab[i][j].isEmpty()):
					cells.append(self.tab[i][j])
		return cells

	def update(self):
		# kill "dead" cells
		for cell in self.cells():
			cell.update()
			if cell.dead:
				cell.kill()

def test_gridToCols():

	# test colToGrid
	grid=Grid([],2,2)
	print('LEFT :'+str(grid.gridToCols(K_LEFT))) 
	print('RIGHT :'+str(grid.gridToCols(K_RIGHT))) 
	print('UP :'+str(grid.gridToCols(K_UP)) )
	print('DOWN :'+str(grid.gridToCols(K_DOWN)))

def test_colsToGrid():
	grid=Grid([],2,2)
	print(grid)
	# LEFT
	# cols=[Column([EmptyCell(i,j) for j in range(2)]) for i in range(2)]
	cols=grid.gridToCols(K_LEFT)
	grid.colsToGrid(cols,K_LEFT)
	print('LEFT : '+str(grid))
	# RIGHT
	cols=[Column([EmptyCell(i,j) for j in range(1,-1,-1)]) for i in range(2)]
	grid.colsToGrid(cols,K_RIGHT)
	print('RIGHT : '+str(grid))	
	# UP
	cols=[Column([EmptyCell(i,j) for i in range(2)]) for j in range(2)]
	# cols=grid.gridToCols(K_UP)
	grid.colsToGrid(cols,K_UP)
	print('UP : '+str(grid))	
	# DOWN
	cols=[Column([EmptyCell(i,j) for i in range(1,-1,-1)]) for j in range(2)]
	# cols=grid.gridToCols(K_DOWN)
	grid.colsToGrid(cols,K_DOWN)
	print('DOWN : '+str(grid))	

def test():
	pygame.init()
	win = pygame.display.set_mode((2,2))
	grid=Grid([])
	col=Column([Cell(0,1,val=2),Cell(1,1,val=2)])
	print(col)
	col.update()
	print(col)

def test_digits():
	# display all digits for aesthetics :
	# are the colors right ?
	# what's the best font ?
	# is the font size right ?
	nx=4
	ny=4
	pygame.init()
	win = pygame.display.set_mode((128*nx, 128*ny))
	pygame.mouse.set_visible(True)

	background = pygame.Surface(win.get_size())
	background = background.convert()
	background.fill((128, 128, 128))
	win.blit(background,(0,0))
	#Rafraichissement de l'ecran
	grid=Grid(nx,ny)
	for i,val in enumerate([2,4,8,16,32,64,128,256,512,1024,2048]):
		x=i/4
		y=i%4
		grid.insert_tile(x,y,val)
	# another way to read this loop is :
	# x in range(4), y in range(4), i = 4*x+y, val=2**(i+1)
	win.blit(background,(0,0))
	grid.update()
	cells=pygame.sprite.RenderPlain()
	cells.add(grid.cells())
	cells.draw(win)
	pygame.display.flip()

def play(nx=4,ny=4,nohist=False,p=.8):

	pygame.init()
	win = pygame.display.set_mode((128*ny, 128*nx))
	# pygame.mouse.set_visible(True)
	# pour essayer :
	pygame.mouse.set_visible(False)
	
	# lecture de l'historique des scores
	scores=read_csv()

	background = pygame.Surface(win.get_size())
	background = background.convert()
	background.fill((128, 128, 128))
	win.blit(background,(0,0))
	
	# création du plateau
	grid=Grid(nx,ny,p=p)
	grid.initState()
	# Rafraichissement de l'ecran
	grid.update()
	win.blit(background,(0,0))
	cells=pygame.sprite.RenderPlain()
	cells.add(grid.cells())
	cells.draw(win)
	pygame.display.flip()

	clock = pygame.time.Clock()
	#BOUCLE INFINIE	
	while True:
		clock.tick(60)
		for event in pygame.event.get():
			# Interaction utilisateur : au clavier
			if event.type==QUIT:
				return
			if event.type==KEYDOWN:
				if event.key==K_ESCAPE:
					return
				if event.key in [K_UP,K_DOWN,K_LEFT,K_RIGHT]:
					############ GATEWAY ###########
					if grid.move(event.key):
						grid.newTile()
					################################
			# this block of code will be obsolete
			# as well as the whole sprite group silly stuff
			grid.update()
			win.blit(background,(0,0))
			cells=pygame.sprite.RenderPlain(grid.cells())
			cells.add(grid.cells())
			cells.draw(win)
			pygame.display.flip()

			if grid.isOver():
				s=grid.score()
				if s in scores:
					scores[s]+=1
				else:
				    scores[s]=1
				
				if not nohist:
					write_csv(scores)
					print(scores)
				return

def test_history():
    # test csv read/write funcitonalities of the game
    scores=read_csv()
    print(scores)
    write_csv(scores)

if __name__=='__main__':
	readme="play 2048 offline : argument -nx 4 -ny 4 for a 4x4 grid (default)"
	parser=argparse.ArgumentParser(description=readme)
	parser.add_argument("-nx",type=int,default=4)
	parser.add_argument("-ny",type=int,default=4)
	parser.add_argument("-nohist",action="store_true",default=False)
	parser.add_argument("-test",choices=["digits","anim"])
	parser.add_argument("-p",type=float,default=.8)
	args=parser.parse_args()
	# test_anim()
        #test_history()
	res=play(nx=args.nx,ny=args.ny,nohist=args.nohist,p=args.p)

