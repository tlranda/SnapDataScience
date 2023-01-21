import pandas as pd
import argparse
import numpy as np
from pprint import pprint,pformat

LOC_KEYS = ['loc:left','loc:middle','loc:right']

# Uses reference files to find nice replacements for displaying strings vs their CSV equivalent
class NiceName:
	def __init__(self):
		self.initialized = False
		self.references = {'locations': 'all_locations.json',
						   'decks': 'all_decks.json',
						   'cards': 'all_cards.json',}
		self.unniceable = []

	def initialize(self):
		import json
		import pdb
		pdb.set_trace()
		self.reversible = []
		for k,v in self.references.items():
			try:
				setattr(self,k,json.load(open(v,'r')))
			except IOError:
				print(f"WARNING: NiceNames failed to load {k} (from {v})")
			else:
				setattr(self,'reverse_'+k,dict((v,k) for (k,v) in getattr(self,k).items()))
				self.reversible.append(k)
		del json
		self.initialized = True

	def nice(self, string):
		if not self.initialized:
			return string
		else:
			for k in self.reversible:
				reverse_dict = getattr(self,'reverse_'+k)
				if string in reverse_dict.keys():
					return reverse_dict[string]
			if string not in self.unniceable:
				print(f"WARNING: Could not nice-ify: {string}")
				self.unniceable.append(string)
			return string

	def __call__(self, string):
		return self.nice(string)

nice = NiceName()

# Take CSV locations and split into Left Right and Middle locations
def location_split(data,delim=',',padding='PADDING'):
	locations = data['locations'].tolist()
	left, middle, right = [], [], []
	for entry in locations:
		locs = entry.split(delim)
		while len(locs) < 3:
			locs.append(padding)
		left.append(locs[0])
		middle.append(locs[1])
		right.append(locs[2])
	for col, coldata in zip(LOC_KEYS, [left,middle,right]):
		data[col] = coldata
	return data

# Take CSV cards and split into max-len list of cards
# Padding is DYNAMIC because while I don't track non-deck cards, Thanos etc may create track-able cards midgame and I'll want to know which stones got played etc
def cards_split(data, delim=',',padding='PADDING'):
	cards = data['cards'].tolist()
	new_cards = []
	max_len = 0
	for entry in cards:
		game_cards = entry.split(delim)
		max_len = max(max_len, len(game_cards))
		new_cards.append(game_cards)
	for entry in new_cards:
		while len(entry) < max_len:
			entry.append(padding)
	data['cards'] = new_cards
	return data

# Determine how many locations repeat and statistics about their repetition
def locationAnalyzer(data,args):
	padding = args.padding
	stacked_locations = np.hstack([data[loc].iloc[idx] for idx in range(len(data)) for loc in LOC_KEYS])
	unique_locations = sorted(set(stacked_locations)-set([padding]))
	N_LOCS = len(stacked_locations) - stacked_locations.tolist().count(padding)
	# Template to fill out per location
	insight = {'location': [],
			   'n_occur': [],
			   'appearance_rate': [],
			   'avg_sep': [],
			   }
	for k in LOC_KEYS:
		insight[k] = []
	for uniq in unique_locations:
		insight['location'].append(nice(uniq))
		indices = np.where(stacked_locations==uniq)[0]
		insight['n_occur'].append(len(indices))
		insight['appearance_rate'].append(len(indices)/N_LOCS)
		game_ids, game_mods = np.divmod(indices,3)
		for idx,k in enumerate(LOC_KEYS):
			insight[k].append(game_mods.tolist().count(idx))
		if insight['n_occur'][-1] > 1:
			between_games = [(j-i) for (i,j) in zip(game_ids[:-1], game_ids[1:])]
			insight['avg_sep'].append(sum(between_games)/len(between_games))
		else:
			insight['avg_sep'].append(np.inf)
	insight = pd.DataFrame(insight)
	return insight.sort_values(by='n_occur',ascending=False)

def streak_equals(arr,conds):
	if not hasattr(conds, '__iter__'):
		conds = [conds]
	# Get indices where condition is satisfied
	locs = []
	for cond in conds:
		locs = np.hstack((locs,np.where(arr==cond)[0]))
	locs.sort()
	streaks = []
	# Recursively condense streak-lengths
	while len(locs) > 0:
		streaks.append(len(locs))
		locs = np.where((locs[1:]-locs[:-1])==1)[0]
	# Remove n-repeat counted for all streaks
	for reverse_idx in range(len(streaks)-1,0,-1):
		for count,decreasing_idx in enumerate(range(reverse_idx-1,-1,-1)):
			streaks[decreasing_idx] -= (count+2)*streaks[reverse_idx]
	return streaks

def deckAnalyzer(data,args):
	match_results = data[['my deck','outcome','cubes','bot behavior?','deck archetype','archetype certain']]
	N_GAMES = len(match_results)
	OUTCOMES = ['SKIP','resolve','opp retreat','retreat']
	WINLOSS = [2,3]
	STR_OUTCOMES = ['WIN','LOSE','OPPONENT RETREAT','RETREAT']
	my_decks = sorted(set(match_results['my deck']))
	opp_decks = sorted(set(match_results['deck archetype']))
	matchups = {}
	for my_deck in my_decks:
		locs = match_results[match_results['my deck'] == my_deck].index
		filtered = match_results.iloc[locs]
		DECK_GAMES = len(filtered)
		outcomes = [OUTCOMES.index(o) & WINLOSS[int(c<0)] for (o,c) in zip(filtered['outcome'],filtered['cubes'])]
		insight = {}
		insight['sample_size'] = DECK_GAMES
		insight['winrate'] = (outcomes.count(0)+outcomes.count(2))/DECK_GAMES
		insight['netcubes'] = sum(filtered['cubes'])
		insight['cuberate'] = insight['netcubes']/DECK_GAMES
		insight['retreatrate'] = outcomes.count(3)/DECK_GAMES
		insight['spookrate'] = outcomes.count(2)/DECK_GAMES
		insight['winstreaks'] = streak_equals(np.asarray(outcomes), [0,2])
		insight['losestreaks'] = streak_equals(np.asarray(outcomes), [1,3])
		insight['botrate'] = filtered['bot behavior?'].tolist().count('yes')/DECK_GAMES
		insight['botcubes'] = filtered['cubes'].iloc[filtered[filtered['bot behavior?']=='yes'].index].sum()
		matchups[nice(my_deck)] = insight
	return matchups

def cardAnalyzer(data,args):
	padding = args.padding
	TOTAL_GAMES = len(data)
	tracked_cards = np.hstack(data['cards'])
	CARDS_PER_GAME = len(tracked_cards) // TOTAL_GAMES
	unique_cards = sorted(set(tracked_cards)-set([padding]))
	insight = {}
	for card in unique_cards:
		locs = np.where(tracked_cards==card)[0]
		game_idx = locs // CARDS_PER_GAME
		info = {}
		info['appearances'] = len(locs)
		info['appearance_rate'] = info['appearances']/TOTAL_GAMES
		info['archetypes'] = sorted(set(data['deck archetype'].iloc[game_idx]))
		info['bot_likelihood'] = len(set(game_idx)-set(data[data['bot behavior?']=='no'].index))/info['appearances']
		insight[nice(card)] = info
	# Supply some sort orders
	insight['SORT_NAME'] = [k for k in insight.keys()]
	# argsort([insight[c]['appearances'] for c in insight.keys()])[::-1] doesn't preserve alphabetical order
	# So I have to iteratively build it instead
	appearances = np.asarray([insight[c]['appearances'] for c in insight.keys() if not c.startswith('SORT')])
	uniq_appear = sorted(set(appearances))[::-1]
	insight['SORT_APPEARANCES'] = []
	for ua in uniq_appear:
		insight['SORT_APPEARANCES'] = np.hstack((insight['SORT_APPEARANCES'], np.where(appearances==ua)[0]))
	insight['SORT_APPEARANCES'] = insight['SORT_APPEARANCES'].astype(int)
	return insight

def initial_load(args):
	data = pd.read_csv(args.file)
	data = location_split(data)
	data = cards_split(data)
	if args.nice_names:
		nice.initialize()
	return data

def parse(prs,args=None):
	if args is None:
		args = prs.parse_args()
	return args

def build():
	prs = argparse.ArgumentParser()
	prs.add_argument('--file',required=True,help="CSV to analyze")
	prs.add_argument('--padding',default='PADDING',type=str,help="Padding token for locations and cards")
	prs.add_argument('--card-sort',choices=['SORT_NAME','SORT_APPEARANCES'],default='SORT_APPEARANCES',help="Order for card data")
	prs.add_argument('--limit-cards',default=None,type=int,help="Maximum number of cards to display (default: ALL)")
	prs.add_argument('--nice-names',action='store_true',help="Replace location and card names with nicer versions when specified")
	return prs

def main(args):
	data = initial_load(args)
	print("--- LOCATION ANALYSIS ---")
	location_insight = locationAnalyzer(data,args)
	print(location_insight)

	print("--- DECK ANALYSIS ---")
	match_result_insight = deckAnalyzer(data,args)
	for k,v in match_result_insight.items():
		print(k)
		print('\t'+'\t'.join([l for l in pformat(v).splitlines(True)]))

	print("--- OPPONENT CARD ANALYSIS ---")
	card_insight = cardAnalyzer(data,args)
	sort_keys = [k for k in card_insight.keys() if k.startswith('SORT')]
	card_sortings = dict((k,card_insight.pop(k)) for k in sort_keys)
	sort = card_sortings[args.card_sort]
	if args.card_sort != 'SORT_NAME':
		sort = np.asarray(card_sortings['SORT_NAME'])[sort]
	if args.limit_cards is None:
		args.limit_cards = len(card_insight.keys())
	for limit in range(args.limit_cards):
		k = sort[limit]
		v = card_insight[k]
		print(k)
		print('\t'+'\t'.join([l for l in pformat(v).splitlines(True)]))

if __name__ == '__main__':
	main(parse(build()))

