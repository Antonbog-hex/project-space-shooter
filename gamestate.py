# gamestate // all values set in main
active_object = None
bullets = None
planets = None
enemies = None
particle_effects = None
player = None
camera = None
waste_bin = [] # list to keep elements that will be removed in a later stage
#managers
chunkmanager = None # ChunkManager(around_chunks=1, chunk_size  = (5000,5000))
enemy_manager = None #EnemyManager()
score_manager = None #ScoreManager()
menu = None # Menu(screen)
