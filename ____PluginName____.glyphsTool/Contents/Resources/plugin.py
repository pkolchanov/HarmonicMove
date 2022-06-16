# encoding: utf-8

###########################################################################################################
#
#
#	Select Tool Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/SelectTool
#
#
###########################################################################################################

from __future__ import division, print_function, unicode_literals
import objc
from math import sqrt
from scipy.optimize import fsolve
from GlyphsApp import *
from GlyphsApp.plugins import *

def getIntersection( x1,y1, x2,y2, x3,y3, x4,y4 ):
	px = ( (x1*y2-y1*x2)*(x3-x4)-(x1-x2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) ) 
	py = ( (x1*y2-y1*x2)*(y3-y4)-(y1-y2)*(x3*y4-y3*x4) ) / ( (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4) )
	return px, py

def derivative(p0,p1,p2,p3,t):
	return 3*((1-t)**2)*(p1-p0) +6*(1-t)*t*(p2-p1) + 3*(t**2)*(p3-p2)

def second_derivative(p0,p1,p2,p3,t):
	return 6*(1-t)*(p2-2*p1+p0)+6*t*(p3-2*p2+p1)

def curvature(x_0,y_0,x_1,y_1,x_2,y_2,x_3,y_3, t):
	dx = derivative(x_0, x_1, x_2, x_3, t)
	ddx = second_derivative(x_0, x_1, x_2, x_3, t)
	dy = derivative(y_0, y_1, y_2, y_3, t)
	ddy = second_derivative(y_0, y_1, y_2, y_3, t)
	return (ddx * dy + ddy * dx) / ((dy ** 2 + dx ** 2) ** 1.5)


def get_line_params(x_0,y_0,x_1,y_1):
	if x_0-x_1 != 0:
		z = (y_0-y_1)/(x_0-x_1)
	else :
		z = 0
	b = (y_0+y_1 - z*(x_0+x_1))/2
	return z, b


#todos
# fsolve → ?
# only scale handles?
# move anyway if cant

class ____PluginClassName____(SelectTool):

	@objc.python_method
	def settings(self):
		self.name = Glyphs.localize({'en': u'My Select Tool', 'de': u'Mein Auswahlwerkzeug'})
		self.generalContextMenus = [
			{'name': Glyphs.localize({'en': u'Layer info in Macro window', 'de': u'Ebenen-Infos in Makro-Fenster'}), 'action': self.printInfo_},
		]
		self.keyboardShortcut = 'c'

	@objc.python_method
	def start(self):
		pass
	
	@objc.python_method
	def activate(self):
		pass
	
	@objc.python_method
	def background(self, layer):
		if len(layer.selection) != 1:
			return

		for shape in layer.shapes:
			if not shape.nodes:
				continue
			for node in shape.nodes:
				
				if node in layer.selection:

					N = node.nextNode
					NN = node.nextNode.nextNode
					P = node.prevNode
					PP = node.prevNode.prevNode

					if node.type == 'offcurve' and N.type =='offcurve' :
						xIntersect, yIntersect = (
										getIntersection( 
											node.x, node.y, P.x, P.y,
											N.x, N.y, NN.x, NN.y,
											) 
										)
						intersection = NSPoint( xIntersect, yIntersect )
					if  node.type == 'offcurve' and P.type =='offcurve': 
						xIntersect, yIntersect = (
										getIntersection( 
											node.x, node.y, N.x, N.y,
											P.x, P.y, PP.x, PP.y,
											) 
										)
						intersection = NSPoint( xIntersect, yIntersect )
					
					if intersection:
						handleSize = 5
						print(intersection)
						rect = NSRect()
						rect.origin = NSPoint(intersection.x-handleSize/2, intersection.y-handleSize/2)
						rect.size = NSSize(handleSize, handleSize)
						NSBezierPath.bezierPathWithOvalInRect_(rect).fill()

					

	@objc.python_method
	def deactivate(self):
		pass
	

	def moveSelectionWithPoint_withModifier_(self, delta,modidierKeys):
		print(delta, modidierKeys, self.draggStart(), self.dragging())
		draggStart = self.draggStart()
		isDragging = self.dragging()
		#objc.super(____PluginClassName____, self).moveSelectionWithPoint_withModifier_(delta, modidierKeys)
		layer = self.editViewController().graphicView().activeLayer()
		if len(layer.selection) != 1:
			return
		for shape in layer.shapes:
			if not shape.nodes:
				continue
			for node in shape.nodes:
				if node in layer.selection:
				

					N = node.nextNode
					NN = node.nextNode.nextNode
					P = node.prevNode
					PP = node.prevNode.prevNode
					target_positon = addPoints(draggStart, delta) if isDragging else addPoints(node.position, delta)
					
					if node.type == 'offcurve' and N.type =='offcurve':
						print ('P1')
						x_0, y_0, x_1,y_1, x_2,y_2,x_3,y_3 = P.x, P.y, node.x, node.y, N.x, N.y, NN.x, NN.y
						initial_k = curvature(x_0,y_0, x_1,y_1, x_2,y_2,x_3,y_3, 0)

						if (x_2 == x_3):
							def to_solve(to_optimize):
								return initial_k -curvature(x_0,y_0,target_positon.x,target_positon.y,x_2,to_optimize,x_3,y_3,0)
							new_y_2 = fsolve(to_solve, N.y)[0]
							if new_y_2 == y_2:
								break
							N.position = NSPoint(x_2, new_y_2)
							node.position = target_positon
						else:
							z, b = get_line_params(x_2,y_2,x_3,y_3)
							def to_solve(new_x_2):
								new_y_2 = z*new_x_2+b
								return initial_k -curvature(x_0,y_0,target_positon.x,target_positon.y,new_x_2,new_y_2,x_3,y_3,0)
							new_x_2 = fsolve(to_solve, x_2)[0]

							N.position = NSPoint(new_x_2, z*new_x_2+b)
							node.position = target_positon

					if node.type == 'offcurve' and P.type =='offcurve':
						print ('P2' )
						x_0, y_0, x_1,y_1, x_2,y_2,x_3,y_3 = PP.x, PP.y, P.x, P.y, node.x, node.y, N.x, N.y
						initial_k = curvature(x_0, y_0, x_1,y_1, x_2,y_2,x_3,y_3, 1)

					
						if (x_0 == x_1):
							def to_solve(new_y_1):
								return initial_k -curvature(x_0,y_0,x_1, new_y_1,target_positon.x,target_positon.y,x_3,y_3,1)

							new_y_1 = fsolve(to_solve, y_1)[0]
							P.position = NSPoint(x_1, new_y_1)
							node.position = target_positon
						else:
							z, b = get_line_params(x_0,y_0,x_1,y_1)
							def to_solve(new_x_1):
								new_y_1 = z*new_x_1+b
								return initial_k -curvature(x_0,y_0,new_x_1,new_y_1,target_positon.x,target_positon.y, x_3,y_3,1)

							new_x_1 = fsolve(to_solve, x_1)[0]
							P.position = NSPoint(new_x_1, z*new_x_1+b)
							node.position = target_positon

	def printInfo_(self, sender):
		"""
		Example for a method triggered by a context menu item.
		Fill in your own method name and code.
		Remove this method if you do not want any extra context menu items.
		"""

		# Execute only if layers are actually selected
		if Glyphs.font.selectedLayers:
			layer = Glyphs.font.selectedLayers[0]
		
			# Do stuff:
			print("Current layer:", layer.parent.name, layer.name)
			print("  Number of paths:", len(layer.paths))
			print("  Number of components:", len(layer.components))
			print("  Number of anchors:", len(layer.anchors))

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__
