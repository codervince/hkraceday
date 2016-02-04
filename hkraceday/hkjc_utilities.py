import unicodedata
import re

def getfullraceclassname(rc):
	if int(rc) in range(1,6):
		return "Class " + str(rc)
	else:
		return "Group"

def removeunicode(mystr):
	remap = {u'\xa0': None}
	mystr = unicodedata.normalize('NFD', mystr)
	l = re.findall(r'\d+', mystr)
	return reduce(lambda x, y: x+y, l)
	# mystr.replace(u'\xa0', u'').replace(u'\xa0\xa0', u'')
	# return mystr

def doprint(*args):
	print_stmt = "{}"*len(args)
	print print_stmt.format(*args)

def postostring(pos):
	if pos == 99 or pos is None:
		return 'x'
	if pos == 1:
		return 'w'
	if pos.isdigit() and pos != 99:
		return 'l'

def get_winlossstring(lis):
	'''
	take a list of positions and returns win or loss
	'''
	return map(postostring, lis)


def get_raceclass(cl):
	hkjcclasses = {
	"HongKongGroupThree": u'HKG3',
	"HongKongGroupTwo": u'HKG2',
	"HongKongGroupOne": u'HKG1',
	"Class1": u'1',
	"Class2": u'2',
	"Class3": u'3',
	"Class4": u'4',
	"Class5": u'5',
	"RestrictedRace": u'R',
	}
	return hkjcclasses.get(cl, "None")
'''
"A+3" Course
'''
def get_surface(s):
    s = s.strip()
    surfaces = {
    u"-": "AWT",
    u"-": "AWT",
    u"AWT": "AWT",
    u"C+3": "C+3",
    u"B+2": "B+2",
    u"C": "C",
    u"A+3": "A+3",
    u'"A" Course':"A",
    u'"B" Course':"B",
    u'"C" Course':"C",
    u'"A+3" Course':"A+3",
    u'"C+3" Course':"C+3"
    }
    # return s.translate(surfaces)
    try:
        return surfaces.get(s, "No surface found in dict")
    except KeyError:
        return "No Surface found"

def get_goingabb(g, track):
	g = g.strip()
	goings = {
	u"Good": u'G',
	u"Good to Firm": u'GF',

	}
	awt_goings = {
	u'Good': u'GD',
	u'Wet Fast': u'WF'
	}
	if track == u'All Weather Track':
		return awt_goings.get(g, "None")
	else:
		return goings.get(g, "None")
'''
rules -
sliced actual rps [2, 1, 1, 2]
'''
def nullcheck(s):
	return s is not None and s != []

def ismadeall(rplist):
	return sum(rplist) == len(rplist) #all ones

def islostlead(rplist):
	if nullcheck(rplist):
		rplist = rplist[:-1]
		return sum(rplist) == len(rplist) #all ones except last

def pasthorsessecl1(rplist):
	if nullcheck(rplist) and len(rplist)>2:
		secl1 = rplist[-1]
		secl2 = rplist[-2]
		return secl2 - secl1

# 1,2,3 for al but last sec
def isonpace(rplist):
	if nullcheck(rplist):
		rplist = rplist[:-1]
		onpaces = [ x for x in rplist if x in [1,2,3]]
		return len(onpaces) == len(rplist)

def isbackmarker(rplist):
	if nullcheck(rplist):
		rplist = rplist[:2]
		bms = [ x for x in rplist if x >=10]
		return len(bms) == len(rplist)
