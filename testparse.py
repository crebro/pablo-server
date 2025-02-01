from utils.turtle_parser import Parser

source = 'repeat 5 [ fd 100 ]'
parser = Parser(source)
print(parser.parse())

