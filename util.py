import sys

def showUsage():
	sys.stderr.write("""Command line usage:
""" + sys.argv[0] + """ <module> <command> <options>
""")
	sys.exit()
