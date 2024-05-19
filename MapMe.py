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
DATA_DIR="data/"
BORDER=12
SELECT_THICKNESS=6
STEP=16
MIN_STEP=3
FAR_CUTOFF=3
LOW_MEM=True
ZOOM_THRESH=24
ENABLE_ZOOM=True
AA_ALL_TEXT=False
MODE=0

def lcs(X, Y, m=None, n=None):
    if m is None: m=len(X)
    if n is None: n=len(Y)
    if m == 0 or n == 0:
       return 0;
    elif X[m-1] == Y[n-1]:
       return 1-0.01*(m+n) + lcs(X, Y, m-1, n-1);
    else:
       return max(lcs(X, Y, m, n-1), lcs(X, Y, m-1, n));

class ArtificialComboBox:
	def __init__(self,parent,opts,shape,alt_text="Select",match_threshold=1,**kwargs):
		self.loc=shape
		self.choices=np.array(opts,dtype=str)
		self.options=kwargs
		self.parent=parent
		self.base_text=alt_text
		self.focus=False
		self.threshold=match_threshold
		self.setup()
	
	def setup(self):
		self.rect=pygame.Rect(*self.loc)
		self.max_guess=5 if "max_guess" not in self.options else int(self.options["max_guess"])
		self.clear()
	
	def clear(self):
		self.text=self.base_text
		self.typing=False
	def get_text(self): return self.text.strip()
	def set_text(self,t,keep_typing=True):
		self.text=t
		self.typing=keep_typing
	
	def _get_predictions(self):
		query=self.get_text()
		if not len(query) or not self.typing: return []
		hdist=np.array([lcs(query,ch) for ch in self.choices])
		hdist_idx=np.argsort(hdist)[::-1]
		hdist=hdist[hdist_idx]
		#print(hdist)
		res=list(self.choices[hdist_idx[hdist>=self.threshold]])
		if not len(res): return []
		else: return res[:self.max_guess]
	
	def update(self,events):
		if self.focus:
			col=YELLOW if "focuscolor" not in self.options else self.options["focuscolor"]
		else:
			col=WHITE if "bgcolor" not in self.options else self.options["bgcolor"]
		hlcol=None if "hlcolor" not in self.options else self.options["hlcolor"]
		bthick=2 if "border" not in self.options else int(self.options["border"])
		bordcol=BLACK if "bordercolor" not in self.options else self.options["bordercolor"]
		pygame.draw.rect(self.parent,col,self.rect)
		
		tsx=10 if "text_x_shift" not in self.options else self.options["text_x_shift"]
		tsy=5 if "text_y_shift" not in self.options else self.options["text_y_shift"]
		text_surface = DEFAULT_FONT.render(self.text, AA_ALL_TEXT, BLACK)
		self.parent.blit(text_surface,(self.loc[0]+tsx,self.loc[1]+tsy))
		
		band_height=self.loc[-1] if "band_height" not in self.options else self.options["band_height"]
		
		found=False
		found_idx=-1
		if self.focus:
			bx,by=self.loc[0],self.loc[1]+self.loc[3]
			for i,pred in enumerate(self.preds):
				nR=pygame.Rect(bx,by,self.loc[2],band_height)
				if nR.collidepoint(*pygame.mouse.get_pos()):
					found=True
					found_idx=i
					break
				by+=band_height
				
		for event in events:
			if event.type == pygame.MOUSEBUTTONDOWN:
				if self.rect.collidepoint(*pygame.mouse.get_pos()):
					self.focus=True
				elif self.focus:
					if found:
						self.set_text(pred,False)
					self.focus=False
				else:
					continue
			if not self.focus: continue
			if event.type==pygame.KEYDOWN and event.key<256:
				if (event.key<97 or event.key>123) and event.key not in (32,8): continue
				if event.key==8 and len(self.text):
					if not self.typing: self.text=""
					else: self.text=self.text[:-1]
					continue
				elif event.key!=8:
					ch=chr(event.key)
					if self.typing: self.text+=ch
					else:
						self.text=ch
						self.typing=True
		
		if self.focus:
			all_guesses=self._get_predictions()
			self.preds=all_guesses
			bx,by=self.loc[0],self.loc[1]+self.loc[3]
			for i,pred in enumerate(all_guesses):
				if found and found_idx==i and hlcol is not None: pygame.draw.rect(self.parent,hlcol,(bx,by,self.loc[2],band_height))
				else: pygame.draw.rect(self.parent,col,(bx,by,self.loc[2],band_height))
				text_surface = DEFAULT_FONT.render(pred.strip(), AA_ALL_TEXT, BLACK)
				self.parent.blit(text_surface,(bx+10,by+5))
				by+=band_height
		
		pygame.draw.rect(self.parent,bordcol,(self.loc[0]-bthick,self.loc[1]-bthick,self.loc[2]+2*bthick,self.loc[3]+2*bthick),bthick)
				

class ArtificialWidgets:
	def __init__(self):
		self.widgets=[]
	
	def addWidget(self,obj): self.widgets.append(obj)
	def update(self,events):
		for obj in self.widgets: obj.update(events)
		

class DynamicMapLoader:
	def __init__(self,mapfol,ext=".npz",memorize=True):
		self.folder=mapfol
		self.ext=ext
		self.maps=dict()
		self.mem=True
	
	def __getitem__(self,x):
		if x not in self.maps:
			map=np.load(self.folder+"/"+x+self.ext)["data"]
			if not self.mem: return map
			else: self.maps[x]=map
		return self.maps[x]
	
	def reset(self):
		self.maps=dict()

## Game data
print("Loading country names and connections ...",end=" ",flush=True)
country_names=np.load("data/indexed_countries.npy")
countries_for_dropdown=[s.replace("_"," ") for s in country_names]
country_adj=np.load("data/adjacency2.npy")
country_adj=country_adj | country_adj.transpose() # Symmetrize
assert (country_adj.shape[0]==len(country_names))
print("done",flush=True)

all_data=sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".npz")])
if not LOW_MEM:
	maps=dict()
	print("Loading all country maps ...",end=" ",flush=True)
	for f in all_data:
		  map=np.load("data/"+f)["data"]
		  country=f[:-4].lower()
		  maps[country]=map
	print("done")
else:
	print("Using low memory mode - dynamic map loading",flush=True)
	maps=DynamicMapLoader(DATA_DIR)
	print("Map loader is setup",flush=True)

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
        self.zoom=None
        self.cropping=None
        
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
    	if (self.zoom is None) or not ENABLE_ZOOM:
    		grid_bounds_x,grid_bounds_y=np.where(final_grid)
    		x_min=np.min(grid_bounds_x)
    		x_max=np.max(grid_bounds_x)
    		y_min=np.min(grid_bounds_y)
    		y_max=np.max(grid_bounds_y)
    	else:
    		x_min,x_max=self.zoom[0]
    		y_min,y_max=self.zoom[1]
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
    
    def on_grid(self,x,y):
    	if x<0 or y<0: return False
    	try:
    		v=self.final_grid[y,x]
    		return True
    	except IndexError: return False
    def bound_to_grid(self,x,y):
    	if x<0:
    		x=0
    	if y<0:
    		y=0
    	return x,y
    
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
BOLD_DEFAULT_FONT = pygame.font.SysFont('Calibri', 20,bold=True)


# Standard drawing protocols
def draw_title():
	text_surface = TITLE_FONT.render('Connect '+start.replace("_"," ")+' to '+end.replace("_"," ")+" in "+str(puz.rank-1)+" guesses", True, TITLE_TEXT_COLOR)
	DISPLAYSURF.blit(text_surface,(100,5))
def draw_extras():
	pygame.draw.rect(DISPLAYSURF,GREY,PANEL_RECT)
	pygame.draw.rect(DISPLAYSURF,TITLE_COLOR,TITLE_RECT)
	draw_title()
def draw_rules(antialias=True):
	pygame.draw.rect(DISPLAYSURF,GREY,(0,0,WIDTH-PANEL_WIDTH,HEIGHT))
	heading = TITLE_FONT.render("Rules", True, BLACK)
	DISPLAYSURF.blit(heading,((WIDTH-PANEL_WIDTH)//2-50,5))
	line1=DEFAULT_FONT.render("You will be given 2 countries to connect. Guess other nearby countries to form a", antialias, BLACK)
	line2=DEFAULT_FONT.render("connected linkage between the two. Some connections can go through water-ways.", antialias, BLACK)
	line3=DEFAULT_FONT.render("Guess which ones!", antialias, BLACK)
	line4=DEFAULT_FONT.render("The optimal path length (minimum guesses required) is given.", antialias, BLACK)
	DISPLAYSURF.blit(line1,(40,50))
	DISPLAYSURF.blit(line2,(40,75))
	DISPLAYSURF.blit(line3,(40,100))
	DISPLAYSURF.blit(line4,(40,125))
	
	sh2=BOLD_DEFAULT_FONT.render("Color codes",True,BLACK)
	DISPLAYSURF.blit(sh2,(40,175))
	
	red_name=DEFAULT_FONT.render("Red",antialias,RED)
	yellow_name=DEFAULT_FONT.render("Yellow",antialias,YELLOW)
	orange_name=DEFAULT_FONT.render("Orange",antialias,ORANGE)
	green_name=DEFAULT_FONT.render("Green",antialias,GREEN)
	
	line1_1=DEFAULT_FONT.render("indicates countries you identified, and are part of an optimal path", antialias, BLACK)
	line1_2=DEFAULT_FONT.render("between the two countries", antialias, BLACK)
	line2=DEFAULT_FONT.render("indicates that you are close but not on the optimal path", antialias, BLACK)
	line3_1=DEFAULT_FONT.render("indicates that you are way off. The 'Hide bad guesses' button", antialias, BLACK)
	line3_2=DEFAULT_FONT.render("can hide these for brevity", antialias, BLACK)
	line4=DEFAULT_FONT.render("indicates the start and end countries", antialias, BLACK)
	DISPLAYSURF.blit(green_name,(60,210))
	DISPLAYSURF.blit(line1_1,(150,210))
	DISPLAYSURF.blit(line1_2,(150,230))
	DISPLAYSURF.blit(orange_name,(60,260))
	DISPLAYSURF.blit(line2,(150,260))
	DISPLAYSURF.blit(red_name,(60,285))
	DISPLAYSURF.blit(line3_1,(150,285))
	DISPLAYSURF.blit(line3_2,(150,305))
	DISPLAYSURF.blit(yellow_name,(60,330))
	DISPLAYSURF.blit(line4,(150,330))
	
	line1=DEFAULT_FONT.render("Hovering the mouse over any country in the map shows its name in the right-side panel", antialias, BLACK)
	DISPLAYSURF.blit(line1,(40,375))
	line1=DEFAULT_FONT.render("To guess an intermediate country click on the textbox and start typing", antialias, BLACK)
	line2=DEFAULT_FONT.render("A drop-down box will automatically suggest possible countries. Click on one to select", antialias, BLACK)
	line3=DEFAULT_FONT.render("Click on 'Guess' to commit to your guess after selecting a country", antialias, BLACK)
	DISPLAYSURF.blit(line1,(40,400))
	DISPLAYSURF.blit(line2,(40,425))
	DISPLAYSURF.blit(line3,(40,450))
	
	line4=DEFAULT_FONT.render("Click on 'Reset' to restart the game with another pair of starting countries", antialias, BLACK)
	DISPLAYSURF.blit(line4,(40,500))

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
CLICK_START=None
CLICK_START_ORIG=None
#path=None

# Interactable functions
def confirm_button():
	global K,GUESSES,puz,DRAWN_MAP
	#ce=dropdown_countries.getText().strip().lower()
	ce=art_combobox.get_text()
	if ce=="" or ce==art_combobox.base_text: return
	ce=ce.replace(" ","_")
	GUESSES+=1
	try:
		idx=list(country_names).index(ce)
	except:
		return
	puz.guess(idx)
	#dropdown_countries.textBar.text.clear()
	art_combobox.clear()
	vic=puz.victory()
	if vic:
		button_confirm.hide()
		button_win.show()
	print("Victory\n",vic)
	DRAWN_MAP=get_map_image(puz)
	K=0

def reset_button(via_button=True):
	global K,GUESSES,puz,start,end,DRAWN_MAP,button_confirm,maps
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
	if via_button and LOW_MEM:
		maps.reset()
		print("Low memory mode - Clearing map cache",flush=True)

def unblock_button():
	#dropdown_countries.textBar.text.clear()
	#dropdown_countries.reset()
	art_combobox.clear()

def help_button():
	global MODE,button_help
	if MODE==0:
		MODE=1
		button_help.setText("Back to game")
		button_confirm.disable()
		button_unblock.disable()
		button_reset_zoom.disable()
	else:
		MODE=0
		button_help.setText("Help (Rules)")
		button_confirm.enable()
		button_unblock.enable()
		button_reset_zoom.enable()

def hide_far_button():
	global button_hide_far,HIDE_FAR,K,DRAWN_MAP
	HIDE_FAR=not HIDE_FAR
	if HIDE_FAR: button_hide_far.setText("Show all")
	else: button_hide_far.setText("Hide bad guesses")
	DRAWN_MAP=get_map_image(puz)
	K=0

def reset_zoom_button():
	global puz,DRAWN_MAP,K,CLICK_START,CLICK_START_ORIG
	CLICK_START=None
	CLICK_START_ORIG=None
	puz.zoom=None
	DRAWN_MAP=get_map_image(puz)
	K=0

# Mouse Actions
## Click down
def click_down(x,y):
	global CLICK_START,CLICK_START_ORIG
	if x>WIDTH-PANEL_WIDTH or y<TITLE_HEIGHT:
		CLICK_START=None
		CLICK_START_ORIG=None
		return
	CLICK_START_ORIG=(x,y)
	cx,cy=puz.bound_to_grid(*backmap(x,y))
	CLICK_START=(cx,cy)
## Click up
def click_up(x,y):
	global puz,DRAWN_MAP,K,CLICK_START,CLICK_START_ORIG
	if CLICK_START is None: return
	cx,cy=puz.bound_to_grid(*backmap(x,y))
	cxo,cyo=CLICK_START[0],CLICK_START[1]
	if abs(cxo-cx)<ZOOM_THRESH or abs(cyo-cy)<ZOOM_THRESH:
		CLICK_START=None
		CLICK_START_ORIG=None
		return
	else:
		if cxo>cx: cx,cxo=cxo,cx
		if cyo>cy: cy,cyo=cyo,cy
		cxo+=puz.cropping[1][0]
		cx+=puz.cropping[1][0]
		cyo+=puz.cropping[0][0]
		cy+=puz.cropping[0][0]
		if cx>puz.cropping[1][1]: cx=puz.cropping[1][1]
		if cy>puz.cropping[0][1]: cy=puz.cropping[0][1]
		puz.zoom=((cyo,cy),(cxo,cx))
	CLICK_START=None
	CLICK_START_ORIG=None
	DRAWN_MAP=get_map_image(puz)
	K=0


# Interactables
## Dropdown of countries
#dropdown_countries = ComboBox(DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, TITLE_HEIGHT+100+BUTTONS_HEIGHT+12, PANEL_WIDTH-2*PANEL_BORDER, DROPDOWNS_HEIGHT, name='Select guess country',
#    choices=countries_for_dropdown,
#    maxResults=5,
#    font=pygame.font.SysFont('calibri', 30),
#    borderRadius=3, colour=DROPDOWNS_COLOR, direction='down',
#    textHAlign='left')

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
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, HEIGHT-2*BUTTONS_HEIGHT, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Reset', fontSize=30,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=reset_button, font=pygame.font.SysFont('calibri', 18))
## Unblock button
button_unblock=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, TITLE_HEIGHT+100-BUTTONS_HEIGHT-10, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Clear Box', fontSize=30,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=unblock_button, font=pygame.font.SysFont('calibri', 18))
button_help=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, HEIGHT-150-int(6*BUTTONS_HEIGHT), PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Help (Rules)', fontSize=30,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=help_button, font=pygame.font.SysFont('calibri', 18))
   
## Hide-far button
button_hide_far=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, HEIGHT-150-2*BUTTONS_HEIGHT, PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Hide bad guesses', fontSize=27,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=hide_far_button, font=pygame.font.SysFont('calibri', 18))
button_reset_zoom=Button(
    DISPLAYSURF, WIDTH-PANEL_WIDTH+PANEL_BORDER, HEIGHT-150-int(3.5*BUTTONS_HEIGHT), PANEL_WIDTH-2*PANEL_BORDER, BUTTONS_HEIGHT, text='Reset Zoom', fontSize=27,
    margin=15, inactiveColour=BUTTONS_COLOR, hoverColour=(60, 60, 60), pressedColour=(128, 128, 128),
    radius=5, onClick=reset_zoom_button, font=pygame.font.SysFont('calibri', 18))

# Pick the two countries:
reset_button(via_button=False)

# Manually add artificial stuff
ARTIFICIAL_WIDGETS=ArtificialWidgets()
art_combobox=ArtificialComboBox(DISPLAYSURF,countries_for_dropdown,(WIDTH-PANEL_WIDTH+PANEL_BORDER, TITLE_HEIGHT+100+BUTTONS_HEIGHT+12, PANEL_WIDTH-2*PANEL_BORDER, DROPDOWNS_HEIGHT),"Select country (type ...)",band_height=DROPDOWNS_HEIGHT//2,text_y_shift=15,hlcolor=GREEN)
ARTIFICIAL_WIDGETS.addWidget(art_combobox)


print(lcs("china","ind"),lcs("india","ind"))
# Start the gameloop
while True:
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        elif MODE==0 and (event.type == pygame.MOUSEBUTTONDOWN):
        	click_down(*pygame.mouse.get_pos())
        elif MODE==0 and (event.type == pygame.MOUSEBUTTONUP):
        	click_up(*pygame.mouse.get_pos())
    
    if MODE==1:
    	draw_rules()
    else:
    	if K%DRAW_MOD==0 or CLICK_START_ORIG is not None:
    		DISPLAYSURF.fill(BLACK)
    		draw_map(puz)
    		K=0
    		if CLICK_START_ORIG is not None:
    			cmous=pygame.mouse.get_pos()
    			ox,oy=CLICK_START_ORIG[0],CLICK_START_ORIG[1]
    			w,h=abs(cmous[0]-CLICK_START_ORIG[0]),abs(cmous[1]-CLICK_START_ORIG[1])
    			if ox>cmous[0]: ox=cmous[0]
    			if oy>cmous[1]: oy=cmous[1]
    			pygame.draw.rect(DISPLAYSURF,WHITE,pygame.Rect(ox,oy,w,h),SELECT_THICKNESS)
		  
    	if K%MOUSEOVER_MOD==0:
    		draw_extras()
    		mouse_pos=pygame.mouse.get_pos()
    		backmap_pos=backmap(*mouse_pos)
    		country_text=puz.get_country_at(*backmap_pos)
    		if country_text is not None:
    			text_surface = DEFAULT_FONT.render(country_text, True, BLACK)
    			DISPLAYSURF.blit(text_surface,(WIDTH-PANEL_WIDTH+20,HEIGHT//2-100))
    	K+=1
    
    pygame_widgets.update(events)
    if MODE==0:
    	ARTIFICIAL_WIDGETS.update(events)
    pygame.display.update()
    frames_per_second.tick(FPS)

