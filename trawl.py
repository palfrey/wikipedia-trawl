import codecs

import locale
import sys

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

import sqlite3
from sys import argv
con = sqlite3.connect("links.sqlite")
con.text_factory = unicode
cur = con.cursor()
cur.execute("select name, next from links order by name")

philosophy = 0
dead = 0
others = 0

while True:
	(name, onwards) = cur.fetchone()
	print name, "=>", onwards

	loop = [name]
	while True:
		if onwards == None:
			print "dead end"
			dead += 1
			break
		onwards = onwards.strip()
		onwards = (onwards[0].upper() + onwards[1:]).replace("_", " ")
		if onwards in loop:
			print "found loop", onwards, loop
			if "Philosophy" in loop:
				philosophy +=1
			else:
				others +=1
			print "scores", philosophy, others, dead
			break
		print "onwards", onwards
		loop.append(onwards)
		cur2 = con.cursor()
		cur2.execute("select next from links where name=?", (onwards,))

		ret = cur2.fetchone()

		if ret == None:
			print "fail"
			cur2 = con.cursor()
			cur2.execute("select next from redirects where name=?", (onwards,))
			ret = cur2.fetchone()
			if ret == None:
				print "fail", onwards
				dead += 1
				break

		onwards = ret[0]

