import re
import codecs

import locale
import sys

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

title = re.compile("<title>([^>]+)</title")
text = re.compile("<text xml:space=\"preserve\">(.+)")
bracket = re.compile("((?:{{)|(?:}})|\(|\)|(?:(?<!')''(?!'))|\n)")
link = re.compile("((?:\[\[)|(?:\]\]))")

debug = False

removesets = [
		["&lt;!--", "--&gt;"],
		["&lt;ref&gt;", "&lt;/ref&gt;"]
		]

for r in removesets:
	r.append(re.compile("%s.+?%s"%tuple(r), re.MULTILINE|re.DOTALL))

redirects = {}

def generate_next(fname, existing):
	current = None
	intext = False
	earlierText = ""

	dump = codecs.open(fname, "rb", "utf-8")
	for line in dump:
		if current!=None:
			if not intext:
				poss = text.search(line)
				if poss!=None:
					intext = True
					if debug:
						print "poss", poss.groups()
					line = poss.groups()[0]
					earlierText = ""
					brackets = []
				else:
					continue
			
			if debug:
				print "line", line
			earlierText += "\n" + line

			continueLoop = False
			for (first, second, pattern) in removesets:
				if earlierText.find(first)!=-1 and earlierText.find(second)==-1:
					continueLoop = True
					if debug:
						print "looking for", second
					break # find remove bit end

				while True:
					comm = pattern.search(earlierText)
					if comm == None:
						break
					else:
						if debug:
							print "replaced", earlierText[comm.start():comm.end()]
						earlierText = earlierText[:comm.start()] + earlierText[comm.end():]
			
			if continueLoop:
				continue

			linkbegin = None
			linkcount = 0

			for l in link.finditer(earlierText):
				bit = l.groups()[0]
				if bit == "[[":
					if linkcount == 0:
						linkbegin = l.start()+2
					linkcount +=1
				elif bit == "]]":
					linkcount -=1
				else:
					raise Exception, bit

				if linkcount == 0:
					newlink = earlierText[linkbegin:l.start()]
					linkend = l.start()
					if newlink.find("#")!=-1:
						newlink = newlink[:newlink.find("#")]
						if len(newlink) == 0:
							continue
				else:
					continue
				
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
					if namespace in ("file", "image", "template", "wikipedia", "wikt", "category", "wp", "wikinvest", "wiktionary"):
						continue
					if newlink.find("UTC")==-1 and newlink.find(": ")==-1:
						raise Exception, (current, newlink, earlierText[:l.end()])
				#print "earlier", earlierText

				for match in bracket.finditer(earlierText[:l.start()]):
					bra = match.groups()[0]
					if bra in ("{{", "("):
						brackets.append((bra, match.start()))
						if debug:
							print "open", earlierText[match.start()-10:match.end()+10], brackets
					elif bra in ("}}", ")"):
						# cope with mismatched brackets
						if bra == "}}":
							while len(brackets)>0 and brackets[-1][0] != "{{":
								brackets = brackets[:-1]
							brackets = brackets[:-1]
						elif bra == ")":
							# FIXME: While is a nasty hack to work around issues like the lack of a close in "Antoine Lavoisier"
							while len(brackets)>0 and brackets[-1][0] == "(":
								brackets = brackets[:-1]

								# don't strip extra brackets from outside the link
								if linkbegin < match.start() and linkend > match.end():
									break
						else:
							raise Exception, earlierText
						if linkbegin != None:
							# strip all brackets during links
							old = brackets
							brackets = [b for b in brackets if b[0] != "(" or b[1] <linkbegin or b[1]>linkend]
							if old!=brackets:
								print "before", old
								print "after", brackets

						if debug:
							print "close", linkbegin, earlierText[match.start()-10:match.end()+10], brackets
					elif bra == "''":
						if debug:
							print "saw a ''", brackets, match.start(), earlierText[match.start()-10:match.end()+10]
						if len(brackets)>0 and brackets[-1][0] == "''":
							brackets = brackets[:-1]
						else:
							brackets.append((bra, match.start()))
					elif bra == "\n":
						if len(brackets)>0 and brackets[-1][0] == "''":
							brackets = brackets[:-1]
					else:
						raise Exception, (bra, earlierText[:l.start()])

				if len(brackets) > 0:
					if debug:
						print "bad match", brackets, newlink, "text", earlierText
					earlierText = earlierText[l.end():]
					break
				
				brackets = []

				if newlink in redirects:
					raise Exception, (newlink, redirects[newlink])

				yield (current, newlink)
				linkbegin = None
				current = None
				intext = False
				break

			if intext and earlierText.find("</text>")!=-1:
				raise Exception, current

		poss = title.search(line)
		if poss!=None:
			assert current == None
			current = poss.groups()[0]
			if existing(current):
				print "already have", current
				current = None
			elif current.find("Wikipedia:")!=-1:
				print "wikipedia internal link", current
				current = None
			else:
				if debug:
					print "title", current
		else:
			continue

def sqlite_existing(title):
	cur.execute("select name from links where name=?", (title,))
	f = cur.fetchall()
	return len(f)==1

if __name__ == "__main__":
	import sqlite3
	from sys import argv
	con = sqlite3.connect("links.sqlite")
	con.text_factory = unicode
	cur = con.cursor()
	cur.execute("select name from sqlite_master where type='table' and name='links'")
	if len(cur.fetchall())==0:
		cur.execute("create table links (name text primary key, next text, loopCount int, waysHere int)")

	for (name, to) in generate_next(argv[1], sqlite_existing):
		print "new", name, to
		cur.execute("insert into links values (?, ?, 0, 1)",(name, to))
		con.commit()

