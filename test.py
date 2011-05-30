from os import listdir
from os.path import join
from generate_next import generate_next
import codecs

test_dir = "test"

tests = {}

for line in codecs.open(join(test_dir, "list.txt"), "rb", "utf-8"):
	(name, to, fname) = line.strip().split(",")
	tests[fname] = (name, to)

for fname in listdir(test_dir):
	if fname.find(".xml")!=-1:
		found = False
		for (name, to) in generate_next(join(test_dir, fname), lambda x:False):
			assert not found
			assert fname in tests, (fname, (name, to))
			assert tests[fname] == (name, to), (tests[fname], (name, to))
			found = True
		assert found, fname

