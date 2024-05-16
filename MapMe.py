#!/usr/bin/env python3

# Imports
import pygame
import pygame_widgets
from pygame_widgets.button import Button
from pygame_widgets.dropdown import Dropdown
from pygame_widgets.combobox import ComboBox
from pygame.locals import *
import sys,os
import numpy as np
np_int=np.int8
import matplotlib.pyplot as plt
from PIL import Image

# Load the game
## Game data
print("Loading country names and connections ...",end=" ",flush=True)
country_names=np.load("data/indexed_countries.npy")
countries_for_dropdown=[s.replace("_"," ") for s in country_names]
country_adj=np.load("data/adjacency.npy")
country_adj=country_adj | country_adj.transpose() # Symmetrize
assert (country_adj.shape[0]==len(country_names))
print("done",flush=True)

DATA_DIR="data/"
BORDER=12
STEP=14
MIN_STEP=3
FAR_CUTOFF=3

all_data=sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".npz")])
maps=dict()
print("Loading all country maps ...",end=" ",flush=True)
for f in all_data:
    map=np.load("data/"+f)["data"]
    country=f[:-4].lower()
    maps[country]=map
print("done")

def path_finder(adj,start,end,using,skipping=[]):
	#print(country_names[start],country_names[end])
	path=[start]
	if adj[start,end]: return [start,end]
	if not len(using): raise ValueError("No path")
	net_using=list(set(using)-set(skipping))
	#print(country_names[start],flush=True)
	for u in net_using:
		if not adj[start,u]: continue
		#print("\t",country_names[u],flush=True)
		try:
			npath=path_finder(adj,u,end,net_using,[u])
		except ValueError: continue
		return path+npath
	raise ValueError("No path")

def make_path(step=STEP):
    tot_neigh=0
    while tot_neigh<=2:
        rv1=np.random.choice(np.arange(len(country_names)))
        country1=country_names[rv1]
        tot_neigh=np.sum(country_adj[rv1])
    path=[rv1]
    cid=rv1
    while len(path)<step+1:
        nn=np.where(country_adj[cid])[0] # Next (potentially selected) neighbours
        nn=list(set(nn)-set(path))
        if not len(nn):
            raise ValueError("Bad paths from "+country1)
        n_hope=0
        TRIES=0
        while n_hope<=0 or (n_hope==1 and len(path)!=step):
            TRIES+=1
            if TRIES>100: raise ValueError("Bad paths from "+country1)
    
            s1=np.random.choice(nn)
            n_hope=np.sum(country_adj[s1])
        path.append(s1)
        cid=s1
    return path


## Core game - Puzzle object
class Puzzle:
    def __init__(self,path,adj,names):
        self.path=path
        self.guessed=[]
        self.guessed_rank=[]
        self.names=names
        self.adj=adj
        
        self.evaluate()

    def evaluate(self):
        path=self.path
        self.guessed=[self.path[0],self.path[-1]]
        self.guessed_rank={path[0]: 0, path[-1]: len(path)-1}
        self.types={path[0]: -1, path[-1]: -1} # Starting and ending points have no type
        M=self.adj.copy()
        R=1
        ev=M[self.path[0],self.path[-1]]
        while not ev:
            M=np.matmul(M,self.adj)
            ev=M[self.path[0],self.path[-1]]
            R+=1
        self.guessed_rank[path[-1]]=R
        self.rank=R # Puzzle Rank

    def guess(self,idx):
        if idx in self.guessed:
            print("Already guessed/Start or End")
            return
        self.guessed.append(idx)
        M1=self.adj.copy()
        M2=self.adj.copy()
        ev1=M1[self.path[0],idx]
        ev2=M2[idx,self.path[-1]]
        R1=1
        R2=1
        while (not ev1 and R1<STEP*3) or (R2<STEP*3 and not ev2):
            if not ev1:
                M1=np.matmul(M1,self.adj)
                ev1=M1[self.path[0],idx]
                R1+=1
            if not ev2:
                M2=np.matmul(M2,self.adj)
                ev2=M2[idx,self.path[-1]]
                R2+=1
            
        self.guessed_rank[idx]=max(R1,R2)
        chk=((R1+R2)-self.rank)
        if chk==0: self.types[idx]=1
        elif chk<FAR_CUTOFF: self.types[idx]=0
        else: self.types[idx]=2
        #self.types[idx]=1 if chk else 0
        return (self.types[idx]==1)
        
    def get_pure_grid(self,include_end=True):
        start=country_names[self.path[0]]
        end=country_names[self.path[-1]]
        final_grid=maps[start]
        final_grid=final_grid.astype(float)
        if include_end: final_grid+=maps[end]
        
        return final_grid

    def crop_grid(self,final_grid):
        final_grid[2000:,:1000]=0.0
        grid_bounds_x,grid_bounds_y=np.where(final_grid)
        x_min=np.min(grid_bounds_x)
        x_max=np.max(grid_bounds_x)
        y_min=np.min(grid_bounds_y)
        y_max=np.max(grid_bounds_y)
        self.cropping=((x_min,x_max),(y_min,y_max))
        final_grid=final_grid[max(x_min-BORDER,0):x_max+BORDER,max(0,y_min-BORDER):y_max+BORDER]
        return final_grid

    def victory(self):
        vp=0
        for c in self.guessed:
            if self.types[c]==1: vp+=1
        #if (vp+1)<self.rank: return False
        try:
        	print(path_finder(self.adj,self.path[0],self.path[-1],self.guessed),"is the path")
        	return True
        except ValueError: return False
    
    def get_country_at(self,x,y):
    	if x<0 or y<0: return None
    	try:
    		if not self.final_grid[y,x]: return None
    	except IndexError: return None
    	for cidx in self.guessed:
    		map=maps[country_names[cidx]]
    		x_min,x_max=self.cropping[0]
    		y_min,y_max=self.cropping[1]
    		map=map[max(x_min-BORDER,0):x_max+BORDER,max(0,y_min-BORDER):y_max+BORDER]
    		if map[y,x]: return country_names[cidx].replace("_"," ")
    	return None
        
    def draw_plt(self,draw_bad=True):
        final_grid=self.get_pure_grid().astype(float)
        for c in self.guessed:
            if self.types[c]==-1: continue #Start or end
            elif draw_bad and (self.types[c]==0 or self.types[c]==2):
                final_grid+=maps[self.names[c]]/BLUE_FACTOR
            elif self.types[c]==1:
                final_grid+=maps[self.names[c]]/GREEN_FACTOR
        final_grid=self.crop_grid(final_grid)
        plt.imshow(final_grid)
    
    def grid_for_pygame(self,draw_bad=True,draw_very_bad=None):
        global HIDE_FAR
        if draw_very_bad is None: draw_very_bad=not HIDE_FAR
        final_grid=self.get_pure_grid().astype(np_int)    	
        for c in self.guessed:
            if self.types[c]==-1: continue #Start or end
            elif draw_bad and (self.types[c]==0):
                final_grid+=2*maps[self.names[c]].astype(np_int)
            elif draw_very_bad and (self.types[c]==2):
                final_grid+=4*maps[self.names[c]].astype(np_int)
            elif self.types[c]==1:
                final_grid+=3*maps[self.names[c]].astype(np_int)
        final_grid=self.crop_grid(final_grid)
        self.final_grid=final_grid
        return self.final_grid

# Pygame colors
BLACK = pygame.Color(0, 0, 0)         # Black
WHITE = pygame.Color(255, 255, 255)   # White
GREY = pygame.Color(128, 128, 128)   # Grey
RED = pygame.Color(255, 0, 0)       # Red
ORANGE = pygame.Color(255, 140, 0)       # Orange
GREEN = pygame.Color(0, 255, 0)       # Green
BLUE = pygame.Color(60, 60, 255)       # Blue
YELLOW = pygame.Color(255, 255, 0)       # Yellow

# Window Parameters
WIDTH=1000
HEIGHT=800
IMG_TMP_LOC="/tmp/mapme.png"
SCALE_PROP=True
scale_x,scale_y=1.0,1.0
FPS=24
DRAW_MOD=4
MOUSEOVER_MOD=1
DROPDOWNS_HEIGHT=48
DROPDOWNS_COLOR=WHITE
BUTTONS_HEIGHT=48
BUTTONS_COLOR=pygame.Color(160,160,160)
HIDE_FAR=False


# Decor
## Panel
PANEL_WIDTH=250
PANEL_TRIM=False # Change to True to get a trimmed panel
PANEL_TRIM_HEIGHT=HEIGHT//2
PANEL_BORDER=25
## Title Bar
TITLE_HEIGHT=40
TITLE_THROUGH_PANEL=True
TITLE_COLOR=pygame.Color(40,40,60)
TITLE_TEXT_COLOR=YELLOW

## Calculations based on parameters
PANEL_RECT=pygame.Rect(WIDTH-PANEL_WIDTH,HEIGHT-PANEL_TRIM_HEIGHT if PANEL_TRIM else 0,PANEL_WIDTH,PANEL_TRIM_HEIGHT if PANEL_TRIM else HEIGHT)
TITLE_RECT=pygame.Rect(0,0,WIDTH if TITLE_THROUGH_PANEL else WIDTH-PANEL_WIDTH,TITLE_HEIGHT)

# Start and setup pygame window
pygame.init()
pygame.font.init()
DISPLAYSURF = pygame.display.set_mode((WIDTH, HEIGHT))
frames_per_second = pygame.time.Clock()
frames_per_second.tick(FPS)
pygame.display.set_caption("Map Me")

TITLE_FONT = pygame.font.SysFont('Calibri', 30)
DEFAULT_FONT = pygame.font.SysFont('Calibri', 18)


# Standard drawing protocols
def draw_title():
	text_surface = TITLE_FONT.render('Connect '+start.replace("_"," ")+' to '+end.replace("_"," "), True, TITLE_TEXT_COLOR)
	DISPLAYSURF.blit(text_surface,(100,5))
def draw_extras():
	pygame.draw.rect(DISPLAYSURF,GREY,PANEL_RECT)
	pygame.draw.rect(DISPLAYSURF,TITLE_COLOR,TITLE_RECT)
	draw_title()
def get_map_image(puz,draw_bad=True):
	global scale_x,scale_y
	final_grid=puz.grid_for_pygame(draw_bad=draw_bad, draw_very_bad=not HIDE_FAR)
	img_shape=final_grid.shape
	img=pygame.Surface((img_shape[1],img_shape[0]))
	
	cat=np.where(final_grid==1) # Start and end
	for i in range(len(cat[0])):
		img.set_at((cat[1][i], cat[0][i]), YELLOW)
	
	cat=np.where(final_grid==2) # Bad guess
	for i in range(len(cat[0])):
		img.set_at((cat[1][i], cat[0][i]), ORANGE)
	
	cat=np.where(final_grid==3) # Good Guess
	for i in range(len(cat[0])):
		img.set_at((cat[1][i], cat[0][i]), GREEN)
	
	cat=np.where(final_grid==4) # Very bad guess
	for i in range(len(cat[0])):
		img.set_at((cat[1][i], cat[0][i]), RED)
	
	scale_x=(WIDTH-PANEL_WIDTH-BORDER)/img.get_width()
	scale_y=(HEIGHT-TITLE_HEIGHT-BORDER)/img.get_height()
	if not SCALE_PROP:
		img=pygame.transform.scale(img,(WIDTH-PANEL_WIDTH-BORDER,HEIGHT-TITLE_HEIGHT-BORDER))
	else:
		wscale=scale_x
		hscale=scale_y
		if wscale>hscale:
			scale=hscale
		else:
			scale=wscale
		scale_x=scale
		scale_y=scale
		img=pygame.transform.scale(img,(int(img.get_width()*scale),int(img.get_height()*scale)))
	#pygame.image.save(img,"test.png")
	return img

def draw_map(puz):
	global DRAWN_MAP
	if DRAWN_MAP is None: DRAWN_MAP=get_map_image(puz)
	DISPLAYSURF.blit(DRAWN_MAP,(0,TITLE_HEIGHT))

def backmap(click_x,click_y):
	click_y-=TITLE_HEIGHT
	click_x/=scale_x
	click_y/=scale_y
	return int(click_x),int(click_y)

K=0 # global step id (for whether to draw or not)
GUESSES=0
puz=None
start,end=None,None
DRAWN_MAP=None
#path=None

# Interactable functions
def confirm_button():
	global K,GUESSES,puz,DRAWN_MAP
	ce=dropdown_countries.getText().strip().lower()
	if ce=="": return
	ce=ce.replace(" ","_")
	GUESSES+=1
	idx=list(country_names).index(ce)
	puz.guess(idx)
	dropdown_countries.textBar.text.clear()
	vic=puz.victory()
	if vic:
		button_confirm.hide()
		button_win.show()
	print("Victory\n",vic)
	DRAWN_MAP=get_map_image(puz)
	K=0

def reset_button():
	global K,GUESSES,puz,start,end,DRAWN_MAP,button_confirm
	button_confirm.show()
	button_win.hide()
	K=0
	GUESSES=0
	diff=0
	while diff<MIN_STEP:
		  try:
		      path=make_path()
		  except ValueError:
		      continue
		  puz=Puzzle(path,country_adj,country_names)
		  diff=puz.rank-1
	start=country_names[path[0]]
	end=country_names[path[-1]]
	print("Start:",start)
	print("End:",end)
	DRAWN_MAP=None

def unblock_button():
	dropdown_countries.textBar.text.clear()
	dropdown_countries.reset()

def hide_far_button():
	global button_hide_far,HIDE_FAR,K,DRAWN_MAP
	HIDE_FAR=not HIDE_FAR
	if HIDE_FAR: button_hide_far.setText("Show all")
	else: button_hide_far.setText("Hide bad guesses")
	DRAWN_MAP=get_map_image(puz)
	K=0

# Interactables
## Dropdown of countries
dropdown_countries = ComboBox(DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, TITLE_HEIGHT+100+BUTTONS_HEIGHT+12, PANEL_WIDTH-2*PANEL_BORDER, DROPDOWNS_HEIGHT, name='Select guess country',
    choices=countries_for_dropdown,
    maxResults=5,
    font=pygame.font.SysFont('calibri', 30),
    borderRadius=3, colour=DROPDOWNS_COLOR, direction='down',
    textHAlign='left')
## Confirm button
button_confirm=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, TITLE_HEIGHT+100, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Guess', fontSize=30,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(0, 128, 0),
    radius=5, onClick=confirm_button, font=pygame.font.SysFont('calibri', 18))
## Win button (placeholder to say you win)
button_win=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, TITLE_HEIGHT+100, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='You Win!', fontSize=30,
    margin=15, inactiveColour=(0, 200, 0), hoverColour=(0, 200, 0), pressedColour=(0, 200, 0),
    radius=5, onClick=None, font=pygame.font.SysFont('calibri', 18))
button_win.disable()

## Reset button
button_reset=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, HEIGHT-150, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Reset', fontSize=30,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=reset_button, font=pygame.font.SysFont('calibri', 18))
## Unblock button
button_unblock=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, TITLE_HEIGHT+100-BUTTONS_HEIGHT-10, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Clear Box', fontSize=30,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=unblock_button, font=pygame.font.SysFont('calibri', 18))
## Hide-far button
button_hide_far=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, HEIGHT-250, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Hide bad guesses', fontSize=27,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=hide_far_button, font=pygame.font.SysFont('calibri', 18))

# Pick the two countries:
reset_button()

# Start the gameloop
while True:
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
    
    if K%DRAW_MOD==0:
    	DISPLAYSURF.fill(BLACK)
    	draw_map(puz)
    	K=0
    
    if K%MOUSEOVER_MOD==0:
    	draw_extras()
    	mouse_pos=pygame.mouse.get_pos()
    	backmap_pos=backmap(*mouse_pos)
    	country_text=puz.get_country_at(*backmap_pos)
    	if country_text is not None:
    		text_surface = DEFAULT_FONT.render(country_text, True, BLACK)
    		DISPLAYSURF.blit(text_surface,(WIDTH-PANEL_WIDTH+20,HEIGHT//2))
    K+=1
    
    pygame_widgets.update(events)
    pygame.display.update()
    frames_per_second.tick(FPS)

