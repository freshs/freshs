
##modify this line if you don't have Espresso on your PATH, but you still want to run the espresso tests
ESPRESSO_PATH=~/Espresso/bin/Espresso

WIN=-w
KEEP=-k
LOG=

all: WIN=
all: KEEP=
all: clean tests status

.PHONY: status
status:
	@grep -e FAIL -e SUCCESS *_log.txt

tests: riot_spres ell_spres ell_ffs espresso_spres espresso_ffs

.PHONY: riot_spres
riot_spres: LOG=-l riot_spres_log.txt
riot_spres:
	@echo "testing riot_spres"
	./test_freshs.bash $(WIN) $(KEEP) $(LOG) -r test_riot_spres/riot_spres_ref.sqlite -c test_riot_spres/riot_spres.conf -h ../harnesses/riot -e /bin/bash -p prof_riot_spres.txt
	@echo

espresso_spres : LOG=-l espresso_spres_log.txt
espresso_spres : have_espresso
	@echo "testing espresso_spres"
	./test_freshs.bash $(WIN) $(KEEP) $(LOG) -r test_espresso_spres/espresso_spres_ref.sqlite -c test_espresso_spres/espresso_spres.conf -h ../harnesses/espresso -e $(ESPRESSO_PATH) -p prof_espresso_spres.txt 
	@echo

espresso_ffs : LOG=-l espresso_ffs_log.txt
espresso_ffs : have_espresso
	@echo "testing espresso_ffs"
	./test_freshs.bash $(WIN) $(KEEP) $(LOG) -r test_espresso_ffs/espresso_ffs_ref.sqlite -c test_espresso_ffs/espresso_ffs.conf -h ../harnesses/espresso -e $(ESPRESSO_PATH) -p prof_espresso_ffs.txt 
	@echo

espresso_nsffs : LOG=-l espresso_ffs_log.txt
espresso_nsffs : have_espresso
	@echo "testing espresso_nsffs"
	./test_freshs.bash $(WIN) $(KEEP) $(LOG) -r test_espresso_nsffs/espresso_nsffs_tif_ref.sqlite -c test_espresso_nsffs/espresso_nsffs_tif.conf -h ../harnesses/espresso -e $(ESPRESSO_PATH) -p prof_espresso_nsffs_tif.txt 
	@echo

have_espresso :
	@echo "testing for Espresso executable" on path $(ESPRESSO_PATH)
	@which $(ESPRESSO_PATH)

.PHONY : clean
clean:
	rm -f *~ *\# 20[1-9][0-9]-[0-1][0-9]*
	rm -Rf CONF
	rm -f *auto* DB/* OUTPUT/* initialcfg.xyz ellOutTraj.etj
	rm -f profile.dat prof*.txt *_log.txt server.log

.PHONY : clobber
clobber : clean
	rm -f ../server/*.pyc ../server/*~
	rm -f ../client/*.pyc ../client/*~






