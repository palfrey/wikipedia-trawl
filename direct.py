import sqlite3
from urlgrab import Cache
from lxml import etree
from lxml.html.soupparser import fromstring
from sys import argv

cache = Cache()

def get_next_link(page):
	main = etree.HTML(cache.get("http://en.wikipedia.org/wiki/"+page, max_age=-1).read())
	content = main.xpath(".//div[@id='content']")
	assert len(content)==1, content
	content = content[0]

	for link in content.iterfind(".//a"):
		if "href" not in link.attrib:
			continue
		href = link.attrib["href"]
		#if href.find("/wiki/")==-1 or href.find("/wiki/Wikipedia:")!=-1 or href.find("/wiki/Portal:")!=-1 or href.find("/wiki/Template:")!=-1 or href.find("/wiki/Template_talk:")!=-1 or href.find("action=")!=-1 or href.find("/wiki/File:")!=-1or href.find("/wiki/Help:")!=-1:
		if href.find("/wiki/")==-1 or href.find("action=")!=-1 or href.find(":")!=-1:
			#print "bad", link.attrib
			continue

		context = etree.tostring(link.getparent())
		parent = link.getparent()
		invalid = False
		while parent != None:
			if parent.tag == "div" and "class" in parent.attrib:
				classes = parent.attrib["class"].split(" ")
				for cl in classes:
					if cl in ["dablink", "NavHead", "NavFrame", "NavContent", "thumbcaption", "thumbinner", "thumb", "tright", "rellink"]:
						invalid = True
						break
					else:
						raise Exception, (link.attrib, parent.attrib, context)
			elif parent.tag in ["i", "table"]:
				invalid = True
				break
			elif parent.tag in ["span"] and parent.attrib["id"] in ["coordinates"]:
				invalid = True
				break
			parent = parent.getparent()

		text = "href=\"%s\""%href
		location = context.find(text)
		assert location!=-1, (text, context)
		count = 0
		for i in range(location, 0, -1):
			if context[i] == ")":
				count -=1
			elif context[i] == "(":
				count +=1

		if count != 0:
			invalid = True
		
		if invalid:
			#print "invalid", link.attrib
			continue
		#print "valid", link.attrib
		#print etree.tostring(link.getparent())
		assert href.find("/wiki/")==0, href
		return href[len("/wiki/"):]
	return None

if __name__ == "__main__":
	link = argv[1]
	links = [link]

	con = sqlite3.connect("links.sqlite")
	cur = con.cursor()
	cur.execute("select name from sqlite_master where type='table' and name='links'")
	if len(cur.fetchall())==0:
		cur.execute("create table links (name text primary key, next text, loopCount int, waysHere int)")

	while True:
		print link
		cur.execute("select next from links where name='%s'"%link)
		f = cur.fetchall()
		if len(f)!=1:
			newlink = get_next_link(link)
			cur.execute("insert into links values (?, ?, 0, 1)",(link, newlink))
			con.commit()
		else:
			newlink = f[0][0]
		link = newlink
		if link in links:
			print "loop", link
			break
		links.append(link)
