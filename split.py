import re
from sys import argv
from os.path import exists

page = re.compile("<page>(.+)</page>", re.MULTILINE|re.DOTALL)
text = re.compile("<text xml:space=\"preserve\">(.+)</text>", re.MULTILINE|re.DOTALL)
title = re.compile("<title>([^>]+)</title")

current = ""

for line in open(argv[1]):
	current += line
	if current.find("</page>")==-1:
		continue
	
	match = page.search(current)
	content = text.search(current).groups()[0]
	name = title.search(current).groups()[0]

	fname = "test/possible/%s.xml"%(name.replace("/", "_"))
	if not exists(fname):
		print name
		open(fname, "wb").write(current[match.start():match.end()])

	current = current[match.end():]
