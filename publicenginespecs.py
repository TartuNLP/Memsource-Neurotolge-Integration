from collections import defaultdict

# ID: [ 'auth', isOldAPI ]
engines = { 'public': ['public', False],
	'newdefinedengineexample': ['passwordexample', True] }

#lists each user's access to translation engines
userExtraEngineAccess = defaultdict( lambda: ['public'], {
	'somenewuserexample': ['public', 'newdefinedengineexample']]
	})
