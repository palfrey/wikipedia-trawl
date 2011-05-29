import sqlite3
from sys import argv
import re
import codecs

import locale
import sys

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

title = re.compile("<title>([^>]+)</title")
text = re.compile("<text xml:space=\"preserve\">(.+)")
link = re.compile("\[\[([^\]]+)\]\]")
comments = re.compile("&lt;!--.+?--&gt;", re.MULTILINE|re.DOTALL)
bracket = re.compile("((?:{{)|(?:}})|\(|\)|(?:(?<!')''(?!'))|\n)")

con = sqlite3.connect("links.sqlite")
con.text_factory = unicode
cur = con.cursor()
cur.execute("select name from sqlite_master where type='table' and name='links'")
if len(cur.fetchall())==0:
	cur.execute("create table links (name text primary key, next text, loopCount int, waysHere int)")

dump = codecs.open(argv[1], "rb", "utf-8")

current = None
intext = False
earlierText = ""

redirects = {}

for line in dump:
	if current!=None:
		if not intext:
			poss = text.search(line)
			if poss!=None:
				intext = True
				print "poss", poss.groups()
				line = poss.groups()[0]
				earlierText = ""
			else:
				continue
		
		earlierText += line

		if earlierText.find("&lt;!--")!=-1 and earlierText.find("--&gt;")==-1:
			continue # find comment end

		while True:
			comm = comments.search(earlierText)
			if comm == None:
				break
			else:
				earlierText = earlierText[:comm.start()] + earlierText[comm.end():]

		for l in link.finditer(earlierText):
			newlink = l.groups()[0]
			
			if earlierText.find("#REDIRECT")!=-1:
				print "saw redirect", newlink
				redirects[current] = newlink
				current = None
				intext = False
				break

			if newlink.find("|")!=-1:
				newlink = newlink.split("|")[0]

			if newlink.find(":")!=-1:
				if newlink[0] == ":":
					newlink = newlink[1:]
				namespace = newlink.split(":")[0].lower()
				if namespace.find(" ")!=-1:
					continue
				if namespace in ("file", "image", "template", "wikipedia", "wikt", "category", "wp", "wikinvest"):
					continue
				raise Exception, (newlink, earlierText[:l.end()])
			#print "earlier", earlierText

			brackets = []
			for match in bracket.finditer(earlierText[:l.start()]):
				bra = match.groups()[0]
				if bra in ("{{", "("):
					brackets.append(bra)
				elif bra in ("}}", ")"):
					# cope with mismatched brackets
					if bra == "}}":
						while len(brackets)>0 and brackets[-1] != "{{":
							brackets = brackets[:-1]
						brackets = brackets[:-1]
					elif bra == ")":
						if len(brackets)>0 and brackets[-1] == "(":
							brackets = brackets[:-1]
					else:
						raise Exception, earlierText
				elif bra == "''":
					if len(brackets)>0 and brackets[-1] == "''":
						brackets = brackets[:-1]
					else:
						brackets.append(bra)
				elif bra == "\n":
					if len(brackets)>0 and brackets[-1] == "''":
						brackets = brackets[:-1]
				else:
					raise Exception, (bra, earlierText[:l.start()])
			
			if len(brackets) > 0:
				#print "bad count", len(brackets), newlink.encode("ascii", "replace")
				continue

			if newlink in redirects:
				raise Exception, (newlink, redirects[newlink])

			if newlink[0] == "#":
				raise Exception, (newlink, earlierText)

			print "current", current, newlink
			cur.execute("insert into links values (?, ?, 0, 1)",(current, newlink))
			con.commit()
			current = None
			intext = False
			break

		if intext and earlierText.find("</text>")!=-1:
			raise Exception, earlierText

	poss = title.search(line)
	if poss!=None:
		assert current == None
		current = poss.groups()[0]
		cur.execute("select name from links where name=?", (current,))
		f = cur.fetchall()
		if len(f)==1:
			print "already have", current
			current = None
		else:
			print "title", current
	else:
		continue

